"""Command line interface for the free node scraper."""

from __future__ import annotations

import argparse
import logging
import os
import sys

from .dedup import dedup_nodes
from .fetcher import fetch_sources, load_source_list
from .parsers import parse_links
from .writer import write_clash_config, write_subscription


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch, parse, deduplicate and export free proxy nodes."
    )
    parser.add_argument(
        "--sources",
        default="sources.txt",
        help="Path to a file containing one subscription URL per line (default: sources.txt)",
    )
    parser.add_argument(
        "--output",
        default="output",
        help="Directory to write generated subscription files to (default: output)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=15,
        help="Per-request timeout in seconds (default: 15)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser


def run(argv=None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    logger = logging.getLogger(__name__)

    try:
        urls = load_source_list(args.sources)
    except OSError as exc:
        logger.error("Could not read sources file %s: %s", args.sources, exc)
        return 1

    if not urls:
        logger.warning("No subscription sources found in %s", args.sources)

    texts = fetch_sources(urls, timeout=args.timeout)

    nodes = []
    for text in texts:
        nodes.extend(parse_links(text))

    unique_nodes = dedup_nodes(nodes)
    logger.info(
        "Fetched %d nodes from %d source(s), %d unique after dedup",
        len(nodes),
        len(urls),
        len(unique_nodes),
    )

    os.makedirs(args.output, exist_ok=True)
    subscription_path = os.path.join(args.output, "subscription.txt")
    clash_path = os.path.join(args.output, "clash.yaml")

    write_subscription(unique_nodes, subscription_path)
    write_clash_config(unique_nodes, clash_path)

    logger.info("Wrote %s and %s", subscription_path, clash_path)
    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
