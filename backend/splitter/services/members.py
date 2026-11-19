from django.db import transaction
from django.db.models import Q

from ..models import Membership, Settlement
from .balances import compute_net_balances
from .expenses import log


class MemberError(Exception):
    pass


@transaction.atomic
def remove_member(group, user, actor):
    m = Membership.objects.select_for_update().filter(group=group, user=user).first()
    if m is None:
        raise MemberError("Not a member of this group.")
    if compute_net_balances(group).get(user.id, 0) != 0:
        raise MemberError("Settle up first: this person's balance isn't zero yet.")
    if Settlement.objects.filter(group=group, status=Settlement.Status.PENDING).filter(
            Q(from_user=user) | Q(to_user=user)).exists():
        raise MemberError("There is a pending payment involving this person. Confirm or reject it first.")
    log(group, actor, "member.left" if actor == user else "member.removed", "group", group.id, {"user": user.id})
    m.delete()
    if not group.memberships.exists():
        group.delete()
