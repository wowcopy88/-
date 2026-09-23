from free_node_scraper.dedup import dedup_nodes
from free_node_scraper.parsers import Node


def make_node(server="1.1.1.1", port=443, auth="uuid-1", protocol="vmess", raw=None):
    return Node(
        protocol=protocol,
        server=server,
        port=port,
        name="n",
        auth=auth,
        raw=raw or f"{protocol}://{server}:{port}",
    )


def test_dedup_removes_exact_duplicates():
    nodes = [make_node(), make_node(), make_node()]
    result = dedup_nodes(nodes)
    assert len(result) == 1


def test_dedup_keeps_first_occurrence():
    first = make_node(raw="first")
    duplicate = make_node(raw="duplicate")
    result = dedup_nodes([first, duplicate])
    assert len(result) == 1
    assert result[0].raw == "first"


def test_dedup_distinguishes_different_identities():
    nodes = [
        make_node(server="1.1.1.1", port=443, auth="a"),
        make_node(server="1.1.1.1", port=444, auth="a"),
        make_node(server="1.1.1.2", port=443, auth="a"),
        make_node(server="1.1.1.1", port=443, auth="b"),
        make_node(server="1.1.1.1", port=443, auth="a", protocol="ss"),
    ]
    result = dedup_nodes(nodes)
    assert len(result) == 5


def test_dedup_empty_input():
    assert dedup_nodes([]) == []
