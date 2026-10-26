"""Hugging Face cache completeness helpers.

A model directory under ``~/.cache/huggingface/hub`` can exist while a
download is still *in progress* (or was interrupted). Treating such a
partial directory as "cached" makes the CLIP/BLIP loaders attempt to read
truncated weights and hang or crash. This module is the single source of
truth for "is this model fully present on disk?" — both :mod:`clip_tagger`
and :mod:`describe` delegate here so the rule (and its edge cases) live in
one place.
"""

from __future__ import annotations

from pathlib import Path


def model_cached(marker: Path, weights_name: str) -> bool:
    """True when ``marker`` holds a *complete* copy of one HF model.

    ``marker`` is the hub cache directory for the model (e.g.
    ``models--openai--clip-vit-base-patch32``); ``weights_name`` is the
    weights file we require inside a snapshot (e.g. ``pytorch_model.bin``).

    Rules (evaluated in order):
      * the marker must exist;
      * no ``*.incomplete`` blob may remain anywhere under it — this is
        checked before anything else, so a partial download is rejected
        even if a stale/committed weights file is also present;
      * at least one snapshot must contain ``weights_name``;
      * otherwise, any *non-empty* snapshot directory counts (for models
        whose weights file name we don't pin).
    """
    if not marker.exists():
        return False
    # Partial downloads leave *.incomplete blobs behind — reject first,
    # regardless of any (possibly stale) committed weights.
    if list(marker.rglob("*.incomplete")):
        return False
    # A weights file inside a snapshot is the strongest signal of a
    # finished download.
    for snapshot in marker.glob("snapshots/*"):
        if (snapshot / weights_name).is_file():
            return True
    # Fall back to "any non-empty committed snapshot dir" for models whose
    # weights file name we don't pin (keeps the probe from being
    # over-specific). Empty dirs never count.
    return any(
        snapshot.is_dir() and any(snapshot.iterdir())
        for snapshot in marker.glob("snapshots/*")
    )
