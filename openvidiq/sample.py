"""Bundled sample dataset.

A snapshot of the real public channel Kurzgesagt – In a Nutshell
(@kurzgesagt): its 20 most recent public uploads, with exact view
counts read from vidIQ's public stats page on 20 November 2026
(figures as of 19 November 2026). See sample_data/SAMPLE_SOURCE.md
for the full sourcing note. The previous fictional "Mystery Lane"
dataset is kept as the offline test fixture in
sample_data/mystery_lane_fixture/.
"""

from __future__ import annotations

import json
from pathlib import Path

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_data"


def load_sample() -> tuple[dict, list[dict]]:
    """Return (channel, videos) from the bundled JSON files."""
    channel = json.loads((SAMPLE_DIR / "channel.json").read_text(encoding="utf-8"))
    videos = json.loads((SAMPLE_DIR / "videos.json").read_text(encoding="utf-8"))
    channel["source"] = "sample"
    for video in videos:
        video["url"] = f"https://www.youtube.com/watch?v={video['video_id']}"
    return channel, videos
