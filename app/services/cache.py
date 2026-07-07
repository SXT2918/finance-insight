"""Small in-process TTL cache for external calls (tape quotes, intraday chart).

On a fetch failure, returns the last good value marked stale rather than
raising, so pages still render with a stale-data notice instead of a 500.
"""

import time


class TTLCache:
    def __init__(self):
        self._store = {}

    def get_or_fetch(self, key, ttl_seconds, fetch_fn):
        now = time.time()
        entry = self._store.get(key)
        if entry and now - entry["ts"] < ttl_seconds:
            return entry["value"], False

        try:
            value = fetch_fn()
            self._store[key] = {"ts": now, "value": value}
            return value, False
        except Exception:
            if entry:
                return entry["value"], True
            raise


cache = TTLCache()
