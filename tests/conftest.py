"""Shared fixtures for the test suite."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trait_gpt.collection import load_fixture
from trait_gpt.models import Collection, Token

FIXTURES = Path(__file__).parent / "fixtures"
RARE3 = FIXTURES / "rare3.json"


@pytest.fixture
def rare3() -> Collection:
    """The handcrafted 3-token golden collection (see test_rarity.py)."""
    return load_fixture(RARE3)


@pytest.fixture
def pixel_cats() -> Collection:
    """The bundled 24-token demo fixture."""
    return load_fixture()


@pytest.fixture
def token() -> Token:
    return Token(
        token_id=7,
        traits={
            "background": "gold",
            "skin": "black",
            "eyes": "sapphire",
            "accessory": "crown",
        },
        name="Pixel Cat #7",
        image="generated://1007",
    )


def load_test_collection(name: str) -> Collection:
    """Load any JSON under tests/fixtures (used by collection tests)."""
    return load_fixture(FIXTURES / name)


def raw_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))