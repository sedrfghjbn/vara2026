#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для создания администратора
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

print("=" * 60)
print("Создание администратора")
print("=" * 60)
print()

username = input("Введите логин: ").strip()
if not username:
    print("Ошибка: логин не может быть пустым!")
    sys.exit(1)

# Проверяем, существует ли пользователь
if User.objects.filter(username=username).exists():
    user = User.objects.get(username=username)
    print(f"Пользователь {username} уже существует.")
    choice = input("Сделать его администратором? (y/n): ").strip().lower()
    if choice == 'y':
        user.is_superuser = True
        user.is_staff = True
        user.role = 'admin'
        user.save()
        print(f"✓ Пользователь {username} теперь администратор!")
        print(f"  - is_superuser: {user.is_superuser}")
        print(f"  - is_staff: {user.is_staff}")
        print(f"  - role: {user.role}")
    else:
        print("Отменено.")
    sys.exit(0)

email = input("Введите email: ").strip()
if not email:
    print("Ошибка: email не может быть пустым!")
    sys.exit(1)

password = input("Введите пароль: ").strip()
if len(password) < 8:
    print("Ошибка: пароль должен содержать минимум 8 символов!")
    sys.exit(1)

# Создаем суперпользователя
try:
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        is_superuser=True,
        is_staff=True,
        role='admin'
    )
    print()
    print("=" * 60)
    print("✓ Администратор успешно создан!")
    print("=" * 60)
    print(f"Логин: {user.username}")
    print(f"Email: {user.email}")
    print(f"Роль: {user.get_role_display()}")
    print(f"is_superuser: {user.is_superuser}")
    print(f"is_staff: {user.is_staff}")
    print()
    print("Теперь вы можете войти в админ-панель:")
    print("  http://127.0.0.1:8000/admin/")
    print()
except Exception as e:
    print(f"Ошибка при создании пользователя: {e}")
    sys.exit(1)

