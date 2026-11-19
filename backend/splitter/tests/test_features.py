import datetime
import re
from unittest import mock

import pytest
from django.core import mail
from rest_framework.test import APIClient

from splitter.models import Expense, Group, Membership, RecurringExpense
from splitter.tasks import generate_recurring_expenses

pytestmark = pytest.mark.django_db


@pytest.fixture
def trio(make_user, client_for):
    a, b, c = make_user("asha"), make_user("ravi"), make_user("meena")
    ca = client_for(a)
    g = ca.post("/api/groups/", {"name": "Trip"}, format="json").json()
    for u in (b, c):
        client_for(u).post("/api/groups/join/", {"invite_code": g["invite_code"]}, format="json")
    return g["id"], (a, b, c), (ca, client_for(b), client_for(c))


def parts(users):
    return [{"user": u.id, "value": None} for u in users]


def add_expense(gid, client, payer, amount, users):
    return client.post(f"/api/groups/{gid}/expenses/", {
        "payer": payer.id, "amount_paise": amount, "description": "x", "date": "2026-11-01",
        "split_type": "equal", "participants": parts(users)}, format="json")


# ---- leave / remove ----
def test_cannot_leave_with_balance_then_can_after_settling(trio):
    gid, users, (ca, cb, cc) = trio
    a, b, c = users
    add_expense(gid, ca, a, 90_000, users)
    r = cb.post(f"/api/groups/{gid}/leave/")
    assert r.status_code == 409 and "Settle up" in r.json()["detail"]
    sid = cb.post(f"/api/groups/{gid}/settlements/", {"to_user": a.id, "amount_paise": 30_000}, format="json").json()["id"]
    assert cb.post(f"/api/groups/{gid}/leave/").status_code == 409  # pending payment
    ca.post(f"/api/groups/{gid}/settlements/{sid}/respond/", {"action": "accept"}, format="json")
    assert cb.post(f"/api/groups/{gid}/leave/").status_code == 204
    assert not Membership.objects.filter(group_id=gid, user=b).exists()
    assert cb.get(f"/api/groups/{gid}/").status_code == 404  # no longer a member
    names = [x["username"] for x in ca.get(f"/api/groups/{gid}/balances/").json()["balances"]]
    assert "ravi" not in names
    assert sum(x["net_paise"] for x in ca.get(f"/api/groups/{gid}/balances/").json()["balances"]) == 0


def test_only_creator_removes_members(trio):
    gid, users, (ca, cb, cc) = trio
    a, b, c = users
    assert cb.delete(f"/api/groups/{gid}/members/{c.id}/").status_code == 403
    assert ca.delete(f"/api/groups/{gid}/members/{a.id}/").status_code == 400
    assert ca.delete(f"/api/groups/{gid}/members/{c.id}/").status_code == 204
    assert Group.objects.get(pk=gid).memberships.count() == 2


# ---- invites ----
def test_invite_emails(trio):
    gid, users, (ca, cb, cc) = trio
    r = ca.post(f"/api/groups/{gid}/invite/", {"emails": "friend@example.com, bad-email"}, format="json")
    assert r.status_code == 200 and r.json() == {"sent": 1, "invalid": ["bad-email"]}
    assert len(mail.outbox) == 1 and "/join/" in mail.outbox[0].body and mail.outbox[0].to == ["friend@example.com"]
    outsider = APIClient()
    assert outsider.post(f"/api/groups/{gid}/invite/", {"emails": "a@b.com"}, format="json").status_code == 401


# ---- password reset + profile ----
def test_password_reset_flow(make_user):
    make_user("asha")
    c = APIClient()
    assert c.post("/api/auth/password-reset/", {"email": "nobody@example.com"}, format="json").status_code == 200
    assert len(mail.outbox) == 0  # unknown email: same response, no mail
    assert c.post("/api/auth/password-reset/", {"email": "ASHA@example.com"}, format="json").status_code == 200
    m = re.search(r"/reset-password/([^/\s]+)/([^/\s]+)", mail.outbox[0].body)
    uid, token = m.groups()
    bad = c.post("/api/auth/password-reset/confirm/", {"uid": uid, "token": token, "password": "123"}, format="json")
    assert bad.status_code == 400
    ok = c.post("/api/auth/password-reset/confirm/", {"uid": uid, "token": token, "password": "brandNew#2026"}, format="json")
    assert ok.status_code == 200
    assert c.post("/api/auth/token/", {"username": "asha", "password": "brandNew#2026"}, format="json").status_code == 200
    again = c.post("/api/auth/password-reset/confirm/", {"uid": uid, "token": token, "password": "another#2026"}, format="json")
    assert again.status_code == 400  # token is single-use


def test_profile_and_change_password(make_user, client_for):
    u = make_user("asha")
    make_user("ravi")
    c = client_for(u)
    assert c.get("/api/auth/me/").json()["username"] == "asha"
    assert c.patch("/api/auth/me/", {"email": "new@example.com"}, format="json").status_code == 200
    assert c.patch("/api/auth/me/", {"email": "ravi@example.com"}, format="json").status_code == 400  # taken
    assert c.post("/api/auth/change-password/", {"old_password": "nope", "new_password": "Zxcvbn#12345"}, format="json").status_code == 400
    assert c.post("/api/auth/change-password/", {"old_password": "pass12345", "new_password": "Zxcvbn#12345"}, format="json").status_code == 200


# ---- recurring ----
def test_recurring_api_run_now_and_catch_up(trio):
    gid, users, (ca, cb, cc) = trio
    a = users[0]
    body = {"payer": a.id, "amount_paise": 900_000, "description": "Rent", "category": "rent",
            "split_type": "equal", "day_of_month": 5, "participants": parts(users)}
    r = ca.post(f"/api/groups/{gid}/recurring/", body, format="json")
    assert r.status_code == 201, r.content
    rid = r.json()["id"]
    assert cb.get(f"/api/groups/{gid}/recurring/").json()[0]["description"] == "Rent"
    assert ca.post(f"/api/groups/{gid}/recurring/{rid}/run/").status_code == 201
    assert Expense.objects.filter(description="Rent").count() == 1
    bad = dict(body, split_type="exact", participants=[{"user": a.id, "value": 1}])
    assert ca.post(f"/api/groups/{gid}/recurring/", bad, format="json").status_code == 400
    assert ca.patch(f"/api/groups/{gid}/recurring/{rid}/", {"active": False}, format="json").json()["active"] is False
    assert ca.delete(f"/api/groups/{gid}/recurring/{rid}/").status_code == 204


def test_recurring_task_catches_up_missed_days(trio):
    gid, users, _ = trio
    RecurringExpense.objects.create(group_id=gid, payer=users[0], amount_paise=300_000, description="Wifi",
                                    participants=[{"user": u.id, "value": None} for u in users], day_of_month=5)
    assert generate_recurring_expenses(datetime.date(2026, 12, 3)) == 0   # not due yet
    assert generate_recurring_expenses(datetime.date(2026, 12, 7)) == 1   # cron missed the 5th: still created
    assert generate_recurring_expenses(datetime.date(2026, 12, 8)) == 0   # once per month
    assert generate_recurring_expenses(datetime.date(2027, 1, 5)) == 1


def test_recurring_deactivates_when_payer_left(trio):
    gid, users, (ca, cb, cc) = trio
    r = RecurringExpense.objects.create(group_id=gid, payer=users[1], amount_paise=300_000, description="Wifi",
                                        participants=parts(users), day_of_month=1)
    assert cb.post(f"/api/groups/{gid}/leave/").status_code == 204
    assert generate_recurring_expenses(datetime.date(2026, 12, 2)) == 0
    r.refresh_from_db()
    assert r.active is False


# ---- pagination, summary, cron ----
def test_pagination_and_summary(trio):
    gid, users, (ca, cb, cc) = trio
    for _ in range(55):
        add_expense(gid, ca, users[0], 3_000, users)
    p1 = ca.get(f"/api/groups/{gid}/expenses/").json()
    assert p1["count"] == 55 and len(p1["results"]) == 50 and p1["next"]
    assert len(ca.get(f"/api/groups/{gid}/expenses/?page=2").json()["results"]) == 5
    s = ca.get("/api/summary/").json()
    assert s["owed_paise"] == 55 * 2_000 and s["owe_paise"] == 0
    assert cb.get("/api/summary/").json()["owe_paise"] == 55 * 1_000


def test_cron_requires_token(settings):
    settings.CRON_TOKEN = "s3cret"
    c = APIClient()
    assert c.post("/api/cron/daily/").status_code == 403
    assert c.post("/api/cron/daily/", HTTP_X_CRON_TOKEN="wrong").status_code == 403
    r = c.post("/api/cron/daily/", HTTP_X_CRON_TOKEN="s3cret")
    assert r.status_code == 200 and "recurring_created" in r.json()
    settings.CRON_TOKEN = ""
    assert c.post("/api/cron/daily/", HTTP_X_CRON_TOKEN="").status_code == 403  # disabled when unset


def test_brevo_backend_builds_request(settings):
    from django.core.mail import EmailMultiAlternatives
    from splitter.email_backend import BrevoEmailBackend
    settings.BREVO_API_KEY = "key123"
    settings.DEFAULT_FROM_EMAIL = "Splitter <me@example.com>"
    msg = EmailMultiAlternatives("Hi", "plain", None, ["to@example.com"])
    msg.attach_alternative("<b>html</b>", "text/html")
    with mock.patch("urllib.request.urlopen") as op:
        assert BrevoEmailBackend().send_messages([msg]) == 1
    req = op.call_args[0][0]
    import json
    body = json.loads(req.data)
    assert req.headers["Api-key"] == "key123"
    assert body["sender"] == {"email": "me@example.com", "name": "Splitter"}
    assert body["to"] == [{"email": "to@example.com"}] and body["htmlContent"] == "<b>html</b>"
