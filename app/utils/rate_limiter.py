import asyncio
import time
from typing import List


class AsyncRateLimiter:
    """
    Sliding window async rate limiter.
    Ensures no more than `max_requests` are dispatched in any `window_seconds` rolling interval.
    Also supports dynamic backoff delays (e.g. from 429 Retry-After headers).
    """

    def __init__(self, max_requests: int = 10, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.timestamps: List[float] = []
        self._lock = asyncio.Lock()
        self.cooldown_until: float = 0.0

    async def acquire(self):
        """
        Wait if necessary until a request token is available under rate limit constraints.
        """
        async with self._lock:
            while True:
                now = time.monotonic()
                # Check explicit 429 cooldown
                if self.cooldown_until > now:
                    wait_time = self.cooldown_until - now
                    await asyncio.sleep(wait_time)
                    continue

                # Remove timestamps outside sliding window
                cutoff = now - self.window_seconds
                self.timestamps = [t for t in self.timestamps if t > cutoff]

                if len(self.timestamps) < self.max_requests:
                    self.timestamps.append(now)
                    return

                # Calculate wait time until oldest request leaves sliding window
                oldest = self.timestamps[0]
                sleep_duration = (oldest + self.window_seconds) - now + 0.05
                if sleep_duration > 0:
                    await asyncio.sleep(sleep_duration)

    async def set_cooldown(self, seconds: float):
        """
        Force a global cooldown pause (e.g. when 429 Retry-After is encountered).
        """
        async with self._lock:
            target = time.monotonic() + seconds
            if target > self.cooldown_until:
                self.cooldown_until = target
