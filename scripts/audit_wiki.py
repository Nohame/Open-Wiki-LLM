#!/usr/bin/env python3
"""Audit des pages wiki : détecte les pages incomplètes, stales ou problématiques.

Scanne le dossier wiki/, parse chaque frontmatter YAML et signale :
  - pages en statut draft ou sans statut
  - confidence low ou absente
  - sources vides
  - updated_at trop ancienne (> --max-age-days)
  - liens wiki cassés [[Page]] qui ne correspondent à aucune page existante

Usage:
  python scripts/audit_wiki.py
  python scripts/audit_wiki.py --wiki-dir ./wiki
  python scripts/audit_wiki.py --max-age-days 30
  python scripts/audit_wiki.py --output audit.csv
  python scripts/audit_wiki.py --only-issues

Dépendances : pip install click python-frontmatter
"""
import csv
import re
from datetime import date, timedelta
from pathlib import Path

import click
import frontmatter

WIKI_LINK_RE = re.compile(r"\[\[([^\]]+)\]")


# ---------------------------------------------------------------------------
# Issue detection
# ---------------------------------------------------------------------------

def _slug_from_path(wiki_path: Path, file_path: Path) -> str:
    return str(file_path.relative_to(wiki_path).with_suffix("")).replace("/", "--")


def _all_slugs(wiki_path: Path) -> set[str]:
    slugs = set()
    for f in wiki_path.rglob("*.md"):
        if f.name == "index.md":
            continue
        slugs.add(_slug_from_path(wiki_path, f))
    return slugs


def audit_page(
    file_path: Path,
    wiki_path: Path,
    known_slugs: set[str],
    max_age_days: int,
) -> dict:
    slug = _slug_from_path(wiki_path, file_path)
    issues = []

    try:
        post = frontmatter.load(str(file_path))
    except Exception as e:
        return {
            "slug": slug,
            "path": str(file_path.relative_to(wiki_path)),
            "status": "?",
            "confidence": "?",
            "sources": 0,
            "updated_at": "",
            "issues": [f"frontmatter parse error: {e}"],
        }

    meta = post.metadata
    status = meta.get("status", "")
    confidence = meta.get("confidence", "")
    sources = meta.get("sources") or []
    updated_at = meta.get("updated_at", "")

    if status in ("draft", ""):
        issues.append(f"status={status or 'manquant'}")

    if confidence in ("low", ""):
        issues.append(f"confidence={confidence or 'manquant'}")

    if not sources:
        issues.append("sources vides")

    if updated_at:
        try:
            if isinstance(updated_at, str):
                d = date.fromisoformat(updated_at)
            else:
                d = updated_at
            age = (date.today() - d).days
            if age > max_age_days:
                issues.append(f"stale ({age}j > {max_age_days}j)")
        except (ValueError, TypeError):
            issues.append(f"updated_at invalide: {updated_at!r}")
    else:
        issues.append("updated_at manquant")

    wiki_links = WIKI_LINK_RE.findall(post.content)
    for link in wiki_links:
        link_slug = link.lower().replace(" ", "-")
        if link_slug not in known_slugs:
            issues.append(f"lien cassé: [[{link}]]")

    return {
        "slug": slug,
        "path": str(file_path.relative_to(wiki_path)),
        "status": status or "—",
        "confidence": confidence or "—",
        "sources": len(sources) if isinstance(sources, list) else 0,
        "updated_at": str(updated_at) if updated_at else "—",
        "issues": issues,
    }


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def _severity(issues: list[str]) -> str:
    if not issues:
        return "ok"
    critical = {"status=draft", "sources vides", "frontmatter parse error"}
    for issue in issues:
        for c in critical:
            if issue.startswith(c):
                return "❌"
    return "⚠ "


def _print_row(row: dict, only_issues: bool) -> None:
    issues = row["issues"]
    if only_issues and not issues:
        return
    icon = _severity(issues)
    issues_str = ", ".join(issues) if issues else "—"
    click.echo(
        f"  {icon}  {row['path']:<45} "
        f"status={row['status']:<12} "
        f"confidence={row['confidence']:<8} "
        f"sources={row['sources']}  "
        f"→ {issues_str}"
    )


def _print_summary(total: int, with_issues: int, clean: int) -> None:
    icon = "✅" if with_issues == 0 else "⚠ "
    click.echo(
        f"\n{icon} {total} pages auditées — "
        f"{with_issues} avec problèmes, {clean} propres"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.command()
@click.option("--wiki-dir", default="./wiki", show_default=True,
              type=click.Path(exists=True, file_okay=False),
              help="Répertoire wiki à auditer")
@click.option("--max-age-days", default=90, show_default=True,
              help="Âge max (jours) avant de marquer une page stale")
@click.option("--output", default=None, type=click.Path(dir_okay=False),
              help="Exporter le rapport en CSV")
@click.option("--only-issues", is_flag=True, default=False,
              help="Afficher uniquement les pages avec des problèmes")
def main(wiki_dir, max_age_days, output, only_issues):
    """Audit des pages wiki : détecte les pages incomplètes ou problématiques."""
    wiki_path = Path(wiki_dir)
    pages = [f for f in sorted(wiki_path.rglob("*.md")) if f.name != "index.md"]

    if not pages:
        click.echo(f"Aucune page trouvée dans {wiki_path}")
        return

    known_slugs = _all_slugs(wiki_path)
    results = []

    click.echo(f"\nAudit de {len(pages)} pages dans {wiki_path}\n")

    for page in pages:
        row = audit_page(page, wiki_path, known_slugs, max_age_days)
        results.append(row)
        _print_row(row, only_issues)

    with_issues = sum(1 for r in results if r["issues"])
    clean = len(results) - with_issues
    _print_summary(len(results), with_issues, clean)

    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["slug", "path", "status", "confidence", "sources", "updated_at", "issues"],
            )
            writer.writeheader()
            for row in results:
                writer.writerow({**row, "issues": "; ".join(row["issues"])})
        click.echo(f"\n📄 Rapport exporté → {output}")


if __name__ == "__main__":
    main()
