# trait-gpt tips of the day

> Maintained by `scripts/daily_update.py` (Daily Green automation) — one
> dated, non-empty NFT rarity / AI tip per day, rotated from the pool in
> `scripts/tips_pool.json`. Pause by creating a `.daily-pause` file in the
> repo root, or unload the scheduler job (see README, Daily Green).


## 2026-08-23 — AI/rarity tip: Reservoir tokenIds arrive as strings — sometimes 'contract:tokenId'

The Reservoir v7 API returns tokenId as an int for some contracts and `0xcontract:tokenId` strings for others. trait-gpt's parser splits on the last ':' and coerces to int, with tests pinning both forms. If you parse ERC-721 data from any API, expect the string form and normalize early — a crash halfway through a batch is the alternative.

> `python -c "from trait_gpt.collection import load_collection; c = load_collection(); print(c.n_tokens, 'tokens')"`

