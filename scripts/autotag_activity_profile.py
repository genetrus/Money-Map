from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

from money_map.domain.activity_profile_autotag import (
    ROLE_IDS,
    UNKNOWN,
    classify_role_family,
)


def load_variants(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def save_variants(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(
            payload,
            handle,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )


def ensure_activity_profile(variant: dict[str, Any]) -> dict[str, Any]:
    activity_profile = variant.get("activity_profile")
    if not isinstance(activity_profile, dict):
        activity_profile = {}
        variant["activity_profile"] = activity_profile
    if "role_family" not in activity_profile:
        activity_profile["role_family"] = UNKNOWN
    return activity_profile


def print_report(
    counts: Counter[str],
    examples: dict[str, list[tuple[str, str]]],
    unknowns: list[tuple[str, str]],
) -> None:
    print("\nRole distribution:")
    for role in ROLE_IDS + [UNKNOWN]:
        print(f"- {role}: {counts.get(role, 0)}")

    print("\nUnknown (top 20):")
    for variant_id, title in unknowns[:20]:
        print(f"- {variant_id}: {title}")

    print("\nExamples per role:")
    for role in ROLE_IDS:
        print(f"\n{role}:")
        for variant_id, title in examples.get(role, [])[:10]:
            print(f"- {title} ({variant_id})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-tag activity_profile.role_family.")
    parser.add_argument(
        "--path",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "variants.yaml",
        help="Path to variants.yaml",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing role_family")
    parser.add_argument("--debug", action="store_true", help="Print debug output per variant")
    args = parser.parse_args()

    payload = load_variants(args.path)
    variants = payload.get("variants", [])
    counts: Counter[str] = Counter()
    examples: dict[str, list[tuple[str, str]]] = defaultdict(list)
    unknowns: list[tuple[str, str]] = []
    updated = False

    for variant in variants:
        activity_profile = ensure_activity_profile(variant)
        current_role = activity_profile.get("role_family", UNKNOWN) or UNKNOWN
        if current_role != UNKNOWN and not args.force:
            counts[current_role] += 1
            if len(examples[current_role]) < 10:
                examples[current_role].append((variant.get("id", ""), variant.get("title", "")))
            continue

        title = variant.get("title", "")
        summary = variant.get("notes", "")
        if args.debug:
            role, debug = classify_role_family(title, summary, return_debug=True)
            print(
                f"{variant.get('id')}: {title} -> {role} "
                f"(score {debug['best_score']}, second {debug['second_role']}:{debug['second_score']})"
            )
            print(f"  strong: {debug['strong_hits'].get(role)}")
            print(f"  weak: {debug['weak_hits'].get(role)}")
        else:
            role = classify_role_family(title, summary)

        activity_profile["role_family"] = role
        updated = True
        counts[role] += 1
        if role == UNKNOWN:
            unknowns.append((variant.get("id", ""), title))
        if role in ROLE_IDS and len(examples[role]) < 10:
            examples[role].append((variant.get("id", ""), title))

    if updated:
        save_variants(args.path, payload)

    print_report(counts, examples, unknowns)


if __name__ == "__main__":
    main()
