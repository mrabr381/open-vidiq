"""Pure analysis: every number is computed from the videos given.

No external calls, no invented data. All scores are derived from the
videos list (and the channel's subscriber count when known).
"""

from __future__ import annotations

import math
import re
import statistics
from collections import Counter
from datetime import datetime

from .youtube_api import days_since

STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with",
    "by", "at", "from", "is", "are", "was", "were", "be", "been", "it",
    "its", "this", "that", "these", "those", "i", "you", "he", "she",
    "we", "they", "my", "your", "his", "her", "our", "their", "as",
    "but", "not", "no", "so", "if", "then", "than", "too", "very",
    "can", "could", "will", "would", "should", "do", "does", "did",
    "have", "has", "had", "what", "when", "where", "who", "whom",
    "which", "why", "how", "about", "into", "over", "under", "out",
    "up", "down", "all", "any", "some", "more", "most", "other",
    "new", "one", "two", "also", "just", "like", "get", "got",
    # Prepositions / generic verbs and nouns: they flood word counts but
    # say nothing about a channel's topics. "lost" and "found" are kept —
    # for a mystery channel they are real topics, not filler.
    "against", "between", "through", "during", "before", "after",
    "without", "within", "upon", "among", "towards", "toward",
    # Meta words: they appear in almost every description ("this video",
    # "watch now", "us", "them") and say nothing about the topic.
    "video", "videos", "us", "them", "re", "now",
    "read", "look", "looks", "check", "take", "takes", "give", "made",
    "make", "find", "say", "says", "said", "tell", "tells", "know",
    "think", "want", "need", "see", "saw", "come", "went", "go",
    "man", "woman", "people", "person", "nobody", "someone",
    "something", "anyone", "everyone", "thing", "things",
    "way", "ways", "day", "days", "year", "years", "time",
    "still", "even", "back", "first", "last", "every", "each",
    "really", "actually", "very", "quite", "rather", "truly",
    "definitely", "probably", "maybe", "perhaps", "almost", "nearly",
}

HOOK_WORDS = {
    "secret", "secrets", "revealed", "exposed", "hidden", "lost", "found",
    "mystery", "haunted", "cursed", "forbidden", "nobody", "never", "real",
    "truth", "shocking", "insane", "amazing", "finally", "actually",
}

WORD_RE = re.compile(r"[a-z][a-z\-']{1,}")


def tokenize(text: str) -> list[str]:
    return [w for w in WORD_RE.findall((text or "").lower()) if w not in STOPWORDS]


def median_views(videos: list[dict]) -> float:
    views = sorted(v["views"] for v in videos)
    return float(statistics.median(views)) if views else 0.0


def enrich_videos(videos: list[dict], subscribers: int | None, now: datetime | None = None) -> list[dict]:
    """Add computed metrics to copies of the video dicts.

    outlier_score = views / channel median views (1.0 = exactly average).
    views_per_sub  = views / subscribers (None when subs are hidden).
    velocity       = views / days since publish.
    """
    median = median_views(videos)
    enriched = []
    for video in videos:
        days = days_since(video["published_at"], now=now)
        item = dict(video)
        item["days_old"] = days
        item["outlier_score"] = round(video["views"] / median, 2) if median else 0.0
        item["views_per_sub"] = (
            round(video["views"] / subscribers, 2) if subscribers else None
        )
        item["velocity"] = round(video["views"] / days, 1)
        item["is_short"] = video.get("duration_seconds", 0) > 0 and video["duration_seconds"] < 60
        enriched.append(item)
    return enriched


def find_outliers(enriched: list[dict], threshold: float = 2.0) -> tuple[list[dict], list[dict]]:
    """(outliers, notable) — outliers score >= threshold, notable 1.5–threshold."""
    outliers = [v for v in enriched if v["outlier_score"] >= threshold]
    notable = [v for v in enriched if 1.5 <= v["outlier_score"] < threshold]
    outliers.sort(key=lambda v: v["outlier_score"], reverse=True)
    notable.sort(key=lambda v: v["outlier_score"], reverse=True)
    return outliers, notable


URL_RE = re.compile(r"https?://\S+|www\.\S+|\b[a-z0-9-]+\.[a-z]{2,}(?:/\S*)?")


def _strip_urls(text: str) -> str:
    """Remove URLs before tokenizing.

    A raw link contributes junk tokens ("https", "kgs", "link", "com",
    "shop", "calendar" from shop.kgs.link/calendar-…) that then top
    the keyword table — they describe the channel's shop, not the
    video. Sponsor/promo paragraphs survive as plain words, but at
    1–2 videos each they no longer dominate.
    """
    return URL_RE.sub(" ", text or "")


def _description_summary(description: str) -> str:
    """The part of a description that actually describes the video.

    Real descriptions put the summary first and the boilerplate after
    ("Sources & further reading", "OUR CHANNELS", "HOW CAN YOU SUPPORT
    US?", "Follow us …"). Counting the whole description lets footer
    words ("discord", "caption", "patreon") flood the keyword table —
    on the Kurzgesagt sample they were the entire top-15. Cut at the
    first footer marker; fall back to the full text when there is none.
    """
    markers = (
        "sources & further reading", "sources:", "our channels",
        "how can you support us", "follow us", "support us on patreon",
        "our sources", "further reading",
    )
    lowered = (description or "").lower()
    cut = len(description or "")
    for marker in markers:
        idx = lowered.find(marker)
        if idx != -1:
            cut = min(cut, idx)
    return (description or "")[:cut]


def keyword_analysis(enriched: list[dict]) -> dict:
    """Word frequency in titles + descriptions, and outlier lift.

    lift(word) = share of outlier videos using the word / share of
    non-outlier videos using it. A lift above 1 means the word shows up
    proportionally more in outperforming videos. Words appearing in
    fewer than 2 videos are ignored — a single video proves nothing.
    """
    outliers, _ = find_outliers(enriched)
    outlier_ids = {v["video_id"] for v in outliers}
    total_counts: Counter = Counter()
    outlier_doc: Counter = Counter()
    rest_doc: Counter = Counter()
    for video in enriched:
        text = _strip_urls(video["title"] + " " + _description_summary(video.get("description", "")))
        words = set(tokenize(text))
        total_counts.update(words)
        target = outlier_doc if video["video_id"] in outlier_ids else rest_doc
        target.update(words)
    n_out, n_rest = max(1, len(outliers)), max(1, len(enriched) - len(outliers))
    # Boilerplate filter: a word in more than half the videos carries no
    # signal — it is channel boilerplate repeated in every description
    # (footers, "watch in other languages" links, social links), not a
    # topic. Real descriptions (e.g. the Kurzgesagt sample) are full of
    # it; without this the keyword table is just the channel footer.
    # A genuine topic word rarely clears 50% of a channel's videos.
    boilerplate_cutoff = len(enriched) // 2
    keywords = []
    for word, count in total_counts.most_common():
        if count < 2:
            continue
        if count > boilerplate_cutoff and len(enriched) >= 5:
            continue
        out_share = outlier_doc.get(word, 0) / n_out
        rest_share = rest_doc.get(word, 0) / n_rest
        lift = round(out_share / rest_share, 2) if rest_share else (round(out_share * n_rest, 2) if out_share else 0.0)
        keywords.append({
            "word": word,
            "videos": count,
            "outlier_videos": outlier_doc.get(word, 0),
            "lift": lift,
        })
    # Fully deterministic ordering (word as final tiebreaker): keyword
    # counts are built from sets, whose iteration order varies per
    # process, so a sort without a tiebreaker would shuffle tied rows
    # between runs and make reports non-reproducible.
    keywords.sort(key=lambda k: (-k["lift"], -k["videos"], k["word"]))
    return {
        "top_overall": sorted(keywords, key=lambda k: (-k["videos"], -k["lift"], k["word"]))[:15],
        "top_outlier_lift": [k for k in keywords if k["outlier_videos"] > 0][:15],
        "gap_words": [k for k in keywords if k["lift"] >= 2.0 and k["videos"] >= 3][:10],
    }


def title_pattern_analysis(enriched: list[dict]) -> dict:
    """What do outlier titles do differently from the rest?

    Compares: title length, numbers, [brackets], questions, hook words,
    and ALL-CAPS words — outlier average vs. channel average. Every
    figure is a count from the actual titles.
    """
    outliers, _ = find_outliers(enriched)

    def features(videos: list[dict]) -> dict:
        if not videos:
            return {"n": 0, "avg_length": 0.0, "with_number": 0.0, "with_brackets": 0.0,
                    "is_question": 0.0, "with_hook_word": 0.0, "avg_hook_words": 0.0}
        n = len(videos)
        lengths, nums, brackets, questions, hooks = [], 0, 0, 0, 0
        hook_total = 0
        for video in videos:
            title = video["title"]
            lengths.append(len(title))
            if re.search(r"\d", title):
                nums += 1
            if "[" in title or "(" in title:
                brackets += 1
            if title.strip().endswith("?"):
                questions += 1
            # Check hook words against the raw title, not tokenize():
            # tokenize() drops generic words, and "nobody" is both a
            # generic pronoun (useless as a keyword) and a real hook word.
            title_words = set(WORD_RE.findall(title.lower()))
            found = HOOK_WORDS & title_words
            hook_total += len(found)
            if found:
                hooks += 1
        return {
            "n": n,
            "avg_length": round(sum(lengths) / n, 1),
            "with_number": round(nums / n * 100, 1),
            "with_brackets": round(brackets / n * 100, 1),
            "is_question": round(questions / n * 100, 1),
            "with_hook_word": round(hooks / n * 100, 1),
            "avg_hook_words": round(hook_total / n, 2),
        }

    return {"outliers": features(outliers), "all_videos": features(enriched)}


def posting_windows(enriched: list[dict]) -> dict:
    """Best weekday / time-of-day by median views (UTC publish time).

    Only reported when at least 3 videos fall in a bucket — a single
    video's views say nothing about a time slot.
    """
    def median_for(videos: list[dict]) -> float:
        return float(statistics.median([v["views"] for v in videos])) if videos else 0.0

    by_day: dict[str, list[dict]] = {}
    by_slot: dict[str, list[dict]] = {}
    for video in enriched:
        try:
            published = datetime.fromisoformat(video["published_at"].replace("Z", "+00:00"))
        except ValueError:
            continue
        by_day.setdefault(published.strftime("%A"), []).append(video)
        hour = published.hour
        slot = "Morning (06–12)" if 6 <= hour < 12 else (
            "Afternoon (12–18)" if 12 <= hour < 18 else (
                "Evening (18–24)" if 18 <= hour < 24 else "Night (00–06)"))
        by_slot.setdefault(slot, []).append(video)
    days = [
        {"day": day, "videos": len(vs), "median_views": int(median_for(vs))}
        for day, vs in by_day.items() if len(vs) >= 3
    ]
    slots = [
        {"slot": slot, "videos": len(vs), "median_views": int(median_for(vs))}
        for slot, vs in by_slot.items() if len(vs) >= 3
    ]
    days.sort(key=lambda d: d["median_views"], reverse=True)
    slots.sort(key=lambda s: s["median_views"], reverse=True)
    return {"by_weekday": days, "by_time_slot": slots}


def analyse(channel: dict, videos: list[dict], niche: str = "") -> dict:
    """Full analysis. `niche` is only used as a label / generator seed."""
    enriched = enrich_videos(videos, channel.get("subscribers"))
    outliers, notable = find_outliers(enriched)
    median = median_views(videos)
    total_views = sum(v["views"] for v in videos)
    return {
        "channel": channel,
        "niche": niche.strip(),
        "video_count": len(enriched),
        "total_views": total_views,
        "median_views": int(median),
        "avg_views": int(total_views / len(enriched)) if enriched else 0,
        "videos": enriched,
        "outliers": outliers,
        "notable": notable,
        "keywords": keyword_analysis(enriched),
        "title_patterns": title_pattern_analysis(enriched),
        "posting_windows": posting_windows(enriched),
    }


def fmt_number(n: int | float) -> str:
    """12,400 / 1.2M / 45.6K — display only, never used in maths."""
    n = float(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:g}M"
    if n >= 1_000:
        return f"{n / 1_000:g}K"
    return f"{int(n):,}"


def fmt_duration(seconds: int) -> str:
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"
