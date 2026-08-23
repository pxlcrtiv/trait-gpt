"""Core data shapes for trait-gpt."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Required keys on every token record in a collection JSON.
TOKEN_REQUIRED_FIELDS = ("token_id", "traits")
# Optional keys.
TOKEN_OPTIONAL_FIELDS = ("name", "image", "attributes")

# Built-in visual attribute candidates for CLIP zero-shot tagging.
DEFAULT_ATTRIBUTE_CANDIDATES = [
    "pixel art",
    "cartoon character",
    "cat face",
    "cute",
    "minimalist",
    "vintage",
    "watercolor painting",
    "cyberpunk",
    "steampunk",
    "3D render",
    "photorealistic",
    "anime",
    "meme",
    "lustrous gold",
    "royal crown",
    "colorful",
    "dark moody",
    "sunset lighting",
    "neon lights",
    "whimsical",
]


@dataclass(frozen=True)
class TraitCount:
    """How often one trait value occurs in a collection."""

    trait: str
    value: str
    count: int
    frequency: float  # count / n_tokens


@dataclass(frozen=True)
class RarityRank:
    """Per-token rarity result."""

    token_id: int
    score: float  # trait-count-normalized rarity score (mean trait rarity)
    score_sum: float  # unnormalized sum of trait rarities
    rank: int  # competition rank: 1 = rarest; ties share the rank
    percentile: float  # 0.0 (rarest) .. 100.0 (most common)

    def as_dict(self) -> dict[str, Any]:
        return {
            "token_id": self.token_id,
            "score": self.score,
            "score_sum": self.score_sum,
            "rank": self.rank,
            "percentile": self.percentile,
        }


@dataclass
class Token:
    """One NFT token with its traits."""

    token_id: int
    traits: dict[str, str] = field(default_factory=dict)
    name: str = ""
    image: str = ""  # URL, local path, or "generated://<seed>"

    def display_name(self) -> str:
        return self.name or f"#{self.token_id}"


@dataclass
class Collection:
    """A parsed NFT collection."""

    name: str
    slug: str
    description: str
    tokens: list[Token]
    source: str  # "fixture" | "reservoir"

    @property
    def n_tokens(self) -> int:
        return len(self.tokens)

    @property
    def trait_names(self) -> list[str]:
        names: list[str] = []
        for t in self.tokens:
            for k in t.traits:
                if k not in names:
                    names.append(k)
        return names


@dataclass(frozen=True)
class TaggedAttributes:
    """Result of CLIP (or keyword-fallback) attribute tagging."""

    token_id: int
    tags: list[str]
    scores: dict[str, float]  # label -> score, when available
    method: str  # "clip" | "keyword"

    def as_dict(self) -> dict[str, Any]:
        return {
            "token_id": self.token_id,
            "tags": self.tags,
            "scores": self.scores,
            "method": self.method,
        }


@dataclass(frozen=True)
class Description:
    """Result of per-token description generation."""

    token_id: int
    text: str
    method: str  # "template" | "blip"

    def as_dict(self) -> dict[str, Any]:
        return {"token_id": self.token_id, "text": self.text, "method": self.method}