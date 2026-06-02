from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Employee, Vacancy, Training, Certificate, Department, Position
from hr.integrations.telegram.models import (
    EmployeeTelegramLink,
    UserTelegramLink,
    TelegramLinkCode,
    TelegramLinkSession,
    NotificationLog,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'telegram_bind_code', 'is_staff', 'is_active']
    list_filter = ['role', 'is_staff', 'is_active']
    readonly_fields = ['telegram_bind_code']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Дополнительная информация', {'fields': ('role', 'phone', 'telegram_bind_code')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Дополнительная информация', {'fields': ('role', 'phone', 'email')}),
    )


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'position', 'department', 'status', 'hire_date']
    list_filter = ['status', 'department', 'position']
    search_fields = ['first_name', 'last_name', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'hr_manager', 'department', 'created_at']
    list_filter = ['status', 'department', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']


from django.utils import timezone


@admin.register(Training)
class TrainingAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'responsible', 'start_date', 'end_date']
    list_filter = ['status', 'start_date']
    search_fields = ['title', 'description']
    filter_horizontal = ['participants']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['start_selected_now']

    def start_selected_now(self, request, queryset):
        started = 0
        today = timezone.localtime(timezone.now()).date()
        for training in queryset:
            training._started_by_user = request.user
            training.start_date = today
            training.status = 'in_progress'
            training.save()
            started += 1
        self.message_user(request, f'Запущено {started} обучений (start_date установлена на {today}).')
    start_selected_now.short_description = 'Start selected trainings (set start_date=today and notify)'


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ['employee', 'training', 'issue_date']
    list_filter = ['issue_date', 'training']
    search_fields = ['employee__first_name', 'employee__last_name', 'training__title']


@admin.register(EmployeeTelegramLink)
class EmployeeTelegramLinkAdmin(admin.ModelAdmin):
    list_display = ['employee', 'telegram_chat_id', 'is_active', 'linked_at']
    list_filter = ['is_active']
    search_fields = ['employee__first_name', 'employee__last_name', 'telegram_chat_id']


@admin.register(UserTelegramLink)
class UserTelegramLinkAdmin(admin.ModelAdmin):
    list_display = ['user', 'telegram_chat_id', 'is_active', 'linked_at']
    list_filter = ['is_active']
    search_fields = ['user__email', 'user__username', 'telegram_chat_id']


@admin.register(TelegramLinkSession)
class TelegramLinkSessionAdmin(admin.ModelAdmin):
    list_display = ['telegram_chat_id', 'awaiting_code', 'updated_at']
    list_filter = ['awaiting_code']


@admin.register(TelegramLinkCode)
class TelegramLinkCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'user', 'employee', 'is_used', 'expires_at', 'created_at']
    list_filter = ['is_used']
    search_fields = ['code', 'user__email']


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = [
        'event_type', 'recipient_role', 'status', 'telegram_chat_id', 'created_at',
    ]
    list_filter = ['event_type', 'recipient_role', 'status', 'created_at']
    search_fields = ['event_type', 'error_message', 'message_text']
    readonly_fields = [
        'event_type', 'recipient_role', 'recipient_user', 'recipient_employee',
        'telegram_chat_id', 'message_text', 'status', 'error_message',
        'attempt_count', 'payload', 'created_at', 'sent_at',
    ]

