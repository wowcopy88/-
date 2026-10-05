"""Parse proxy share links (ss/vmess/trojan/vless) into Clash proxy dicts."""
import base64
import json
from typing import Dict, List, Optional
from urllib.parse import parse_qs, unquote, urlsplit


def _b64decode(data: str) -> str:
    data = data.strip().replace("-", "+").replace("_", "/")
    data += "=" * (-len(data) % 4)
    return base64.b64decode(data).decode("utf-8", errors="replace")


def _name(default: str, fragment: str) -> str:
    return unquote(fragment) if fragment else default


def parse_ss(link: str) -> Optional[Dict]:
    parts = urlsplit(link)
    body = parts.netloc + parts.path
    if "@" not in body:
        body = _b64decode(body)
    userinfo, _, hostport = body.rpartition("@")
    if ":" not in userinfo:
        userinfo = _b64decode(userinfo)
    cipher, _, password = userinfo.partition(":")
    host, _, port = hostport.rstrip("/").rpartition(":")
    if not (cipher and host and port.isdigit()):
        return None
    return {"name": _name(f"{host}:{port}", parts.fragment), "type": "ss",
            "server": host.strip("[]"), "port": int(port),
            "cipher": cipher, "password": unquote(password)}


def parse_vmess(link: str) -> Optional[Dict]:
    cfg = json.loads(_b64decode(link[len("vmess://"):]))
    host, port = cfg.get("add"), cfg.get("port")
    if not host or not str(port).isdigit() or not cfg.get("id"):
        return None
    proxy = {"name": cfg.get("ps") or f"{host}:{port}", "type": "vmess",
             "server": host, "port": int(port), "uuid": cfg["id"],
             "alterId": int(cfg.get("aid") or 0), "cipher": cfg.get("scy") or "auto",
             "tls": cfg.get("tls") == "tls"}
    net = cfg.get("net") or "tcp"
    if net != "tcp":
        proxy["network"] = net
    if net == "ws":
        proxy["ws-opts"] = {"path": cfg.get("path") or "/",
                            "headers": {"Host": cfg.get("host") or ""}}
    if cfg.get("sni"):
        proxy["servername"] = cfg["sni"]
    return proxy


def _parse_url_style(link: str, kind: str) -> Optional[Dict]:
    parts = urlsplit(link)
    host, port, secret = parts.hostname, parts.port, unquote(parts.username or "")
    if not (host and port and secret):
        return None
    q = {k: v[0] for k, v in parse_qs(parts.query).items()}
    proxy = {"name": _name(f"{host}:{port}", parts.fragment), "type": kind,
             "server": host, "port": port}
    proxy["uuid" if kind == "vless" else "password"] = secret
    tls = q.get("security") == "tls" or kind == "trojan"
    if tls:
        proxy["tls"] = True
    if q.get("sni") or q.get("peer"):
        proxy["servername" if kind == "vless" else "sni"] = q.get("sni") or q.get("peer")
    if q.get("allowInsecure") == "1" or q.get("insecure") == "1":
        proxy["skip-cert-verify"] = True
    if q.get("type") == "ws":
        proxy["network"] = "ws"
        proxy["ws-opts"] = {"path": q.get("path", "/"),
                            "headers": {"Host": q.get("host", "")}}
    return proxy


def parse_link(link: str) -> Optional[Dict]:
    link = link.strip()
    try:
        if link.startswith("ss://"):
            return parse_ss(link)
        if link.startswith("vmess://"):
            return parse_vmess(link)
        if link.startswith("trojan://"):
            return _parse_url_style(link, "trojan")
        if link.startswith("vless://"):
            return _parse_url_style(link, "vless")
    except (ValueError, KeyError, TypeError):
        return None
    return None


def parse_subscription(text: str) -> List[Dict]:
    """Parse a subscription body (plain links or base64-encoded links)."""
    if "://" not in text.split("\n", 1)[0]:
        try:
            text = _b64decode("".join(text.split()))
        except ValueError:
            pass
    proxies = (parse_link(line) for line in text.splitlines() if line.strip())
    return [p for p in proxies if p]
