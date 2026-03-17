"""NetworkX-based graph backend."""

from __future__ import annotations

from typing import Any

import networkx as nx


class NetworkXBackend:
    """Graph backend using NetworkX DiGraph."""

    def __init__(self) -> None:
        self._graph = nx.DiGraph()

    def add_node(self, name: str, **attrs: Any) -> None:
        self._graph.add_node(name, **attrs)

    def remove_node(self, name: str) -> None:
        if self._graph.has_node(name):
            self._graph.remove_node(name)

    def has_node(self, name: str) -> bool:
        return self._graph.has_node(name)

    def add_edge(self, source: str, target: str, **attrs: Any) -> None:
        self._graph.add_edge(source, target, **attrs)

    def remove_edge(self, source: str, target: str) -> None:
        if self._graph.has_edge(source, target):
            self._graph.remove_edge(source, target)

    def get_children(self, name: str) -> list[str]:
        """Get direct successors (children in is-a hierarchy)."""
        return list(self._graph.successors(name))

    def get_ancestors(self, name: str) -> list[str]:
        """Get all ancestors (transitive predecessors)."""
        return list(nx.ancestors(self._graph, name))

    def get_nodes(self) -> list[str]:
        return list(self._graph.nodes)

    def get_edges(self) -> list[tuple[str, str, dict]]:
        return [(u, v, d) for u, v, d in self._graph.edges(data=True)]

    def to_dict(self) -> dict:
        return nx.node_link_data(self._graph)

    def from_dict(self, data: dict) -> None:
        self._graph = nx.node_link_graph(data)

    @property
    def graph(self) -> nx.DiGraph:
        return self._graph
