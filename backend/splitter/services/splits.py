"""Split computation. Pure functions, no DB. All money is integer paise."""
from decimal import Decimal

from ..models import SplitType


class SplitError(ValueError):
    pass


def distribute(total, weights):
    """Split `total` paise proportionally to integer `weights` ({user_id: weight}).

    Largest-remainder style: everyone gets floor(total*w/W); the leftover paise
    go one each to eligible users in ascending user-id order, so the result is
    deterministic and ALWAYS sums exactly to `total`.
    """
    if total <= 0:
        raise SplitError("Amount must be positive.")
    if not weights:
        raise SplitError("At least one participant is required.")
    if any(w < 0 for w in weights.values()):
        raise SplitError("Weights cannot be negative.")
    total_w = sum(weights.values())
    if total_w <= 0:
        raise SplitError("Total weight must be positive.")
    shares = {u: total * w // total_w for u, w in weights.items()}
    leftover = total - sum(shares.values())
    eligible = [u for u in sorted(weights) if weights[u] > 0]
    for u in eligible[:leftover]:
        shares[u] += 1
    assert sum(shares.values()) == total
    return shares


def _to_int(value, what):
    if value is None:
        raise SplitError(f"A {what} is required for every participant.")
    value = Decimal(value)
    if value != value.to_integral_value():
        raise SplitError(f"{what.capitalize()} must be a whole number.")
    return int(value)


def compute_splits(split_type, total, participants):
    """participants: [{"user": id, "value": number|None}] -> {user_id: share_paise}"""
    ids = [p["user"] for p in participants]
    if len(ids) != len(set(ids)):
        raise SplitError("A participant is listed more than once.")
    if not participants:
        raise SplitError("At least one participant is required.")

    if split_type == SplitType.EQUAL:
        return distribute(total, {u: 1 for u in ids})

    if split_type == SplitType.SHARES:
        weights = {p["user"]: _to_int(p.get("value"), "share") for p in participants}
        return distribute(total, weights)

    if split_type == SplitType.PERCENT:
        bps = {}
        for p in participants:
            if p.get("value") is None:
                raise SplitError("A percentage is required for every participant.")
            pct = Decimal(p["value"]) * 100  # basis points, 2 decimals of a percent
            if pct != pct.to_integral_value() or pct < 0:
                raise SplitError("Percentages allow at most 2 decimals and cannot be negative.")
            bps[p["user"]] = int(pct)
        if sum(bps.values()) != 10_000:
            raise SplitError("Percentages must total 100%.")
        return distribute(total, bps)

    if split_type == SplitType.EXACT:
        exact = {p["user"]: _to_int(p.get("value"), "amount") for p in participants}
        if any(v < 0 for v in exact.values()):
            raise SplitError("Amounts cannot be negative.")
        if sum(exact.values()) != total:
            raise SplitError(f"Exact amounts add up to {sum(exact.values())} paise but the total is {total}.")
        return exact

    raise SplitError("Unknown split type.")
