"""Команды Telegram-бота: /status, /mytrainings, /help."""

from django.contrib.auth import get_user_model
from django.utils import timezone

from hr.models import Employee, Training

from .models import UserTelegramLink

User = get_user_model()

ROLE_LABELS = {
    'hr_manager': 'HR-менеджер',
    'employee': 'Сотрудник',
}


def resolve_linked_user(chat_id):
    link = UserTelegramLink.objects.filter(
        telegram_chat_id=chat_id,
        is_active=True,
    ).select_related('user').first()
    return link.user if link else None


def _user_role_label(user):
    if user.is_superuser:
        return 'Администратор'
    return ROLE_LABELS.get(user.role, user.get_role_display())


def _training_schedule_marker(training, today):
    if training.end_date < today:
        return 'завершено'
    if training.start_date <= today <= training.end_date:
        return 'идёт сейчас'
    if training.start_date > today:
        return 'скоро'
    return training.get_status_display()


def cmd_status(chat_id):
    user = resolve_linked_user(chat_id)
    if not user:
        return (
            'Telegram ещё не привязан.\n'
            'Отправьте /start и введите код из раздела «Профиль» HR-системы.'
        )

    full_name = user.get_full_name() or user.username
    lines = [
        '📋 Информация о подключении',
        '',
        f'👤 {full_name}',
        f'📧 {user.email}',
        f'🔐 Роль: {_user_role_label(user)}',
        '',
        '✅ Уведомления включены',
    ]

    try:
        employee = user.employee_profile
        lines.extend([
            '',
            f'💼 Должность: {employee.position.name if employee.position else "—"}',
            f'📌 Статус: {employee.get_status_display()}',
        ])
    except Employee.DoesNotExist:
        pass

    return '\n'.join(lines)


def cmd_help():
    return (
        '🤖 HR-бот\n\n'
        'Доступные команды:\n\n'
        '• /status — информация об аккаунте\n'
        '• /mytrainings — мои обучения\n'
        '• /help — список команд\n\n'
        'После привязки аккаунта уведомления приходят автоматически.'
    )


def cmd_mytrainings(chat_id):
    user = resolve_linked_user(chat_id)
    if not user:
        return (
            'Сначала привяжите аккаунт: /start и код из профиля HR-системы.'
        )

    try:
        employee = user.employee_profile
    except Employee.DoesNotExist:
        if user.is_hr_manager():
            return (
                'У вашего аккаунта нет карточки сотрудника.\n'
                'Команда /mytrainings показывает обучения участника.\n'
                'Откройте раздел «Обучение» в веб-системе.'
            )
        return 'Карточка сотрудника не найдена. Обратитесь к HR.'

    today = timezone.now().date()
    trainings = (
        Training.objects.filter(participants=employee)
        .exclude(status='cancelled')
        .order_by('start_date')[:5]
    )

    if not trainings:
        return (
            '🎓 Обучения пока не назначены\n\n'
            'Когда HR назначит обучение, информация появится здесь.'
        )

    lines = ['🎓 Ваши обучения', '']
    for t in trainings:
        marker = _training_schedule_marker(t, today)
        lines.append(f'• {t.title}')
        lines.append(
            f'📅 {t.start_date.strftime("%d.%m.%Y")} — '
            f'{t.end_date.strftime("%d.%m.%Y")}'
        )
        lines.append(f'Статус: {marker}')
        lines.append('')
    return '\n'.join(lines).rstrip()

