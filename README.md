![Open-vidIQ — Find which of your videos beat the average — free.](assets/hero.svg)

# Open-vidIQ 📺

[![CI](https://github.com/mrabr381/open-vidiq/actions/workflows/ci.yml/badge.svg)](https://github.com/mrabr381/open-vidiq/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![No API key required](https://img.shields.io/badge/API%20key-not%20required-brightgreen.svg)](#quickstart)

**Find which of your videos beat the average — free.**

Paste a channel. Find out what actually works on it — then generate titles from it. Open-vidIQ is a free, open-source YouTube outlier / SEO research agent: it finds a channel's outlier videos (views vs. its own median), measures velocity, finds the keywords its winners share, compares title patterns, spots the best posting windows, and generates titles, a description and tags — all from the free YouTube Data API. No paid tier, no account, no upload.

## Try it now

**Live sample report:** [see a real report, generated from a real channel](https://mrabr381.github.io/open-vidiq/sample_output/) — Kurzgesagt – In a Nutshell (@kurzgesagt, 25,800,000 subscribers, 4,020,025,007 total views, 401 videos as of 19 November 2026). The sample covers its 20 most recent public uploads: median **2,333,635** views per video, and the top video — "AI Just Crossed the Terrifying Line - Now What?" (24,185,772 views) — scored **10.36×** the median.

**Web app — 1-click deploy (repo owner):** [share.streamlit.io](https://share.streamlit.io) → Create app → repo `mrabr381/open-vidiq`, branch `main`, file `app.py` → Deploy. No key needed for the sample channel; optional `YOUTUBE_API_KEY` in Secrets for live channels.

**Run it on any public channel yourself** — for example, the same channel live:

```bash
python -m openvidiq --channel @kurzgesagt --keyword "science" --out report/
```

Live numbers come from your own free YouTube Data API key ($0, 10,000 quota units/day). The bundled sample is a snapshot (views as of 19 November 2026) — see [`sample_data/SAMPLE_SOURCE.md`](sample_data/SAMPLE_SOURCE.md) for exactly where every number came from.

## Quickstart

```bash
git clone https://github.com/mrabr381/open-vidiq.git
cd open-vidiq
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Try it with no key at all** (bundled real-channel snapshot):

```bash
python -m openvidiq --sample --out report/
```

**Analyse a real channel** — get a free YouTube Data API v3 key ($0, 10,000 quota units/day): Google Cloud Console → APIs & Services → enable "YouTube Data API v3" → Credentials → Create API key. Then:

```bash
cp .env.example .env   # add your YOUTUBE_API_KEY (never commit .env)
python -m openvidiq --channel @yourchannel --keyword "your niche" --out report/
```

## What it produces

- **Outlier score** — every video's views ÷ the channel's median views. 1.0× is exactly average; 2.0×+ is an outlier. No black box, the maths is in the report.
- **Velocity** — views ÷ days since publish, so a 3-month-old hit can be fairly compared with a 2-year-old one.
- **Keyword gap** — which words appear in outlier videos far more than in the rest ("lift"). Keywords come from titles + the summary part of descriptions (channel footers, links and shop promos are stripped out — see `openvidiq/analysis.py`).
- **Title patterns & posting windows** — length, numbers, brackets, questions, hook words (outliers vs. channel average, counted from the real titles) and best weekday/time-of-day by median views (only when 3+ videos fall in a bucket).
- **Generated titles, description & tags** — built from the channel's own keywords and title phrases. Optional Gemini polish with your own free key.

One command, five files:

```
report/
├── report.md            # outliers, keywords, patterns, posting windows, titles
├── generated_titles.md  # 10 titles + description + tags
├── videos.csv           # all videos, ranked by views, with metrics
├── outliers.csv         # the outliers only
└── keywords.csv         # keyword frequencies + outlier lift
```

## Usage

```
python -m openvidiq --sample --out report/
python -m openvidiq --channel UCxxxxxxxxxxxxxxxxxxxxxx --max-videos 100 --out report/
python -m openvidiq --channel https://www.youtube.com/@somechannel --keyword "cooking" --out report/
python -m openvidiq --channel "Channel Name" --api-key YOUR_KEY --out report/
```

| Option | What it does |
|---|---|
| `--sample` | Analyse the bundled Kurzgesagt snapshot (no key needed) |
| `--channel ID\|@handle\|URL\|name` | Channel to analyse (needs `YOUTUBE_API_KEY`) |
| `--keyword "..."` | Niche keyword — seeds titles and tags |
| `--api-key KEY` | YouTube Data API v3 key (or `YOUTUBE_API_KEY` env / `.env`) |
| `--gemini-key KEY` | Gemini key for AI-polished titles (or `GEMINI_API_KEY`); optional |
| `--max-videos N` | Videos to fetch, 1–500 (default 50) |
| `--out DIR` | Output directory (default `report/`) |

Exit codes: `0` done, `1` error with a plain message (bad key, no videos, no channel found), `2` bad arguments.

## Web app

```bash
streamlit run app.py
```

Pick "Sample channel" to try it with no key, or "Live channel" with your YouTube API key. Results show as tables on the page, with `report.md` and `videos.csv` download buttons.

## Comparison with vidIQ

Prices below are the ones verified in Nov 2026 market research — re-check before quoting elsewhere. The point of this table is the gap: the free tiers are deliberately throttled, and a 25-tool YouTube-SEO directory checked in Oct 2026 found **0 open-source tools among 25**.

| | vidIQ | TubeBuddy | **Open-vidIQ** |
|---|---|---|---|
| Free plan | 150 AI credits/mo, 3 keyword results/search, 3 ideas/day | Limited free tier | **Unlimited, free forever** |
| Paid plan | Boost $19/mo, Max $49/mo | A/B testing only in Legend $32.99/mo | **$0 — there is no paid plan** |
| Outlier research | Paid features | Paid features | **Free, median-based, transparent maths** |
| Title generation | Paid credits | Paid | **Free (local, or BYO Gemini free key)** |
| Data source | vidIQ's own | TubeBuddy's own | **YouTube Data API v3 — $0, 10,000 units/day** |
| Open source | No | No | **Yes (MIT)** |

Open-vidIQ is not affiliated with vidIQ, TubeBuddy, or YouTube.

## Quality promise — no invented numbers

- Every figure in a report is computed from the videos fetched (or the bundled sample, clearly labelled SAMPLE on every page). Views, subscribers, keywords and dates are never estimated or made up.
- Outlier scores are recomputed from the median in the same run — the test suite cross-checks them against the CSVs.
- Generated titles are *suggestions* built from keywords and phrases the channel has actually used. They carry no view guarantee, and the report says so.
- If the API key is missing, invalid, or out of quota, the tool says so plainly and stops — it never silently substitutes fake data.
- The sample snapshot is honest about its limits: view counts as of 19 Nov 2026, publish dates only (times set to 12:00 UTC), and likes/comments not collected (they are not needed for the maths). Full note: [`sample_data/SAMPLE_SOURCE.md`](sample_data/SAMPLE_SOURCE.md).

## Honest limitations

- **Live YouTube data was not end-to-end tested in the sandbox** — no YouTube API key was available there. The client was verified against the real API's error responses (a bad key returns a clear 400 message, exit 1), and the full pipeline was tested on the sample dataset. First run with a real free key on a normal network is the remaining check.
- **A successful Gemini call was not live-tested** either (no key in the sandbox). The Gemini path is verified by code path + failure fallback only; the local generator is the tested default.
- Views are a snapshot: a video published yesterday has had less time to gather views than a year-old one. Velocity corrects for that; outlier score does not — the report says so next to both numbers.
- The API returns at most the channel's public videos, newest first; private, deleted and age-restricted videos are invisible to it. Subscriber counts are hidden on some channels — views-per-subscriber is then unavailable and the report falls back to the median-based score.
- Keyword "lift" needs at least 2 videos using a word; tiny channels (under ~10 videos) give thin, noisy results — the report still runs, but says so.

## How it works

```
channel / niche ──► YouTube Data API v3 ──► videos (snippet + statistics)
        │                    (1 unit per call; search 100, used only if needed)
        ▼
  analysis.py ──► median, outlier score, velocity, keywords + lift,
                  title patterns, posting windows
        ▼
  generate.py ──► local titles/tags (Gemini polish optional, BYO free key)
        ▼
  outputs.py  ──► report.md + generated_titles.md + 3 CSVs
```

Tests: `python -m pytest tests/ -q` — median / outlier / velocity maths on the offline fixture and the real Kurzgesagt sample, plus a check that no URL/footer junk leaks into keywords. CI runs them on every push (see `.github/workflows/ci.yml`).

## Project structure

```
open-vidiq/
├── app.py                          # Streamlit web app (repo root, deploy-ready)
├── openvidiq/                      # cli.py, youtube_api.py, analysis.py, generate.py, outputs.py, sample.py
├── prompts/                        # editable Gemini prompts (titles, descriptions, tags)
├── sample_data/
│   ├── channel.json / videos.json  # Kurzgesagt snapshot: 20 most recent uploads, views as of 19 Nov 2026
│   ├── SAMPLE_SOURCE.md            # where every sample number came from
│   └── mystery_lane_fixture/       # old fictional channel, kept as the offline test fixture
├── tests/                          # pytest — outlier/velocity maths + keyword hygiene
├── .github/workflows/ci.yml
└── sample_output/                  # generated sample report + index.html demo page
```

## License

MIT — see [LICENSE](LICENSE).
