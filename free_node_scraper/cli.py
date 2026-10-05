"""Command line entry: python -m free_node_scraper.cli URL... -o clash.yaml"""
import argparse
import sys
from typing import List, Optional

from .checker import filter_alive
from .dedup import dedup
from .fetcher import fetch
from .parsers import parse_subscription
from .writer import to_clash


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Aggregate free nodes into a Clash config")
    ap.add_argument("urls", nargs="+", help="subscription URLs")
    ap.add_argument("-o", "--output", default="clash.yaml")
    ap.add_argument("--timeout", type=float, default=5.0, help="TCP check timeout (s)")
    ap.add_argument("--workers", type=int, default=50)
    ap.add_argument("--max-latency", type=float, default=None, help="drop nodes slower than N ms")
    ap.add_argument("--no-check", action="store_true", help="skip availability check")
    args = ap.parse_args(argv)

    proxies = []
    for url in args.urls:
        try:
            proxies += parse_subscription(fetch(url))
        except Exception as exc:  # network/parse errors shouldn't abort other sources
            print(f"skip {url}: {exc}", file=sys.stderr)
    proxies = dedup(proxies)
    total = len(proxies)
    if not args.no_check:
        proxies = filter_alive(proxies, args.timeout, args.workers, args.max_latency)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(to_clash(proxies))
    print(f"{len(proxies)}/{total} nodes written to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
