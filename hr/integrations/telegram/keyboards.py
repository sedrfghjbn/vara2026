"""Inline-клавиатуры для уведомлений Telegram: дружелюбные и контекстные."""

from .site_urls import (
    employee_detail_url,
    employees_list_url,
    profile_url,
    training_detail_url,
    trainings_list_url,
)


def _url_button(text, url):
    return {'text': text, 'url': url}


def _callback_button(text, callback_data):
    return {'text': text, 'callback_data': callback_data}


def _keyboard(rows):
    return {'inline_keyboard': rows}


def build_event_keyboard(event_type, payload, recipient_role):
    """Inline-клавиатуры под событие и роль получателя."""
    employee_id = payload.get('employee_id')
    training_id = payload.get('training_id')

    # Новый сотрудник
    if event_type == 'employee_created':
        if recipient_role == 'hr_manager' and employee_id:
            return _keyboard([
                [_url_button('👤 Карточка', employee_detail_url(employee_id))],
                [_url_button('📋 Все сотрудники', employees_list_url())],
            ])
        if recipient_role == 'employee':
            return _keyboard([[_url_button('📄 Мой профиль', profile_url())]])

    # Изменение статуса / больничный
    if event_type == 'employee_status_changed':
        if recipient_role == 'employee':
            return _keyboard([[_url_button('📄 Профиль', profile_url())]])
        if recipient_role == 'hr_manager' and employee_id:
            return _keyboard([[_url_button('👤 Карточка', employee_detail_url(employee_id))]])

    # Обновление профиля
    if event_type == 'employee_updated':
        if recipient_role == 'hr_manager' and employee_id:
            return _keyboard([[_url_button('👤 Карточка', employee_detail_url(employee_id))]])
        if recipient_role == 'employee':
            return _keyboard([[_url_button('📄 Профиль', profile_url())]])

    # Увольнение
    if event_type == 'employee_fired':
        if recipient_role in ('hr_manager', 'admin') and employee_id:
            return _keyboard([[_url_button('👤 Карточка', employee_detail_url(employee_id))]])
        if recipient_role == 'employee':
            return _keyboard([[_url_button('📄 Профиль', profile_url())]])

    # Перевод в отдел / смена должности
    if event_type in ('department_changed', 'position_changed'):
        if recipient_role == 'employee':
            return _keyboard([[_url_button('📄 Профиль', profile_url())]])
        if recipient_role == 'hr_manager' and employee_id:
            return _keyboard([[_url_button('👤 Карточка', employee_detail_url(employee_id))]])
        return None

    # Обучение назначено
    if event_type == 'training_assigned' and recipient_role == 'employee':
        rows = []
        if training_id:
            rows.append([_url_button('🎓 Открыть', training_detail_url(training_id))])
        rows.append([_url_button('📚 Все обучения', trainings_list_url())])
        return _keyboard(rows)

    # Обучение началось
    if event_type == 'training_started':
        if recipient_role == 'employee' and training_id:
            return _keyboard([[_url_button('🎓 Открыть', training_detail_url(training_id))]])
        if recipient_role == 'hr_manager' and training_id:
            return _keyboard([[_url_button('🎓 Обучение', training_detail_url(training_id))]])

    # Отпуск / больничный
    if event_type in (
        'vacation_started',
        'vacation_approved',
        'vacation_rejected',
    ):
        if recipient_role == 'employee':
            return _keyboard([[_url_button('📄 Профиль', profile_url())]])
        if recipient_role == 'hr_manager' and employee_id:
            return _keyboard([[_url_button('👤 Карточка', employee_detail_url(employee_id))]])

    return None
