#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import subprocess

# Получаем директорию скрипта
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

print("=" * 50)
print("Создание и применение миграций для HR системы")
print("=" * 50)
print(f"Рабочая директория: {os.getcwd()}")
print()

# Шаг 1: Создание миграций
print("Шаг 1: Создание миграций...")
print("-" * 50)
result = subprocess.run(
    [sys.executable, 'manage.py', 'makemigrations', 'hr'],
    cwd=script_dir,
    capture_output=False
)
print()

# Шаг 2: Применение миграций
print("Шаг 2: Применение миграций...")
print("-" * 50)
result = subprocess.run(
    [sys.executable, 'manage.py', 'migrate'],
    cwd=script_dir,
    capture_output=False
)
print()

print("=" * 50)
print("Миграции выполнены!")
print("=" * 50)
input("Нажмите Enter для выхода...")

