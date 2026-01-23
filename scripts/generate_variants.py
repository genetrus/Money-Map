#!/usr/bin/env python
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "variants"
OUTPUT_PATH = DATA_DIR / "variants.generated.json"

CELL_PRIORITY = ["A1", "A2", "A3", "A4", "P1", "P2", "P3", "P4"]
MIN_VARIANTS_PER_ARCH = 4

ROLE_FAMILIES = [
    "OPS",
    "ADMIN",
    "SALES",
    "SUPPORT",
    "LOGISTICS",
    "MAINTENANCE",
    "CONTENT",
    "ANALYTICS",
]

CHANNEL_STATE_KEYS = ["automation", "channel_system", "delegation", "subscription"]

ALLOWED_BY_MECHANISM = {
    "salary": {
        "to_whom": {"single_client", "platform"},
        "measure": {"rate", "price"},
    },
    "fee_for_result": {
        "to_whom": {"single_client", "many_people", "platform"},
        "measure": {"price"},
    },
    "commission": {
        "to_whom": {"market", "platform", "many_people"},
        "measure": {"percent"},
    },
    "entrepreneurship_margin": {
        "to_whom": {"many_people", "market", "platform"},
        "measure": {"price", "rent"},
    },
    "rent_access": {
        "to_whom": {"single_client", "many_people"},
        "measure": {"rent"},
    },
    "interest_dividends": {
        "to_whom": {"market"},
        "measure": {"percent", "payout"},
    },
    "appreciation": {
        "to_whom": {"market"},
        "measure": {"appreciation"},
    },
    "intellectual_property": {
        "to_whom": {"many_people", "platform"},
        "measure": {"price", "rent", "appreciation"},
    },
    "attention_audience": {
        "to_whom": {"platform", "many_people"},
        "measure": {"payout", "price", "percent"},
    },
    "data_compute": {
        "to_whom": {"platform", "many_people", "single_client"},
        "measure": {"rent", "price"},
    },
    "grants_prizes": {
        "to_whom": {"state", "platform"},
        "measure": {"payout"},
    },
    "transfers_insurance": {
        "to_whom": {"state"},
        "measure": {"payout"},
    },
    "gifts_inheritance": {
        "to_whom": {"many_people"},
        "measure": {"payout"},
    },
    "savings_effect": {
        "to_whom": {"market", "state"},
        "measure": {"price", "payout"},
    },
}


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def normalize_title(value: str) -> str:
    return " ".join(value.lower().strip().split())


def stable_int(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest(), 16)


def _unique(items: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _cap(items: Iterable[str], limit: int) -> List[str]:
    result = _unique(items)
    return result[:limit]


def _filter_allowed(items: Iterable[str], allowed: set[str]) -> List[str]:
    return [item for item in _unique(items) if item in allowed]


def normalize_risk_level(value: str, mod_set: List[Dict[str, Any]]) -> str:
    if value == "high":
        return "high"
    if value == "medium":
        if any(mod.get("category") == "risk" for mod in mod_set):
            return "high"
        return "low"
    return "low"


def build_channel_state(mod_set: List[Dict[str, Any]]) -> Dict[str, bool]:
    state = {key: False for key in CHANNEL_STATE_KEYS}
    for mod in mod_set:
        mod_id = mod.get("id")
        if mod_id in state:
            state[mod_id] = True
    return state


def select_mod_sets(archetype: Dict[str, Any], modifiers: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    mechanism_id = archetype["mechanism_id"]
    allowed = ALLOWED_BY_MECHANISM[mechanism_id]
    by_category: Dict[str, List[Dict[str, Any]]] = {}
    for mod in modifiers:
        category = mod["category"]
        applies = mod.get("applies_to", {}).get("mechanisms")
        if applies and mechanism_id not in applies:
            continue
        by_category.setdefault(category, []).append(mod)

    channels = []
    base_to_whom = set(archetype["base_classifiers"]["to_whom"])
    for mod in by_category.get("channel", []):
        mod_to = set(mod["changes"].get("to_whom_add", []))
        if mod_to and mod_to.intersection(allowed["to_whom"]):
            channels.append(mod)

    channels = sorted(channels, key=lambda item: item["id"])
    primary = None
    for mod in channels:
        mod_to = set(mod["changes"].get("to_whom_add", []))
        if base_to_whom.intersection(mod_to):
            primary = mod
            break
    if primary is None and channels:
        primary = channels[0]

    secondary = None
    if channels and len(channels) > 1:
        idx = stable_int(archetype["arch_id"]) % (len(channels) - 1)
        candidates = [m for m in channels if m is not primary]
        secondary = candidates[idx % len(candidates)]

    packaging = sorted(by_category.get("packaging", []), key=lambda item: item["id"])
    risk_mods = sorted(by_category.get("risk", []), key=lambda item: item["id"])

    mod_sets: List[List[Dict[str, Any]]] = []
    if primary:
        mod_sets.append([primary])
    if secondary:
        mod_sets.append([secondary])

    if packaging and primary:
        base_hash = stable_int(f"{archetype['arch_id']}-pkg")
        first_idx = base_hash % len(packaging)
        second_idx = (base_hash // 7) % len(packaging)
        for idx in _unique([first_idx, second_idx]):
            mod_sets.append([primary, packaging[idx]])

    if risk_mods and primary:
        if stable_int(archetype["arch_id"]) % 2 == 0:
            mod_sets.append([primary, risk_mods[0]])

    # Ensure minimum variants per archetype
    if primary and len(mod_sets) < MIN_VARIANTS_PER_ARCH:
        for mod in packaging:
            candidate = [primary, mod]
            if candidate not in mod_sets:
                mod_sets.append(candidate)
            if len(mod_sets) >= MIN_VARIANTS_PER_ARCH:
                break

    return mod_sets[:6]


def apply_modifiers(archetype: Dict[str, Any], mod_set: List[Dict[str, Any]]) -> Dict[str, Any]:
    mechanism_id = archetype["mechanism_id"]
    allowed = ALLOWED_BY_MECHANISM[mechanism_id]

    title = archetype["base_title"]
    desc = archetype["base_desc"]

    sell_tags = _unique(archetype["base_classifiers"]["sell"])
    to_whom_tags = _unique(archetype["base_classifiers"]["to_whom"])
    value_tags = _unique(archetype["base_classifiers"]["measure"])
    matrix_cells = _unique(archetype["base_matrix_cells"])
    bridges = _unique(archetype["default_bridges"])
    routes = _unique(archetype["default_routes"])

    for mod in mod_set:
        changes = mod.get("changes", {})
        title += changes.get("title_suffix", "")
        desc_suffix = changes.get("desc_suffix")
        if desc_suffix:
            desc = f"{desc} {desc_suffix}"
        sell_tags = _unique(sell_tags + changes.get("sell_add", []))
        to_whom_tags = _unique(to_whom_tags + changes.get("to_whom_add", []))
        value_tags = _unique(value_tags + changes.get("measure_add", []))
        matrix_cells = _unique(matrix_cells + changes.get("matrix_add", []))
        bridges = _unique(bridges + changes.get("bridges_add", []))
        routes = _unique(routes + changes.get("routes_add", []))

    to_whom_tags = _filter_allowed(to_whom_tags, allowed["to_whom"]) or list(
        allowed["to_whom"]
    )[:1]
    value_tags = _filter_allowed(value_tags, allowed["measure"]) or list(
        allowed["measure"]
    )[:1]

    matrix_cells = sorted(set(matrix_cells), key=lambda cell: CELL_PRIORITY.index(cell))
    matrix_cells = matrix_cells[:3]
    bridges = _cap(bridges, 8)
    routes = _cap(routes, 3)

    return {
        "title": title,
        "notes": desc,
        "sell_tags": _cap(sell_tags, 3),
        "to_whom_tags": _cap(to_whom_tags, 2),
        "value_tags": _cap(value_tags, 2),
        "matrix_cells": matrix_cells,
        "bridge_ids": bridges,
        "routes": routes,
    }


def build_variants(archetypes: List[Dict[str, Any]], modifiers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    variants = []
    dedup_keys = set()
    for arch in archetypes:
        mod_sets = select_mod_sets(arch, modifiers)
        for mod_set in mod_sets:
            mod_key = "base" if not mod_set else ".".join(mod["id"] for mod in mod_set)
            payload = apply_modifiers(arch, mod_set)
            risk_level = normalize_risk_level(arch["risk_level"], mod_set)
            channel_state = build_channel_state(mod_set)
            variant_id = f"{arch['mechanism_id']}.{arch['arch_id']}.{mod_key}"
            dedup_key = (
                arch["mechanism_id"],
                normalize_title(payload["title"]),
                arch["role_family"],
                tuple(sorted(payload["sell_tags"])),
                tuple(sorted(payload["to_whom_tags"])),
                tuple(sorted(payload["value_tags"])),
            )
            if dedup_key in dedup_keys:
                continue
            dedup_keys.add(dedup_key)

            variants.append(
                {
                    "id": variant_id,
                    "title": payload["title"],
                    "kind": arch["kind"],
                    "primary_way_id": arch["mechanism_id"],
                    "matrix_cells": payload["matrix_cells"],
                    "sell_tags": payload["sell_tags"],
                    "to_whom_tags": payload["to_whom_tags"],
                    "value_tags": payload["value_tags"],
                    "risk_level": risk_level,
                    "activity": arch["activity"],
                    "scalability": arch["scalability"],
                    "outside_market": arch["outside_market"],
                    "requirements": [],
                    "first_steps": [],
                    "success_metrics": [],
                    "related_variant_ids": [],
                    "notes": payload["notes"],
                    "bridge_ids": payload["bridge_ids"],
                    "route_ids": payload["routes"],
                    "channel_state": channel_state,
                    "activity_profile": {
                        "task_profile": [],
                        "environment": None,
                        "social_intensity": None,
                        "role_family": arch["role_family"],
                    },
                }
            )
    return variants


def report_coverage(variants: List[Dict[str, Any]]) -> List[str]:
    errors = []
    total = len(variants)
    print(f"Total variants: {total}")

    by_mech = Counter(v["primary_way_id"] for v in variants)
    print("\nBy mechanism:")
    for mech, count in sorted(by_mech.items()):
        marker = "" if count >= 25 else "  <25"
        print(f"  {mech}: {count}{marker}")
        if count < 25:
            errors.append(f"Mechanism {mech} has only {count} variants")

    by_role = Counter(v["activity_profile"]["role_family"] for v in variants)
    print("\nBy role_family:")
    for role in ROLE_FAMILIES:
        count = by_role.get(role, 0)
        print(f"  {role}: {count}")
        if count < 20:
            errors.append(f"Role family {role} has only {count} variants")

    by_cell = Counter(cell for v in variants for cell in v["matrix_cells"])
    print("\nBy matrix cell:")
    for cell in CELL_PRIORITY:
        count = by_cell.get(cell, 0)
        marker = "" if count >= 20 else "  <20"
        print(f"  {cell}: {count}{marker}")
        if count < 20:
            errors.append(f"Matrix cell {cell} has only {count} variants")

    by_sell = Counter(tag for v in variants for tag in v["sell_tags"])
    print("\nBy sell tag:")
    for tag, count in sorted(by_sell.items()):
        marker = "" if count >= 15 else "  <15"
        print(f"  {tag}: {count}{marker}")
        if count < 15:
            errors.append(f"Sell tag {tag} has only {count} variants")

    by_to = Counter(tag for v in variants for tag in v["to_whom_tags"])
    print("\nBy to_whom tag:")
    for tag, count in sorted(by_to.items()):
        marker = "" if count >= 20 else "  <20"
        print(f"  {tag}: {count}{marker}")
        if count < 20:
            errors.append(f"To_whom tag {tag} has only {count} variants")

    by_value = Counter(tag for v in variants for tag in v["value_tags"])
    print("\nBy value tag:")
    for tag, count in sorted(by_value.items()):
        marker = "" if count >= 20 else "  <20"
        print(f"  {tag}: {count}{marker}")
        if count < 20:
            errors.append(f"Value tag {tag} has only {count} variants")

    normalized_titles = Counter(normalize_title(v["title"]) for v in variants)
    suspicious = [(title, count) for title, count in normalized_titles.items() if count > 1]
    suspicious = sorted(suspicious, key=lambda item: item[1], reverse=True)[:20]
    print("\nTop-20 suspicious duplicate titles:")
    if not suspicious:
        print("  (none)")
    else:
        for title, count in suspicious:
            print(f"  {title} — {count}")

    if total < 350:
        errors.append(f"Total variants {total} < 350")

    return errors


def main() -> int:
    archetypes_path = DATA_DIR / "archetypes.yaml"
    modifiers_path = DATA_DIR / "modifiers.yaml"
    if not archetypes_path.exists() or not modifiers_path.exists():
        raise FileNotFoundError("archetypes.yaml или modifiers.yaml не найдены")

    archetypes = _load_yaml(archetypes_path).get("archetypes", [])
    modifiers = _load_yaml(modifiers_path).get("modifiers", [])
    variants = build_variants(archetypes, modifiers)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump({"variants": variants}, handle, ensure_ascii=False, indent=2)

    errors = report_coverage(variants)
    if errors:
        print("\nCoverage errors:")
        for err in errors:
            print(f"- {err}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
