from django.contrib import admin

from . import models

for m in (models.Group, models.Membership, models.Expense, models.ExpenseSplit,
          models.Settlement, models.ActivityLog, models.RecurringExpense):
    admin.site.register(m)
