import argparse
import html
import urllib.parse
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .pipeline import ingest_data, run_pipeline
from .reporting import build_executive_csv, build_executive_markdown

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = str(PROJECT_ROOT / "recall_radar.db")
DEFAULT_RECALLS = str(PROJECT_ROOT / "data" / "recalls_sample.csv")
DEFAULT_PANTRY = str(PROJECT_ROOT / "data" / "pantry_sample.csv")


def _render_page(
    *,
    state: str,
    threshold: float,
    db_path: str,
    message: str = "",
    error: str = "",
    results: dict | None = None,
) -> str:
    safe_state = html.escape(state)
    safe_db = html.escape(db_path)
    safe_message = html.escape(message)
    safe_error = html.escape(error)

    if results:
        counts = results["counts"]
        total = results["total_matches"]
        insights = results["insights"]
        bucket_html = "".join(
            (
                f'<div class="bucket {bucket.lower()}">'
                f'<h3>{bucket}</h3>'
                f'<p class="count">{counts[bucket]}</p>'
                "</div>"
            )
            for bucket in ["HIGH", "MEDIUM", "LOW"]
        )

        detail_parts: list[str] = []
        for bucket in ["HIGH", "MEDIUM", "LOW"]:
            lines = results["details"][bucket]
            if not lines:
                continue
            line_items = "".join(f"<li>{html.escape(line)}</li>" for line in lines)
            detail_parts.append(
                f"<section class='detail-card'><h4>{bucket} Matches</h4><ul>{line_items}</ul></section>"
            )
        details_html = "".join(detail_parts) or "<p>No matches found.</p>"

        action_items = "".join(f"<li>{html.escape(a)}</li>" for a in results["actions"])
        units_by_risk = insights["units_by_risk"]
        top_brands = insights["top_brands_at_risk"]
        top_locations = insights["top_locations_at_risk"]
        trend_points = insights.get("daily_risk_trend", [])
        detection_stats = insights["detection_stats"]
        max_brand_units = max([v for _, v in top_brands], default=1)
        max_location_units = max([v for _, v in top_locations], default=1)

        brand_bars = "".join(
            (
                "<div class='bar-row'>"
                f"<span>{html.escape(name)}</span>"
                f"<div class='bar-track'><div class='bar-fill brand' style='width:{(units / max_brand_units) * 100:.1f}%'></div></div>"
                f"<strong>{units}</strong>"
                "</div>"
            )
            for name, units in top_brands
        ) or "<p>No impacted brands detected.</p>"

        location_bars = "".join(
            (
                "<div class='bar-row'>"
                f"<span>{html.escape(name)}</span>"
                f"<div class='bar-track'><div class='bar-fill location' style='width:{(units / max_location_units) * 100:.1f}%'></div></div>"
                f"<strong>{units}</strong>"
                "</div>"
            )
            for name, units in top_locations
        ) or "<p>No impacted locations detected.</p>"

        max_trend_units = max([p["units_at_risk"] for p in trend_points], default=1)
        trend_bars = "".join(
            (
                "<div class='trend-row'>"
                f"<span>{html.escape(point['date'])}</span>"
                f"<div class='bar-track'><div class='bar-fill trend' style='width:{(point['units_at_risk'] / max_trend_units) * 100:.1f}%'></div></div>"
                f"<strong>{point['units_at_risk']}u</strong>"
                "</div>"
            )
            for point in trend_points
        ) or "<p>No trend points available.</p>"

        results_html = f"""
        <section class="panel">
          <div class="summary-row">
            <div class="summary">
              <h3>Total Candidate Matches</h3>
              <p class="total">{total}</p>
            </div>
            <div class="bucket-grid">{bucket_html}</div>
          </div>
          <div class="detail-grid">{details_html}</div>
          <div class="actions">
            <h3>Recommended Actions</h3>
            <ol>{action_items}</ol>
          </div>
        </section>
        <section class="panel">
          <h3>Impact Snapshot</h3>
          <div class="impact-grid">
            <div class="impact-card">
              <h4>Impacted Items</h4>
              <p class="impact-value">{insights["impacted_items"]}</p>
            </div>
            <div class="impact-card">
              <h4>Units At Risk (HIGH)</h4>
              <p class="impact-value">{units_by_risk["HIGH"]}</p>
            </div>
            <div class="impact-card">
              <h4>Units At Risk (MEDIUM)</h4>
              <p class="impact-value">{units_by_risk["MEDIUM"]}</p>
            </div>
            <div class="impact-card">
              <h4>Units At Risk (LOW)</h4>
              <p class="impact-value">{units_by_risk["LOW"]}</p>
            </div>
          </div>
          <div class="viz-grid">
            <section class="viz-card">
              <h4>Top Brands At Risk (Units)</h4>
              {brand_bars}
            </section>
            <section class="viz-card">
              <h4>Top Locations At Risk (Units)</h4>
              {location_bars}
            </section>
          </div>
          <div class="stats-line">
            Candidate pairs: <strong>{detection_stats.get("candidate_pairs", 0)}</strong> |
            Scored pairs: <strong>{detection_stats.get("scored_pairs", 0)}</strong> |
            Cartesian baseline: <strong>{detection_stats.get("cartesian_pairs", 0)}</strong>
          </div>
          <section class="viz-card trend-card">
            <h4>14-Day Units At Risk Trend</h4>
            {trend_bars}
          </section>
          <div class="download-row">
            <form method="get" action="/download-report.csv">
              <input type="hidden" name="state" value="{safe_state}" />
              <input type="hidden" name="threshold" value="{threshold}" />
              <input type="hidden" name="db" value="{safe_db}" />
              <button class="btn-secondary" type="submit">Download CSV Report</button>
            </form>
            <form method="get" action="/download-report.md">
              <input type="hidden" name="state" value="{safe_state}" />
              <input type="hidden" name="threshold" value="{threshold}" />
              <input type="hidden" name="db" value="{safe_db}" />
              <button class="btn-secondary" type="submit">Download Markdown Report</button>
            </form>
          </div>
        </section>
        """
    else:
        results_html = """
        <section class="panel empty">
          <h3>Run Analysis</h3>
          <p>Load data and click <strong>Run Analysis</strong> to generate risk triage and action steps.</p>
        </section>
        """

    return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>RecallRadar Dashboard</title>
  <style>
    :root {{
      --ink: #10252b;
      --teal: #0d8b8f;
      --mint: #9fe3d5;
      --warm: #ffd07f;
      --danger: #bc2f2f;
      --ok: #2f6f4f;
      --card: #ffffffee;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: "Avenir Next", "Trebuchet MS", "Gill Sans", sans-serif;
      background: radial-gradient(1200px 500px at 8% 8%, #c5f2e8 0%, transparent 65%),
                  radial-gradient(900px 500px at 92% 18%, #ffe0a8 0%, transparent 55%),
                  linear-gradient(135deg, #e8fbf6 0%, #eff7ff 45%, #fff8ea 100%);
      min-height: 100vh;
      padding: 28px 16px 48px;
    }}
    .container {{ max-width: 1080px; margin: 0 auto; }}
    .hero {{
      background: linear-gradient(90deg, #0d8b8f, #0f5f88);
      color: #fff;
      border-radius: 20px;
      padding: 22px;
      box-shadow: 0 12px 30px #0d8b8f40;
    }}
    .hero h1 {{ margin: 0 0 8px; font-size: 2rem; letter-spacing: 0.2px; }}
    .hero p {{ margin: 0; opacity: 0.95; }}
    .panel {{
      background: var(--card);
      border-radius: 16px;
      margin-top: 16px;
      padding: 16px;
      border: 1px solid #ffffff;
      box-shadow: 0 10px 24px #14364f1a;
    }}
    .controls {{ display: grid; gap: 12px; grid-template-columns: repeat(4, minmax(0, 1fr)); }}
    .controls label {{ font-size: 0.86rem; text-transform: uppercase; letter-spacing: 0.08em; color: #35545b; }}
    .controls input {{
      width: 100%;
      margin-top: 6px;
      border: 1px solid #9fc3c0;
      border-radius: 10px;
      padding: 10px 12px;
      background: #fff;
      font-size: 1rem;
    }}
    .buttons {{ display: flex; gap: 10px; align-items: end; }}
    button {{
      border: none;
      border-radius: 999px;
      padding: 11px 18px;
      cursor: pointer;
      font-weight: 700;
      letter-spacing: 0.02em;
    }}
    .btn-primary {{ background: linear-gradient(90deg, #0d8b8f, #1279b2); color: #fff; }}
    .btn-secondary {{ background: #d8eee9; color: #0f595d; }}
    .message {{ color: var(--ok); margin-top: 10px; font-weight: 600; }}
    .error {{ color: var(--danger); margin-top: 10px; font-weight: 700; }}
    .summary-row {{ display: grid; gap: 12px; grid-template-columns: 1fr 2fr; }}
    .summary {{ background: #f4fdf9; border-radius: 14px; padding: 12px; }}
    .summary .total {{ font-size: 2.1rem; margin: 6px 0 0; font-weight: 800; }}
    .bucket-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
    .bucket {{ border-radius: 14px; padding: 12px; color: #fff; }}
    .bucket h3 {{ margin: 0; font-size: 0.95rem; }}
    .bucket .count {{ margin: 8px 0 0; font-size: 1.7rem; font-weight: 800; }}
    .bucket.high {{ background: linear-gradient(120deg, #b74343, #9f2d2d); }}
    .bucket.medium {{ background: linear-gradient(120deg, #bc7d1d, #a86400); }}
    .bucket.low {{ background: linear-gradient(120deg, #2f7a56, #27694a); }}
    .detail-grid {{ display: grid; gap: 10px; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); margin-top: 12px; }}
    .detail-card {{ background: #f8fbff; border-radius: 12px; padding: 12px; border: 1px solid #e2ebf7; }}
    .detail-card h4 {{ margin: 0 0 8px; }}
    .detail-card ul {{ margin: 0; padding-left: 18px; }}
    .actions {{ margin-top: 12px; background: #fff9ef; border-radius: 12px; padding: 12px; border: 1px solid #f2dfbe; }}
    .actions h3 {{ margin-top: 0; }}
    .impact-grid {{ display: grid; gap: 10px; grid-template-columns: repeat(4, minmax(0, 1fr)); }}
    .impact-card {{ background: #f4faff; border: 1px solid #d8e7f9; border-radius: 12px; padding: 10px; }}
    .impact-card h4 {{ margin: 0; font-size: 0.9rem; color: #305165; }}
    .impact-value {{ margin: 8px 0 0; font-size: 1.6rem; font-weight: 800; }}
    .viz-grid {{ margin-top: 12px; display: grid; gap: 10px; grid-template-columns: 1fr 1fr; }}
    .viz-card {{ background: #fbfdff; border: 1px solid #dde8f6; border-radius: 12px; padding: 12px; }}
    .viz-card h4 {{ margin-top: 0; margin-bottom: 8px; }}
    .bar-row {{ display: grid; grid-template-columns: 120px 1fr auto; gap: 8px; align-items: center; margin-bottom: 8px; }}
    .bar-row span {{ font-size: 0.9rem; color: #27444e; }}
    .bar-track {{ height: 10px; border-radius: 999px; background: #e8eff8; overflow: hidden; }}
    .bar-fill {{ height: 100%; border-radius: 999px; }}
    .bar-fill.brand {{ background: linear-gradient(90deg, #1f8ab2, #0f628e); }}
    .bar-fill.location {{ background: linear-gradient(90deg, #4ca86c, #2f7a56); }}
    .bar-fill.trend {{ background: linear-gradient(90deg, #b8701f, #8f4f08); }}
    .trend-card {{ margin-top: 12px; }}
    .trend-row {{ display: grid; grid-template-columns: 110px 1fr auto; gap: 8px; align-items: center; margin-bottom: 8px; }}
    .trend-row span {{ font-size: 0.88rem; color: #2d4a52; }}
    .download-row {{ margin-top: 12px; display: flex; gap: 10px; flex-wrap: wrap; }}
    .stats-line {{ margin-top: 8px; font-size: 0.92rem; color: #26484f; }}
    .empty p {{ margin-bottom: 0; }}
    @media (max-width: 900px) {{
      .controls {{ grid-template-columns: 1fr 1fr; }}
      .summary-row {{ grid-template-columns: 1fr; }}
      .impact-grid {{ grid-template-columns: 1fr 1fr; }}
      .viz-grid {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 560px) {{
      .controls {{ grid-template-columns: 1fr; }}
      .bucket-grid {{ grid-template-columns: 1fr; }}
      .buttons {{ flex-wrap: wrap; }}
      .impact-grid {{ grid-template-columns: 1fr; }}
      .bar-row {{ grid-template-columns: 100px 1fr auto; }}
      .trend-row {{ grid-template-columns: 96px 1fr auto; }}
    }}
  </style>
</head>
<body>
  <main class="container">
    <header class="hero">
      <h1>RecallRadar Dashboard</h1>
      <p>Agentic AI triage for household food safety and rapid response.</p>
    </header>

    <section class="panel">
      <form method="post" action="/analyze" class="controls">
        <div>
          <label for="state">State</label>
          <input id="state" name="state" value="{safe_state}" maxlength="2" required />
        </div>
        <div>
          <label for="threshold">Threshold</label>
          <input id="threshold" name="threshold" type="number" step="0.01" min="0" max="1" value="{threshold}" required />
        </div>
        <div>
          <label for="db">SQLite DB Path</label>
          <input id="db" name="db" value="{safe_db}" required />
        </div>
        <div class="buttons">
          <button class="btn-primary" type="submit">Run Analysis</button>
          <button class="btn-secondary" type="submit" formaction="/ingest-sample">Load Sample Data</button>
        </div>
      </form>
      {f'<div class="message">{safe_message}</div>' if safe_message else ''}
      {f'<div class="error">{safe_error}</div>' if safe_error else ''}
    </section>

    {results_html}
  </main>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    default_state = "CA"
    default_threshold = 0.52
    default_db_path = DEFAULT_DB

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self._send_html(
                _render_page(
                    state=self.default_state,
                    threshold=self.default_threshold,
                    db_path=self.default_db_path,
                )
            )
            return

        if parsed.path in {"/download-report.csv", "/download-report.md"}:
            params = urllib.parse.parse_qs(parsed.query)
            state, threshold, db_path = self._extract_common_params(params)
            try:
                result = run_pipeline(db_path, state=state, threshold=threshold)
            except ValueError as exc:
                self._send_text(str(exc), HTTPStatus.BAD_REQUEST)
                return

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            if parsed.path.endswith(".csv"):
                payload = build_executive_csv(result, state=state, threshold=threshold, db_path=db_path)
                self._send_attachment(
                    payload.encode("utf-8"),
                    f"recallradar_report_{ts}.csv",
                    "text/csv; charset=utf-8",
                )
                return

            payload = build_executive_markdown(result, state=state, threshold=threshold, db_path=db_path)
            self._send_attachment(
                payload.encode("utf-8"),
                f"recallradar_report_{ts}.md",
                "text/markdown; charset=utf-8",
            )
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(length).decode("utf-8")
        params = urllib.parse.parse_qs(data)

        state, threshold, db_path = self._extract_common_params(params)

        if self.path == "/ingest-sample":
            recalls_count, pantry_count = ingest_data(db_path, DEFAULT_RECALLS, DEFAULT_PANTRY)
            page = _render_page(
                state=state,
                threshold=threshold,
                db_path=db_path,
                message=f"Loaded sample data: {recalls_count} recalls and {pantry_count} pantry items.",
            )
            self._send_html(page)
            return

        if self.path == "/analyze":
            try:
                result = run_pipeline(db_path, state=state, threshold=threshold)
            except ValueError as exc:
                page = _render_page(
                    state=state,
                    threshold=threshold,
                    db_path=db_path,
                    error=str(exc),
                )
                self._send_html(page)
                return

            details: dict[str, list[str]] = {"HIGH": [], "MEDIUM": [], "LOW": []}
            for bucket in ["HIGH", "MEDIUM", "LOW"]:
                for m in result.triaged[bucket][:8]:
                    reasons = ", ".join(m.reasons)
                    details[bucket].append(
                        f"item={m.item_id}, recall={m.recall_id}, score={m.score}, reasons={reasons}"
                    )

            page = _render_page(
                state=state,
                threshold=threshold,
                db_path=db_path,
                message="Analysis complete.",
                results={
                    "total_matches": len(result.matches),
                    "counts": {k: len(v) for k, v in result.triaged.items()},
                    "details": details,
                    "actions": result.actions,
                    "insights": result.insights,
                },
            )
            self._send_html(page)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def _send_html(self, page: str) -> None:
        body = page.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, body_text: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = body_text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_attachment(self, body: bytes, filename: str, content_type: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _extract_common_params(self, params: dict[str, list[str]]) -> tuple[str, float, str]:
        state = (params.get("state", [self.default_state])[0] or self.default_state).upper()[:2]
        db_path = params.get("db", [self.default_db_path])[0] or self.default_db_path
        try:
            threshold = float(params.get("threshold", [str(self.default_threshold)])[0])
        except ValueError:
            threshold = self.default_threshold
        return state, threshold, db_path


def main() -> None:
    parser = argparse.ArgumentParser(description="RecallRadar web dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--db", default=DEFAULT_DB)
    args = parser.parse_args()

    DashboardHandler.default_db_path = args.db

    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"RecallRadar UI running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
