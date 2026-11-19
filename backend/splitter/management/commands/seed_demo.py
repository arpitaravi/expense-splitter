"""python manage.py seed_demo  -> demo users + a trip group with realistic data (idempotent)."""
import datetime

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.test.utils import override_settings

from splitter.models import Group, Membership, Settlement
from splitter.services import expenses as svc
from splitter.services.splits import compute_splits

PASSWORD = "demo12345"


class Command(BaseCommand):
    help = "Create demo users (asha, ravi, meena / demo12345) and a sample group."

    def handle(self, *args, **opts):
        # never email the fake demo addresses
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.dummy.EmailBackend"):
            self._seed()

    def _seed(self):
        User = get_user_model()
        users = {}
        for name in ("asha", "ravi", "meena"):
            u, created = User.objects.get_or_create(username=name, defaults={"email": f"{name}@example.com"})
            if created:
                u.set_password(PASSWORD)
                u.save()
            users[name] = u
        if Group.objects.filter(name="Goa Trip 🏖️", created_by=users["asha"]).exists():
            self.stdout.write("Demo data already exists.")
            return
        g = Group.objects.create(name="Goa Trip 🏖️", created_by=users["asha"])
        for u in users.values():
            Membership.objects.create(group=g, user=u)
        ids = [u.id for u in users.values()]
        everyone = [{"user": i, "value": None} for i in ids]
        d = datetime.date.today()

        def add(payer, amount, desc, cat, split="equal", parts=None, days=0):
            parts = parts or everyone
            svc.create_expense(group=g, actor=users[payer], payer_id=users[payer].id,
                               amount_paise=amount, description=desc, category=cat,
                               date=d - datetime.timedelta(days=days), split_type=split,
                               splits=compute_splits(split, amount, parts))

        add("asha", 1_800_000, "Hotel (3 nights)", "travel", days=6)
        add("ravi", 450_000, "Beach shack dinner", "food", days=4)
        add("meena", 320_000, "Scooter rental", "travel", "shares",
            [{"user": users["asha"].id, "value": 2}, {"user": users["ravi"].id, "value": 1},
             {"user": users["meena"].id, "value": 1}], days=3)
        add("asha", 120_000, "Water sports", "fun", "percent",
            [{"user": users["asha"].id, "value": 40}, {"user": users["ravi"].id, "value": 30},
             {"user": users["meena"].id, "value": 30}], days=2)
        s = Settlement.objects.create(group=g, from_user=users["ravi"], to_user=users["asha"], amount_paise=200_000)
        svc.respond_to_settlement(settlement=s, actor=users["asha"], accept=True)
        self.stdout.write(self.style.SUCCESS(f"Demo ready. Log in as asha / {PASSWORD}"))
