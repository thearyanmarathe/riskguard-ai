"""Small process-local rate limiter for protected API operations."""

from __future__ import annotations

import os
import threading
import time
from collections import OrderedDict, deque


DEFAULT_REQUESTS = 60
DEFAULT_WINDOW_SECONDS = 60
MAX_TRACKED_CLIENTS = 10_000


def _positive_setting(name: str, default: int, maximum: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default
    return value if 1 <= value <= maximum else default


class LocalRateLimiter:
    """Fixed-window limiter with bounded, lazily-cleaned in-memory state."""

    def __init__(self) -> None:
        self._entries: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = threading.Lock()

    @property
    def tracked_clients(self) -> int:
        with self._lock:
            return len(self._entries)

    def reset(self) -> None:
        with self._lock:
            self._entries.clear()

    def check(self, key: str) -> tuple[bool, int]:
        limit = _positive_setting("RISKGUARD_RATE_LIMIT_REQUESTS", DEFAULT_REQUESTS, 10_000)
        window = _positive_setting("RISKGUARD_RATE_LIMIT_WINDOW_SECONDS", DEFAULT_WINDOW_SECONDS, 86_400)
        now = time.monotonic()
        cutoff = now - window
        with self._lock:
            for client_key, timestamps in list(self._entries.items()):
                while timestamps and timestamps[0] <= cutoff:
                    timestamps.popleft()
                if not timestamps:
                    del self._entries[client_key]
            timestamps = self._entries.setdefault(key, deque())
            self._entries.move_to_end(key)
            if len(self._entries) > MAX_TRACKED_CLIENTS:
                self._entries.popitem(last=False)
            if len(timestamps) >= limit:
                retry_after = max(1, int(timestamps[0] + window - now + 0.999))
                return False, retry_after
            timestamps.append(now)
            return True, 0
