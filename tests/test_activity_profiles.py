from money_map.core.load import load_app_data


def test_money_way_profile_map_complete() -> None:
    data = load_app_data()
    taxonomy_ids = {item.id for item in data.taxonomy}
    for tax_id in taxonomy_ids:
        assert data.money_way_profile_map.get(tax_id), f"Missing mapping for {tax_id}"


def test_activity_profiles_unique() -> None:
    data = load_app_data()
    profile_ids = [profile.id for profile in data.activity_profiles]
    assert len(profile_ids) == len(set(profile_ids)), "Duplicate profile ids detected"


def test_activity_subprofiles_parent_exists() -> None:
    data = load_app_data()
    profile_ids = {profile.id for profile in data.activity_profiles}
    for subprofile in data.activity_subprofiles:
        assert subprofile.parent_profile_id in profile_ids


def test_variants_profile_coverage() -> None:
    data = load_app_data()
    if not data.variants:
        return
    tagged = sum(1 for variant in data.variants if variant.profile_id)
    assert tagged / len(data.variants) >= 0.85
