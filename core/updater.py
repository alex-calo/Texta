"""Lightweight update checker — queries GitHub releases for a newer version.

Industry-standard "non-intrusive" update flow:
- Runs once on startup, off the critical path.
- Hits the public GitHub releases API (no auth, no rate limiting concerns at home use).
- Returns an UpdateInfo if a newer version is available; the caller decides UX.
- Never auto-downloads or auto-installs — that requires Sparkle/WinSparkle and
  signed update feeds, which is a v2 concern.
"""
import json
import logging
import urllib.request
from typing import NamedTuple, Optional

logger = logging.getLogger(__name__)


class UpdateInfo(NamedTuple):
    version: str
    url: str
    notes: str


def check_for_update(repo: str, current_version: str, timeout: float = 5.0) -> Optional[UpdateInfo]:
    """Query GitHub releases for a newer version.

    Args:
        repo:            "owner/repo" (e.g. "yourorg/texta")
        current_version: this app's semver (e.g. "1.0.0")
        timeout:         max seconds to wait for the network call

    Returns:
        UpdateInfo if a newer version is available, else None.
    """
    if not repo:
        return None

    api = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        req = urllib.request.Request(api, headers={'Accept': 'application/vnd.github+json'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        logger.debug(f"Update check failed: {e}")
        return None

    latest = (data.get('tag_name') or '').lstrip('v').strip()
    if not latest:
        return None
    if not _semver_gt(latest, current_version):
        return None

    return UpdateInfo(
        version=latest,
        url=data.get('html_url', ''),
        notes=(data.get('body') or '')[:500],
    )


def _semver_gt(a: str, b: str) -> bool:
    """Return True if version `a` is strictly greater than `b` (basic semver)."""
    def parse(v: str):
        parts = []
        for chunk in v.split('.')[:3]:
            num = ''
            for ch in chunk:
                if ch.isdigit():
                    num += ch
                else:
                    break
            parts.append(int(num) if num else 0)
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts)

    try:
        return parse(a) > parse(b)
    except Exception:
        return False
