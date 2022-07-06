from __future__ import annotations

import json
from typing import Mapping, Any, Callable, Sequence

import networkx as nx


__all__ = [
    "get_graphology_key",
    "apply_sizing",
    "run_layout_fn",
    "export_to_graphology",
    "import_from_graphology",
]

_KEY_ATTR_NAME = "key"
_SIZE_ATTR_NAME = "size"
_DEFAULT_SIZE = 15
_DEFAULT_LAYOUT_FN = nx.spring_layout


def get_graphology_key(
    graph: nx.Graph, identifier, key_field_name: str = _KEY_ATTR_NAME
) -> str:
    entity = graph.nodes[identifier]
    return str(entity.get(key_field_name, None) or identifier)


def run_layout_fn(
    graph: nx.Graph, layout_fn: Callable = _DEFAULT_LAYOUT_FN
) -> nx.Graph:
    layout = layout_fn(graph)
    layout_dict = {node: {"x": x, "y": y} for node, (x, y) in layout.items()}
    nx.set_node_attributes(graph, layout_dict)
    return graph


def apply_sizing(graph: nx.Graph, size: int = _DEFAULT_SIZE, nodes: Sequence = ()):
    if not nodes:
        nodes = graph.nodes

    attr_dict = {node: size for node in nodes}

    nx.set_node_attributes(graph, attr_dict, _SIZE_ATTR_NAME)


def export_to_graphology(
    graph: nx.Graph, layout_fn: Callable = _DEFAULT_LAYOUT_FN
) -> Mapping:
    """
    export networkx graph to graphology serialization format
    reference: https://graphology.github.io/serialization
    @param graph: networkx graph
    @param layout_fn:
    @return:
    """
    data = {
        "attributes": {},
        "options": {
            "allowSelfLoops": True,
            "type": "directed" if graph.is_directed() else "undirected",
            "multi": graph.is_multigraph(),
        },
        "nodes": [],
        "edges": [],
    }

    if any(("x" not in attr or "y" not in attr) for attr in graph.nodes.values()):
        run_layout_fn(graph, layout_fn)

    for node, attr in graph.nodes.items():  # type: Any, nx.NodeView[str, Any]
        apply_sizing(graph, nodes=(node,))

        data["nodes"].append(
            {
                "key": attr.get(_KEY_ATTR_NAME, None) or node,
                "attributes": attr.copy(),
            }
        )

    if graph.is_multigraph():
        graph: nx.MultiGraph
        for e in graph.edges(keys=True):
            s, t, k = e[0], e[1], e[2]
            data["edges"].append(
                {
                    "key": k,
                    "source": s,
                    "target": t,
                    "attributes": graph.adj[s][t][k].copy(),
                }
            )
    else:
        for e in graph.edges():
            s, t = e[0], e[1]
            data["edges"].append(
                {
                    "key": f"{s}->{t}",  # optional I think
                    "source": s,
                    "target": t,
                    "attributes": graph.adj[s][t].copy(),
                }
            )

    return data


def import_from_graphology(json_obj: str | Mapping) -> nx.Graph:
    if isinstance(json_obj, str):
        json_obj = json.loads(json_obj)

    graph_options = json_obj.get("options", {})
    graph_attrs = json_obj.get("attributes", {})

    is_multi = graph_options.get("multi", False)
    is_directed = (
        graph_type := graph_options.get("type", "undirected")
    ) == "directed" or graph_type == "mixed"

    if is_multi:
        if is_directed:
            graph_cls = nx.MultiDiGraph
        else:
            graph_cls = nx.MultiGraph
    else:
        if is_directed:
            graph_cls = nx.DiGraph
        else:
            graph_cls = nx.Graph

    graph = graph_cls()

    graph.graph.update(graph_attrs)

    nodes = json_obj.get("nodes", [])
    for node in nodes:
        graph.add_node(node["key"], **node["attributes"])

    edges = json_obj.get("edges", [])
    # not sure if this works or not
    for edge in edges:
        is_undirected = edge.get("undirected", None)
        graph.add_edge(
            edge["source"],
            edge["target"],
            key=edge.get("key", None),
            **edge["attributes"],
            undirected=is_undirected,
        )

        if is_undirected:
            graph.add_edge(
                edge["target"],
                edge["source"],
                key=edge.get("key", None),
                **edge["attributes"],
                undirected=is_undirected,
            )

    return graph
