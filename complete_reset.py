#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import sqlite3
import subprocess

# Абсолютный путь к проекту
BASE_DIR = r'C:\Users\alisa\Desktop\курсач пи ВАРЯ'
os.chdir(BASE_DIR)

print("=" * 60)
print("Полный сброс базы данных")
print("=" * 60)
print()

# Шаг 1: Удаление базы данных
db_path = os.path.join(BASE_DIR, 'db.sqlite3')
if os.path.exists(db_path):
    os.remove(db_path)
    print("✓ База данных удалена")
else:
    print("База данных не найдена")
print()

# Шаг 2: Создание новой базы данных и применение миграций
print("Создание новой базы данных и применение миграций...")
print("-" * 60)

# Сначала создаем базовые таблицы Django
result = subprocess.run(
    [sys.executable, 'manage.py', 'migrate', '--run-syncdb'],
    cwd=BASE_DIR,
    capture_output=True,
    text=True,
    encoding='utf-8'
)
print(result.stdout)
if result.stderr:
    print("Предупреждения:", result.stderr)

# Затем применяем все миграции
result = subprocess.run(
    [sys.executable, 'manage.py', 'migrate'],
    cwd=BASE_DIR,
    capture_output=True,
    text=True,
    encoding='utf-8'
)
print(result.stdout)
if result.stderr and 'error' in result.stderr.lower():
    print("Ошибки:", result.stderr)

print()
print("=" * 60)
print("✓ Готово!")
print("=" * 60)

