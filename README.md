# Open-vidIQ 📺

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![No API key required](https://img.shields.io/badge/API%20key-not%20required-brightgreen.svg)](#quickstart)
[![Streamlit](https://img.shields.io/badge/Streamlit-app-FF4B4B.svg)](#live-demo)
[![GitHub Pages demo](https://img.shields.io/badge/demo-live%20sample%20report-22c55e.svg)](#live-demo)

**Paste a channel. Find out what actually works on it — then generate titles from it.**

Open-vidIQ is a free, open-source YouTube outlier / SEO research agent. It finds a
channel's outlier videos (views vs. its own median), measures velocity, finds the
keywords its winners share, compares title patterns, spots the best posting
windows, and generates titles, a description and tags — all from the free
YouTube Data API. No paid tier, no account, no upload.

> **Live demo:** a real sample report, generated from the bundled fictional
> channel — [sample report page](sample_output/index.html) (works on
> GitHub Pages, no server needed) — or run the web app on Streamlit Community
> Cloud (one-click deploy, see [Live demo](#live-demo)).

## Table of contents

- [Before / after](#before--after)
- [What it produces](#what-it-produces)
- [Live demo](#live-demo)
- [Quickstart](#quickstart)
- [Usage](#usage)
- [Web app](#web-app)
- [Comparison with vidIQ](#comparison-with-vidiq)
- [Quality promise — no invented numbers](#quality-promise--no-invented-numbers)
- [How it works](#how-it-works)
- [Honest limitations](#honest-limitations)
- [Project structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## Before / after

**Before — guessing what to make next:**

```
📹 "Maybe another video like the last one?"
📊 vidIQ free: 3 keyword results per search, 3 ideas a day
😩 …and the outlier that actually worked sits unnoticed in the back catalogue
```

**After — one command:**

```bash
python -m openvidiq --channel @yourchannel --keyword "your niche" --out report/
```

```
report/
├── report.md            # outliers, keywords, patterns, posting windows, titles
├── generated_titles.md  # 10 titles + description + tags
├── videos.csv           # all videos, ranked by views, with metrics
├── outliers.csv         # the outliers only
└── keywords.csv         # keyword frequencies + outlier lift
```

<details>
<summary>📄 See a real excerpt (from the sample report)</summary>

```
## 🏆 Outlier videos
| # | Video | Views | Outlier score | Views/day |
| 1 | The Tower of London's Lost Princes — What Really Happened? | 62,400 | 4.86× | 95.1 |
| 2 | Jack the Ripper: The Suspect Nobody Talks About | 45,800 | 3.56× | 74.5 |

## 💡 Generated titles
1. Unsolved Mysteries: The Cursed Objects Files
2. The Cursed Objects: What Really Happened?
3. 3 Secrets of the Cursed Objects, Finally Explained
```

The sample report in full: [sample_output/report.md](sample_output/report.md).

</details>

## What it produces

- **Outlier score** — every video's views ÷ the channel's median views.
  1.0× is exactly average; 2.0×+ is an outlier. No black box, the maths is
  in the report.
- **Velocity** — views ÷ days since publish, so a 3-month-old hit can be
  fairly compared with a 2-year-old one.
- **Keyword gap** — which words appear in outlier videos far more than in
  the rest ("lift"), and which topics the winners own that the channel
  under-uses.
- **Title patterns** — length, numbers, brackets, questions, hook words:
  outlier average vs. channel average, as counts from the real titles.
- **Posting windows** — best weekday and time-of-day by median views
  (only when 3+ videos fall in a bucket — one video proves nothing).
- **Generated titles, description & tags** — built from the channel's own
  keywords and title phrases. Optional Gemini polish with your own free key.

## Live demo

- ✅ **Already built:** [sample_output/index.html](sample_output/index.html) —
  static page showing the full sample pack (summary, outliers, keywords,
  generated titles, download links), zero external requests.
  **ABR's step (2 min):** repo Settings → Pages → Source: Deploy from a
  branch → `main`, folder `/ (root)` → Save. Live at
  `https://mrabr381.github.io/open-vidiq/sample_output/`.
- ✅ **Streamlit Cloud ready:** `app.py` at the repo root, clean
  `requirements.txt`. **ABR's step (1 click):** share.streamlit.io →
  Create app → repo `mrabr381/open-vidiq`, branch `main`, file `app.py` →
  Deploy. No key needed for the sample channel; optional
  `YOUTUBE_API_KEY` in Secrets for live channels.

## Quickstart

```bash
git clone https://github.com/mrabr381/open-vidiq.git
cd open-vidiq
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Try it with no key at all** (bundled fictional sample channel):

```bash
python -m openvidiq --sample --out report/
```

**Analyse a real channel** — get a free YouTube Data API v3 key
($0, 10,000 quota units/day): Google Cloud Console → APIs & Services →
enable "YouTube Data API v3" → Credentials → Create API key. Then:

```bash
cp .env.example .env   # add your YOUTUBE_API_KEY (never commit .env)
python -m openvidiq --channel @yourchannel --keyword "your niche" --out report/
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
| `--sample` | Analyse the bundled fictional channel (no key needed) |
| `--channel ID\|@handle\|URL\|name` | Channel to analyse (needs `YOUTUBE_API_KEY`) |
| `--keyword "..."` | Niche keyword — seeds titles and tags |
| `--api-key KEY` | YouTube Data API v3 key (or `YOUTUBE_API_KEY` env / `.env`) |
| `--gemini-key KEY` | Gemini key for AI-polished titles (or `GEMINI_API_KEY`); optional |
| `--max-videos N` | Videos to fetch, 1–500 (default 50) |
| `--out DIR` | Output directory (default `report/`) |

Exit codes: `0` done, `1` error with a plain message (bad key, no videos,
no channel found), `2` bad arguments.

## Web app

```bash
streamlit run app.py
```

Pick "Sample channel" to try it with no key, or "Live channel" with your
YouTube API key. Results show as tables on the page, with `report.md` and
`videos.csv` download buttons.

## Comparison with vidIQ

Prices below are the ones verified in Nov 2026 market research — re-check
before quoting elsewhere. The point of this table is the gap: the free tiers
are deliberately throttled, and a 25-tool YouTube-SEO directory checked in
Oct 2026 found **0 open-source tools among 25**.

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

- Every figure in a report is computed from the videos fetched (or the
  bundled sample, clearly labelled SAMPLE on every page). Views,
  subscribers, keywords and dates are never estimated or made up.
- Outlier scores are recomputed from the median in the same run — the
  test suite cross-checks them against the CSVs.
- Generated titles are *suggestions* built from keywords and phrases the
  channel has actually used. They carry no view guarantee, and the report
  says so.
- If the API key is missing, invalid, or out of quota, the tool says so
  plainly and stops — it never silently substitutes fake data.

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

## Honest limitations

- **Live YouTube data was not end-to-end tested in the sandbox** — no
  YouTube API key was available there. The client was verified against
  the real API's error responses (a bad key returns a clear 400 message,
  exit 1), and the full pipeline was tested on the sample dataset. First
  run with a real free key on a normal network is the remaining check.
- **A successful Gemini call was not live-tested** either (no key in the
  sandbox). The Gemini path is verified by code path + failure fallback
  only; the local generator is the tested default.
- Views are a snapshot: a video published yesterday has had less time to
  gather views than a year-old one. Velocity corrects for that; outlier
  score does not — the report says so next to both numbers.
- The API returns at most the channel's public videos, newest first;
  private, deleted and age-restricted videos are invisible to it.
- Subscriber counts are hidden on some channels — views-per-subscriber
  is then unavailable and the report falls back to the median-based score.
- Keyword "lift" needs at least 2 videos using a word; tiny channels
  (under ~10 videos) give thin, noisy results — the report still runs,
  but says so.

## Project structure

```
open-vidiq/
├── README.md, LICENSE (MIT), .gitignore, .env.example
├── requirements.txt, pyproject.toml
├── app.py                          # Streamlit web app (repo root, deploy-ready)
├── openvidiq/
│   ├── __init__.py
│   ├── __main__.py                 # python -m openvidiq
│   ├── cli.py                      # args, input routing, exit codes 0/1/2
│   ├── youtube_api.py              # YouTube Data API v3 client, quota-aware
│   ├── analysis.py                 # outlier score, velocity, keywords, patterns
│   ├── generate.py                 # local + Gemini title/description/tag generation
│   ├── outputs.py                  # report.md + CSV writers
│   └── sample.py                   # bundled sample dataset loader
├── prompts/                        # editable Gemini prompts (titles, descriptions, tags)
├── sample_data/
│   └── channel.json / videos.json  # fictional "Mystery Lane" channel, 24 videos
└── sample_output/                  # generated sample report + index.html demo page
```

## Contributing

Issues and pull requests are welcome. Please keep the quality promise:
no invented numbers, no hardcoded keys, and every new metric covered by a
test on the sample dataset.

## License

MIT — see [LICENSE](LICENSE).
