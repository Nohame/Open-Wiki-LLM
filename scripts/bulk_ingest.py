#!/usr/bin/env python3
"""Ingestion en masse des fichiers bruts via POST /api/ingest/text.

Scanne un répertoire source, envoie chaque fichier à l'API OpenWikiLLM,
et tient un manifeste JSON pour éviter les doublons.

Usage:
  python scripts/bulk_ingest.py
  python scripts/bulk_ingest.py --raw-dir ./raw/imports
  python scripts/bulk_ingest.py --api-url http://localhost:8088 --api-key secret
  python scripts/bulk_ingest.py --tags documentation --tags procedure
  python scripts/bulk_ingest.py --dry-run
  python scripts/bulk_ingest.py --force   # réingère même les fichiers déjà traités

Dépendances : pip install click httpx
"""
import json
import re
from pathlib import Path

import click
import httpx

MANIFEST_PATH = Path("data/ingest_manifest.json")
SUPPORTED_EXTENSIONS = {".md", ".txt"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {}


def save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _title_from_path(path: Path) -> str:
    name = path.stem.replace("-", " ").replace("_", " ")
    return name.capitalize()


def _print_separator(name: str) -> None:
    click.echo(f"\n{'━' * 3} {name} {'━' * 30}")


def _print_skip(name: str, reason: str) -> None:
    click.echo(f"⏭  SKIP {name} : {reason}")


def _print_run(name: str, title: str) -> None:
    click.echo(f"▶  {name:<40} → {title}")


def _print_ok(slug: str) -> None:
    click.echo(f"   ✓  slug: {slug}")


def _print_error(err: str) -> None:
    click.echo(f"   ✗  {err}", err=True)


def _print_summary(treated: int, skips: int, errors: int) -> None:
    icon = "✅" if errors == 0 else "❌"
    click.echo(
        f"\n{icon} Terminé : {treated} fichiers ingérés, {skips} skips, {errors} erreurs"
    )


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def discover_files(raw_dir: Path) -> list[Path]:
    files = []
    for ext in SUPPORTED_EXTENSIONS | IMAGE_EXTENSIONS:
        files.extend(sorted(raw_dir.rglob(f"*{ext}")))
    return files


def ingest_file(
    path: Path,
    title: str,
    tags: list[str],
    api_url: str,
    api_key: str,
) -> dict:
    headers = {"X-API-Key": api_key} if api_key else {}
    if path.suffix.lower() in IMAGE_EXTENSIONS:
        return _ingest_image_file(path, title, tags, api_url, headers)
    payload = {
        "text": path.read_text(encoding="utf-8"),
        "title": title,
        "tags": tags,
    }
    with httpx.Client(timeout=120.0) as client:
        response = client.post(f"{api_url}/api/ingest/text", json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


def _ingest_image_file(
    path: Path,
    title: str,
    tags: list[str],
    api_url: str,
    headers: dict,
) -> dict:
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp", ".gif": "image/gif"}
    mime = mime_map.get(path.suffix.lower(), "image/png")
    with httpx.Client(timeout=180.0) as client:
        response = client.post(
            f"{api_url}/api/ingest/image",
            headers=headers,
            data={"title": title, "tags": ",".join(tags)},
            files={"file": (path.name, path.read_bytes(), mime)},
        )
        response.raise_for_status()
        return response.json()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.command()
@click.option("--raw-dir", default="./raw", show_default=True,
              type=click.Path(exists=True, file_okay=False),
              help="Répertoire source des fichiers bruts")
@click.option("--api-url", default="http://localhost:8088", show_default=True,
              help="URL de l'API OpenWikiLLM")
@click.option("--api-key", default="", envvar="API_KEY",
              help="Clé API (ou via API_KEY env)")
@click.option("--tags", multiple=True, metavar="TAG",
              help="Tags à ajouter aux pages créées (répétable)")
@click.option("--dry-run", is_flag=True, default=False,
              help="Affiche ce qui serait fait sans appeler l'API")
@click.option("--force", is_flag=True, default=False,
              help="Réingère les fichiers déjà présents dans le manifeste")
def main(raw_dir, api_url, api_key, tags, dry_run, force):
    """Ingestion en masse des fichiers bruts via POST /api/ingest/text."""
    raw_path = Path(raw_dir)
    files = discover_files(raw_path)
    manifest = load_manifest()
    tag_list = list(tags)

    if not files:
        click.echo(f"Aucun fichier trouvé dans {raw_path}")
        return

    treated = skips = errors = 0

    for path in files:
        key = str(path.relative_to(Path(".")))
        _print_separator(path.name)

        if not force and key in manifest:
            _print_skip(path.name, f"déjà ingéré → slug: {manifest[key]}")
            skips += 1
            continue

        title = _title_from_path(path)
        _print_run(path.name, title)

        if dry_run:
            click.echo(f"   [DRY-RUN] POST /api/ingest/text — title={title!r} tags={tag_list}")
            treated += 1
            continue

        try:
            result = ingest_file(path, title, tag_list, api_url, api_key)
            manifest[key] = result["slug"]
            save_manifest(manifest)
            _print_ok(result["slug"])
            treated += 1
        except httpx.HTTPStatusError as e:
            _print_error(f"HTTP {e.response.status_code}: {e.response.text[:200]}")
            errors += 1
        except Exception as e:
            _print_error(str(e))
            errors += 1

    _print_summary(treated, skips, errors)


if __name__ == "__main__":
    main()
