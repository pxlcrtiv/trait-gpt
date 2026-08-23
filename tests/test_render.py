"""Render tests — procedural images must be deterministic and trait-driven."""

from __future__ import annotations

from io import BytesIO

from trait_gpt.models import Collection, Token
from trait_gpt.render import render_token_image, resolve_image


def _png_bytes(img) -> bytes:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_render_deterministic(token) -> None:
    a = _png_bytes(render_token_image(token))
    b = _png_bytes(render_token_image(token))
    assert a == b


def test_render_size_and_mode(token) -> None:
    img = render_token_image(token)
    assert img.size == (384, 384)
    assert img.mode == "RGB"


def test_background_changes_pixels() -> None:
    sunset = Token(token_id=1, traits={"background": "sunset"}, image="generated://1")
    midnight = Token(token_id=2, traits={"background": "midnight"}, image="generated://2")
    assert _png_bytes(render_token_image(sunset)) != _png_bytes(render_token_image(midnight))


def test_accessory_changes_pixels(token) -> None:
    plain = Token(
        token_id=token.token_id,
        traits={**token.traits, "accessory": "none"},
        image="generated://1007",
    )
    assert _png_bytes(render_token_image(token)) != _png_bytes(render_token_image(plain))


def test_seed_affects_jitter() -> None:
    a = render_token_image(Token(token_id=1, traits={"background": "gold"}, image="generated://1"))
    b = render_token_image(Token(token_id=1, traits={"background": "gold"}, image="generated://2"))
    assert _png_bytes(a) != _png_bytes(b)


def test_resolve_generated_image(token) -> None:
    img = resolve_image(token)
    assert img is not None
    assert img.size == (384, 384)


def test_resolve_missing_url_returns_none() -> None:
    # No cache dir → remote URLs resolve to None (offline-safe).
    t = Token(token_id=1, traits={}, image="https://example.invalid/x.png")
    assert resolve_image(t, cache_dir=None) is None


def test_render_is_deterministic_across_collections(pixel_cats) -> None:
    first = pixel_cats.tokens[0]
    png1 = _png_bytes(render_token_image(first))
    collection2 = Collection(
        name="reloaded",
        slug="x",
        description="",
        tokens=[Token(token_id=first.token_id, traits=first.traits, image=first.image)],
        source="fixture",
    )
    png2 = _png_bytes(render_token_image(collection2.tokens[0]))
    assert png1 == png2