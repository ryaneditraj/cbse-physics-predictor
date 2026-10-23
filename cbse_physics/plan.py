"""Turn a concept ranking into an hour-budget study plan.

Expected marks are P(appears) times the average marks when it appeared.
Their sum is the value of covering those concepts, not a predicted board score.
"""

from __future__ import annotations

from dataclasses import dataclass

from cbse_physics.models import RankedConcept
from cbse_physics.taxonomy import Taxonomy


@dataclass(frozen=True)
class PlanItem:
    ranked: RankedConcept
    hours: float

    @property
    def expected_marks(self) -> float:
        return self.ranked.expected_marks


@dataclass(frozen=True)
class StudyPlan:
    items: tuple[PlanItem, ...]
    hours_budget: float
    hours_used: float

    @property
    def expected_marks(self) -> float:
        return sum(item.expected_marks for item in self.items)

    def hours_by_group(self, taxonomy: Taxonomy) -> list[tuple[str, float]]:
        totals: dict[str, float] = {}
        for item in self.items:
            group = taxonomy.group(item.ranked.concept)
            totals[group.name] = totals.get(group.name, 0.0) + item.hours
        return sorted(totals.items(), key=lambda pair: (-pair[1], pair[0]))


def build_plan(ranking: list[RankedConcept], hours: float) -> StudyPlan:
    if hours <= 0:
        raise ValueError("hours must be positive")
    remaining = hours
    chosen: list[PlanItem] = []
    ordered = sorted(ranking, key=lambda item: (-item.ev_per_hour, item.concept.id))
    for ranked in ordered:
        needed = ranked.concept.study_hours
        if needed <= remaining + 1e-9:
            chosen.append(PlanItem(ranked=ranked, hours=needed))
            remaining -= needed
    items = tuple(sorted(chosen, key=lambda item: (-item.ranked.ev_per_hour, item.ranked.concept.id)))
    used = hours - remaining
    return StudyPlan(items=items, hours_budget=hours, hours_used=used)
