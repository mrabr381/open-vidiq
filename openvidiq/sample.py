"""Bundled sample dataset.

A clearly fictional channel ("Mystery Lane") with internally consistent
numbers, so the app is demonstrably useful with no API key. The sample
report labels itself SAMPLE on every page — sample figures are never
presented as a real channel's data.
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
