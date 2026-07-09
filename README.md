# Project Health Reporting Agent

> AI-powered automated project health reporting using **Gemini 2.5 Flash** + rule-based RAG scoring.

Built as part of the Zycus AI Engineer Intern technical assignment.

---

## What This Does

| Phase | Output |
|-------|--------|
| Phase 1 | RAG Methodology (`RAG_Methodology.md`) |
| Phase 2 | AI Agent that reads project plans → RAG status + reasoning |
| Phase 3 | Auto-generated 6-slide executive PowerPoint presentation |
| Bonus   | Weekly scheduler (`scheduler.py`) |

---

## Project Structure

```
project_health_agent/
├── main.py                   # Main entry point
├── scheduler.py              # Bonus: weekly scheduler
├── config.py                 # Config & thresholds
├── data_loader.py            # Excel → structured data
├── rag_engine.py             # Rule-based RAG pre-scoring
├── gemini_agent.py           # Gemini AI analysis
├── report_writer.py          # Save/load reports
├── presentation_generator.py # PowerPoint generator
├── RAG_Methodology.md        # Phase 1 document
├── requirements.txt
├── .env.example              # Copy to .env
├── data/                     # Put your .xlsx files here
├── outputs/                  # Weekly reports saved here
├── presentations/            # PowerPoint files
└── logs/
```

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Get a Gemini API key
- Visit: https://aistudio.google.com/app/apikey
- Create a free API key

### 3. Configure environment
```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Edit `.env`:
```
GEMINI_API_KEY=your_actual_key_here
```

### 4. Add project files
Copy your `.xlsx` project plan files into the `data/` directory.

---

## Running the Agent

### Analyse all projects + generate presentation
```bash
cd project_health_agent
python main.py
```

### Analyse a specific project
```bash
python main.py --file "data/Project Plan B.xlsx"
```

### Generate presentation from saved reports only
```bash
python main.py --presentation-only
```

### Run analysis only (no presentation)
```bash
python main.py --no-presentation
```

### Start the weekly scheduler (Bonus)
```bash
# Runs every Monday at 08:00, also run immediately:
python scheduler.py --run-now

# Just start the schedule (run at next Monday 08:00):
python scheduler.py
```

---

## How It Works

### Data Flow
```
Excel File → data_loader.py → Structured Dict
                                    ↓
                            rag_engine.py (5 rule-based dimensions)
                                    ↓
                            gemini_agent.py (Gemini validation + reasoning)
                                    ↓
                    report_writer.py (JSON + TXT saved to outputs/)
                                    ↓
                    presentation_generator.py (6-slide PowerPoint)
```

### RAG Scoring
The agent uses a **hybrid approach**:
1. **Rule-based engine** scores 5 dimensions: schedule slippage, completion rate, in-plan RAG distribution, milestone health, on-hold ratio.
2. **Gemini 2.5 Flash** receives the pre-score + full project context, validates the RAG, adds plain-English reasoning and actionable recommendations.

See `RAG_Methodology.md` for full details.

### Handling Messy Data
- Unparseable Excel cells are skipped (not crashed on)
- Missing columns → that dimension defaults to Green with a note
- Missing dates → completion scoring defaults to Amber
- JSON parse errors from Gemini → graceful fallback to rule-based score

---

## Outputs

### Weekly Report (JSON)
```json
{
  "project_name": "Zycus - UniSan S2P Implementation",
  "report_date": "2026-07-09",
  "rag_status": "Red",
  "executive_summary": "...",
  "reasoning": {
    "schedule": "...",
    "completion_rate": "...",
    "milestone_health": "...",
    "blockers_risks": "...",
    "stakeholder_sentiment": "..."
  },
  "key_metrics": {...},
  "top_risks": [...],
  "recommendations": [...]
}
```

### Weekly Report (TXT)
Human-readable formatted version of the above.

### Monthly Presentation (PPTX)
6 slides:
1. **Cover** — portfolio status + headline
2. **Portfolio Snapshot** — per-project RAG tiles
3. **Trend Analysis** — cross-project trends
4. **Emerging Risks** — severity-ranked risk registry
5. **Executive Recommendations** — top 5 actions
6. **Next Steps** — closing summary

---

## Design Decisions

1. **Hybrid RAG scoring**: Rules alone miss context; pure LLM is inconsistent. Combining both gives reproducible + intelligent scores.
2. **Gemini 2.5 Flash**: Fast, cost-effective, excellent at structured JSON output.
3. **Conservative aggregation**: Overall RAG = worst dimension. Better to be safe and flag early.
4. **No crash on bad data**: The agent degrades gracefully — always produces a report even if some data is missing.
5. **Separation of concerns**: Each module (load, score, AI, save, present) is independently testable.

---

## Requirements

- Python 3.10+
- Gemini API key (free tier works)
- Windows / Linux / Mac

---

*Built by [Your Name] for Zycus AI Engineer Intern technical assignment, July 2026.*
