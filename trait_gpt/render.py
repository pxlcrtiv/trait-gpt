"""Deterministic procedural token art — offline, no external images.

The bundled Pixel Cats fixture references ``generated://<seed>`` images so
the whole demo (Streamlit gallery, CLIP tagging, screenshots) works with
zero network access. Every token renders to the same PNG for a given seed:
pure PIL, no randomness.

Rendering is intentionally *simple* (flat shapes matching the token's
traits) — it exists to make rarity + tag + description pipelines
demonstrable, not to be good art. The one-liner in README says so.
"""

from __future__ import annotations

import hashlib
from typing import Any

from PIL import Image, ImageDraw

from .models import Token

CANVAS = 96  # logical pixels; upscaled 4x at render time
SCALE = 4

_BG = {
    "sunset": (238, 99, 82),
    "midnight": (13, 27, 42),
    "forest": (34, 110, 60),
    "ocean": (30, 144, 210),
    "gold": (222, 172, 46),
    "default": (128, 128, 128),
}
_SKIN = {
    "orange": (238, 140, 62),
    "grey": (158, 158, 170),
    "white": (243, 243, 240),
    "black": (34, 34, 40),
    "default": (200, 200, 200),
}
_EYE = {
    "green": (40, 200, 80),
    "blue": (70, 130, 255),
    "amber": (255, 180, 30),
    "sapphire": (20, 80, 190),
    "default": (60, 60, 60),
}


def _jitter(seed: int, trait: str, base: tuple[int, int, int], amount: int = 14) -> tuple[int, int, int]:
    """Deterministic per-token color jitter so two tokens sharing traits
    still look distinct (hashed from seed + trait name)."""
    h = hashlib.sha256(f"{seed}:{trait}".encode()).digest()
    return tuple(  # type: ignore[return-value]
        min(255, max(0, c + (h[i] % (2 * amount + 1)) - amount)) for i, c in enumerate(base)
    )


def render_token_image(token: Token, scale: int = SCALE) -> Image.Image:
    """Render a token's procedural portrait at ``scale``x CANVAS pixels."""
    traits = token.traits
    seed = _seed_for(token)
    bg = _jitter(seed, "bg", _BG.get(traits.get("background", ""), _BG["default"]))
    img = Image.new("RGB", (CANVAS, CANVAS), bg)
    d = ImageDraw.Draw(img)

    head_c = _jitter(
        seed, "skin", _SKIN.get(traits.get("skin", ""), _SKIN["default"])
    )
    # Ears (two triangles) + head (rounded rectangle).
    d.polygon([(16, 44), (28, 10), (42, 34)], fill=head_c)
    d.polygon([(54, 34), (68, 10), (80, 44)], fill=head_c)
    d.rounded_rectangle([(14, 30), (82, 84)], radius=18, fill=head_c)

    # Eyes.
    eye_c = _EYE.get(traits.get("eyes", ""), _EYE["default"])
    d.rounded_rectangle([(32, 46), (42, 56)], radius=3, fill=eye_c)
    d.rounded_rectangle([(54, 46), (64, 56)], radius=3, fill=eye_c)
    d.rounded_rectangle([(35, 49), (39, 53)], radius=2, fill=(255, 255, 255))
    d.rounded_rectangle([(57, 49), (61, 53)], radius=2, fill=(255, 255, 255))

    # Nose + whiskers.
    d.polygon([(46, 60), (50, 60), (48, 66)], fill=(220, 120, 120))
    whisker = (240, 240, 240) if head_c[0] + head_c[1] + head_c[2] < 360 else (70, 70, 70)
    for y in (62, 68, 74):
        d.line([(8, y + 2), (30, y - 4)], fill=whisker, width=2)
        d.line([(66, y - 4), (88, y + 2)], fill=whisker, width=2)

    accessory = traits.get("accessory", "none")
    if accessory == "crown":
        gold = (255, 215, 60)
        d.polygon([(30, 34), (34, 14), (40, 28)], fill=gold)
        d.polygon([(40, 28), (48, 8), (56, 28)], fill=gold)
        d.polygon([(56, 28), (62, 14), (66, 34)], fill=gold)
        d.rounded_rectangle([(28, 30), (68, 36)], radius=2, fill=gold)
    elif accessory == "scarf":
        d.rounded_rectangle([(22, 72), (74, 82)], radius=4, fill=(205, 32, 60))
        d.polygon([(30, 78), (40, 78), (36, 92)], fill=(205, 32, 60))
    elif accessory == "goggles":
        d.rounded_rectangle([(24, 42), (72, 60)], radius=6, fill=(90, 90, 96))
        d.rounded_rectangle([(32, 46), (42, 56)], radius=3, fill=(190, 220, 255))
        d.rounded_rectangle([(54, 46), (64, 56)], radius=3, fill=(190, 220, 255))

    if scale != 1:
        img = img.resize((CANVAS * scale, CANVAS * scale), Image.NEAREST)
    return img


def _seed_for(token: Token) -> int:
    """Stable per-token seed: from image spec, then token_id."""
    spec = token.image
    if spec.startswith("generated://"):
        try:
            return int(spec.split("://", 1)[1])
        except ValueError:
            pass
    return int(token.token_id) * 7919 + 13


def resolve_image(token: Token, cache_dir: str | None = None) -> Any | None:
    """Return a usable PIL image for a token, or None if unavailable.

    - ``generated://<seed>`` → procedurally rendered PNG
    - http(s) URL          → downloaded once and cached in ``cache_dir``
      (None or failure → None, callers show a placeholder)
    - local path           → opened directly
    """
    spec = token.image
    if not spec:
        return None
    if spec.startswith("generated://"):
        return render_token_image(token)
    if spec.startswith(("http://", "https://")):
        if cache_dir is None:
            return None
        import hashlib as _h
        import urllib.request

        cache = __import__("pathlib").Path(cache_dir)
        cache.mkdir(parents=True, exist_ok=True)
        target = cache / f"{_h.sha256(spec.encode()).hexdigest()[:16]}.png"
        if not target.exists():
            try:
                with urllib.request.urlopen(spec, timeout=15) as resp:  # noqa: S310
                    target.write_bytes(resp.read())
            except OSError:
                return None
        return Image.open(target)
    p = __import__("pathlib").Path(spec)
    if p.exists():
        return Image.open(p)
    return None