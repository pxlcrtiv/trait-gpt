"""Golden tests for the rarity engine — exact values pinned to the formula.

Golden collection ``rare3`` (3 tokens, 2 traits each):

    #1 Alpha:  background=red (count 2), eyes=green (count 1)
    #2 Beta:   background=red (count 2), eyes=blue  (count 2)
    #3 Gamma:  background=blue (count 1), eyes=blue (count 2)

    N=3 → trait_rarity(v) = 3 / count(v):
        (background, red)   = 1.5
        (background, blue)  = 3.0
        (eyes, green)       = 3.0
        (eyes, blue)        = 1.5

    score = mean trait rarity:
        #1: (1.5 + 3.0) / 2 = 2.25   sum 4.5
        #2: (1.5 + 1.5) / 2 = 1.50   sum 3.0
        #3: (3.0 + 1.5) / 2 = 2.25   sum 4.5

    Competition ranking: #1 and #3 tie at rank 1 (tie-break token_id → #1
    listed first), #2 is rank 3. Percentile = 100*(rank-1)/(N-1):
    rank 1 → 0.0, rank 3 → 100.0.
"""

from __future__ import annotations

import pytest

from trait_gpt.models import Collection, Token
from trait_gpt.rarity import (
    RarityError,
    rank_collection,
    score_token,
    top_tokens,
    trait_counts,
    trait_rarity_map,
    trait_stats,
)


class TestGoldenRare3:
    def test_trait_rarity_map_exact_values(self, rare3: Collection) -> None:
        rarities = trait_rarity_map(rare3)
        assert rarities == {
            ("background", "red"): 1.5,
            ("background", "blue"): 3.0,
            ("eyes", "green"): 3.0,
            ("eyes", "blue"): 1.5,
        }

    def test_scores_exact(self, rare3: Collection) -> None:
        by_id = {t.token_id: t for t in rare3.tokens}
        rarities = trait_rarity_map(rare3)
        assert score_token(by_id[1], rarities) == (2.25, 4.5)
        assert score_token(by_id[2], rarities) == (1.5, 3.0)
        assert score_token(by_id[3], rarities) == (2.25, 4.5)

    def test_rank_and_percentile_exact(self, rare3: Collection) -> None:
        ranks = rank_collection(rare3)
        assert [(r.token_id, r.score, r.rank, r.percentile) for r in ranks] == [
            (1, 2.25, 1, 0.0),
            (3, 2.25, 1, 0.0),  # tie: same rank, same percentile
            (2, 1.5, 3, 100.0),  # competition ranking skips rank 2
        ]


class TestFormula:
    def test_frequency_sum_is_one(self, pixel_cats: Collection) -> None:
        for rows in trait_stats(pixel_cats).values():
            assert sum(r.frequency for r in rows) == pytest.approx(1.0)

    def test_trait_rarity_is_n_over_count(self, pixel_cats: Collection) -> None:
        rarities = trait_rarity_map(pixel_cats)
        n = pixel_cats.n_tokens
        for (trait, value), expected in rarities.items():
            count = sum(
                1 for t in pixel_cats.tokens if t.traits.get(trait) == value
            )
            assert expected == pytest.approx(n / count)

    def test_mean_normalization_decouples_from_trait_count(self) -> None:
        """Two tokens with equal *mean* rarity but different *sums* tie."""
        col = Collection(
            name="norm",
            slug="norm",
            description="",
            tokens=[
                Token(token_id=1, traits={"background": "red"}),
                Token(token_id=2, traits={"background": "red", "eyes": "blue"}),
                Token(token_id=3, traits={"background": "blue", "eyes": "green"}),
            ],
            source="fixture",
        )
        ranks = rank_collection(col)
        by_id = {r.token_id: r for r in ranks}
        # (background,red)=3/2=1.5; (eyes,blue)=3/1=3.0; (eyes,green)=3/1=3.0
        assert by_id[2].score == pytest.approx((1.5 + 3.0) / 2)  # 2.25
        assert by_id[1].score == pytest.approx(1.5)  # single trait
        assert by_id[1].score_sum < by_id[2].score_sum
        assert by_id[2].rank < by_id[1].rank  # rarer mean ranks higher

    def test_traitless_token_scores_zero(self, rare3: Collection) -> None:
        col = Collection(
            name="x",
            slug="x",
            description="",
            tokens=[*rare3.tokens, Token(token_id=9, traits={})],
            source="fixture",
        )
        ranks = rank_collection(col)
        last = ranks[-1]
        assert last.token_id == 9
        assert last.score == 0.0
        assert last.rank == col.n_tokens

    def test_empty_collection_raises(self) -> None:
        col = Collection(
            name="empty", slug="empty", description="", tokens=[], source="fixture"
        )
        with pytest.raises(RarityError):
            rank_collection(col)
        with pytest.raises(RarityError):
            trait_counts(col, "background")

    def test_competition_ranking_skips_ranks(self, rare3: Collection) -> None:
        ranks = rank_collection(rare3)
        assert [r.rank for r in ranks] == [1, 1, 3]  # no rank 2


class TestDeterminism:
    def test_rerun_is_identical(self, pixel_cats: Collection) -> None:
        a = [r.as_dict() for r in rank_collection(pixel_cats)]
        b = [r.as_dict() for r in rank_collection(pixel_cats)]
        assert a == b

    def test_top_tokens_ordering(self, pixel_cats: Collection) -> None:
        top = top_tokens(pixel_cats, k=3)
        assert len(top) == 3
        assert top[0].rank == 1
        scores = [r.score for r in top]
        assert scores == sorted(scores, reverse=True)

    def test_bundled_fixture_rarest_is_token_7(self, pixel_cats: Collection) -> None:
        """README golden value: Pixel Cats #7 (gold bg + crown) is #1."""
        top = top_tokens(pixel_cats, k=1)[0]
        assert top.token_id == 7
        assert top.score == pytest.approx(17.0)  # (24/1 + 24/1 + 24/2 + 24/3) / 4
        assert top.percentile == 0.0