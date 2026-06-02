import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone


class EmployeeTelegramLink(models.Model):
    """Привязка Telegram chat_id к карточке сотрудника."""

    employee = models.OneToOneField(
        'hr.Employee',
        on_delete=models.CASCADE,
        related_name='telegram_link',
        verbose_name='Сотрудник',
    )
    telegram_chat_id = models.BigIntegerField(verbose_name='Telegram Chat ID')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    linked_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата привязки')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'hr'
        verbose_name = 'Telegram-привязка сотрудника'
        verbose_name_plural = 'Telegram-привязки сотрудников'

    def __str__(self):
        return f'{self.employee} → {self.telegram_chat_id}'


class UserTelegramLink(models.Model):
    """Привязка Telegram chat_id к пользователю (HR-менеджер / администратор)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='telegram_link',
        verbose_name='Пользователь',
    )
    telegram_chat_id = models.BigIntegerField(verbose_name='Telegram Chat ID')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    linked_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата привязки')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'hr'
        verbose_name = 'Telegram-привязка пользователя'
        verbose_name_plural = 'Telegram-привязки пользователей'

    def __str__(self):
        return f'{self.user} → {self.telegram_chat_id}'


class TelegramLinkSession(models.Model):
    """Сессия диалога привязки: /start → ожидание кода → привязка."""

    telegram_chat_id = models.BigIntegerField(unique=True, verbose_name='Telegram Chat ID')
    awaiting_code = models.BooleanField(default=True, verbose_name='Ожидает код')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'hr'
        verbose_name = 'Сессия привязки Telegram'
        verbose_name_plural = 'Сессии привязки Telegram'

    def __str__(self):
        state = 'ожидает код' if self.awaiting_code else 'завершена'
        return f'chat {self.telegram_chat_id} ({state})'


class TelegramLinkCode(models.Model):
    """Одноразовый код для команды /start <code> в Telegram-боте."""

    code = models.CharField(max_length=32, unique=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='telegram_link_codes',
    )
    employee = models.ForeignKey(
        'hr.Employee',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='telegram_link_codes',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        app_label = 'hr'
        verbose_name = 'Код привязки Telegram'
        verbose_name_plural = 'Коды привязки Telegram'

    @classmethod
    def generate_for_user(cls, user, employee=None, ttl_minutes=30):
        active = cls.objects.filter(
            user=user,
            is_used=False,
            expires_at__gt=timezone.now(),
        ).order_by('-created_at').first()
        if active:
            if employee and active.employee_id != getattr(employee, 'pk', None):
                active.employee = employee
                active.save(update_fields=['employee'])
            return active

        code = secrets.token_urlsafe(8)[:12].upper()
        return cls.objects.create(
            code=code,
            user=user,
            employee=employee,
            expires_at=timezone.now() + timezone.timedelta(minutes=ttl_minutes),
        )

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()


class NotificationLog(models.Model):
    """Журнал доставки Telegram-уведомлений."""

    STATUS_PENDING = 'pending'
    STATUS_SENT = 'sent'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Ожидает'),
        (STATUS_SENT, 'Отправлено'),
        (STATUS_FAILED, 'Ошибка'),
    ]

    RECIPIENT_EMPLOYEE = 'employee'
    RECIPIENT_HR = 'hr_manager'
    RECIPIENT_ADMIN = 'admin'
    RECIPIENT_CHOICES = [
        (RECIPIENT_EMPLOYEE, 'Сотрудник'),
        (RECIPIENT_HR, 'HR-менеджер'),
        (RECIPIENT_ADMIN, 'Администратор'),
    ]

    event_type = models.CharField(max_length=64, db_index=True, verbose_name='Тип события')
    recipient_role = models.CharField(
        max_length=20,
        choices=RECIPIENT_CHOICES,
        verbose_name='Роль получателя',
    )
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notification_logs',
        verbose_name='Пользователь',
    )
    recipient_employee = models.ForeignKey(
        'hr.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notification_logs',
        verbose_name='Сотрудник',
    )
    telegram_chat_id = models.BigIntegerField(null=True, blank=True)
    message_text = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    error_message = models.TextField(blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'hr'
        verbose_name = 'Лог уведомления'
        verbose_name_plural = 'Логи уведомлений'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.event_type} → {self.recipient_role} ({self.status})'
