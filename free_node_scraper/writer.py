"""Render proxies as a Clash configuration (YAML, no external deps)."""
import json
from typing import Dict, List

_q = lambda v: json.dumps(v, ensure_ascii=False)  # JSON scalars are valid YAML


def _unique_names(proxies: List[Dict]) -> List[Dict]:
    used, out = {}, []
    for p in proxies:
        n = used.get(p["name"], 0)
        used[p["name"]] = n + 1
        out.append(dict(p, name=p["name"] if n == 0 else f'{p["name"]}-{n + 1}'))
    return out


def to_clash(proxies: List[Dict]) -> str:
    proxies = _unique_names(proxies)
    names = [_q(p["name"]) for p in proxies]
    lines = ["mixed-port: 7890", "allow-lan: false", "mode: rule", "log-level: info",
             "proxies:"]
    lines += [f"  - {json.dumps(p, ensure_ascii=False)}" for p in proxies]
    group_proxies = ", ".join(names)
    lines += [
        "proxy-groups:",
        f'  - {{"name": "Auto", "type": "url-test", "url": "http://www.gstatic.com/generate_204", "interval": 300, "proxies": [{group_proxies}]}}',
        f'  - {{"name": "Proxy", "type": "select", "proxies": ["Auto", {group_proxies}]}}'
        if names else '  - {"name": "Proxy", "type": "select", "proxies": ["DIRECT"]}',
        "rules:",
        "  - GEOIP,CN,DIRECT",
        "  - MATCH,Proxy",
    ]
    if not names:  # url-test group requires proxies
        del lines[lines.index("proxy-groups:") + 1]
    return "\n".join(lines) + "\n"
