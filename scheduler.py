"""
scheduler.py
============
Bonus: Runs the project health agent on a weekly schedule (every Monday 08:00).
Also exposes a manual "run now" option.
"""

import os
import time
import signal
import sys
from pathlib import Path
from datetime import datetime

import schedule as sched

from config import SCHEDULE_DAY, SCHEDULE_TIME, DATA_DIR
from main import run_all_projects


def _job():
    """The weekly job that runs for all project files."""
    print(f"\n{'='*60}")
    print(f"⏰ Weekly run triggered at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    run_all_projects()
    print(f"\n Weekly run complete. Next run: {SCHEDULE_DAY.title()} at {SCHEDULE_TIME}")


def start_scheduler(run_now: bool = False):
    """Start the weekly scheduler. Blocks until interrupted."""
    print(f"[SCHED] Scheduler started — will run every {SCHEDULE_DAY.title()} at {SCHEDULE_TIME}")
    print("   Press Ctrl+C to stop.\n")

    if run_now:
        print("▶ Running now (--run-now flag detected)...")
        _job()

    # Schedule the weekly job
    getattr(sched.every(), SCHEDULE_DAY).at(SCHEDULE_TIME).do(_job)

    try:
        while True:
            sched.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        print("\n[STOP] Scheduler stopped.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Project Health Agent Scheduler")
    parser.add_argument("--run-now", action="store_true",
                        help="Run immediately before starting the schedule")
    args = parser.parse_args()
    start_scheduler(run_now=args.run_now)
