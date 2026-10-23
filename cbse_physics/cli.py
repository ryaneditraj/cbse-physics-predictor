"""Command-line interface for the CBSE Physics Predictor."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.text import Text

from cbse_physics import __version__
from cbse_physics.analysis import Analysis, AnalysisError, analyze
from cbse_physics.corpus import Appearance, CorpusError, load_corpus, write_corpus
from cbse_physics.extract import ExtractError, collect_pdfs, extract_pdf_text
from cbse_physics.fixture import fixture_path
from cbse_physics.report import write_report
from cbse_physics.tagger import tag_text
from cbse_physics.taxonomy import DEFAULT_TAXONOMY

FIXTURE_LABEL = "deterministic fixture, not a transcription of CBSE papers"
_MODEL_LABELS = {
    "empirical_bayes": "Empirical Bayes",
    "blend": "Bayes + boosting",
    "gradient_boosting": "Gradient boosting",
    "frequency": "Raw frequency",
    "unit_weight": "Official unit weight",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cbse-physics",
        description=(
            "Rank NCERT Class 12 Physics concepts from your own question-paper tags, "
            "check the ranker with a walk-forward backtest, and build an hour-budget study plan."
        ),
    )
    parser.add_argument("--version", action="version", version=f"cbse-physics {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="Run the offline fixture and write an HTML report")
    demo.add_argument("--year", type=int, help="Year to rank. Defaults to the year after the fixture.")
    demo.add_argument("--hours", type=float, default=20, help="Study-plan budget in hours")
    demo.add_argument("--top", type=int, default=12)
    demo.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    demo.add_argument("--out", type=Path, default=Path("out/report.html"))
    demo.add_argument("--svg", type=Path, help="Also write a Rich SVG of this terminal view")
    demo.set_defaults(func=_cmd_demo)

    predict = sub.add_parser("predict", help="Rank concepts for a target year")
    _add_output_flags(predict, default_out=None)
    predict.set_defaults(func=_cmd_predict)

    backtest = sub.add_parser("backtest", help="Walk-forward check of the rankers")
    _add_corpus_flags(backtest)
    backtest.add_argument("--json", action="store_true")
    backtest.set_defaults(func=_cmd_backtest)

    plan = sub.add_parser("plan", help="Build an expected-value study plan")
    _add_corpus_flags(plan)
    plan.add_argument("--json", action="store_true")
    plan.set_defaults(func=_cmd_plan)

    report = sub.add_parser("report", help="Write a self-contained HTML report")
    _add_corpus_flags(report)
    report.add_argument("--out", type=Path, required=True)
    report.set_defaults(func=_cmd_report)

    ingest = sub.add_parser("ingest", help="Tag concepts in local PDFs and append JSONL rows")
    ingest.add_argument("path", type=Path, help="A PDF, or a directory of PDFs")
    ingest.add_argument("--year", type=int, help="Exam year shared by every PDF in this run")
    ingest.add_argument(
        "--year-from-name",
        action="store_true",
        help="Read a 19xx or 20xx year from each file name",
    )
    ingest.add_argument("--set", default="1", dest="paper_set", help="Paper-set label stored with each row")
    ingest.add_argument("--out", type=Path, default=Path("out/appearances.jsonl"))
    ingest.add_argument("--append", action="store_true")
    ingest.add_argument("--force", action="store_true", help="Overwrite --out if it already exists")
    ingest.add_argument("--dry-run", action="store_true", help="Print tags without writing")
    ingest.set_defaults(func=_cmd_ingest)
    return parser


def _add_corpus_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--corpus", type=Path, help="JSONL corpus. Defaults to the built-in fixture.")
    parser.add_argument("--year", type=int, help="Year to rank. Defaults to the year after the corpus.")
    parser.add_argument("--hours", type=float, default=20, help="Study-plan budget in hours")
    parser.add_argument("--top", type=int, default=12)


def _add_output_flags(parser: argparse.ArgumentParser, default_out: Path | None) -> None:
    _add_corpus_flags(parser)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    if default_out is None:
        parser.add_argument("--out", type=Path, help="Optional HTML report path")
    else:
        parser.add_argument("--out", type=Path, default=default_out)


def _corpus_from_args(args: argparse.Namespace) -> tuple[list[Appearance], str]:
    if args.corpus is None:
        path = fixture_path()
        if not path.is_file():
            raise CorpusError("built-in fixture is missing")
        return load_corpus(path, DEFAULT_TAXONOMY), FIXTURE_LABEL
    rows = load_corpus(args.corpus, DEFAULT_TAXONOMY)
    return rows, f"user file {args.corpus.name}"


def _analyze_args(args: argparse.Namespace) -> Analysis:
    rows, label = _corpus_from_args(args)
    hours = getattr(args, "hours", 20)
    top = getattr(args, "top", 12)
    if hours <= 0:
        raise AnalysisError("--hours must be positive")
    if top <= 0:
        raise AnalysisError("--top must be positive")
    args.hours = hours
    args.top = top
    return analyze(
        rows,
        DEFAULT_TAXONOMY,
        target_year=args.year,
        hours=args.hours,
        corpus_label=label,
    )


def _print_human(analysis: Analysis, console: Console, top: int) -> None:
    console.print(Text("CBSE Physics Predictor", style="bold"))
    console.print(f"Class 12 theory  ·  target {analysis.target_year}  ·  {analysis.corpus_label}")
    for warning in analysis.warnings:
        console.print(f"note: {warning}", style="yellow")
    console.print(analysis.selection_reason)
    console.print(
        "Expected marks are the value of covering a concept, not a predicted board score."
    )

    table = Table(title=f"Walk-forward, top {analysis.backtest.k}", header_style="bold")
    table.add_column("Ranker")
    table.add_column("Marks captured", justify="right")
    table.add_column("Precision", justify="right")
    for name in ("empirical_bayes", "blend", "gradient_boosting", "frequency", "unit_weight"):
        mark = "→ " if name == analysis.selected_model else ""
        fraction = analysis.backtest.mean_marks_fraction(name)
        precision = analysis.backtest.mean_precision(name)
        table.add_row(
            f"{mark}{_MODEL_LABELS[name]}",
            "—" if fraction is None else f"{fraction * 100:.1f}%",
            "—" if precision is None else f"{precision * 100:.1f}%",
        )
    table.add_row("Uniform random", f"{analysis.random_baseline * 100:.1f}%", "—")
    console.print(table)

    ranking = Table(title=f"Top concepts for {analysis.target_year}", header_style="bold")
    ranking.add_column("#", justify="right")
    ranking.add_column("Concept")
    ranking.add_column("Chapter")
    ranking.add_column("P(appears)", justify="right")
    ranking.add_column("E[marks]", justify="right")
    for index, item in enumerate(analysis.ranking[:top], start=1):
        ranking.add_row(
            str(index),
            item.concept.name,
            item.concept.chapter,
            f"{item.probability * 100:.1f}%",
            f"{item.expected_marks:.2f}",
        )
    console.print(ranking)

    plan = Table(
        title=f"Study plan · {analysis.plan.hours_used:.1f} / {analysis.plan.hours_budget:.0f} h",
        header_style="bold",
    )
    plan.add_column("Hours", justify="right")
    plan.add_column("Concept")
    plan.add_column("Marks / hour", justify="right")
    plan.add_column("Expected marks", justify="right")
    for item in analysis.plan.items:
        plan.add_row(
            f"{item.hours:.1f}",
            item.ranked.concept.name,
            f"{item.ranked.ev_per_hour:.2f}",
            f"{item.expected_marks:.2f}",
        )
    console.print(plan)
    console.print(
        f"Covered value: {analysis.plan.expected_marks:.2f} expected marks across the scheduled concepts."
    )


def _emit(analysis: Analysis, args: argparse.Namespace, console: Console) -> int:
    out = getattr(args, "out", None)
    if out is not None:
        write_report(out, analysis, top=args.top)
    if args.json:
        json.dump(analysis.to_dict(args.top), sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        _print_human(analysis, console, args.top)
    svg = getattr(args, "svg", None)
    if svg is not None:
        svg.parent.mkdir(parents=True, exist_ok=True)
        console.save_svg(str(svg), title="cbse-physics demo")
        _strip_remote_svg_fonts(svg)
    if out is not None:
        print(f"Wrote {out}", file=sys.stderr)
    if svg is not None:
        print(f"Wrote {svg}", file=sys.stderr)
    return 0


def _cmd_demo(args: argparse.Namespace, console: Console) -> int:
    args.corpus = None
    return _emit(_analyze_args(args), args, console)


def _cmd_predict(args: argparse.Namespace, console: Console) -> int:
    return _emit(_analyze_args(args), args, console)


def _cmd_backtest(args: argparse.Namespace, console: Console) -> int:
    analysis = _analyze_args(args)
    if args.json:
        payload = analysis.to_dict(analysis.backtest.k)["backtest"]
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    _print_human(analysis, console, top=5)
    return 0


def _cmd_plan(args: argparse.Namespace, console: Console) -> int:
    analysis = _analyze_args(args)
    if args.json:
        json.dump(analysis.to_dict(args.top)["plan"], sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    _print_human(analysis, console, args.top)
    return 0


def _cmd_report(args: argparse.Namespace, console: Console) -> int:
    analysis = _analyze_args(args)
    write_report(args.out, analysis, top=args.top)
    console.print(f"Wrote {args.out}")
    return 0


def _year_from_name(path: Path) -> int | None:
    for token in path.stem.replace("_", " ").replace("-", " ").split():
        if len(token) == 4 and token.isdigit() and token.startswith(("19", "20")):
            return int(token)
    return None


def _strip_remote_svg_fonts(path: Path) -> None:
    """Rich embeds a CDN font. Drop those URLs so the SVG does not fetch remotely."""

    text = path.read_text(encoding="utf-8")
    text = re.sub(r"\s*url\(\"https?://[^\"]+\"\)(?:\s*format\(\"[^\"]+\"\))?,?", "", text)
    text = text.replace("https://www.textualize.io", "textualize.io")
    path.write_text(text, encoding="utf-8")


def _safe_name(path: Path) -> str:
    cleaned = "".join(char if char.isprintable() else " " for char in path.name)
    cleaned = cleaned.replace("\n", " ").replace("\r", " ").strip()
    return (cleaned or "paper.pdf")[:120]


def _cmd_ingest(args: argparse.Namespace, console: Console) -> int:
    if args.year is None and not args.year_from_name:
        raise ExtractError("pass --year, or --year-from-name")
    if args.year is not None and not 1990 <= args.year <= 2100:
        raise ExtractError("--year must be from 1990 to 2100")
    if re.fullmatch(r"[A-Za-z0-9._ /-]{1,40}", args.paper_set) is None:
        raise ExtractError("--set has unsupported characters")
    pdfs = collect_pdfs(args.path)
    if not pdfs:
        raise ExtractError("no PDFs found")
    rows: list[Appearance] = []
    untagged: list[str] = []
    for pdf in pdfs:
        label = _safe_name(pdf)
        year = args.year if args.year is not None else _year_from_name(pdf)
        if year is None:
            raise ExtractError(f"no year in the file name: {label}")
        text = extract_pdf_text(pdf)
        tagged = tag_text(text, DEFAULT_TAXONOMY)
        if not tagged:
            untagged.append(label)
            console.print(f"{label}: no concepts tagged")
            continue
        console.print(f"{label}: {len(tagged)} concepts")
        for concept, hits in tagged:
            rows.append(
                Appearance(
                    year=year,
                    paper_set=args.paper_set.strip(),
                    concept_id=concept.id,
                    marks=None,
                    source=label,
                    keyword_hits=hits,
                )
            )
            if args.dry_run:
                console.print(f"  {concept.id}  ({hits})")
    if args.dry_run:
        console.print(f"dry run: {len(rows)} tags, nothing written")
        return 0 if rows else 1
    if not rows:
        raise ExtractError("no concepts tagged. Nothing was written.")
    if args.out.exists() and not args.append and not args.force:
        raise ExtractError(f"{args.out} already exists. Pass --append or --force.")
    existing: list[Appearance] = []
    if args.append and args.out.exists():
        existing = load_corpus(args.out, DEFAULT_TAXONOMY)
    write_corpus(args.out, existing + rows)
    console.print(f"Wrote {len(rows)} rows to {args.out}")
    if untagged:
        console.print(f"{len(untagged)} files had no tags.", style="yellow")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    record = getattr(args, "svg", None) is not None
    if record:
        console = Console(record=True, width=108, force_terminal=True)
    else:
        console = Console()
    try:
        return int(args.func(args, console))
    except (CorpusError, AnalysisError, ExtractError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
