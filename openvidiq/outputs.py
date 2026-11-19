"""Write the report: Markdown + CSVs. Every figure comes from the
analysis dict — this module computes nothing new, it only formats.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from .analysis import fmt_duration, fmt_number

VIDEO_COLUMNS = [
    "rank", "title", "video_id", "url", "published_at", "days_old",
    "views", "likes", "comments", "duration_seconds", "duration",
    "outlier_score", "views_per_sub", "velocity_views_per_day", "is_short",
]


def _video_row(rank: int, video: dict) -> dict:
    return {
        "rank": rank,
        "title": video["title"],
        "video_id": video["video_id"],
        "url": video["url"],
        "published_at": video["published_at"],
        "days_old": video["days_old"],
        "views": video["views"],
        "likes": video["likes"],
        "comments": video["comments"],
        "duration_seconds": video["duration_seconds"],
        "duration": fmt_duration(video["duration_seconds"]),
        "outlier_score": video["outlier_score"],
        "views_per_sub": video["views_per_sub"],
        "velocity_views_per_day": video["velocity"],
        "is_short": video["is_short"],
    }


def write_csvs(analysis: dict, out_dir: Path) -> dict[str, Path]:
    """videos.csv (all videos, ranked by views), outliers.csv, keywords.csv."""
    out_dir.mkdir(parents=True, exist_ok=True)
    by_views = sorted(analysis["videos"], key=lambda v: v["views"], reverse=True)
    paths: dict[str, Path] = {}

    videos_path = out_dir / "videos.csv"
    with videos_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=VIDEO_COLUMNS)
        writer.writeheader()
        for rank, video in enumerate(by_views, start=1):
            writer.writerow(_video_row(rank, video))
    paths["videos"] = videos_path

    outliers_path = out_dir / "outliers.csv"
    with outliers_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=VIDEO_COLUMNS)
        writer.writeheader()
        for rank, video in enumerate(analysis["outliers"], start=1):
            writer.writerow(_video_row(rank, video))
    paths["outliers"] = outliers_path

    keywords_path = out_dir / "keywords.csv"
    with keywords_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["word", "videos", "outlier_videos", "lift"])
        writer.writeheader()
        for item in analysis["keywords"]["top_overall"]:
            writer.writerow(item)
    paths["keywords"] = keywords_path
    return paths


def _outlier_table(outliers: list[dict]) -> str:
    if not outliers:
        return "_No video scored 2.0× the channel median — this channel has no clear outliers in the analysed set._\n"
    lines = ["| # | Video | Views | Outlier score | Views/day |", "|---|---|---|---|---|"]
    for i, video in enumerate(outliers, start=1):
        lines.append(
            f"| {i} | [{video['title']}]({video['url']}) | {video['views']:,} "
            f"| {video['outlier_score']}× | {video['velocity']:,} |"
        )
    return "\n".join(lines) + "\n"


def build_report(analysis: dict, pack: dict, source: str) -> str:
    """Full Markdown report. `source` is 'sample' or 'youtube-api'."""
    channel = analysis["channel"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sample_banner = (
        "> ⚠️ **SAMPLE DATA** — this report was generated from the bundled fictional "
        "channel, not a real YouTube channel. Run with `--channel` and a YouTube "
        "Data API key for real data.\n\n"
        if source == "sample" else ""
    )
    subs = (
        f"{channel['subscribers']:,}" if channel.get("subscribers") is not None
        else "hidden by the channel"
    )
    lines = [
        f"# YouTube Outlier Report — {channel['title']}",
        "",
        sample_banner,
        f"**Channel:** [{channel['title']}]({channel['url']})  ·  "
        f"**Subscribers:** {subs}  ·  **Videos analysed:** {analysis['video_count']}  ·  "
        f"**Generated:** {now}  ·  **Source:** {'sample dataset' if source == 'sample' else 'YouTube Data API v3'}",
        "",
        f"**Niche:** {analysis['niche'] or '— (pass --keyword to set one)'}",
        "",
        "## At a glance",
        "",
        f"- **Total views** (analysed videos): {analysis['total_views']:,}",
        f"- **Median views per video:** {analysis['median_views']:,}",
        f"- **Average views per video:** {analysis['avg_views']:,}",
        f"- **Outliers** (≥2.0× median): {len(analysis['outliers'])}  ·  "
        f"**Notable** (1.5–2.0×): {len(analysis['notable'])}",
        "",
        "Outlier score = a video's views ÷ the channel's median views. "
        "1.0× is exactly average; 2.0× means the video pulled double the "
        "channel's typical video. Velocity = views ÷ days since publish.",
        "",
        "## 🏆 Outlier videos",
        "",
        _outlier_table(analysis["outliers"]),
    ]
    if analysis["notable"]:
        lines += [
            "### Notable (1.5–2.0× median)",
            "",
        ]
        for video in analysis["notable"]:
            lines.append(
                f"- [{video['title']}]({video['url']}) — {video['views']:,} views, "
                f"{video['outlier_score']}×"
            )
        lines.append("")
    lines += [
        "## 🔑 Keywords",
        "",
        "Lift = how much more often a word appears in outlier videos than in "
        "the rest (1.0 = no difference). Only words in 2+ videos are listed.",
        "",
        "### Most frequent words",
        "",
        "| Word | Videos | In outliers | Lift |",
        "|---|---|---|---|",
    ]
    for item in analysis["keywords"]["top_overall"][:15]:
        lines.append(
            f"| {item['word']} | {item['videos']} | {item['outlier_videos']} | {item['lift']}× |"
        )
    lines += [
        "",
        "### Highest lift in outliers",
        "",
        "| Word | Videos | In outliers | Lift |",
        "|---|---|---|---|",
    ]
    for item in analysis["keywords"]["top_outlier_lift"][:8]:
        lines.append(
            f"| {item['word']} | {item['videos']} | {item['outlier_videos']} | {item['lift']}× |"
        )
    gap = analysis["keywords"]["gap_words"]
    lines += [
        "",
        "**Gap words** (lift ≥ 2.0×, in 3+ videos — topics the outliers own, "
        "the rest of the channel under-uses): "
        + (", ".join(w["word"] for w in gap) if gap else "none found in this set."),
        "",
        "## ✍️ Title patterns",
        "",
        "| Pattern | Outliers | All videos |",
        "|---|---|---|",
    ]
    pat = analysis["title_patterns"]
    for label, key in [
        ("Average title length (chars)", "avg_length"),
        ("Titles with a number (%)", "with_number"),
        ("Titles with [brackets] or (parens) (%)", "with_brackets"),
        ("Titles ending in a question (%)", "is_question"),
        ("Titles with a hook word (%)", "with_hook_word"),
    ]:
        lines.append(f"| {label} | {pat['outliers'][key]} | {pat['all_videos'][key]} |")
    lines += [
        "",
        "Hook words checked: secret, revealed, hidden, lost, mystery, haunted, "
        "cursed, truth, shocking, and similar. Percentages are counts from the "
        "actual titles in this set.",
        "",
        "## 🕒 Posting windows",
        "",
    ]
    windows = analysis["posting_windows"]
    if windows["by_weekday"]:
        lines.append("| Weekday | Videos | Median views |")
        lines.append("|---|---|---|")
        for row in windows["by_weekday"]:
            lines.append(f"| {row['day']} | {row['videos']} | {row['median_views']:,} |")
        lines.append("")
    else:
        lines.append("_Too few videos per weekday to call a best day (need 3+ per bucket)._")
        lines.append("")
    if windows["by_time_slot"]:
        lines.append("| Time slot (UTC) | Videos | Median views |")
        lines.append("|---|---|---|")
        for row in windows["by_time_slot"]:
            lines.append(f"| {row['slot']} | {row['videos']} | {row['median_views']:,} |")
        lines.append("")
    else:
        lines.append("_Too few videos per time slot to call a best time (need 3+ per bucket)._")
        lines.append("")
    lines += [
        "## 💡 Generated titles, description & tags",
        "",
        f"_{pack['note']}_",
        "",
    ]
    for i, title in enumerate(pack["titles"], start=1):
        lines.append(f"{i}. {title}")
    lines += [
        "",
        "### Suggested description (for the top title)",
        "",
        "```",
        pack["description"],
        "```",
        "",
        "### Suggested tags",
        "",
        ", ".join(pack["tags"]),
        "",
        "## Method & limitations",
        "",
        "- Outlier score, velocity, keywords and patterns are computed from "
        f"the {analysis['video_count']} videos in this report — nothing is estimated.",
        "- Views are a snapshot at generation time; a video published yesterday "
        "has had less time to accumulate views than a year-old one — velocity "
        "(views/day) corrects for that, outlier score does not.",
        "- The free YouTube Data API tier allows 10,000 quota units/day; this "
        "tool uses ~1 unit per video fetched (search, when needed, costs 100).",
        "- Subscriber counts are hidden on some channels — views-per-subscriber "
        "is then unavailable, and outlier score (median-based) is used instead.",
        "- Generated titles are suggestions built from your real keywords — "
        "they are not predictions and carry no view guarantee.",
        "",
        "_Generated by Open-vidIQ — free, open source, no paid tier._",
    ]
    return "\n".join(lines)


def write_report(analysis: dict, pack: dict, source: str, out_dir: Path) -> dict[str, Path]:
    """Write report.md, titles.md and the CSVs. Returns all paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = write_csvs(analysis, out_dir)
    report_path = out_dir / "report.md"
    report_path.write_text(build_report(analysis, pack, source), encoding="utf-8")
    paths["report"] = report_path
    titles_path = out_dir / "generated_titles.md"
    titles_path.write_text(
        "# Generated titles\n\n"
        f"_{pack['note']}_\n\n"
        + "\n".join(f"{i}. {t}" for i, t in enumerate(pack["titles"], start=1))
        + "\n\n## Description\n\n```\n" + pack["description"] + "\n```\n\n## Tags\n\n"
        + ", ".join(pack["tags"]) + "\n",
        encoding="utf-8",
    )
    paths["titles"] = titles_path
    return paths
