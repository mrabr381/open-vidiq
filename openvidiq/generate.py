"""Title / description / tag generation.

Two engines, both grounded in the analysis — nothing is invented:

* Local (default, no key): deterministic formulas built from the
  channel's own top keywords, its outlier title patterns, and the
  user's niche keyword. Every suggested title contains a keyword that
  actually appears in the channel's videos.
* Gemini (optional, BYO free key): rewrites the same grounded brief
  with the prompts in prompts/. If the call fails for any reason, the
  local output is returned instead, with a note saying so.

A generated title is a *suggestion*, not a fact — the report says so.
"""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path

from . import OpenVidIQError

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
GEMINI_TIMEOUT_SECONDS = 120


def _load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _top_words(analysis: dict, limit: int = 8) -> list[str]:
    seen: list[str] = []
    for item in analysis["keywords"]["top_overall"]:
        if item["word"] not in seen:
            seen.append(item["word"])
    return seen[:limit]


def _title_bigrams(analysis: dict, limit: int = 8) -> list[str]:
    """Two-word topic phrases from the channel's own titles.

    Single keywords make broken titles ("The Nobody: …", "Why Does
    Evidence…?"). Real topics are phrases — "lost princes", "secret
    tunnels", "cursed objects" — so seeds are adjacent non-stopwords
    from titles, ranked by frequency with an outlier bonus. Each phrase
    is one the channel has actually used.
    """
    from collections import Counter

    from .analysis import STOPWORDS, WORD_RE

    counts: Counter = Counter()
    outlier_ids = {v["video_id"] for v in analysis["outliers"]}
    for video in analysis["videos"]:
        # Candidate phrases must occur verbatim in the title text.
        # Stripping stopwords first would join words that were never
        # adjacent ("Cursed Objects in British Museums" -> the nonsense
        # phrase "objects british"), so contiguity is checked against
        # the raw title, not the stripped word list.
        raw = re.sub(r"[^a-z0-9 ]", " ", video["title"].lower())
        raw = re.sub(r"\s+", " ", raw).strip()
        padded = f" {raw} "
        words = [w for w in WORD_RE.findall(video["title"].lower())
                 if w not in STOPWORDS and len(w) >= 3]
        for first, second in zip(words, words[1:]):
            phrase = f"{first} {second}"
            if f" {phrase} " not in padded:
                continue
            counts[phrase] += 2 if video["video_id"] in outlier_ids else 1
    ranked = [phrase for phrase, _ in
              sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
              if len(phrase) >= 7]
    return [phrase.title() for phrase in ranked[:limit]]


def local_titles(analysis: dict, count: int = 10) -> list[str]:
    """Deterministic titles from real topic phrases + observed patterns.

    Seeds are two-word phrases the channel has actually used, so titles
    read like the channel's own ("The Secret Tunnels: What Really
    Happened?") instead of single-keyword word salad. Which formulas are
    used follows the outliers' real devices (numbers, questions).
    The niche keyword, when given, is title-cased and leads the first title.
    """
    phrases = _title_bigrams(analysis)
    words = _top_words(analysis)
    niche = (analysis.get("niche") or "").strip()
    niche_title = " ".join(w.capitalize() for w in niche.split()) if niche else ""
    patterns = analysis["title_patterns"]
    outliers_use_numbers = patterns["outliers"].get("with_number", 0) >= 20
    outliers_use_questions = patterns["outliers"].get("is_question", 0) >= 20
    titles: list[str] = []
    seen: set[str] = set()

    def add(title: str) -> None:
        title = re.sub(r"\s+", " ", title).strip()
        if title and title.lower() not in seen and 25 <= len(title) <= 100:
            seen.add(title.lower())
            titles.append(title)

    if niche_title and phrases:
        add(f"{niche_title}: The {phrases[0]} Files")
    for i, phrase in enumerate(phrases):
        if len(titles) >= count:
            break
        # Max 3 titles per phrase, so the pack covers several topics
        # instead of exhausting every formula on the first two.
        before = len(titles)
        add(f"The {phrase}: What Really Happened?")
        if outliers_use_numbers and len(titles) < count and len(titles) - before < 3:
            add(f"{3 + i} Secrets of the {phrase}, Finally Explained")
        if len(titles) < count and len(titles) - before < 3:
            add(f"The Hidden Truth About {phrase}")
        if outliers_use_questions and len(titles) < count and len(titles) - before < 3:
            # Plural phrases ("Cursed Objects") take "Do", singular "Does".
            verb = "Do" if phrase.endswith("s") else "Does"
            add(f"Why {verb} the {phrase} Still Haunt Us?")
        if len(titles) < count and len(titles) - before < 3:
            add(f"{phrase} — The Question That Won't Go Away")
    for word in words:
        if len(titles) >= count:
            break
        add(f"The Hidden Truth About {word.title()}")
    return titles[:count]


def local_description(analysis: dict, title: str) -> str:
    """Description built only from the channel's real keywords."""
    words = _top_words(analysis, limit=6)
    channel = analysis["channel"]["title"]
    niche = analysis.get("niche") or "this topic"
    keyword_line = ", ".join(words)
    return (
        f"{title}\n\n"
        f"In this video from {channel}, we dig into {niche} — "
        f"including {keyword_line}.\n\n"
        f"Chapters, sources and links are in the pinned comment.\n"
        f"Subscribe for a new video every week."
    )


def local_tags(analysis: dict, limit: int = 15) -> list[str]:
    """Tags = the channel's own top keywords (+ niche), lowercased."""
    tags: list[str] = []
    niche = (analysis.get("niche") or "").strip().lower()
    if niche and niche not in tags:
        tags.append(niche)
    seen_roots: set[str] = set()
    for word in _top_words(analysis, limit=limit):
        if word in tags:
            continue
        # Skip a word whose singular/plural twin is already a tag
        # ("suspect" after "suspects" adds nothing).
        root = word[:-1] if word.endswith("s") and len(word) > 3 else word
        if root in seen_roots:
            continue
        seen_roots.add(root)
        tags.append(word)
    return tags[:limit]


def _gemini_call(prompt: str, api_key: str) -> str:
    """One Gemini call, time-boxed in a daemon thread.

    The SDK's own timeout does not bound a TLS-level hang (proven in
    the sister project), so the wall-clock limit is enforced here.
    Raises on any failure; the caller falls back to local output.
    """
    import google.generativeai as genai  # imported lazily — optional dep

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    result: dict = {}

    def _run() -> None:
        try:
            result["text"] = model.generate_content(prompt).text
        except Exception as exc:  # noqa: BLE001 — fallback handles it
            result["error"] = str(exc)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=GEMINI_TIMEOUT_SECONDS)
    if thread.is_alive():
        raise OpenVidIQError("Gemini call timed out after 120s; using local output instead.")
    if "error" in result:
        raise OpenVidIQError(result["error"])
    return (result.get("text") or "").strip()


def generate_pack(analysis: dict, gemini_key: str | None = None) -> dict:
    """Generate titles, one description, and tags.

    Returns {"engine": "gemini"|"local", "note": str, "titles": [...],
    "description": str, "tags": [...]}. The note always states which
    engine produced the pack, so nobody mistakes local formulas for AI.
    """
    titles = local_titles(analysis)
    tags = local_tags(analysis)
    description = local_description(analysis, titles[0] if titles else "New video")
    pack = {
        "engine": "local",
        "note": (
            "Generated locally from your channel's own keywords and title "
            "patterns — no API key used. Set GEMINI_API_KEY for AI-polished versions."
        ),
        "titles": titles,
        "description": description,
        "tags": tags,
    }
    if not gemini_key:
        return pack
    brief = {
        "channel": analysis["channel"]["title"],
        "niche": analysis.get("niche") or "",
        "median_views": analysis["median_views"],
        "top_keywords": _top_words(analysis),
        "outlier_titles": [v["title"] for v in analysis["outliers"][:5]],
        "title_patterns": analysis["title_patterns"]["outliers"],
        "local_titles": titles,
    }
    prompt = (
        _load_prompt("titles")
        + "\n\nChannel brief (JSON, all figures real — do not invent others):\n"
        + json.dumps(brief, indent=2)
        + "\n\nReturn 10 titles, one per line, no numbering, no extra text."
    )
    try:
        text = _gemini_call(prompt, gemini_key)
        lines = [line.strip("0123456789. -•\t") for line in text.splitlines()]
        lines = [line for line in lines if 10 <= len(line) <= 100]
        if len(lines) >= 5:
            pack["engine"] = "gemini"
            pack["titles"] = lines[:10]
            pack["note"] = (
                "Titles polished by Gemini (BYO free key) from your channel's "
                "real keywords and outlier titles. Description and tags are "
                "local, built from the same data."
            )
    except Exception as exc:  # noqa: BLE001 — local fallback is the design
        pack["note"] += f" Gemini was tried and failed ({exc}); local output used."
    return pack
