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


## 2026-08-26 — AI/rarity tip: Cache images by content hash, not by token id

trait-gpt's remote-image cache keys files by the URL's sha256, so the same image is never downloaded twice and two tokens sharing an image share a cache entry. Keying by token id double-downloads shared art and breaks when a token's metadata changes. If you fetch metadata at all, make the cache key the content address, not the identity.

> `trait-gpt tags 7 --clip --json`


## 2026-08-27 — AI/rarity tip: Zero-shot models need your vocabulary — trait names are not visual attributes

CLIP was trained on natural language about *images*, so 'background=gold' scores poorly as a candidate but 'lustrous gold' and 'metallic' score well. Map trait values to visual adjectives before tagging, or accept tags that describe the art style instead of the metadata. trait-gpt's keyword fallback is exactly that map — and it doubles as a good CLIP candidate list.

> `trait-gpt tags 7`


## 2026-08-28 — AI/rarity tip: Streamlit caching: cache resources once, cache data by input

`@st.cache_resource` reuses the loaded model pipeline across reruns (a 600 MB CLIP load should happen once, not per click); `@st.cache_data` memoizes the rarity DataFrame keyed by its arguments. Failing to split the two makes every interaction in your gallery pay the full model-load cost. trait-gpt's app.py shows the pattern.

> `streamlit run app.py`


## 2026-08-29 — AI/rarity tip: pandas 3 changed defaults — write assertions, not assumptions

Newer pandas majors change copy semantics and value handling in quiet ways. trait-gpt's `as_dataframe` builds the rarity table from explicit dict rows (`pd.DataFrame([...])`) instead of relying on index/column inference, and the CLI JSON path never touches pandas at all. When your analysis layer and display layer disagree, the golden tests catch it.

> `python -m pytest tests/test_rarity.py -q`


## 2026-08-30 — AI/rarity tip: A rarity API should degrade the same way the demo does

trait-gpt's `load_collection` resolves: local file path → fixture; anything else → Reservoir (key required); nothing → bundled fixture. Same function, three behaviors, all documented in the docstring, all covered by tests. When your loader has fallbacks, encode the fallback *order* in code and tests — prose in a README drifts, tests don't.

> `python -c "from trait_gpt.collection import load_collection; print(load_collection().name)"`

