"""Tests for the outlier / velocity maths.

Two datasets:
- the offline fixture: the old fictional "Mystery Lane" channel
  (sample_data/mystery_lane_fixture/) — the verified numbers are
  median 12,850 views and top outlier 4.86x.
- the live sample: the real Kurzgesagt snapshot
  (sample_data/channel.json + videos.json) — median 2,333,635 views,
  top outlier 10.36x, 7 outliers.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from openvidiq.analysis import (
    analyse,
    days_since,
    enrich_videos,
    find_outliers,
    fmt_number,
    keyword_analysis,
    median_views,
)
from openvidiq.sample import load_sample

REPO = Path(__file__).resolve().parent.parent
FIXTURE_DIR = REPO / "sample_data" / "mystery_lane_fixture"
NOW = datetime(2026, 11, 20, tzinfo=timezone.utc)


def _load_fixture():
    channel = json.loads((FIXTURE_DIR / "channel.json").read_text(encoding="utf-8"))
    videos = json.loads((FIXTURE_DIR / "videos.json").read_text(encoding="utf-8"))
    return channel, videos


def test_fixture_median_views_is_12850():
    _, videos = _load_fixture()
    assert median_views(videos) == 12850.0


def test_fixture_top_outlier_is_4_86x():
    channel, videos = _load_fixture()
    enriched = enrich_videos(videos, channel["subscribers"], now=NOW)
    top = max(enriched, key=lambda v: v["outlier_score"])
    assert top["title"].startswith("The Tower of London")
    assert top["views"] == 62400
    assert top["outlier_score"] == 4.86  # 62400 / 12850
    outliers, _ = find_outliers(enriched)
    assert len(outliers) == 5


def test_velocity_is_views_per_day():
    _, videos = _load_fixture()
    enriched = enrich_videos(videos, 12400, now=NOW)
    for video in enriched:
        days = days_since(video["published_at"], now=NOW)
        assert video["velocity"] == round(video["views"] / days, 1)
        assert video["days_old"] == days
        assert days >= 1


def test_days_since_known_dates():
    assert days_since("2026-11-19T00:00:00Z", now=NOW) == 1
    assert days_since("2026-11-10T00:00:00Z", now=NOW) == 10
    assert days_since("not-a-date", now=NOW) == 1


def test_outlier_thresholds():
    _, videos = _load_fixture()
    enriched = enrich_videos(videos, 12400, now=NOW)
    outliers, notable = find_outliers(enriched)
    assert all(v["outlier_score"] >= 2.0 for v in outliers)
    assert all(1.5 <= v["outlier_score"] < 2.0 for v in notable)
    assert outliers == sorted(outliers, key=lambda v: v["outlier_score"], reverse=True)


def test_real_sample_kurzgesagt_maths():
    channel, videos = load_sample()
    assert channel["title"] == "Kurzgesagt – In a Nutshell"
    assert channel["subscribers"] == 25800000
    assert len(videos) == 20
    analysis = analyse(channel, videos, niche="science")
    assert analysis["median_views"] == 2333635  # int(2333635.5)
    assert analysis["total_views"] == 107923945
    top = analysis["outliers"][0]
    assert top["title"].startswith("AI Just Crossed the Terrifying Line")
    assert top["views"] == 24185772
    assert top["outlier_score"] == 10.36
    assert len(analysis["outliers"]) == 7
    assert len(analysis["notable"]) == 1


def test_real_sample_keywords_have_no_url_boilerplate():
    channel, videos = load_sample()
    analysis = analyse(channel, videos, niche="science")
    words = {k["word"] for k in analysis["keywords"]["top_overall"]}
    junk = {"https", "kgs", "link", "com", "discord", "patreon", "http", "www"}
    assert not (words & junk), f"URL/footer junk in keywords: {words & junk}"
    assert "cancer" in words or "civilization" in words


def test_fmt_number():
    assert fmt_number(999) == "999"
    assert fmt_number(12400) == "12.4K"
    assert fmt_number(1200000) == "1.2M"
    assert fmt_number(25800000) == "25.8M"


def test_keyword_lift_needs_two_videos():
    # A word in a single video is ignored, however extreme its views.
    _, videos = _load_fixture()
    enriched = enrich_videos(videos, 12400, now=NOW)
    keywords = keyword_analysis(enriched)
    for item in keywords["top_overall"]:
        assert item["videos"] >= 2
