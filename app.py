"""trait-gpt — Streamlit gallery for NFT rarity + AI descriptions.

Zero-key demo (≤ 5 min):

    pip install -r requirements.txt
    streamlit run app.py

→ the bundled Pixel Cats fixture loads, the rarity table renders, and every
token gets attribute tags + a description (template path by default; CLIP
and BLIP models are optional one-time downloads).

Env toggles:
    TRAIT_GPT_RESERVOIR_KEY=...   load a real Reservoir collection
    TRAIT_GPT_CLIP=0              force keyword attribute tags
    TRAIT_GPT_DESCRIBER=blip      use BLIP captions (one-time ~1 GB download)
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from trait_gpt.clip_tagger import clip_model_cached, tag_token
from trait_gpt.collection import CollectionError, load_collection
from trait_gpt.describe import describe_token
from trait_gpt.rarity import as_dataframe, rank_collection, trait_stats
from trait_gpt.render import resolve_image

PAGE_TITLE = "trait-gpt — NFT rarity + AI descriptions"

st.set_page_config(page_title=PAGE_TITLE, page_icon="🐱", layout="wide")


@st.cache_data(show_spinner=False)
def load(_source: str) -> object:
    """Load collection once per app run. ``_source`` is just a cache key."""
    return load_collection(_source or None)


@st.cache_resource
def clip_pipeline_available() -> bool:
    return clip_model_cached()


def build_rows(collection) -> pd.DataFrame:
    """Rarity table + trait column in one frame for st.dataframe."""
    df = as_dataframe(collection)
    by_id = {t.token_id: t for t in collection.tokens}
    df["Traits"] = [
        " · ".join(f"{k}={v}" for k, v in by_id[i].traits.items()) for i in df.index
    ]
    return df


def main() -> None:
    st.title("🐱 trait-gpt")
    st.caption(
        "Rarity score + AI-written description for any NFT collection — "
        "trait statistics, CLIP zero-shot attribute tags, BLIP captions. "
        "All on CPU, no GPU, no paid APIs."
    )

    with st.sidebar:
        st.header("Collection")
        source = st.text_input(
            "JSON path (or Reservoir contract with a key set)",
            placeholder="(default: bundled Pixel Cats fixture)",
        )
        st.caption(
            "Tip: run with `TRAIT_GPT_RESERVOIR_KEY=... streamlit run app.py` "
            "to load a real collection from Reservoir."
        )
        st.header("AI options")
        use_clip = st.checkbox("CLIP attribute tags", value=clip_pipeline_available())
        if use_clip and not clip_pipeline_available():
            st.warning("CLIP model not cached — tags will be keyword-based until it is.")
        use_blip = st.checkbox(
            "BLIP captions (one-time ~1 GB download)", value=False
        )

    try:
        collection = load(source)
    except CollectionError as exc:
        st.error(f"Could not load collection: {exc}")
        st.stop()

    st.subheader(f"{collection.name} — {collection.n_tokens} tokens (source: {collection.source})")
    st.write(collection.description or "")

    # ---------------- Trait stats ----------------
    st.header("Trait statistics")
    stats = trait_stats(collection)
    cols = st.columns(max(1, len(stats)))
    for col, (trait, rows) in zip(cols, stats.items()):
        with col:
            st.markdown(f"**{trait}**")
            table = pd.DataFrame(
                [{"value": r.value, "count": r.count, "frequency": f"{r.frequency:.1%}"} for r in rows]
            )
            st.dataframe(table, hide_index=True, use_container_width=True)

    # ---------------- Rarity table ----------------
    st.header("Rarity table")
    st.caption(
        "score = mean trait rarity (N / count per trait value), normalized by "
        "trait count — see README for the exact formula. Rank 1 = rarest."
    )
    table = build_rows(collection)
    st.dataframe(table, hide_index=False, use_container_width=True, height=360)

    rankings = rank_collection(collection)
    top = rankings[0]
    st.success(
        f"🏆 Rarest token: **#{top.token_id}** — score {top.score:.4f} "
        f"(rank {top.rank}/{collection.n_tokens}, percentile {top.percentile:.1f})"
    )

    # ---------------- Token gallery ----------------
    st.header("Token gallery")
    token_ids = [t.token_id for t in collection.tokens]
    deep_link = st.query_params.get("token")
    default_idx = token_ids.index(int(deep_link)) if deep_link and deep_link.isdigit() and int(deep_link) in token_ids else 0
    token = st.selectbox(
        "Pick a token",
        collection.tokens,
        index=default_idx,
        format_func=lambda t: f"#{t.token_id} — {t.display_name()}",
    )

    image = resolve_image(token, cache_dir="/tmp/trait-gpt-imgcache")
    col_img, col_info = st.columns([1, 2])
    with col_img:
        if image is not None:
            st.image(image, caption=f"#{token.token_id} — {token.display_name()}", width=288)
        else:
            st.warning("No image available for this token.")

    with col_info:
        st.markdown("**Traits**")
        st.write({k: v for k, v in token.traits.items()})

        st.markdown("**Attribute tags**")
        with st.spinner("Tagging…"):
            tags = tag_token(token, image, allow_clip=use_clip, require_cached=True)
        st.write(
            f"`{tags.method}` — " + ", ".join(f"**{t}**" for t in tags.tags) if tags.tags
            else "`keyword` — no tags derived"
        )
        if tags.scores:
            st.caption(" · ".join(f"{k}: {v:.2f}" for k, v in tags.scores.items()))

        st.markdown("**Description**")
        with st.spinner("Describing…"):
            desc = describe_token(token, image, use_blip=use_blip)
        st.info(f"`{desc.method}` — {desc.text}")

        rank_row = next(r for r in rankings if r.token_id == token.token_id)
        st.markdown(
            f"**Rarity** — score {rank_row.score:.4f} · sum {rank_row.score_sum:.4f} "
            f"· rank **{rank_row.rank}** of {collection.n_tokens} · percentile {rank_row.percentile:.1f}"
        )
        st.progress(1.0 - rank_row.percentile / 100.0)

    st.divider()
    st.caption(
        "Educational demo — the NFT market has cooled, this is a learning "
        "project, not investment advice. No tokens are real; no keys needed."
    )


if __name__ == "__main__":
    main()