import threading
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class FixedWindowConfig:
    window_seconds: int = 60
    max_requests: int = 1000


class FixedWindowRateLimiter:
    """Thread-safe fixed-window limiter.

    Aligns windows to epoch boundaries: floor(now / window_seconds) * window_seconds.
    """

    def __init__(self, *, config: FixedWindowConfig) -> None:
        self._config = config
        self._lock = threading.Lock()
        self._window_start = self._current_window_start()
        self._count = 0

    def _current_window_start(self) -> int:
        now = int(time.time())
        return (now // self._config.window_seconds) * self._config.window_seconds

    def acquire(self) -> float:
        """Attempt to take a permit. Returns 0 if allowed, else seconds to wait until next window."""
        with self._lock:
            now_window = self._current_window_start()
            if now_window != self._window_start:
                self._window_start = now_window
                self._count = 0

            if self._count < self._config.max_requests:
                self._count += 1
                return 0.0

            # Compute time remaining to next window
            now = int(time.time())
            next_window = self._window_start + self._config.window_seconds
            wait = max(0, next_window - now)
            return float(wait)
