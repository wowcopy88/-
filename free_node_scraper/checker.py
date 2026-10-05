"""TCP-connect availability and latency check."""
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional


def tcp_latency(host: str, port: int, timeout: float = 5.0) -> Optional[float]:
    """Return connect latency in ms, or None if unreachable."""
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return (time.monotonic() - start) * 1000
    except OSError:
        return None


def filter_alive(proxies: List[Dict], timeout: float = 5.0, workers: int = 50,
                 max_latency: Optional[float] = None) -> List[Dict]:
    """Keep reachable proxies, sorted by latency (ascending)."""
    with ThreadPoolExecutor(max_workers=workers) as pool:
        latencies = list(pool.map(
            lambda p: tcp_latency(p["server"], p["port"], timeout), proxies))
    alive = [(lat, p) for lat, p in zip(latencies, proxies)
             if lat is not None and (max_latency is None or lat <= max_latency)]
    alive.sort(key=lambda x: x[0])
    return [p for _, p in alive]
