"""Главная клавиатура и обработчики кнопок меню HR-бота."""

from django.contrib.auth import get_user_model
from django.utils import timezone

from hr.models import Employee, Training

from .commands import resolve_linked_user

User = get_user_model()


def get_main_keyboard():
    """ReplyKeyboardMarkup главного меню."""
    return {
        'keyboard': [
            [{'text': '📄 Мой профиль'}],
            [{'text': '🎓 Мои обучения'}],
            [{'text': '📞 HR'}, {'text': 'ℹ️ Помощь'}],
        ],
        'resize_keyboard': True,
        'one_time_keyboard': False,
    }


def handle_my_profile(chat_id):
    """Обработчик кнопки «Мой профиль»."""
    user = resolve_linked_user(chat_id)
    if not user:
        return 'Аккаунт не подключён. Отправьте /start для привязки.'

    try:
        emp = user.employee_profile
    except Employee.DoesNotExist:
        return (
            '👤 <b>Мой профиль</b>\n\n'
            'У вас нет карточки сотрудника.\n'
            'Обратитесь в HR.'
        )

    status_emoji = {
        'active': '✅',
        'sick_leave': '🤒',
        'on_leave': '🏖️',
        'dismissed': '👋',
    }.get(emp.status, '📌')

    lines = [
        '👤 <b>Мой профиль</b>',
        '',
        f'<b>ФИО:</b> {emp.full_name}',
        f'<b>Отдел:</b> {emp.department.name if emp.department else "—"}',
        f'<b>Должность:</b> {emp.position.name if emp.position else "—"}',
        f'<b>Email:</b> {emp.email}',
        f'{status_emoji} <b>Статус:</b> {emp.get_status_display()}',
    ]

    if emp.phone:
        lines.append(f'<b>Телефон:</b> {emp.phone}')

    return '\n'.join(lines)


def handle_my_trainings(chat_id):
    """Обработчик кнопки «Мои обучения»."""
    user = resolve_linked_user(chat_id)
    if not user:
        return 'Аккаунт не подключён. Отправьте /start для привязки.'

    try:
        emp = user.employee_profile
    except Employee.DoesNotExist:
        if user.is_hr_manager():
            return (
                '🎓 <b>Мои обучения</b>\n\n'
                'У HR-менеджера нет личных обучений.\n'
                'Откройте раздел «Обучение» в веб-системе.'
            )
        return 'Карточка сотрудника не найдена.'

    today = timezone.now().date()
    trainings = (
        Training.objects.filter(
            participants=emp,
        )
        .exclude(status='cancelled')
        .order_by('start_date')[:10]
    )

    if not trainings:
        return (
            '🎓 <b>Мои обучения</b>\n\n'
            'Вам пока не назначены обучения.\n\n'
            'Скоро может появиться новое.'
        )

    lines = ['🎓 <b>Мои обучения</b>', '']

    for i, t in enumerate(trainings, 1):
        status_marker = 'завершено'
        if t.end_date < today:
            status_marker = '✅ завершено'
        elif t.start_date <= today <= t.end_date:
            status_marker = '🔄 идёт сейчас'
        elif t.start_date > today:
            status_marker = '⏳ ещё не началось'

        lines.append(f'<b>{i}. {t.title}</b>')
        lines.append(
            f'📅 {t.start_date.strftime("%d.%m")} — {t.end_date.strftime("%d.%m.%Y")}'
        )
        lines.append(f'{status_marker}')
        lines.append('')

    return '\n'.join(lines).rstrip()


def handle_hr_contact(chat_id):
    """Обработчик кнопки «HR»."""
    user = resolve_linked_user(chat_id)
    
    from .contacts import collect_hr_contact_emails
    
    emails = collect_hr_contact_emails()
    
    lines = [
        '👨‍💼 <b>Контакты HR</b>',
        '',
    ]

    if emails:
        for email in emails:
            safe = email.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            lines.append(f'📧 <a href="mailto:{safe}">{safe}</a>')
    else:
        lines.append('Контакты HR не найдены.')
        lines.append('Обратитесь в веб-систему.')

    lines.append('')
    lines.append('Если у вас срочный вопрос, напишите напрямую.')

    return '\n'.join(lines)


def handle_help(chat_id):
    """Обработчик кнопки «Помощь»."""
    return (
        'ℹ️ <b>Справка</b>\n\n'
        '<b>📄 Мой профиль</b> — информация о вас\n'
        '<b>🎓 Мои обучения</b> — назначенные курсы\n'
        '<b>📞 HR</b> — контакты отдела кадров\n\n'
        '<b>Команды:</b>\n'
        '/status — данные аккаунта\n'
        '/mytrainings — обучения\n'
        '/help — эта справка\n\n'
        'Уведомления приходят автоматически.'
    )


def process_menu_button(chat_id, button_text, client):
    """Обработка нажатия кнопки главного меню."""
    handlers = {
        '📄 Мой профиль': handle_my_profile,
        '🎓 Мои обучения': handle_my_trainings,
        '📞 HR': handle_hr_contact,
        'ℹ️ Помощь': handle_help,
    }

    handler = handlers.get(button_text)
    if handler:
        text = handler(chat_id)
        client.send_message(
            chat_id,
            text,
            reply_markup=get_main_keyboard(),
            parse_mode='HTML',
        )
        return True

    return False
