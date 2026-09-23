import base64
import os
from unittest.mock import Mock, patch

import yaml

from free_node_scraper.cli import run

SS_LINK = "ss://YWVzLTI1Ni1nY206cGFzc3dvcmQxMjM@ss.example.com:8388#TestSS"


def test_cli_end_to_end(tmp_path):
    sources_file = tmp_path / "sources.txt"
    sources_file.write_text("https://example.com/sub\n")

    output_dir = tmp_path / "out"

    encoded = base64.b64encode(SS_LINK.encode()).decode()
    mock_response = Mock()
    mock_response.text = encoded
    mock_response.raise_for_status = Mock()

    with patch("free_node_scraper.fetcher.requests.get", return_value=mock_response):
        exit_code = run(
            [
                "--sources",
                str(sources_file),
                "--output",
                str(output_dir),
            ]
        )

    assert exit_code == 0
    assert os.path.exists(output_dir / "subscription.txt")
    assert os.path.exists(output_dir / "clash.yaml")

    with open(output_dir / "clash.yaml", "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    assert len(config["proxies"]) == 1
    assert config["proxies"][0]["type"] == "ss"


def test_cli_missing_sources_file_returns_error(tmp_path):
    missing = tmp_path / "does-not-exist.txt"
    exit_code = run(["--sources", str(missing), "--output", str(tmp_path / "out")])
    assert exit_code == 1
