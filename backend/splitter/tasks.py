import logging
from datetime import date

from celery import shared_task
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from .models import Expense, Group, RecurringExpense
from .services.balances import compute_net_balances

logger = logging.getLogger(__name__)


def safe_delay(task, *args):
    """Never fail a request because the broker/email is down.
    With CELERY_ENABLED=1 the task is queued; otherwise it runs inline (no worker needed)."""
    try:
        if settings.CELERY_ENABLED:
            task.delay(*args)
        else:
            task(*args)
    except Exception:  # pragma: no cover
        logger.exception("Could not run/enqueue %s", task)


def rupees(paise):
    return f"₹{paise / 100:,.2f}"


@shared_task
def notify_new_expense(expense_id):
    e = Expense.objects.select_related("payer", "group").get(pk=expense_id)
    for split in e.splits.select_related("user"):
        u = split.user
        if u.id == e.payer_id or not u.email:
            continue
        send_mail(
            subject=f"[{e.group.name}] New expense: {e.description}",
            message=(f"{e.payer.username} paid {rupees(e.amount_paise)} for \"{e.description}\".\n"
                     f"Your share: {rupees(split.share_paise)}.\n{settings.FRONTEND_URL}/groups/{e.group_id}"),
            from_email=None, recipient_list=[u.email], fail_silently=True)


@shared_task
def weekly_digest():
    """Monday digest: tell each person what they owe in each group."""
    sent = 0
    for group in Group.objects.prefetch_related("memberships__user"):
        net = compute_net_balances(group)
        for m in group.memberships.all():
            amount = net.get(m.user_id, 0)
            if amount < 0 and m.user.email:
                send_mail(f"[{group.name}] You owe {rupees(-amount)}",
                          f"Hi {m.user.username}, you currently owe {rupees(-amount)} in \"{group.name}\".",
                          None, [m.user.email], fail_silently=True)
                sent += 1
    return sent


def run_recurring(r, today):
    """Create one expense from a recurring template. Returns the expense or None."""
    from .models import Membership
    from .services import expenses as svc
    from .services.splits import SplitError, compute_splits
    members = set(Membership.objects.filter(group=r.group).values_list("user_id", flat=True))
    parts = [p for p in r.participants if p["user"] in members]
    if r.payer_id not in members or not parts:
        r.active = False  # payer/everyone left the group: stop generating
        r.save(update_fields=["active"])
        return None
    try:
        splits = compute_splits(r.split_type, r.amount_paise, parts)
    except SplitError:
        logger.warning("Recurring %s skipped: split no longer valid", r.pk)
        return None
    with transaction.atomic():
        e = svc.create_expense(group=r.group, actor=r.payer, payer_id=r.payer_id,
                               amount_paise=r.amount_paise, description=r.description,
                               category=r.category, date=today, split_type=r.split_type, splits=splits)
        r.last_run = today
        r.save(update_fields=["last_run"])
    return e


@shared_task
def generate_recurring_expenses(today=None):
    """Create this month's expense for every template that is due (catches up if a day was missed)."""
    today = today or date.today()
    created = 0
    for r in RecurringExpense.objects.filter(active=True, day_of_month__lte=today.day).select_related("group", "payer"):
        if r.last_run and (r.last_run.year, r.last_run.month) == (today.year, today.month):
            continue
        if run_recurring(r, today):
            created += 1
    return created


@shared_task
def send_invite_email(group_id, inviter_id, email):
    group = Group.objects.get(pk=group_id)
    inviter = get_user_model().objects.get(pk=inviter_id)
    link = f"{settings.FRONTEND_URL}/join/{group.invite_code}"
    send_mail(
        subject=f"{inviter.username} invited you to \"{group.name}\" on Splitter",
        message=(f"Hi!\n\n{inviter.username} added you to the expense group \"{group.name}\".\n"
                 f"Join here: {link}\n\nSign up (or log in) first if you don't have an account."),
        from_email=None, recipient_list=[email], fail_silently=True)


@shared_task
def send_password_reset_email(user_id):
    user = get_user_model().objects.get(pk=user_id)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}"
    send_mail(
        subject="Reset your Splitter password",
        message=f"Hi {user.username},\n\nReset your password here (valid for a few hours):\n{link}\n\n"
                "If you didn't ask for this, ignore this email.",
        from_email=None, recipient_list=[user.email], fail_silently=True)
