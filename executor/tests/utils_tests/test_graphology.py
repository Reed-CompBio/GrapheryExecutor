from __future__ import annotations

import networkx as nx
import pytest

from ...utils.graphology_helper import (
    export_to_graphology,
    run_layout_fn,
    import_from_graphology,
    apply_sizing,
)


@pytest.mark.parametrize(
    "graph_type, target_attr",
    [
        (nx.Graph, {"multi": False, "type": "undirected"}),
        (nx.DiGraph, {"multi": False, "type": "directed"}),
        (nx.MultiGraph, {"multi": True, "type": "undirected"}),
        (nx.MultiDiGraph, {"multi": True, "type": "directed"}),
    ],
)
def test_export_different_types_from_graphology(graph_type, target_attr):
    """
    Test that the graphology module is importable.
    """
    g = graph_type()
    result = export_to_graphology(g)
    result_options = result.get("options", {})

    assert result_options["allowSelfLoops"]

    for key, target in target_attr.items():
        assert result_options[key] == target


def test_undirected_graph_export():
    g = nx.path_graph(10)
    run_layout_fn(g)
    apply_sizing(g)

    result = import_from_graphology(export_to_graphology(g))

    assert set(result.nodes) == set(g.nodes)
    assert set(result.edges) == set(g.edges)

    for node, attr in g.nodes.items():
        assert result.nodes[node] == attr
