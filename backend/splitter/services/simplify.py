import heapq


def simplify_debts(net):
    """Greedy debt simplification with two heaps.

    net: {user_id: net_paise}; positive = should receive, negative = owes.
    Returns [(from_user, to_user, amount)] with at most n-1 payments.
    Time O(n log n). (Finding the true minimum is NP-hard - subset-sum style -
    so this is the standard practical approximation.)
    """
    creditors = [(-amt, u) for u, amt in net.items() if amt > 0]  # max-heap via negation
    debtors = [(amt, u) for u, amt in net.items() if amt < 0]     # most negative first
    heapq.heapify(creditors)
    heapq.heapify(debtors)
    payments = []
    while creditors and debtors:
        neg_credit, c = heapq.heappop(creditors)
        neg_debt, d = heapq.heappop(debtors)
        credit, debt = -neg_credit, -neg_debt
        amount = min(credit, debt)
        payments.append((d, c, amount))
        if credit > amount:
            heapq.heappush(creditors, (-(credit - amount), c))
        if debt > amount:
            heapq.heappush(debtors, (-(debt - amount), d))
    return payments
