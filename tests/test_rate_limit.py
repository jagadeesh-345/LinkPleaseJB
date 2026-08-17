import time
import pytest
from app.utils.rate_limiter import AsyncRateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_sliding_window():
    # Configure 3 requests per 1 second window
    limiter = AsyncRateLimiter(max_requests=3, window_seconds=1.0)

    start = time.monotonic()
    for _ in range(3):
        await limiter.acquire()
    first_batch_duration = time.monotonic() - start
    assert first_batch_duration < 0.2  # Immediate acquisition for first 3

    # 4th request must pause until window passes
    await limiter.acquire()
    total_duration = time.monotonic() - start
    assert total_duration >= 0.9  # Waited for sliding window slot
