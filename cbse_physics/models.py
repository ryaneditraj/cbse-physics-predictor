"""Empirical Bayes rates, a shallow gradient-boosting ranker, and walk-forward.

Every feature for a label year is computed from earlier years only. The test
year in a walk-forward fold is not in that fold's matrix.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sklearn.ensemble import GradientBoostingClassifier

from cbse_physics.corpus import YearHit, collapse_years
from cbse_physics.corpus import Appearance
from cbse_physics.taxonomy import THEORY_MARKS, Concept, Taxonomy

FEATURE_NAMES: tuple[str, ...] = (
    "bayes_rate",
    "raw_rate",
    "years_since_last",
    "mean_marks",
    "group_mark_share",
    "equal_split_prior",
    "last_year_hit",
    "recent_rate",
)

FEATURE_LABELS: dict[str, str] = {
    "bayes_rate": "Shrunk hit rate",
    "raw_rate": "Raw hit rate",
    "years_since_last": "Years since it last appeared",
    "mean_marks": "Average marks when it appeared",
    "group_mark_share": "Official unit-group share of the paper",
    "equal_split_prior": "That share split evenly across its concepts",
    "last_year_hit": "Appeared in the most recent past year",
    "recent_rate": "Hit rate over the last three years",
}

MODEL_BAYES = "empirical_bayes"
MODEL_GBDT = "gradient_boosting"
MODEL_BLEND = "blend"
MODEL_ORDER = (MODEL_BAYES, MODEL_BLEND, MODEL_GBDT)
TOP_K = 10
MIN_TRAIN_YEARS = 3


@dataclass(frozen=True)
class RankedConcept:
    concept: Concept
    probability: float
    expected_marks: float
    bayes_rate: float
    raw_rate: float
    model: str

    @property
    def ev_per_hour(self) -> float:
        return self.expected_marks / self.concept.study_hours


@dataclass
class FoldScore:
    year: int
    marks_fraction: dict[str, float]
    precision_at_k: dict[str, float]
    marks_available: float


@dataclass
class Backtest:
    folds: list[FoldScore] = field(default_factory=list)
    k: int = TOP_K

    def mean_marks_fraction(self, model: str) -> float | None:
        values = [fold.marks_fraction[model] for fold in self.folds if model in fold.marks_fraction]
        if not values:
            return None
        return sum(values) / len(values)

    def mean_precision(self, model: str) -> float | None:
        values = [fold.precision_at_k[model] for fold in self.folds if model in fold.precision_at_k]
        if not values:
            return None
        return sum(values) / len(values)

    @property
    def evaluated_years(self) -> list[int]:
        return [fold.year for fold in self.folds]


@dataclass(frozen=True)
class ModelChoice:
    name: str
    reason: str


def beta_prior(rates: list[float]) -> tuple[float, float]:
    """Method-of-moments Beta(alpha, beta). Uniform when the sample is too thin."""

    if len(rates) < 2:
        return 1.0, 1.0
    mean = sum(rates) / len(rates)
    variance = sum((rate - mean) ** 2 for rate in rates) / (len(rates) - 1)
    if mean <= 0.01 or mean >= 0.99 or variance <= 1e-8:
        return 1.0, 1.0
    common = mean * (1.0 - mean) / variance - 1.0
    if common <= 0:
        return 1.0, 1.0
    alpha = mean * common
    beta = (1.0 - mean) * common
    if alpha < 0.05 or beta < 0.05 or alpha > 500 or beta > 500:
        return 1.0, 1.0
    return alpha, beta


def posterior_rate(hits: int, trials: int, alpha: float, beta: float) -> float:
    return (hits + alpha) / (trials + alpha + beta)


def _appeared(grid: dict[str, dict[int, YearHit]], concept_id: str, year: int) -> YearHit | None:
    return grid.get(concept_id, {}).get(year)


def _resolved_marks(hit: YearHit | None, concept: Concept) -> float:
    if hit is None:
        return 0.0
    if hit.marks is None:
        return concept.typical_marks
    return hit.marks


def feature_map(
    concept: Concept,
    prior_years: list[int],
    grid: dict[str, dict[int, YearHit]],
    taxonomy: Taxonomy,
    alpha: float,
    beta: float,
    as_of_year: int,
) -> dict[str, float]:
    if not prior_years or as_of_year <= max(prior_years):
        raise ValueError("features require a strictly earlier history")
    hits = [year for year in prior_years if _appeared(grid, concept.id, year) is not None]
    trials = len(prior_years)
    raw = len(hits) / trials
    group = taxonomy.group(concept)
    group_size = len(taxonomy.concepts_in_group(group.id))
    span = float(as_of_year - min(prior_years))
    if hits:
        years_since = (as_of_year - max(hits)) / span
        mark_values = [_resolved_marks(_appeared(grid, concept.id, year), concept) for year in hits]
        mean_marks = sum(mark_values) / len(mark_values)
    else:
        years_since = 1.0
        mean_marks = concept.typical_marks
    recent = prior_years[-3:]
    recent_hits = sum(1 for year in recent if _appeared(grid, concept.id, year) is not None)
    most_recent = prior_years[-1]
    return {
        "bayes_rate": posterior_rate(len(hits), trials, alpha, beta),
        "raw_rate": raw,
        "years_since_last": years_since,
        "mean_marks": mean_marks,
        "group_mark_share": group.marks / THEORY_MARKS,
        "equal_split_prior": (group.marks / group_size) / THEORY_MARKS,
        "last_year_hit": 1.0 if _appeared(grid, concept.id, most_recent) is not None else 0.0,
        "recent_rate": recent_hits / len(recent),
    }


def _vector(values: dict[str, float]) -> list[float]:
    return [values[name] for name in FEATURE_NAMES]


def _rates(prior_years: list[int], grid: dict[str, dict[int, YearHit]], taxonomy: Taxonomy) -> list[float]:
    trials = len(prior_years)
    rates: list[float] = []
    for concept in taxonomy.concepts:
        hits = sum(1 for year in prior_years if _appeared(grid, concept.id, year) is not None)
        rates.append(hits / trials if trials else 0.0)
    return rates


def _examples(
    years: list[int],
    cutoff: int,
    grid: dict[str, dict[int, YearHit]],
    taxonomy: Taxonomy,
) -> tuple[list[list[float]], list[int]]:
    features: list[list[float]] = []
    labels: list[int] = []
    for label_year in years:
        if label_year >= cutoff:
            continue
        prior = [year for year in years if year < label_year]
        if not prior:
            continue
        alpha, beta = beta_prior(_rates(prior, grid, taxonomy))
        for concept in taxonomy.concepts:
            values = feature_map(concept, prior, grid, taxonomy, alpha, beta, label_year)
            features.append(_vector(values))
            labels.append(1 if _appeared(grid, concept.id, label_year) is not None else 0)
    return features, labels


def _fit_gbdt(features: list[list[float]], labels: list[int]) -> GradientBoostingClassifier | None:
    if len(set(labels)) < 2 or len(labels) < 8:
        return None
    model = GradientBoostingClassifier(
        n_estimators=60,
        max_depth=2,
        learning_rate=0.06,
        subsample=0.9,
        min_samples_leaf=2,
        random_state=0,
    )
    model.fit(features, labels)
    return model


def _rank_from_scores(
    scores: dict[str, float],
    expected: dict[str, float],
    bayes: dict[str, float],
    raw: dict[str, float],
    taxonomy: Taxonomy,
    model: str,
) -> list[RankedConcept]:
    ranked = [
        RankedConcept(
            concept=concept,
            probability=scores[concept.id],
            expected_marks=expected[concept.id],
            bayes_rate=bayes[concept.id],
            raw_rate=raw[concept.id],
            model=model,
        )
        for concept in taxonomy.concepts
    ]
    ranked.sort(key=lambda item: (-item.probability, -item.expected_marks, item.concept.id))
    return ranked


@dataclass(frozen=True)
class YearFit:
    by_model: dict[str, list[RankedConcept]]
    importances: tuple[tuple[str, float], ...]
    gbdt_fitted: bool


def fit_year(
    years: list[int],
    grid: dict[str, dict[int, YearHit]],
    taxonomy: Taxonomy,
    target_year: int,
) -> YearFit:
    prior = [year for year in years if year < target_year]
    if not prior:
        raise ValueError(f"no corpus years before {target_year}")
    alpha, beta = beta_prior(_rates(prior, grid, taxonomy))
    bayes_scores: dict[str, float] = {}
    raw_scores: dict[str, float] = {}
    mean_marks: dict[str, float] = {}
    vectors: list[list[float]] = []
    for concept in taxonomy.concepts:
        values = feature_map(concept, prior, grid, taxonomy, alpha, beta, target_year)
        bayes_scores[concept.id] = values["bayes_rate"]
        raw_scores[concept.id] = values["raw_rate"]
        mean_marks[concept.id] = values["mean_marks"]
        vectors.append(_vector(values))

    gbdt_scores = dict(bayes_scores)
    importances: list[tuple[str, float]] = []
    features, labels = _examples(years, target_year, grid, taxonomy)
    model = _fit_gbdt(features, labels)
    fitted = model is not None
    if model is not None:
        probabilities = model.predict_proba(vectors)
        class_index = list(model.classes_).index(1)
        for concept, probability in zip(taxonomy.concepts, probabilities, strict=True):
            gbdt_scores[concept.id] = float(probability[class_index])
        importances = sorted(
            zip(FEATURE_NAMES, (float(value) for value in model.feature_importances_), strict=True),
            key=lambda item: (-item[1], item[0]),
        )

    def expected_for(probabilities: dict[str, float]) -> dict[str, float]:
        return {concept_id: probabilities[concept_id] * mean_marks[concept_id] for concept_id in probabilities}

    blend = {
        concept.id: 0.5 * bayes_scores[concept.id] + 0.5 * gbdt_scores[concept.id]
        for concept in taxonomy.concepts
    }
    scorebook = {MODEL_BAYES: bayes_scores, MODEL_GBDT: gbdt_scores, MODEL_BLEND: blend}
    by_model = {
        name: _rank_from_scores(scores, expected_for(scores), bayes_scores, raw_scores, taxonomy, name)
        for name, scores in scorebook.items()
    }
    return YearFit(by_model=by_model, importances=tuple(importances), gbdt_fitted=fitted)


def rank_year(
    years: list[int],
    grid: dict[str, dict[int, YearHit]],
    taxonomy: Taxonomy,
    target_year: int,
    model_name: str,
) -> tuple[list[RankedConcept], list[tuple[str, float]]]:
    fitted = fit_year(years, grid, taxonomy, target_year)
    return fitted.by_model[model_name], list(fitted.importances)


def _truth(
    grid: dict[str, dict[int, YearHit]],
    taxonomy: Taxonomy,
    year: int,
) -> dict[str, float]:
    marks: dict[str, float] = {}
    for concept in taxonomy.concepts:
        hit = _appeared(grid, concept.id, year)
        marks[concept.id] = 0.0 if hit is None else _resolved_marks(hit, concept)
    return marks


def _marks_fraction(ranking: list[RankedConcept], truth: dict[str, float], k: int) -> float:
    total = sum(truth.values())
    if total <= 0:
        return 0.0
    captured = sum(truth[item.concept.id] for item in ranking[:k])
    return captured / total


def _precision(ranking: list[RankedConcept], truth: dict[str, float], k: int) -> float:
    if k <= 0:
        return 0.0
    hits = sum(1 for item in ranking[:k] if truth[item.concept.id] > 0)
    return hits / k


def walk_forward(
    rows: list[Appearance],
    taxonomy: Taxonomy,
    *,
    k: int = TOP_K,
    min_train_years: int = MIN_TRAIN_YEARS,
) -> Backtest:
    years, grid, _imputed = collapse_years(rows)
    backtest = Backtest(k=k)
    for test_year in years:
        train_years = [year for year in years if year < test_year]
        if len(train_years) < min_train_years:
            continue
        if max(train_years) >= test_year:
            raise RuntimeError("walk-forward leaked the test year")
        truth = _truth(grid, taxonomy, test_year)
        fold = FoldScore(year=test_year, marks_fraction={}, precision_at_k={}, marks_available=sum(truth.values()))
        fitted = fit_year(years, grid, taxonomy, test_year)
        for model_name in MODEL_ORDER:
            ranking = fitted.by_model[model_name]
            fold.marks_fraction[model_name] = _marks_fraction(ranking, truth, k)
            fold.precision_at_k[model_name] = _precision(ranking, truth, k)
        weight_ranking = sorted(
            taxonomy.concepts,
            key=lambda concept: (-taxonomy.group(concept).marks, concept.chapter_number, concept.id),
        )
        weight_as_ranked = [
            RankedConcept(concept, 0.0, 0.0, 0.0, 0.0, "unit_weight") for concept in weight_ranking
        ]
        fold.marks_fraction["unit_weight"] = _marks_fraction(weight_as_ranked, truth, k)
        fold.precision_at_k["unit_weight"] = _precision(weight_as_ranked, truth, k)
        frequency_ranked = sorted(fitted.by_model[MODEL_BAYES], key=lambda item: (-item.raw_rate, item.concept.id))
        fold.marks_fraction["frequency"] = _marks_fraction(frequency_ranked, truth, k)
        fold.precision_at_k["frequency"] = _precision(frequency_ranked, truth, k)
        backtest.folds.append(fold)
    return backtest


def choose_model(backtest: Backtest) -> ModelChoice:
    if not backtest.folds:
        return ModelChoice(MODEL_BAYES, "Not enough earlier years for a walk-forward check, so the plan uses empirical Bayes.")
    scored = [(name, backtest.mean_marks_fraction(name)) for name in MODEL_ORDER]
    available = [(name, score) for name, score in scored if score is not None]
    available.sort(key=lambda item: (-item[1], MODEL_ORDER.index(item[0])))
    winner, score = available[0]
    tied = [name for name, other in available if abs(other - score) <= 1e-12]
    # MODEL_ORDER already prefers the simpler model on an exact tie because
    # available is sorted by score then by that order, and Bayes is first.
    if len(tied) > 1 and winner == MODEL_BAYES:
        return ModelChoice(
            winner,
            f"Walk-forward marks captured in the top {backtest.k} were tied, so the simpler empirical Bayes ranker is used.",
        )
    label = {
        MODEL_BAYES: "empirical Bayes",
        MODEL_GBDT: "gradient boosting",
        MODEL_BLEND: "the Bayes and gradient-boosting blend",
    }[winner]
    return ModelChoice(
        winner,
        f"Walk-forward selected {label}: it captured the largest share of marks inside the top {backtest.k} concepts.",
    )


def analytic_random_fraction(taxonomy: Taxonomy, k: int = TOP_K) -> float:
    """Expected top-k marks share if concepts were drawn uniformly."""

    count = len(taxonomy.concepts)
    if count == 0:
        return 0.0
    return min(k, count) / count
