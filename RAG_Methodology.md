# RAG Status Methodology
## Project Health Reporting Framework

**Document Owner:** AI Project Health Agent  
**Version:** 1.0 | **Date:** July 2026

---

## Overview

This framework defines how RAG (Red / Amber / Green) status is calculated for any Zycus S2P implementation project. The methodology combines **five quantitative signals** derived from project plan data with **Gemini AI reasoning** to produce a balanced, explainable health score.

---

## The Five Scoring Dimensions

| # | Dimension | Weight | What it measures |
|---|-----------|--------|-----------------|
| 1 | **Schedule Slippage** | High | Max days any active task is delayed vs baseline |
| 2 | **Completion Rate vs Expected** | High | Actual % complete vs where we should be today |
| 3 | **In-Plan RAG Distribution** | Medium | % of tasks already flagged Red inside the project plan |
| 4 | **Milestone Health** | Medium | Whether key phase milestones are overdue |
| 5 | **On-Hold Task Ratio** | Low | % of tasks blocked / on hold |

The **overall RAG = worst colour across all five dimensions** (conservative approach — one Red makes the project Red).

---

## Dimension 1 — Schedule Slippage

Measures the **worst slippage** (in calendar days) among all In-Progress or Not-Started tasks, using the `Variance` column (Actual End − Baseline End).

| Condition | RAG |
|-----------|-----|
| Max slippage > 10 days | Red |
| Max slippage 3–10 days | Amber |
| Max slippage < 3 days | Green |

---

## Dimension 2 — Completion Rate vs Expected

Compares **actual % of tasks completed** against the **expected % based on elapsed project time**.

```
Expected % = (Days elapsed since start) / (Total project duration)
Gap = Expected % - Actual %
```

| Condition | RAG |
|-----------|-----|
| Gap > 15% | Red |
| Gap 7-15% | Amber |
| Gap < 7%  | Green |

**Assumption:** Linear work distribution over the project timeline.

---

## Dimension 3 — In-Plan RAG Distribution

Uses the `RAG` / `Schedule Health` column already present in Zycus project plans.

| Condition | RAG |
|-----------|-----|
| > 20% of tasks are Red | Red |
| 8-20% Red OR > 30% Amber | Amber |
| < 8% Red tasks | Green |

---

## Dimension 4 — Milestone Health

Checks whether any **Phase / Milestone end dates** are overdue today (for non-completed milestones).

| Condition | RAG |
|-----------|-----|
| Any milestone > 7 days overdue | Red |
| Any milestone 1-7 days overdue | Amber |
| All milestones on track | Green |

---

## Dimension 5 — On-Hold Task Ratio

| Condition | RAG |
|-----------|-----|
| On-Hold > 10% of total tasks | Red |
| On-Hold 4-10% of total tasks | Amber |
| On-Hold < 4% of total tasks  | Green |

---

## AI Layer — Gemini Override

After the rule-based score, **Gemini 2.5 Flash** receives:
- The project text summary
- The rule-based pre-score and dimension details
- Any comments/blockers from the project file

Gemini can **confirm or override** the overall RAG if qualitative context (e.g., a critical blocker in comments, or a significant mitigation already in place) justifies it. The model must explain its reasoning in plain English.

This hybrid approach ensures:
- **Consistency** — rules catch the obvious signals
- **Judgment** — AI handles nuance, incomplete data, and context

---

## Handling Incomplete / Messy Data

| Issue | Handling |
|-------|----------|
| Missing Variance column | Schedule dimension defaults to Green with a note |
| Missing project dates | Completion dimension defaults to Amber with a note |
| Empty RAG column | Dimension skipped, noted in report |
| Unparseable cells | Filtered out; data quality note added to report |
| Partially populated milestones | Only non-null rows scored |

---

## Assumptions

1. Project plans follow the Zycus standard Excel format.
2. Baseline dates represent the original contracted plan (not revised).
3. "Completed" tasks are excluded from slippage calculations.
4. Stakeholder sentiment is inferred from comments/status fields (no survey data available).
5. Budget data is not available in the provided Excel format — this dimension is omitted but can be added when financial data is supplied.

---

## RAG Colour Definitions

| Status | Meaning | Action |
|--------|---------|--------|
| Green  | On track. No material risks. | Continue as planned. |
| Amber  | At risk. Issues exist but recoverable. | Escalate to PM; review mitigations. |
| Red    | In trouble. Significant delay/risk. | Immediate VP/Client attention required. |
