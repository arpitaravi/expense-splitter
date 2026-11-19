import hmac
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import Group, RecurringExpense
from .serializers import MeSerializer, RecurringSerializer, RecurringWriteSerializer
from .services import expenses as svc
from .services.balances import compute_net_balances
from .services.members import MemberError, remove_member
from .tasks import (generate_recurring_expenses, run_recurring, safe_delay, send_invite_email,
                    send_password_reset_email, weekly_digest)
from .views import GroupScoped

User = get_user_model()


# ---------------- account ----------------
class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user


class ChangePassword(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        old, new = request.data.get("old_password", ""), request.data.get("new_password", "")
        if not request.user.check_password(old):
            return Response({"old_password": "Current password is wrong."}, status=400)
        try:
            validate_password(new, request.user)
        except DjangoValidationError as exc:
            return Response({"new_password": list(exc.messages)}, status=400)
        request.user.set_password(new)
        request.user.save()
        return Response({"detail": "Password changed. Please log in again on other devices."})


class PasswordResetRequest(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        email = (request.data.get("email") or "").strip()
        if email:
            u = User.objects.filter(email__iexact=email, is_active=True).first()
            if u:
                safe_delay(send_password_reset_email, u.id)
        # same answer either way: don't reveal which emails are registered
        return Response({"detail": "If that email is registered, a reset link has been sent."})


class PasswordResetConfirm(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(request.data.get("uid", ""))))
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            user = None
        if user is None or not default_token_generator.check_token(user, request.data.get("token", "")):
            return Response({"detail": "This reset link is invalid or has expired."}, status=400)
        new = request.data.get("password", "")
        try:
            validate_password(new, user)
        except DjangoValidationError as exc:
            return Response({"password": list(exc.messages)}, status=400)
        user.set_password(new)
        user.save()
        return Response({"detail": "Password updated. You can log in now."})


class SummaryView(APIView):
    """Across all my groups: how much I'm owed / owe."""

    def get(self, request):
        per, owed, owe = [], 0, 0
        for g in Group.objects.filter(memberships__user=request.user):
            net = compute_net_balances(g).get(request.user.id, 0)
            per.append({"group": g.id, "net_paise": net})
            owed += max(net, 0)
            owe += max(-net, 0)
        return Response({"owed_paise": owed, "owe_paise": owe, "groups": per})


# ---------------- members ----------------
class LeaveGroup(GroupScoped, APIView):
    def post(self, request, group_id):
        try:
            remove_member(self.get_group(), request.user, actor=request.user)
        except MemberError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RemoveMember(GroupScoped, APIView):
    def delete(self, request, group_id, user_id):
        group = self.get_group()
        if group.created_by_id != request.user.id:
            return Response({"detail": "Only the group creator can remove members."}, status=403)
        if user_id == request.user.id:
            return Response({"detail": "Use 'Leave group' to leave."}, status=400)
        target = User.objects.filter(pk=user_id).first()
        if target is None:
            raise NotFound()
        try:
            remove_member(group, target, actor=request.user)
        except MemberError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(status=status.HTTP_204_NO_CONTENT)


class InviteView(GroupScoped, APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "invite"

    def post(self, request, group_id):
        group = self.get_group()
        raw = request.data.get("emails", [])
        if isinstance(raw, str):
            raw = raw.replace("\n", ",").split(",")
        emails, invalid = [], []
        for e in {x.strip().lower() for x in raw if x.strip()}:
            try:
                validate_email(e)
                emails.append(e)
            except DjangoValidationError:
                invalid.append(e)
        if not emails:
            return Response({"detail": "Enter at least one valid email.", "invalid": invalid}, status=400)
        if len(emails) > 10:
            return Response({"detail": "Max 10 emails at a time."}, status=400)
        for e in emails:
            safe_delay(send_invite_email, group.id, request.user.id, e)
        svc.log(group, request.user, "member.invited", "group", group.id, {"count": len(emails)})
        return Response({"sent": len(emails), "invalid": invalid})


# ---------------- recurring ----------------
class RecurringListCreate(GroupScoped, APIView):
    def get(self, request, group_id):
        qs = RecurringExpense.objects.filter(group=self.get_group()).select_related("payer").order_by("id")
        return Response(RecurringSerializer(qs, many=True).data)

    def post(self, request, group_id):
        group = self.get_group()
        s = RecurringWriteSerializer(data=request.data, context={"group": group})
        s.is_valid(raise_exception=True)
        d = s.validated_data
        today = date.today()
        r = RecurringExpense.objects.create(
            group=group, payer_id=d["payer"], amount_paise=d["amount_paise"], description=d["description"],
            category=d["category"], split_type=d["split_type"], day_of_month=d["day_of_month"],
            participants=[{"user": p["user"], "value": None if p.get("value") is None else str(p["value"])}
                          for p in d["participants"]],
            # if this month's day has already passed, the first run is next month
            last_run=today if d["day_of_month"] <= today.day else None)
        svc.log(group, request.user, "recurring.created", "recurring", r.id, {"description": r.description})
        return Response(RecurringSerializer(r).data, status=201)


class RecurringDetail(GroupScoped, APIView):
    def _get(self, pk):
        r = RecurringExpense.objects.filter(pk=pk, group=self.get_group()).first()
        if r is None:
            raise NotFound()
        return r

    def patch(self, request, group_id, pk):
        r = self._get(pk)
        if "active" in request.data:
            r.active = bool(request.data["active"])
            r.save(update_fields=["active"])
        return Response(RecurringSerializer(r).data)

    def delete(self, request, group_id, pk):
        self._get(pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecurringRunNow(RecurringDetail):
    def post(self, request, group_id, pk):
        r = self._get(pk)
        e = run_recurring(r, date.today())
        if e is None:
            return Response({"detail": "Could not create the expense (members changed?)."}, status=409)
        return Response({"expense": e.id}, status=201)


# ---------------- scheduler hook (free hosting has no Celery beat) ----------------
class CronDaily(APIView):
    """POST with header X-Cron-Token. Call it daily from cron-job.org / GitHub Actions."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = []

    def post(self, request):
        from django.conf import settings
        token = settings.CRON_TOKEN
        if not token or not hmac.compare_digest(request.headers.get("X-Cron-Token", ""), token):
            return Response({"detail": "Forbidden"}, status=403)
        created = generate_recurring_expenses()
        digests = weekly_digest() if date.today().weekday() == 0 else 0  # Mondays
        return Response({"recurring_created": created, "digests_sent": digests})
