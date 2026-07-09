"""
main.py
=======
Primary entry point for the Project Health Reporting Agent.

Usage
-----
# Analyse all projects in data/ and generate a presentation:
    python main.py

# Analyse a specific project file:
    python main.py --file "data/Project Plan B.xlsx"

# Only generate the monthly presentation (from saved reports):
    python main.py --presentation-only

# Run on a weekly schedule:
    python scheduler.py --run-now
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Ensure we can import from this directory
sys.path.insert(0, str(Path(__file__).parent))

from config import DATA_DIR, OUTPUTS_DIR, GEMINI_API_KEY
from data_loader import load_project
from gemini_agent import analyse_project, format_console_report
from report_writer import save_report, load_all_reports
from presentation_generator import generate_presentation


def check_api_key():
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        print(" ERROR: GEMINI_API_KEY is not set.")
        print("   1. Copy .env.example to .env")
        print("   2. Add your Gemini API key to .env")
        print("   Get your key: https://aistudio.google.com/app/apikey")
        sys.exit(1)


def run_single_project(filepath: str | Path) -> dict:
    """Analyse one project file and save the report."""
    filepath = Path(filepath)
    print(f"")
    print(f"[>] Loading: {filepath.name}")
    
    try:
        project = load_project(filepath)
        print(f"   Project: {project['project_name']}")
        print(f"   Manager: {project['project_manager']}")
        print(f"   Tasks  : {sum(project['summary'].values())} total")
    except Exception as e:
        print(f"   [X] Could not load file: {e}")
        return {}

    print(f"   [~] Analysing with Gemini...")
    try:
        report = analyse_project(filepath, project_data=project)
    except Exception as e:
        print(f"   [X] Gemini call failed: {e}")
        return {}

    # Print to console
    print(format_console_report(report))

    # Save report
    save_report(report, project["project_name"])
    return report


def run_all_projects(data_dir: Path = None) -> list[dict]:
    """Analyse all Excel files found in the data directory."""
    data_dir = data_dir or DATA_DIR
    xlsx_files = list(data_dir.glob("*.xlsx"))

    if not xlsx_files:
        print(f"[!] No .xlsx files found in {data_dir}")
        return []

    print(f"")
    print(f"=" * 60)
    print(f"[*] Project Health Reporting Agent")
    print(f"    Found {len(xlsx_files)} project file(s) to analyse")
    print(f"    Run date: {datetime.now().strftime('%d %B %Y %H:%M')}")
    print(f"=" * 60)

    reports = []
    for xlsx in xlsx_files:
        report = run_single_project(xlsx)
        if report:
            reports.append(report)

    return reports


def main():
    check_api_key()

    parser = argparse.ArgumentParser(
        description="Project Health Reporting Agent powered by Gemini"
    )
    parser.add_argument(
        "--file", type=str, default=None,
        help="Path to a specific Excel project file"
    )
    parser.add_argument(
        "--presentation-only", action="store_true",
        help="Skip analysis; generate presentation from saved reports"
    )
    parser.add_argument(
        "--no-presentation", action="store_true",
        help="Run analysis only, skip presentation generation"
    )
    args = parser.parse_args()

    reports = []

    if args.presentation_only:
        # Load already-saved reports
        reports = load_all_reports()
        if not reports:
            print("[!] No saved reports found in outputs/. Run analysis first.")
            sys.exit(1)
        print(f"[>] Loaded {len(reports)} saved report(s) for presentation.")
    elif args.file:
        report = run_single_project(args.file)
        if report:
            reports = [report]
    else:
        reports = run_all_projects()

    if not args.no_presentation and reports:
        print(f"")
        print(f"=" * 60)
        print(f"[*] Generating Monthly Executive Presentation...")
        print(f"=" * 60)
        try:
            pptx_path = generate_presentation(reports)
            print(f"")
            print(f"[OK] All done!")
            print(f"   Reports saved in  : outputs/")
            print(f"   Presentation      : {pptx_path}")
        except Exception as e:
            print(f"[X] Presentation generation failed: {e}")
            import traceback; traceback.print_exc()
    else:
        print(f"\n Analysis complete. Reports saved in: {OUTPUTS_DIR}")


if __name__ == "__main__":
    main()
