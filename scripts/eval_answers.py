#!/usr/bin/env python3
"""Évaluation de la qualité des réponses via POST /api/answer.

Charge un jeu de données golden (YAML), pose chaque question à l'API,
vérifie les mots-clés attendus, et optionnellement utilise Ollama comme juge.

Usage:
  python scripts/eval_answers.py
  python scripts/eval_answers.py --dataset evals/golden_dataset.yaml
  python scripts/eval_answers.py --mode strict
  python scripts/eval_answers.py --judge          # scoring Ollama
  python scripts/eval_answers.py --output eval_result.csv
  python scripts/eval_answers.py --id livraison_01  # un seul cas

Dépendances : pip install click httpx pyyaml
"""
import csv
import json
from pathlib import Path

import click
import httpx
import yaml

DEFAULT_DATASET = Path("evals/golden_dataset.yaml")

_JUDGE_PROMPT = """\
Tu évalues la réponse d'un assistant wiki. Note sur 3 dimensions.
Réponds UNIQUEMENT avec un objet JSON : {{"pertinence": <0-3>, "sources": <0-2>, "format": <0-1>}}

Guide de notation :
- pertinence (0-3) : 3=répond exactement, 2=partiellement, 1=tangentiel, 0=hors sujet
- sources    (0-2) : 2=sources correctes citées, 1=sources vagues, 0=aucune source ou hallucination
- format     (0-1) : 1=réponse claire et structurée, 0=prose confuse

Question posée : {question}

Mots-clés attendus : {expected_keywords}

Réponse de l'assistant :
{response}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_dataset(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def call_answer(question: str, mode: str, api_url: str, api_key: str) -> dict:
    headers = {"X-API-Key": api_key} if api_key else {}
    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            f"{api_url}/api/answer",
            json={"question": question, "mode": mode},
            headers=headers,
        )
        response.raise_for_status()
        return response.json()


def judge_with_ollama(
    question: str,
    expected_keywords: list[str],
    answer: str,
    ollama_url: str,
    ollama_model: str,
) -> dict[str, int]:
    prompt = _JUDGE_PROMPT.format(
        question=question,
        expected_keywords=", ".join(expected_keywords),
        response=answer,
    )
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{ollama_url}/api/generate",
                json={"model": ollama_model, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            raw = response.json()["response"].strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw)
    except Exception:
        return {"pertinence": -1, "sources": -1, "format": -1}


def check_keywords(answer: str, expected_keywords: list[str]) -> tuple[bool, list[str]]:
    lower = answer.lower()
    found = [kw for kw in expected_keywords if kw.lower() in lower]
    return len(found) > 0, found


def _print_separator(case_id: str) -> None:
    click.echo(f"\n{'━' * 3} {case_id} {'━' * 30}")


def _print_summary(total: int, passed: int, failed: int, errors: int) -> None:
    icon = "✅" if failed == 0 and errors == 0 else "❌"
    click.echo(
        f"\n{icon} {total} cas — {passed} passés, {failed} échoués, {errors} erreurs"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.command()
@click.option("--dataset", default=str(DEFAULT_DATASET), show_default=True,
              type=click.Path(exists=True, dir_okay=False),
              help="Fichier YAML golden dataset")
@click.option("--api-url", default="http://localhost:8088", show_default=True,
              help="URL de l'API OpenWikiLLM")
@click.option("--api-key", default="", envvar="API_KEY",
              help="Clé API (ou via API_KEY env)")
@click.option("--mode", default=None,
              type=click.Choice(["draft", "strict", "source_only", "validated_only"]),
              help="Override le mode de chaque cas du dataset")
@click.option("--judge", is_flag=True, default=False,
              help="Utiliser Ollama pour scorer la qualité des réponses")
@click.option("--ollama-url", default="http://localhost:11434", show_default=True,
              help="URL Ollama (pour --judge)")
@click.option("--ollama-model", default="mistral", show_default=True, envvar="OLLAMA_MODEL",
              help="Modèle Ollama (ou via OLLAMA_MODEL env)")
@click.option("--id", "case_id", default=None,
              help="Exécuter uniquement ce cas (par id)")
@click.option("--output", default=None, type=click.Path(dir_okay=False),
              help="Exporter les résultats en CSV")
def main(dataset, api_url, api_key, mode, judge, ollama_url, ollama_model, case_id, output):
    """Évaluation de la qualité des réponses via POST /api/answer."""
    cases = load_dataset(Path(dataset))
    if case_id:
        cases = [c for c in cases if c.get("id") == case_id]
        if not cases:
            click.echo(f"Cas introuvable : {case_id}", err=True)
            raise SystemExit(1)

    results = []
    passed = failed = errors = 0

    for case in cases:
        cid = case.get("id", "?")
        question = case["question"]
        effective_mode = mode or case.get("mode", "validated_only")
        expected = case.get("expected_keywords", [])
        notes = case.get("notes", "")

        _print_separator(cid)
        if notes:
            click.echo(f"   ℹ  {notes}")
        click.echo(f"   Q: {question}")
        click.echo(f"   mode: {effective_mode}")

        try:
            data = call_answer(question, effective_mode, api_url, api_key)
            answer_text = data.get("answer", "")
            sources = data.get("sources", [])
        except httpx.HTTPStatusError as e:
            click.echo(f"   ✗  HTTP {e.response.status_code}: {e.response.text[:200]}", err=True)
            errors += 1
            results.append({"id": cid, "status": "error", "answer": "", "keywords_found": "", "sources": "", "score_pertinence": "", "score_sources": "", "score_format": ""})
            continue
        except Exception as e:
            click.echo(f"   ✗  {e}", err=True)
            errors += 1
            results.append({"id": cid, "status": "error", "answer": "", "keywords_found": "", "sources": "", "score_pertinence": "", "score_sources": "", "score_format": ""})
            continue

        kw_ok, kw_found = check_keywords(answer_text, expected)
        status = "PASS" if kw_ok else "FAIL"
        icon = "✓" if kw_ok else "✗"

        click.echo(f"   {icon}  {status} — mots-clés trouvés: {kw_found or '—'}")
        click.echo(f"   A: {answer_text[:200]}{'…' if len(answer_text) > 200 else ''}")
        if sources:
            click.echo(f"   sources: {', '.join(sources)}")

        row = {
            "id": cid,
            "status": status,
            "answer": answer_text[:500],
            "keywords_found": ", ".join(kw_found),
            "sources": ", ".join(sources),
            "score_pertinence": "",
            "score_sources": "",
            "score_format": "",
        }

        if judge:
            scores = judge_with_ollama(question, expected, answer_text, ollama_url, ollama_model)
            row["score_pertinence"] = scores.get("pertinence", "")
            row["score_sources"] = scores.get("sources", "")
            row["score_format"] = scores.get("format", "")
            total_score = sum(v for v in scores.values() if isinstance(v, int) and v >= 0)
            click.echo(f"   🔍 score Ollama: pertinence={scores.get('pertinence', '?')} sources={scores.get('sources', '?')} format={scores.get('format', '?')} → total={total_score}/6")

        results.append(row)
        if kw_ok:
            passed += 1
        else:
            failed += 1

    _print_summary(len(cases), passed, failed, errors)

    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["id", "status", "answer", "keywords_found", "sources",
                            "score_pertinence", "score_sources", "score_format"],
            )
            writer.writeheader()
            writer.writerows(results)
        click.echo(f"\n📄 Résultats exportés → {output}")


if __name__ == "__main__":
    main()
