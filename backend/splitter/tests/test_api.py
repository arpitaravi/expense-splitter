import datetime

import pytest

from splitter.models import ActivityLog, Expense
from splitter.services.balances import compute_net_balances
from splitter.tasks import generate_recurring_expenses
from splitter.models import RecurringExpense

pytestmark = pytest.mark.django_db


@pytest.fixture
def trio(make_user, client_for):
    a, b, c = make_user("asha"), make_user("ravi"), make_user("meena")
    ca = client_for(a)
    g = ca.post("/api/groups/", {"name": "Goa trip"}, format="json").json()
    for u in (b, c):
        assert client_for(u).post("/api/groups/join/", {"invite_code": g["invite_code"]}, format="json").status_code == 200
    return g["id"], (a, b, c), (ca, client_for(b), client_for(c))


def expense(gid, client, payer, amount, split="equal", parts=None, version=None, **kw):
    body = {"payer": payer.id, "amount_paise": amount, "description": "Dinner", "date": "2026-11-01",
            "split_type": split, "participants": parts, **kw}
    if version:
        body["version"] = version
    return client.post(f"/api/groups/{gid}/expenses/", body, format="json")


def everyone(users, value=None):
    return [{"user": u.id, "value": value} for u in users]


def test_equal_split_and_balances_sum_to_zero(trio):
    gid, users, (ca, cb, cc) = trio
    a, b, c = users
    r = expense(gid, ca, a, 100_000, parts=everyone(users))
    assert r.status_code == 201, r.content
    shares = sorted(s["share_paise"] for s in r.json()["splits"])
    assert shares == [33333, 33333, 33334]
    bal = ca.get(f"/api/groups/{gid}/balances/").json()
    nets = {x["username"]: x["net_paise"] for x in bal["balances"]}
    assert sum(nets.values()) == 0
    assert nets["asha"] == 66666 and nets["ravi"] < 0 and nets["meena"] < 0
    assert len(bal["suggested_payments"]) == 2


def test_invalid_split_rejected_and_nothing_saved(trio):
    gid, users, (ca, *_r) = trio
    r = expense(gid, ca, users[0], 1000, "exact", [{"user": users[0].id, "value": 300}, {"user": users[1].id, "value": 300}])
    assert r.status_code == 400
    assert Expense.objects.count() == 0


def test_non_member_cannot_read_or_write(trio, make_user, client_for):
    gid, users, _ = trio
    outsider = client_for(make_user("eve"))
    assert outsider.get(f"/api/groups/{gid}/expenses/").status_code == 404
    assert outsider.get(f"/api/groups/{gid}/balances/").status_code == 404
    assert expense(gid, outsider, users[0], 1000, parts=everyone(users)).status_code == 404


def test_payer_must_be_member(trio, make_user):
    gid, users, (ca, *_r) = trio
    eve = make_user("eve")
    assert expense(gid, ca, eve, 1000, parts=everyone(users)).status_code == 400


def test_settlement_needs_receiver_confirmation(trio):
    gid, users, (ca, cb, cc) = trio
    a, b, c = users
    expense(gid, ca, a, 90_000, parts=everyone(users))  # ravi & meena owe 30000 each
    s = cb.post(f"/api/groups/{gid}/settlements/", {"to_user": a.id, "amount_paise": 30_000}, format="json")
    assert s.status_code == 201
    sid = s.json()["id"]
    assert compute_net_balances(__import__("splitter.models", fromlist=["Group"]).Group.objects.get(pk=gid))[b.id] == -30_000  # pending: no effect
    assert cb.post(f"/api/groups/{gid}/settlements/{sid}/respond/", {"action": "accept"}, format="json").status_code == 403  # payer can't self-confirm
    assert ca.post(f"/api/groups/{gid}/settlements/{sid}/respond/", {"action": "accept"}, format="json").status_code == 200
    net = {x["username"]: x["net_paise"] for x in ca.get(f"/api/groups/{gid}/balances/").json()["balances"]}
    assert net["ravi"] == 0 and net["asha"] == 30_000 and sum(net.values()) == 0
    assert ca.post(f"/api/groups/{gid}/settlements/{sid}/respond/", {"action": "reject"}, format="json").status_code == 409


def test_edit_with_stale_version_conflicts_and_delete_is_soft(trio):
    gid, users, (ca, cb, _c) = trio
    a = users[0]
    e = expense(gid, ca, a, 30_000, parts=everyone(users)).json()
    body = {"payer": a.id, "amount_paise": 60_000, "description": "Bigger dinner", "date": "2026-11-01",
            "split_type": "equal", "participants": everyone(users), "version": e["version"]}
    assert cb.put(f"/api/groups/{gid}/expenses/{e['id']}/", body, format="json").status_code == 200
    assert ca.put(f"/api/groups/{gid}/expenses/{e['id']}/", body, format="json").status_code == 409  # stale
    assert ca.delete(f"/api/groups/{gid}/expenses/{e['id']}/").status_code == 204
    assert Expense.objects.get(pk=e["id"]).is_deleted is True
    assert ca.get(f"/api/groups/{gid}/expenses/").json()["count"] == 0
    assert all(x["net_paise"] == 0 for x in ca.get(f"/api/groups/{gid}/balances/").json()["balances"])
    actions = list(ActivityLog.objects.filter(entity_type="expense").values_list("action", flat=True))
    assert {"expense.created", "expense.updated", "expense.deleted"} <= set(actions)


def test_insights(trio):
    gid, users, (ca, *_r) = trio
    expense(gid, ca, users[0], 30_000, parts=everyone(users), category="food")
    expense(gid, ca, users[1], 10_000, parts=everyone(users), category="travel")
    d = ca.get(f"/api/groups/{gid}/insights/").json()
    assert d["by_category"][0] == {"category": "food", "total_paise": 30_000}
    assert d["by_month"] == [{"month": "2026-11", "total_paise": 40_000}]


def test_recurring_expense_task(trio):
    gid, users, _ = trio
    from splitter.models import Group
    RecurringExpense.objects.create(group_id=gid, payer=users[0], amount_paise=900_000, description="Rent",
                                    participants=everyone(users), day_of_month=1)
    day = datetime.date(2026, 12, 1)
    assert generate_recurring_expenses(day) == 1
    assert generate_recurring_expenses(day) == 0  # idempotent for the same day
    assert Expense.objects.filter(description="Rent").count() == 1


def test_health_and_seed_demo(client_for):
    from django.core.management import call_command
    from rest_framework.test import APIClient
    assert APIClient().get("/api/health/").json() == {"status": "ok"}
    call_command("seed_demo")
    call_command("seed_demo")  # idempotent
    from splitter.models import Group
    g = Group.objects.get(name__startswith="Goa")
    net = compute_net_balances(g)
    assert sum(net.values()) == 0 and g.expenses.count() == 4
