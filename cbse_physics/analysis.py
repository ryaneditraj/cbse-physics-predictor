"""Glue the corpus, the ranker, and the study plan into one result."""

from __future__ import annotations

from dataclasses import dataclass, field

from cbse_physics.corpus import Appearance, collapse_years
from cbse_physics.models import (
    MODEL_BAYES,
    Backtest,
    RankedConcept,
    analytic_random_fraction,
    choose_model,
    fit_year,
    walk_forward,
)
from cbse_physics.plan import StudyPlan, build_plan
from cbse_physics.taxonomy import Taxonomy


class AnalysisError(ValueError):
    """The corpus cannot support the requested year or hour budget."""


@dataclass
class Analysis:
    target_year: int
    corpus_label: str
    years: list[int]
    row_count: int
    imputed_mark_rows: int
    selected_model: str
    selection_reason: str
    backtest: Backtest
    ranking: list[RankedConcept]
    plan: StudyPlan
    importances: tuple[tuple[str, float], ...]
    gbdt_fitted: bool
    random_baseline: float
    warnings: list[str] = field(default_factory=list)

    def to_dict(self, top: int) -> dict[str, object]:
        def model_block(name: str) -> dict[str, float | None]:
            return {
                "marks_fraction_at_k": self.backtest.mean_marks_fraction(name),
                "precision_at_k": self.backtest.mean_precision(name),
            }

        return {
            "target_year": self.target_year,
            "corpus_label": self.corpus_label,
            "corpus_years": self.years,
            "row_count": self.row_count,
            "imputed_mark_rows": self.imputed_mark_rows,
            "selected_model": self.selected_model,
            "selection_reason": self.selection_reason,
            "gbdt_fitted": self.gbdt_fitted,
            "warnings": list(self.warnings),
            "backtest": {
                "k": self.backtest.k,
                "evaluated_years": self.backtest.evaluated_years,
                "random_baseline_marks_fraction": self.random_baseline,
                "models": {
                    "empirical_bayes": model_block("empirical_bayes"),
                    "blend": model_block("blend"),
                    "gradient_boosting": model_block("gradient_boosting"),
                    "frequency": model_block("frequency"),
                    "unit_weight": model_block("unit_weight"),
                },
            },
            "ranking": [
                {
                    "id": item.concept.id,
                    "name": item.concept.name,
                    "chapter": item.concept.chapter,
                    "unit_group": item.concept.unit_group,
                    "probability": round(item.probability, 4),
                    "expected_marks": round(item.expected_marks, 3),
                    "ev_per_hour": round(item.ev_per_hour, 3),
                    "study_hours": item.concept.study_hours,
                    "bayes_rate": round(item.bayes_rate, 4),
                }
                for item in self.ranking[:top]
            ],
            "plan": {
                "hours_budget": self.plan.hours_budget,
                "hours_used": round(self.plan.hours_used, 2),
                "expected_marks_covered": round(self.plan.expected_marks, 3),
                "items": [
                    {
                        "id": item.ranked.concept.id,
                        "name": item.ranked.concept.name,
                        "chapter": item.ranked.concept.chapter,
                        "hours": item.hours,
                        "expected_marks": round(item.expected_marks, 3),
                        "ev_per_hour": round(item.ranked.ev_per_hour, 3),
                    }
                    for item in self.plan.items
                ],
            },
        }


def analyze(
    rows: list[Appearance],
    taxonomy: Taxonomy,
    *,
    target_year: int | None,
    hours: float,
    corpus_label: str,
) -> Analysis:
    years, grid, imputed = collapse_years(rows)
    if target_year is None:
        target_year = years[-1] + 1
    if not any(year < target_year for year in years):
        raise AnalysisError(f"no corpus years fall before {target_year}")
    backtest = walk_forward(rows, taxonomy)
    choice = choose_model(backtest)
    fitted = fit_year(years, grid, taxonomy, target_year)
    selected = choice.name
    reason = choice.reason
    if selected != MODEL_BAYES and not fitted.gbdt_fitted:
        selected = MODEL_BAYES
        reason = "Gradient boosting did not fit on this window, so the plan uses empirical Bayes."
    ranking = fitted.by_model[selected]
    warnings: list[str] = []
    if imputed:
        warnings.append(
            f"{imputed} rows did not record marks. Those appearances use the concept's planning weight."
        )
    if target_year in years:
        warnings.append(
            f"{target_year} is already in the corpus. Training uses only earlier years, so this is a hindcast."
        )
    if not backtest.folds:
        warnings.append("This corpus is too short for a walk-forward backtest.")
    return Analysis(
        target_year=target_year,
        corpus_label=corpus_label,
        years=years,
        row_count=len(rows),
        imputed_mark_rows=imputed,
        selected_model=selected,
        selection_reason=reason,
        backtest=backtest,
        ranking=ranking,
        plan=build_plan(ranking, hours),
        importances=fitted.importances,
        gbdt_fitted=fitted.gbdt_fitted,
        random_baseline=analytic_random_fraction(taxonomy, backtest.k),
        warnings=warnings,
    )
