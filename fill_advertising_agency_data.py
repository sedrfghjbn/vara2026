"""
Скрипт для заполнения базы данных начальными данными для рекламного агентства
Запуск: python fill_advertising_agency_data.py
"""
import os
import sys
import django
from datetime import date

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'finance_project.settings')
django.setup()

from hr.models import Department, Position, Employee


def fill_data():
    print('Начинаю заполнение базы данных...\n')
    
    # Создаем отделы
    departments_data = [
        {
            'name': 'Отдел креатива',
            'description': 'Разработка креативных концепций, дизайн, копирайтинг'
        },
        {
            'name': 'Отдел продаж',
            'description': 'Привлечение клиентов, работа с существующими клиентами'
        },
        {
            'name': 'Отдел медиапланирования',
            'description': 'Планирование и размещение рекламы в медиа'
        },
        {
            'name': 'Отдел производства',
            'description': 'Производство рекламных материалов, полиграфия'
        },
        {
            'name': 'Отдел маркетинга',
            'description': 'Маркетинговые исследования, стратегии продвижения'
        },
        {
            'name': 'Отдел клиентского сервиса',
            'description': 'Работа с клиентами, аккаунт-менеджмент'
        },
    ]
    
    departments = {}
    for dept_data in departments_data:
        dept, created = Department.objects.get_or_create(
            name=dept_data['name'],
            defaults={'description': dept_data['description']}
        )
        departments[dept.name] = dept
        if created:
            print(f'✓ Создан отдел: {dept.name}')
        else:
            print(f'→ Отдел уже существует: {dept.name}')
    
    print()
    
    # Создаем должности
    positions_data = [
        # Креативный отдел
        {'name': 'Креативный директор', 'description': 'Руководитель креативного отдела'},
        {'name': 'Арт-директор', 'description': 'Руководство визуальным направлением проектов'},
        {'name': 'Дизайнер', 'description': 'Создание визуальных решений'},
        {'name': 'Копирайтер', 'description': 'Написание текстов для рекламы'},
        {'name': 'Графический дизайнер', 'description': 'Разработка графических материалов'},
        
        # Отдел продаж
        {'name': 'Директор по продажам', 'description': 'Руководство отделом продаж'},
        {'name': 'Менеджер по продажам', 'description': 'Привлечение новых клиентов'},
        {'name': 'Старший менеджер по продажам', 'description': 'Работа с ключевыми клиентами'},
        
        # Медиапланирование
        {'name': 'Медиапланер', 'description': 'Планирование рекламных кампаний'},
        {'name': 'Старший медиапланер', 'description': 'Стратегическое медиапланирование'},
        
        # Клиентский сервис
        {'name': 'Аккаунт-менеджер', 'description': 'Работа с клиентами, ведение проектов'},
        {'name': 'Старший аккаунт-менеджер', 'description': 'Работа с крупными клиентами'},
        {'name': 'Менеджер по работе с клиентами', 'description': 'Поддержка клиентов'},
        
        # Производство
        {'name': 'Производственный менеджер', 'description': 'Координация производства материалов'},
        {'name': 'Технический директор', 'description': 'Руководство техническими процессами'},
        
        # Маркетинг
        {'name': 'Маркетолог', 'description': 'Разработка маркетинговых стратегий'},
        {'name': 'SMM-менеджер', 'description': 'Ведение социальных сетей'},
        {'name': 'Аналитик', 'description': 'Анализ эффективности кампаний'},
    ]
    
    positions = {}
    for pos_data in positions_data:
        pos, created = Position.objects.get_or_create(
            name=pos_data['name'],
            defaults={'description': pos_data['description']}
        )
        positions[pos.name] = pos
        if created:
            print(f'✓ Создана должность: {pos.name}')
        else:
            print(f'→ Должность уже существует: {pos.name}')
    
    print()
    
    # Создаем несколько сотрудников
    employees_data = [
        {
            'first_name': 'Анна',
            'last_name': 'Иванова',
            'middle_name': 'Сергеевна',
            'email': 'anna.ivanova@agency.ru',
            'phone': '+79991234567',
            'date_of_birth': date(1985, 5, 15),
            'department': 'Отдел креатива',
            'position': 'Креативный директор',
            'hire_date': date(2020, 1, 10),
            'status': 'active'
        },
        {
            'first_name': 'Дмитрий',
            'last_name': 'Петров',
            'middle_name': 'Александрович',
            'email': 'dmitry.petrov@agency.ru',
            'phone': '+79991234568',
            'date_of_birth': date(1990, 8, 22),
            'department': 'Отдел креатива',
            'position': 'Арт-директор',
            'hire_date': date(2021, 3, 1),
            'status': 'active'
        },
        {
            'first_name': 'Мария',
            'last_name': 'Сидорова',
            'middle_name': 'Владимировна',
            'email': 'maria.sidorova@agency.ru',
            'phone': '+79991234569',
            'date_of_birth': date(1992, 11, 5),
            'department': 'Отдел креатива',
            'position': 'Дизайнер',
            'hire_date': date(2022, 6, 15),
            'status': 'active'
        },
        {
            'first_name': 'Иван',
            'last_name': 'Козлов',
            'middle_name': 'Игоревич',
            'email': 'ivan.kozlov@agency.ru',
            'phone': '+79991234570',
            'date_of_birth': date(1988, 2, 28),
            'department': 'Отдел продаж',
            'position': 'Директор по продажам',
            'hire_date': date(2019, 9, 1),
            'status': 'active'
        },
        {
            'first_name': 'Елена',
            'last_name': 'Морозова',
            'middle_name': 'Дмитриевна',
            'email': 'elena.morozova@agency.ru',
            'phone': '+79991234571',
            'date_of_birth': date(1993, 7, 12),
            'department': 'Отдел продаж',
            'position': 'Менеджер по продажам',
            'hire_date': date(2023, 2, 1),
            'status': 'active'
        },
        {
            'first_name': 'Сергей',
            'last_name': 'Волков',
            'middle_name': 'Петрович',
            'email': 'sergey.volkov@agency.ru',
            'phone': '+79991234572',
            'date_of_birth': date(1987, 4, 18),
            'department': 'Отдел медиапланирования',
            'position': 'Медиапланер',
            'hire_date': date(2021, 11, 10),
            'status': 'active'
        },
        {
            'first_name': 'Ольга',
            'last_name': 'Новикова',
            'middle_name': 'Андреевна',
            'email': 'olga.novikova@agency.ru',
            'phone': '+79991234573',
            'date_of_birth': date(1991, 9, 25),
            'department': 'Отдел клиентского сервиса',
            'position': 'Аккаунт-менеджер',
            'hire_date': date(2022, 4, 5),
            'status': 'active'
        },
        {
            'first_name': 'Александр',
            'last_name': 'Федоров',
            'middle_name': 'Сергеевич',
            'email': 'alexander.fedorov@agency.ru',
            'phone': '+79991234574',
            'date_of_birth': date(1989, 12, 3),
            'department': 'Отдел маркетинга',
            'position': 'Маркетолог',
            'hire_date': date(2020, 7, 20),
            'status': 'active'
        },
    ]
    
    created_count = 0
    for emp_data in employees_data:
        # Проверяем, существует ли сотрудник с таким email
        if Employee.objects.filter(email=emp_data['email']).exists():
            print(f'→ Сотрудник уже существует: {emp_data["email"]}')
            continue
        
        department = departments.get(emp_data['department'])
        position = positions.get(emp_data['position'])
        
        employee = Employee.objects.create(
            first_name=emp_data['first_name'],
            last_name=emp_data['last_name'],
            middle_name=emp_data['middle_name'],
            email=emp_data['email'],
            phone=emp_data['phone'],
            date_of_birth=emp_data['date_of_birth'],
            department=department,
            position=position,
            hire_date=emp_data['hire_date'],
            status=emp_data['status']
        )
        created_count += 1
        print(f'✓ Создан сотрудник: {employee.full_name} - {position.name if position else "Без должности"}')
    
    print(f'\n✓ Заполнение завершено!')
    print(f'  Отделов: {len(departments)}')
    print(f'  Должностей: {len(positions)}')
    print(f'  Сотрудников создано: {created_count}')


if __name__ == '__main__':
    fill_data()

