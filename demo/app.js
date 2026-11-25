// Open-vidIQ demo data + maths.
//
// REAL sample data, copied from the repo's own snapshot:
//   sample_data/videos.json  (Kurzgesagt – In a Nutshell, @kurzgesagt)
//   20 most recent public uploads, exact view counts as of 19 Nov 2026.
//   See sample_data/SAMPLE_SOURCE.md for where every number came from.
//
// Everything on this page (median, outlier scores, velocity) is computed
// LIVE in this file from the array below — nothing is hardcoded except
// the raw views/dates. The Python pipeline (openvidiq/analysis.py) uses
// the same formulae, so the numbers here must match sample_output/:
//   median 2,333,635 views, 7 outliers (>= 2.0x), top outlier 10.36x.

"use strict";

// Snapshot date: view counts are as of 19 Nov 2026, publish times 12:00 UTC
// (see SAMPLE_SOURCE.md). Velocity is views / whole days from publish to
// this date — the same reference the Python report uses — so the numbers
// stay stable and match sample_output/outliers.csv.
const SNAPSHOT = new Date("2026-11-19T12:00:00Z");
const OUTLIER_THRESHOLD = 2.0;
const NOTABLE_THRESHOLD = 1.5;

// video_id, title, published date, exact views, length in seconds.
// Short = under 90 seconds in this sample (13 Shorts, 7 long-form).
const VIDEOS = [
  { id: "NKeZ_HRk_O8", title: "Cool Down Your Room... With a FRIDGE?", published: "2026-11-14", views: 374365, duration: 73 },
  { id: "Y1vEGsnNYek", title: "What Is Food Fortification?", published: "2026-11-12", views: 493409, duration: 79 },
  { id: "fEjvSbI_PT4", title: "Dying Is Complicated", published: "2026-11-10", views: 5197669, duration: 840 },
  { id: "KBfIo9sZbC4", title: "How Does Ketamine Work?", published: "2026-10-29", views: 968282, duration: 72 },
  { id: "5_Fayfx2NUM", title: "How I Survived Late-Stage Cancer (A Fun Story)", published: "2026-10-27", views: 8822700, duration: 894 },
  { id: "35No369rmq0", title: "What If We Cool Down the Sun?", published: "2026-10-24", views: 1045429, duration: 79 },
  { id: "PXbVn-f_wuM", title: "You Will Only Like Half of This Video", published: "2026-10-20", views: 5851757, duration: 214 },
  { id: "_y9JuojAIg0", title: "We Finally Know More About Humanity’s First Civilization", published: "2026-10-08", views: 12457919, duration: 1051 },
  { id: "ujkD4SxPKOI", title: "AI Just Crossed the Terrifying Line - Now What?", published: "2026-10-05", views: 24185772, duration: 1304 },
  { id: "b1EMX3wyqCY", title: "Your Brain on Magic Mushrooms", published: "2026-09-28", views: 1409223, duration: 71 },
  { id: "oNTaHYXQ4MM", title: "Humans Can Regrow an Organ", published: "2026-09-26", views: 1608080, duration: 74 },
  { id: "RQprZZJIb6Y", title: "Your Skeleton Is Electric", published: "2026-09-24", views: 558289, duration: 72 },
  { id: "QW_jlUn4gA8", title: "This Is What a Godlike Civilization Would Look Like", published: "2026-09-22", views: 9668580, duration: 852 },
  { id: "0NY2gAftzJE", title: "This Woman Cured Her Cancer with an Insane Method", published: "2026-09-15", views: 21462659, duration: 914 },
  { id: "NIifnIP_NnQ", title: "How ADHD Medication Works", published: "2026-09-05", views: 1018999, duration: 71 },
  { id: "hiIIGMeMEuE", title: "What If You Never Slept?", published: "2026-09-03", views: 3059191, duration: 71 },
  { id: "tZ8i1RxGSYM", title: "Can Earth Run Out of Water?", published: "2026-08-31", views: 4174806, duration: 79 },
  { id: "EqkRVbaBxtg", title: "What If Gravity Was 10% Stronger?", published: "2026-08-29", views: 1489965, duration: 70 },
  { id: "YqAI0oqtt7w", title: "Dust Is Not What You Think", published: "2026-08-27", views: 3078276, duration: 71 },
  { id: "OKsWuqNjomQ", title: "Why Ebola Keeps Coming Back", published: "2026-08-24", views: 998575, duration: 72 },
];

// ---- maths (same formulae as openvidiq/analysis.py) -----------------------

function median(values) {
  const s = [...values].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

// Whole days between publish (12:00 UTC) and the snapshot, minimum 1.
function daysOld(published) {
  const pub = new Date(published + "T12:00:00Z");
  return Math.max(1, Math.floor((SNAPSHOT - pub) / 86400000));
}

const MEDIAN = median(VIDEOS.map((v) => v.views));

const ENRICHED = VIDEOS.map((v) => {
  const days = daysOld(v.published);
  return {
    ...v,
    days,
    score: v.views / MEDIAN, // outlier score: views / channel median
    velocity: v.views / days, // views per day since publish
    isOutlier: v.views / MEDIAN >= OUTLIER_THRESHOLD,
    isShort: v.duration < 90,
    url: "https://www.youtube.com/watch?v=" + v.id,
  };
}).sort((a, b) => b.views - a.views);

ENRICHED.forEach((v, i) => { v.rank = i + 1; });

const OUTLIERS = ENRICHED.filter((v) => v.isOutlier);
const TOP = ENRICHED[0];

// ---- formatting -----------------------------------------------------------

const fmtInt = (n) => Math.round(n).toLocaleString("en-US");
const fmtViews = (n) => fmtInt(n);
const fmtScore = (n) => n.toFixed(2) + "×";
const fmtVelocity = (n) => fmtInt(Math.round(n * 10) / 10) + "/day";
const fmtDuration = (s) => {
  const m = Math.floor(s / 60);
  return m + ":" + String(s % 60).padStart(2, "0");
};

// ---- state ----------------------------------------------------------------

let selectedId = TOP.id;
let sortKey = "views";
let sortDir = -1; // -1 = descending, 1 = ascending

const $ = (id) => document.getElementById(id);
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

// ---- render: stat cards ----------------------------------------------------

function renderStats() {
  $("stat-videos").textContent = ENRICHED.length;
  // README quotes the median truncated to a whole number (2,333,635);
  // the exact median is 2,333,635.5 and that is what scores are computed from.
  $("stat-median").textContent = fmtViews(Math.floor(MEDIAN));
  $("stat-outliers").textContent = OUTLIERS.length;
  $("stat-top").textContent = fmtScore(TOP.score);
  $("verify-line").textContent =
    "Computed live in your browser from the 20 videos below: median " +
    fmtViews(MEDIAN) + " views, " + OUTLIERS.length + " outliers (≥ 2.00×), " +
    "top outlier " + fmtScore(TOP.score) + " — the same numbers as the " +
    "Python report (sample_output/outliers.csv).";
}

// ---- render: bar chart ------------------------------------------------------

function renderChart() {
  const chart = $("chart");
  chart.innerHTML = "";
  const maxViews = TOP.views;
  const medianPct = (MEDIAN / maxViews) * 100;

  const medianLine = document.createElement("div");
  medianLine.className = "median-line";
  medianLine.style.bottom = "calc(" + medianPct.toFixed(2) + "% + 28px)";
  medianLine.title = "Channel median: " + fmtViews(MEDIAN) + " views";
  const medianLabel = document.createElement("span");
  medianLabel.className = "median-label";
  medianLabel.textContent = "median " + fmtViews(Math.floor(MEDIAN));
  medianLine.appendChild(medianLabel);
  chart.appendChild(medianLine);

  for (const v of ENRICHED) {
    const bar = document.createElement("button");
    bar.type = "button";
    bar.className = "bar" + (v.isOutlier ? " outlier" : "") + (v.id === selectedId ? " selected" : "");
    bar.style.height = Math.max(2, (v.views / maxViews) * 100).toFixed(2) + "%";
    bar.title = v.title + " — " + fmtViews(v.views) + " views (" + fmtScore(v.score) + " the median)";
    bar.setAttribute("aria-label", v.title + ", " + fmtViews(v.views) + " views, " + fmtScore(v.score) + " the median");
    bar.setAttribute("aria-pressed", v.id === selectedId ? "true" : "false");
    bar.dataset.id = v.id;
    bar.innerHTML = "<span class='bar-value'>" + fmtViews(v.views) + "</span>" +
      "<span class='bar-rank'>#" + v.rank + "</span>";
    bar.addEventListener("click", () => selectVideo(v.id));
    chart.appendChild(bar);
  }
}

// ---- render: detail panel ---------------------------------------------------

function renderDetail() {
  const v = ENRICHED.find((x) => x.id === selectedId) || TOP;
  const diff = v.views - MEDIAN;
  const pct = ((diff / MEDIAN) * 100).toFixed(0);
  $("detail-title").textContent = v.title;
  $("detail-link").href = v.url;
  $("detail-meta").textContent =
    "Published " + v.published + " · " + v.days + " days old at snapshot · " +
    fmtDuration(v.duration) + " (" + (v.isShort ? "Short" : "long-form") + ") · rank #" + v.rank + " of 20 by views";
  $("detail-views").textContent = fmtViews(v.views);
  $("detail-score").textContent = fmtScore(v.score);
  $("detail-vs").textContent =
    (diff >= 0 ? "+" : "−") + fmtViews(Math.abs(diff)) + " vs median (" +
    (diff >= 0 ? "+" : "") + pct + "%) — " +
    (v.isOutlier ? "outlier: beat the median by 2× or more."
      : v.score >= NOTABLE_THRESHOLD ? "notable: 1.5–2× the median, just under outlier level."
      : "below the outlier line (under 2× the median).");
  $("detail-velocity").textContent = fmtVelocity(v.velocity);
  $("detail-velocity-note").textContent =
    fmtViews(v.views) + " views ÷ " + v.days + " days since publish (to 19 Nov 2026). " +
    "Velocity lets a 9-day-old hit be fairly compared with a 2-month-old one.";
  // Velocity bar: this video vs the fastest video.
  const maxVel = Math.max(...ENRICHED.map((x) => x.velocity));
  $("detail-velocity-bar").style.width = ((v.velocity / maxVel) * 100).toFixed(1) + "%";
  $("detail-velocity-rank").textContent =
    "Fastest velocity in the sample: " + fmtVelocity(maxVel) + " (" +
    ENRICHED.slice().sort((a, b) => b.velocity - a.velocity)[0].title + "). " +
    "This video ranks #" + (ENRICHED.slice().sort((a, b) => b.velocity - a.velocity).findIndex((x) => x.id === v.id) + 1) +
    " of 20 by velocity.";
}

function selectVideo(id) {
  selectedId = id;
  renderChart();
  renderDetail();
  renderTable();
}

// ---- render: outlier list ---------------------------------------------------

function renderOutliers() {
  const list = $("outlier-list");
  list.innerHTML = "";
  for (const v of OUTLIERS) {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "outlier-item" + (v.id === selectedId ? " selected" : "");
    btn.innerHTML = "<span class='outlier-mult'>" + fmtScore(v.score) + "</span> " +
      "<span class='outlier-title'>" + esc(v.title) + "</span>" +
      "<span class='outlier-views'>" + fmtViews(v.views) + " views · " + v.published + "</span>";
    btn.addEventListener("click", () => selectVideo(v.id));
    li.appendChild(btn);
    list.appendChild(li);
  }
}

// ---- render: sortable table -------------------------------------------------

const COLUMNS = [
  { key: "rank", label: "#", numeric: true },
  { key: "title", label: "Title", numeric: false },
  { key: "published", label: "Published", numeric: false },
  { key: "views", label: "Views", numeric: true },
  { key: "score", label: "× median", numeric: true },
  { key: "velocity", label: "Views / day", numeric: true },
  { key: "days", label: "Days old", numeric: true },
  { key: "duration", label: "Length", numeric: true },
];

function sortedRows() {
  const rows = [...ENRICHED];
  rows.sort((a, b) => {
    const av = a[sortKey], bv = b[sortKey];
    const cmp = typeof av === "string" ? av.localeCompare(bv) : av - bv;
    return cmp * sortDir;
  });
  return rows;
}

function renderTable() {
  const thead = document.querySelector("#video-table thead tr");
  thead.innerHTML = "";
  for (const col of COLUMNS) {
    const th = document.createElement("th");
    th.scope = "col";
    th.className = col.numeric ? "num" : "";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "sort-btn";
    btn.textContent = col.label + (sortKey === col.key ? (sortDir === -1 ? " ↓" : " ↑") : "");
    btn.setAttribute("aria-sort", sortKey === col.key ? (sortDir === -1 ? "descending" : "ascending") : "none");
    btn.addEventListener("click", () => {
      if (sortKey === col.key) sortDir = -sortDir;
      else { sortKey = col.key; sortDir = col.numeric ? -1 : 1; }
      renderTable();
    });
    th.appendChild(btn);
    thead.appendChild(th);
  }

  const tbody = document.querySelector("#video-table tbody");
  tbody.innerHTML = "";
  for (const v of sortedRows()) {
    const tr = document.createElement("tr");
    if (v.isOutlier) tr.className = "outlier-row";
    if (v.id === selectedId) tr.classList.add("selected-row");
    tr.innerHTML =
      "<td class='num'>" + v.rank + "</td>" +
      "<td><a href='" + v.url + "' target='_blank' rel='noopener'>" + esc(v.title) + "</a>" +
      (v.isOutlier ? " <span class='badge'>outlier</span>" : "") +
      (v.isShort ? " <span class='badge short'>Short</span>" : "") + "</td>" +
      "<td>" + v.published + "</td>" +
      "<td class='num'>" + fmtViews(v.views) + "</td>" +
      "<td class='num'><strong>" + fmtScore(v.score) + "</strong></td>" +
      "<td class='num'>" + fmtVelocity(v.velocity) + "</td>" +
      "<td class='num'>" + v.days + "</td>" +
      "<td class='num'>" + fmtDuration(v.duration) + "</td>";
    tr.addEventListener("click", (e) => {
      if (e.target.tagName !== "A") selectVideo(v.id);
    });
    tbody.appendChild(tr);
  }
}

// ---- go ---------------------------------------------------------------------

renderStats();
renderChart();
renderDetail();
renderOutliers();
renderTable();
