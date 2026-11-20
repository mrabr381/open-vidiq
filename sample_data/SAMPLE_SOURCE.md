# Sample dataset — source

`channel.json` + `videos.json` are a snapshot of the real public channel
**Kurzgesagt – In a Nutshell** (@kurzgesagt), not a fictional channel.

- **What:** the channel's 20 most recent public uploads (7 long-form
  videos + 13 Shorts), with exact view counts.
- **View counts, publish dates, lengths:** vidIQ's public stats page,
  https://vidiq.com/youtube-stats/channel/@kurzgesagt/videos/ — read
  20 November 2026, figures as of 19 November 2026 (25,800,000
  subscribers, 4,020,025,007 total views, 401 videos).
- **Video IDs:** matched by title against the channel's own YouTube
  pages (https://www.youtube.com/@kurzgesagt/videos and /shorts, read
  20 November 2026). YouTube shows rounded view counts there (e.g.
  "24M" for the 24,185,772-view video), and every rounded count agrees
  with the exact vidIQ figure for the same title.
- **Descriptions:** the full public description of each video, fetched
  from its YouTube watch page on 20 November 2026.
- **What was NOT collected:** likes and comments (`null` in
  `videos.json`). They are not needed for outlier, velocity, keyword or
  title-pattern maths, so no values were guessed.
- **Publish times:** vidIQ publishes dates only, so `published_at`
  uses 12:00 UTC on the published date. Day-level maths (velocity,
  days-old) is unaffected.
- **Channel join date:** 9 July 2013 (vidIQ page); time of day unknown,
  stored as midnight UTC.

The previous fictional "Mystery Lane" dataset is kept as the offline
test fixture at `mystery_lane_fixture/` — the test suite asserts the
verified maths on it (median 12,850 views, top outlier 4.86×).
