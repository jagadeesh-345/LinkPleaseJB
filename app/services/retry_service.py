from datetime import datetime, timedelta, timezone
import random


def calculate_next_attempt(attempt_count: int, base_delay: float = 1.0, max_delay: float = 60.0) -> datetime:
    """
    Calculates exponential backoff timestamp with random jitter.
    Delay = min(max_delay, base_delay * 2^(attempt_count - 1)) + random_jitter
    """
    exponential = base_delay * (2 ** max(0, attempt_count - 1))
    jitter = random.uniform(0.1, 1.0)
    total_delay = min(max_delay, exponential) + jitter
    return datetime.now(timezone.utc) + timedelta(seconds=total_delay)
