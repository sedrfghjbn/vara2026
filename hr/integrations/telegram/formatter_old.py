"""Формирование текста Telegram-уведомлений (сценарии 1–6)."""

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


def _time_footer(payload):
    return f'🕐 {_fmt_time(payload)}'


def _fmt_email_line(email, subject=None):
    safe = _escape_html(email)
    href = f'mailto:{safe}'
    if subject:
        from urllib.parse import quote
        href = f'{href}?subject={quote(subject)}'
    return f'📧 <a href="{href}">{safe}</a>'


def _contact_hr_block(payload):
    """Сотруднику: как написать HR."""
    actor_email = payload.get('actor_email')
    actor_role = payload.get('actor_role')
    lines = ['💬 <b>Связаться с HR</b>']
    if actor_email and actor_role in ('hr_manager', 'admin'):
        lines.append(_fmt_email_line(actor_email, subject='Вопрос по HR-системе'))
        return '\n'.join(lines)

    # Fallback: if this is a training event and actor info is missing,
    # prefer the training responsible (if they are HR) to avoid listing all HR contacts.
    training_id = payload.get('training_id')
    if not actor_email and training_id:
        try:
            from hr.models import Training
            tr = Training.objects.select_related('responsible').filter(pk=training_id).first()
            if tr and tr.responsible:
                resp = tr.responsible
                if getattr(resp, 'is_superuser', False) or getattr(resp, 'role', None) == 'hr_manager':
                    lines.append(_fmt_email_line(resp.email, subject='Вопрос по HR-системе'))
                    return '\n'.join(lines)
        except Exception:
            # don't fail formatting on DB errors
            pass

    emails = collect_hr_contact_emails()
    if emails:
        for email in emails:
            lines.append(_fmt_email_line(email, subject='Вопрос по HR-системе'))
    else:
        lines.append('Контакты HR не найдены — уточните в веб-системе.')
    return '\n'.join(lines)


def _contact_employee_block(payload):
    """HR/админу: как написать сотруднику."""
    email = payload.get('email')
    employee_id = payload.get('employee_id')
    if not email and not employee_id:
        return ''

    lines = ['💬 <b>Написать сотруднику</b>']
    if email:
        name = payload.get('name') or 'сотруднику'
        lines.append(_fmt_email_line(email, subject=f'HR: {name}'))
    if employee_id:
        url = _escape_html(employee_detail_url(employee_id))
        lines.append(f'🔗 <a href="{url}">Карточка в системе</a>')
    return '\n'.join(lines)


def _contacts_block(payload, recipient_role):
    if recipient_role == 'employee':
        return _contact_hr_block(payload)
    if recipient_role in ('hr_manager', 'admin'):
        return _contact_employee_block(payload)
    return ''


def _footer_with_contacts(payload, recipient_role):
    parts = []
    contacts = _contacts_block(payload, recipient_role)
    if contacts:
        parts.append(contacts)
    parts.append(_time_footer(payload))
    return '\n\n'.join(parts)


def build_employee_payload(employee, **extra):
    """Стандартный payload для событий, связанных с сотрудником."""
    payload = {
        'employee_id': employee.id,
        'name': employee.full_name,
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
        f'Сотрудник: {_escape_html(payload.get("name"))}\n'
        f'Время: {_fmt_time(payload)}'
    )


def _format_changed_fields_block(payload):
    """Блок «Изменения:» со списком полей."""
    changes = payload.get('changed_fields') or []
    if not changes:
        return None
    lines = ['Изменения:']
    for item in changes:
        label = _escape_html(item.get('label', item.get('field', 'Поле')))
        old_val = _escape_html(item.get('old') or '—')
        new_val = _escape_html(item.get('new') or '—')
        lines.append(f'• {label}: {old_val} → {new_val}')
    return '\n'.join(lines)


def _training_dates_line(payload):
    details = (payload.get('details') or '').strip()
    if details.startswith('Даты: '):
        return details[6:].strip()
    return details


def _fmt_employee_created(payload, recipient_role):
    name = _escape_html(payload.get('name'))
    department = _escape_html(payload.get('department'))
    position = _escape_html(payload.get('position'))
    email = payload.get('email')

    if recipient_role == 'hr_manager':
        return (
            f'🆕 <b>Новый сотрудник в системе</b>\n\n'
            f'👤 {name}\n'
            f'💼 {position}\n'
            f'🏢 {department}\n\n'
            f'{_footer_with_contacts(payload, recipient_role)}'
        )
    if recipient_role == 'employee':
        return (
            f'🎉 <b>Добро пожаловать в команду!</b>\n\n'
            f'Для вас создан профиль сотрудника в HR-системе.\n\n'
            f'🏢 Отдел: {department}\n'
            f'💼 Должность: {position}\n\n'
            f'Желаем успешной работы!\n\n'
            f'{_footer_with_contacts(payload, recipient_role)}'
        )
    return _fmt_generic('Новый сотрудник', payload)


def _fmt_employee_status_changed(payload, recipient_role):
    name = _escape_html(payload.get('name'))
    old_status = _escape_html(payload.get('previous_status') or '—')
    new_status = _escape_html(payload.get('status') or '—')
    department = _escape_html(payload.get('department'))
    changes_block = _format_changed_fields_block(payload)
    status_code = payload.get('status_code')
    previous_status_code = payload.get('previous_status_code')

    if recipient_role == 'employee':
        if status_code == 'sick_leave':
            parts = [
                '🤒 <b>Вам назначен больничный</b>',
                '',
                f'🔄 Было: {old_status}',
                f'🔄 Стало: {new_status}',
            ]
            if changes_block:
                parts.extend(['', changes_block])
            parts.extend(['', 'Если это произошло по ошибке, свяжитесь с HR.'])
            text = '\n'.join(parts)
            return f'{text}\n\n{_footer_with_contacts(payload, recipient_role)}'

        if previous_status_code == 'sick_leave' and status_code == 'active':
            parts = [
                '👋 <b>Ваш больничный завершён</b>',
                '',
                'У вас закончился больничный, вы вернулись на работу.',
            ]
            if changes_block:
                parts.extend(['', changes_block])
            parts.extend(['', 'Если нужно, свяжитесь с HR.'])
            text = '\n'.join(parts)
            return f'{text}\n\n{_footer_with_contacts(payload, recipient_role)}'

        parts = [
            '📋 <b>Ваш статус изменён</b>',
            '',
            f'🔄 Было: {old_status}',
            f'🔄 Стало: {new_status}',
        ]
        if changes_block:
            parts.extend(['', changes_block])
        parts.extend(['', 'Если это произошло по ошибке, свяжитесь с HR.'])
        text = '\n'.join(parts)
        return f'{text}\n\n{_footer_with_contacts(payload, recipient_role)}'

    if status_code == 'sick_leave':
        return (
            f'🤒 <b>Сотруднику назначен больничный</b>\n\n'
            f'{name} переведён в статус «На больничном».\n\n'
            f'{_footer_with_contacts(payload, recipient_role)}'
        )

    if previous_status_code == 'sick_leave' and status_code == 'active':
        return (
            f'👋 <b>Сотрудник вернулся после больничного</b>\n\n'
            f'{name} снова активен в системе.\n\n'
            f'{_footer_with_contacts(payload, recipient_role)}'
        )

    parts = [
        '📋 <b>Изменение статуса сотрудника</b>',
        '',
        f'{name} сменил статус.',
        '',
        f'🔄 Было: {old_status}',
        f'🔄 Стало: {new_status}',
        '',
        f'🏢 {department}',
    ]
    if changes_block:
        parts.extend(['', changes_block])
    text = '\n'.join(parts)
    return f'{text}\n\n{_footer_with_contacts(payload, recipient_role)}'


def _fmt_employee_updated(payload, recipient_role):
    name = _escape_html(payload.get('name'))
    changes_block = _format_changed_fields_block(payload)
    if not changes_block:
        changes_block = (
            'Изменения:\n'
            f'• ФИО: {_escape_html(payload.get("name"))}\n'
            f'• Email: {_escape_html(payload.get("email"))}\n'
            f'• Телефон: {_escape_html(payload.get("phone"))}'
        )

    if recipient_role == 'employee':
        if payload.get('actor_role') == 'employee' or payload.get('actor_email') == payload.get('email'):
            title = '✏️ <b>Вы обновили свои данные</b>'
        else:
            title = '✏️ <b>Ваши данные обновлены</b>'
        return (
            f'{title}\n\n'
            f'{changes_block}\n\n'
            f'Если изменения внесены не вами, обратитесь в HR.\n\n'
            f'{_footer_with_contacts(payload, recipient_role)}'
        )
    return (
        f'✏️ <b>Обновлена карточка сотрудника</b>\n\n'
        f'👤 {name}\n\n'
        f'{changes_block}\n\n'
        f'{_footer_with_contacts(payload, recipient_role)}'
    )


def _fmt_employee_deleted(payload, recipient_role):
    name = _escape_html(payload.get('name'))
    actor_email = payload.get('actor_email')
    actor_line = f'Удалил: {_escape_html(actor_email)}\n\n' if actor_email else ''
    if recipient_role in ('hr_manager', 'admin'):
        return (
            f'🗑️ <b>Сотрудник удалён</b>\n\n'
            f'👤 {name}\n'
            f'{actor_line}'
            f'{_footer_with_contacts(payload, recipient_role)}'
        )
    return _fmt_generic('Сотрудник удалён', payload)


def _fmt_employee_fired(payload, recipient_role):
    name = _escape_html(payload.get('name'))
    department = _escape_html(payload.get('department'))
    position = _escape_html(payload.get('position'))

    if recipient_role == 'employee':
        return (
            f'⚠️ <b>Изменение статуса</b>\n\n'
            f'Ваш статус в HR-системе изменён на «Уволен».\n\n'
            f'Если у вас остались вопросы, обратитесь в отдел кадров.\n\n'
            f'{_footer_with_contacts(payload, recipient_role)}'
        )
    if recipient_role == 'admin':
        return (
            f'🚨 <b>Увольнение сотрудника</b>\n\n'
            f'{name} переведён в статус «Уволен».\n\n'
            f'🏢 {department}\n'
            f'💼 {position}\n\n'
            f'{_footer_with_contacts(payload, recipient_role)}'
        )
    return (
        f'🚨 <b>Кадровое изменение</b>\n\n'
        f'Сотрудник {name} переведён в статус «Уволен».\n\n'
        f'🏢 {department}\n'
        f'💼 {position}\n\n'
        f'{_footer_with_contacts(payload, recipient_role)}'
    )


def _fmt_department_changed(payload, recipient_role):
    name = _escape_html(payload.get('name'))
    old_dept = _escape_html(payload.get('old_department') or '—')
    new_dept = _escape_html(payload.get('department') or '—')
    position = _escape_html(payload.get('position'))

    if recipient_role == 'employee':
        return (
            f'🎯 <b>Вы переведены в новый отдел</b>\n\n'
            f'📍 Новый отдел: {new_dept}\n'
            f'💼 Должность: {position}\n\n'
            f'Желаем успехов на новом месте.\n\n'
            f'{_footer_with_contacts(payload, recipient_role)}'
        )
    return (
        f'🔄 <b>Перевод сотрудника</b>\n\n'
        f'{name} переведён в другой отдел.\n\n'
        f'📍 Было: {old_dept}\n'
        f'📍 Стало: {new_dept}\n\n'
        f'{_footer_with_contacts(payload, recipient_role)}'
    )


def _fmt_position_changed(payload, recipient_role):
    name = _escape_html(payload.get('name'))
    old_pos = _escape_html(payload.get('old_position') or '—')
    new_pos = _escape_html(payload.get('position') or '—')
    department = _escape_html(payload.get('department'))

    if recipient_role == 'employee':
        return (
            f'🎉 <b>Поздравляем!</b>\n\n'
            f'Ваша должность была изменена.\n\n'
            f'📌 Было: {old_pos}\n'
            f'📌 Стало: {new_pos}\n\n'
            f'{_footer_with_contacts(payload, recipient_role)}'
        )
    return (
        f'💼 <b>Изменение должности</b>\n\n'
        f'{name} получил новую должность.\n\n'
        f'📌 Было: {old_pos}\n'
        f'📌 Стало: {new_pos}\n\n'
        f'🏢 {department}\n'
        f'{_footer_with_contacts(payload, recipient_role)}'
    )


def _fmt_training_assigned(payload, recipient_role):
    dates = _escape_html(_training_dates_line(payload))
    training_id = payload.get('training_id')
    training_link = ''
    if training_id:
        try:
            url = _escape_html(__import__('hr.integrations.telegram.site_urls', fromlist=['']).training_detail_url(training_id))
            training_link = f'🔗 <a href="{url}">Открыть обучение</a>\n\n'
        except Exception:
            training_link = ''
    return (
        f'🎓 <b>Вам назначено обучение</b>\n\n'
        f'Курс: {_escape_html(payload.get("training_title"))}\n\n'
        f'📅 {dates}\n\n'
        f'{training_link}'
        f'Не забудьте пройти обучение в указанные сроки.\n\n'
        f'{_footer_with_contacts(payload, recipient_role)}'
    )


def _fmt_training_started(payload, recipient_role):
    dates = _escape_html(_training_dates_line(payload))
    if recipient_role == 'employee':
        # add training link when available
        training_id = payload.get('training_id')
        training_link = ''
        if training_id:
            try:
                url = _escape_html(__import__('hr.integrations.telegram.site_urls', fromlist=['']).training_detail_url(training_id))
                training_link = f'🔗 <a href="{url}">Открыть обучение</a>\n\n'
            except Exception:
                training_link = ''
        return (
            f'🎓 <b>Обучение началось</b>\n\n'
            f'Курс: {_escape_html(payload.get("training_title"))}\n\n'
            f'📅 {dates}\n\n'
            f'{training_link}'
            f'Удачи в обучении — следуйте указаниям и завершите задания вовремя.\n\n'
            f'{_footer_with_contacts(payload, recipient_role)}'
        )
    return (
        f'🎓 <b>Началось обучение</b>\n\n'
        f'Курс: {_escape_html(payload.get("training_title"))}\n\n'
        f'📅 {dates}\n\n'
        f'Количество участников: {payload.get("participants_count", "—")}\n\n'
        f'{_footer_with_contacts(payload, recipient_role)}'
    )


def _fmt_vacation_started(payload, recipient_role):
    name = _escape_html(payload.get('name'))
    department = _escape_html(payload.get('department'))
    changes_block = _format_changed_fields_block(payload)

    if recipient_role == 'employee':
        parts = [
            '🏖 <b>Отпуск согласован</b>',
            '',
            'Ваш отпуск успешно оформлен.',
        ]
        if changes_block:
            parts.extend(['', changes_block])
        parts.extend(['', 'Желаем хорошего отдыха!'])
        text = '\n'.join(parts)
        return f'{text}\n\n{_footer_with_contacts(payload, recipient_role)}'

    parts = [
        '🏖 <b>Сотрудник ушёл в отпуск</b>',
        '',
        f'{name} переведён в статус «В отпуске».',
        '',
        f'🏢 {department}',
    ]
    if changes_block:
        parts.extend(['', changes_block])
    text = '\n'.join(parts)
    return f'{text}\n\n{_footer_with_contacts(payload, recipient_role)}'


def _fmt_vacation_approved(payload, recipient_role):
    return (
        f'👋 <b>С возвращением!</b>\n\n'
        f'Отпуск завершён, ваш статус снова активен.\n\n'
        f'Хорошего рабочего дня!\n\n'
        f'{_footer_with_contacts(payload, recipient_role)}'
    )


def _fmt_vacation_rejected(payload, recipient_role):
    status = _escape_html(payload.get('status') or '—')
    return (
        f'❌ <b>Отпуск не согласован</b>\n\n'
        f'Заявка на отпуск была отклонена.\n\n'
        f'Текущий статус: {status}\n\n'
        f'Для уточнения причины обратитесь к HR.\n\n'
        f'{_footer_with_contacts(payload, recipient_role)}'
    )


def _fmt_generic(title, payload):
    return (
        f'<b>{_escape_html(title)}</b>\n'
        f'{_escape_html(payload.get("name"))}\n'
        f'{_time_footer(payload)}'
    )
