def normalize_score(value) -> float:
    """Convert a 0-1 or percentage score to a clamped 0-1 value."""
    score = float(value or 0)
    if score > 1:
        score /= 100
    return max(0.0, min(score, 1.0))


def percentage_score(value, digits=0):
    return round(normalize_score(value) * 100, digits)