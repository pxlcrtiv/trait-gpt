"""CLI tests — run the argparse entry point in-process and assert on output."""

from __future__ import annotations

import json

import pytest

from trait_gpt.cli import main


@pytest.fixture
def fixture_flag() -> list[str]:
    return ["--collection", "tests/fixtures/rare3.json"]


def test_cli_rank_json(fixture_flag, capsys) -> None:
    rc = main([*fixture_flag, "rank", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["n_tokens"] == 3
    assert out["rankings"][0]["token_id"] == 1
    assert [r["rank"] for r in out["rankings"]] == [1, 1, 3]


def test_cli_rank_text_columns(capsys) -> None:
    rc = main(["--collection", "tests/fixtures/rare3.json", "rank", "--top", "1"])
    captured = capsys.readouterr().out
    assert rc == 0
    assert "score" in captured and "rank" in captured and "#1" in captured


def test_cli_stats(fixture_flag, capsys) -> None:
    rc = main([*fixture_flag, "stats"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "background" in out
    assert "3 tokens" in out


def test_cli_describe(fixture_flag, capsys) -> None:
    rc = main([*fixture_flag, "describe", "2"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "[template]" in out
    assert "red" in out  # token 2 has background=red


def test_cli_describe_unknown_token(fixture_flag) -> None:
    with pytest.raises(SystemExit):
        main([*fixture_flag, "describe", "99"])


def test_cli_tags_keyword_when_clip_disabled(fixture_flag, monkeypatch, capsys) -> None:
    monkeypatch.setenv("TRAIT_GPT_CLIP", "0")
    rc = main([*fixture_flag, "tags", "3", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["method"] == "keyword"
    assert isinstance(out["tags"], list)


def test_cli_default_collection_is_fixture(capsys) -> None:
    """No --collection flag → bundled Pixel Cats fixture (zero keys)."""
    rc = main(["rank", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["collection"] == "Pixel Cats"
    assert out["n_tokens"] == 24
    assert out["rankings"][0]["token_id"] == 7