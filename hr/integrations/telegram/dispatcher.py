"""Role-based маршрутизация событий к получателям Telegram."""

import logging
from typing import List

from django.contrib.auth import get_user_model
from django.db.models import Q

from hr.models import Employee

from .models import EmployeeTelegramLink, UserTelegramLink
from .registry import get_event_definition, registered_event_types
from .service import NotificationService, SendTarget

logger = logging.getLogger('hr.integrations.telegram')
User = get_user_model()


class EventDispatcher:
    """Принимает событие и направляет уведомления целевой аудитории."""

    _service = None

    @classmethod
    def get_service(cls):
        if cls._service is None:
            cls._service = NotificationService()
        return cls._service

    @classmethod
    def dispatch(cls, event_type: str, payload: dict):
        """
        Точка входа для signals и бизнес-кода.
        Не выбрасывает исключения — ошибки Telegram не ломают Django.
        """
        try:
            definition = get_event_definition(event_type)
            if not definition:
                logger.warning('Unknown event type: %s', event_type)
                return []

            targets = cls._resolve_targets(definition.audiences, payload)
            if not targets:
                logger.info('No Telegram targets for event %s', event_type)
                return []

            return cls.get_service().send_bulk(event_type, targets, payload)
        except Exception as exc:
            logger.exception('Event dispatch failed for %s: %s', event_type, exc)
            return []

    @classmethod
    def _resolve_targets(cls, audiences, payload) -> List[SendTarget]:
        targets = []
        seen_chat_ids = set()
        employee = cls._get_employee_from_payload(payload)
        exclude_user_id = employee.user_id if employee else None

        for audience in audiences:
            if audience == 'employee':
                targets.extend(cls._employee_targets(payload, seen_chat_ids))
            elif audience == 'hr_manager':
                targets.extend(cls._hr_manager_targets(seen_chat_ids, exclude_user_id))
            elif audience == 'admin':
                targets.extend(cls._admin_targets(seen_chat_ids, exclude_user_id))

        return targets

    @classmethod
    def _add_target(cls, targets, seen, chat_id, role, user=None, employee=None):
        if chat_id in seen:
            return
        seen.add(chat_id)
        targets.append(SendTarget(
            chat_id=chat_id,
            recipient_role=role,
            user=user,
            employee=employee,
        ))

    @classmethod
    def _employee_targets(cls, payload, seen):
        targets = []
        employee = cls._get_employee_from_payload(payload)
        if not employee:
            return targets

        link = EmployeeTelegramLink.objects.filter(
            employee=employee,
            is_active=True,
        ).first()
        if link:
            cls._add_target(
                targets, seen, link.telegram_chat_id,
                'employee', user=employee.user, employee=employee,
            )
            return targets

        if employee.user_id:
            user_link = UserTelegramLink.objects.filter(
                user_id=employee.user_id,
                is_active=True,
            ).first()
            if user_link:
                cls._add_target(
                    targets, seen, user_link.telegram_chat_id,
                    'employee', user=employee.user, employee=employee,
                )
        return targets

    @classmethod
    def _hr_manager_targets(cls, seen, exclude_user_id=None):
        targets = []
        hr_users = User.objects.filter(is_active=True).filter(
            models_q_hr_manager(),
        )
        if exclude_user_id:
            hr_users = hr_users.exclude(pk=exclude_user_id)
        for user in hr_users:
            link = UserTelegramLink.objects.filter(user=user, is_active=True).first()
            if link:
                cls._add_target(targets, seen, link.telegram_chat_id, 'hr_manager', user=user)
        return targets

    @classmethod
    def _admin_targets(cls, seen, exclude_user_id=None):
        targets = []
        admins = User.objects.filter(is_active=True, is_superuser=True)
        if exclude_user_id:
            admins = admins.exclude(pk=exclude_user_id)
        for user in admins:
            link = UserTelegramLink.objects.filter(user=user, is_active=True).first()
            if link:
                cls._add_target(targets, seen, link.telegram_chat_id, 'admin', user=user)
        return targets

    @classmethod
    def _get_employee_from_payload(cls, payload):
        employee_id = payload.get('employee_id')
        if employee_id:
            return Employee.objects.filter(pk=employee_id).select_related(
                'department', 'position', 'user',
            ).first()
        return None


def models_q_hr_manager():
    """Как User.is_hr_manager(): роль HR или суперпользователь Django."""
    return Q(role='hr_manager') | Q(is_superuser=True)


def emit_event(event_type: str, payload: dict):
    """Публичный API для ручного вызова событий из views/команд."""
    if event_type not in registered_event_types():
        raise ValueError(f'Unknown event type: {event_type}')
    return EventDispatcher.dispatch(event_type, payload)
