# Changelog

All notable changes to trait-gpt are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[SemVer](https://semver.org/).

## [Unreleased]

- Planned: full-collection Reservoir pagination, per-trait rarity heatmaps,
  OpenSea-style trait floor aggregation demo.

## [0.1.0] — 2026-08-23

Initial release — the zero-key NFT rarity demo.

### Added

- **Rarity engine** (`trait_gpt/rarity.py`): statistical trait rarity
  (`N / count`), trait-count-normalized token score (mean trait rarity),
  competition ranking with ties, percentile (0 = rarest). Pure Python,
  fully deterministic, golden-tested.
- **Collection loading** (`trait_gpt/collection.py`): bundled offline
  fixture (24-token Pixel Cats, procedurally rendered art), JSON validation,
  and an optional Reservoir v7 client (needs `TRAIT_GPT_RESERVOIR_KEY`).
- **CLIP zero-shot attribute tags** (`trait_gpt/clip_tagger.py`):
  `openai/clip-vit-base-patch32` on CPU with a confidence floor; automatic
  deterministic keyword fallback when the model is not cached; every result
  labeled `clip | keyword`.
- **Per-token descriptions** (`trait_gpt/describe.py`): deterministic
  trait-interpolated template path (default, offline) and optional BLIP
  captioning (`Salesforce/blip-image-captioning-base`); failures degrade to
  template; every result labeled `blip | template`.
- **Streamlit gallery** (`app.py`): trait statistics, rarity table, token
  gallery with tags, description, and rarity card. Zero-key demo:
  `streamlit run app.py`.
- **CLI** (`trait-gpt stats | rank | describe | tags`): JSON and text
  output, offline by default.
- **Daily Green automation**: `scripts/daily_update.py` +
  `scripts/tips_pool.json` (25 curated tips), deterministic daily commits,
  idempotent, backfills missed days, pause-able.
- **Quality**: 71 pytest tests (golden math, mocked model paths,
  offline-safe; real CLIP/BLIP tests skip without cached models),
  CI workflow (`ci.yml`), cloud-fallback daily workflow
  (`daily.yml`), MIT license, CONTRIBUTING, this changelog.

[0.1.0]: https://github.com/pxlcrtiv/trait-gpt/releases/tag/v0.1.0