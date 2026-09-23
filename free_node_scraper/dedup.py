"""Deduplicate parsed proxy nodes."""

from __future__ import annotations

from typing import Iterable, List

from .parsers import Node


def dedup_nodes(nodes: Iterable[Node]) -> List[Node]:
    """Remove duplicate nodes, keeping the first occurrence.

    Two nodes are considered duplicates when they share the same
    protocol, server, port and authentication material (see
    :meth:`Node.identity`).
    """
    seen = set()
    unique: List[Node] = []
    for node in nodes:
        key = node.identity()
        if key in seen:
            continue
        seen.add(key)
        unique.append(node)
    return unique
