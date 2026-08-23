"""CLIP tagger tests — keyword path always runs; CLIP path is mocked or
skipped when the model is not cached (suite stays green offline)."""

from __future__ import annotations

from pathlib import Path

import pytest

from trait_gpt import clip_tagger
from trait_gpt.clip_tagger import (  # noqa: F401  (imported for monkeypatch targets)
    CLIP_CACHE_MARKER,
    ClipTagger,
    clip_model_cached,
    keyword_tags,
    tag_token,
)
from trait_gpt.models import TaggedAttributes, Token


class TestKeywordFallback:
    def test_crown_token_tags(self) -> None:
        token = Token(token_id=1, traits={"accessory": "crown"})
        result = keyword_tags(token, limit=4)
        assert result.method == "keyword"
        assert "royal crown" in result.tags
        assert result.scores == {}

    def test_deterministic(self) -> None:
        token = Token(token_id=1, traits={"background": "gold", "accessory": "crown"})
        a = keyword_tags(token).tags
        b = keyword_tags(token).tags
        assert a == b

    def test_limit_respected(self) -> None:
        token = Token(token_id=1, traits={"skin": "orange"})
        assert len(keyword_tags(token, limit=2).tags) <= 2

    def test_every_trait_value_yields_something(self, pixel_cats) -> None:
        seen: set[str] = set()
        for token in pixel_cats.tokens:
            for result in [keyword_tags(token)]:
                seen.update(result.tags)
        assert len(seen) >= 8  # curated map covers many values


class TestClipPath:
    def test_mocked_pipeline_tags(self, monkeypatch) -> None:
        class FakePipe:
            def __call__(self, image, candidate_labels):
                return [
                    {"label": "pixel art", "score": 0.9},
                    {"label": "cute", "score": 0.03},
                    {"label": "photorealistic", "score": 0.001},
                ]

        tagger = ClipTagger(require_cached=False)
        monkeypatch.setattr(tagger, "_pipe", FakePipe())
        token = Token(token_id=1, traits={"accessory": "crown"})
        result = tagger.tag(None, token)
        assert result.method == "clip"
        # top_percent=0.01 keeps score >= 0.009 → pixel art + cute only.
        assert result.tags == ["pixel art", "cute"]
        assert result.scores["pixel art"] == 0.9

    def test_require_cached_blocks_when_not_cached(self, monkeypatch) -> None:
        monkeypatch.setattr(
            clip_tagger, "CLIP_CACHE_MARKER", Path("/definitely/not/cached")
        )
        assert not clip_model_cached()
        tagger = ClipTagger(require_cached=True)
        assert tagger.available() is False
        with pytest.raises(RuntimeError, match="not cached"):
            tagger.tag(None, Token(token_id=1, traits={}))

    def test_tag_token_env_disables_clip(self, monkeypatch) -> None:
        monkeypatch.setenv("TRAIT_GPT_CLIP", "0")
        result = tag_token(
            Token(token_id=1, traits={"background": "gold"}), None, allow_clip=True
        )
        assert result.method == "keyword"

    def test_tag_token_falls_back_on_pipeline_failure(self, monkeypatch) -> None:
        class BrokenPipe:
            def __call__(self, *args, **kwargs):
                raise RuntimeError("boom")

        tagger = ClipTagger(require_cached=False)
        monkeypatch.setattr(tagger, "_pipe", BrokenPipe())
        token = Token(token_id=1, traits={"background": "gold"})
        # Force the clip path to be attempted with the broken pipe.
        monkeypatch.setattr(clip_tagger, "ClipTagger", lambda **kw: tagger)
        result = tag_token(token, None, allow_clip=True, require_cached=False)
        assert result.method == "keyword"

    @pytest.mark.network
    @pytest.mark.slow
    @pytest.mark.skipif(
        not clip_model_cached(), reason="CLIP model not in HF cache — skip"
    )
    def test_real_clip_on_rendered_image(self, token) -> None:
        from trait_gpt.render import render_token_image

        image = render_token_image(token)
        result = tag_token(token, image, allow_clip=True, require_cached=True)
        assert result.method == "clip"
        assert len(result.tags) >= 1