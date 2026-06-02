@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo Сброс базы данных и создание миграций
echo ========================================
echo.

echo Шаг 1: Удаление старой базы данных...
if exist "db.sqlite3" (
    del "db.sqlite3"
    echo База данных удалена
) else (
    echo База данных не найдена
)
echo.

echo Шаг 2: Удаление старых миграций hr...
if exist "hr\migrations\0001_initial.py" del "hr\migrations\0001_initial.py"
if exist "hr\migrations\0002_*.py" del "hr\migrations\0002_*.py"
if exist "hr\migrations\0003_*.py" del "hr\migrations\0003_*.py"
if exist "hr\migrations\0004_*.py" del "hr\migrations\0004_*.py"
if exist "hr\migrations\0005_*.py" del "hr\migrations\0005_*.py"
echo Старые миграции удалены
echo.

echo Шаг 3: Создание новых миграций...
python manage.py makemigrations hr
if errorlevel 1 (
    echo ОШИБКА при создании миграций!
    pause
    exit /b 1
)
echo.

echo Шаг 4: Применение миграций...
python manage.py migrate
if errorlevel 1 (
    echo ОШИБКА при применении миграций!
    pause
    exit /b 1
)
echo.

echo ========================================
echo Готово! База данных сброшена!
echo ========================================
echo.
pause

