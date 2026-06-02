#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для настройки HR системы
Удаляет старую БД и создает новую с миграциями
"""
import os
import sys
import subprocess
import sqlite3

# Получаем директорию скрипта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

print("=" * 60)
print("Настройка HR системы")
print("=" * 60)
print(f"Рабочая директория: {BASE_DIR}")
print()

# Шаг 1: Удаление старой БД (если есть)
db_path = os.path.join(BASE_DIR, 'db.sqlite3')
if os.path.exists(db_path):
    print("Шаг 1: Удаление старой базы данных...")
    try:
        os.remove(db_path)
        print(f"✓ База данных {db_path} удалена")
    except Exception as e:
        print(f"⚠ Не удалось удалить БД: {e}")
    print()
else:
    print("Шаг 1: Старая база данных не найдена, пропускаем")
    print()

# Шаг 2: Создание миграций
print("Шаг 2: Создание миграций для приложения hr...")
print("-" * 60)
result = subprocess.run(
    [sys.executable, 'manage.py', 'makemigrations', 'hr'],
    cwd=BASE_DIR
)
if result.returncode != 0:
    print("❌ Ошибка при создании миграций!")
    input("Нажмите Enter для выхода...")
    sys.exit(1)
print()

# Шаг 3: Применение миграций
print("Шаг 3: Применение миграций...")
print("-" * 60)
result = subprocess.run(
    [sys.executable, 'manage.py', 'migrate'],
    cwd=BASE_DIR
)
if result.returncode != 0:
    print("❌ Ошибка при применении миграций!")
    input("Нажмите Enter для выхода...")
    sys.exit(1)
print()

print("=" * 60)
print("✓ Настройка завершена успешно!")
print("=" * 60)
print()
print("Теперь вы можете:")
print("1. Создать суперпользователя: python manage.py createsuperuser")
print("2. Запустить сервер: python manage.py runserver")
print()
input("Нажмите Enter для выхода...")

