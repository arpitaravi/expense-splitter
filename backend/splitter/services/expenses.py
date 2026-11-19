from django.db import transaction
from django.utils import timezone

from ..models import ActivityLog, Expense, ExpenseSplit, Settlement


class ConflictError(Exception):
    """Expense was edited by someone else since the client loaded it."""


def log(group, actor, action, entity_type, entity_id, payload=None):
    ActivityLog.objects.create(group=group, actor=actor, action=action,
                               entity_type=entity_type, entity_id=entity_id, payload=payload or {})


def _snapshot(e):
    return {
        "payer": e.payer_id, "amount_paise": e.amount_paise, "description": e.description,
        "category": e.category, "date": str(e.date), "split_type": e.split_type,
        "splits": {s.user_id: s.share_paise for s in e.splits.all()},
    }


def _write_splits(expense, splits):
    ExpenseSplit.objects.bulk_create(
        [ExpenseSplit(expense=expense, user_id=u, share_paise=s) for u, s in splits.items()])


@transaction.atomic
def create_expense(*, group, actor, payer_id, amount_paise, description, category, date,
                   split_type, splits):
    e = Expense.objects.create(group=group, payer_id=payer_id, created_by=actor,
                               amount_paise=amount_paise, description=description,
                               category=category, date=date, split_type=split_type)
    _write_splits(e, splits)
    log(group, actor, "expense.created", "expense", e.id, _snapshot(e))
    from ..tasks import notify_new_expense, safe_delay
    transaction.on_commit(lambda: safe_delay(notify_new_expense, e.id))
    return e


@transaction.atomic
def update_expense(*, expense_id, group, actor, version, payer_id, amount_paise, description,
                   category, date, split_type, splits):
    # Row lock + version check => two simultaneous editors can't silently overwrite each other.
    e = Expense.objects.select_for_update().get(pk=expense_id, group=group, is_deleted=False)
    if e.version != version:
        raise ConflictError()
    before = _snapshot(e)
    e.payer_id, e.amount_paise, e.description = payer_id, amount_paise, description
    e.category, e.date, e.split_type = category, date, split_type
    e.version += 1
    e.save()
    e.splits.all().delete()
    _write_splits(e, splits)
    log(group, actor, "expense.updated", "expense", e.id, {"before": before, "after": _snapshot(e)})
    return e


@transaction.atomic
def delete_expense(*, expense_id, group, actor, version=None):
    e = Expense.objects.select_for_update().get(pk=expense_id, group=group, is_deleted=False)
    if version is not None and e.version != version:
        raise ConflictError()
    before = _snapshot(e)
    e.is_deleted = True  # soft delete: history stays, balances are recomputed from live rows
    e.version += 1
    e.save()
    log(group, actor, "expense.deleted", "expense", e.id, before)
    return e


@transaction.atomic
def respond_to_settlement(*, settlement, actor, accept):
    s = Settlement.objects.select_for_update().get(pk=settlement.pk)
    if s.status != Settlement.Status.PENDING:
        raise ValueError("This settlement was already answered.")
    if s.to_user_id != actor.id:
        raise PermissionError("Only the receiver can confirm a settlement.")
    s.status = Settlement.Status.ACCEPTED if accept else Settlement.Status.REJECTED
    s.responded_at = timezone.now()
    s.save()
    log(s.group, actor, f"settlement.{s.status}", "settlement", s.id,
        {"from": s.from_user_id, "to": s.to_user_id, "amount_paise": s.amount_paise})
    return s
