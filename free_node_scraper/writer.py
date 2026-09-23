"""Write aggregated nodes out as subscription files."""

from __future__ import annotations

import base64
from typing import Any, Dict, Iterable, List

import yaml

from .parsers import Node


def write_subscription(nodes: Iterable[Node], path: str) -> None:
    """Write a base64-encoded subscription file made of raw node links."""
    raw_links = "\n".join(node.raw for node in nodes if node.raw)
    encoded = base64.b64encode(raw_links.encode("utf-8")).decode("ascii")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(encoded)


def _node_to_clash_proxy(node: Node, index: int) -> Dict[str, Any]:
    name = node.name or f"{node.protocol}-{node.server}-{node.port}-{index}"
    proxy: Dict[str, Any] = {
        "name": name,
        "server": node.server,
        "port": node.port,
    }

    if node.protocol == "vmess":
        extra = node.extra
        proxy.update(
            {
                "type": "vmess",
                "uuid": extra.get("id", ""),
                "alterId": int(extra.get("aid", 0) or 0),
                "cipher": extra.get("scy", "auto"),
                "network": extra.get("net", "tcp"),
                "tls": extra.get("tls") == "tls",
            }
        )
        if extra.get("net") == "ws":
            proxy["ws-opts"] = {
                "path": extra.get("path", ""),
                "headers": {"Host": extra.get("host", "")},
            }
    elif node.protocol == "vless":
        extra = node.extra
        proxy.update(
            {
                "type": "vless",
                "uuid": node.auth,
                "network": extra.get("type", "tcp"),
                "tls": extra.get("security") == "tls",
            }
        )
        if extra.get("sni"):
            proxy["servername"] = extra["sni"]
        if extra.get("flow"):
            proxy["flow"] = extra["flow"]
    elif node.protocol == "trojan":
        extra = node.extra
        proxy.update(
            {
                "type": "trojan",
                "password": node.auth,
            }
        )
        if extra.get("sni"):
            proxy["sni"] = extra["sni"]
    elif node.protocol == "ss":
        extra = node.extra
        proxy.update(
            {
                "type": "ss",
                "cipher": extra.get("method", ""),
                "password": extra.get("password", ""),
            }
        )
    elif node.protocol == "ssr":
        extra = node.extra
        proxy.update(
            {
                "type": "ssr",
                "cipher": extra.get("method", ""),
                "password": extra.get("password", ""),
                "protocol": extra.get("protocol_param", ""),
                "obfs": extra.get("obfs", ""),
            }
        )

    return proxy


def build_clash_config(nodes: List[Node]) -> Dict[str, Any]:
    proxies = [_node_to_clash_proxy(node, idx) for idx, node in enumerate(nodes)]
    proxy_names = [proxy["name"] for proxy in proxies]
    return {
        "proxies": proxies,
        "proxy-groups": [
            {
                "name": "auto",
                "type": "select",
                "proxies": proxy_names,
            }
        ],
        "rules": ["MATCH,auto"],
    }


def write_clash_config(nodes: Iterable[Node], path: str) -> None:
    config = build_clash_config(list(nodes))
    with open(path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, allow_unicode=True, sort_keys=False)
