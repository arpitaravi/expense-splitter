import random

import pytest

from splitter.services.splits import SplitError, compute_splits, distribute


def P(*pairs):
    return [{"user": u, "value": v} for u, v in pairs]


def test_equal_remainder_is_deterministic():
    assert compute_splits("equal", 1000, P((1, None), (2, None), (3, None))) == {1: 334, 2: 333, 3: 333}


def test_exact_must_sum_to_total():
    assert compute_splits("exact", 1000, P((1, 600), (2, 400))) == {1: 600, 2: 400}
    with pytest.raises(SplitError):
        compute_splits("exact", 1000, P((1, 600), (2, 300)))


def test_percent_must_total_100():
    assert compute_splits("percent", 1001, P((1, 50), (2, 30), (3, 20))) == {1: 501, 2: 300, 3: 200}
    with pytest.raises(SplitError):
        compute_splits("percent", 1000, P((1, 50), (2, 30)))


def test_shares_weights():
    assert compute_splits("shares", 900, P((1, 2), (2, 1))) == {1: 600, 2: 300}


def test_duplicate_and_bad_input():
    with pytest.raises(SplitError):
        compute_splits("equal", 100, P((1, None), (1, None)))
    with pytest.raises(SplitError):
        compute_splits("shares", 100, P((1, 1.5), (2, 1)))


def test_distribute_always_sums_to_total():
    rnd = random.Random(7)
    for _ in range(500):
        total = rnd.randint(1, 10**7)
        weights = {u: rnd.randint(0, 20) for u in range(rnd.randint(1, 9))}
        if sum(weights.values()) == 0:
            continue
        assert sum(distribute(total, weights).values()) == total
