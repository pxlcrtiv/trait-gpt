"""CLIP zero-shot attribute tags — with a zero-download keyword fallback.

Primary path (``method="clip"``): OpenAI CLIP ViT-B/32 runs on CPU via
``transformers`` and scores the token image against a fixed list of visual
attribute candidates (e.g. "pixel art", "royal crown", "vaporwave"). The
top candidates become the tags. The model downloads once on first use
(~600 MB) and is then cached.

Fallback path (``method="keyword"``): if the CLIP model is not present in
the Hugging Face cache (or downloads are disabled), tags are derived
deterministically from the token's *traits* through a small curated
trait→attribute map. No network, no model, no keys — the demo never
depends on CLIP being installed.

Every result carries its method, so UIs and logs can label which path ran.
"""

from __future__ import annotations

import os
from pathlib import Path

from .models import DEFAULT_ATTRIBUTE_CANDIDATES, TaggedAttributes, Token

CLIP_MODEL = "openai/clip-vit-base-patch32"
_CLIP_WEIGHTS = "pytorch_model.bin"
CLIP_CACHE_MARKER = Path.home() / ".cache" / "huggingface" / "hub" / (
    "models--openai--clip-vit-base-patch32"
)


def _model_complete(marker: Path, weights_name: str) -> bool:
    """True when the model is fully present in the HF cache.

    The marker directory exists while a download is *in progress*, so we
    additionally require the weights file — a partial download must not
    count as "cached" (it would make tests hang mid-download).
    """
    if not marker.exists():
        return False
    for snapshot in marker.glob("snapshots/*"):
        if (snapshot / weights_name).is_file():
            return True
    # Some models store weights as the snapshot's only file set; accept an
    # empty snapshot dir only if the marker is fully committed (no
    # *.incomplete files anywhere under it).
    if list(marker.rglob("*.incomplete")):
        return False
    return any(snapshot.is_dir() for snapshot in marker.glob("snapshots/*"))


def clip_model_cached() -> bool:
    """True if the CLIP model is fully in the local HF cache (no download)."""
    return _model_complete(CLIP_CACHE_MARKER, _CLIP_WEIGHTS)

# trait value -> attribute tags (keyword fallback)
_KEYWORD_TAGS: dict[str, list[str]] = {
    "sunset": ["sunset lighting", "warm colors", "orange"],
    "midnight": ["dark moody", "night scene", "blue hour"],
    "forest": ["forest green", "nature themed"],
    "ocean": ["ocean blue", "aquatic", "cyan"],
    "gold": ["lustrous gold", "metallic", "precious"],
    "orange": ["ginger cat", "warm fur"],
    "grey": ["silver fur", "monochrome"],
    "white": ["white fur", "clean minimal"],
    "black": ["black cat", "gothic"],
    "green": ["green eyes", "emerald"],
    "blue": ["blue eyes", "azure"],
    "amber": ["amber eyes", "honey"],
    "sapphire": ["sapphire eyes", "deep blue"],
    "crown": ["royal crown", "king", "regal"],
    "scarf": ["red scarf", "cozy", "winter"],
    "goggles": ["aviator goggles", "steampunk", "inventor"],
    "none": [],
}
_ART_TAGS = ["pixel art", "cute", "cartoon character", "cat face"]


def clip_model_cached() -> bool:
    """True if the CLIP model is already in the local HF cache (no download)."""
    return CLIP_CACHE_MARKER.exists()


def keyword_tags(token: Token, limit: int = 4) -> TaggedAttributes:
    """Deterministic trait-derived tags (``method="keyword"``)."""
    tags: list[str] = []
    for value in token.traits.values():
        for tag in _KEYWORD_TAGS.get(str(value).lower(), []):
            if tag not in tags:
                tags.append(tag)
    for tag in _ART_TAGS:
        if tag not in tags:
            tags.append(tag)
    return TaggedAttributes(token_id=token.token_id, tags=tags[:limit], scores={}, method="keyword")


def _load_clip():
    """Load the zero-shot image classification pipeline (may download)."""
    from transformers import pipeline

    return pipeline("zero-shot-image-classification", model=CLIP_MODEL)


class ClipTagger:
    """Lazy CLIP tagger. Instantiation is cheap; the model loads on first use."""

    def __init__(
        self,
        candidates: list[str] | None = None,
        require_cached: bool = False,
    ) -> None:
        self.candidates = list(candidates or DEFAULT_ATTRIBUTE_CANDIDATES)
        self.require_cached = require_cached
        self._pipe = None

    def available(self) -> bool:
        if self.require_cached and not clip_model_cached():
            return False
        try:
            self._ensure_pipe()
            return True
        except Exception:  # noqa: BLE001 — availability probe must never crash
            return False

    def _ensure_pipe(self):
        if self._pipe is None:
            if self.require_cached and not clip_model_cached():
                raise RuntimeError(
                    f"CLIP model {CLIP_MODEL} not cached; downloads disabled"
                )
            self._pipe = _load_clip()

    def tag(self, image, token: Token, limit: int = 4, top_percent: float = 0.01) -> TaggedAttributes:
        """CLIP zero-shot tags for ``image`` (``method="clip"``).

        ``top_percent`` drops candidates scoring below that fraction of the
        top score, keeping only tags the model is actually confident about.
        """
        self._ensure_pipe()
        results = self._pipe(image, candidate_labels=self.candidates)
        best = results[0]["score"] if results else 0.0
        chosen = [r for r in results if r["score"] >= best * top_percent]
        tags = [r["label"] for r in chosen[:limit]]
        scores = {r["label"]: round(float(r["score"]), 4) for r in chosen[:limit]}
        return TaggedAttributes(token_id=token.token_id, tags=tags, scores=scores, method="clip")


def tag_token(
    token: Token,
    image=None,
    *,
    allow_clip: bool = True,
    require_cached: bool = True,
    candidates: list[str] | None = None,
) -> TaggedAttributes:
    """Tag one token: CLIP when possible, keyword fallback otherwise.

    - ``allow_clip=False`` or env ``TRAIT_GPT_CLIP=0`` → keyword path.
    - ``require_cached=True`` (default): CLIP is used only if the model is
      already downloaded — never triggers a surprise 600 MB download.
    - ``require_cached=False``: let CLIP download on first use.
    """
    if os.environ.get("TRAIT_GPT_CLIP") == "0":
        allow_clip = False
    if allow_clip:
        tagger = ClipTagger(candidates=candidates, require_cached=require_cached)
        if tagger.available():
            try:
                return tagger.tag(image, token)
            except Exception:  # noqa: BLE001 — fall back, never crash the demo
                pass
    return keyword_tags(token)