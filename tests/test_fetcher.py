import base64
from unittest.mock import Mock, patch

import pytest
import requests

from free_node_scraper.fetcher import (
    decode_subscription,
    fetch_source,
    fetch_sources,
    load_source_list,
)


def test_decode_subscription_plain_text_passthrough():
    text = "vmess://abc\nss://def"
    assert decode_subscription(text) == text


def test_decode_subscription_base64():
    plain = "vmess://abc\nss://def"
    encoded = base64.b64encode(plain.encode()).decode()
    assert decode_subscription(encoded) == plain


def test_decode_subscription_empty():
    assert decode_subscription("") == ""
    assert decode_subscription("   ") == ""


def test_load_source_list(tmp_path):
    source_file = tmp_path / "sources.txt"
    source_file.write_text("# comment\nhttps://a.example.com\n\nhttps://b.example.com\n")
    urls = load_source_list(str(source_file))
    assert urls == ["https://a.example.com", "https://b.example.com"]


def test_fetch_source_decodes_response():
    plain = "ss://xyz"
    encoded = base64.b64encode(plain.encode()).decode()
    mock_response = Mock()
    mock_response.text = encoded
    mock_response.raise_for_status = Mock()

    with patch("free_node_scraper.fetcher.requests.get", return_value=mock_response) as get:
        result = fetch_source("https://example.com/sub")
        get.assert_called_once()
        assert result == plain


def test_fetch_sources_skips_failures():
    def side_effect(url, timeout, headers):
        if "bad" in url:
            raise requests.RequestException("boom")
        response = Mock()
        response.text = base64.b64encode(b"vmess://ok").decode()
        response.raise_for_status = Mock()
        return response

    with patch("free_node_scraper.fetcher.requests.get", side_effect=side_effect):
        results = fetch_sources(["https://good.example.com", "https://bad.example.com"])
    assert results == ["vmess://ok"]
