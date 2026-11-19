from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import ActivityLog, Expense, ExpenseSplit, Group, RecurringExpense, Settlement, SplitType
from .services.splits import SplitError, compute_splits

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def validate_email(self, v):
        if User.objects.filter(email__iexact=v).exists():
            raise serializers.ValidationError("Email already registered.")
        return v

    def validate_password(self, v):
        validate_password(v)
        return v

    def create(self, data):
        return User.objects.create_user(**data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class GroupSerializer(serializers.ModelSerializer):
    members = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ["id", "name", "invite_code", "created_by", "created_at", "members"]
        read_only_fields = ["invite_code", "created_by", "created_at"]

    def get_members(self, g):
        return UserSerializer([m.user for m in g.memberships.select_related("user")], many=True).data


class ParticipantSerializer(serializers.Serializer):
    user = serializers.IntegerField()
    value = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, allow_null=True)


class ExpenseWriteSerializer(serializers.Serializer):
    payer = serializers.IntegerField()
    amount_paise = serializers.IntegerField(min_value=1)
    description = serializers.CharField(max_length=255)
    category = serializers.CharField(max_length=50, default="general")
    date = serializers.DateField()
    split_type = serializers.ChoiceField(choices=SplitType.choices)
    participants = ParticipantSerializer(many=True, allow_empty=False)
    version = serializers.IntegerField(required=False)

    def validate(self, attrs):
        member_ids = set(self.context["group"].memberships.values_list("user_id", flat=True))
        if attrs["payer"] not in member_ids:
            raise serializers.ValidationError({"payer": "Payer must be a group member."})
        parts = [{"user": p["user"], "value": p.get("value")} for p in attrs["participants"]]
        if any(p["user"] not in member_ids for p in parts):
            raise serializers.ValidationError({"participants": "All participants must be group members."})
        try:
            attrs["splits"] = compute_splits(attrs["split_type"], attrs["amount_paise"], parts)
        except SplitError as exc:
            raise serializers.ValidationError({"participants": str(exc)})
        return attrs


class ExpenseSplitSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseSplit
        fields = ["user", "share_paise"]


class ExpenseSerializer(serializers.ModelSerializer):
    splits = ExpenseSplitSerializer(many=True, read_only=True)
    payer_name = serializers.CharField(source="payer.username", read_only=True)

    class Meta:
        model = Expense
        fields = ["id", "group", "payer", "payer_name", "amount_paise", "description", "category",
                  "date", "split_type", "receipt", "version", "created_at", "splits"]


class ReceiptSerializer(serializers.Serializer):
    receipt = serializers.FileField()


class SettlementSerializer(serializers.ModelSerializer):
    from_name = serializers.CharField(source="from_user.username", read_only=True)
    to_name = serializers.CharField(source="to_user.username", read_only=True)

    class Meta:
        model = Settlement
        fields = ["id", "from_user", "from_name", "to_user", "to_name", "amount_paise", "status", "created_at"]
        read_only_fields = ["id", "from_user", "status", "created_at"]


class ActivitySerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor.username", read_only=True, default=None)

    class Meta:
        model = ActivityLog
        fields = ["id", "actor", "actor_name", "action", "entity_type", "entity_id", "payload", "created_at"]


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]
        read_only_fields = ["username"]

    def validate_email(self, v):
        if User.objects.filter(email__iexact=v).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("Email already in use.")
        return v


class RecurringSerializer(serializers.ModelSerializer):
    payer_name = serializers.CharField(source="payer.username", read_only=True)

    class Meta:
        model = RecurringExpense
        fields = ["id", "payer", "payer_name", "amount_paise", "description", "category",
                  "split_type", "participants", "day_of_month", "active", "last_run"]


class RecurringWriteSerializer(ExpenseWriteSerializer):
    date = None      # removed: generated expenses use the run date
    version = None
    day_of_month = serializers.IntegerField(min_value=1, max_value=28)
