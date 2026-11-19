"""Open-vidIQ — open-source YouTube outlier / SEO research agent.

Free alternative to vidIQ's paid tiers. Every number in a report is
computed from real YouTube Data API results or from the bundled sample
dataset — nothing is invented.
"""

__version__ = "0.1.0"


class OpenVidIQError(Exception):
    """User-facing error: bad input, missing key, or a failed API call."""
