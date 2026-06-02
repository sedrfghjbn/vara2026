#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import subprocess

# Получаем директорию, где находится этот скрипт
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

print(f"Рабочая директория: {os.getcwd()}")
print("Выполняю makemigrations...")

# Выполняем makemigrations
result1 = subprocess.run([sys.executable, 'manage.py', 'makemigrations'], 
                        cwd=BASE_DIR, capture_output=True, text=True, encoding='utf-8')
print(result1.stdout)
if result1.stderr:
    print("Ошибки:", result1.stderr)

print("\nВыполняю migrate...")
# Выполняем migrate
result2 = subprocess.run([sys.executable, 'manage.py', 'migrate'], 
                        cwd=BASE_DIR, capture_output=True, text=True, encoding='utf-8')
print(result2.stdout)
if result2.stderr:
    print("Ошибки:", result2.stderr)
