import uuid

from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


def new_invite_code():
    return uuid.uuid4().hex[:12]


class Group(models.Model):
    name = models.CharField(max_length=120)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_groups")
    invite_code = models.CharField(max_length=32, unique=True, default=new_invite_code)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Membership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="memberships")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "group"], name="uniq_member")]


class SplitType(models.TextChoices):
    EQUAL = "equal", "Equal"
    EXACT = "exact", "Exact amounts"
    PERCENT = "percent", "Percentages"
    SHARES = "shares", "Shares / weights"


class Expense(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="expenses")
    payer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="paid_expenses")
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    amount_paise = models.PositiveBigIntegerField()  # money is ALWAYS integer paise
    description = models.CharField(max_length=255)
    category = models.CharField(max_length=50, default="general")
    date = models.DateField()
    split_type = models.CharField(max_length=10, choices=SplitType.choices, default=SplitType.EQUAL)
    receipt = models.FileField(upload_to="receipts/", null=True, blank=True)
    is_deleted = models.BooleanField(default=False)  # soft delete
    version = models.PositiveIntegerField(default=1)  # optimistic concurrency
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-id"]
        indexes = [models.Index(fields=["group", "is_deleted", "date"])]


class ExpenseSplit(models.Model):
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name="splits")
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    share_paise = models.PositiveBigIntegerField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["expense", "user"], name="uniq_split_user")]


class Settlement(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="settlements")
    from_user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="settlements_made")
    to_user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="settlements_received")
    amount_paise = models.PositiveBigIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class ActivityLog(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="activity")
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="+")
    action = models.CharField(max_length=50)  # e.g. expense.created
    entity_type = models.CharField(max_length=30)
    entity_id = models.PositiveBigIntegerField()
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class RecurringExpense(models.Model):
    """Template used by the Celery beat task to generate e.g. monthly rent."""
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="recurring")
    payer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    amount_paise = models.PositiveBigIntegerField()
    description = models.CharField(max_length=255)
    category = models.CharField(max_length=50, default="rent")
    split_type = models.CharField(max_length=10, choices=SplitType.choices, default=SplitType.EQUAL)
    participants = models.JSONField(default=list)  # [{"user": id, "value": n}]
    day_of_month = models.PositiveSmallIntegerField(default=1)
    last_run = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)
