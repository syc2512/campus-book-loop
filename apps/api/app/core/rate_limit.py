"""Process-local failed-login limiter.

This is deliberately small: it slows down password guessing for one account
from one client without adding Redis. It is not a distributed rate limit and
must be replaced by a shared limiter when the API runs multiple replicas.
"""

from __future__ import annotations

import threading
import time


class LoginRateLimiter:
    def __init__(self, max_failures: int = 5, window_seconds: int = 300) -> None:
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            failures, window_started = self._failures.get(key, (0, now))
            if now - window_started >= self.window_seconds:
                self._failures.pop(key, None)
                return True
            return failures < self.max_failures

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            failures, window_started = self._failures.get(key, (0, now))
            if now - window_started >= self.window_seconds:
                failures, window_started = 0, now
            self._failures[key] = (failures + 1, window_started)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()


login_rate_limiter = LoginRateLimiter()
