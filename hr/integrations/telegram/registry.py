"""Реестр событий Telegram-бота (только утверждённые сценарии)."""

from dataclasses import dataclass
from typing import FrozenSet, Optional, Tuple


@dataclass(frozen=True)
class EventDefinition:
    event_type: str
    label: str
    audiences: Tuple[str, ...]
    category: str


# Аудитории: employee | hr_manager | admin
EVENT_REGISTRY = {
    'employee_created': EventDefinition(
        event_type='employee_created',
        label='Создание нового сотрудника',
        audiences=('hr_manager', 'employee'),
        category='hr',
    ),
    'employee_status_changed': EventDefinition(
        event_type='employee_status_changed',
        label='Изменение статуса сотрудника',
        audiences=('employee', 'hr_manager'),
        category='hr',
    ),
    'employee_updated': EventDefinition(
        event_type='employee_updated',
        label='Редактирование карточки сотрудника',
        audiences=('hr_manager', 'employee'),
        category='hr',
    ),
    'employee_deleted': EventDefinition(
        event_type='employee_deleted',
        label='Удаление сотрудника',
        audiences=('hr_manager', 'admin'),
        category='hr',
    ),
    'employee_fired': EventDefinition(
        event_type='employee_fired',
        label='Увольнение сотрудника',
        audiences=('employee', 'hr_manager', 'admin'),
        category='hr',
    ),
    'department_changed': EventDefinition(
        event_type='department_changed',
        label='Перевод в другой отдел',
        audiences=('employee', 'hr_manager'),
        category='hr',
    ),
    'position_changed': EventDefinition(
        event_type='position_changed',
        label='Смена должности',
        audiences=('employee', 'hr_manager'),
        category='hr',
    ),
    'training_assigned': EventDefinition(
        event_type='training_assigned',
        label='Назначение обучения',
        audiences=('employee',),
        category='employee',
    ),
    'training_started': EventDefinition(
        event_type='training_started',
        label='Начало обучения',
        audiences=('employee', 'hr_manager'),
        category='employee',
    ),
    'vacation_started': EventDefinition(
        event_type='vacation_started',
        label='Отправление в отпуск',
        audiences=('employee', 'hr_manager'),
        category='employee',
    ),
    'vacation_approved': EventDefinition(
        event_type='vacation_approved',
        label='Выход из отпуска',
        audiences=('employee',),
        category='employee',
    ),
    'vacation_rejected': EventDefinition(
        event_type='vacation_rejected',
        label='Отклонение отпуска',
        audiences=('employee',),
        category='employee',
    ),
}


def get_event_definition(event_type: str) -> Optional[EventDefinition]:
    return EVENT_REGISTRY.get(event_type)


def registered_event_types() -> FrozenSet[str]:
    return frozenset(EVENT_REGISTRY.keys())
