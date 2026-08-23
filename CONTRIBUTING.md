# Contributing to trait-gpt

First off: **thank you** — this project lives on community ideas. Rarity
math, prompt engineering, and UI polish all benefit from fresh eyes.

## Ground rules

- **The demo must work with zero keys and zero network.** The bundled
  fixture collection (`data/fixtures/pixel-cats.json`) is the product's
  guarantee. New features must degrade gracefully: CLIP missing → keyword
  tags; BLIP missing → template descriptions. A feature that breaks the
  offline path gets reverted.
- **Label every path.** Every result carries a `method` field
  (`clip | keyword`, `blip | template`). New generation paths must do the
  same.
- **Never hardcode a key.** Reservoir is optional and read from
  `TRAIT_GPT_RESERVOIR_KEY` (or the constructor arg).
- **Golden tests for math.** Rarity formula changes require updating the
  worked example in `trait_gpt/rarity.py`, the README "How rarity works"
  section, and the golden values in `tests/test_rarity.py` — all three,
  together, in one commit.
- **Model-dependent tests skip, never fail.** Heavy model tests are marked
  `network`/`slow` and skip when the model is not in the HF cache. The
  suite must stay green with no network (`python -m pytest -q`).

## Getting started

```bash
git clone https://github.com/pxlcrtiv/trait-gpt
cd trait-gpt
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest
python -m pytest tests/ -q          # offline suite, no models needed

# optional one-time model downloads for the AI paths:
streamlit run app.py                # then toggle CLIP / BLIP in the sidebar
```

## How to add something

1. **A new trait-statistic or scoring feature** — extend
   `trait_gpt/rarity.py`, add golden tests with hand-computed values, and
   update the README formula section in the same commit.
2. **A new description/tagging backend** — add a module next to
   `clip_tagger.py` / `describe.py`, return results with a `method` label,
   and wire a graceful fallback to the existing default path.
3. **A better fixture** — edit `data/fixtures/make_fixture.py` (it must
   stay deterministic) and regenerate; the golden tests will tell you if a
   rarity claim changed.
4. **A tip for the daily log** — append to `scripts/tips_pool.json`
   (title + body; keep them factual and repo-specific). The Daily Green
   automation picks it up automatically.

## Code style

- `ruff` defaults (line length 100). One deliberate deviation: `BLE001`
  (broad except) is allowed around model pipelines — failures must degrade
  to the fallback path, never crash the demo. Keep the reason in the
  comment.
- Type hints on public functions; docstrings with a one-line summary.
- No new runtime dependencies without a good reason — CPU-only, small
  models, no paid APIs.

## Reporting issues

Open an issue with: what you ran, the exact command, the expected vs.
actual output, and whether models were cached. For rarity-score
discrepancies, include the collection JSON (or enough traits to reproduce
the math by hand).