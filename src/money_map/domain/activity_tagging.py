from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class AutoTagResult:
    profile_id: Optional[str]
    subprofile_id: Optional[str]
    confidence: float


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _keyword_hits(text: str, keywords: Iterable[str]) -> int:
    normalized = normalize_text(text)
    words = normalized.split()
    score = 0
    for keyword in keywords:
        if not keyword:
            continue
        keyword_norm = normalize_text(keyword)
        if " " in keyword_norm:
            if keyword_norm in normalized:
                score += 1
            continue
        if any(word.startswith(keyword_norm) for word in words):
            score += 1
    return score


def _best_match(scores: Dict[str, int]) -> tuple[Optional[str], int, int]:
    if not scores:
        return None, 0, 0
    sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_id, best_score = sorted_scores[0]
    second_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0
    return best_id, best_score, second_score


def auto_tag_variant(
    text: str,
    *,
    profile_keywords: Dict[str, List[str]],
    subprofile_keywords: Dict[str, List[str]],
    subprofile_parent: Dict[str, str],
) -> AutoTagResult:
    normalized = normalize_text(text)
    profile_scores = {
        profile_id: _keyword_hits(normalized, keywords)
        for profile_id, keywords in profile_keywords.items()
    }
    best_profile, best_score, second_score = _best_match(profile_scores)
    if not best_profile or best_score == 0:
        return AutoTagResult(None, None, 0.0)

    confidence = best_score / (best_score + second_score + 1)
    sub_scores = {}
    for sub_id, keywords in subprofile_keywords.items():
        if subprofile_parent.get(sub_id) != best_profile:
            continue
        sub_scores[sub_id] = _keyword_hits(normalized, keywords)
    best_sub, sub_score, _ = _best_match(sub_scores)
    if sub_score == 0:
        best_sub = None

    return AutoTagResult(best_profile, best_sub, confidence)


def auto_tag_layers(
    text: str,
    *,
    keywords_map: Dict[str, List[str]],
) -> List[str]:
    normalized = normalize_text(text)
    results = []
    for key, keywords in keywords_map.items():
        if _keyword_hits(normalized, keywords) > 0:
            results.append(key)
    return results
