"""
data_loader.py
==============
Reads and normalises project plan Excel files (Zycus format).
Returns a structured dict ready for the RAG engine and Gemini prompt.
"""

import re
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Optional


# ── Column-name normalisation map ─────────────────────────────────────────────
_COL_ALIASES = {
    "task name":         "task_name",
    "name":              "task_name",
    "status":            "status",
    "% complete":        "pct_complete",
    "% completed":       "pct_complete",
    "start date":        "start_date",
    "start":             "start_date",
    "end date":          "end_date",
    "finish":            "end_date",
    "baseline start":    "baseline_start",
    "baseline finish":   "baseline_finish",
    "variance":          "variance",
    "rag":               "rag",
    "schedule health":   "schedule_health",
    "at risk?":          "at_risk",
    "on hold?":          "on_hold",
    "duration":          "duration",
    "level":             "level",
    "phase/milestone":   "phase",
    "project manager":   "project_manager",
    "status comment":    "status_comment",
    "comments":          "comments",
    "critical ?":        "critical",
    "total float":       "total_float",
    "owner":             "owner",
}


def _normalise_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Lower-case and map column names to canonical names.
    
    If renaming creates duplicate column names (e.g., two 'Start' columns),
    we keep only the first occurrence of each canonical name.
    """
    mapping = {}
    for col in df.columns:
        key = col.strip().lower()
        if key in _COL_ALIASES:
            mapping[col] = _COL_ALIASES[key]
    df = df.rename(columns=mapping)
    # Drop duplicate columns (keep first occurrence)
    df = df.loc[:, ~df.columns.duplicated(keep='first')]
    return df


def _parse_variance(val) -> Optional[float]:
    """Convert variance strings like '-8d', '6d', '0' to float (days)."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    s = str(val).strip().replace("d", "").replace("+", "")
    try:
        return float(s)
    except ValueError:
        return None


def _parse_pct(val) -> Optional[float]:
    """Ensure percentage is in [0,1] range."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        v = float(val)
        return v if v <= 1.0 else v / 100.0
    except (ValueError, TypeError):
        return None


def load_project(filepath: str | Path) -> dict:
    """
    Load a Zycus project plan Excel file and return a normalised dict.

    Returns
    -------
    {
        "project_name":    str,
        "project_manager": str,
        "start_date":      datetime,
        "end_date":        datetime,
        "summary":         {not_started, in_progress, completed, on_hold},
        "tasks":           pd.DataFrame  (normalised),
        "comments":        list[str],
        "file":            str,
    }
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Project file not found: {filepath}")

    xl = pd.ExcelFile(filepath, engine="openpyxl")
    sheets = xl.sheet_names

    # ── Summary sheet ─────────────────────────────────────────────────────────
    summary_raw = {}
    if "Summary" in sheets:
        df_sum = pd.read_excel(filepath, sheet_name="Summary",
                               header=None, engine="openpyxl")
        for _, row in df_sum.iterrows():
            if pd.notna(row.iloc[0]) and pd.notna(row.iloc[1]):
                summary_raw[str(row.iloc[0]).strip()] = row.iloc[1]

    summary = {
        "not_started":  int(summary_raw.get("Not Started",  0) or 0),
        "in_progress":  int(summary_raw.get("In Progress",  0) or 0),
        "completed":    int(summary_raw.get("Completed",    0) or 0),
        "on_hold":      int(summary_raw.get("On Hold",      0) or 0),
    }

    project_manager = str(summary_raw.get("Project Manager", "Unknown"))
    start_date      = summary_raw.get("Project Start Date")
    end_date        = summary_raw.get("Project End Date")

    # ── Comments sheet ────────────────────────────────────────────────────────
    comments_list: list[str] = []
    if "Comments" in sheets:
        df_com = pd.read_excel(filepath, sheet_name="Comments",
                               engine="openpyxl")
        for _, row in df_com.iterrows():
            parts = [str(v).strip() for v in row if pd.notna(v) and str(v).strip()]
            if parts:
                comments_list.append(" | ".join(parts))

    # ── Main task sheet (first sheet) ─────────────────────────────────────────
    main_sheet = sheets[0]
    df = pd.read_excel(filepath, sheet_name=main_sheet, engine="openpyxl")
    df = _normalise_cols(df)

    # Parse key columns
    if "pct_complete" in df.columns:
        df["pct_complete"] = df["pct_complete"].apply(_parse_pct)
    if "variance" in df.columns:
        df["variance"] = df["variance"].apply(_parse_variance)

    # Coerce date columns safely (column must be a simple Series, not dict-like)
    for dcol in ["start_date", "end_date", "baseline_start", "baseline_finish"]:
        if dcol in df.columns:
            try:
                df[dcol] = pd.to_datetime(df[dcol], errors="coerce")
            except Exception:
                # If conversion fails (e.g. mixed types), force string conversion first
                df[dcol] = pd.to_datetime(
                    df[dcol].astype(str), errors="coerce"
                )

    # Identify project name from first data row
    project_name = "Unknown Project"
    if "task_name" in df.columns:
        candidates = df.loc[df["task_name"].notna(), "task_name"]
        if not candidates.empty:
            project_name = str(candidates.iloc[0])

    # Drop fully-empty rows
    df = df.dropna(how="all")

    return {
        "project_name":    project_name,
        "project_manager": project_manager,
        "start_date":      start_date,
        "end_date":        end_date,
        "summary":         summary,
        "tasks":           df,
        "comments":        comments_list,
        "file":            str(path.name),
    }


def project_to_text(project: dict) -> str:
    """
    Convert the loaded project dict into a concise text representation
    suitable for injection into an LLM prompt (Gemini).
    """
    s = project["summary"]
    total_tasks = s["not_started"] + s["in_progress"] + s["completed"] + s["on_hold"]
    pct_done = (s["completed"] / total_tasks * 100) if total_tasks else 0

    lines = [
        f"PROJECT: {project['project_name']}",
        f"Project Manager: {project['project_manager']}",
        f"Planned Start: {_fmt_date(project['start_date'])}",
        f"Planned End:   {_fmt_date(project['end_date'])}",
        f"",
        f"TASK SUMMARY (total {total_tasks} tasks)",
        f"  Completed   : {s['completed']}  ({pct_done:.1f}%)",
        f"  In Progress : {s['in_progress']}",
        f"  Not Started : {s['not_started']}",
        f"  On Hold     : {s['on_hold']}",
    ]

    df = project["tasks"]
    today = datetime.now()

    # ── Schedule slippage ─────────────────────────────────────────────────────
    slippage_rows = []
    if "variance" in df.columns and "task_name" in df.columns:
        slipped = df[df["variance"].notna() & (df["variance"] > 0)]
        slipped = slipped.sort_values("variance", ascending=False).head(10)
        for _, row in slipped.iterrows():
            name = str(row.get("task_name", ""))[:60]
            var  = row.get("variance", 0)
            sts  = row.get("status", "")
            slippage_rows.append(f"    {name} | Slippage: {var:.0f}d | Status: {sts}")

    if slippage_rows:
        lines += ["", "TOP SLIPPED TASKS (by days delayed):"] + slippage_rows

    # ── RAG breakdown ─────────────────────────────────────────────────────────
    rag_col = None
    for cname in ["rag", "schedule_health"]:
        if cname in df.columns:
            rag_col = cname
            break

    if rag_col:
        rag_counts = df[rag_col].dropna().str.strip().str.lower().value_counts()
        lines += ["", "RAG STATUS DISTRIBUTION (from plan):"]
        for color, cnt in rag_counts.items():
            lines.append(f"    {color.capitalize()}: {cnt} tasks")

    # ── At-risk / on-hold tasks ───────────────────────────────────────────────
    if "at_risk" in df.columns:
        at_risk_count = df["at_risk"].astype(str).str.strip().str.lower().isin(
            ["yes", "true", "1", "x"]
        ).sum()
        lines.append(f"\nAt-Risk Tasks: {at_risk_count}")

    if "on_hold" in df.columns:
        on_hold_count = df["on_hold"].astype(str).str.strip().str.lower().isin(
            ["yes", "true", "1", "x"]
        ).sum()
        lines.append(f"On-Hold Tasks: {on_hold_count}")

    # ── Milestones / phases ───────────────────────────────────────────────────
    milestone_rows = []
    if "phase" in df.columns:
        milestones = df[df["phase"].notna()][["phase", "status", "end_date", "rag"]
                                             if "rag" in df.columns
                                             else ["phase", "status", "end_date"]]
        milestones = milestones.drop_duplicates(subset=["phase"])
        for _, row in milestones.iterrows():
            phase   = str(row.get("phase", ""))[:50]
            status  = str(row.get("status", ""))
            end_dt  = row.get("end_date")
            rag_val = row.get("rag", "")
            end_str = _fmt_date(end_dt) if pd.notna(end_dt) else "N/A"
            overdue = ""
            if pd.notna(end_dt) and status.lower() not in ("completed",):
                delta = (today - end_dt).days
                if delta > 0:
                    overdue = f"  {delta}d overdue"
            milestone_rows.append(
                f"    [{rag_val}] {phase} | {status} | Due: {end_str}{overdue}"
            )

    if milestone_rows:
        lines += ["", "MILESTONES / PHASES:"] + milestone_rows[:15]

    # ── Comments ──────────────────────────────────────────────────────────────
    if project["comments"]:
        lines += ["", "RECENT COMMENTS / BLOCKERS:"]
        for c in project["comments"][:10]:
            lines.append(f"    - {c}")

    # ── Status comments from tasks ────────────────────────────────────────────
    if "status_comment" in df.columns:
        comments = df[df["status_comment"].notna()]["status_comment"].dropna().tolist()
        if comments:
            lines += ["", "STATUS COMMENTS FROM TASKS:"]
            for c in comments[:8]:
                lines.append(f"    - {str(c)[:120]}")

    return "\n".join(lines)


def _fmt_date(d) -> str:
    if d is None:
        return "N/A"
    try:
        if isinstance(d, datetime):
            return d.strftime("%d %b %Y")
        return str(d)
    except Exception:
        return str(d)
