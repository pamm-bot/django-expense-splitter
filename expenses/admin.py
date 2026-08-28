from django.contrib import admin

from .models import Expense, ExpenseShare, Group, Settlement


class ExpenseShareInline(admin.TabularInline):
    model = ExpenseShare
    extra = 0


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ["name", "created_by", "created_at"]
    filter_horizontal = ["members"]


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["description", "group", "amount", "paid_by", "created_at"]
    list_filter = ["group"]
    inlines = [ExpenseShareInline]


@admin.register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display = ["group", "paid_by", "paid_to", "amount", "created_at"]
    list_filter = ["group"]
