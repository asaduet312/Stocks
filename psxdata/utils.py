"""Shared utilities for psxdata."""
from __future__ import annotations

import threading
import time as _time
from typing import Any, Callable

from psxdata.constants import MAX_REQUESTS_PER_SECOND


class RateLimiter:
    """Thread-safe fixed-interval rate limiter (leaky-bucket style)."""

    def __init__(
        self,
        max_per_second: int = MAX_REQUESTS_PER_SECOND,
        time_func: Callable[[], float] = _time.monotonic,
        sleep_func: Callable[[float], None] = _time.sleep,
    ) -> None:
        if max_per_second <= 0:
            raise ValueError(f"max_per_second must be > 0, got {max_per_second}")
        self._interval = 1.0 / max_per_second
        self._time = time_func
        self._sleep = sleep_func
        self._lock = threading.Lock()
        self._last_request: float | None = None

    def __enter__(self) -> "RateLimiter":
        with self._lock:
            if self._last_request is not None:
                elapsed = self._time() - self._last_request
                deficit = self._interval - elapsed
                if deficit > 0:
                    self._sleep(deficit)
            self._last_request = self._time()
        return self

    def __exit__(self, *args: Any) -> None:
        pass
