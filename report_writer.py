"""
report_writer.py
================
Saves individual weekly reports as JSON + formatted text files.
"""

import json
from datetime import datetime
from pathlib import Path

from config import OUTPUTS_DIR


def save_report(report: dict, project_name: str = None) -> Path:
    """
    Save the report to the outputs directory.
    Returns the path to the saved JSON file.
    """
    name = (project_name or report.get("project_name", "unknown"))
    # Sanitise filename
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in name)[:40]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = OUTPUTS_DIR / f"{safe_name}_{timestamp}.json"
    txt_path  = OUTPUTS_DIR / f"{safe_name}_{timestamp}.txt"

    # Save JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    # Save formatted text
    from gemini_agent import format_console_report
    txt = format_console_report(report)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(txt)

    print(f"[OK] Report saved: {json_path.name}")
    return json_path


def load_all_reports() -> list[dict]:
    """Load all saved JSON reports from the outputs directory."""
    reports = []
    for json_file in sorted(OUTPUTS_DIR.glob("*.json")):
        try:
            with open(json_file, encoding="utf-8") as f:
                r = json.load(f)
                r["_source_file"] = str(json_file.name)
                reports.append(r)
        except Exception as e:
            print(f" Could not load {json_file.name}: {e}")
    return reports
