from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ActivityLog, Expense, Group, Membership, Settlement
from .serializers import (ActivitySerializer, ExpenseSerializer, ExpenseWriteSerializer,
                          GroupSerializer, ReceiptSerializer, RegisterSerializer,
                          SettlementSerializer)
from .services import expenses as svc
from .services.balances import compute_net_balances
from .services.simplify import simplify_debts

User = get_user_model()


class GroupScoped:
    """Every group-nested endpoint goes through here: non-members get a 404,
    so users can neither read nor even discover other groups' data."""

    def get_group(self):
        if not hasattr(self, "_group"):
            g = Group.objects.filter(pk=self.kwargs["group_id"], memberships__user=self.request.user).first()
            if g is None:
                raise NotFound()
            self._group = g
        return self._group


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class GroupListCreate(generics.ListCreateAPIView):
    serializer_class = GroupSerializer

    def get_queryset(self):
        return (Group.objects.filter(memberships__user=self.request.user)
                .prefetch_related("memberships__user").order_by("-created_at"))

    def perform_create(self, serializer):
        g = serializer.save(created_by=self.request.user)
        Membership.objects.create(group=g, user=self.request.user)
        svc.log(g, self.request.user, "group.created", "group", g.id, {"name": g.name})


class GroupDetail(GroupScoped, APIView):
    def get(self, request, group_id):
        return Response(GroupSerializer(self.get_group()).data)


class JoinGroup(APIView):
    def post(self, request):
        code = request.data.get("invite_code", "")
        group = Group.objects.filter(invite_code=code).first()
        if group is None:
            raise NotFound("Invalid invite code.")
        try:
            Membership.objects.create(group=group, user=request.user)
            svc.log(group, request.user, "member.joined", "group", group.id)
        except IntegrityError:
            pass  # already a member: joining twice is harmless
        return Response(GroupSerializer(group).data)


class ExpenseListCreate(GroupScoped, generics.ListCreateAPIView):
    serializer_class = ExpenseSerializer

    def get_queryset(self):
        return (Expense.objects.filter(group=self.get_group(), is_deleted=False)
                .select_related("payer").prefetch_related("splits"))

    def create(self, request, *args, **kwargs):
        group = self.get_group()
        s = ExpenseWriteSerializer(data=request.data, context={"group": group})
        s.is_valid(raise_exception=True)
        d = s.validated_data
        e = svc.create_expense(group=group, actor=request.user, payer_id=d["payer"],
                               amount_paise=d["amount_paise"], description=d["description"],
                               category=d["category"], date=d["date"], split_type=d["split_type"],
                               splits=d["splits"])
        return Response(ExpenseSerializer(e, context={"request": request}).data, status=status.HTTP_201_CREATED)


class ExpenseDetail(GroupScoped, APIView):
    def _get(self, pk):
        e = (Expense.objects.filter(pk=pk, group=self.get_group(), is_deleted=False)
             .select_related("payer").prefetch_related("splits").first())
        if e is None:
            raise NotFound()
        return e

    def get(self, request, group_id, pk):
        return Response(ExpenseSerializer(self._get(pk), context={"request": request}).data)

    def put(self, request, group_id, pk):
        group = self.get_group()
        self._get(pk)
        s = ExpenseWriteSerializer(data=request.data, context={"group": group})
        s.is_valid(raise_exception=True)
        d = s.validated_data
        if "version" not in d:
            return Response({"version": "Required for edits."}, status=400)
        try:
            e = svc.update_expense(expense_id=pk, group=group, actor=request.user, version=d["version"],
                                   payer_id=d["payer"], amount_paise=d["amount_paise"],
                                   description=d["description"], category=d["category"], date=d["date"],
                                   split_type=d["split_type"], splits=d["splits"])
        except svc.ConflictError:
            return Response({"detail": "Someone else edited this expense. Reload and retry."}, status=409)
        return Response(ExpenseSerializer(e, context={"request": request}).data)

    def delete(self, request, group_id, pk):
        group = self.get_group()
        self._get(pk)
        version = request.query_params.get("version")
        try:
            svc.delete_expense(expense_id=pk, group=group, actor=request.user,
                               version=int(version) if version else None)
        except svc.ConflictError:
            return Response({"detail": "Someone else edited this expense. Reload and retry."}, status=409)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReceiptUpload(GroupScoped, APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, group_id, pk):
        e = Expense.objects.filter(pk=pk, group=self.get_group(), is_deleted=False).first()
        if e is None:
            raise NotFound()
        s = ReceiptSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        f = s.validated_data["receipt"]
        if f.size > 5 * 1024 * 1024 or f.content_type not in ("image/jpeg", "image/png", "application/pdf"):
            return Response({"receipt": "Only JPG/PNG/PDF up to 5 MB."}, status=400)
        e.receipt = f
        e.save(update_fields=["receipt"])
        svc.log(e.group, request.user, "expense.receipt_added", "expense", e.id)
        return Response(ExpenseSerializer(e, context={"request": request}).data)


class BalanceView(GroupScoped, APIView):
    def get(self, request, group_id):
        group = self.get_group()
        net = compute_net_balances(group)
        names = dict(User.objects.filter(id__in=net).values_list("id", "username"))
        payments = simplify_debts(net)
        return Response({
            "balances": [{"user": u, "username": names[u], "net_paise": a} for u, a in sorted(net.items())],
            "suggested_payments": [
                {"from_user": f, "from_name": names[f], "to_user": t, "to_name": names[t], "amount_paise": a}
                for f, t, a in payments],
        })


class SettlementListCreate(GroupScoped, generics.ListCreateAPIView):
    serializer_class = SettlementSerializer

    def get_queryset(self):
        return Settlement.objects.filter(group=self.get_group()).select_related("from_user", "to_user")

    def perform_create(self, serializer):
        group = self.get_group()
        to_user = serializer.validated_data["to_user"]
        if to_user == self.request.user:
            raise ValidationError({"to_user": "You cannot pay yourself."})
        if not Membership.objects.filter(group=group, user=to_user).exists():
            raise ValidationError({"to_user": "Receiver must be a group member."})
        if serializer.validated_data["amount_paise"] <= 0:
            raise ValidationError({"amount_paise": "Must be positive."})
        s = serializer.save(group=group, from_user=self.request.user)  # always "I paid X"
        svc.log(group, self.request.user, "settlement.created", "settlement", s.id,
                {"to": to_user.id, "amount_paise": s.amount_paise})


class SettlementRespond(GroupScoped, APIView):
    def post(self, request, group_id, pk):
        s = Settlement.objects.filter(pk=pk, group=self.get_group()).first()
        if s is None:
            raise NotFound()
        action = request.data.get("action")
        if action not in ("accept", "reject"):
            return Response({"action": "Must be 'accept' or 'reject'."}, status=400)
        try:
            s = svc.respond_to_settlement(settlement=s, actor=request.user, accept=action == "accept")
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=403)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=409)
        return Response(SettlementSerializer(s).data)


class ActivityView(GroupScoped, generics.ListAPIView):
    serializer_class = ActivitySerializer

    def get_queryset(self):
        return ActivityLog.objects.filter(group=self.get_group()).select_related("actor")


class InsightsView(GroupScoped, APIView):
    def get(self, request, group_id):
        qs = Expense.objects.filter(group=self.get_group(), is_deleted=False)
        by_cat = qs.values("category").annotate(total=Sum("amount_paise")).order_by("-total")
        by_month = qs.annotate(m=TruncMonth("date")).values("m").annotate(total=Sum("amount_paise")).order_by("m")
        by_member = qs.values("payer__username").annotate(total=Sum("amount_paise")).order_by("-total")
        return Response({
            "by_category": [{"category": r["category"], "total_paise": r["total"]} for r in by_cat],
            "by_month": [{"month": r["m"].strftime("%Y-%m"), "total_paise": r["total"]} for r in by_month],
            "by_member": [{"username": r["payer__username"], "total_paise": r["total"]} for r in by_member],
        })


class Health(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = []

    def get(self, request):
        return Response({"status": "ok"})
