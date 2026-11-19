from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views, views_extra as x

urlpatterns = [
    path("health/", views.Health.as_view()),
    path("auth/register/", views.RegisterView.as_view()),
    path("auth/token/", TokenObtainPairView.as_view()),
    path("auth/token/refresh/", TokenRefreshView.as_view()),
    path("auth/me/", x.MeView.as_view()),
    path("auth/change-password/", x.ChangePassword.as_view()),
    path("auth/password-reset/", x.PasswordResetRequest.as_view()),
    path("auth/password-reset/confirm/", x.PasswordResetConfirm.as_view()),
    path("summary/", x.SummaryView.as_view()),
    path("cron/daily/", x.CronDaily.as_view()),
    path("groups/", views.GroupListCreate.as_view()),
    path("groups/join/", views.JoinGroup.as_view()),
    path("groups/<int:group_id>/", views.GroupDetail.as_view()),
    path("groups/<int:group_id>/expenses/", views.ExpenseListCreate.as_view()),
    path("groups/<int:group_id>/expenses/<int:pk>/", views.ExpenseDetail.as_view()),
    path("groups/<int:group_id>/expenses/<int:pk>/receipt/", views.ReceiptUpload.as_view()),
    path("groups/<int:group_id>/balances/", views.BalanceView.as_view()),
    path("groups/<int:group_id>/settlements/", views.SettlementListCreate.as_view()),
    path("groups/<int:group_id>/settlements/<int:pk>/respond/", views.SettlementRespond.as_view()),
    path("groups/<int:group_id>/activity/", views.ActivityView.as_view()),
    path("groups/<int:group_id>/insights/", views.InsightsView.as_view()),
    path("groups/<int:group_id>/leave/", x.LeaveGroup.as_view()),
    path("groups/<int:group_id>/members/<int:user_id>/", x.RemoveMember.as_view()),
    path("groups/<int:group_id>/invite/", x.InviteView.as_view()),
    path("groups/<int:group_id>/recurring/", x.RecurringListCreate.as_view()),
    path("groups/<int:group_id>/recurring/<int:pk>/", x.RecurringDetail.as_view()),
    path("groups/<int:group_id>/recurring/<int:pk>/run/", x.RecurringRunNow.as_view()),
]
