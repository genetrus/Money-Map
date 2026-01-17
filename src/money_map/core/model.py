from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


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
