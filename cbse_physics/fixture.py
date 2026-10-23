"""Deterministic fixture corpus.

The draws are a simulator so `cbse-physics demo` works offline and the
backtest is reproducible. They are not a transcription of CBSE papers, and the
year labels are simulator indexes rather than claims about a real sitting.
"""

from __future__ import annotations

import random
from pathlib import Path

from cbse_physics.corpus import Appearance, write_corpus
from cbse_physics.taxonomy import DEFAULT_TAXONOMY, Concept

FIXTURE_YEARS = tuple(range(2016, 2026))
FIXTURE_SETS = ("A", "B")
STAPLES = frozenset(
    {
        "ch01.gauss_law",
        "ch02.capacitance",
        "ch03.cells_kirchhoff",
        "ch04.galvanometer",
        "ch06.faraday_lenz",
        "ch07.lcr",
        "ch09.lenses",
        "ch10.ydse",
        "ch11.photoelectric",
        "ch14.diode",
    }
)
RARES = frozenset(
    {
        "ch02.dielectrics",
        "ch05.materials",
        "ch08.spectrum",
        "ch09.prism",
        "ch12.spectra",
    }
)


def fixture_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "fixture_appearances.jsonl"


def _probability(concept: Concept, year: int) -> float:
    group_marks = {1: 16, 2: 16, 3: 16, 4: 17, 5: 17, 6: 17, 7: 17, 8: 18, 9: 18, 10: 18, 11: 12, 12: 12, 13: 12, 14: 7}[
        concept.chapter_number
    ]
    probability = 0.07 + 0.28 * (group_marks / 18)
    hot_chapter = ((year - FIXTURE_YEARS[0]) % 14) + 1
    if concept.chapter_number == hot_chapter:
        probability += 0.24
    if concept.id in STAPLES:
        probability += 0.16
    if concept.id in RARES:
        probability -= 0.05
    return min(0.72, max(0.03, probability))


def build_fixture_rows() -> list[Appearance]:
    rows: list[Appearance] = []
    for year in FIXTURE_YEARS:
        for paper_set in FIXTURE_SETS:
            for concept in DEFAULT_TAXONOMY.concepts:
                generator = random.Random(f"{year}:{paper_set}:{concept.id}")
                if generator.random() > _probability(concept, year):
                    continue
                marks = float(concept.typical_marks)
                if generator.random() < 0.25:
                    marks = float(generator.choice((1, 2, 3, 5)))
                rows.append(
                    Appearance(
                        year=year,
                        paper_set=paper_set,
                        concept_id=concept.id,
                        marks=marks,
                        source="fixture",
                    )
                )
    rows.sort(key=lambda row: (row.year, row.paper_set, row.concept_id))
    return rows


def write_fixture(path: Path | None = None) -> Path:
    destination = path or fixture_path()
    write_corpus(destination, build_fixture_rows())
    return destination
