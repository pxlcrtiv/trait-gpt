# trait-gpt tips of the day

> Maintained by `scripts/daily_update.py` (Daily Green automation) — one
> dated, non-empty NFT rarity / AI tip per day, rotated from the pool in
> `scripts/tips_pool.json`. Pause by creating a `.daily-pause` file in the
> repo root, or unload the scheduler job (see README, Daily Green).


## 2026-08-23 — AI/rarity tip: Reservoir tokenIds arrive as strings — sometimes 'contract:tokenId'

The Reservoir v7 API returns tokenId as an int for some contracts and `0xcontract:tokenId` strings for others. trait-gpt's parser splits on the last ':' and coerces to int, with tests pinning both forms. If you parse ERC-721 data from any API, expect the string form and normalize early — a crash halfway through a batch is the alternative.

> `python -c "from trait_gpt.collection import load_collection; c = load_collection(); print(c.n_tokens, 'tokens')"`


## 2026-08-24 — AI/rarity tip: The rarity curve tells you more than the #1 token

A collection with one ultra-rare token and 23 near-identical commons has a different market dynamic than one with a smooth rarity curve. Plot the score distribution, not just the leaderboard: trait-gpt's app shows the full table plus trait-frequency bars, which makes the shape of the collection visible at a glance. Extrapolating from the top-1 alone is how bad flips happen.

> `trait-gpt stats`


## 2026-08-25 — AI/rarity tip: Procedural placeholder art keeps demos legal and offline

Hotlinking real NFT images into a demo repo is both fragile and legally iffy. trait-gpt renders each token's portrait deterministically from its traits (PIL, pure shapes, seeded jitter) — every demo, screenshot, and CI run has images without a single external URL. Artists can swap in real art by pointing the fixture at local files.

> `python -m trait_gpt.cli describe 7 --image-out /tmp/cat7.png`

