"""Fetch raw subscription content from remote sources."""

from __future__ import annotations

import base64
import binascii
import logging
from typing import Iterable, List

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 15
DEFAULT_HEADERS = {"User-Agent": "free-node-scraper/0.1"}

_NODE_PREFIXES = ("vmess://", "vless://", "trojan://", "ss://", "ssr://")


def _looks_like_plain_nodes(text: str) -> bool:
    for line in text.splitlines():
        line = line.strip()
        if line and line.startswith(_NODE_PREFIXES):
            return True
    return False


def decode_subscription(content: str) -> str:
    """Return plain-text node links from subscription ``content``.

    Subscription content is typically base64 encoded, but some sources
    already provide plain-text node links. This function detects which
    case applies and returns normalized plain text.
    """
    content = content.strip()
    if not content:
        return ""

    if _looks_like_plain_nodes(content):
        return content

    padded = content + "=" * (-len(content) % 4)
    try:
        decoded = base64.b64decode(padded, validate=False).decode(
            "utf-8", errors="ignore"
        )
    except (binascii.Error, ValueError):
        return content

    if _looks_like_plain_nodes(decoded):
        return decoded

    # Neither the original nor the decoded content looks like node
    # links; fall back to whichever is non-empty, preferring the
    # original so callers can still attempt to parse it.
    return content


def fetch_source(url: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Fetch a single subscription source and return decoded node text."""
    response = requests.get(url, timeout=timeout, headers=DEFAULT_HEADERS)
    response.raise_for_status()
    return decode_subscription(response.text)


def fetch_sources(urls: Iterable[str], timeout: int = DEFAULT_TIMEOUT) -> List[str]:
    """Fetch multiple sources, skipping ones that fail."""
    texts = []
    for url in urls:
        url = url.strip()
        if not url or url.startswith("#"):
            continue
        try:
            texts.append(fetch_source(url, timeout=timeout))
        except requests.RequestException as exc:
            logger.warning("Failed to fetch %s: %s", url, exc)
    return texts


def load_source_list(path: str) -> List[str]:
    """Read a newline separated list of subscription URLs from ``path``."""
    with open(path, "r", encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip() and not line.startswith("#")]
