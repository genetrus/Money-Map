from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from money_map.core.model import AppData


@dataclass
class ClassificationResult:
    tags: Dict[str, List[str]]
    taxonomy_scores: List[Tuple[str, float]]
    cell_scores: List[Tuple[str, float]]
    explanation: List[str]
    confidence: float


def classify_by_tags(
    data: AppData,
    sell: Sequence[str],
    to_whom: Sequence[str],
    value: Sequence[str],
    top_n: int = 5,
) -> ClassificationResult:
    tags = {
        "sell": sorted(set(sell)),
        "to_whom": sorted(set(to_whom)),
        "value": sorted(set(value)),
    }

    taxonomy_scores = _score_taxonomy(data, tags)
    cell_scores = _score_cells_from_tags(data, tags)
    explanation = _build_explanation(tags)
    confidence = _confidence_from_scores(taxonomy_scores)

    return ClassificationResult(
        tags=tags,
        taxonomy_scores=taxonomy_scores[:top_n],
        cell_scores=cell_scores[:top_n],
        explanation=explanation,
        confidence=confidence,
    )


def classify_by_text(data: AppData, text: str, top_n: int = 5) -> ClassificationResult:
    lowered = text.lower()
    tags = _extract_tags(data, lowered)
    taxonomy_scores = _score_taxonomy(data, tags, text_hint=lowered)
    cell_scores = _score_cells_from_tags(data, tags)
    explanation = _build_explanation(tags)
    confidence = _confidence_from_scores(taxonomy_scores)

    return ClassificationResult(
        tags=tags,
        taxonomy_scores=taxonomy_scores[:top_n],
        cell_scores=cell_scores[:top_n],
        explanation=explanation,
        confidence=confidence,
    )


def _extract_tags(data: AppData, text: str) -> Dict[str, List[str]]:
    tags = {"sell": [], "to_whom": [], "value": []}
    tag_groups = data.keywords.keywords.get("tags", {})
    for group_name, group in tag_groups.items():
        for tag_name, words in group.items():
            if any(word.lower() in text for word in words):
                tags[group_name].append(tag_name)
    for key in tags:
        tags[key] = sorted(set(tags[key]))
    return tags


def _score_taxonomy(
    data: AppData, tags: Dict[str, List[str]], text_hint: str | None = None
) -> List[Tuple[str, float]]:
    taxonomy_hints = data.keywords.keywords.get("taxonomy_hints", {})
    scores: List[Tuple[str, float]] = []
    for item in data.taxonomy:
        score = 0.0
        score += len(set(tags["sell"]) & set(item.sell)) * 1.5
        score += len(set(tags["to_whom"]) & set(item.to_whom)) * 1.0
        score += len(set(tags["value"]) & set(item.value)) * 1.5

        if text_hint:
            hints = taxonomy_hints.get(item.id, [])
            if any(hint.lower() in text_hint for hint in hints):
                score += 2.0

        if score > 0:
            scores.append((item.id, round(score, 2)))

    scores.sort(key=lambda pair: (-pair[1], pair[0]))
    return scores


def _score_cells_from_tags(data: AppData, tags: Dict[str, List[str]]) -> List[Tuple[str, float]]:
    scores: Dict[str, float] = {}
    for tag in tags["sell"]:
        mapping = data.mappings.sell_items.get(tag)
        if mapping and mapping.typical_cells:
            for cell in mapping.typical_cells:
                scores[cell] = scores.get(cell, 0.0) + 1.2
    for tag in tags["value"]:
        mapping = data.mappings.value_measures.get(tag)
        if mapping and mapping.typical_cells:
            for cell in mapping.typical_cells:
                scores[cell] = scores.get(cell, 0.0) + 1.1

    for item in data.taxonomy:
        if set(tags["sell"]) & set(item.sell) or set(tags["value"]) & set(item.value):
            for cell in item.typical_cells:
                scores[cell] = scores.get(cell, 0.0) + 0.3

    ranked = sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))
    return [(cell, round(score, 2)) for cell, score in ranked]


def _build_explanation(tags: Dict[str, List[str]]) -> List[str]:
    parts: List[str] = []
    for key, title in [
        ("sell", "sell"),
        ("to_whom", "to_whom"),
        ("value", "value"),
    ]:
        if tags[key]:
            parts.append(f"{title}: {', '.join(tags[key])}")
    return parts


def _confidence_from_scores(scores: List[Tuple[str, float]]) -> float:
    if not scores:
        return 0.1
    top = scores[0][1]
    if top >= 5:
        return 0.9
    if top >= 3:
        return 0.7
    if top >= 1:
        return 0.5
    return 0.3
