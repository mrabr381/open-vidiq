"""YouTube Data API v3 client.

Free tier: $0, 10,000 quota units/day (a channels.list / playlistItems.list /
videos.list call costs 1 unit each; search costs 100 units, so channel
resolution prefers the cheap forHandle lookup and only falls back to
search when it has to).

Nothing here invents data: every video dict comes straight from the API
response. A missing/invalid key or an empty result is an error, never a
fabricated dataset.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests

from . import OpenVidIQError

API_BASE = "https://www.googleapis.com/youtube/v3"
REQUEST_TIMEOUT = 30


def _get(endpoint: str, api_key: str, **params) -> dict:
    params["key"] = api_key
    try:
        resp = requests.get(f"{API_BASE}/{endpoint}", params=params, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:  # network down, DNS, proxy …
        raise OpenVidIQError(
            f"Could not reach the YouTube API ({exc}). Check your connection and try again."
        ) from exc
    if resp.status_code == 400:
        raise OpenVidIQError(
            "YouTube API rejected the request (400). Your API key may be invalid "
            "or the channel could not be found. Check YOUTUBE_API_KEY and the channel."
        )
    if resp.status_code == 403:
        detail = ""
        try:
            detail = resp.json()["error"]["errors"][0].get("reason", "")
        except Exception:
            pass
        if "quota" in detail.lower():
            raise OpenVidIQError(
                "YouTube API daily quota is exhausted (10,000 units/day on the free "
                "tier). Wait until tomorrow or use another Google Cloud project key."
            )
        raise OpenVidIQError(
            "YouTube API refused the request (403). The key may be invalid, "
            "the YouTube Data API v3 may not be enabled in your Google Cloud "
            "project, or the key is restricted to another API."
        )
    if resp.status_code != 200:
        raise OpenVidIQError(f"YouTube API returned HTTP {resp.status_code}: {resp.text[:200]}")
    return resp.json()


_DURATION_RE = re.compile(
    r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)


def parse_duration_iso8601(value: str) -> int:
    """'PT12M34S' -> 754 seconds. Returns 0 for anything unparseable."""
    match = _DURATION_RE.match(value or "")
    if not match:
        return 0
    parts = {k: int(v) for k, v in match.groupdict().items() if v}
    return parts.get("days", 0) * 86400 + parts.get("hours", 0) * 3600 + parts.get("minutes", 0) * 60 + parts.get("seconds", 0)


def extract_channel_ref(query: str) -> tuple[str, str]:
    """Return (kind, value) for a channel ID, @handle, URL, or plain name.

    kind is one of: 'id', 'handle', 'name'.
    """
    query = (query or "").strip()
    if not query:
        raise OpenVidIQError("No channel given. Pass a channel ID, @handle, URL, or name.")
    # Full URL: youtube.com/@handle, /channel/UC…, /c/name, /user/name
    if query.startswith("http"):
        path = urlparse(query).path.strip("/")
        if path.startswith("channel/"):
            return "id", path.split("/", 1)[1]
        if path.startswith("@"):
            return "handle", path[1:].split("/")[0]
        if path.startswith(("c/", "user/")):
            return "name", path.split("/", 1)[1]
        if path:
            return "name", path.split("/")[0]
    if query.startswith("UC") and len(query) == 24:
        return "id", query
    if query.startswith("@"):
        return "handle", query[1:]
    return "name", query


def resolve_channel(query: str, api_key: str) -> dict:
    """Resolve any channel reference to a channel dict.

    Returns: channel_id, title, handle, subscribers, video_count,
    description, published_at, thumbnail_url, url.
    """
    kind, value = extract_channel_ref(query)
    if kind == "id":
        data = _get("channels", api_key, part="snippet,statistics", id=value)
    elif kind == "handle":
        data = _get("channels", api_key, part="snippet,statistics", forHandle=value)
    else:
        # Plain name: one search call (100 units) — the only search we make.
        data = _get("search", api_key, part="snippet", q=value, type="channel", maxResults=1)
        items = data.get("items", [])
        if not items:
            raise OpenVidIQError(f'No YouTube channel found matching "{value}".')
        channel_id = items[0]["snippet"]["channelId"]
        data = _get("channels", api_key, part="snippet,statistics", id=channel_id)
    items = data.get("items", [])
    if not items:
        raise OpenVidIQError(f'No YouTube channel found for "{query}".')
    item = items[0]
    snippet, stats = item["snippet"], item.get("statistics", {})
    subs_raw = stats.get("subscriberCount")
    return {
        "channel_id": item["id"],
        "title": snippet.get("title", ""),
        "handle": snippet.get("customUrl", ""),
        "subscribers": int(subs_raw) if subs_raw and subs_raw.isdigit() else None,
        "subscribers_hidden": subs_raw is None,
        "video_count": int(stats.get("videoCount", 0) or 0),
        "description": snippet.get("description", ""),
        "published_at": snippet.get("publishedAt", ""),
        "thumbnail_url": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
        "url": f"https://www.youtube.com/channel/{item['id']}",
    }


def fetch_channel_videos(channel_id: str, api_key: str, max_videos: int = 50) -> list[dict]:
    """Fetch a channel's videos (newest first) via its uploads playlist.

    Each video dict: video_id, title, description, published_at,
    views, likes, comments, duration_seconds, url, thumbnail_url.
    Shorts/lives are included as published — the report flags them by
    duration (<60s) instead of silently dropping them.
    """
    if max_videos < 1:
        raise OpenVidIQError("--max-videos must be at least 1.")
    # Uploads playlist id = 'UU' + channel id without the 'UC' prefix.
    playlist_id = "UU" + channel_id[2:] if channel_id.startswith("UC") else None
    if playlist_id is None:
        raise OpenVidIQError(f"Cannot derive the uploads playlist for channel id {channel_id!r}.")
    video_ids: list[str] = []
    page_token = ""
    while len(video_ids) < max_videos:
        params = {
            "part": "contentDetails",
            "playlistId": playlist_id,
            "maxResults": min(50, max_videos - len(video_ids)),
        }
        if page_token:
            params["pageToken"] = page_token
        data = _get("playlistItems", api_key, **params)
        for item in data.get("items", []):
            video_ids.append(item["contentDetails"]["videoId"])
        page_token = data.get("nextPageToken", "")
        if not page_token:
            break
    if not video_ids:
        raise OpenVidIQError("This channel has no public videos to analyse.")
    videos: list[dict] = []
    for start in range(0, len(video_ids), 50):
        chunk = video_ids[start:start + 50]
        data = _get(
            "videos", api_key,
            part="snippet,statistics,contentDetails",
            id=",".join(chunk),
        )
        for item in data.get("items", []):
            snippet, stats = item["snippet"], item.get("statistics", {})
            videos.append({
                "video_id": item["id"],
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "published_at": snippet.get("publishedAt", ""),
                "views": int(stats.get("viewCount", 0) or 0),
                "likes": int(stats.get("likeCount", 0) or 0),
                "comments": int(stats.get("commentCount", 0) or 0),
                "duration_seconds": parse_duration_iso8601(
                    item.get("contentDetails", {}).get("duration", "")
                ),
                "url": f"https://www.youtube.com/watch?v={item['id']}",
                "thumbnail_url": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
            })
    # Keep API order (newest first) — analysis sorts as needed.
    videos.sort(key=lambda v: v["published_at"], reverse=True)
    return videos


def days_since(published_at: str, now: datetime | None = None) -> int:
    """Whole days between a video's publish date and now (minimum 1)."""
    try:
        published = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except ValueError:
        return 1
    now = now or datetime.now(timezone.utc)
    return max(1, (now - published).days)
