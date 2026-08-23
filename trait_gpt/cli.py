"""trait-gpt CLI — rarity stats, rankings, tags, descriptions from the shell.

Examples::

    trait-gpt stats                     # trait value counts, fixture collection
    trait-gpt rank --top 5              # 5 rarest tokens, JSON
    trait-gpt describe 7                # description for token #7
    trait-gpt tags 7 --clip             # CLIP tags (downloads model on first use)
    trait-gpt stats --collection ./my-collection.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .collection import load_collection
from .describe import describe_token
from .rarity import rank_collection, trait_stats
from .render import resolve_image, render_token_image
from .clip_tagger import tag_token, clip_model_cached


def _out(obj: object, as_json: bool) -> None:
    if as_json:
        print(json.dumps(obj, indent=2, default=str))
    else:
        print(obj)


def _find_token(collection, token_id: int):
    for token in collection.tokens:
        if token.token_id == token_id:
            return token
    sys.exit(f"token #{token_id} not found in collection '{collection.name}'")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="trait-gpt",
        description="NFT rarity scoring + AI descriptions, CPU-only, zero keys.",
    )
    parser.add_argument(
        "--collection",
        default=None,
        help="path to a collection JSON, or a Reservoir contract address "
        "(needs TRAIT_GPT_RESERVOIR_KEY); default: bundled Pixel Cats fixture",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_stats = sub.add_parser("stats", help="trait value counts and frequencies")
    p_stats.add_argument("--json", action="store_true", dest="as_json")

    p_rank = sub.add_parser("rank", help="rarity table, rarest first")
    p_rank.add_argument("--top", type=int, default=0, help="only the first N tokens (0 = all)")
    p_rank.add_argument("--json", action="store_true", dest="as_json")

    p_desc = sub.add_parser("describe", help="per-token description")
    p_desc.add_argument("token_id", type=int)
    p_desc.add_argument("--blip", action="store_true", help="use BLIP captioning (downloads ~1 GB on first use)")
    p_desc.add_argument("--image-out", default=None, help="also render the token image to this PNG path")

    p_tags = sub.add_parser("tags", help="CLIP zero-shot attribute tags (keyword fallback if no model)")
    p_tags.add_argument("token_id", type=int)
    p_tags.add_argument("--clip", action="store_true", help="allow CLIP model download if not cached")
    p_tags.add_argument("--json", action="store_true", dest="as_json")

    args = parser.parse_args(argv)

    collection = load_collection(args.collection)

    if args.command == "stats":
        stats = {
            trait: [{"value": r.value, "count": r.count, "frequency": round(r.frequency, 4)} for r in rows]
            for trait, rows in trait_stats(collection).items()
        }
        if not args.as_json:
            print(f"Collection: {collection.name} ({collection.n_tokens} tokens, source={collection.source})")
            for trait, rows in stats.items():
                print(f"\n{trait}:")
                for row in rows:
                    bar = "#" * int(40 * row["frequency"])
                    print(f"  {row['value']:<12} {row['count']:>3}  {row['frequency']:.2%} {bar}")
        else:
            _out({"collection": collection.name, "n_tokens": collection.n_tokens, "traits": stats}, True)
        return 0

    if args.command == "rank":
        ranks = rank_collection(collection)
        if args.top > 0:
            ranks = ranks[: args.top]
        rows = [r.as_dict() for r in ranks]
        if not args.as_json:
            print(
                f"{'#':>4}  {'score':>8}  {'sum':>8}  {'rank':>4}  {'pct':>6}  token"
            )
            for r in rows:
                print(
                    f"{r['token_id']:>4}  {r['score']:>8.4f}  {r['score_sum']:>8.4f}  "
                    f"{r['rank']:>4}  {r['percentile']:>6.1f}  #{r['token_id']}"
                )
        else:
            _out({"collection": collection.name, "n_tokens": collection.n_tokens, "rankings": rows}, True)
        return 0

    token = _find_token(collection, args.token_id)
    if args.command == "describe":
        image = resolve_image(token, cache_dir="/tmp/trait-gpt-imgcache")
        desc = describe_token(token, image, use_blip=args.blip)
        _out(desc.as_dict(), getattr(args, "as_json", False) or False)
        if not getattr(args, "as_json", False):
            print(f"[{desc.method}] {desc.text}")
        if args.image_out:
            (render_token_image(token) if token.image.startswith("generated://") else image).save(  # type: ignore[union-attr]
                args.image_out
            )
            print(f"image saved to {args.image_out}")
        return 0

    # tags
    image = resolve_image(token, cache_dir="/tmp/trait-gpt-imgcache")
    tagged = tag_token(token, image, allow_clip=args.clip, require_cached=not args.clip)
    _out(tagged.as_dict(), args.as_json)
    if not args.as_json:
        if tagged.scores:
            rendered = " · ".join(f"{t} ({tagged.scores[t]:.4f})" for t in tagged.tags)
        else:
            rendered = ", ".join(tagged.tags)
        print(f"[{tagged.method}] {rendered}")
        if tagged.method == "keyword":
            print("(CLIP model not used — pass --clip to allow a one-time download)")
        else:
            print(f"(CLIP model: {clip_model_cached()})")
    return 0


if __name__ == "__main__":
    sys.exit(main())