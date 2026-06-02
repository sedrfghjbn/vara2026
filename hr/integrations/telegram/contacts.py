"""Контакты HR и сотрудников для Telegram-уведомлений."""

from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


def collect_hr_contact_emails():
    """Активные email HR-менеджеров и администраторов."""
    return list(
        User.objects.filter(is_active=True)
        .filter(Q(role='hr_manager') | Q(is_superuser=True))
        .exclude(email='')
        .order_by('email')
        .values_list('email', flat=True)
        .distinct()
    )
