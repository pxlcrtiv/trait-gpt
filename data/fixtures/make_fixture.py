#!/usr/bin/env python3
"""Regenerate data/fixtures/pixel-cats.json — the bundled demo collection.

Deterministic (fixed seed): the same script always produces the same
fixture, so test golden values never drift. The fixture deliberately owns
one very rare token (#7: gold background + crown) so the rarity table has a
clear #1, and a skewed distribution so ranks are interesting.

Usage:
    python data/fixtures/make_fixture.py [out_path]

Trait distributions (24 tokens):
    background: gold 1, midnight 2, forest 4, ocean 6, sunset 11
    skin:       black 3, white 4, grey 6, orange 11
    eyes:       sapphire 2, amber 3, blue 4, green 15
    accessory:  crown 1, goggles 2, scarf 3, none 18
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

N_TOKENS = 24
DISTRIBUTIONS: dict[str, list[str]] = {
    "background": ["gold"] + ["midnight"] * 2 + ["forest"] * 4 + ["ocean"] * 6 + ["sunset"] * 11,
    "skin": ["black"] * 3 + ["white"] * 4 + ["grey"] * 6 + ["orange"] * 11,
    "eyes": ["sapphire"] * 2 + ["amber"] * 3 + ["blue"] * 4 + ["green"] * 15,
    "accessory": ["crown"] + ["goggles"] * 2 + ["scarf"] * 3 + ["none"] * 18,
}

META = {
    "name": "Pixel Cats",
    "slug": "pixel-cats",
    "description": (
        "A tiny generative cat collection used as trait-gpt's zero-key demo "
        "fixture. 24 tokens, 4 traits, procedurally rendered art — the "
        "rarity table, attribute tags and descriptions in the README all "
        "come from this file."
    ),
}


def build_tokens(rng: random.Random) -> list[dict]:
    # The single gold-background + crown token lands on #7 on purpose:
    # golden values in the README (rarest token) refer to #7. Give it the
    # rarest pair of the other two traits as well, so #7 is the dream combo
    # (score = (24 + 8 + 12 + 24) / 4 = 17.0).
    per_trait: dict[str, list[str]] = {}
    for trait, values in DISTRIBUTIONS.items():
        pool = list(values)
        rng.shuffle(pool)
        per_trait[trait] = pool

    for trait, rarest in (("background", "gold"), ("skin", "black"), ("eyes", "sapphire"), ("accessory", "crown")):
        pool = per_trait[trait]
        i = pool.index(rarest)
        pool[i], pool[6] = pool[6], pool[i]
        assert pool[6] == rarest

    tokens: list[dict] = []
    for i in range(N_TOKENS):
        tokens.append(
            {
                "token_id": i + 1,
                "name": f"Pixel Cat #{i + 1}",
                "traits": {
                    "background": per_trait["background"][i],
                    "skin": per_trait["skin"][i],
                    "eyes": per_trait["eyes"][i],
                    "accessory": per_trait["accessory"][i],
                },
                "image": f"generated://{1000 + i}",
            }
        )
    # Sanity: distributions must be respected exactly.
    for trait, values in DISTRIBUTIONS.items():
        counts = {v: [t["traits"][trait] for t in tokens].count(v) for v in set(values)}
        assert counts == {v: values.count(v) for v in set(values)}, (trait, counts)
    return tokens


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "pixel-cats.json"
    fixture = {
        **META,
        "n_tokens": N_TOKENS,
        "traits": list(DISTRIBUTIONS),
        "tokens": build_tokens(random.Random(0xC0FFEE)),
    }
    out.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} ({N_TOKENS} tokens)")
    return 0


if __name__ == "__main__":
    sys.exit(main())