import random

BACKOFF_SCHEDULE = [1, 5, 30]  # secondes indexées par attempts (0=1er échec, 1=2e, 2=3e)


def compute_next_retry_delay(attempts: int, jitter_factor: float = 0.2) -> float:
    """
    Délai avant le prochain retry en secondes.
    attempts: nombre de tentatives déjà effectuées (0, 1, 2)
    jitter_factor: variation aléatoire ±N% (défaut ±20%)
    """
    idx = min(attempts, len(BACKOFF_SCHEDULE) - 1)
    base_delay = BACKOFF_SCHEDULE[idx]
    jitter = base_delay * jitter_factor
    return base_delay + random.uniform(-jitter, jitter)
