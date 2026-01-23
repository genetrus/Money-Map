from __future__ import annotations

import inspect
from typing import Any, Iterable

from st_cytoscape import cytoscape


def render_cytoscape(
    elements: Iterable[dict[str, Any]],
    stylesheet: list[dict[str, Any]],
    layout: dict[str, Any],
    *,
    height: str = "720px",
    selection_type: str = "single",
    key: str | None = None,
) -> Any:
    kwargs: dict[str, Any] = {
        "layout": layout,
        "height": height,
        "selection_type": selection_type,
    }
    if key is not None:
        signature = inspect.signature(cytoscape)
        if "key" in signature.parameters:
            kwargs["key"] = key
    return cytoscape(elements, stylesheet, **kwargs)
