from hr.models import Department, Position, Employee
from datetime import date

# Создаем отделы
departments_data = [
    {'name': 'Отдел креатива', 'description': 'Разработка креативных концепций, дизайн, копирайтинг'},
    {'name': 'Отдел продаж', 'description': 'Привлечение клиентов, работа с существующими клиентами'},
    {'name': 'Отдел медиапланирования', 'description': 'Планирование и размещение рекламы в медиа'},
    {'name': 'Отдел производства', 'description': 'Производство рекламных материалов, полиграфия'},
    {'name': 'Отдел маркетинга', 'description': 'Маркетинговые исследования, стратегии продвижения'},
    {'name': 'Отдел клиентского сервиса', 'description': 'Работа с клиентами, аккаунт-менеджмент'},
]

departments = {}
for dept_data in departments_data:
    dept, created = Department.objects.get_or_create(name=dept_data['name'], defaults={'description': dept_data['description']})
    departments[dept.name] = dept
    print(f'{"✓ Создан" if created else "→ Уже существует"} отдел: {dept.name}')

# Создаем должности
positions_data = [
    {'name': 'Креативный директор', 'description': 'Руководитель креативного отдела'},
    {'name': 'Арт-директор', 'description': 'Руководство визуальным направлением проектов'},
    {'name': 'Дизайнер', 'description': 'Создание визуальных решений'},
    {'name': 'Копирайтер', 'description': 'Написание текстов для рекламы'},
    {'name': 'Графический дизайнер', 'description': 'Разработка графических материалов'},
    {'name': 'Директор по продажам', 'description': 'Руководство отделом продаж'},
    {'name': 'Менеджер по продажам', 'description': 'Привлечение новых клиентов'},
    {'name': 'Старший менеджер по продажам', 'description': 'Работа с ключевыми клиентами'},
    {'name': 'Медиапланер', 'description': 'Планирование рекламных кампаний'},
    {'name': 'Старший медиапланер', 'description': 'Стратегическое медиапланирование'},
    {'name': 'Аккаунт-менеджер', 'description': 'Работа с клиентами, ведение проектов'},
    {'name': 'Старший аккаунт-менеджер', 'description': 'Работа с крупными клиентами'},
    {'name': 'Менеджер по работе с клиентами', 'description': 'Поддержка клиентов'},
    {'name': 'Производственный менеджер', 'description': 'Координация производства материалов'},
    {'name': 'Технический директор', 'description': 'Руководство техническими процессами'},
    {'name': 'Маркетолог', 'description': 'Разработка маркетинговых стратегий'},
    {'name': 'SMM-менеджер', 'description': 'Ведение социальных сетей'},
    {'name': 'Аналитик', 'description': 'Анализ эффективности кампаний'},
]

positions = {}
for pos_data in positions_data:
    pos, created = Position.objects.get_or_create(name=pos_data['name'], defaults={'description': pos_data['description']})
    positions[pos.name] = pos
    print(f'{"✓ Создана" if created else "→ Уже существует"} должность: {pos.name}')

print(f'\n✓ Заполнение завершено! Отделов: {len(departments)}, Должностей: {len(positions)}')

