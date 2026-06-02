"""Абсолютные ссылки на страницы HR-системы (для кнопок в Telegram)."""

from django.conf import settings
from django.urls import reverse


def site_base_url():
    return getattr(settings, 'SITE_BASE_URL', 'http://127.0.0.1:8000').rstrip('/')


def absolute_url(path_name, *args, **kwargs):
    path = reverse(path_name, args=args, kwargs=kwargs)
    return f'{site_base_url()}{path}'


def employee_detail_url(employee_id):
    return absolute_url('hr:employee_detail', employee_id=employee_id)


def employees_list_url():
    return absolute_url('hr:employees_list')


def profile_url():
    return absolute_url('hr:profile')


def training_detail_url(training_id):
    return absolute_url('hr:training_detail', training_id=training_id)


def trainings_list_url():
    return absolute_url('hr:trainings_list')
