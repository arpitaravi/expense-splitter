import random
from collections import defaultdict

from splitter.services.simplify import simplify_debts


def test_example():
    net = {1: 500, 2: -300, 3: -200}
    assert sorted(simplify_debts(net)) == [(2, 1, 300), (3, 1, 200)]


def test_random_groups_settle_to_zero_in_at_most_n_minus_1():
    rnd = random.Random(42)
    for _ in range(300):
        n = rnd.randint(2, 12)
        vals = [rnd.randint(-10_000, 10_000) for _ in range(n - 1)]
        vals.append(-sum(vals))  # invariant: balances sum to zero
        net = dict(enumerate(vals))
        pays = simplify_debts(net)
        assert len(pays) <= n - 1
        after = defaultdict(int, net)
        for f, t, a in pays:
            assert a > 0
            after[f] += a
            after[t] -= a
        assert all(v == 0 for v in after.values())
