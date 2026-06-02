#!/bin/bash
cd "$(dirname "$0")"

PY=python3
if ! command -v "$PY" >/dev/null 2>&1; then
    echo "Ошибка: python3 не найден. Установите Python 3 с https://www.python.org/downloads/"
    exit 1
fi

echo "Установка зависимостей..."
"$PY" -m pip install -r requirements.txt

echo ""
echo "Применение миграций..."
"$PY" manage.py migrate

echo ""
echo "Запуск сервера: http://127.0.0.1:8000/"
"$PY" manage.py runserver
