"""Price fraction (tick size) rules per BEI Peraturan II-A Kep-00003/BEI/04-2025."""

FRACTION_TABLE = [
    (200, 1),
    (500, 2),
    (2000, 5),
    (5000, 10),
]
FRACTION_ABOVE_MAX = 25


def price_fraction(price: float) -> int:
    """Returns the valid tick size for a given price."""
    for upper_bound, fraction in FRACTION_TABLE:
        if price < upper_bound:
            return fraction
    return FRACTION_ABOVE_MAX


def round_to_fraction(price: float) -> float:
    """Rounds a price down to the nearest valid tick for its own price band."""
    fraction = price_fraction(price)
    return (price // fraction) * fraction
