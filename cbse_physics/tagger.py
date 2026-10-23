"""Keyword tagger from extracted paper text onto NCERT concept ids.

Matching is case-insensitive and requires a keyword boundary so short tokens
do not fire inside unrelated words. The tagger returns ids only. Callers should
not persist the source text.
"""

from __future__ import annotations

import re

from cbse_physics.taxonomy import Concept, Taxonomy


def _normalize(text: str) -> str:
    return (
        text.casefold()
        .replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2212", "-")
    )


def _pattern(phrase: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(phrase)}(?!\w)")


def _phrases(concept: Concept) -> tuple[str, ...]:
    seen: list[str] = []
    for phrase in concept.keywords:
        normal = _normalize(phrase)
        if normal not in seen:
            seen.append(normal)
    return tuple(seen)


def tag_text(text: str, taxonomy: Taxonomy) -> list[tuple[Concept, int]]:
    if not text or not text.strip():
        return []
    folded = _normalize(text)
    hits: list[tuple[Concept, int]] = []
    for concept in taxonomy.concepts:
        count = 0
        for phrase in _phrases(concept):
            count += len(_pattern(phrase).findall(folded))
        if count:
            hits.append((concept, count))
    hits.sort(key=lambda item: (-item[1], item[0].chapter_number, item[0].id))
    return hits
