"""Collection loading: bundled fixture (offline, default) or Reservoir API.

The Reservoir client is fully optional — it needs ``TRAIT_GPT_RESERVOIR_KEY``
and a network connection. Without either, the bundled fixture collection
(repo ``data/fixtures/``) gives the same end-to-end demo: rarity table,
attribute tags, and descriptions — zero keys, zero downloads.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

from .models import Collection, Token

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "fixtures" / "pixel-cats.json"
)

RESERVOIR_BASE = "https://api.reservoir.tools"
TOKENS_ENDPOINT = "/tokens/v7"


class CollectionError(RuntimeError):
    """Raised when a collection cannot be loaded."""


def _coerce_token_id(raw: object) -> int:
    """token_id may arrive as int or as a "contract:tokenId" string."""
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        if ":" in raw:
            raw = raw.rsplit(":", 1)[1]
        return int(raw)
    raise CollectionError(f"cannot interpret token_id: {raw!r}")


def parse_tokens(records: list[dict]) -> list[Token]:
    """Validate and normalize raw token records into ``Token`` objects."""
    tokens: list[Token] = []
    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            raise CollectionError(f"token record #{i} is not an object")
        missing = [f for f in ("token_id", "traits") if f not in rec]
        if missing:
            raise CollectionError(
                f"token record #{i} missing required field(s): {', '.join(missing)}"
            )
        traits = rec["traits"]
        if not isinstance(traits, dict):
            raise CollectionError(f"token #{i} 'traits' must be an object")
        tokens.append(
            Token(
                token_id=_coerce_token_id(rec["token_id"]),
                traits={str(k): str(v) for k, v in traits.items()},
                name=str(rec.get("name", "")),
                image=str(rec.get("image", "")) or str(rec.get("image_url", "")),
            )
        )
    return tokens


def load_fixture(path: str | os.PathLike[str] | None = None) -> Collection:
    """Load the bundled fixture collection (deterministic, offline)."""
    p = Path(path) if path else FIXTURE_PATH
    if not p.exists():
        raise CollectionError(f"fixture file not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CollectionError(f"fixture is not valid JSON: {p} ({exc})") from exc
    if not isinstance(data, dict) or "tokens" not in data:
        raise CollectionError(f"fixture missing 'tokens' list: {p}")
    tokens = parse_tokens(data["tokens"])
    if not tokens:
        raise CollectionError(f"fixture has no tokens: {p}")
    return Collection(
        name=str(data.get("name", Path(p).stem)),
        slug=str(data.get("slug", Path(p).stem)),
        description=str(data.get("description", "")),
        tokens=tokens,
        source="fixture",
    )


class ReservoirClient:
    """Minimal Reservoir API client (optional; needs TRAIT_GPT_RESERVOIR_KEY).

    Example::

        client = ReservoirClient(os.environ["TRAIT_GPT_RESERVOIR_KEY"])
        collection = client.load_collection("0xbc4ca0eda7647a8ab7c2061c2e118a18a936f13d")  # BAYC
    """

    def __init__(self, api_key: str | None = None, base_url: str = RESERVOIR_BASE) -> None:
        self.api_key = api_key or os.environ.get("TRAIT_GPT_RESERVOIR_KEY")
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise CollectionError(
                "no Reservoir API key — set TRAIT_GPT_RESERVOIR_KEY or use the "
                "bundled fixture (load_fixture())"
            )
        return {"accept": "application/json", "x-api-key": self.api_key}

    def _get_json(self, path: str, params: dict[str, str]) -> dict:
        url = f"{self.base_url}{path}?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(  # noqa: S310 — https only, key auth
                urllib.request.Request(url, headers=self._headers()), timeout=30
            ) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise CollectionError(f"Reservoir HTTP {exc.code}: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise CollectionError(f"Reservoir unreachable: {exc.reason}") from exc

    def load_collection(self, contract: str, limit: int = 50) -> Collection:
        """Fetch tokens for a collection contract and parse them.

        Tokens are limited to ``limit`` (Reservoir caps at 50/page; this is
        a demo-grade client, not a full indexer — see README caveats).
        """
        payload = self._get_json(
            TOKENS_ENDPOINT,
            {"collection": contract, "limit": str(limit)},
        )
        return self.parse_payload(payload, source=contract)

    def parse_payload(self, payload: dict, source: str = "reservoir") -> Collection:
        """Turn a Reservoir v7 tokens payload into a ``Collection``.

        Pure parsing (no network) — tests cover this offline with a sample
        payload. Trait names arrive split across ``attribute.key`` /
        ``attribute.value``; we merge them into the flat ``traits`` dict.
        """
        records: list[dict] = []
        for item in payload.get("tokens", []):
            rec: dict = {"token_id": item.get("tokenId"), "traits": {}}
            if item.get("token"):
                rec["name"] = item["token"].get("name", "")
                img = item["token"].get("image")
                if isinstance(img, str):
                    rec["image"] = img
            attrs = (item.get("token") or {}).get("attributes") or []
            for attr in attrs:
                key, value = attr.get("key"), attr.get("value")
                if key is not None and value is not None:
                    rec["traits"][str(key)] = str(value)
            if rec["token_id"] is not None:
                records.append(rec)
        tokens = parse_tokens(records)
        return Collection(
            name=str(payload.get("collection", {}).get("name", source)),
            slug=source,
            description=str(payload.get("collection", {}).get("description", "")),
            tokens=tokens,
            source="reservoir",
        )


def load_collection(path_or_contract: str | None = None) -> Collection:
    """Convenience loader: path → fixture; contract + key → Reservoir.

    Order of resolution:
      1. ``path_or_contract`` is an existing file path → fixture.
      2. Otherwise treat it as a Reservoir contract address; requires
         ``TRAIT_GPT_RESERVOIR_KEY``.
      3. Nothing given → bundled fixture.
    """
    if path_or_contract:
        p = Path(path_or_contract)
        if p.exists():
            return load_fixture(p)
        return ReservoirClient().load_collection(path_or_contract)
    return load_fixture()