"""Per-token descriptions — template interpolation (default) or BLIP captions.

Template path (``method="template"``, the default): a deterministic,
grammar-aware sentence built from the token's traits. Runs anywhere,
including a fresh `pip install` with no model downloads at all.

BLIP path (``method="blip"``): Salesforce BLIP image-captioning-base
generates a true caption from the rendered token image (CPU, one-time
~1 GB download). Enable explicitly via ``TRAIT_GPT_DESCRIBER=blip`` or
``use_blip=True``; if the model cannot load, we fall back to the template
path and label the fallback in the returned ``Description.method`` so the
UI can show exactly which path produced the text.
"""

from __future__ import annotations

import os

from .models import Description, Token

BLIP_MODEL = "Salesforce/blip-image-captioning-base"

_TEMPLATE_TRAIT_SENTENCES = {
    "background": "The scene is set against a {value} backdrop",
    "skin": "This {value}-furred cat is the star of the show",
    "eyes": "It gazes out with striking {value} eyes",
    "accessory": "A dashing {value} completes the look",
    "default": "It sports a {value} accent",
}

ACCESSORY_ARTICLES = {"none": "no accessory", "crown": "a gold crown", "scarf": "a red scarf", "goggles": "aviator goggles"}


def template_description(token: Token) -> Description:
    """Deterministic trait-interpolated description (``method="template"``)."""
    sentences: list[str] = []
    for trait, value in token.traits.items():
        if trait == "accessory" and value in ACCESSORY_ARTICLES:
            sentences.append(f"Accessorized with {ACCESSORY_ARTICLES[value]}.")
            continue
        template = _TEMPLATE_TRAIT_SENTENCES.get(trait, _TEMPLATE_TRAIT_SENTENCES["default"])
        sentences.append(template.format(value=value) + ".")
    if not sentences:
        sentences = ["A plain, featureless token — rarity is not its game."]
    text = f"{token.display_name()}: " + " ".join(sentences)
    return Description(token_id=token.token_id, text=text, method="template")


class BlipDescriber:
    """Lazy BLIP captioner; the model downloads on first use."""

    def __init__(self, require_cached: bool = False) -> None:
        self.require_cached = require_cached
        self._processor = None
        self._model = None

    @staticmethod
    def _model_cached() -> bool:
        from pathlib import Path

        marker = Path.home() / ".cache" / "huggingface" / "hub" / (
            "models--Salesforce--blip-image-captioning-base"
        )
        if not marker.exists():
            return False
        # Stale *.incomplete markers can survive a finished download — the
        # real test is the weights file inside a snapshot.
        return any(
            (snapshot / "pytorch_model.bin").is_file()
            for snapshot in marker.glob("snapshots/*")
        )

    def _ensure_pipe(self):
        if self._processor is None:
            from pathlib import Path

            marker = Path.home() / ".cache" / "huggingface" / "hub" / (
                "models--Salesforce--blip-image-captioning-base"
            )
            if self.require_cached and not marker.exists():
                raise RuntimeError(
                    f"BLIP model {BLIP_MODEL} not cached; downloads disabled"
                )
            # Use the processor + model API directly rather than a pipeline:
            # transformers >= 5 removed the "image-to-text" task (renamed to
            # "image-text-to-text", which requires text input and behaves
            # differently). BlipProcessor/BlipForConditionalGeneration work
            # identically on transformers 4.x and 5.x.
            from transformers import BlipForConditionalGeneration, BlipProcessor

            self._processor = BlipProcessor.from_pretrained(BLIP_MODEL)
            self._model = BlipForConditionalGeneration.from_pretrained(BLIP_MODEL)
            self._model.eval()

    def describe(self, image, token: Token) -> Description:
        self._ensure_pipe()
        import torch

        inputs = self._processor(image, return_tensors="pt")
        with torch.no_grad():
            out = self._model.generate(**inputs, max_new_tokens=40)
        text = self._processor.decode(out[0], skip_special_tokens=True)
        return Description(token_id=token.token_id, text=str(text).strip(), method="blip")


def describe_token(token: Token, image=None, *, use_blip: bool | None = None) -> Description:
    """Describe one token. Defaults to the template path.

    ``use_blip``: None → env ``TRAIT_GPT_DESCRIBER`` (``"blip"`` enables);
    True → BLIP; False → template. BLIP failures degrade to template with
    the method labeled ``"template"``.
    """
    if use_blip is None:
        use_blip = os.environ.get("TRAIT_GPT_DESCRIBER") == "blip"
    if not use_blip:
        return template_description(token)
    try:
        return BlipDescriber().describe(image, token)
    except Exception:  # noqa: BLE001 — fall back, never crash the demo
        return template_description(token)