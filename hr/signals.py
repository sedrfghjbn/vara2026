"""Django signals → Event Dispatcher (Telegram-уведомления по типу изменения)."""

import logging

from django.db.models.signals import m2m_changed, post_save, pre_save
from django.dispatch import receiver

from hr.models import Employee, Training

from hr.integrations.telegram.dispatcher import EventDispatcher
from hr.integrations.telegram.formatter import build_employee_payload

logger = logging.getLogger('hr.integrations.telegram')

STATUS_LABELS = dict(Employee.STATUS_CHOICES)


def _status_label(code):
    if not code:
        return '—'
    return STATUS_LABELS.get(code, code)


def _status_change_already_handled(prev_status, new_status):
    """Смены статуса, для которых уже есть отдельные события."""
    if prev_status != 'dismissed' and new_status == 'dismissed':
        return True
    if new_status == 'on_leave' and prev_status != 'on_leave':
        return True
    if prev_status == 'on_leave' and new_status == 'active':
        return True
    if prev_status == 'on_leave' and new_status not in ('on_leave', 'active', 'dismissed'):
        return True
    return False


# «Карточка обновлена» — контактные/личные поля, не статус, отдел и должность
PROFILE_FIELDS = (
    'first_name', 'last_name', 'middle_name', 'email', 'phone', 'date_of_birth',
)

PROFILE_FIELD_LABELS = {
    'first_name': 'Имя',
    'last_name': 'Фамилия',
    'middle_name': 'Отчество',
    'email': 'Email',
    'phone': 'Телефон',
    'date_of_birth': 'Дата рождения',
}


def _profile_field_display(field_name, value):
    if value is None or value == '':
        return '—'
    if field_name == 'date_of_birth' and hasattr(value, 'strftime'):
        return value.strftime('%d.%m.%Y')
    return value


@receiver(pre_save, sender=Employee)
def employee_pre_save(sender, instance, **kwargs):
    if not instance.pk:
        instance._prev_status = None
        instance._prev_department_id = None
        instance._prev_position_id = None
        instance._profile_changed = False
        instance._profile_changed_fields = []
        return
    try:
        previous = Employee.objects.only(
            'status',
            'department_id',
            'position_id',
            *PROFILE_FIELDS,
        ).get(pk=instance.pk)
        instance._prev_status = previous.status
        instance._prev_department_id = previous.department_id
        instance._prev_position_id = previous.position_id
        changed_fields = []
        for field in PROFILE_FIELDS:
            old_value = getattr(previous, field)
            new_value = getattr(instance, field)
            if old_value != new_value:
                changed_fields.append({
                    'field': field,
                    'label': PROFILE_FIELD_LABELS.get(field, field),
                    'old': _profile_field_display(field, old_value),
                    'new': _profile_field_display(field, new_value),
                })
        instance._profile_changed_fields = changed_fields
        instance._profile_changed = bool(changed_fields)
    except Employee.DoesNotExist:
        instance._prev_status = None
        instance._prev_department_id = None
        instance._prev_position_id = None
        instance._profile_changed = False
        instance._profile_changed_fields = []


@receiver(post_save, sender=Employee)
def employee_post_save(sender, instance, created, **kwargs):
    try:
        payload = build_employee_payload(
            instance,
            change_type='created' if created else 'updated',
        )

        if created:
            EventDispatcher.dispatch('employee_created', payload)
            return

        prev_status = getattr(instance, '_prev_status', None)
        prev_department_id = getattr(instance, '_prev_department_id', None)
        prev_position_id = getattr(instance, '_prev_position_id', None)
        profile_changed = getattr(instance, '_profile_changed', False)
        changed_fields = getattr(instance, '_profile_changed_fields', [])
        other_event_dispatched = False

        def _add_profile_changes(payload):
            if profile_changed:
                payload['changed_fields'] = changed_fields
                payload['profile_update_included'] = True
            return payload

        # Увольнение
        if prev_status != 'dismissed' and instance.status == 'dismissed':
            EventDispatcher.dispatch('employee_fired', _add_profile_changes({
                **payload,
                'change_type': 'fired',
            }))
            other_event_dispatched = True

        # Отправление в отпуск
        vacation_started = instance.status == 'on_leave' and prev_status != 'on_leave'
        if vacation_started:
            vacation_payload = _add_profile_changes({
                **payload,
                'change_type': 'vacation_started',
            })
            EventDispatcher.dispatch('vacation_started', vacation_payload)
            other_event_dispatched = True

        # Возврат из отпуска на работу
        if prev_status == 'on_leave' and instance.status == 'active':
            EventDispatcher.dispatch('vacation_approved', _add_profile_changes({
                **payload,
                'change_type': 'vacation_approved',
            }))
            other_event_dispatched = True

        # Отпуск прерван / отменён (из «В отпуске» в другой статус, кроме увольнения)
        if prev_status == 'on_leave' and instance.status not in ('on_leave', 'active', 'dismissed'):
            EventDispatcher.dispatch('vacation_rejected', _add_profile_changes({
                **payload,
                'change_type': 'vacation_rejected',
                'previous_status': 'В отпуске',
            }))
            other_event_dispatched = True

        # Больничный ↔ работает и прочие смены статуса
        if (
            prev_status
            and prev_status != instance.status
            and not _status_change_already_handled(prev_status, instance.status)
        ):
            EventDispatcher.dispatch('employee_status_changed', _add_profile_changes({
                **payload,
                'change_type': 'status_changed',
                'previous_status': _status_label(prev_status),
                'previous_status_code': prev_status,
            }))
            other_event_dispatched = True

        # Перевод в другой отдел
        if prev_department_id != instance.department_id:
            from hr.models import Department
            old_department_name = '—'
            if prev_department_id:
                dept = Department.objects.filter(pk=prev_department_id).first()
                old_department_name = dept.name if dept else str(prev_department_id)

            EventDispatcher.dispatch('department_changed', _add_profile_changes({
                **payload,
                'change_type': 'department_changed',
                'old_department': old_department_name,
            }))
            other_event_dispatched = True

        # Смена должности
        if prev_position_id != instance.position_id:
            from hr.models import Position
            old_position_name = '—'
            if prev_position_id:
                pos = Position.objects.filter(pk=prev_position_id).first()
                old_position_name = pos.name if pos else str(prev_position_id)

            EventDispatcher.dispatch('position_changed', _add_profile_changes({
                **payload,
                'change_type': 'position_changed',
                'old_position': old_position_name,
            }))
            other_event_dispatched = True

        # Имя, фамилия, email, телефон — отдельное уведомление
        if profile_changed and not other_event_dispatched:
            EventDispatcher.dispatch('employee_updated', {
                **payload,
                'change_type': 'profile_updated',
                'changed_fields': changed_fields,
            })

    except Exception as exc:
        logger.exception('employee_post_save signal error: %s', exc)


@receiver(pre_save, sender=Training)
def training_pre_save(sender, instance, **kwargs):
    # track previous status to detect transitions to in_progress
    if not instance.pk:
        instance._prev_status = None
        return
    try:
        previous = Training.objects.only('status').get(pk=instance.pk)
        instance._prev_status = previous.status
    except Training.DoesNotExist:
        instance._prev_status = None


@receiver(post_save, sender=Training)
def training_post_save(sender, instance, created, **kwargs):
    """Handle automatic dispatch when a training moves to in_progress."""
    try:
        prev_status = getattr(instance, '_prev_status', None)
        # start notifications when status changed to in_progress
        if prev_status != 'in_progress' and instance.status == 'in_progress':
            participants = instance.participants.select_related('department', 'position').all()
            def _fmt(d):
                try:
                    return d.strftime('%d.%m.%Y') if d else '—'
                except Exception:
                    return str(d)

            for employee in participants:
                payload = build_employee_payload(
                    employee,
                    training_title=instance.title,
                    training_id=instance.pk,
                    details=f'Даты: {_fmt(instance.start_date)} — {_fmt(instance.end_date)}',
                    participants_count=participants.count(),
                )
                # include actor info when available (manual start)
                if hasattr(instance, '_started_by_user') and instance._started_by_user is not None:
                    actor = instance._started_by_user
                    payload['actor_email'] = actor.email
                    payload['actor_role'] = 'admin' if getattr(actor, 'is_superuser', False) else 'hr_manager' if getattr(actor, 'role', None) == 'hr_manager' else 'employee'
                    payload['actor_name'] = getattr(actor, 'get_full_name', lambda: None)() or getattr(actor, 'username', None)
                EventDispatcher.dispatch('training_started', payload)

    except Exception as exc:
        logger.exception('training_post_save signal error: %s', exc)


@receiver(m2m_changed, sender=Training.participants.through)
def training_participants_changed(sender, instance, action, pk_set, **kwargs):
    """5. Назначение обучения."""
    if action != 'post_add' or not pk_set:
        return
    try:
        def _fmt(d):
            try:
                return d.strftime('%d.%m.%Y') if d else '—'
            except Exception:
                return str(d)

        for employee_id in pk_set:
            employee = Employee.objects.select_related('department', 'position').filter(
                pk=employee_id,
            ).first()
            if not employee:
                continue
            payload = build_employee_payload(
                employee,
                training_title=instance.title,
                training_id=instance.pk,
                details=f'Даты: {_fmt(instance.start_date)} — {_fmt(instance.end_date)}',
            )
            EventDispatcher.dispatch('training_assigned', payload)
    except Exception as exc:
        logger.exception('training_participants_changed signal error: %s', exc)
