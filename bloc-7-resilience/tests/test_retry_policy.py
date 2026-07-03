import pytest
from app.services.retry_policy import compute_next_retry_delay, BACKOFF_SCHEDULE


def test_first_retry_delay_in_range():
    # 1er échec → base 1s ±20% → [0.8, 1.2]
    for _ in range(50):
        delay = compute_next_retry_delay(0)
        assert 0.8 <= delay <= 1.2, f"delay={delay} hors [0.8, 1.2]"


def test_second_retry_delay_in_range():
    # 2e échec → base 5s ±20% → [4.0, 6.0]
    for _ in range(50):
        delay = compute_next_retry_delay(1)
        assert 4.0 <= delay <= 6.0, f"delay={delay} hors [4.0, 6.0]"


def test_third_retry_delay_in_range():
    # 3e échec → base 30s ±20% → [24.0, 36.0]
    for _ in range(50):
        delay = compute_next_retry_delay(2)
        assert 24.0 <= delay <= 36.0, f"delay={delay} hors [24.0, 36.0]"


def test_overflow_attempts_clamped_to_last():
    # attempts=99 → clamped sur le dernier schedule (30s)
    for _ in range(20):
        delay = compute_next_retry_delay(99)
        assert 24.0 <= delay <= 36.0


def test_jitter_is_random():
    delays = {compute_next_retry_delay(0) for _ in range(20)}
    # Avec 20 tirages, on devrait avoir au moins 2 valeurs différentes (quasi certain)
    assert len(delays) > 1


def test_custom_jitter_factor():
    # jitter_factor=0 → pas de jitter
    delays = {compute_next_retry_delay(0, jitter_factor=0.0) for _ in range(10)}
    assert len(delays) == 1
    assert list(delays)[0] == BACKOFF_SCHEDULE[0]


def test_backoff_schedule_is_increasing():
    assert BACKOFF_SCHEDULE[0] < BACKOFF_SCHEDULE[1] < BACKOFF_SCHEDULE[2]
