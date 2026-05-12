#!/usr/bin/env python3
"""Script d'intégration rétroactive des CSV historiques en base SQLite."""

import re
import subprocess
from datetime import date
from pathlib import Path

import click


# ---------------------------------------------------------------------------
# Parsing des noms de fichiers
# ---------------------------------------------------------------------------

_RE_LEGALLAIS = re.compile(r"^LCEART_(\d{4})-(\d{2})-(\d{2})\.csv$")
_RE_PEGASUS = re.compile(r"^pegasus_catalog_sentinel_export_prod_(\d{4})-(\d{2})-(\d{2})(?:_\d+)?\.csv$")
_RE_STATS = re.compile(r"^articles_stats_30d_(\d{4})-(\d{2})-(\d{2})\.csv$")


def parse_legallais_date(filename: str) -> date | None:
    """Parse LCEART_YYYY-DD-MM.csv → date. Retourne None si le nom ne matche pas."""
    m = _RE_LEGALLAIS.match(filename)
    if not m:
        return None
    yyyy, dd, mm = m.group(1), m.group(2), m.group(3)
    try:
        return date(int(yyyy), int(mm), int(dd))
    except ValueError:
        return None


def parse_pegasus_date(filename: str) -> date | None:
    """Parse pegasus_catalog_sentinel_export_prod_YYYY-MM-DD[...].csv → date."""
    m = _RE_PEGASUS.match(filename)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def parse_stats_date(filename: str) -> date | None:
    """Parse articles_stats_30d_YYYY-MM-DD.csv → date."""
    m = _RE_STATS.match(filename)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def discover_files(data_dir: Path) -> dict:
    """
    Scanne data_dir et retourne un dict avec 3 listes triées par date croissante :
      legallais : [(date, Path), ...]
      pegasus   : [(date, Path), ...]  — une seule entrée par date (premier alphabétique)
      stats     : [(date, Path), ...]
    """
    legallais: dict[date, Path] = {}
    pegasus: dict[date, Path] = {}
    stats: dict[date, Path] = {}

    for f in sorted(data_dir.iterdir()):  # sorted → ordre alphabétique pour la dédup Pegasus
        if not f.is_file() or f.suffix != ".csv":
            continue
        name = f.name
        d = parse_legallais_date(name)
        if d:
            legallais.setdefault(d, f)
            continue
        d = parse_pegasus_date(name)
        if d:
            pegasus.setdefault(d, f)  # setdefault = premier alphabétique gagne
            continue
        d = parse_stats_date(name)
        if d:
            stats.setdefault(d, f)

    return {
        "legallais": sorted(legallais.items()),
        "pegasus": sorted(pegasus.items()),
        "stats": sorted(stats.items()),
    }


# ---------------------------------------------------------------------------
# Pairing logic (N/N-1 matching)
# ---------------------------------------------------------------------------


def find_nearest_stats(
    stats: list[tuple[date, Path]], target: date
) -> tuple[date, Path] | None:
    """
    Retourne le fichier stats le plus adapté pour la date target :
    - Priorité 1 : le plus récent <= target
    - Priorité 2 : le plus proche > target (fallback)
    - None si stats est vide
    """
    if not stats:
        return None
    lte = [(d, p) for d, p in stats if d <= target]
    if lte:
        return max(lte, key=lambda x: x[0])
    # fallback : le plus proche futur
    return min((x for x in stats if x[0] > target), key=lambda x: x[0])


def build_delta_pairs(
    files: list[tuple[date, Path]],
    stats: list[tuple[date, Path]],
) -> list[dict]:
    """
    Construit la liste des appariements pour une commande delta (legallais ou pegasus).
    Chaque élément est un dict avec les clés :
      date, skip, reason, prev, curr, stats_file, stats_date, gap, gap_days
    """
    result = []
    for i, (d, curr_path) in enumerate(files):
        entry: dict = {"date": d, "skip": False, "reason": "", "prev": None, "curr": None, "prev_date": None, "gap": False, "gap_days": 0}

        # Chercher N-1
        prev_candidates = [(pd, pp) for pd, pp in files[:i] if pd < d]
        if not prev_candidates:
            entry["skip"] = True
            entry["reason"] = "aucun fichier antérieur disponible"
            result.append(entry)
            continue

        prev_date, prev_path = max(prev_candidates, key=lambda x: x[0])
        entry["prev"] = prev_path
        entry["curr"] = curr_path
        entry["prev_date"] = prev_date

        # Gap detection
        delta_days = (d - prev_date).days
        if delta_days > 1:
            entry["gap"] = True
            entry["gap_days"] = delta_days

        # Chercher stats
        stats_entry = find_nearest_stats(stats, d)
        if stats_entry is None:
            entry["skip"] = True
            entry["reason"] = "aucun fichier sales_stats disponible"
            result.append(entry)
            continue

        entry["stats_date"], entry["stats_file"] = stats_entry
        result.append(entry)

    return result


def build_funnel_pairs(
    legallais: list[tuple[date, Path]],
    pegasus: list[tuple[date, Path]],
) -> list[dict]:
    """
    Construit la liste des appariements pour la commande funnel.
    Nécessite un fichier Legallais ET Pegasus à la même date ISO exacte.
    """
    peg_by_date = {d: p for d, p in pegasus}
    result = []
    for d, leg_path in legallais:
        entry: dict = {"date": d, "skip": False, "reason": ""}
        if d not in peg_by_date:
            entry["skip"] = True
            entry["reason"] = "aucun fichier Pegasus pour cette date"
        else:
            entry["legallais"] = leg_path
            entry["pegasus"] = peg_by_date[d]
        result.append(entry)
    return result


# ---------------------------------------------------------------------------
# Exécution
# ---------------------------------------------------------------------------


def run_command(cmd: list[str], dry_run: bool = False) -> tuple[int, str, str]:
    """
    Exécute cmd via subprocess.
    En dry-run : affiche la commande et retourne (0, '', '').
    Retourne (returncode, stdout, stderr).
    """
    if dry_run:
        click.echo(f"  [DRY-RUN] {' '.join(cmd)}")
        return 0, "", ""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


# ---------------------------------------------------------------------------
# Helpers d'affichage
# ---------------------------------------------------------------------------


def _stats_label(stats_date: date, target: date) -> str:
    """Formate le label stats avec décalage en jours."""
    delta = (stats_date - target).days
    sign = "+" if delta >= 0 else ""
    return f"stats: {stats_date.isoformat()}{sign}{delta}j"


def _print_separator(d: date) -> None:
    """Affiche un séparateur avec la date."""
    click.echo(f"\n{'━' * 3} {d} {'━' * 30}")


def _print_gap(prev_date: date, curr_date: date, gap_days: int) -> None:
    """Affiche un avertissement pour un gap détecté."""
    click.echo(f"⚠  Gap détecté : {prev_date} → {curr_date} ({gap_days} jours)")


def _print_skip(method: str, d: date, reason: str) -> None:
    """Affiche un skip."""
    click.echo(f"⏭  SKIP {method} {d} : {reason}")


def _print_run(method: str, label: str) -> None:
    """Affiche l'exécution d'une commande."""
    click.echo(f"▶  {method:<20} {label}")


def _print_summary(treated: int, skips: int, errors: int) -> None:
    """Affiche le résumé final."""
    icon = "✅" if errors == 0 else "❌"
    click.echo(
        f"\n{icon} Terminé : {treated} dates traitées, {skips} skips, {errors} erreurs"
    )


# ---------------------------------------------------------------------------
# Entrée CLI
# ---------------------------------------------------------------------------

VALID_METHODS = {"legallais", "pegasus", "funnel"}


@click.command()
@click.option("--data-dir", default="./data", type=click.Path(exists=True, file_okay=False), show_default=True, help="Répertoire source des CSV")
@click.option("--db", default="./data/catalogue.db", type=click.Path(dir_okay=False), show_default=True, help="Chemin SQLite")
@click.option("--methods", multiple=True, metavar="METHOD", help="legallais | pegasus | funnel (répétable, défaut: les 3)")
@click.option("--email-to", multiple=True, metavar="ADRESSE", help="Activer l'envoi email (répétable)")
@click.option("--output-dir", default=None, type=click.Path(file_okay=False, writable=True), help="Activer l'export CSV dans ce dossier")
@click.option("--no-db", is_flag=True, default=False, help="Ne pas sourcer en base")
@click.option("--dry-run", is_flag=True, default=False, help="Affiche les commandes sans les exécuter")
def main(data_dir, db, methods, email_to, output_dir, no_db, dry_run):
    """Intégration rétroactive des CSV historiques en base SQLite."""
    data_path = Path(data_dir)

    # Validation des méthodes
    active_methods = set(methods) if methods else VALID_METHODS
    unknown = active_methods - VALID_METHODS
    if unknown:
        raise click.BadParameter(f"Méthodes inconnues : {', '.join(unknown)}. Valeurs valides : {', '.join(VALID_METHODS)}")

    files = discover_files(data_path)

    db_arg = [] if no_db else ["--db", db]
    email_args = [arg for addr in email_to for arg in ["--email-to", addr]]
    output_args = ["--output-dir", output_dir] if output_dir else []
    common_opts = db_arg + email_args + output_args + ["-q"]  # -q : retro.py capture et reprint stdout

    treated = skips = errors = 0

    # --- Legallais delta ---
    if "legallais" in active_methods:
        pairs = build_delta_pairs(files["legallais"], files["stats"])
        for entry in pairs:
            d = entry["date"]
            _print_separator(d)
            if entry["skip"]:
                _print_skip("legallais-delta", d, entry["reason"])
                skips += 1
                continue
            if entry["gap"]:
                _print_gap(entry["prev_date"], d, entry["gap_days"])
            label = (
                f"{entry['prev'].name} → {entry['curr'].name}"
                f"  ({_stats_label(entry['stats_date'], d)})"
            )
            _print_run("legallais-delta", label)
            cmd = (
                ["python", "src/main.py", "analyse-legallais-delta",
                 str(entry["prev"]), str(entry["curr"]), str(entry["stats_file"]),
                 "--execution-date", d.isoformat()]
                + common_opts
            )
            code, out, err = run_command(cmd, dry_run=dry_run)
            if out:
                click.echo(out.rstrip())
            if code != 0:
                click.echo(f"  ✗ Erreur (code {code}) : {err.strip()}", err=True)
                errors += 1
            else:
                treated += 1

    # --- Pegasus delta ---
    if "pegasus" in active_methods:
        pairs = build_delta_pairs(files["pegasus"], files["stats"])
        for entry in pairs:
            d = entry["date"]
            _print_separator(d)
            if entry["skip"]:
                _print_skip("pegasus-delta", d, entry["reason"])
                skips += 1
                continue
            if entry["gap"]:
                _print_gap(entry["prev_date"], d, entry["gap_days"])
            label = (
                f"{entry['prev'].name} → {entry['curr'].name}"
                f"  ({_stats_label(entry['stats_date'], d)})"
            )
            _print_run("pegasus-delta", label)
            cmd = (
                ["python", "src/main.py", "analyse-pegasus-delta",
                 str(entry["prev"]), str(entry["curr"]), str(entry["stats_file"]),
                 "--execution-date", d.isoformat()]
                + common_opts
            )
            code, out, err = run_command(cmd, dry_run=dry_run)
            if out:
                click.echo(out.rstrip())
            if code != 0:
                click.echo(f"  ✗ Erreur (code {code}) : {err.strip()}", err=True)
                errors += 1
            else:
                treated += 1

    # --- Funnel ---
    if "funnel" in active_methods:
        pairs = build_funnel_pairs(files["legallais"], files["pegasus"])
        for entry in pairs:
            d = entry["date"]
            _print_separator(d)
            if entry["skip"]:
                _print_skip("funnel", d, entry["reason"])
                skips += 1
                continue
            label = f"{entry['legallais'].name} + {entry['pegasus'].name}"
            _print_run("funnel", label)
            cmd = (
                ["python", "src/main.py", "analyse-funnel",
                 str(entry["legallais"]), str(entry["pegasus"]),
                 "--execution-date", d.isoformat()]
                + common_opts
            )
            code, out, err = run_command(cmd, dry_run=dry_run)
            if out:
                click.echo(out.rstrip())
            if code != 0:
                click.echo(f"  ✗ Erreur (code {code}) : {err.strip()}", err=True)
                errors += 1
            else:
                treated += 1

    _print_summary(treated, skips, errors)


if __name__ == "__main__":
    main()
