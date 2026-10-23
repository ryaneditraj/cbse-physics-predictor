import json
import os
from pathlib import Path

import pytest
from pypdf import PdfWriter

from cbse_physics.analysis import analyze
from cbse_physics.cli import main
from cbse_physics.corpus import Appearance, CorpusError, load_corpus, parse_appearance, write_corpus
from cbse_physics.extract import ExtractError, collect_pdfs, extract_pdf_text
from cbse_physics.fixture import FIXTURE_YEARS, build_fixture_rows, fixture_path
from cbse_physics.corpus import collapse_years as collapse
from cbse_physics.models import beta_prior, feature_map, posterior_rate, walk_forward
from cbse_physics.plan import build_plan
from cbse_physics.report import render_report
from cbse_physics.tagger import tag_text
from cbse_physics.taxonomy import DEFAULT_TAXONOMY, THEORY_MARKS
from tests.pdfutil import make_pdf


def test_taxonomy_covers_the_theory_paper():
    assert sum(group.marks for group in DEFAULT_TAXONOMY.groups) == THEORY_MARKS == 70
    assert len(DEFAULT_TAXONOMY.concepts) >= 30
    assert {concept.chapter_number for concept in DEFAULT_TAXONOMY.concepts} == set(range(1, 15))


def test_tagger_hits_specific_concepts_and_ignores_loose_words():
    text = (
        "Apply Gauss's theorem to a uniformly charged infinite plane sheet. "
        "A later question asks for the fringe width in Young's double slit experiment."
    )
    ids = [concept.id for concept, _hits in tag_text(text, DEFAULT_TAXONOMY)]
    assert "ch01.gauss_law" in ids
    assert "ch10.ydse" in ids
    assert "ch03.drift_ohm" not in ids

    assert tag_text("The current affairs club met on Friday.", DEFAULT_TAXONOMY) == []
    curly = "State Faraday’s law and Lenz’s law for an induced emf."
    curly_ids = [concept.id for concept, _hits in tag_text(curly, DEFAULT_TAXONOMY)]
    assert "ch06.faraday_lenz" in curly_ids


def test_beta_prior_shrinks_a_small_sample():
    alpha, beta = beta_prior([0.5, 0.5, 0.5, 0.5])
    assert alpha == pytest.approx(1.0)
    assert beta == pytest.approx(1.0)
    rates = [0.2, 0.8, 0.2, 0.8]
    alpha, beta = beta_prior(rates)
    assert posterior_rate(3, 4, alpha, beta) < 0.75


def test_features_ignore_the_year_being_predicted():
    rows = [
        Appearance(year, "A", "ch02.capacitance", 5, "notes")
        for year in range(2018, 2025)
    ]
    rows.append(Appearance(2024, "A", "ch01.gauss_law", 5, "notes"))
    years, grid, _imputed = collapse(rows)
    concept = DEFAULT_TAXONOMY.by_id["ch01.gauss_law"]
    prior = [year for year in years if year < 2024]
    before = feature_map(concept, prior, grid, DEFAULT_TAXONOMY, 1, 1, 2024)
    assert before["raw_rate"] == 0
    assert before["last_year_hit"] == 0
    after_prior = [year for year in years if year < 2025]
    after = feature_map(concept, after_prior, grid, DEFAULT_TAXONOMY, 1, 1, 2025)
    assert after["last_year_hit"] == 1
    assert after["raw_rate"] > 0


def test_a_concept_that_always_appears_ranks_first():
    rows = [Appearance(year, "A", "ch01.gauss_law", 5, "notes") for year in range(2016, 2026)]
    result = analyze(rows, DEFAULT_TAXONOMY, target_year=2026, hours=6, corpus_label="unit")
    assert result.ranking[0].concept.id == "ch01.gauss_law"
    assert result.plan.hours_used <= 6
    assert result.backtest.folds
    assert all(fold.year >= 2019 for fold in result.backtest.folds)


def test_walk_forward_training_years_stay_in_the_past():
    rows = build_fixture_rows()
    backtest = walk_forward(rows, DEFAULT_TAXONOMY)
    assert backtest.evaluated_years
    assert backtest.evaluated_years[0] >= FIXTURE_YEARS[0] + 3
    best = max(
        backtest.mean_marks_fraction(name) or 0
        for name in ("empirical_bayes", "blend", "gradient_boosting")
    )
    random_share = 10 / len(DEFAULT_TAXONOMY.concepts)
    assert best > random_share


def test_plan_respects_the_hour_budget():
    rows = build_fixture_rows()
    result = analyze(rows, DEFAULT_TAXONOMY, target_year=None, hours=12, corpus_label="fixture")
    assert result.target_year == FIXTURE_YEARS[-1] + 1
    assert result.plan.hours_used <= 12 + 1e-9
    assert result.plan.hours_used == pytest.approx(sum(item.hours for item in result.plan.items))
    assert all(item.hours <= 12 for item in result.plan.items)


def test_report_escapes_markup():
    rows = build_fixture_rows()
    result = analyze(rows, DEFAULT_TAXONOMY, target_year=2026, hours=8, corpus_label="fixture")
    result.corpus_label = '<script>alert(1)</script>'
    result.warnings.append('<img src=x onerror=alert(1)> {broke}')
    page = render_report(result)
    assert "<script" not in page.lower()
    assert "<img" not in page.lower()
    assert "&lt;script&gt;" in page
    assert "&lt;img" in page
    assert "&#123;broke&#125;" in page
    assert "not a board-score forecast" in page
    assert 'content="noindex' in page


def test_corpus_rejects_bad_rows_and_strips_paths(tmp_path: Path):
    with pytest.raises(CorpusError):
        parse_appearance({"year": True, "concept_id": "ch01.gauss_law"}, 1, DEFAULT_TAXONOMY)
    with pytest.raises(CorpusError):
        parse_appearance(
            {"year": 2024, "concept_id": "nope", "paper_set": "A"},
            3,
            DEFAULT_TAXONOMY,
        )
    row = parse_appearance(
        {
            "year": 2024,
            "concept_id": "ch01.gauss_law",
            "paper_set": "A",
            "source": "/home/student/secret/paper.pdf",
            "marks": 5,
        },
        1,
        DEFAULT_TAXONOMY,
    )
    assert row.source == "paper.pdf"
    path = tmp_path / "corpus.jsonl"
    write_corpus(path, [row])
    loaded = load_corpus(path, DEFAULT_TAXONOMY)
    assert loaded[0].concept_id == "ch01.gauss_law"


def test_directory_scan_skips_symlinks_that_leave_the_folder(tmp_path: Path):
    root = tmp_path / "papers"
    root.mkdir()
    outside = tmp_path / "outside.pdf"
    outside.write_bytes(make_pdf("Gauss's theorem"))
    (root / "linked.pdf").symlink_to(outside)
    assert collect_pdfs(root) == []
    assert collect_pdfs(outside) == [outside.resolve()]


def test_pdf_round_trip_and_ingest(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    pdf = tmp_path / "physics-2024.pdf"
    pdf.write_bytes(make_pdf("Use the lens maker formula for a thin lens in contact."))
    assert "lens maker" in extract_pdf_text(pdf).lower()
    out = tmp_path / "appearances.jsonl"
    code = main(["ingest", str(pdf), "--year", "2024", "--set", "1", "--out", str(out)])
    assert code == 0
    rows = load_corpus(out, DEFAULT_TAXONOMY)
    assert any(row.concept_id == "ch09.lenses" for row in rows)
    assert all(row.source == "physics-2024.pdf" for row in rows)
    again = main(["ingest", str(pdf), "--year", "2024", "--out", str(out)])
    assert again == 1
    captured = capsys.readouterr()
    assert "already exists" in captured.err


def test_unsafe_ocr_command_is_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    blank = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with blank.open("wb") as handle:
        writer.write(handle)
    monkeypatch.setenv("CBSE_PHYSICS_OCR", "1")
    monkeypatch.setenv("CBSE_PHYSICS_TESSERACT_CMD", "tesseract; rm -rf /tmp/nope")
    with pytest.raises(ExtractError, match="plain path"):
        extract_pdf_text(blank)
    monkeypatch.setenv("CBSE_PHYSICS_TESSERACT_CMD", "tesseract && whoami")
    with pytest.raises(ExtractError, match="plain path"):
        extract_pdf_text(blank)


def test_cli_demo_json(capsys: pytest.CaptureFixture[str]):
    code = main(["demo", "--json", "--out", os.devnull, "--hours", "10", "--top", "5"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["target_year"] == 2026
    assert payload["selected_model"] in {"empirical_bayes", "blend", "gradient_boosting"}
    assert len(payload["ranking"]) == 5
    assert payload["plan"]["hours_used"] <= 10
    assert "fixture" in payload["corpus_label"]


def test_fixture_file_matches_the_generator():
    path = fixture_path()
    assert path.is_file()
    on_disk = load_corpus(path, DEFAULT_TAXONOMY)
    generated = build_fixture_rows()
    assert [(row.year, row.paper_set, row.concept_id, row.marks, row.source) for row in on_disk] == [
        (row.year, row.paper_set, row.concept_id, row.marks, row.source) for row in generated
    ]


def test_checked_in_sample_report_matches_the_fixture_backtest():
    page = (Path(__file__).resolve().parents[1] / "docs" / "sample-report.html").read_text(encoding="utf-8")
    assert "35.8%" in page
    assert "deterministic fixture" in page
    assert "not a board-score forecast" in page
    assert "<script" not in page.lower()


def test_repo_has_no_obvious_secrets():
    root = Path(__file__).resolve().parents[1]
    patterns = ("AKIA", "-----BEGIN ", "ghp_", "xoxb-")
    skip = {".git", ".venv", "__pycache__", "out", ".pytest_cache", "node_modules"}
    for path in root.rglob("*"):
        if not path.is_file() or any(part in skip for part in path.parts):
            continue
        if path.suffix not in {".py", ".yml", ".yaml", ".toml", ".json", ".jsonl", ".md", ".html", ".txt"}:
            continue
        if path.name == "test_predictor.py":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            assert pattern not in text, f"{pattern} found in {path}"
