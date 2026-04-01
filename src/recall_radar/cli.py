import argparse
from pathlib import Path

from .pipeline import ingest_data, run_pipeline
from .synth import generate_synthetic_data


def cmd_ingest(args: argparse.Namespace) -> None:
    recalls_count, pantry_count = ingest_data(args.db, args.recalls_csv, args.pantry_csv)
    print(f"Ingested {recalls_count} recall rows and {pantry_count} pantry rows into {args.db}.")


def cmd_run(args: argparse.Namespace) -> None:
    try:
        result = run_pipeline(args.db, state=args.state, threshold=args.threshold)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    print("=== RecallRadar Action Plan ===")
    print(f"State: {args.state} | Threshold: {args.threshold}")
    print(f"Matches: {len(result.matches)}")
    print("")

    for bucket in ["HIGH", "MEDIUM", "LOW"]:
        print(f"[{bucket}] {len(result.triaged[bucket])}")
        for m in result.triaged[bucket][: args.max_per_bucket]:
            print(f"  - item={m.item_id}, recall={m.recall_id}, score={m.score}, reasons={', '.join(m.reasons)}")
        print("")

    print("Actions:")
    for action in result.actions:
        print(f"- {action}")

    print("")
    print("Impact Insights:")
    print(f"- impacted_items={result.insights['impacted_items']}")
    print(f"- units_by_risk={result.insights['units_by_risk']}")
    print(f"- top_brands_at_risk={result.insights['top_brands_at_risk']}")
    print(f"- top_locations_at_risk={result.insights['top_locations_at_risk']}")
    print(f"- detection_stats={result.insights['detection_stats']}")


def cmd_synth(args: argparse.Namespace) -> None:
    recalls_path = Path(args.recalls_csv)
    pantry_path = Path(args.pantry_csv)
    recalls_count, pantry_count = generate_synthetic_data(
        recalls_path=recalls_path,
        pantry_path=pantry_path,
        recalls_count=args.recalls_count,
        pantry_count=args.pantry_count,
        seed=args.seed,
    )
    print(
        f"Generated synthetic data: recalls={recalls_count} ({recalls_path}), "
        f"pantry={pantry_count} ({pantry_path})"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RecallRadar: agentic food recall matching")
    parser.add_argument("--db", default="recall_radar.db", help="SQLite database path")

    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="Ingest CSV data")
    ingest.add_argument("--recalls-csv", default="data/recalls_sample.csv")
    ingest.add_argument("--pantry-csv", default="data/pantry_sample.csv")
    ingest.set_defaults(func=cmd_ingest)

    run = sub.add_parser("run", help="Run multi-agent workflow")
    run.add_argument("--state", default="CA")
    run.add_argument("--threshold", type=float, default=0.52)
    run.add_argument("--max-per-bucket", type=int, default=5)
    run.set_defaults(func=cmd_run)

    synth = sub.add_parser("synth-data", help="Generate synthetic high-volume CSV datasets")
    synth.add_argument("--recalls-csv", default="data/recalls_synthetic.csv")
    synth.add_argument("--pantry-csv", default="data/pantry_synthetic.csv")
    synth.add_argument("--recalls-count", type=int, default=50000)
    synth.add_argument("--pantry-count", type=int, default=120000)
    synth.add_argument("--seed", type=int, default=42)
    synth.set_defaults(func=cmd_synth)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
