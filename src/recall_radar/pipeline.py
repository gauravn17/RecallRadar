from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from .agents import ActionPlannerAgent, DetectionAgent, TriageAgent
from .matching import risk_bucket
from .db import get_connection, init_db
from .ingest import ingest_pantry, ingest_recalls


@dataclass
class PipelineResult:
    matches: list
    triaged: dict
    actions: list[str]
    insights: dict


def rows(conn, query: str) -> list[dict]:
    return [dict(r) for r in conn.execute(query).fetchall()]


def ingest_data(db_path: str, recalls_csv: str, pantry_csv: str) -> tuple[int, int]:
    conn = get_connection(db_path)
    init_db(conn)
    recalls_count = ingest_recalls(conn, Path(recalls_csv))
    pantry_count = ingest_pantry(conn, Path(pantry_csv))
    return recalls_count, pantry_count


def run_pipeline(db_path: str, state: str, threshold: float) -> PipelineResult:
    conn = get_connection(db_path)
    init_db(conn)

    recalls = rows(conn, "SELECT * FROM recalls")
    pantry = rows(conn, "SELECT * FROM pantry_items")

    if not recalls or not pantry:
        raise ValueError("No data found. Run ingest first.")

    detector = DetectionAgent(threshold=threshold)
    triage = TriageAgent()
    planner = ActionPlannerAgent()

    matches = detector.run(pantry, recalls, user_state=state)
    triaged = triage.run(matches)
    pantry_by_id = {x["item_id"]: x for x in pantry}
    recalls_by_id = {x["recall_id"]: x for x in recalls}
    actions = planner.run(triaged, pantry_by_id, recalls_by_id)
    insights = _build_insights(
        matches=matches,
        pantry_by_id=pantry_by_id,
        recalls_by_id=recalls_by_id,
        detection_stats=getattr(detector, "last_stats", {}),
    )

    return PipelineResult(matches=matches, triaged=triaged, actions=actions, insights=insights)


def _build_insights(matches: list, pantry_by_id: dict, recalls_by_id: dict, detection_stats: dict) -> dict:
    best_match_by_item: dict[str, tuple[float, str]] = {}
    for m in matches:
        current = best_match_by_item.get(m.item_id)
        if current is None or m.score > current[0]:
            best_match_by_item[m.item_id] = (m.score, m.recall_id)

    impacted_items = len(best_match_by_item)
    units_by_risk = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    brands_at_risk: dict[str, int] = {}
    locations_at_risk: dict[str, int] = {}
    recall_class_mix = {"I": 0, "II": 0, "III": 0}
    daily_totals: dict[str, dict[str, int]] = defaultdict(lambda: {"impacted_items": 0, "units_at_risk": 0})

    for item_id, (score, recall_id) in best_match_by_item.items():
        risk = risk_bucket(score)
        item = pantry_by_id[item_id]
        recall = recalls_by_id[recall_id]
        qty = int(item.get("quantity") or 0)
        units_by_risk[risk] += qty

        brand = (item.get("brand") or "Unknown").strip() or "Unknown"
        brands_at_risk[brand] = brands_at_risk.get(brand, 0) + qty

        location = (item.get("location") or "Unknown").strip() or "Unknown"
        locations_at_risk[location] = locations_at_risk.get(location, 0) + qty

        klass = (recall.get("classification") or "").strip().upper()
        if klass in recall_class_mix:
            recall_class_mix[klass] += 1

        event_date = (recall.get("event_date") or "unknown").strip() or "unknown"
        daily_totals[event_date]["impacted_items"] += 1
        daily_totals[event_date]["units_at_risk"] += qty

    def _top_n(d: dict[str, int], n: int = 6) -> list[tuple[str, int]]:
        return sorted(d.items(), key=lambda kv: kv[1], reverse=True)[:n]

    return {
        "impacted_items": impacted_items,
        "units_by_risk": units_by_risk,
        "top_brands_at_risk": _top_n(brands_at_risk),
        "top_locations_at_risk": _top_n(locations_at_risk),
        "recall_class_mix": recall_class_mix,
        "daily_risk_trend": [
            {"date": date_key, **daily_totals[date_key]}
            for date_key in sorted(daily_totals.keys())[-14:]
        ],
        "detection_stats": detection_stats,
    }
