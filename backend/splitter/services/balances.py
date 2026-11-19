from collections import defaultdict

from django.db.models import Sum

from ..models import Expense, ExpenseSplit, Membership, Settlement


def compute_net_balances(group):
    """net[u] = paid for the group - own share owed, adjusted by ACCEPTED settlements.

    Positive => should receive money. Invariant: sum(net.values()) == 0.
    """
    net = defaultdict(int)
    for uid in Membership.objects.filter(group=group).values_list("user_id", flat=True):
        net[uid] = 0

    paid = (Expense.objects.filter(group=group, is_deleted=False)
            .values("payer").annotate(t=Sum("amount_paise")))
    for row in paid:
        net[row["payer"]] += row["t"]

    owed = (ExpenseSplit.objects.filter(expense__group=group, expense__is_deleted=False)
            .values("user").annotate(t=Sum("share_paise")))
    for row in owed:
        net[row["user"]] -= row["t"]

    for s in Settlement.objects.filter(group=group, status=Settlement.Status.ACCEPTED):
        net[s.from_user_id] += s.amount_paise  # they paid, so they owe less
        net[s.to_user_id] -= s.amount_paise    # they received, so they are owed less

    members = set(Membership.objects.filter(group=group).values_list("user_id", flat=True))
    # people who left (balance already 0) shouldn't clutter the list
    return {u: v for u, v in net.items() if u in members or v != 0}
