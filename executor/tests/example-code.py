# Python 3.10
from __future__ import annotations

import networkx as nx
from seeker import tracer

graph: nx.Graph


# variables whose names are in the tracer will be displayed
@tracer("greeting", "a_node", "an_edge")
def main() -> None:
    # since greeting is in `tracer`, it's value will be shown
    greeting: str = "hello world :)"
    greeting = "Welcome to Graphery!"

    # graph elements are stored in the `graph_object`
    # nodes can be referenced by `graph_object.nodes` or `graph_object.V`
    node_iterator = iter(graph.nodes)
    a_node = next(node_iterator)
    not_traced_node = next(node_iterator)

    # Similarly, edges can be referenced by `graph_object.edges` or `graph_object.E`
    edge_iterator = iter(graph.edges)
    an_edge = next(edge_iterator)
    not_traced_edge = next(edge_iterator)
