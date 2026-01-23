from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from money_map.core.model import Variant
from money_map.domain.activity_profile import role_family_label


@dataclass(frozen=True)
class NormalizedVariant:
    id: str
    title: str
    kind: str
    mechanism_id: str
    matrix_cells: list[str]
    matrix_cell: str | None
    risk: str
    activity: str
    scalability: str
    classifiers: dict[str, list[str]]
    summary: str
    description: str
    linked_bridges: list[str]
    linked_route: str | None
    hints_fit: list[str]
    hints_not_fit: list[str]
    first_steps: list[str]
    common_mistakes: list[str]
    outside_market: bool
    success_metrics: list[str]
    related_variant_ids: list[str]
    notes: str | None
    activity_role_family: str
    raw: Variant


@dataclass(frozen=True)
class MatchResult:
    variant: NormalizedVariant
    score: float
    reasons: list[str]
    classifier_match_count: int
    classifier_group_count: int
    data_coverage: int


def normalize_variant(variant: Variant) -> NormalizedVariant:
    summary = variant.notes or "Описание уточняется."
    description = variant.notes or "Подробное описание пока не заполнено."
    return NormalizedVariant(
        id=variant.id,
        title=variant.title,
        kind=variant.kind,
        mechanism_id=variant.primary_way_id,
        matrix_cells=list(variant.matrix_cells),
        matrix_cell=variant.matrix_cells[0] if variant.matrix_cells else None,
        risk=variant.risk_level,
        activity=variant.activity,
        scalability=variant.scalability,
        classifiers={
            "sell": list(variant.sell_tags),
            "to_whom": list(variant.to_whom_tags),
            "measure": list(variant.value_tags),
        },
        summary=summary,
        description=description,
        linked_bridges=list(variant.bridge_ids),
        linked_route=variant.route_ids[0] if variant.route_ids else None,
        hints_fit=list(variant.requirements),
        hints_not_fit=[],
        first_steps=list(variant.first_steps),
        common_mistakes=[],
        outside_market=variant.outside_market,
        success_metrics=list(variant.success_metrics),
        related_variant_ids=list(variant.related_variant_ids),
        notes=variant.notes,
        activity_role_family=variant.activity_profile.role_family,
        raw=variant,
    )


def apply_global_filters(
    variants: Iterable[NormalizedVariant],
    *,
    risk: str,
    activity: str,
    scalability: str,
) -> list[NormalizedVariant]:
    results = list(variants)
    if risk != "all":
        results = [variant for variant in results if variant.risk == risk]
    if activity != "all":
        results = [variant for variant in results if variant.activity == activity]
    if scalability != "all":
        results = [variant for variant in results if variant.scalability == scalability]
    return results


def data_coverage_score(variant: NormalizedVariant) -> int:
    score = 0
    if variant.summary:
        score += 1
    if variant.description:
        score += 1
    if variant.first_steps:
        score += 1
    if variant.hints_fit:
        score += 1
    if variant.common_mistakes:
        score += 1
    if variant.success_metrics:
        score += 1
    if variant.linked_bridges:
        score += 1
    if variant.related_variant_ids:
        score += 1
    return min(score, 5)


def match_score(
    variant: NormalizedVariant,
    *,
    selected_mechanism_ids: list[str],
    selected_matrix_cell: str | None,
    selected_classifiers: dict[str, list[str]],
    selected_route_cells: list[str] | None,
    selected_bridge_ids: list[str],
    selected_role_families: list[str],
    strict: bool,
) -> MatchResult | None:
    score = 0.0
    reasons: list[str] = []

    if selected_mechanism_ids:
        if variant.mechanism_id in selected_mechanism_ids:
            score += 30
            reasons.append("Совпадает способ получения денег")
        elif strict:
            return None

    if selected_matrix_cell:
        if selected_matrix_cell in variant.matrix_cells:
            score += 20
            reasons.append(f"Совпадает ячейка матрицы {selected_matrix_cell}")
        elif strict:
            return None

    classifier_match_count = 0
    selected_groups = {
        group: tags for group, tags in selected_classifiers.items() if tags
    }
    for group, tags in selected_groups.items():
        if set(tags) & set(variant.classifiers.get(group, [])):
            classifier_match_count += 1
        elif strict:
            return None
    if selected_groups:
        threshold = max(1, len(selected_groups) - 1)
        if not strict and classifier_match_count < threshold:
            return None
        if classifier_match_count:
            score += classifier_match_count * 10
            reasons.append(
                f"Совпали классификаторы: {classifier_match_count}/{len(selected_groups)}",
            )

    if selected_route_cells:
        start_cell = selected_route_cells[0]
        end_cell = selected_route_cells[-1]
        if start_cell in variant.matrix_cells and end_cell in variant.matrix_cells:
            score += 10
            reasons.append("Совпадает маршрут")
        elif strict:
            return None

    if selected_bridge_ids:
        matched = [bridge_id for bridge_id in selected_bridge_ids if bridge_id in variant.linked_bridges]
        # В строгом режиме считаем релевантными варианты с хотя бы одним совпавшим мостом.
        if matched:
            score += min(24, 6 * len(matched))
            reasons.append(f"Совпадают мосты: {len(matched)}")
        elif strict:
            return None

    if selected_role_families:
        if variant.activity_role_family in selected_role_families:
            score += 35
            reasons.append(
                f"Совпадает профиль деятельности: {role_family_label(variant.activity_role_family)}",
            )
        elif variant.activity_role_family == "UNKNOWN":
            if strict:
                return None
            score += 5
            reasons.append("Профиль не задан (UNKNOWN)")
        elif strict:
            return None

    score += data_coverage_score(variant)

    return MatchResult(
        variant=variant,
        score=score,
        reasons=reasons,
        classifier_match_count=classifier_match_count,
        classifier_group_count=len(selected_groups),
        data_coverage=data_coverage_score(variant),
    )


def explain_match(result: MatchResult, *, max_items: int = 3) -> list[str]:
    if not result.reasons:
        return ["Подходит по общему профилю."]
    return result.reasons[:max_items]
