from __future__ import annotations

from typing import Mapping, Any

import networkx as nx


__all__ = ["export_to_graphology"]

_KEY_ATTR_NAME = "key"
_DEFAULT_SIZE = 10


def export_to_graphology(graph: nx.Graph) -> Mapping:
    """
    export networkx graph to graphology serialization format
    reference: https://graphology.github.io/serialization
    @param graph: networkx graph
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

    for node, attr in graph.nodes.items():  # type: Any, nx.NodeView[str, Any]
        attr = attr.copy()

        if "size" not in attr:
            attr["size"] = _DEFAULT_SIZE

        data["nodes"].append(
            {
                "key": attr.get(_KEY_ATTR_NAME, None) or node,
                "attribute": attr,
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
