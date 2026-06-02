#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для просмотра пользователей и их прав доступа
"""
import os
import sys
import django

# Настройка Django
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_project.settings')
django.setup()

from hr.models import User

print("=" * 70)
print("ПОЛЬЗОВАТЕЛИ И ИХ ПРАВА ДОСТУПА")
print("=" * 70)
print()

users = User.objects.all().order_by('role', 'username')

if not users.exists():
    print("❌ Пользователи не найдены в базе данных.")
    print()
    print("Для создания пользователя выполните:")
    print("  python manage.py createsuperuser")
    print()
else:
    print(f"Найдено пользователей: {users.count()}")
    print()
    
    # Группировка по ролям
    roles = {
        'admin': [],
        'hr_manager': [],
        'employee': []
    }
    
    for user in users:
        roles[user.role].append(user)
    
    # Администраторы
    if roles['admin']:
        print("🔴 АДМИНИСТРАТОРЫ (полный доступ):")
        print("-" * 70)
        for user in roles['admin']:
            print(f"  • {user.username}")
            print(f"    Email: {user.email}")
            print(f"    Имя: {user.first_name} {user.last_name}".strip() or "Не указано")
            print(f"    Телефон: {user.phone or 'Не указан'}")
            print(f"    Активен: {'Да' if user.is_active else 'Нет'}")
            print(f"    Суперпользователь: {'Да' if user.is_superuser else 'Нет'}")
            print()
    
    # HR-менеджеры
    if roles['hr_manager']:
        print("🟠 HR-МЕНЕДЖЕРЫ (управление сотрудниками, вакансиями, обучением):")
        print("-" * 70)
        for user in roles['hr_manager']:
            print(f"  • {user.username}")
            print(f"    Email: {user.email}")
            print(f"    Имя: {user.first_name} {user.last_name}".strip() or "Не указано")
            print(f"    Телефон: {user.phone or 'Не указан'}")
            print(f"    Активен: {'Да' if user.is_active else 'Нет'}")
            print()
    
    # Обычные сотрудники
    if roles['employee']:
        print("🟡 ОБЫЧНЫЕ СОТРУДНИКИ (просмотр собственного профиля):")
        print("-" * 70)
        for user in roles['employee']:
            print(f"  • {user.username}")
            print(f"    Email: {user.email}")
            print(f"    Имя: {user.first_name} {user.last_name}".strip() or "Не указано")
            print(f"    Телефон: {user.phone or 'Не указан'}")
            print(f"    Активен: {'Да' if user.is_active else 'Нет'}")
            print()

print("=" * 70)
print()
print("ПРАВА ДОСТУПА:")
print("-" * 70)
print("🔴 Администратор:")
print("  • Полный доступ ко всем модулям")
print("  • Управление пользователями")
print("  • Удаление любых записей")
print()
print("🟠 HR-менеджер:")
print("  • Управление сотрудниками (CRUD)")
print("  • Управление вакансиями (CRUD)")
print("  • Управление обучением (CRUD)")
print("  • Просмотр отчётов")
print()
print("🟡 Обычный сотрудник:")
print("  • Просмотр собственного профиля")
print("  • Просмотр своих обучений")
print()
print("=" * 70)

