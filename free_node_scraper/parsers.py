"""Parsers that turn raw proxy node links into a unified :class:`Node`.

Supported protocols: ``vmess``, ``vless``, ``trojan``, ``ss`` (Shadowsocks)
and ``ssr`` (ShadowsocksR).
"""

from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, unquote, urlparse


@dataclass
class Node:
    """A unified representation of a proxy node.

    ``extra`` holds protocol specific fields that are not part of the
    common identity (server/port/auth) but are still needed to render
    the node back into a link or a Clash proxy entry.
    """

    protocol: str
    server: str
    port: int
    name: str = ""
    auth: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)
    raw: str = ""

    def identity(self) -> tuple:
        """Return a tuple used to detect duplicate nodes."""
        return (self.protocol, self.server, self.port, self.auth)


def _b64decode(data: str) -> str:
    """Decode base64 data, tolerating missing padding and url-safe chars."""
    data = data.strip().replace("-", "+").replace("_", "/")
    padding = len(data) % 4
    if padding:
        data += "=" * (4 - padding)
    return base64.b64decode(data).decode("utf-8", errors="ignore")


class ParseError(ValueError):
    """Raised when a node link cannot be parsed."""


def parse_vmess(link: str) -> Node:
    if not link.startswith("vmess://"):
        raise ParseError(f"Not a vmess link: {link!r}")
    payload = link[len("vmess://"):]
    try:
        decoded = _b64decode(payload)
        data = json.loads(decoded)
    except (binascii.Error, ValueError, UnicodeDecodeError) as exc:
        raise ParseError(f"Invalid vmess payload: {exc}") from exc

    server = data.get("add", "")
    try:
        port = int(data.get("port", 0))
    except (TypeError, ValueError):
        port = 0
    uuid = data.get("id", "")

    return Node(
        protocol="vmess",
        server=server,
        port=port,
        name=data.get("ps", ""),
        auth=uuid,
        extra=dict(data),
        raw=link,
    )


def _parse_uri_style(link: str, protocol: str) -> Node:
    """Parse ``protocol://auth@server:port?query#name`` style links."""
    parsed = urlparse(link)
    if parsed.scheme != protocol:
        raise ParseError(f"Not a {protocol} link: {link!r}")

    auth = unquote(parsed.username or "")
    server = parsed.hostname or ""
    port = parsed.port or 0
    name = unquote(parsed.fragment or "")
    query = {k: v[0] for k, v in parse_qs(parsed.query).items()}

    return Node(
        protocol=protocol,
        server=server,
        port=port,
        name=name,
        auth=auth,
        extra=query,
        raw=link,
    )


def parse_vless(link: str) -> Node:
    return _parse_uri_style(link, "vless")


def parse_trojan(link: str) -> Node:
    return _parse_uri_style(link, "trojan")


def parse_ss(link: str) -> Node:
    if not link.startswith("ss://"):
        raise ParseError(f"Not a ss link: {link!r}")

    body = link[len("ss://"):]
    name = ""
    if "#" in body:
        body, frag = body.split("#", 1)
        name = unquote(frag)

    query = {}
    if "?" in body:
        body, qs = body.split("?", 1)
        query = {k: v[0] for k, v in parse_qs(qs).items()}

    if "@" in body:
        # ******server:port
        userinfo, hostport = body.rsplit("@", 1)
        try:
            userinfo = _b64decode(userinfo)
        except (binascii.Error, UnicodeDecodeError):
            userinfo = unquote(userinfo)
        server, _, port = hostport.partition(":")
    else:
        # ******server:port)
        try:
            decoded = _b64decode(body)
        except (binascii.Error, UnicodeDecodeError) as exc:
            raise ParseError(f"Invalid ss payload: {exc}") from exc
        userinfo, _, hostport = decoded.rpartition("@")
        server, _, port = hostport.partition(":")

    method, _, password = userinfo.partition(":")

    try:
        port_num = int(port)
    except ValueError:
        port_num = 0

    return Node(
        protocol="ss",
        server=server,
        port=port_num,
        name=name,
        auth=f"{method}:{password}",
        extra={"method": method, "password": password, **query},
        raw=link,
    )


def parse_ssr(link: str) -> Node:
    if not link.startswith("ssr://"):
        raise ParseError(f"Not a ssr link: {link!r}")

    payload = link[len("ssr://"):]
    try:
        decoded = _b64decode(payload)
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise ParseError(f"Invalid ssr payload: {exc}") from exc

    main, _, params_part = decoded.partition("/?")
    parts = main.split(":")
    if len(parts) != 6:
        raise ParseError(f"Malformed ssr payload: {decoded!r}")

    server, port, protocol, method, obfs, password_b64 = parts
    try:
        password = _b64decode(password_b64)
    except (binascii.Error, UnicodeDecodeError):
        password = password_b64

    params = {k: v[0] for k, v in parse_qs(params_part).items()}
    name = ""
    if "remarks" in params:
        try:
            name = _b64decode(params["remarks"])
        except (binascii.Error, UnicodeDecodeError):
            name = params["remarks"]

    try:
        port_num = int(port)
    except ValueError:
        port_num = 0

    return Node(
        protocol="ssr",
        server=server,
        port=port_num,
        name=name,
        auth=f"{method}:{password}",
        extra={
            "protocol_param": protocol,
            "method": method,
            "obfs": obfs,
            "password": password,
            **params,
        },
        raw=link,
    )


_PARSERS = {
    "vmess://": parse_vmess,
    "vless://": parse_vless,
    "trojan://": parse_trojan,
    "ss://": parse_ss,
    "ssr://": parse_ssr,
}


def parse_link(link: str) -> Optional[Node]:
    """Parse a single node link, returning ``None`` if unsupported/invalid."""
    link = link.strip()
    if not link:
        return None
    for prefix, parser in _PARSERS.items():
        if link.startswith(prefix):
            try:
                return parser(link)
            except ParseError:
                return None
    return None


def parse_links(text: str) -> list:
    """Parse every recognizable node link found in ``text``."""
    nodes = []
    for line in text.splitlines():
        node = parse_link(line)
        if node is not None:
            nodes.append(node)
    return nodes
