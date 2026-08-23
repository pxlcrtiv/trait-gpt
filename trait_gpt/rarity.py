"""Rarity math — pure Python, no dependencies beyond the stdlib.

Formula (documented, and the golden tests pin exact values):

1. For every trait value ``v`` seen in the collection:

       trait_rarity(v) = N / count(v)

   where ``N`` is the total number of tokens. This is the classic
   *statistical rarity*: a value carried by 1 of 24 tokens scores 24.0, a
   value carried by 12 of 24 scores 2.0. Rarer value → higher score.

2. Per token, the **trait-count-normalized rarity score** is the *mean*
   trait rarity over the token's traits:

       score(token) = (1 / k) * sum(trait_rarity(v) for v in token.traits)

   Normalizing by trait count means tokens that happen to carry *more*
   traits (and thereby accumulate more terms) are not automatically
   "rarer" than tokens with fewer traits — every token competes on the
   average rarity of what it has. ``score_sum`` (the raw sum) is also
   reported for collectors who prefer the classic sum-based method.

3. Ranking uses **competition ranking** ("1224"): tokens with equal scores
   share a rank, and the next distinct score gets rank = position + 1.

4. ``percentile`` maps rank to 0..100 where 0.0 = rarest:

       percentile = 100 * (rank - 1) / (N - 1)      (0.0 when N == 1)

Everything is deterministic: same collection in, same numbers out, no
randomness, no network.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from .models import Collection, RarityRank, Token, TraitCount


class RarityError(ValueError):
    """Raised for collections that cannot be scored."""


def trait_counts(collection: Collection, trait: str) -> list[TraitCount]:
    """Counts for every value of one trait, sorted rarest-first.

    Order is deterministic: descending rarity, then value name.
    """
    counter: Counter[str] = Counter()
    for token in collection.tokens:
        value = token.traits.get(trait)
        if value is not None:
            counter[value] += 1
    n = collection.n_tokens
    if n == 0:
        raise RarityError("cannot compute trait stats for an empty collection")
    rows = [
        TraitCount(trait=trait, value=v, count=c, frequency=c / n)
        for v, c in counter.items()
    ]
    rows.sort(key=lambda r: (-r.count, r.value))
    return rows


def trait_stats(collection: Collection) -> dict[str, list[TraitCount]]:
    """Trait -> value count table for every trait in the collection."""
    return {trait: trait_counts(collection, trait) for trait in collection.trait_names}


def trait_rarity_map(collection: Collection) -> dict[tuple[str, str], float]:
    """(trait, value) -> trait_rarity for every observed value."""
    n = collection.n_tokens
    if n == 0:
        raise RarityError("cannot compute rarity for an empty collection")
    counter: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for token in collection.tokens:
        for trait, value in token.traits.items():
            counter[trait][value] += 1
    return {
        (trait, value): n / count
        for trait, values in counter.items()
        for value, count in values.items()
    }


def score_token(token: Token, rarities: dict[tuple[str, str], float]) -> tuple[float, float]:
    """(score, score_sum) for one token.

    ``score`` is the trait-count-normalized rarity: the mean trait rarity
    over the token's traits. Tokens with *no* traits score 0.0.
    """
    if not token.traits:
        return 0.0, 0.0
    total = sum(rarities[(trait, value)] for trait, value in token.traits.items())
    mean = total / len(token.traits)
    return mean, total


def rank_collection(collection: Collection) -> list[RarityRank]:
    """Score and rank every token; returns list sorted rarest-first.

    Use this to build the canonical rarity table (also exposed as
    ``as_dataframe`` for pandas consumers).
    """
    rarities = trait_rarity_map(collection)
    scored: list[tuple[float, float, Token]] = []
    for token in collection.tokens:
        mean, total = score_token(token, rarities)
        scored.append((mean, total, token))

    # Sort by score desc; ties broken by token_id for full determinism.
    scored.sort(key=lambda s: (-s[0], s[2].token_id))

    n = len(scored)
    ranks: list[RarityRank] = []
    for i, (mean, total, token) in enumerate(scored):
        # Competition ranking: first occurrence of a score owns the rank.
        if i > 0 and scored[i - 1][0] == mean:
            rank = ranks[-1].rank
        else:
            rank = i + 1
        percentile = 100.0 * (rank - 1) / (n - 1) if n > 1 else 0.0
        ranks.append(
            RarityRank(
                token_id=token.token_id,
                score=round(mean, 6),
                score_sum=round(total, 6),
                rank=rank,
                percentile=round(percentile, 4),
            )
        )
    return ranks


def as_dataframe(collection: Collection) -> "object":  # noqa: ANN001
    """Rarity table as a pandas DataFrame (rarest first).

    Imported lazily so tests of the pure math never need pandas.
    """
    import pandas as pd

    rows = [r.as_dict() for r in rank_collection(collection)]
    df = pd.DataFrame(rows)
    df = df.rename(columns={"token_id": "Token", "score": "Rarity score"})
    df = df.set_index("Token")
    return df


def top_tokens(collection: Collection, k: int = 5) -> list[RarityRank]:
    """The k rarest tokens, rarest first."""
    ranks = rank_collection(collection)
    return ranks[:k]