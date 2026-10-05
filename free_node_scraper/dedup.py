"""Remove duplicate proxies."""
from typing import Dict, List


def dedup(proxies: List[Dict]) -> List[Dict]:
    seen, out = set(), []
    for p in proxies:
        key = (p["type"], p["server"].lower(), p["port"],
               p.get("uuid") or p.get("password"))
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out
