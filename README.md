# RecallRadar (Agentic AI Project)

RecallRadar is an **agentic AI + data engineering** project that answers a real-world question:

> "Do any active food recalls affect what I currently have at home, and what should I do next?"

It uses a multi-agent pipeline:

1. `DetectionAgent` scans pantry items against recall records.
2. `TriageAgent` categorizes hits into HIGH/MEDIUM/LOW risk.
3. `ActionPlannerAgent` generates concrete actions (discard, verify lot number, monitor).

<img width="1710" height="1107" alt="Screenshot 2026-03-31 at 7 26 21 PM" src="https://github.com/user-attachments/assets/3beeabb2-9037-4f7a-85c2-3cbb6b8dbf47" />

<img width="1710" height="1107" alt="Screenshot 2026-03-31 at 7 26 29 PM" src="https://github.com/user-attachments/assets/00fe1fb7-af9d-4128-965d-f3df79b25d2c" />

<img width="1710" height="1107" alt="Screenshot 2026-03-31 at 7 26 35 PM" src="https://github.com/user-attachments/assets/8c9ecd66-197a-4642-b67f-85def44b89fd" />

## Why this is a strong portfolio project

- **SWE**: clean modular architecture, CLI, tests, package structure.
- **AI/ML**: explainable risk scoring + agentic orchestration.
- **Data Engineering**: structured ingestion from CSV into SQLite, deterministic pipelines.

## Quick Start

```bash
cd /Users/gauravnair/Documents/Playground/recall-radar
python3 -m pip install -e .
recall-radar ingest
recall-radar run --state CA
```

## Web Dashboard (Interview Demo Mode)

Run the local UI:

```bash
cd /Users/gauravnair/Documents/Playground/recall-radar
PYTHONPATH=src python3 -m recall_radar.web --host 127.0.0.1 --port 8000
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).

In the dashboard:
- Click `Load Sample Data`
- Click `Run Analysis`
- Show triage cards + action plan live
- Show impact charts (units by risk, top brands, top storage locations)
- Show 14-day risk trend chart (units at risk by recall event date)
- Download executive reports:
  - `CSV` for analytics workflows
  - `Markdown` for sharing with recruiters/interviewers

## Example Output

- Risk bucket counts (HIGH/MEDIUM/LOW)
- Candidate item↔recall matches with reasons
- Action list you can execute immediately

## Data Model

`recalls`:
- `recall_id`, `event_date`, `product_name`, `brand`, `reason`, `classification`, `states`

`pantry_items`:
- `item_id`, `item_name`, `brand`, `quantity`, `location`

## Tests

```bash
cd /Users/gauravnair/Documents/Playground/recall-radar
PYTHONPATH=src python3 -m pytest -q
```

If `pytest` is unavailable:

```bash
cd /Users/gauravnair/Documents/Playground/recall-radar
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Extension Ideas

- Pull live FDA recall feed on a schedule.
- Add semantic matching (embeddings).
- Add an LLM summarizer + notification draft for impacted households.
- Expose as a FastAPI service and lightweight frontend dashboard.

## High-Volume Demo

Generate synthetic scale data:

```bash
cd /Users/gauravnair/Documents/Playground/recall-radar
PYTHONPATH=src python3 -m recall_radar.cli synth-data \
  --recalls-count 2000 \
  --pantry-count 5000 \
  --recalls-csv data/recalls_synthetic.csv \
  --pantry-csv data/pantry_synthetic.csv
```

Ingest and run:

```bash
cd /Users/gauravnair/Documents/Playground/recall-radar
PYTHONPATH=src python3 -m recall_radar.cli --db recall_radar_synth.db ingest \
  --recalls-csv data/recalls_synthetic.csv \
  --pantry-csv data/pantry_synthetic.csv

PYTHONPATH=src python3 -m recall_radar.cli --db recall_radar_synth.db run --state CA --threshold 0.6
```

You will see scalability metrics in output:
- `candidate_pairs` and `scored_pairs` (indexed blocking)
- `cartesian_pairs` baseline for comparison
