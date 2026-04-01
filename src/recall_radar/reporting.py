import csv
import io
from datetime import datetime


def build_executive_csv(result, state: str, threshold: float, db_path: str) -> str:
    out = io.StringIO()
    writer = csv.writer(out)

    writer.writerow(["section", "metric", "value"])
    writer.writerow(["run", "generated_at", datetime.now().isoformat(timespec="seconds")])
    writer.writerow(["run", "state", state])
    writer.writerow(["run", "threshold", threshold])
    writer.writerow(["run", "db_path", db_path])
    writer.writerow(["summary", "total_matches", len(result.matches)])
    writer.writerow(["summary", "high_matches", len(result.triaged["HIGH"])])
    writer.writerow(["summary", "medium_matches", len(result.triaged["MEDIUM"])])
    writer.writerow(["summary", "low_matches", len(result.triaged["LOW"])])
    writer.writerow(["impact", "impacted_items", result.insights["impacted_items"]])

    for risk, units in result.insights["units_by_risk"].items():
        writer.writerow(["units_by_risk", risk, units])

    for brand, units in result.insights["top_brands_at_risk"]:
        writer.writerow(["top_brands_at_risk", brand, units])

    for location, units in result.insights["top_locations_at_risk"]:
        writer.writerow(["top_locations_at_risk", location, units])

    for klass, count in result.insights["recall_class_mix"].items():
        writer.writerow(["recall_class_mix", klass, count])

    for point in result.insights.get("daily_risk_trend", []):
        writer.writerow(["daily_risk_trend", point["date"], f"items={point['impacted_items']};units={point['units_at_risk']}"])

    stats = result.insights.get("detection_stats", {})
    for key in ["pantry_items", "recalls", "candidate_pairs", "scored_pairs", "cartesian_pairs"]:
        writer.writerow(["detection_stats", key, stats.get(key, 0)])

    return out.getvalue()


def build_executive_markdown(result, state: str, threshold: float, db_path: str) -> str:
    now = datetime.now().isoformat(timespec="seconds")
    trend_rows = "\n".join(
        f"| {p['date']} | {p['impacted_items']} | {p['units_at_risk']} |"
        for p in result.insights.get("daily_risk_trend", [])
    ) or "| n/a | 0 | 0 |"

    brand_rows = "\n".join(
        f"- {name}: {units} units" for name, units in result.insights["top_brands_at_risk"]
    ) or "- n/a"

    location_rows = "\n".join(
        f"- {name}: {units} units" for name, units in result.insights["top_locations_at_risk"]
    ) or "- n/a"

    stats = result.insights.get("detection_stats", {})

    return f"""# RecallRadar Executive Report

Generated: {now}

## Run Context
- State: `{state}`
- Threshold: `{threshold}`
- Database: `{db_path}`

## Match Summary
- Total candidate matches: **{len(result.matches)}**
- HIGH: **{len(result.triaged['HIGH'])}**
- MEDIUM: **{len(result.triaged['MEDIUM'])}**
- LOW: **{len(result.triaged['LOW'])}**

## Actionable Impact
- Impacted items: **{result.insights['impacted_items']}**
- Units at risk (HIGH): **{result.insights['units_by_risk']['HIGH']}**
- Units at risk (MEDIUM): **{result.insights['units_by_risk']['MEDIUM']}**
- Units at risk (LOW): **{result.insights['units_by_risk']['LOW']}**

### Top Brands At Risk
{brand_rows}

### Top Locations At Risk
{location_rows}

## Risk Trend (By Recall Event Date)
| Date | Impacted Items | Units At Risk |
|---|---:|---:|
{trend_rows}

## Detection Throughput
- Pantry items: **{stats.get('pantry_items', 0)}**
- Recall rows: **{stats.get('recalls', 0)}**
- Candidate pairs (indexed): **{stats.get('candidate_pairs', 0)}**
- Scored pairs: **{stats.get('scored_pairs', 0)}**
- Cartesian baseline: **{stats.get('cartesian_pairs', 0)}**

## Recommended Actions
""" + "\n".join(f"- {a}" for a in result.actions[:50]) + "\n"
