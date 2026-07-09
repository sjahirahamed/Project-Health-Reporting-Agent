"""
gemini_agent.py
===============
Gemini-powered Project Health Reporting Agent.

Responsibilities:
1. Receives project data + rule-based pre-score.
2. Calls Gemini to validate the RAG, produce plain-English reasoning,
   identify blockers, and generate recommendations.
3. Returns a structured report dict.
"""

import json
import re
from datetime import datetime
from typing import Optional

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL
from data_loader import project_to_text
from rag_engine import compute_rule_based_rag


# ── Configure Gemini ──────────────────────────────────────────────────────────
client = genai.Client(api_key=GEMINI_API_KEY)


# ── System instruction ────────────────────────────────────────────────────────
SYSTEM_INSTRUCTION = """\
You are a Senior Project Health Analyst at a global Professional Services firm.
Your role is to assess project plans and generate CLEAR, ACTIONABLE, executive-quality reports.

RULES:
- Be concise and direct. Avoid jargon.
- Provide a RAG status: RED, AMBER, or GREEN.
- If data is incomplete, state assumptions clearly and still provide a status.
- Reasoning must be specific — cite actual numbers and task names.
- Recommendations must be actionable, not generic.
- Always respond with valid JSON matching the schema provided.
"""

# ── Prompt template ───────────────────────────────────────────────────────────
REPORT_PROMPT = """\
You are analysing the following project health data.

=== PROJECT DATA ===
{project_text}

=== RULE-BASED PRE-SCORE ===
Overall (algorithmic): {algo_rag}
Dimensions:
{dimensions_text}

=== TASK ===
Based on all the above information, produce a comprehensive project health report.
Today's date: {today}

Return ONLY a valid JSON object (no markdown fences) with this exact schema:
{{
  "project_name": "...",
  "report_date": "YYYY-MM-DD",
  "rag_status": "Red|Amber|Green",
  "executive_summary": "2-3 sentence plain-English summary for a VP.",
  "reasoning": {{
    "schedule": "...",
    "completion_rate": "...",
    "milestone_health": "...",
    "blockers_risks": "...",
    "stakeholder_sentiment": "..."
  }},
  "key_metrics": {{
    "overall_completion_pct": 0.0,
    "tasks_at_risk": 0,
    "days_to_deadline": 0,
    "worst_slippage_days": 0
  }},
  "top_risks": ["risk1", "risk2", "risk3"],
  "recommendations": ["action1", "action2", "action3"],
  "data_quality_notes": "Any caveats about missing/incomplete data."
}}
"""


def _build_dimensions_text(dims: dict) -> str:
    lines = []
    for name, info in dims.items():
        lines.append(f"  {name}: {info['rag']} — {info['detail']}")
    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    """Try to parse JSON from model output, stripping any markdown fences."""
    text = text.strip()
    # Remove ```json ... ``` fences if present
    text = re.sub(r"^```[a-z]*\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def analyse_project(filepath: str, project_data: Optional[dict] = None) -> dict:
    """
    Main entry point. Loads project, runs rule-based scoring, calls Gemini,
    and returns a structured report.

    Parameters
    ----------
    filepath     : path to the Excel file
    project_data : pre-loaded project dict (optional, to avoid re-loading)

    Returns
    -------
    report dict (as returned by Gemini, plus meta fields)
    """
    from data_loader import load_project

    # 1. Load data
    if project_data is None:
        project_data = load_project(filepath)

    # 2. Rule-based pre-score
    pre_score = compute_rule_based_rag(project_data)

    # 3. Build text representations
    project_text    = project_to_text(project_data)
    dimensions_text = _build_dimensions_text(pre_score["dimensions"])
    today           = datetime.now().strftime("%d %B %Y")

    # 4. Build prompt
    prompt = REPORT_PROMPT.format(
        project_text    = project_text,
        algo_rag        = pre_score["overall_rag"],
        dimensions_text = dimensions_text,
        today           = today,
    )

    # 5. Call Gemini
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
        ),
    )
    raw_text = response.text

    # 6. Parse response
    try:
        report = _extract_json(raw_text)
    except (json.JSONDecodeError, ValueError):
        # Graceful degradation: return a partial report with raw text
        report = {
            "project_name":      project_data["project_name"],
            "report_date":       datetime.now().strftime("%Y-%m-%d"),
            "rag_status":        pre_score["overall_rag"],
            "executive_summary": "Gemini could not parse this response. See raw_response.",
            "reasoning":         {},
            "key_metrics":       {},
            "top_risks":         [],
            "recommendations":   [],
            "data_quality_notes": "JSON parse error from Gemini.",
            "raw_response":      raw_text,
        }

    # 7. Attach meta
    report["_meta"] = {
        "file":              project_data["file"],
        "algo_rag":          pre_score["overall_rag"],
        "algo_dimensions":   pre_score["dimensions"],
        "generated_at":      datetime.now().isoformat(),
    }

    return report


def format_console_report(report: dict) -> str:
    """
    Pretty-print the report for console output.
    """
    rag = report.get("rag_status", "?")
    rag_icons = {"Red": "[RED]", "Amber": "[AMBER]", "Green": "[GREEN]"}
    icon = rag_icons.get(rag, "")

    lines = [
        "=" * 70,
        f"{icon}  PROJECT HEALTH REPORT  {icon}",
        f"Project : {report.get('project_name', 'N/A')}",
        f"Date    : {report.get('report_date', 'N/A')}",
        f"RAG     : {rag}",
        "=" * 70,
        "",
        "EXECUTIVE SUMMARY",
        "-" * 40,
        report.get("executive_summary", ""),
        "",
        "DETAILED REASONING",
        "-" * 40,
    ]

    reasoning = report.get("reasoning", {})
    for key, val in reasoning.items():
        lines.append(f"  [{key.upper().replace('_', ' ')}] {val}")

    metrics = report.get("key_metrics", {})
    if metrics:
        lines += [
            "",
            "KEY METRICS",
            "-" * 40,
            f"  Overall Completion : {metrics.get('overall_completion_pct', 'N/A')}%",
            f"  Tasks At Risk      : {metrics.get('tasks_at_risk', 'N/A')}",
            f"  Days to Deadline   : {metrics.get('days_to_deadline', 'N/A')}",
            f"  Worst Slippage     : {metrics.get('worst_slippage_days', 'N/A')} days",
        ]

    risks = report.get("top_risks", [])
    if risks:
        lines += ["", "TOP RISKS", "-" * 40]
        for i, r in enumerate(risks, 1):
            lines.append(f"  {i}. {r}")

    recs = report.get("recommendations", [])
    if recs:
        lines += ["", "RECOMMENDATIONS", "-" * 40]
        for i, r in enumerate(recs, 1):
            lines.append(f"  {i}. {r}")

    dq = report.get("data_quality_notes", "")
    if dq:
        lines += ["", f"DATA NOTES: {dq}"]

    lines.append("=" * 70)
    return "\n".join(lines)
