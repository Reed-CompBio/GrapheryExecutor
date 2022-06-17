from __future__ import annotations

from typing import Mapping

import networkx as nx

__all__ = [
    "get_cytoscape_name",
    "get_cytoscape_id",
    "cyjs_from_graph",
    "graph_from_cyjs",
]

_DEFAULT_NODE_NAME_FIELD = "name"
_DEFAULT_ID_NAME_FIELD = "id"


def get_cytoscape_name(
    graph: nx.Graph, identifier, name: str = _DEFAULT_NODE_NAME_FIELD
) -> str:
    entity = graph.nodes[identifier]
    return entity.get(name) or str(identifier)


def get_cytoscape_id(
    graph: nx.Graph, identifier, id_name: str = _DEFAULT_ID_NAME_FIELD
) -> str:
    entity = graph.nodes[identifier]
    return entity.get(id_name) or str(identifier)


def cyjs_from_graph(
    graph: nx.Graph,
    name: str = _DEFAULT_NODE_NAME_FIELD,
    ident: str = _DEFAULT_ID_NAME_FIELD,
) -> Mapping:
    """Returns data in Cytoscape JSON format (cyjs).

    Parameters
    ----------
    graph : NetworkX Graph
        The graph to convert to cytoscape format
    name : string
        A string which is mapped to the 'name' node element in cyjs format.
        Must not have the same value as `ident`.
    ident : string
        A string which is mapped to the 'id' node element in cyjs format.
        Must not have the same value as `name`.

    Returns
    -------
    data: dict
        A dictionary with cyjs formatted data.

    Raises
    ------
    NetworkXError
        If the values for `name` and `ident` are identical.

    See Also
    --------
    cytoscape_graph: convert a dictionary in cyjs format to a graph

    References
    ----------
    .. [1] Cytoscape user's manual:
       http://manual.cytoscape.org/en/stable/index.html

    Examples
    --------
    >>> G = nx.path_graph(2)
    >>> nx.cytoscape_data(graph)  # doctest: +SKIP
    {'data': [],
     'directed': False,
     'multigraph': False,
     'elements': {'nodes': [{'data': {'id': '0', 'value': 0, 'name': '0'}},
       {'data': {'id': '1', 'value': 1, 'name': '1'}}],
      'edges': [{'data': {'source': 0, 'target': 1}}]}}
    """

    if name == ident:
        raise nx.NetworkXError("name and ident must be different.")

    jsondata = {"data": list(graph.graph.items())}
    jsondata["directed"] = graph.is_directed()
    jsondata["multigraph"] = graph.is_multigraph()
    jsondata["elements"] = {"nodes": [], "edges": []}
    nodes = jsondata["elements"]["nodes"]
    edges = jsondata["elements"]["edges"]

    for i, j in graph.nodes.items():
        n = {"data": j.copy()}
        n["data"]["id"] = get_cytoscape_id(graph, i, ident)
        n["data"]["value"] = i
        n["data"]["name"] = get_cytoscape_name(graph, i, name)
        nodes.append(n)

    if graph.is_multigraph():
        graph: nx.MultiGraph
        for e in graph.edges(keys=True):
            n = {"data": graph.adj[e[0]][e[1]][e[2]].copy()}
            n["data"]["source"] = e[0]
            n["data"]["target"] = e[1]
            n["data"]["key"] = e[2]
            edges.append(n)
    else:
        for e in graph.edges():
            n = {"data": graph.adj[e[0]][e[1]].copy()}
            n["data"]["source"] = e[0]
            n["data"]["target"] = e[1]
            edges.append(n)
    return jsondata


def graph_from_cyjs(
    cyjs: Mapping,
    name: str = _DEFAULT_NODE_NAME_FIELD,
    ident: str = _DEFAULT_ID_NAME_FIELD,
) -> nx.Graph:
    """
    Create a NetworkX graph from a dictionary in cytoscape JSON format.

    Parameters
    ----------
    cyjs : dict
        A dictionary of data conforming to cytoscape JSON format.
    attrs : dict or None (default=None)
        A dictionary containing the keys 'name' and 'ident' which are mapped to
        the 'name' and 'id' node elements in cyjs format. All other keys are
        ignored. Default is `None` which results in the default mapping
        ``dict(name="name", ident="id")``.

        .. deprecated:: 2.6

           The `attrs` keyword argument will be replaced with `name` and
           `ident` in networkx 3.0

    name : string
        A string which is mapped to the 'name' node element in cyjs format.
        Must not have the same value as `ident`.
    ident : string
        A string which is mapped to the 'id' node element in cyjs format.
        Must not have the same value as `name`.

    Returns
    -------
    graph : a NetworkX graph instance
        The `graph` can be an instance of `Graph`, `DiGraph`, `MultiGraph`, or
        `MultiDiGraph` depending on the input data.

    Raises
    ------
    NetworkXError
        If the `name` and `ident` attributes are identical.

    See Also
    --------
    cytoscape_data: convert a NetworkX graph to a dict in cyjs format

    References
    ----------
    .. [1] Cytoscape user's manual:
       http://manual.cytoscape.org/en/stable/index.html

    Examples
    --------
    >>> data_dict = {
    ...     'data': [],
    ...     'directed': False,
    ...     'multigraph': False,
    ...     'elements': {'nodes': [{'data': {'id': '0', 'value': 0, 'name': '0'}},
    ...       {'data': {'id': '1', 'value': 1, 'name': '1'}}],
    ...      'edges': [{'data': {'source': 0, 'target': 1}}]}
    ... }
    >>> G = nx.cytoscape_graph(data_dict)
    >>> G.name
    ''
    >>> G.nodes()
    NodeView((0, 1))
    >>> G.nodes(data=True)[0]
    {'id': '0', 'value': 0, 'name': '0'}
    >>> G.edges(data=True)
    EdgeDataView([(0, 1, {'source': 0, 'target': 1})])
    """
    if name == ident:
        raise nx.NetworkXError("name and ident must be different.")

    multigraph = cyjs.get("multigraph")
    directed = cyjs.get("directed")
    if multigraph:
        graph = nx.MultiGraph()
    else:
        graph = nx.Graph()
    if directed:
        graph = graph.to_directed()
    graph.graph = dict(cyjs.get("data", []))
    for d in cyjs["elements"]["nodes"]:
        node_data = d["data"].copy()
        node = d["data"][ident]

        if d["data"].get(name):
            node_data[name] = d["data"].get(name)
        if d["data"].get(ident):
            node_data[ident] = d["data"].get(ident)

        graph.add_node(node)
        graph.nodes[node].update(node_data)

    for d in cyjs["elements"]["edges"]:
        edge_data = d["data"].copy()
        sour = d["data"]["source"]
        targ = d["data"]["target"]
        if multigraph:
            key = d["data"].get("key", 0)
            graph.add_edge(sour, targ, key=key)
            graph.edges[sour, targ, key].update(edge_data)
        else:
            graph.add_edge(sour, targ)
            graph.edges[sour, targ].update(edge_data)
    return graph
