"""Description tests — template path is offline and always runs; the BLIP
path is mocked (real model is a heavy optional download)."""

from __future__ import annotations

import pytest

from trait_gpt import describe
from trait_gpt.describe import BlipDescriber, describe_token, template_description
from trait_gpt.models import Description, Token


class TestTemplate:
    def test_interpolates_traits(self, token) -> None:
        desc = template_description(token)
        assert desc.method == "template"
        assert "gold" in desc.text.lower()
        assert "crown" in desc.text.lower()
        assert "#7" in desc.text

    def test_deterministic(self, token) -> None:
        assert template_description(token).text == template_description(token).text

    def test_empty_traits_sane(self) -> None:
        desc = template_description(Token(token_id=1, traits={}))
        assert desc.method == "template"
        assert len(desc.text) > 10

    def test_accessory_articles(self) -> None:
        desc = template_description(Token(token_id=2, traits={"accessory": "scarf"}))
        assert "red scarf" in desc.text


class TestBlipPath:
    def test_blip_mocked(self, monkeypatch) -> None:
        monkeypatch.setattr(
            describe.BlipDescriber,
            "describe",
            lambda self, image, token: Description(
                token_id=token.token_id, text="a cat wearing a crown", method="blip"
            ),
        )
        desc = describe_token(Token(token_id=7, traits={}), None, use_blip=True)
        assert desc.method == "blip"
        assert desc.text == "a cat wearing a crown"

    def test_blip_failure_falls_back_to_template(self, monkeypatch) -> None:
        monkeypatch.setattr(
            describe.BlipDescriber,
            "describe",
            lambda self, image, token: (_ for _ in ()).throw(RuntimeError("no model")),
        )
        desc = describe_token(Token(token_id=7, traits={"skin": "black"}), None, use_blip=True)
        assert desc.method == "template"
        assert "black" in desc.text

    def test_env_blip_forces_blip(self, monkeypatch) -> None:
        monkeypatch.setenv("TRAIT_GPT_DESCRIBER", "blip")
        monkeypatch.setattr(
            describe.BlipDescriber,
            "describe",
            lambda self, image, token: Description(
                token_id=token.token_id, text="captioned", method="blip"
            ),
        )
        desc = describe_token(Token(token_id=1, traits={}), None)
        assert desc.method == "blip"

    def test_env_off_uses_template(self, monkeypatch) -> None:
        monkeypatch.setenv("TRAIT_GPT_DESCRIBER", "template")
        desc = describe_token(Token(token_id=1, traits={}), None)
        assert desc.method == "template"

    @pytest.mark.network
    @pytest.mark.slow
    @pytest.mark.skipif(
        not BlipDescriber._model_cached(), reason="BLIP model not in HF cache — skip"
    )
    def test_real_blip_caption(self, token) -> None:
        from trait_gpt.render import render_token_image

        image = render_token_image(token)
        desc = describe_token(
            token, image, use_blip=True,
        )
        assert desc.method == "blip"
        assert len(desc.text) > 3