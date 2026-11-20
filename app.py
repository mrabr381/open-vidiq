"""Open-vidIQ web app — Streamlit, deploy-ready for Streamlit Community Cloud.

No key needed to try it: "Use sample data" runs the full analysis on a
bundled snapshot of a real public channel (Kurzgesagt – In a Nutshell,
20 most recent uploads, views as of 19 Nov 2026). With your own free
YouTube Data API key, paste any channel and analyse it live.
"""

from __future__ import annotations

import csv as csv_mod
import io
import os

import streamlit as st

from openvidiq import OpenVidIQError
from openvidiq.analysis import analyse, fmt_number
from openvidiq.generate import generate_pack
from openvidiq.outputs import build_report
from openvidiq.sample import load_sample
from openvidiq.youtube_api import fetch_channel_videos, resolve_channel

st.set_page_config(page_title="Open-vidIQ — free YouTube outlier research", page_icon="📺")
st.title("📺 Open-vidIQ")
st.markdown(
    "Free, open-source YouTube outlier / SEO research — the free alternative "
    "to vidIQ's paid tiers. Every number comes from the YouTube Data API or "
    "the bundled sample dataset. Nothing is invented."
)

with st.sidebar:
    st.header("Settings")
    mode = st.radio("Data source", ["Sample channel (no key)", "Live channel (API key)"])
    api_key = st.text_input("YouTube Data API v3 key", type="password",
                            help="Free — $0, 10,000 units/day. Google Cloud Console → enable YouTube Data API v3.")
    gemini_key = st.text_input("Gemini API key (optional)", type="password",
                               help="Free tier, bring-your-own-key. Only polishes the generated titles.")
    max_videos = st.slider("Max videos to analyse", 10, 200, 50)

channel_input = st.text_input(
    "Channel (ID, @handle, URL, or name)",
    value="@kurzgesagt",
    disabled=(mode == "Sample channel (no key)"),
)
niche = st.text_input("Niche keyword (optional)", value="science",
                      help="Seeds the generated titles and tags, e.g. 'science'.")

if st.button("🔍 Analyse channel", type="primary"):
    try:
        if mode.startswith("Sample"):
            channel, videos = load_sample()
            source = "sample"
            st.info("Using the bundled SAMPLE dataset: Kurzgesagt – In a Nutshell, "
                    "20 most recent public uploads, views as of 19 Nov 2026.")
        else:
            key = (api_key or os.environ.get("YOUTUBE_API_KEY", "")).strip()
            if not key:
                st.error("No YouTube API key. Add one above, set YOUTUBE_API_KEY, or use the sample channel.")
                st.stop()
            with st.spinner("Resolving channel…"):
                channel = resolve_channel(channel_input, key)
            with st.spinner(f"Fetching up to {max_videos} videos from {channel['title']}…"):
                videos = fetch_channel_videos(channel["channel_id"], key, max_videos)
            source = "youtube-api"
        with st.spinner("Analysing…"):
            analysis = analyse(channel, videos, niche=niche)
            pack = generate_pack(analysis, gemini_key=(gemini_key or None))
        st.success(
            f"Done — {analysis['video_count']} videos, "
            f"{len(analysis['outliers'])} outliers, {len(analysis['notable'])} notable."
        )

        subs = f"{channel['subscribers']:,}" if channel.get("subscribers") is not None else "hidden"
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Subscribers", subs)
        c2.metric("Median views", fmt_number(analysis["median_views"]))
        c3.metric("Total views", fmt_number(analysis["total_views"]))
        c4.metric("Outliers (≥2×)", len(analysis["outliers"]))

        st.subheader("🏆 Outlier videos")
        if analysis["outliers"]:
            st.dataframe(
                [{
                    "Title": v["title"],
                    "Views": v["views"],
                    "Outlier score": f"{v['outlier_score']}×",
                    "Views/day": v["velocity"],
                    "Published": v["published_at"][:10],
                } for v in analysis["outliers"]],
                use_container_width=True, hide_index=True,
            )
        else:
            st.write("No video scored 2.0× the channel median in this set.")

        st.subheader("🔑 Top keywords")
        st.dataframe(
            [{
                "Word": k["word"], "Videos": k["videos"],
                "In outliers": k["outlier_videos"], "Lift": f"{k['lift']}×",
            } for k in analysis["keywords"]["top_overall"][:15]],
            use_container_width=True, hide_index=True,
        )

        st.subheader("✍️ Title patterns")
        pat = analysis["title_patterns"]
        st.dataframe(
            [{
                "Pattern": label,
                "Outliers": pat["outliers"][key],
                "All videos": pat["all_videos"][key],
            } for label, key in [
                ("Avg title length (chars)", "avg_length"),
                ("Titles with a number (%)", "with_number"),
                ("Titles with [brackets] / (parens) (%)", "with_brackets"),
                ("Titles ending in a question (%)", "is_question"),
                ("Titles with a hook word (%)", "with_hook_word"),
            ]],
            use_container_width=True, hide_index=True,
        )

        st.subheader("💡 Generated titles")
        st.caption(pack["note"])
        for i, title in enumerate(pack["titles"], start=1):
            st.write(f"{i}. {title}")
        st.subheader("Suggested tags")
        st.write(", ".join(pack["tags"]))

        st.subheader("⬇️ Download the full report")
        report = build_report(analysis, pack, source)
        st.download_button("Download report.md", report, file_name="open-vidiq-report.md")
        buf = io.StringIO()
        writer = csv_mod.DictWriter(buf, fieldnames=[
            "title", "views", "outlier_score", "velocity", "published_at", "url"])
        writer.writeheader()
        for v in sorted(analysis["videos"], key=lambda x: x["views"], reverse=True):
            writer.writerow({k: v[k] for k in
                             ["title", "views", "outlier_score", "velocity", "published_at", "url"]})
        st.download_button("Download videos.csv", buf.getvalue(), file_name="videos.csv")
    except OpenVidIQError as exc:
        st.error(str(exc))
    except Exception as exc:  # noqa: BLE001 — show, don't crash silently
        st.error(f"Something went wrong: {exc}")

st.divider()
st.caption(
    "Open-vidIQ is free and open source (MIT). It is not affiliated with vidIQ, "
    "TubeBuddy, or YouTube. The sample dataset is a snapshot of real public "
    "data (Kurzgesagt, views as of 19 Nov 2026). Generated titles are "
    "suggestions, not predictions."
)
