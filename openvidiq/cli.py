"""Command-line interface.

    python -m openvidiq --sample --out report/
    python -m openvidiq --channel @mysterylane --keyword "unsolved mysteries" --out report/
    python -m openvidiq --channel UCxxxxxxxxxxxxxxxxxxxxxx --max-videos 100 --out report/

Keys come from --api-key / --gemini-key, or the environment
(YOUTUBE_API_KEY, GEMINI_API_KEY), or a .env file. They are never
written to any output file. Without a YouTube key, only --sample works —
the tool refuses to invent a dataset.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # optional dependency — env vars still work
    def load_dotenv(*args, **kwargs):  # type: ignore[no-redef]
        return False

from . import OpenVidIQError
from .analysis import analyse
from .generate import generate_pack
from .outputs import write_report
from .sample import load_sample
from .youtube_api import fetch_channel_videos, resolve_channel


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openvidiq",
        description="Open-source YouTube outlier / SEO research agent. "
        "Finds what actually works on a channel and generates titles from it.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--sample", action="store_true",
                       help="Analyse the bundled fictional sample channel (no key needed).")
    group.add_argument("--channel", metavar="ID|@HANDLE|URL|NAME",
                       help="YouTube channel to analyse (needs YOUTUBE_API_KEY).")
    parser.add_argument("--keyword", default="",
                        help="Niche keyword, e.g. 'unsolved mysteries' (seed for titles/tags).")
    parser.add_argument("--api-key", default="",
                        help="YouTube Data API v3 key (or YOUTUBE_API_KEY env / .env).")
    parser.add_argument("--gemini-key", default="",
                        help="Gemini API key for AI-polished titles (or GEMINI_API_KEY env). "
                        "Optional — without it, titles are generated locally.")
    parser.add_argument("--max-videos", type=int, default=50,
                        help="Max videos to fetch from the channel (default 50, max 500).")
    parser.add_argument("--out", default="report",
                        help="Output directory for report.md + CSVs (default: report/).")
    return parser


def _key(explicit: str, env_name: str, env: dict) -> str:
    return (explicit or env.get(env_name, "") or "").strip()


def run(argv: list[str] | None = None, env: dict | None = None) -> int:
    load_dotenv()
    import os

    env = dict(os.environ) if env is None else env
    args = build_parser().parse_args(argv)
    if args.max_videos < 1 or args.max_videos > 500:
        print("error: --max-videos must be between 1 and 500.", file=sys.stderr)
        return 2
    api_key = _key(args.api_key, "YOUTUBE_API_KEY", env)
    gemini_key = _key(args.gemini_key, "GEMINI_API_KEY", env) or None
    try:
        if args.sample:
            channel, videos = load_sample()
            source = "sample"
            print("Using the bundled SAMPLE channel 'Mystery Lane' (fictional data).")
        else:
            if not api_key:
                raise OpenVidIQError(
                    "No YouTube API key found. Set YOUTUBE_API_KEY, pass --api-key, "
                    "or run with --sample to try the bundled demo dataset."
                )
            print(f"Resolving channel {args.channel!r} …")
            channel = resolve_channel(args.channel, api_key)
            subs = f"{channel['subscribers']:,}" if channel.get("subscribers") else "hidden"
            print(f"Found: {channel['title']} ({subs} subscribers). Fetching videos …")
            videos = fetch_channel_videos(channel["channel_id"], api_key, args.max_videos)
            source = "youtube-api"
        print(f"Analysing {len(videos)} videos …")
        analysis = analyse(channel, videos, niche=args.keyword)
        pack = generate_pack(analysis, gemini_key=gemini_key)
        print(f"Titles generated with the {pack['engine']} engine.")
        out_dir = Path(args.out)
        paths = write_report(analysis, pack, source, out_dir)
        print(f"\nDone — {len(videos)} videos, {len(analysis['outliers'])} outliers, "
              f"{len(analysis['notable'])} notable, in {out_dir}/:")
        for name in ("report", "titles", "videos", "outliers", "keywords"):
            print(f"  - {paths[name].name}")
        return 0
    except OpenVidIQError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
