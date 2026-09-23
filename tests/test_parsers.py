import base64
import json

from free_node_scraper.parsers import (
    Node,
    parse_link,
    parse_links,
    parse_ss,
    parse_ssr,
    parse_trojan,
    parse_vless,
    parse_vmess,
)

VMESS_LINK = (
    "vmess://eyJ2IjogIjIiLCAicHMiOiAiVGVzdFZtZXNzIiwgImFkZCI6ICJ2bWVzcy5leGFtcGxlLmNv"
    "bSIsICJwb3J0IjogIjQ0MyIsICJpZCI6ICJiODMxMzgxZC02MzI0LTRkNTMtYWQ0Zi04Y2RhNDhiMzA4"
    "MTEiLCAiYWlkIjogIjAiLCAibmV0IjogIndzIiwgInR5cGUiOiAibm9uZSIsICJob3N0IjogInZtZXNz"
    "LmV4YW1wbGUuY29tIiwgInBhdGgiOiAiL3dzIiwgInRscyI6ICJ0bHMifQ=="
)
SS_LINK = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQxMjM@ss.example.com:8388#TestSS"
SSR_LINK = (
    "ssr://c3NyLmV4YW1wbGUuY29tOjg5ODk6b3JpZ2luOmFlcy0yNTYtY2ZiOnBsYWluOmNHRnpjM2R2"
    "Y21ReE1qTS8/cmVtYXJrcz1WR1Z6ZEZOVFVn"
)
VLESS_LINK = (
    "vless://b831381d-6324-4d53-ad4f-8cda48b30811@vless.example.com:443"
    "?type=ws&security=tls&path=%2Fws&sni=vless.example.com#TestVless"
)
TROJAN_LINK = "trojan://s3cr3t@trojan.example.com:443?sni=trojan.example.com#TestTrojan"


def test_parse_vmess():
    node = parse_vmess(VMESS_LINK)
    assert node.protocol == "vmess"
    assert node.server == "vmess.example.com"
    assert node.port == 443
    assert node.auth == "b831381d-6324-4d53-ad4f-8cda48b30811"
    assert node.name == "TestVmess"
    assert node.extra["net"] == "ws"


def test_parse_vless():
    node = parse_vless(VLESS_LINK)
    assert node.protocol == "vless"
    assert node.server == "vless.example.com"
    assert node.port == 443
    assert node.auth == "b831381d-6324-4d53-ad4f-8cda48b30811"
    assert node.name == "TestVless"
    assert node.extra["security"] == "tls"
    assert node.extra["path"] == "/ws"


def test_parse_trojan():
    node = parse_trojan(TROJAN_LINK)
    assert node.protocol == "trojan"
    assert node.server == "trojan.example.com"
    assert node.port == 443
    assert node.auth == "s3cr3t"
    assert node.name == "TestTrojan"
    assert node.extra["sni"] == "trojan.example.com"


def test_parse_ss():
    node = parse_ss(SS_LINK)
    assert node.protocol == "ss"
    assert node.server == "ss.example.com"
    assert node.port == 8388
    assert node.name == "TestSS"
    assert node.extra["method"] == "aes-256-gcm"
    assert node.extra["password"] == "password123"


def test_parse_ss_alternate_encoding():
    body = base64.b64encode(b"aes-256-gcm:pw@ss2.example.com:9000").decode()
    link = f"ss://{body}#Alt"
    node = parse_ss(link)
    assert node.server == "ss2.example.com"
    assert node.port == 9000
    assert node.extra["password"] == "pw"


def test_parse_ssr():
    node = parse_ssr(SSR_LINK)
    assert node.protocol == "ssr"
    assert node.server == "ssr.example.com"
    assert node.port == 8989
    assert node.name == "TestSSR"
    assert node.extra["method"] == "aes-256-cfb"
    assert node.extra["password"] == "password123"
    assert node.extra["obfs"] == "plain"


def test_parse_link_dispatches_by_prefix():
    node = parse_link(VMESS_LINK)
    assert isinstance(node, Node)
    assert node.protocol == "vmess"

    assert parse_link("not-a-node-link") is None
    assert parse_link("") is None


def test_parse_links_from_multiline_text():
    text = "\n".join([VMESS_LINK, SS_LINK, "garbage", TROJAN_LINK, VLESS_LINK, SSR_LINK])
    nodes = parse_links(text)
    protocols = sorted(n.protocol for n in nodes)
    assert protocols == ["ss", "ssr", "trojan", "vless", "vmess"]


def test_parse_vmess_invalid_payload_returns_none_via_parse_link():
    assert parse_link("vmess://not-valid-base64!!") is None
