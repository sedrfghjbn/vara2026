#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import glob

# Получаем директорию скрипта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

print("=" * 60)
print("Сброс базы данных и создание новых миграций")
print("=" * 60)
print(f"Рабочая директория: {BASE_DIR}")
print()

# Шаг 1: Удаление старой базы данных
print("Шаг 1: Удаление старой базы данных...")
db_path = os.path.join(BASE_DIR, 'db.sqlite3')
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"✓ База данных {db_path} удалена")
else:
    print("База данных не найдена, пропускаем")
print()

# Шаг 2: Удаление старых миграций hr (кроме __init__.py)
print("Шаг 2: Удаление старых миграций hr...")
migrations_dir = os.path.join(BASE_DIR, 'hr', 'migrations')
if os.path.exists(migrations_dir):
    migration_files = glob.glob(os.path.join(migrations_dir, '*.py'))
    deleted_count = 0
    for file_path in migration_files:
        if os.path.basename(file_path) != '__init__.py':
            os.remove(file_path)
            deleted_count += 1
            print(f"  Удален: {os.path.basename(file_path)}")
    if deleted_count > 0:
        print(f"✓ Удалено {deleted_count} файлов миграций")
    else:
        print("Файлы миграций не найдены")
else:
    print("Папка migrations не найдена, создаем...")
    os.makedirs(migrations_dir, exist_ok=True)
    # Создаем __init__.py если его нет
    init_file = os.path.join(migrations_dir, '__init__.py')
    if not os.path.exists(init_file):
        with open(init_file, 'w') as f:
            f.write('')
        print("✓ Создана папка migrations с __init__.py")
print()

# Шаг 3: Создание новых миграций
print("Шаг 3: Создание новых миграций для приложения hr...")
print("-" * 60)
result = subprocess.run(
    [sys.executable, 'manage.py', 'makemigrations', 'hr'],
    cwd=BASE_DIR,
    capture_output=True,
    text=True,
    encoding='utf-8'
)
print(result.stdout)
if result.stderr:
    print("Ошибки:", result.stderr)
if result.returncode != 0:
    print("❌ Ошибка при создании миграций!")
    input("Нажмите Enter для выхода...")
    sys.exit(1)
print()

# Шаг 4: Применение миграций
print("Шаг 4: Применение миграций...")
print("-" * 60)
result = subprocess.run(
    [sys.executable, 'manage.py', 'migrate'],
    cwd=BASE_DIR,
    capture_output=True,
    text=True,
    encoding='utf-8'
)
print(result.stdout)
if result.stderr:
    print("Ошибки:", result.stderr)
if result.returncode != 0:
    print("❌ Ошибка при применении миграций!")
    input("Нажмите Enter для выхода...")
    sys.exit(1)
print()

print("=" * 60)
print("✓ Готово! База данных сброшена и миграции применены!")
print("=" * 60)
print()
print("Следующие шаги:")
print("1. Создать суперпользователя: python manage.py createsuperuser")
print("2. Запустить сервер: python manage.py runserver")
print()
input("Нажмите Enter для выхода...")

