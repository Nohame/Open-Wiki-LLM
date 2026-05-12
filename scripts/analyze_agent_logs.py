#!/usr/bin/env python3
"""
Analyze agent conversation logs to detect recursion errors and scope drift.

Usage:
  python scripts/analyze_agent_logs.py
  python scripts/analyze_agent_logs.py --days 7
  python scripts/analyze_agent_logs.py --from-date 2026-04-20
  python scripts/analyze_agent_logs.py --output rapport.csv
  python scripts/analyze_agent_logs.py --archives-dir chat_archives

  # LLM-as-judge scoring (requires GOOGLE_API_KEY)
  python scripts/analyze_agent_logs.py --from-date 2026-04-20 --llm-judge
  python scripts/analyze_agent_logs.py --from-date 2026-04-20 --llm-judge --output rapports/judge.csv

  # Candidate detection for golden dataset
  python scripts/analyze_agent_logs.py --from-date 2026-04-20 --export-candidates /tmp/candidates.yaml

  # Combined
  python scripts/analyze_agent_logs.py --from-date 2026-04-20 --llm-judge --export-candidates rapports/candidates.yaml
"""
import csv
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import click

logger = logging.getLogger(__name__)

# Thresholds for quantitative drift signals
_MCP_CALLS_THRESHOLD = 7       # above this → excessive_mcp_calls
_TOKENS_INPUT_THRESHOLD = 80_000  # above this → excessive_tokens

_JUDGE_MODEL = "gemini-3-flash-preview"

_POSTFACTO_JUDGE_PROMPT = """\
You are evaluating a catalog assistant's response against its behavioral specification.
Reply ONLY with a JSON object: {{"scope": <0-3>, "efficiency": <0-2>, "drift_reason": <str or null>}}

Scoring guide:
- scope (0-3): 3=in-domain, tools coherent with question, no hallucination; \
2=mostly correct, minor tool superfluity or slight drift; \
1=partial drift (wrong scope, missing critical tool, answered from memory); \
0=recursion error, unjustified refusal, or out-of-domain without signaling it
- efficiency (0-2): 2=minimal direct calls (≤3 MCP for a standard question); \
1=redundant or suboptimal call sequence but not blocking; \
0=>7 MCP calls or recursion error
- drift_reason: one short sentence in French explaining the issue, or null if scope>=2

Behavioral specification (system prompt):
{system_prompt}

User question:
{user_input}

Tools called (in order):
{tools_called}

Agent final response:
{agent_response}
"""


_CANDIDATE_SIMILARITY_THRESHOLD = 0.6
_CANDIDATE_MIN_OCCURRENCES = 2

_FR_STOPWORDS = frozenset({
    "les", "des", "est", "pas", "sur", "de", "la", "le", "un", "une",
    "que", "qui", "il", "en", "et", "à", "au", "du", "se", "je", "tu",
    "vous", "nous", "ils", "elles", "ce", "son", "sa", "ses", "leur",
    "leurs", "par", "pour", "dans", "avec", "sans", "ou", "ni", "mais",
    "donc", "or", "car", "plus", "moins", "très", "bien", "aussi",
    "quels", "quelles", "quel", "quelle", "comment", "combien", "sont",
})


def _tokenize_french(text: str) -> set[str]:
    """Tokenize a French question: lowercase, strip punctuation, remove stopwords."""
    tokens = re.findall(r"\b[a-zàâçéèêëïîôùûü]+\b", text.lower())
    return {t for t in tokens if t not in _FR_STOPWORDS}


def _jaccard_similarity(a: set, b: set) -> float:
    """Jaccard similarity between two token sets."""
    if not a and not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union > 0 else 0.0


def _subcluster_general(questions: list[str], llm: object) -> list[dict]:
    """Ask Flash to identify emerging intent clusters within 'general' questions.

    Returns list of {label, questions} dicts. Returns [] on LLM failure.
    """
    from langchain_core.messages import HumanMessage

    questions_block = "\n".join(f"- {q}" for q in questions)
    prompt = (
        "Tu analyses des questions posées à un assistant catalogue produit.\n"
        "Ces questions sont taguées 'general' (hors-scope ou intention non reconnue).\n"
        "Identifie des clusters thématiques récurrents parmi ces questions.\n"
        "Réponds UNIQUEMENT avec un JSON: "
        '[{"label": "nom_intention_snake_case", "questions": ["q1", "q2"]}, ...]\n'
        "Si aucun cluster évident (toutes différentes), réponds: []\n\n"
        f"Questions:\n{questions_block}"
    )
    try:
        content = llm.invoke([HumanMessage(content=prompt)]).content
        if isinstance(content, list):
            content = " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
        raw = content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("_subcluster_general failed: %s", exc)
        return []


def _detect_candidates(rows: list[dict], llm: object | None) -> list[dict]:
    """Group conversations by intent, deduplicate by Jaccard, return candidate list."""
    from collections import defaultdict

    by_intent: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        intent = row.get("intent")
        if not intent:
            continue
        by_intent[intent].append(row)

    # Sub-cluster the 'general' group if LLM available and >= 3 conversations
    general_clusters: list[dict] = []
    if llm is not None and len(by_intent.get("general", [])) >= 3:
        general_questions = [r["first_message"] for r in by_intent["general"]]
        clusters = _subcluster_general(general_questions, llm)
        for cluster in clusters:
            general_clusters.append({
                "category": cluster["label"],
                "question": cluster["questions"][0] if cluster["questions"] else "",
                "occurrences": len(cluster["questions"]),
                "last_seen": "",
                "is_new_intent": True,
            })

    candidates: list[dict] = []

    for intent, intent_rows in by_intent.items():
        if intent == "general":
            continue

        sorted_rows = sorted(intent_rows, key=lambda r: r.get("date", ""), reverse=True)

        representative_tokens: list[tuple[set, dict]] = []
        for row in sorted_rows:
            tokens = _tokenize_french(row["first_message"])
            merged = False
            for _rep_tokens, rep_row in representative_tokens:
                if _jaccard_similarity(tokens, _rep_tokens) >= _CANDIDATE_SIMILARITY_THRESHOLD:
                    rep_row["occurrences"] = rep_row.get("occurrences", 1) + 1
                    merged = True
                    break
            if not merged:
                representative_tokens.append((tokens, {
                    "category": intent,
                    "question": row["first_message"],
                    "occurrences": 1,
                    "last_seen": row.get("date", ""),
                    "is_new_intent": False,
                }))

        for _, candidate in representative_tokens:
            if candidate["occurrences"] >= _CANDIDATE_MIN_OCCURRENCES:
                candidates.append(candidate)

    candidates.extend(general_clusters)
    return candidates


def _make_slug(question: str) -> str:
    """Generate a YAML-safe slug from a question (4 tokens max, 30 chars max)."""
    tokens = sorted(_tokenize_french(question))[:4]
    slug = "_".join(tokens)
    return slug[:30]


def _generate_quality_criteria(question: str, intent: str, llm: object) -> list[str]:
    """Call Flash to generate 2-3 quality criteria bullets for a candidate case."""
    from langchain_core.messages import HumanMessage

    prompt = (
        f"Tu génères des critères de qualité pour évaluer la réponse d'un agent catalogue.\n"
        f"Intention détectée : {intent}\n"
        f"Question utilisateur : {question}\n\n"
        "Génère 2 à 3 critères de qualité en français, sous forme de liste de strings JSON.\n"
        'Exemple : ["L\'agent cite au moins un article avec son SKU", '
        '"L\'agent mentionne la date de la donnée source"]\n'
        "Réponds UNIQUEMENT avec le tableau JSON."
    )
    try:
        content = llm.invoke([HumanMessage(content=prompt)]).content
        if isinstance(content, list):
            content = " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
        raw = content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        criteria = json.loads(raw)
        if isinstance(criteria, list):
            return [str(c) for c in criteria[:3]]
    except Exception as exc:  # noqa: BLE001
        logger.warning("_generate_quality_criteria failed: %s", exc)
    return ["(à compléter manuellement)"]


def _export_candidates_yaml(candidates: list[dict], output_path: Path) -> None:
    """Write candidate entries to a YAML file with inline comments."""
    lines = ["# Candidats golden dataset — générés par analyze_agent_logs.py\n"]
    for c in candidates:
        intent = c["category"]
        slug = _make_slug(c["question"])
        entry_id = f"{intent}_{slug}_01"
        is_new = c.get("is_new_intent", False)
        new_comment = "  # intention non reconnue par HarnessLayer — à valider\n" if is_new else "\n"

        criteria_lines = "\n".join(
            f"    - {cr}" for cr in c.get("quality_criteria", ["(à compléter manuellement)"])
        )

        lines.append(
            f"- id: {entry_id}\n"
            f"  category: {intent}\n"
            f"  question: {json.dumps(c['question'], ensure_ascii=False)}\n"
            f"  expected_intent: {intent}{new_comment}"
            f"  expected_tools: []        # à compléter manuellement\n"
            f"  must_not_call: []         # à compléter manuellement\n"
            f"  constraints:\n"
            f"    max_llm_calls: ~        # à compléter manuellement\n"
            f"    max_mcp_calls: ~        # à compléter manuellement\n"
            f"  quality_criteria:\n"
            f"{criteria_lines}\n"
            f"  occurrences: {c['occurrences']}        "
            f"# méta-champ — à supprimer avant merge dans golden_dataset.yaml\n"
            f"  last_seen: {c.get('last_seen', '')}     "
            f"# méta-champ — à supprimer avant merge dans golden_dataset.yaml\n"
        )

    output_path.write_text("\n".join(lines), encoding="utf-8")


def _parse_verbose(path: Path) -> dict | None:
    """Parse a verbose JSON archive. Returns None if unreadable."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if "turns" not in data:
        return None
    return data


def _detect_recursion_error(turns: list[dict]) -> bool:
    """Return True if any turn's trace contains a recursion limit message."""
    for turn in turns:
        for msg in turn.get("trace", []):
            content = msg.get("content", "")
            if isinstance(content, str) and "Recursion limit" in content:
                return True
    return False


def _detect_scope_issues(
    first_message: str,
    tools_called: list[str],
    nb_mcp: int,
    total_tokens_input: int,
) -> list[str]:
    """
    Return a list of issue codes detected. Empty list = no anomaly.

    Codes
    -----
    vendability_no_tool
        Question mentions "vendab*" (vendabilité, vendable…) but agent did not
        call analyze_vendability. Applies to any scope, not just Legallais.
    excessive_mcp_calls
        nb_mcp_calls > _MCP_CALLS_THRESHOLD. Scope-agnostic: a well-formed
        strategy should rarely exceed this regardless of question type.
    excessive_tokens
        total_tokens_input > _TOKENS_INPUT_THRESHOLD. High token consumption
        indicates a long chain of sequential calls building redundant context.
    sku_lookup_missing
        A 6+-digit numeric SKU appears in the question but neither lookup_article
        nor lookup_article_batch was called. Agent may have answered without
        resolving the article chain.

    All codes are heuristics — use as signals, not verdicts.
    """
    issues: list[str] = []
    msg = first_message.lower()

    # Vendability question without the dedicated cross-domain tool
    if "vendab" in msg and "analyze_vendability" not in tools_called:
        issues.append("vendability_no_tool")

    # Too many MCP calls — agnostic signal
    if nb_mcp > _MCP_CALLS_THRESHOLD:
        issues.append("excessive_mcp_calls")

    # Excessive token consumption — cost / drift signal
    if total_tokens_input > _TOKENS_INPUT_THRESHOLD:
        issues.append("excessive_tokens")

    # SKU-like code in question but no lookup tool called
    if (
        re.search(r"\b\d{6,}\b", first_message)
        and "lookup_article" not in tools_called
        and "lookup_article_batch" not in tools_called
    ):
        issues.append("sku_lookup_missing")

    return issues


def _turn_metrics(turn: dict) -> dict:
    """Extract performance metrics for a single turn."""
    perf = turn.get("performance", {})
    mcp_calls = perf.get("mcp_calls", [])
    llm_calls = perf.get("llm_calls", [])
    return {
        "nb_llm": len(llm_calls),
        "nb_mcp": len(mcp_calls),
        "total_tokens_input": (perf.get("total_tokens") or {}).get("input", 0),
        "total_ms": perf.get("total_ms", 0),
        "tools_called": [c.get("tool", "") for c in mcp_calls],
    }


def _aggregate_turns(turns: list[dict]) -> dict:
    """Aggregate performance metrics across all turns of a conversation."""
    nb_llm = 0
    nb_mcp = 0
    total_tokens_input = 0
    total_ms = 0
    tools_called: list[str] = []

    for turn in turns:
        perf = turn.get("performance", {})
        nb_llm += len(perf.get("llm_calls", []))
        mcp_calls = perf.get("mcp_calls", [])
        nb_mcp += len(mcp_calls)
        tools_called.extend(c.get("tool", "") for c in mcp_calls)
        total_tokens_input += (perf.get("total_tokens") or {}).get("input", 0)
        total_ms += perf.get("total_ms", 0)

    return {
        "nb_llm": nb_llm,
        "nb_mcp": nb_mcp,
        "total_tokens_input": total_tokens_input,
        "total_ms": total_ms,
        "tools_called": tools_called,
    }


def _load_feedback_map(archives_dir: Path) -> dict[str, str]:
    """Map each verbose archive path → last assistant feedback value.

    Standard archive is derived by stripping '_verbose' from the verbose path.
    Returns only entries where feedback is non-null.
    """
    fb_map: dict[str, str | None] = {}
    for verbose_path in archives_dir.rglob("*_verbose.json"):
        standard_path = verbose_path.with_name(
            verbose_path.name.replace("_verbose.json", ".json")
        )
        if not standard_path.exists():
            continue
        try:
            data = json.loads(standard_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        # Find last assistant message with non-null feedback
        feedback = None
        for msg in reversed(data.get("messages", [])):
            if msg.get("role") == "assistant" and msg.get("feedback") is not None:
                feedback = msg["feedback"]
                break
        if feedback is not None:
            fb_map[str(verbose_path)] = feedback
    return fb_map


def _compute_cutoff(
    days: int | None,
    from_date: str | None,
) -> datetime | None:
    """Return a UTC-aware cutoff datetime. from_date takes priority over days."""
    if from_date is not None:
        try:
            d = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise click.BadParameter(
                f"Format attendu : YYYY-MM-DD, reçu : {from_date!r}",
                param_hint="--from-date",
            )
        return d
    if days is not None:
        return datetime.now(timezone.utc) - timedelta(days=days)
    return None


def _extract_agent_response(turns: list[dict]) -> str:
    """Extract the last AIMessage text from the trace of the last turn."""
    for turn in reversed(turns):
        for msg in reversed(turn.get("trace", [])):
            if msg.get("type") != "AIMessage":
                continue
            content = msg.get("content", "")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return "".join(
                    item.get("text", "") for item in content if isinstance(item, dict)
                )
    return ""


def _parse_judge_score_postfacto(raw: str) -> dict:
    """Parse Flash judge JSON for post-facto scoring. Returns zeros on failure.

    Expected format: {"scope": 0-3, "efficiency": 0-2, "drift_reason": str|null}
    """
    try:
        stripped = raw.strip()
        if stripped.startswith("```"):
            stripped = stripped.split("```")[1]
            if stripped.startswith("json"):
                stripped = stripped[4:]
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            match = re.search(r'\{[^{}]+\}', stripped, re.DOTALL)
            if not match:
                raise ValueError("No JSON object found")
            data = json.loads(match.group())
        return {
            "scope": max(0, min(3, int(data.get("scope", 0)))),
            "efficiency": max(0, min(2, int(data.get("efficiency", 0)))),
            "drift_reason": data.get("drift_reason") or None,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("_parse_judge_score_postfacto failed (%s) — raw: %r", exc, raw[:300])
        return {"scope": 0, "efficiency": 0, "drift_reason": None}


def _judge_conversation(
    data: dict,
    tools_called: list[str],
    feedback: str | None,
    llm: object,
) -> dict:
    """Call Flash judge on one conversation. Returns score dict."""
    from langchain_core.messages import HumanMessage

    turns = data.get("turns", [])
    user_input = turns[0].get("user_input", "") if turns else ""
    agent_response = _extract_agent_response(turns)
    system_prompt = data.get("system_prompt", "(non disponible)")

    prompt = _POSTFACTO_JUDGE_PROMPT.format(
        system_prompt=system_prompt[:2000],
        user_input=user_input,
        tools_called=", ".join(tools_called) if tools_called else "(aucun)",
        agent_response=agent_response[:3000],
    )
    try:
        content = llm.invoke([HumanMessage(content=prompt)]).content
        if isinstance(content, list):
            content = " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
        raw = content
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM judge call failed: %s", exc)
        return {"scope_score": 0, "efficiency_score": 0, "drift_reason_llm": None, "human_override": False}

    scores = _parse_judge_score_postfacto(raw)
    human_override = (feedback == "negative") and (scores["scope"] >= 2)

    return {
        "scope_score": scores["scope"],
        "efficiency_score": scores["efficiency"],
        "drift_reason_llm": scores["drift_reason"],
        "human_override": human_override,
    }


def analyze_archives(
    archives_dir: Path,
    days: int | None = None,
    cutoff: datetime | None = None,
    llm_judge: bool = False,
    llm: object | None = None,
    feedback_map: dict | None = None,
) -> list[dict]:
    """Scan verbose JSON files and return a list of conversation summaries."""
    if cutoff is None and days is not None:
        cutoff = _compute_cutoff(days=days, from_date=None)
    feedback_map = feedback_map or {}

    results = []
    for verbose_path in sorted(archives_dir.rglob("*_verbose.json"), reverse=True):
        data = _parse_verbose(verbose_path)
        if data is None:
            continue

        started_at_str = data.get("started_at", "")
        if cutoff and started_at_str:
            try:
                dt = datetime.fromisoformat(started_at_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt < cutoff:
                    continue
            except ValueError:
                pass

        turns = data.get("turns", [])
        session_id = data.get("session_id", verbose_path.stem)[:8]

        # --- Per-turn rows ---
        turn_rows: list[dict] = []
        for i, turn in enumerate(turns):
            user_input = turn.get("user_input", "")
            intent = turn.get("intent")
            metrics = _turn_metrics(turn)
            recursion_error = _detect_recursion_error([turn])
            scope_issues = _detect_scope_issues(
                user_input, metrics["tools_called"], metrics["nb_mcp"], metrics["total_tokens_input"]
            )

            row: dict = {
                "session_id": session_id,
                "turn_number": i + 1,
                "is_rollup": False,
                "date": started_at_str[:10] if started_at_str else "",
                "first_message": (user_input[:57] + "...") if len(user_input) > 60 else user_input,
                "nb_llm_calls": metrics["nb_llm"],
                "nb_mcp_calls": metrics["nb_mcp"],
                "total_tokens_input": metrics["total_tokens_input"],
                "total_ms": metrics["total_ms"],
                "recursion_error": recursion_error,
                "scope_drift_flag": bool(scope_issues),
                "scope_drift_reasons": ",".join(scope_issues),
                "tools_called": metrics["tools_called"],
                "scope_score": None,
                "efficiency_score": None,
                "drift_reason_llm": None,
                "human_override": False,
                "intent": intent,
            }

            if llm_judge and llm is not None:
                turn_data = {"turns": [turn], "system_prompt": data.get("system_prompt", "")}
                turn_feedback = feedback_map.get(str(verbose_path)) if i == len(turns) - 1 else None
                judge_result = _judge_conversation(turn_data, metrics["tools_called"], turn_feedback, llm)
                row.update(judge_result)

            turn_rows.append(row)

        # --- Rollup row (arithmetic aggregation, no LLM call) ---
        agg = _aggregate_turns(turns)
        all_drift_codes = [
            code
            for r in turn_rows
            for code in r["scope_drift_reasons"].split(",")
            if code
        ]
        n_drift_turns = sum(1 for r in turn_rows if r["scope_drift_flag"])
        scope_scores = [r["scope_score"] for r in turn_rows if r["scope_score"] is not None]
        effic_scores = [r["efficiency_score"] for r in turn_rows if r["efficiency_score"] is not None]

        rollup: dict = {
            "session_id": session_id,
            "turn_number": 0,
            "is_rollup": True,
            "date": started_at_str[:10] if started_at_str else "",
            "first_message": f"TOTAL ({len(turns)} turn(s))",
            "nb_llm_calls": agg["nb_llm"],
            "nb_mcp_calls": agg["nb_mcp"],
            "total_tokens_input": agg["total_tokens_input"],
            "total_ms": agg["total_ms"],
            "recursion_error": any(r["recursion_error"] for r in turn_rows),
            "scope_drift_flag": any(r["scope_drift_flag"] for r in turn_rows),
            "scope_drift_reasons": ",".join(sorted(set(all_drift_codes))),
            "tools_called": agg["tools_called"],
            "scope_score": min(scope_scores) if scope_scores else None,
            "efficiency_score": min(effic_scores) if effic_scores else None,
            "drift_reason_llm": None,
            "human_override": any(r.get("human_override", False) for r in turn_rows),
            "intent": turn_rows[0]["intent"] if turn_rows else None,
            "n_drift_turns": n_drift_turns,
            "n_turns": len(turns),
        }

        results.extend(turn_rows)
        results.append(rollup)

    return results


def _print_frequency_table(candidates: list[dict]) -> None:
    """Print candidate frequency table before YAML generation."""
    if not candidates:
        click.echo("Aucun candidat détecté (seuil occurrences non atteint).")
        return
    click.echo("\nCandidats détectés :")
    header = f"{'INTENT':<20} {'OCCURRENCES':>12}  QUESTION"
    click.echo(header)
    click.echo("-" * 80)
    for c in sorted(candidates, key=lambda x: x["occurrences"], reverse=True):
        label = c["category"]
        if c.get("is_new_intent"):
            label = click.style(f"{label} [nouveau]", fg="cyan")
        click.echo(f"{label:<20} {c['occurrences']:>12}  {c['question'][:50]}")


_DRIFT_COL_WIDTH = 46  # wide enough for [excessive_mcp_calls,excessive_tokens]
_DRIFT_LLM_COL_WIDTH = 45


def _print_table(rows: list[dict]) -> None:
    """Print aligned console table grouped by session, with rollup lines."""
    if not rows:
        click.echo("Aucune archive verbose trouvée.")
        return

    has_judge = any(r.get("scope_score") is not None for r in rows if not r.get("is_rollup"))

    header = (
        f"{'SESSION':<10} {'TURN':>4} {'DATE':<10} {'QUESTION (60c)':<62} "
        f"{'LLM':>4} {'MCP':>4} {'TOKENS-IN':>10} {'RÉCURS':>7} "
        f"{'DÉRIVE':<{_DRIFT_COL_WIDTH}}"
    )
    if has_judge:
        header += f"{'SCOPE':>5} {'EFFIC':>5}  {'DRIFT-LLM':<{_DRIFT_LLM_COL_WIDTH}}"
    click.echo(header)
    click.echo("-" * len(header))

    for r in rows:
        is_rollup = r.get("is_rollup", False)

        if r["recursion_error"]:
            recurs_str = click.style("✓ ⚠", fg="red") + "   "
        else:
            recurs_str = "✗      "

        if r["scope_drift_flag"]:
            codes = f"[{r['scope_drift_reasons']}]"
            visible_len = 3 + 2 + len(codes)
            padding = " " * max(0, _DRIFT_COL_WIDTH - visible_len)
            drift_str = click.style("✓ ⚠", fg="yellow") + f"  {codes}" + padding
        else:
            drift_str = "✗" + " " * (_DRIFT_COL_WIDTH - 1)

        if is_rollup:
            n_turns = r.get("n_turns", "?")
            n_drift = r.get("n_drift_turns", 0)
            drift_summary = f" {n_drift}/{n_turns} turn(s) en dérive" if n_drift else ""
            turn_col = click.style("  ╰─", fg="bright_black")
            question_col = click.style(
                (f"TOTAL{drift_summary}"[:62]).ljust(62), fg="bright_black"
            )
        else:
            turn_col = f"{r['turn_number']:>4}"
            msg = r["first_message"]
            question_col = f"{msg:<62}"

        line = (
            f"{r['session_id']:<10} "
            f"{turn_col} "
            f"{r['date']:<10} "
            f"{question_col} "
            f"{r['nb_llm_calls']:>4} "
            f"{r['nb_mcp_calls']:>4} "
            f"{r['total_tokens_input']:>10} "
            f"{recurs_str}"
            f"{drift_str}"
        )
        if has_judge:
            scope = r.get("scope_score")
            effic = r.get("efficiency_score")
            scope_str = str(scope) if scope is not None else "-"
            effic_str = str(effic) if effic is not None else "-"
            drift_llm = (r.get("drift_reason_llm") or "")[:_DRIFT_LLM_COL_WIDTH]
            if is_rollup:
                drift_llm = ""
            line += f"{scope_str:>5} {effic_str:>5}  {drift_llm:<{_DRIFT_LLM_COL_WIDTH}}"
        click.echo(line)

    click.echo()
    # Summary counts — only from non-rollup rows
    turn_rows = [r for r in rows if not r.get("is_rollup")]
    n_recursion = sum(1 for r in turn_rows if r["recursion_error"])
    n_drift = sum(1 for r in turn_rows if r["scope_drift_flag"])
    if n_recursion:
        click.echo(click.style(f"⚠  {n_recursion} turn(s) avec erreur de récursion", fg="red"))
    if n_drift:
        from collections import Counter
        all_reasons: list[str] = []
        for r in turn_rows:
            if r["scope_drift_reasons"]:
                all_reasons.extend(r["scope_drift_reasons"].split(","))
        counts = Counter(all_reasons)
        click.echo(click.style(
            f"⚠  {n_drift} turn(s) avec dérive détectée — codes : "
            + ", ".join(f"{code}×{n}" for code, n in counts.most_common()),
            fg="yellow",
        ))
    if not n_recursion and not n_drift:
        click.echo(click.style("✓  Aucune anomalie détectée", fg="green"))

    if has_judge:
        click.echo("\nÉchelle de scoring LLM :")
        click.echo("  SCOPE  Scope (0-3) — cohérence périmètre et outils : la réponse couvre-t-elle exactement ce qui était demandé ?")
        click.echo("         3 dans le périmètre, outils cohérents, aucune hallucination")
        click.echo("         2 écart mineur (outil superflu, légère dérive)")
        click.echo("         1 dérive partielle (outil manquant, réponse de mémoire)")
        click.echo("         0 récursion, refus injustifié, ou hors domaine")
        click.echo("  EFFIC  Efficiency (0-2) — stratégie d'appels MCP : l'agent a-t-il atteint sa réponse avec le minimum d'appels nécessaires ?")
        click.echo("         2 ≤ 3 appels MCP, séquence directe")
        click.echo("         1 appels redondants ou séquence sous-optimale")
        click.echo("         0 > 7 appels MCP ou erreur de récursion")


def _init_flash_llm() -> object:
    """Instantiate Flash LLM. Raises ClickException if GOOGLE_API_KEY missing."""
    import os
    if not os.environ.get("GOOGLE_API_KEY"):
        raise click.ClickException(
            "GOOGLE_API_KEY manquante — requis pour --llm-judge et --export-candidates"
        )
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(model=_JUDGE_MODEL, temperature=0)


@click.command()
@click.option("--days", default=None, type=int, help="Analyser les N derniers jours")
@click.option(
    "--from-date",
    default=None,
    metavar="YYYY-MM-DD",
    help="Analyser les conversations depuis cette date (priorité sur --days)",
)
@click.option("--output", default=None, type=click.Path(), help="Export CSV du rapport")
@click.option(
    "--archives-dir",
    default="chat_archives",
    show_default=True,
    type=click.Path(exists=True, file_okay=False),
    help="Répertoire des archives de conversations",
)
@click.option("--llm-judge", is_flag=True, default=False, help="Score chaque conversation via Flash LLM (nécessite GOOGLE_API_KEY)")
@click.option("--export-candidates", default=None, type=click.Path(), metavar="PATH", help="Exporter les candidats golden dataset en YAML (nécessite GOOGLE_API_KEY si LLM actif)")
def main(days: int | None, from_date: str | None, output: str | None, archives_dir: str, llm_judge: bool, export_candidates: str | None) -> None:
    """Analyse les logs verbose des conversations agentiques.

    Détecte les erreurs de récursion et les dérives de scope (heuristiques) :

    \b
    vendability_no_tool   question vendab* sans appel à analyze_vendability
    excessive_mcp_calls   nb_mcp_calls > 7 (agnostique au contenu)
    excessive_tokens      total_tokens_input > 80 000 (agnostique au contenu)
    sku_lookup_missing    SKU numérique dans la question sans lookup_article_batch
    """
    archives_path = Path(archives_dir)
    cutoff = _compute_cutoff(days=days, from_date=from_date)

    needs_llm = llm_judge or export_candidates is not None
    llm = None
    feedback_map: dict = {}
    if needs_llm:
        import os
        if os.environ.get("GOOGLE_API_KEY"):
            llm = _init_flash_llm()
        elif llm_judge:
            raise click.ClickException(
                "GOOGLE_API_KEY manquante — requis pour --llm-judge"
            )
        if llm_judge and llm is not None:
            n_archives = len(list(archives_path.rglob("*_verbose.json")))
            click.echo(f"⚠  --llm-judge activé : {n_archives} archive(s) à scorer (coût API Flash)")
            feedback_map = _load_feedback_map(archives_path)

    rows = analyze_archives(archives_path, cutoff=cutoff, llm_judge=llm_judge, llm=llm, feedback_map=feedback_map)
    _print_table(rows)

    if export_candidates is not None:
        candidates = _detect_candidates([r for r in rows if not r.get("is_rollup")], llm=llm)
        _print_frequency_table(candidates)
        if candidates:
            if llm is not None:
                for c in candidates:
                    if "quality_criteria" not in c:
                        c["quality_criteria"] = _generate_quality_criteria(
                            c["question"], c["category"], llm
                        )
            out_path = Path(export_candidates)
            _export_candidates_yaml(candidates, out_path)
            click.echo(f"\nCandidats exportés : {out_path} ({len(candidates)} entrée(s))")

    if output:
        out_path = Path(output)
        fieldnames = [
            "session_id", "turn_number", "is_rollup", "date", "first_message",
            "nb_llm_calls", "nb_mcp_calls", "total_tokens_input", "total_ms",
            "recursion_error", "scope_drift_flag", "scope_drift_reasons",
        ]
        if llm_judge:
            fieldnames += ["scope_score", "efficiency_score", "drift_reason_llm", "human_override"]
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        click.echo(f"\nRapport exporté : {out_path}")


if __name__ == "__main__":
    main()
