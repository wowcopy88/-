import base64
import json
import socket
import threading

from free_node_scraper.checker import filter_alive
from free_node_scraper.dedup import dedup
from free_node_scraper.parsers import parse_subscription
from free_node_scraper.writer import to_clash

b64 = lambda s: base64.b64encode(s.encode()).decode()
VMESS = "vmess://" + b64(json.dumps({"add": "1.2.3.4", "port": "443", "id": "u-1", "ps": "vm", "net": "ws", "tls": "tls", "path": "/w"}))
SS = "ss://" + b64("aes-256-gcm:pw") + "@5.6.7.8:8388#ss1"
TROJAN = "trojan://pass@9.9.9.9:443?sni=x.com#tj"
VLESS = "vless://uuid-1@8.8.8.8:443?security=tls&type=ws&path=%2Fa#vl"


def test_parse_plain_and_base64():
    body = "\n".join([VMESS, SS, TROJAN, VLESS, "junk"])
    for text in (body, b64(body)):
        ps = parse_subscription(text)
        assert [p["type"] for p in ps] == ["vmess", "ss", "trojan", "vless"]
    assert ps[1]["cipher"] == "aes-256-gcm" and ps[1]["password"] == "pw"
    assert ps[0]["network"] == "ws"


def test_dedup():
    ps = parse_subscription("\n".join([SS, SS, TROJAN]))
    assert len(dedup(ps)) == 2


def test_filter_alive_and_writer():
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen()
    port = srv.getsockname()[1]
    threading.Thread(target=lambda: srv.accept(), daemon=True).start()
    good = {"name": "ok", "type": "trojan", "server": "127.0.0.1", "port": port, "password": "x"}
    bad = {"name": "bad", "type": "trojan", "server": "127.0.0.1", "port": 1, "password": "x"}
    alive = filter_alive([bad, good], timeout=1)
    srv.close()
    assert alive == [good]
    out = to_clash(alive)
    assert "proxies:" in out and '"ok"' in out and "MATCH,Proxy" in out
    assert "proxy-groups:" in to_clash([])
