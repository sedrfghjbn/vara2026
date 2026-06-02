#!/bin/bash
cd "$(dirname "$0")"

PY=python3
if ! command -v "$PY" >/dev/null 2>&1; then
    echo "Ошибка: python3 не найден."
    exit 1
fi

echo "Telegram polling (Ctrl+C для остановки)..."
"$PY" manage.py telegram_poll
