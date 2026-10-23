"""Load and validate a local JSONL corpus of concept appearances.

A row records that a concept showed up in one paper. It stores an id, a year,
and optional marks. It does not store question text.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from cbse_physics.taxonomy import Taxonomy

MAX_CORPUS_BYTES = 5_000_000
MAX_ROWS = 50_000
_CONCEPT_ID = re.compile(r"[a-z0-9._-]{1,64}")
_PAPER_SET = re.compile(r"[A-Za-z0-9._ /-]{1,40}")


class CorpusError(ValueError):
    """The corpus file is unreadable or does not match the schema."""


@dataclass(frozen=True)
class Appearance:
    year: int
    paper_set: str
    concept_id: str
    marks: float | None
    source: str
    keyword_hits: int = 0

    def to_json(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "concept_id": self.concept_id,
            "marks": self.marks,
            "paper_set": self.paper_set,
            "source": self.source,
            "year": self.year,
        }
        if self.keyword_hits:
            payload["keyword_hits"] = self.keyword_hits
        return payload


def load_corpus(path: Path, taxonomy: Taxonomy) -> list[Appearance]:
    if not path.is_file():
        raise CorpusError(f"corpus not found: {path.name}")
    size = path.stat().st_size
    if size > MAX_CORPUS_BYTES:
        raise CorpusError(f"corpus exceeds {MAX_CORPUS_BYTES} bytes")
    text = path.read_text(encoding="utf-8")
    rows: list[Appearance] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        if len(rows) >= MAX_ROWS:
            raise CorpusError(f"corpus exceeds {MAX_ROWS} rows")
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CorpusError(f"line {line_no}: invalid JSON") from exc
        rows.append(parse_appearance(payload, line_no, taxonomy))
    if not rows:
        raise CorpusError("corpus has no rows")
    return rows


def parse_appearance(payload: object, line_no: int, taxonomy: Taxonomy) -> Appearance:
    if not isinstance(payload, dict):
        raise CorpusError(f"line {line_no}: expected a JSON object")
    year = payload.get("year")
    if isinstance(year, bool) or not isinstance(year, int) or not 1990 <= year <= 2100:
        raise CorpusError(f"line {line_no}: year must be an integer from 1990 to 2100")
    concept_id = payload.get("concept_id")
    if not isinstance(concept_id, str) or _CONCEPT_ID.fullmatch(concept_id) is None:
        raise CorpusError(f"line {line_no}: concept_id is missing or not a safe id")
    if concept_id not in taxonomy.by_id:
        raise CorpusError(f"line {line_no}: unknown concept_id '{concept_id}'")
    paper_set = payload.get("paper_set", "1")
    if not isinstance(paper_set, str) or _PAPER_SET.fullmatch(paper_set) is None:
        raise CorpusError(f"line {line_no}: paper_set has unsupported characters")
    marks = payload.get("marks", None)
    parsed_marks: float | None
    if marks is None:
        parsed_marks = None
    elif isinstance(marks, bool) or not isinstance(marks, (int, float)) or not 0 < float(marks) <= 70:
        raise CorpusError(f"line {line_no}: marks must be a number from 0 to 70, or null")
    else:
        parsed_marks = float(marks)
    source = payload.get("source", "")
    if not isinstance(source, str) or len(source) > 200:
        raise CorpusError(f"line {line_no}: source must be a short string")
    source_label = Path(source.replace("\\", "/")).name.replace("\n", "").replace("\r", "")
    if len(source_label) > 120:
        source_label = source_label[:117] + "..."
    hits = payload.get("keyword_hits", 0)
    if isinstance(hits, bool) or not isinstance(hits, int) or hits < 0 or hits > 10_000:
        raise CorpusError(f"line {line_no}: keyword_hits must be a non-negative integer")
    return Appearance(
        year=year,
        paper_set=paper_set.strip(),
        concept_id=concept_id,
        marks=parsed_marks,
        source=source_label,
        keyword_hits=hits,
    )


def write_corpus(path: Path, rows: list[Appearance]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(row.to_json(), sort_keys=True, ensure_ascii=True) for row in rows]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


@dataclass(frozen=True)
class YearHit:
    """One concept in one exam year, collapsed across paper sets."""

    marks: float | None
    sets: tuple[str, ...]


def collapse_years(rows: list[Appearance]) -> tuple[list[int], dict[str, dict[int, YearHit]], int]:
    """Collapse paper sets so a concept counts once per year.

    Marks are the maximum recorded among sets. Null marks stay null only when
    every set omitted them. The third return value is how many raw rows omitted
    marks.
    """

    years = sorted({row.year for row in rows})
    buckets: dict[str, dict[int, list[Appearance]]] = {}
    imputed = 0
    for row in rows:
        if row.marks is None:
            imputed += 1
        buckets.setdefault(row.concept_id, {}).setdefault(row.year, []).append(row)
    grid: dict[str, dict[int, YearHit]] = {}
    for concept_id, by_year in buckets.items():
        grid[concept_id] = {}
        for year, group in by_year.items():
            known = [row.marks for row in group if row.marks is not None]
            marks = max(known) if known else None
            sets = tuple(sorted({row.paper_set for row in group}))
            grid[concept_id][year] = YearHit(marks=marks, sets=sets)
    return years, grid, imputed
