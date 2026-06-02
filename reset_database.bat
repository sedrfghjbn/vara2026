@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo Сброс базы данных для HR системы
echo ========================================
echo.

REM Остановка сервера (если запущен)
echo Проверка запущенного сервера...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *runserver*" 2>nul
timeout /t 2 /nobreak >nul

REM Удаление старой базы данных
if exist "db.sqlite3" (
    echo Удаление старой базы данных db.sqlite3...
    del "db.sqlite3"
    echo ✓ База данных удалена
) else (
    echo База данных не найдена, пропускаем удаление
)
echo.

REM Удаление файлов миграций (кроме __init__.py)
echo Очистка старых миграций...
if exist "hr\migrations\*.py" (
    for %%f in (hr\migrations\*.py) do (
        if not "%%~nxf"=="__init__.py" del "%%f"
    )
    echo ✓ Старые миграции удалены
) else (
    echo Папка migrations не найдена
)
echo.

REM Создание новых миграций
echo Создание новых миграций для приложения hr...
python manage.py makemigrations hr
if errorlevel 1 (
    echo.
    echo ОШИБКА при создании миграций!
    pause
    exit /b 1
)
echo.

REM Применение миграций
echo Применение миграций...
python manage.py migrate
if errorlevel 1 (
    echo.
    echo ОШИБКА при применении миграций!
    pause
    exit /b 1
)
echo.

echo ========================================
echo ✓ База данных успешно сброшена!
echo ========================================
echo.
echo Следующие шаги:
echo 1. Создать суперпользователя: python manage.py createsuperuser
echo 2. Запустить сервер: python manage.py runserver
echo.
pause

