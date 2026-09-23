import base64
import os

import yaml

from free_node_scraper.parsers import parse_links
from free_node_scraper.writer import build_clash_config, write_clash_config, write_subscription

VMESS_LINK = (
    "vmess://eyJ2IjogIjIiLCAicHMiOiAiVGVzdFZtZXNzIiwgImFkZCI6ICJ2bWVzcy5leGFtcGxlLmNv"
    "bSIsICJwb3J0IjogIjQ0MyIsICJpZCI6ICJiODMxMzgxZC02MzI0LTRkNTMtYWQ0Zi04Y2RhNDhiMzA4"
    "MTEiLCAiYWlkIjogIjAiLCAibmV0IjogIndzIiwgInR5cGUiOiAibm9uZSIsICJob3N0IjogInZtZXNz"
    "LmV4YW1wbGUuY29tIiwgInBhdGgiOiAiL3dzIiwgInRscyI6ICJ0bHMifQ=="
)
SS_LINK = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQxMjM@ss.example.com:8388#TestSS"
TROJAN_LINK = "trojan://s3cr3t@trojan.example.com:443?sni=trojan.example.com#TestTrojan"


def test_write_subscription_roundtrip(tmp_path):
    nodes = parse_links("\n".join([VMESS_LINK, SS_LINK]))
    out_file = tmp_path / "subscription.txt"
    write_subscription(nodes, str(out_file))

    encoded = out_file.read_text()
    decoded = base64.b64decode(encoded).decode("utf-8")
    assert VMESS_LINK in decoded
    assert SS_LINK in decoded


def test_build_clash_config_contains_expected_proxy_fields():
    nodes = parse_links("\n".join([VMESS_LINK, SS_LINK, TROJAN_LINK]))
    config = build_clash_config(nodes)

    assert "proxies" in config
    assert len(config["proxies"]) == 3

    by_type = {p["type"]: p for p in config["proxies"]}
    assert by_type["vmess"]["uuid"] == "b831381d-6324-4d53-ad4f-8cda48b30811"
    assert by_type["vmess"]["network"] == "ws"
    assert by_type["ss"]["password"] == "password123"
    assert by_type["trojan"]["password"] == "s3cr3t"

    group_names = config["proxy-groups"][0]["proxies"]
    assert set(group_names) == {p["name"] for p in config["proxies"]}


def test_write_clash_config_produces_valid_yaml(tmp_path):
    nodes = parse_links("\n".join([VMESS_LINK, SS_LINK]))
    out_file = tmp_path / "clash.yaml"
    write_clash_config(nodes, str(out_file))

    assert os.path.exists(out_file)
    with open(out_file, "r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    assert len(loaded["proxies"]) == 2
