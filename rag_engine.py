"""
rag_engine.py
=============
Deterministic (rule-based) pre-scoring of a project before passing to Gemini.
Gemini then receives this pre-score as context so it can validate/override.
"""

from datetime import datetime
from typing import Optional
import pandas as pd

from config import RAG_THRESHOLDS as THR


# ── Colour constants ───────────────────────────────────────────────────────────
RED   = "Red"
AMBER = "Amber"
GREEN = "Green"


def _score_schedule_slippage(df: pd.DataFrame) -> tuple[str, str]:
    """Worst slippage among In-Progress / Not-Started tasks."""
    if "variance" not in df.columns:
        return GREEN, "No variance data available."
    active = df[df.get("status", pd.Series()).fillna("").str.lower().isin(
        ["in progress", "not started", ""]
    )]
    var = active["variance"].dropna()
    if var.empty:
        return GREEN, "No active tasks with variance data."
    max_slip = var.max()
    if max_slip >= THR["schedule_slip_red"]:
        return RED, f"Worst task slippage is {max_slip:.0f} days."
    if max_slip >= THR["schedule_slip_amber"]:
        return AMBER, f"Worst task slippage is {max_slip:.0f} days."
    return GREEN, f"Max slippage is {max_slip:.0f} days — within tolerance."


def _score_completion(project: dict) -> tuple[str, str]:
    """Compare actual % done vs expected % done (time elapsed)."""
    s = project["summary"]
    total = s["not_started"] + s["in_progress"] + s["completed"] + s["on_hold"]
    if total == 0:
        return AMBER, "No task data available."

    actual_pct = s["completed"] / total
    start = project["start_date"]
    end   = project["end_date"]
    today = datetime.now()

    if start is None or end is None:
        return AMBER, "Project dates missing — cannot compute expected progress."

    if isinstance(start, datetime):
        pass
    else:
        try:
            start = datetime.combine(start, datetime.min.time())
        except Exception:
            return AMBER, "Invalid start date."

    if isinstance(end, datetime):
        pass
    else:
        try:
            end = datetime.combine(end, datetime.min.time())
        except Exception:
            return AMBER, "Invalid end date."

    total_days   = (end - start).days
    elapsed_days = (today - start).days
    if total_days <= 0:
        return AMBER, "Zero or negative project duration."

    expected_pct = min(elapsed_days / total_days, 1.0)
    gap = expected_pct - actual_pct

    detail = (
        f"Expected {expected_pct*100:.1f}% complete by today; "
        f"actual {actual_pct*100:.1f}%. Gap = {gap*100:.1f}%."
    )
    if gap >= THR["completion_gap_red"]:
        return RED, detail
    if gap >= THR["completion_gap_amber"]:
        return AMBER, detail
    return GREEN, detail


def _score_rag_distribution(df: pd.DataFrame) -> tuple[str, str]:
    """How many tasks are already flagged Red inside the plan."""
    rag_col = None
    for c in ["rag", "schedule_health"]:
        if c in df.columns:
            rag_col = c
            break
    if rag_col is None:
        return GREEN, "No RAG column found in plan."

    total = df[rag_col].dropna().shape[0]
    if total == 0:
        return GREEN, "RAG column empty."

    red_count   = (df[rag_col].dropna().str.lower() == "red").sum()
    amber_count = (df[rag_col].dropna().str.lower().isin(["amber", "yellow"])).sum()
    red_ratio   = red_count / total
    amber_ratio = amber_count / total

    if red_ratio >= THR["red_task_ratio_red"]:
        return RED, f"{red_count}/{total} tasks ({red_ratio*100:.1f}%) are Red."
    if red_ratio >= THR["red_task_ratio_amber"] or amber_ratio >= 0.30:
        return AMBER, (
            f"{red_count} Red + {amber_count} Amber out of {total} tasks."
        )
    return GREEN, f"Only {red_count} Red tasks out of {total}."


def _score_on_hold(project: dict) -> tuple[str, str]:
    s = project["summary"]
    total = s["not_started"] + s["in_progress"] + s["completed"] + s["on_hold"]
    if total == 0:
        return GREEN, "No task data."
    ratio = s["on_hold"] / total
    if ratio >= THR["on_hold_ratio_red"]:
        return RED, f"{s['on_hold']} tasks On Hold ({ratio*100:.1f}% of total)."
    if ratio >= THR["on_hold_ratio_amber"]:
        return AMBER, f"{s['on_hold']} tasks On Hold."
    return GREEN, f"{s['on_hold']} tasks On Hold — acceptable."


def _score_milestones(df: pd.DataFrame) -> tuple[str, str]:
    """Check if any milestone end dates are overdue."""
    if "phase" not in df.columns or "end_date" not in df.columns:
        return GREEN, "No milestone data."
    today = datetime.now()
    milestones = df[df["phase"].notna()].copy()
    milestones["end_date"] = pd.to_datetime(milestones["end_date"], errors="coerce")

    worst_overdue = 0
    worst_name    = ""
    for _, row in milestones.iterrows():
        end = row.get("end_date")
        status = str(row.get("status", "")).lower()
        if pd.isna(end) or status == "completed":
            continue
        overdue = (today - end).days
        if overdue > worst_overdue:
            worst_overdue = overdue
            worst_name = str(row.get("phase", ""))[:50]

    if worst_overdue >= THR["milestone_overdue_days_red"]:
        return RED, f'Milestone "{worst_name}" is {worst_overdue}d overdue.'
    if worst_overdue >= THR["milestone_overdue_days_amber"]:
        return AMBER, f'Milestone "{worst_name}" is {worst_overdue}d overdue.'
    if worst_overdue > 0:
        return AMBER, f"Some milestones are slightly overdue ({worst_overdue}d)."
    return GREEN, "All tracked milestones are on schedule."


# ── Colour hierarchy ──────────────────────────────────────────────────────────
_PRIORITY = {RED: 2, AMBER: 1, GREEN: 0}


def compute_rule_based_rag(project: dict) -> dict:
    """
    Run all rule-based scoring dimensions and return a pre-score dict.

    Returns
    -------
    {
        "overall_rag": "Red"|"Amber"|"Green",
        "dimensions": {
            "schedule_slippage": {"rag": ..., "detail": ...},
            "completion_rate":   {...},
            "rag_distribution":  {...},
            "on_hold_tasks":     {...},
            "milestone_health":  {...},
        }
    }
    """
    df = project["tasks"]

    dims = {}
    dims["schedule_slippage"] = dict(zip(
        ["rag", "detail"], _score_schedule_slippage(df)
    ))
    dims["completion_rate"] = dict(zip(
        ["rag", "detail"], _score_completion(project)
    ))
    dims["rag_distribution"] = dict(zip(
        ["rag", "detail"], _score_rag_distribution(df)
    ))
    dims["on_hold_tasks"] = dict(zip(
        ["rag", "detail"], _score_on_hold(project)
    ))
    dims["milestone_health"] = dict(zip(
        ["rag", "detail"], _score_milestones(df)
    ))

    # Overall = worst dimension
    overall = max(dims.values(), key=lambda d: _PRIORITY[d["rag"]])["rag"]

    return {"overall_rag": overall, "dimensions": dims}
