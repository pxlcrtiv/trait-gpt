"""Collection loading: fixture validation, Reservoir parsing (offline)."""

from __future__ import annotations

import pytest

from trait_gpt.collection import (
    CollectionError,
    ReservoirClient,
    load_collection,
    load_fixture,
    parse_tokens,
)
from trait_gpt.models import Token

SAMPLE_RESERVOIR_PAYLOAD = {
    "collection": {"name": "Bored Ape Yacht Club", "description": "BAYC sample"},
    "tokens": [
        {
            "tokenId": 1,
            "token": {
                "name": "Bored Ape #1",
                "image": "https://img.example/1.png",
                "attributes": [
                    {"key": "background", "value": "blue"},
                    {"key": "fur", "value": "gold"},
                ],
            },
        },
        {
            "tokenId": "0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d:42",
            "token": {
                "name": "Bored Ape #42",
                "image": "https://img.example/42.png",
                "attributes": [{"key": "background", "value": "blue"}],
            },
        },
    ],
}


class TestFixture:
    def test_bundled_fixture_shape(self, pixel_cats) -> None:
        assert pixel_cats.n_tokens == 24
        assert pixel_cats.source == "fixture"
        assert pixel_cats.trait_names == ["background", "skin", "eyes", "accessory"]
        for token in pixel_cats.tokens:
            assert isinstance(token.token_id, int)
            assert token.image.startswith("generated://")

    def test_bundled_fixture_golden_counts(self, pixel_cats) -> None:
        counts = {"background": {}, "accessory": {}}
        for token in pixel_cats.tokens:
            for trait in counts:
                counts[trait][token.traits[trait]] = (
                    counts[trait].get(token.traits[trait], 0) + 1
                )
        assert counts["background"]["gold"] == 1
        assert counts["background"]["sunset"] == 11
        assert counts["accessory"]["crown"] == 1

    def test_missing_file_raises(self) -> None:
        with pytest.raises(CollectionError):
            load_fixture("/nonexistent/collection.json")

    def test_invalid_json_raises(self, tmp_path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        with pytest.raises(CollectionError):
            load_fixture(bad)


class TestParseTokens:
    def test_missing_required_field_rejected(self) -> None:
        with pytest.raises(CollectionError):
            parse_tokens([{"traits": {}}])
        with pytest.raises(CollectionError):
            parse_tokens([{"token_id": 1}])

    def test_non_object_record_rejected(self) -> None:
        with pytest.raises(CollectionError):
            parse_tokens(["nope"])

    def test_token_id_string_forms(self) -> None:
        tokens = parse_tokens(
            [
                {"token_id": "0xabc:42", "traits": {"a": "b"}},
                {"token_id": "43", "traits": {}},
            ]
        )
        assert [t.token_id for t in tokens] == [42, 43]

    def test_image_falls_back_to_image_url(self) -> None:
        tokens = parse_tokens(
            [{"token_id": 1, "traits": {}, "image_url": "https://x/y.png"}]
        )
        assert tokens[0].image == "https://x/y.png"


class TestReservoir:
    def test_requires_key_without_network(self, monkeypatch) -> None:
        monkeypatch.delenv("TRAIT_GPT_RESERVOIR_KEY", raising=False)
        client = ReservoirClient(api_key=None)
        # Key check happens before any HTTP call — must raise without network.
        with pytest.raises(CollectionError, match="TRAIT_GPT_RESERVOIR_KEY"):
            client.load_collection("0xabc")

    def test_parse_payload_offline(self) -> None:
        collection = ReservoirClient(api_key="test-key").parse_payload(
            SAMPLE_RESERVOIR_PAYLOAD
        )
        assert collection.source == "reservoir"
        assert collection.name == "Bored Ape Yacht Club"
        assert [t.token_id for t in collection.tokens] == [1, 42]
        assert collection.tokens[0].traits == {"background": "blue", "fur": "gold"}
        assert collection.tokens[1].traits == {"background": "blue"}
        assert "Bored Ape #42" == collection.tokens[1].name

    def test_http_error_surfaces_as_collection_error(self, monkeypatch) -> None:
        import urllib.error

        client = ReservoirClient(api_key="k")
        # Patch the network layer, NOT _get_json — the mapping logic under
        # test lives in _get_json's except clauses.

        def boom(request, timeout=None):
            raise urllib.error.HTTPError("u", 401, "Unauthorized", {}, None)

        monkeypatch.setattr(urllib.request, "urlopen", boom)
        with pytest.raises(CollectionError, match="401"):
            client.load_collection("0xabc")

    def test_network_error_surfaces_as_collection_error(self, monkeypatch) -> None:
        import urllib.error

        client = ReservoirClient(api_key="k")

        def boom(request, timeout=None):
            raise urllib.error.URLError("connection refused")

        monkeypatch.setattr(urllib.request, "urlopen", boom)
        with pytest.raises(CollectionError, match="unreachable"):
            client.load_collection("0xabc")


class TestLoader:
    def test_load_collection_none_uses_fixture(self) -> None:
        assert load_collection(None).slug == "pixel-cats"

    def test_load_collection_path(self, rare3) -> None:
        loaded = load_collection("tests/fixtures/rare3.json")
        assert loaded.n_tokens == 3
        assert loaded.name == "Rare Three"

    def test_load_collection_missing_path_treats_as_contract(self, monkeypatch) -> None:
        monkeypatch.delenv("TRAIT_GPT_RESERVOIR_KEY", raising=False)
        with pytest.raises(CollectionError, match="TRAIT_GPT_RESERVOIR_KEY"):
            load_collection("/no/such/file.json")