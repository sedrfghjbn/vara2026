"""Переработанный форматер Telegram-уведомлений: дружелюбный корпоративный стиль."""

from django.utils import timezone

from .contacts import collect_hr_contact_emails
from .registry import get_event_definition
from .site_urls import employee_detail_url


def _escape_html(value):
    if value is None:
        return '—'
    text = str(value)
    return (
        text.replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
    )


def _fmt_time(payload):
    raw = payload.get('timestamp')
    if not raw:
        return timezone.localtime(timezone.now()).strftime('%d.%m.%Y %H:%M')
    try:
        from django.utils.dateparse import parse_datetime
        dt = parse_datetime(str(raw))
        if dt:
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            return timezone.localtime(dt).strftime('%d.%m.%Y %H:%M')
    except Exception:
        pass
    return _escape_html(raw)


def _fmt_email_line(email, subject=None):
    safe = _escape_html(email)
    href = f'mailto:{safe}'
    if subject:
        from urllib.parse import quote
        href = f'{href}?subject={quote(subject)}'
    return f'📧 <a href="{href}">{safe}</a>'


def _hr_contact_quick(payload):
    """Быстрый контакт HR для сотрудника."""
    actor_email = payload.get('actor_email')
    actor_role = payload.get('actor_role')
    
    if actor_email and actor_role in ('hr_manager', 'admin'):
        return _fmt_email_line(actor_email)

    training_id = payload.get('training_id')
    if not actor_email and training_id:
        try:
            from hr.models import Training
            tr = Training.objects.select_related('responsible').filter(pk=training_id).first()
            if tr and tr.responsible:
                resp = tr.responsible
                if getattr(resp, 'is_superuser', False) or getattr(resp, 'role', None) == 'hr_manager':
                    return _fmt_email_line(resp.email)
        except Exception:
            pass

    emails = collect_hr_contact_emails()
    if emails:
        return _fmt_email_line(emails[0])
    
    return '👨‍💼 HR-служба'


def _footer_quick(payload):
    """Минималистичный footer."""
    return f'🕐 {_fmt_time(payload)}'


def build_employee_payload(employee, **extra):
    """Стандартный payload для событий, связанных с сотрудником."""
    payload = {
        'employee_id': employee.id,
        'name': employee.full_name,
        'first_name': employee.first_name,
        'last_name': employee.last_name,
        'department': employee.department.name if employee.department else None,
        'position': employee.position.name if employee.position else None,
        'email': employee.email,
        'phone': employee.phone,
        'status': employee.get_status_display(),
        'status_code': employee.status,
        'timestamp': timezone.now().isoformat(),
    }
    if hasattr(employee, '_updated_by_user') and employee._updated_by_user is not None:
        actor = employee._updated_by_user
        payload['actor_email'] = actor.email
        payload['actor_role'] = 'admin' if getattr(actor, 'is_superuser', False) else 'hr_manager' if getattr(actor, 'role', None) == 'hr_manager' else 'employee'
        payload['actor_name'] = getattr(actor, 'get_full_name', lambda: None)() or getattr(actor, 'username', None)
    payload.update(extra)
    return payload


def format_notification(event_type, payload, recipient_role):
    """Текст уведомления по событию и роли получателя."""
    formatters = {
        'employee_created': _fmt_employee_created,
        'employee_updated': _fmt_employee_updated,
        'employee_deleted': _fmt_employee_deleted,
        'employee_fired': _fmt_employee_fired,
        'department_changed': _fmt_department_changed,
        'position_changed': _fmt_position_changed,
        'training_assigned': _fmt_training_assigned,
        'training_started': _fmt_training_started,
        'vacation_started': _fmt_vacation_started,
        'vacation_approved': _fmt_vacation_approved,
        'vacation_rejected': _fmt_vacation_rejected,
        'employee_status_changed': _fmt_employee_status_changed,
    }
    formatter = formatters.get(event_type)
    if formatter:
        return formatter(payload, recipient_role)

    definition = get_event_definition(event_type)
    label = definition.label if definition else event_type
    return (
        f'<b>{_escape_html(label)}</b>\n'
        f'{_escape_html(payload.get("name"))}\n'
        f'{_footer_quick(payload)}'
    )


def _changes_block(payload):
    """Блок изменённых полей."""
    changes = payload.get('changed_fields') or []
    if not changes:
        return None
    
    lines = []
    for item in changes:
        label = _escape_html(item.get('label', item.get('field', 'Поле')))
        old_val = _escape_html(item.get('old') or '—')
        new_val = _escape_html(item.get('new') or '—')
        lines.append(f'{label}: {old_val} → {new_val}')
    
    return '\n'.join(lines)


# ============ EMPLOYEE CREATED ============

def _fmt_employee_created(payload, recipient_role):
    name = _escape_html(payload.get('name'))
    department = _escape_html(payload.get('department') or '—')
    position = _escape_html(payload.get('position') or '—')

    if recipient_role == 'employee':
        return (
            f'👋 <b>Добро пожаловать в команду!</b>\n\n'
            f'Ваш профиль создан в системе.\n\n'
            f'🏢 {department}\n'
            f'💼 {position}\n\n'
            f'Удачи в работе!\n\n'
            f'{_footer_quick(payload)}'
        )
    
    return (
        f'👤 <b>Новый сотрудник</b>\n\n'
        f'{name}\n'
        f'💼 {position} • 🏢 {department}\n\n'
        f'{_footer_quick(payload)}'
    )


# ============ EMPLOYEE UPDATED ============

def _fmt_employee_updated(payload, recipient_role):
    name = _escape_html(payload.get('name'))
    changes = _changes_block(payload)

    if recipient_role == 'employee':
        if payload.get('actor_email') == payload.get('email'):
            title = 'Профиль обновлён'
        else:
            title = 'Данные обновлены'
        
        text = f'✏️ <b>{title}</b>'
        if changes:
            text += f'\n\n{changes}'
        text += f'\n\n{_footer_quick(payload)}'
        return text
    
    return (
        f'✏️ <b>Обновление профиля</b>\n\n'
        f'{name}\n'
        f'{changes or "Изменены контактные данные"}\n\n'
        f'{_footer_quick(payload)}'
    )


# ============ EMPLOYEE FIRED ============

def _fmt_employee_fired(payload, recipient_role):
    name = _escape_html(payload.get('name'))
    department = _escape_html(payload.get('department') or '—')

    if recipient_role == 'employee':
        return (
            f'👋 <b>Изменение статуса</b>\n\n'
            f'Вы уволены из компании.\n'
            f'Текущий статус: Уволен\n\n'
            f'Благодарим за работу!'
        )
    
    return (
        f'👋 <b>Сотрудник уволен</b>\n\n'
        f'{name}\n'
        f'🏢 {department}\n\n'
        f'{_footer_quick(payload)}'
    )


# ============ EMPLOYEE STATUS CHANGED ============

def _fmt_employee_status_changed(payload, recipient_role):
    name = _escape_html(payload.get('name'))
    old_status = _escape_html(payload.get('previous_status') or '—')
    new_status = _escape_html(payload.get('status') or '—')
    department = _escape_html(payload.get('department') or '—')
    status_code = payload.get('status_code')
    previous_status_code = payload.get('previous_status_code')
    changes = _changes_block(payload)

    # Sick leave start
    if status_code == 'sick_leave':
        if recipient_role == 'employee':
            text = '🤒 <b>Больничный оформлен</b>\n\n'
            if changes:
                text += f'{changes}\n\n'
            text += f'Ваш текущий статус: На больничном\n\n'
            text += 'Если нужна помощь, свяжитесь с HR.'
            return text
        
        return (
            f'🤒 <b>Больничный</b>\n\n'
            f'{name}\n'
            f'🏢 {department}\n\n'
            f'{_footer_quick(payload)}'
        )

    # Sick leave return
    if previous_status_code == 'sick_leave' and status_code == 'active':
        if recipient_role == 'employee':
            text = '👋 <b>Больничный завершён</b>\n\n'
            text += 'Добро пожаловать обратно на работу!\n\n'
            if changes:
                text += f'{changes}\n\n'
            text += f'{_footer_quick(payload)}'
            return text
        
        return (
            f'👋 <b>Возврат с больничного</b>\n\n'
            f'{name}\n'
            f'Статус: Работает\n\n'
            f'{_footer_quick(payload)}'
        )

    # Other status changes
    if recipient_role == 'employee':
        text = f'📋 <b>Статус изменён</b>\n\n'
        text += f'Было: {old_status}\n'
        text += f'Стало: {new_status}\n'
        if changes:
            text += f'\n{changes}\n'
        text += f'\n{_footer_quick(payload)}'
        return text
    
    return (
        f'📋 <b>Изменение статуса</b>\n\n'
        f'{name}\n'
        f'{old_status} → {new_status}\n'
        f'🏢 {department}\n\n'
        f'{_footer_quick(payload)}'
    )


# ============ DEPARTMENT CHANGED ============

def _fmt_department_changed(payload, recipient_role):
    name = _escape_html(payload.get('name'))
    old_dept = _escape_html(payload.get('old_department') or '—')
    new_dept = _escape_html(payload.get('department') or '—')
    position = _escape_html(payload.get('position') or '—')

    if recipient_role == 'employee':
        return (
            f'🏢 <b>Перевод в другой отдел</b>\n\n'
            f'Новый отдел: {new_dept}\n'
            f'Должность: {position}\n\n'
            f'Успехов на новом месте!\n\n'
            f'{_footer_quick(payload)}'
        )
    
    return (
        f'🔄 <b>Перевод</b>\n\n'
        f'{name}\n'
        f'{old_dept} → {new_dept}\n\n'
        f'{_footer_quick(payload)}'
    )


# ============ POSITION CHANGED ============

def _fmt_position_changed(payload, recipient_role):
    name = _escape_html(payload.get('name'))
    old_pos = _escape_html(payload.get('old_position') or '—')
    new_pos = _escape_html(payload.get('position') or '—')
    department = _escape_html(payload.get('department') or '—')

    if recipient_role == 'employee':
        return (
            f'🎉 <b>Новая должность</b>\n\n'
            f'Поздравляем!\n\n'
            f'Было: {old_pos}\n'
            f'Стало: {new_pos}\n\n'
            f'{_footer_quick(payload)}'
        )
    
    return (
        f'💼 <b>Изменение должности</b>\n\n'
        f'{name}\n'
        f'{old_pos} → {new_pos}\n'
        f'🏢 {department}\n\n'
        f'{_footer_quick(payload)}'
    )


# ============ TRAINING ASSIGNED ============

def _fmt_training_assigned(payload, recipient_role):
    title = _escape_html(payload.get('training_title') or 'Обучение')
    dates = _escape_html(payload.get('details') or '—')

    return (
        f'🎓 <b>Вам назначено обучение</b>\n\n'
        f'{title}\n'
        f'{dates}\n\n'
        f'Удачи в учёбе!\n\n'
        f'{_footer_quick(payload)}'
    )


# ============ TRAINING STARTED ============

def _fmt_training_started(payload, recipient_role):
    title = _escape_html(payload.get('training_title') or 'Обучение')
    dates = _escape_html(payload.get('details') or '—')

    if recipient_role == 'employee':
        return (
            f'🎓 <b>Обучение началось</b>\n\n'
            f'{title}\n'
            f'{dates}\n\n'
            f'Приступайте к работе!'
        )
    
    count = payload.get('participants_count', '—')
    return (
        f'🎓 <b>Запущено обучение</b>\n\n'
        f'{title}\n'
        f'{dates}\n'
        f'Участников: {count}\n\n'
        f'{_footer_quick(payload)}'
    )


# ============ VACATION STARTED ============

def _fmt_vacation_started(payload, recipient_role):
    name = _escape_html(payload.get('name'))
    department = _escape_html(payload.get('department') or '—')
    changes = _changes_block(payload)

    if recipient_role == 'employee':
        text = '🏖️ <b>Отпуск одобрен</b>\n\n'
        text += 'Хорошего отдыха!\n'
        if changes:
            text += f'\n{changes}\n'
        text += f'\n{_footer_quick(payload)}'
        return text
    
    return (
        f'🏖️ <b>Сотрудник в отпуске</b>\n\n'
        f'{name}\n'
        f'🏢 {department}\n\n'
        f'{_footer_quick(payload)}'
    )


# ============ VACATION APPROVED ============

def _fmt_vacation_approved(payload, recipient_role):
    name = _escape_html(payload.get('name'))
    changes = _changes_block(payload)

    if recipient_role == 'employee':
        text = '👋 <b>С возвращением!</b>\n\n'
        text += 'Отпуск завершён, вы вернулись на работу.\n'
        if changes:
            text += f'\n{changes}\n'
        text += f'\n{_footer_quick(payload)}'
        return text
    
    return (
        f'👋 <b>Возврат с отпуска</b>\n\n'
        f'{name}\n'
        f'Статус: Работает\n\n'
        f'{_footer_quick(payload)}'
    )


# ============ VACATION REJECTED ============

def _fmt_vacation_rejected(payload, recipient_role):
    status = _escape_html(payload.get('status') or '—')

    return (
        f'❌ <b>Отпуск не одобрен</b>\n\n'
        f'Текущий статус: {status}\n\n'
        f'Обратитесь в HR для подробной информации.\n\n'
        f'{_footer_quick(payload)}'
    )


# ============ EMPLOYEE DELETED ============

def _fmt_employee_deleted(payload, recipient_role):
    name = _escape_html(payload.get('name'))
    actor_email = payload.get('actor_email')
    actor_line = f'\nУдалил: {_escape_html(actor_email)}' if actor_email else ''

    if recipient_role in ('hr_manager', 'admin'):
        return (
            f'🗑️ <b>Сотрудник удалён</b>\n\n'
            f'{name}{actor_line}\n\n'
            f'{_footer_quick(payload)}'
        )
    
    return (
        f'🗑️ <b>Запись удалена</b>\n\n'
        f'{name}\n\n'
        f'{_footer_quick(payload)}'
    )
