from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from money_map.domain.activity_profile import DEFAULT_ROLE_FAMILY

class Axis(BaseModel):
    id: str
    values: List[str]
    labels: Dict[str, str]


class Cell(BaseModel):
    id: str
    activity: str
    scalability: str
    risk: str
    label: str
    short: str
    examples: List[str]


class MappingItem(BaseModel):
    label: str
    typical_cells: Optional[List[str]] = None
    notes: Optional[str] = None


class Mappings(BaseModel):
    sell_items: Dict[str, MappingItem]
    to_whom_items: Dict[str, MappingItem]
    value_measures: Dict[str, MappingItem]


class TaxonomyItem(BaseModel):
    id: str
    name: str
    description: str
    sell: List[str]
    to_whom: List[str]
    value: List[str]
    typical_cells: List[str]
    outside_market: bool
    risk_notes: str
    examples: List[str]


class ActivityProfile(BaseModel):
    role_family: str = DEFAULT_ROLE_FAMILY
    task_profile: List[str] = Field(default_factory=list)
    environment: Optional[str] = None
    social_intensity: Optional[str] = None


class ActivityProfileDefinition(BaseModel):
    id: str
    title_ru: str
    description_ru: str
    examples_ru: List[str]
    tags: List[str] = Field(default_factory=list)
    related_classifier_ids: Optional[List[str]] = None


class ActivitySubprofileDefinition(BaseModel):
    id: str
    parent_profile_id: str
    title_ru: str
    examples_ru: List[str]
    tags: List[str] = Field(default_factory=list)


class WorkFormatDefinition(BaseModel):
    id: str
    title_ru: str
    description_ru: str
    examples_ru: List[str]


class EntryLevelDefinition(BaseModel):
    id: str
    title_ru: str
    description_ru: str
    examples_ru: List[str]


class AutoTagging(BaseModel):
    profile_keywords: Dict[str, List[str]] = Field(default_factory=dict)
    subprofile_keywords: Dict[str, List[str]] = Field(default_factory=dict)
    work_format_keywords: Dict[str, List[str]] = Field(default_factory=dict)
    entry_level_keywords: Dict[str, List[str]] = Field(default_factory=dict)


class Variant(BaseModel):
    id: str
    title: str
    kind: str
    primary_way_id: str
    matrix_cells: List[str]
    sell_tags: List[str]
    to_whom_tags: List[str]
    value_tags: List[str]
    risk_level: str
    activity: str
    scalability: str
    outside_market: bool
    requirements: List[str]
    first_steps: List[str]
    success_metrics: List[str]
    related_variant_ids: List[str]
    notes: Optional[str] = None
    bridge_ids: List[str] = Field(default_factory=list)
    route_ids: List[str] = Field(default_factory=list)
    channel_state: Dict[str, bool] = Field(default_factory=dict)
    activity_profile: ActivityProfile = Field(default_factory=ActivityProfile)
    profile_id: Optional[str] = None
    subprofile_id: Optional[str] = None
    work_format_ids: List[str] = Field(default_factory=list)
    entry_level_ids: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    rationale: Optional[str] = None
    archetype_tags: List[str] = Field(default_factory=list)


class PathItem(BaseModel):
    id: str
    name: str
    sequence: List[str]
    note: str


class BridgeItem(BaseModel):
    id: str
    from_cell: str = Field(alias="from")
    to_cell: str = Field(alias="to")
    name: str
    mechanisms: List[str]
    checks: List[str]
    notes: str
    short_summary: Optional[str] = None
    effects: List[str] = Field(default_factory=list)
    linked_way_ids: List[str] = Field(default_factory=list)
    linked_route_ids: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class DiagramConfig(BaseModel):
    diagrams: Dict[str, object]


class Keywords(BaseModel):
    keywords: Dict[str, object]


class AppData(BaseModel):
    axes: List[Axis]
    cells: List[Cell]
    taxonomy: List[TaxonomyItem]
    mappings: Mappings
    paths: List[PathItem]
    bridges: List[BridgeItem]
    diagrams: DiagramConfig
    keywords: Keywords
    activity_profiles: List[ActivityProfileDefinition] = Field(default_factory=list)
    activity_subprofiles: List[ActivitySubprofileDefinition] = Field(default_factory=list)
    work_formats: List[WorkFormatDefinition] = Field(default_factory=list)
    entry_levels: List[EntryLevelDefinition] = Field(default_factory=list)
    money_way_profile_map: Dict[str, List[str]] = Field(default_factory=dict)
    auto_tagging: AutoTagging = Field(default_factory=AutoTagging)
    variants: List[Variant] = Field(default_factory=list)
    variants_by_way_id: Dict[str, List[Variant]] = Field(default_factory=dict)
    variants_by_cell_id: Dict[str, List[Variant]] = Field(default_factory=dict)
    variant_by_id: Dict[str, Variant] = Field(default_factory=dict)
