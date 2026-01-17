from __future__ import annotations

from money_map.core.load import load_app_data
from money_map.core.taxonomy_graph import build_taxonomy_star


def test_taxonomy_star_graph_basic() -> None:
    data = load_app_data()
    graph = build_taxonomy_star(data, include_tags=False, outside_only=False)

    assert "root" in graph
    taxonomy_nodes = [
        node_id
        for node_id, attrs in graph.nodes(data=True)
        if attrs.get("kind") == "taxonomy"
    ]
    assert len(taxonomy_nodes) == len(data.taxonomy)
    assert graph.out_degree("root") == len(taxonomy_nodes)


def test_taxonomy_star_graph_with_tags() -> None:
    data = load_app_data()
    graph = build_taxonomy_star(data, include_tags=True, outside_only=False)

    tag_nodes = [
        node_id for node_id, attrs in graph.nodes(data=True) if attrs.get("kind") == "tag"
    ]
    assert tag_nodes

    tag_edges = [
        (source, target)
        for source, target in graph.edges()
        if graph.nodes[source].get("kind") == "taxonomy"
        and graph.nodes[target].get("kind") == "tag"
    ]
    assert tag_edges
