"""
Configuration for Project Health Reporting Agent
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")

# ===========================================================
# Gemini API
# ===========================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = "gemini-2.5-flash"          # Use flash for speed/cost

# ===========================================================
# Paths
# ===========================================================
BASE_DIR      = Path(__file__).parent
DATA_DIR      = BASE_DIR / "data"
OUTPUTS_DIR   = BASE_DIR / "outputs"
PRESENTATIONS = BASE_DIR / "presentations"
LOGS_DIR      = BASE_DIR / "logs"

# Ensure all dirs exist
for _d in [DATA_DIR, OUTPUTS_DIR, PRESENTATIONS, LOGS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ===========================================================
# RAG Thresholds
# ===========================================================
RAG_THRESHOLDS = {
    # Schedule slippage (days)
    "schedule_slip_red":   10,   # >10 days late → Red
    "schedule_slip_amber":  3,   # 3-10 days late → Amber

    # Overall completion vs expected completion ratio
    "completion_gap_red":   0.15,  # >15% behind expected → Red
    "completion_gap_amber": 0.07,  # 7-15% behind → Amber

    # % tasks in "Red" RAG status from the plan
    "red_task_ratio_red":   0.20,  # >20% tasks red → Red
    "red_task_ratio_amber": 0.08,  # 8-20% tasks red → Amber

    # On-Hold tasks ratio
    "on_hold_ratio_red":   0.10,  # >10% tasks on hold → Red
    "on_hold_ratio_amber": 0.04,

    # Milestone health: if next milestone is overdue
    "milestone_overdue_days_red":   7,
    "milestone_overdue_days_amber": 1,
}

# ===========================================================
# Weekly scheduler
# ===========================================================
SCHEDULE_DAY  = "monday"   # Day to run weekly report
SCHEDULE_TIME = "08:00"    # Time (24h, local timezone)
