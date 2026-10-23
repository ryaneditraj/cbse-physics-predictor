"""Self-contained HTML report. Concept names and filenames are escaped."""

from __future__ import annotations

import html
from pathlib import Path

from cbse_physics.analysis import Analysis
from cbse_physics.models import FEATURE_LABELS

_MODEL_LABELS = {
    "empirical_bayes": "Empirical Bayes",
    "blend": "Bayes + boosting",
    "gradient_boosting": "Gradient boosting",
    "frequency": "Raw frequency",
    "unit_weight": "Official unit weight",
}


def _e(value: object) -> str:
    escaped = html.escape(str(value), quote=True)
    # Braces would be read as format fields by the HTML template below.
    return escaped.replace("{", "&#123;").replace("}", "&#125;")


def _pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.1f}%"


def _num(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}"


def render_report(analysis: Analysis, *, top: int = 12) -> str:
    metric_cards = []
    for name in ("empirical_bayes", "blend", "gradient_boosting", "frequency", "unit_weight"):
        score = analysis.backtest.mean_marks_fraction(name)
        precision = analysis.backtest.mean_precision(name)
        selected = name == analysis.selected_model
        metric_cards.append(
            f"""<article class="metric{' selected' if selected else ''}">
              <p class="kicker">{_e(_MODEL_LABELS[name])}</p>
              <p class="figure">{_e(_pct(score))}</p>
              <p class="fine">of appeared marks inside the top {analysis.backtest.k}</p>
              <p class="fine">precision {_e(_pct(precision))}{' · used for the plan' if selected else ''}</p>
            </article>"""
        )
    rows = []
    for index, item in enumerate(analysis.ranking[:top], start=1):
        rows.append(
            f"""<li>
              <span class="rank">{index:02d}</span>
              <div>
                <p class="name">{_e(item.concept.name)}</p>
                <p class="meta">{_e(item.concept.chapter)} · group {_e(item.concept.unit_group)} · {_e(_num(item.concept.study_hours, 1))} h to cover</p>
              </div>
              <div class="nums">
                <strong>{_e(_pct(item.probability))}</strong>
                <span>{_e(_num(item.expected_marks))} expected marks</span>
              </div>
            </li>"""
        )
    plan_rows = []
    for item in analysis.plan.items:
        plan_rows.append(
            f"""<li>
              <div>
                <p class="name">{_e(item.ranked.concept.name)}</p>
                <p class="meta">{_e(item.ranked.concept.chapter)}</p>
              </div>
              <div class="nums">
                <strong>{_e(_num(item.hours, 1))} h</strong>
                <span>{_e(_num(item.ranked.ev_per_hour))} marks / hour</span>
              </div>
            </li>"""
        )
    if not plan_rows:
        plan_rows.append("<li><p class=\"name\">No concept fits in the remaining time.</p></li>")
    group_bits = _group_bits(analysis)
    warnings = "".join(f"<li>{_e(warning)}</li>" for warning in analysis.warnings)
    warning_block = f'<ul class="plain">{warnings}</ul>' if warnings else ""
    importance = "".join(
        f"<li><span>{_e(FEATURE_LABELS.get(name, name))}</span><strong>{_e(_pct(value))}</strong></li>"
        for name, value in analysis.importances[:5]
    )
    if not importance:
        importance = "<li><span>Not available on this window.</span><strong></strong></li>"
    years = ", ".join(str(year) for year in analysis.years)
    evaluated = ", ".join(str(year) for year in analysis.backtest.evaluated_years) or "none"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'">
  <title>Class 12 Physics study rank for {_e(analysis.target_year)}</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #12140f;
      --bg-2: #1b2016;
      --ink: #f3f1e6;
      --muted: #c4c1b2;
      --line: #31362a;
      --accent: #dff25a;
      --teal: #8fd6c4;
      --warn: #ffbf70;
      --chip: #2a2618;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        radial-gradient(900px 420px at 10% -10%, rgba(223, 242, 90, 0.08), transparent 60%),
        var(--bg);
      color: var(--ink);
      font: 16px/1.5 "Segoe UI", ui-sans-serif, Helvetica, Arial, sans-serif;
    }}
    main {{ max-width: 1080px; margin: 0 auto; padding: 40px 24px 72px; }}
    .eyebrow {{
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--accent);
      font-size: 12px;
      margin: 0 0 8px;
    }}
    h1 {{
      font-family: Georgia, "Iowan Old Style", Palatino, serif;
      font-weight: 500;
      font-size: clamp(36px, 6vw, 64px);
      line-height: 0.95;
      margin: 0 0 12px;
    }}
    .lede {{ max-width: 68ch; color: var(--muted); margin: 0 0 18px; }}
    .banner {{
      background: #2c2416;
      color: var(--warn);
      border: 1px solid #5a4630;
      border-radius: 12px;
      padding: 12px 14px;
      margin: 0 0 22px;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 12px;
      margin: 18px 0 28px;
    }}
    .metric {{
      background: var(--bg-2);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
    }}
    .metric.selected {{ border-color: var(--accent); }}
    .kicker {{ margin: 0; color: var(--muted); font-size: 13px; }}
    .figure {{
      margin: 6px 0 0;
      font-family: Georgia, Palatino, serif;
      font-size: 40px;
      letter-spacing: -0.03em;
      color: var(--ink);
    }}
    .fine {{ margin: 0; color: var(--muted); font-size: 13px; }}
    section {{ margin-top: 28px; }}
    h2 {{
      font-family: Georgia, Palatino, serif;
      font-weight: 500;
      font-size: 28px;
      margin: 0 0 8px;
    }}
    ol.list, ul.plain {{ list-style: none; padding: 0; margin: 0; }}
    ol.list li, .split li {{
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: 14px;
      align-items: center;
      padding: 12px 0;
      border-top: 1px solid var(--line);
    }}
    .rank {{ color: var(--teal); font-variant-numeric: tabular-nums; }}
    .name {{ margin: 0; font-size: 17px; }}
    .meta {{ margin: 2px 0 0; color: var(--muted); font-size: 13px; }}
    .nums {{ text-align: right; }}
    .nums strong {{ display: block; font-size: 18px; }}
    .nums span, .split li span {{ color: var(--muted); }}
    .split {{
      display: grid;
      grid-template-columns: 1.3fr 0.7fr;
      gap: 28px;
    }}
    .split ul {{ list-style: none; padding: 0; margin: 0; }}
    .split li {{ grid-template-columns: 1fr auto; }}
    .note {{ color: var(--muted); max-width: 70ch; }}
    footer {{ margin-top: 36px; color: var(--muted); font-size: 14px; }}
    a {{ color: var(--teal); }}
    @media (max-width: 720px) {{
      .split {{ grid-template-columns: 1fr; }}
      ol.list li {{ grid-template-columns: auto 1fr; }}
      .nums {{ grid-column: 2; text-align: left; }}
    }}
  </style>
</head>
<body>
<main>
  <p class="eyebrow">CBSE Physics Predictor · Class 12 theory</p>
  <h1>What to study before {_e(analysis.target_year)}.</h1>
  <p class="lede">Concepts are ranked from your local paper tags. The number on each row is the model’s chance the concept appears at least once, not the chance of a particular question, and not your predicted score.</p>
  <p class="banner">Corpus: {_e(analysis.corpus_label)}. {_e(analysis.selection_reason)} Expected marks are the value of covering a concept if it appears as the model expects. They are not a board-score forecast.</p>
  {warning_block}
  <section>
    <h2>Walk-forward check</h2>
    <p class="note">Each test year was scored using only earlier years. Random draw of {analysis.backtest.k} concepts would capture about {_e(_pct(analysis.random_baseline))} of appeared marks. Folds: {_e(evaluated)}. Corpus years: {_e(years)}. Rows: {_e(analysis.row_count)}.</p>
    <div class="metrics">{''.join(metric_cards)}</div>
  </section>
  <section>
    <h2>Highest-ranked concepts</h2>
    <ol class="list">{''.join(rows)}</ol>
  </section>
  <section class="split">
    <div>
      <h2>Study plan, {_e(_num(analysis.plan.hours_budget, 0))} hours</h2>
      <p class="note">Filled by expected marks per hour. A concept is included only when its full study block fits. {_e(_num(analysis.plan.hours_used, 1))} hours used. Covered value: {_e(_num(analysis.plan.expected_marks))} expected marks, not a predicted total.</p>
      <ol class="list">{''.join(plan_rows)}</ol>
    </div>
    <div>
      <h2>Hours by unit group</h2>
      <ul>{group_bits}</ul>
      <h2>What the booster used</h2>
      <p class="note">Importances come from the gradient-boosting fit on years before {_e(analysis.target_year)}. They explain that fit. The selected ranker is {_e(_MODEL_LABELS.get(analysis.selected_model, analysis.selected_model))}.</p>
      <ul>{importance}</ul>
    </div>
  </section>
  <footer>
    <p>Not affiliated with CBSE or NCERT. Question text is not stored in this report.</p>
    <p><a href="https://github.com/ryaneditraj/cbse-physics-predictor">github.com/ryaneditraj/cbse-physics-predictor</a></p>
  </footer>
</main>
</body>
</html>
"""


def _group_bits(analysis: Analysis) -> str:
    totals: dict[str, float] = {}
    for item in analysis.plan.items:
        label = item.ranked.concept.unit_group
        totals[label] = totals.get(label, 0.0) + item.hours
    ordered = sorted(totals.items(), key=lambda pair: (-pair[1], pair[0]))
    if not ordered:
        return "<li><span>Nothing scheduled.</span><strong></strong></li>"
    return "".join(
        f"<li><span>Group {_e(name)}</span><strong>{_e(_num(hours, 1))} h</strong></li>"
        for name, hours in ordered
    )


def write_report(path: Path, analysis: Analysis, *, top: int = 12) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(analysis, top=top), encoding="utf-8")
