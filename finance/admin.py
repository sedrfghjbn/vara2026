from django.contrib import admin
from .models import Transaction, Budget, Goal, Category


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['type', 'category', 'amount', 'description', 'date']
    list_filter = ['type', 'category', 'date']
    search_fields = ['description', 'category']


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ['category', 'limit', 'period', 'created_at']
    list_filter = ['period', 'created_at']


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ['name', 'current', 'amount', 'deadline']
    list_filter = ['deadline']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'user', 'created_at']
    list_filter = ['type', 'created_at']
    search_fields = ['name']

