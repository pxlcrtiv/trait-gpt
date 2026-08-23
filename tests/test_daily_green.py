"""Daily Green automation tests: pool quality + deterministic rotation."""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
POOL_PATH = REPO_ROOT / "scripts" / "tips_pool.json"

# scripts/ is not a package — load daily_update.py by path.
_spec = importlib.util.spec_from_file_location(
    "daily_update", REPO_ROOT / "scripts" / "daily_update.py"
)
daily_update = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(daily_update)


@pytest.fixture(scope="module")
def pool() -> list[dict]:
    data = json.loads(POOL_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    return data


class TestPool:
    def test_pool_has_at_least_20_tips(self, pool) -> None:
        assert len(pool) >= 20

    def test_every_entry_has_title_and_body(self, pool) -> None:
        for tip in pool:
            assert isinstance(tip["title"], str) and tip["title"].strip()
            assert isinstance(tip["body"], str) and tip["body"].strip()

    def test_titles_unique(self, pool) -> None:
        titles = [t["title"] for t in pool]
        assert len(titles) == len(set(titles))


class TestRotation:
    def test_same_day_same_tip(self, pool) -> None:
        day = dt.date(2026, 8, 23)
        assert daily_update.pool_tip(day, pool) == daily_update.pool_tip(day, pool)

    def test_consecutive_days_differ(self, pool) -> None:
        a = daily_update.pool_tip(dt.date(2026, 8, 23), pool)
        b = daily_update.pool_tip(dt.date(2026, 8, 24), pool)
        assert a != b


class TestPlanning:
    def test_idempotent_when_up_to_date(self) -> None:
        now = dt.date(2026, 8, 23)
        assert daily_update.plan_days(now, {now}) == []

    def test_backfills_gap(self) -> None:
        now = dt.date(2026, 8, 23)
        have = {dt.date(2026, 8, 20)}
        assert daily_update.plan_days(now, have) == [
            dt.date(2026, 8, 21),
            dt.date(2026, 8, 22),
            dt.date(2026, 8, 23),
        ]

    def test_first_run_emits_only_today(self) -> None:
        now = dt.date(2026, 8, 23)
        assert daily_update.plan_days(now, set()) == [now]

    def test_backfill_capped(self) -> None:
        now = dt.date(2026, 8, 23)
        have = {dt.date(2026, 1, 1)}
        days = daily_update.plan_days(now, have)
        assert len(days) == daily_update.BACKFILL_DAYS
        assert days[-1] == now

    def test_existing_dates_regex_roundtrip(self, tmp_path, monkeypatch) -> None:
        tip = {"title": "T", "body": "B", "command": "trait-gpt rank"}
        log = tmp_path / "daily-tips.md"
        log.write_text(
            "\n".join(daily_update.LOG_HEADER) + "\n\n"
            + "\n".join(daily_update.render_entry(dt.date(2026, 8, 23), tip))
            + "\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(daily_update, "LOG_PATH", log)
        assert daily_update.existing_dates() == {dt.date(2026, 8, 23)}

    def test_rendered_entry_has_date_and_content(self) -> None:
        tip = {"title": "Rarity is math", "body": "N/count per trait value.", "command": ""}
        lines = daily_update.render_entry(dt.date(2026, 8, 23), tip)
        text = "\n".join(lines)
        assert "## 2026-08-23" in text
        assert "Rarity is math" in text