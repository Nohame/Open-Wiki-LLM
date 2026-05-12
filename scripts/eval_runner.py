#!/usr/bin/env python3
"""Catalog Sentinel — LLM-as-judge evaluation runner.

Usage:
    python scripts/eval_runner.py
    python scripts/eval_runner.py --category vendability
    python scripts/eval_runner.py --id vendability_legallais_01
    python scripts/eval_runner.py --output rapports/eval_2026-05-04.csv
    python scripts/eval_runner.py --id vendability_sur_commande_01 --trace
    python scripts/eval_runner.py --category lookup --trace
"""
from __future__ import annotations

import csv
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

import click
import yaml
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

# Ensure src/ is on sys.path so agentic_search imports work
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from agentic_search import run_agent  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATASET_PATH = Path(__file__).parent.parent / "evals" / "golden_dataset.yaml"
FLASH_MODEL = "gemini-3-flash-preview"

_JUDGE_PROMPT = """\
You are evaluating a catalog assistant's response. Score it on 3 dimensions.
Reply ONLY with a JSON object: {{"pertinence": <0-3>, "perimetre": <0-2>, "format": <0-1>}}

Scoring guide:
- pertinence (0-3): 3=answers exactly, 2=answers partially, 1=tangential, 0=no answer
- perimetre (0-2): 2=scope correct, 1=ambiguous/minor drift, 0=wrong scope or hallucination
- format (0-1): 1=uses structured blocks (<data>, <choices>) when relevant, 0=plain prose only

Question asked: {question}

Quality criteria expected:
{criteria}

Agent response:
{response}
"""

# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------


def parse_judge_score(raw: str) -> dict[str, int]:
    """Parse Flash judge JSON response. Returns zeros on parse failure.

    Handles three response formats:
    - Raw JSON          : {"pertinence": 2, ...}
    - Markdown fence    : ```json\\n{"pertinence": 2, ...}\\n```
    - Inline JSON       : "Here is my evaluation: {"pertinence": 2, ...}"
    """
    try:
        stripped = raw.strip()
        if stripped.startswith("```"):
            stripped = stripped.split("```")[1]
            if stripped.startswith("json"):
                stripped = stripped[4:]
        # Direct parse first (fastest path)
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            # Fallback: extract first {...} block (handles prose-wrapped JSON)
            match = re.search(r'\{[^{}]+\}', stripped, re.DOTALL)
            if not match:
                raise ValueError(f"No JSON object found in judge response")  # noqa: TRY301
            data = json.loads(match.group())
        return {
            "pertinence": max(0, min(3, int(data.get("pertinence", 0)))),
            "perimetre": max(0, min(2, int(data.get("perimetre", 0)))),
            "format": max(0, min(1, int(data.get("format", 0)))),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("parse_judge_score failed (%s) — raw: %r", exc, raw[:300])
        return {"pertinence": 0, "perimetre": 0, "format": 0}


def check_constraints(
    case: dict,
    tools_called: list[str],
    perf: dict,
) -> dict[str, bool]:
    """Check binary constraints. All failures are logged, not raised."""
    results: dict[str, bool] = {}

    expected = set(case.get("expected_tools", []))
    called_set = set(tools_called)
    results["expected_tools_called"] = expected.issubset(called_set)

    must_not = set(case.get("must_not_call", []))
    results["must_not_call_respected"] = must_not.isdisjoint(called_set)

    llm_calls = len(perf.get("llm_calls", []))
    results["max_llm_calls_ok"] = llm_calls <= case["constraints"]["max_llm_calls"]

    mcp_calls = len(perf.get("mcp_calls", []))
    results["max_mcp_calls_ok"] = mcp_calls <= case["constraints"]["max_mcp_calls"]

    return results


_MAX_SCORE = 3 + 2 + 1  # pertinence + perimetre + format


def aggregate_results(results: list[dict]) -> dict[str, Any]:
    """Compute summary statistics over all scored cases."""
    if not results:
        return {}
    total = len(results)
    avg_score = sum(r["total_score"] for r in results) / total
    passed_constraints = sum(
        1 for r in results if r.get("constraints") and all(r["constraints"].values())
    )
    return {
        "total_cases": total,
        "avg_score": round(avg_score, 2),
        "avg_score_pct": round(avg_score / _MAX_SCORE * 100, 1),
        "constraint_pass_rate": round(passed_constraints / total * 100, 1),
    }


# ---------------------------------------------------------------------------
# Judge
# ---------------------------------------------------------------------------


def _cap_response(r: str, limit: int = 4000) -> str:
    """Cap response length while preserving tail (where structured blocks appear)."""
    if len(r) <= limit:
        return r
    half = limit // 2
    return r[:half] + "\n…[truncated]…\n" + r[-half:]


def score_response(
    case: dict,
    response: str,
    tools_called: list[str],
    perf: dict,
    llm: ChatGoogleGenerativeAI,
) -> dict[str, Any]:
    """Score a single case using the provided Flash LLM judge. Returns a result dict."""
    criteria_text = "\n".join(f"- {c}" for c in case.get("quality_criteria", []))
    prompt = _JUDGE_PROMPT.format(
        question=case["question"],
        criteria=criteria_text,
        response=_cap_response(response),
    )
    content = llm.invoke([HumanMessage(content=prompt)]).content
    # Normalise to str — langchain-google-genai 4.x may return a list of typed blocks.
    if isinstance(content, list):
        raw = " ".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    else:
        raw = content
    scores = parse_judge_score(raw)
    total_score = scores["pertinence"] + scores["perimetre"] + scores["format"]
    constraints = check_constraints(case, tools_called, perf)

    return {
        "id": case["id"],
        "category": case["category"],
        "question": case["question"][:80],
        "intent_detected": perf.get("intent", "?"),
        "expected_intent": case.get("expected_intent", "?"),
        "intent_correct": perf.get("intent", "?") == case.get("expected_intent", "?"),
        "pertinence": scores["pertinence"],
        "perimetre": scores["perimetre"],
        "format": scores["format"],
        "total_score": total_score,
        "constraints": constraints,
        "all_constraints_pass": all(constraints.values()),
        "response_preview": response[:200],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.command()
@click.option("--category", default=None, help="Filter by category (vendability, catalog_state, lookup, robustesse)")
@click.option("--id", "case_id", default=None, help="Run a single case by ID")
@click.option("--output", default=None, help="CSV output path (e.g. rapports/eval_2026-05-04.csv)")
@click.option("--dataset", default=str(DATASET_PATH), help="Path to golden_dataset.yaml")
@click.option("--trace", is_flag=True, default=False, help="Print agent tool-call trace for cases with constraint failures")
def main(category: str | None, case_id: str | None, output: str | None, dataset: str, trace: bool) -> None:
    """Run LLM-as-judge evaluation against the golden dataset."""
    with open(dataset, encoding="utf-8") as f:
        cases = yaml.safe_load(f)

    # Filter
    if case_id:
        cases = [c for c in cases if c["id"] == case_id]
        if not cases:
            click.echo(f"No case found with id={case_id}", err=True)
            sys.exit(1)
    elif category:
        cases = [c for c in cases if c["category"] == category]
        if not cases:
            click.echo(f"No cases found for category={category}", err=True)
            sys.exit(1)

    # Instantiate Flash judge once — avoids repeated connection-pool creation per case
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        click.echo("GOOGLE_API_KEY manquante pour le juge Flash.", err=True)
        sys.exit(1)
    judge_llm = ChatGoogleGenerativeAI(model=FLASH_MODEL, temperature=0, google_api_key=api_key)

    click.echo(f"Running {len(cases)} case(s)…\n")
    all_results: list[dict] = []

    for case in cases:
        click.echo(f"[{case['id']}] {case['question'][:60]}…")
        t0 = time.perf_counter()
        try:
            response, tools_called, full_trace, perf, intent = run_agent(case["question"], [])
            perf["intent"] = intent  # inject intent into perf for scoring
            elapsed = time.perf_counter() - t0
            result = score_response(case, response, tools_called, perf, judge_llm)
            result["elapsed_s"] = round(elapsed, 1)
            result["error"] = None
            all_results.append(result)
            _print_result(result)
            if trace and not result["all_constraints_pass"]:
                _print_trace(full_trace, result["constraints"])
        except Exception as e:  # noqa: BLE001
            elapsed = time.perf_counter() - t0
            click.echo(f"  ERROR: {e}", err=True)
            all_results.append({
                "id": case["id"],
                "category": case["category"],
                "question": case["question"][:80],
                "total_score": 0,
                "all_constraints_pass": False,
                "elapsed_s": round(elapsed, 1),
                "error": str(e),
            })

    # Summary
    click.echo("\n" + "=" * 60)
    summary = aggregate_results(all_results)
    click.echo(f"SUMMARY: {summary['total_cases']} cases | avg score {summary['avg_score']}/6 ({summary['avg_score_pct']}%) | constraints pass {summary['constraint_pass_rate']}%")
    click.echo("\nÉchelle de scoring LLM (score total = pertinence + périmètre + format) :")
    click.echo("  Pertinence (0-3) — la réponse répond-elle exactement à la question posée ?")
    click.echo("                     3 réponse exacte  2 partielle  1 tangentielle  0 absente")
    click.echo("  Périmètre  (0-2) — le scope est-il correct, sans hallucination ni dérive ?")
    click.echo("                     2 correct  1 ambigu / dérive mineure  0 scope erroné ou hallucination")
    click.echo("  Format     (0-1) — blocs structurés (<data>, <choices>) utilisés si pertinents ?")
    click.echo("                     1 oui  0 prose uniquement")

    # CSV output
    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if all_results:
            flat_results = []
            for r in all_results:
                flat = {k: v for k, v in r.items() if k != "constraints"}
                if "constraints" in r:
                    for ck, cv in r["constraints"].items():
                        flat[f"constraint_{ck}"] = cv
                flat_results.append(flat)
            fieldnames = list(flat_results[0].keys())
            with open(out_path, "w", newline="", encoding="utf-8") as csvf:
                writer = csv.DictWriter(csvf, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(flat_results)
        click.echo(f"\nResults saved to {out_path}")


def _print_result(r: dict) -> None:
    score = r["total_score"]
    bar = "█" * score + "░" * (6 - score)
    intent_ok = "✓" if r.get("intent_correct") else "✗"
    constraints_ok = "✓" if r["all_constraints_pass"] else "✗"
    click.echo(f"  Score: {score}/6 [{bar}] | intent {intent_ok} ({r.get('intent_detected','?')}) | constraints {constraints_ok} | {r['elapsed_s']}s")
    if score == 0 and r.get("response_preview"):
        click.echo(f"  ↳ Response: {r['response_preview'][:160]}")


def _print_trace(trace: list[dict], constraints: dict[str, bool]) -> None:
    """Print the agent tool-call sequence and highlight failing constraints."""
    # Failing constraints summary
    failed = [name for name, ok in constraints.items() if not ok]
    click.echo(f"  ↳ FAILING CONSTRAINTS: {', '.join(failed)}")
    click.echo("  ↳ TRACE:")
    step = 0
    for msg in trace:
        if msg["type"] == "ai" and msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                step += 1
                args_str = ", ".join(f"{k}={v!r}" for k, v in tc.get("args", {}).items())
                click.echo(f"     {step}. [AI  →] {tc['name']}({args_str})")
        elif msg["type"] == "tool":
            content = str(msg.get("content", ""))
            preview = content[:300] + ("…" if len(content) > 300 else "")
            click.echo(f"        [TOOL ←] {msg.get('name', '?')}: {preview}")


if __name__ == "__main__":
    main()
