from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import Employee, Vacancy, Training, Department, Position, Certificate
from datetime import date, timedelta

User = get_user_model()


class UserRegistrationTests(TestCase):
    """Тесты регистрации пользователя"""
    
    def test_registration_success(self):
        """Позитивный тест: успешная регистрация"""
        response = self.client.post(reverse('hr:register'), {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'Test1234',
            'password2': 'Test1234',
            'first_name': 'Test',
            'last_name': 'User',
        })
        self.assertEqual(response.status_code, 302)  # Редирект после успешной регистрации
        self.assertTrue(User.objects.filter(username='testuser').exists())
    
    def test_registration_weak_password(self):
        """Негативный тест: слабый пароль"""
        response = self.client.post(reverse('hr:register'), {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': '123',  # Слишком короткий
            'password2': '123',
        })
        self.assertEqual(response.status_code, 200)  # Остается на странице
        self.assertFalse(User.objects.filter(username='testuser').exists())
    
    def test_registration_password_no_uppercase(self):
        """Негативный тест: пароль без заглавной буквы"""
        response = self.client.post(reverse('hr:register'), {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'test1234',  # Нет заглавной буквы
            'password2': 'test1234',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='testuser').exists())
    
    def test_registration_duplicate_username(self):
        """Негативный тест: дубликат логина"""
        User.objects.create_user(username='testuser', email='existing@example.com', password='Test1234')
        response = self.client.post(reverse('hr:register'), {
            'username': 'testuser',  # Уже существует
            'email': 'new@example.com',
            'password1': 'Test1234',
            'password2': 'Test1234',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username='testuser').count(), 1)  # Только один пользователь
    
    def test_registration_duplicate_email(self):
        """Негативный тест: дубликат email"""
        User.objects.create_user(username='user1', email='test@example.com', password='Test1234')
        response = self.client.post(reverse('hr:register'), {
            'username': 'user2',
            'email': 'test@example.com',  # Уже существует
            'password1': 'Test1234',
            'password2': 'Test1234',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(email='test@example.com').count(), 1)


class AuthenticationTests(TestCase):
    """Тесты аутентификации"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Test1234',
            role='employee'
        )
    
    def test_login_success(self):
        """Позитивный тест: успешный вход"""
        response = self.client.post(reverse('hr:login'), {
            'username': 'testuser',
            'password': 'Test1234',
        })
        self.assertEqual(response.status_code, 302)  # Редирект после входа
    
    def test_login_wrong_password(self):
        """Негативный тест: неверный пароль"""
        response = self.client.post(reverse('hr:login'), {
            'username': 'testuser',
            'password': 'WrongPassword',
        })
        self.assertEqual(response.status_code, 200)  # Остается на странице
        self.assertFalse(response.wsgi_request.user.is_authenticated)
    
    def test_login_nonexistent_user(self):
        """Негативный тест: несуществующий пользователь"""
        response = self.client.post(reverse('hr:login'), {
            'username': 'nonexistent',
            'password': 'Test1234',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)
    
    def test_logout(self):
        """Позитивный тест: выход из системы"""
        self.client.login(username='testuser', password='Test1234')
        response = self.client.post(reverse('hr:logout'))
        self.assertEqual(response.status_code, 302)  # Редирект после выхода


class EmployeeCRUDTests(TestCase):
    """Тесты CRUD операций для сотрудников"""
    
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='Admin1234',
            role='admin'
        )
        self.hr_manager = User.objects.create_user(
            username='hr',
            email='hr@example.com',
            password='Hr1234',
            role='hr_manager'
        )
        self.employee_user = User.objects.create_user(
            username='employee',
            email='employee@example.com',
            password='Emp1234',
            role='employee'
        )
        self.department = Department.objects.create(name='IT')
        self.position = Position.objects.create(name='Developer')
    
    def test_create_employee_as_admin(self):
        """Позитивный тест: создание сотрудника администратором"""
        self.client.login(username='admin', password='Admin1234')
        response = self.client.post(reverse('hr:employee_create'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'email': 'john@example.com',
            'phone': '+79991234567',
            'position': self.position.id,
            'department': self.department.id,
            'hire_date': date.today().isoformat(),
            'status': 'active',
        })
        self.assertEqual(response.status_code, 302)  # Редирект после создания
        self.assertTrue(Employee.objects.filter(email='john@example.com').exists())
    
    def test_create_employee_duplicate_email(self):
        """Негативный тест: создание сотрудника с дубликатом email"""
        Employee.objects.create(
            first_name='Existing',
            last_name='User',
            date_of_birth='1990-01-01',
            email='existing@example.com',
            phone='+79991234567',
            hire_date=date.today(),
        )
        self.client.login(username='admin', password='Admin1234')
        response = self.client.post(reverse('hr:employee_create'), {
            'first_name': 'New',
            'last_name': 'User',
            'date_of_birth': '1990-01-01',
            'email': 'existing@example.com',  # Дубликат
            'phone': '+79991234568',
            'hire_date': date.today().isoformat(),
        })
        self.assertEqual(response.status_code, 200)  # Остается на странице с ошибкой
        self.assertEqual(Employee.objects.filter(email='existing@example.com').count(), 1)
    
    def test_employee_access_denied_for_regular_user(self):
        """Негативный тест: обычный сотрудник не может создавать сотрудников"""
        self.client.login(username='employee', password='Emp1234')
        response = self.client.get(reverse('hr:employee_create'))
        self.assertEqual(response.status_code, 302)  # Редирект (доступ запрещен)
    
    def test_update_employee(self):
        """Позитивный тест: обновление сотрудника"""
        emp = Employee.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth='1990-01-01',
            email='john@example.com',
            phone='+79991234567',
            hire_date=date.today(),
        )
        self.client.login(username='admin', password='Admin1234')
        response = self.client.post(reverse('hr:employee_edit', args=[emp.id]), {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'email': 'john@example.com',
            'phone': '+79991234567',
            'hire_date': date.today().isoformat(),
            'status': 'active',
        })
        self.assertEqual(response.status_code, 302)
        emp.refresh_from_db()
        self.assertEqual(emp.first_name, 'Jane')
    
    def test_delete_employee(self):
        """Позитивный тест: удаление сотрудника"""
        emp = Employee.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth='1990-01-01',
            email='john@example.com',
            phone='+79991234567',
            hire_date=date.today(),
        )
        self.client.login(username='admin', password='Admin1234')
        response = self.client.post(reverse('hr:employee_delete', args=[emp.id]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Employee.objects.filter(id=emp.id).exists())


class VacancyCRUDTests(TestCase):
    """Тесты CRUD операций для вакансий"""
    
    def setUp(self):
        self.hr_manager = User.objects.create_user(
            username='hr',
            email='hr@example.com',
            password='Hr1234',
            role='hr_manager'
        )
        self.department = Department.objects.create(name='IT')
        self.position = Position.objects.create(name='Developer')
    
    def test_create_vacancy(self):
        """Позитивный тест: создание вакансии"""
        self.client.login(username='hr', password='Hr1234')
        response = self.client.post(reverse('hr:vacancy_create'), {
            'title': 'Python Developer',
            'description': 'We need a Python developer',
            'salary_min': 50000,
            'salary_max': 100000,
            'status': 'open',
            'position': self.position.id,
            'department': self.department.id,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Vacancy.objects.filter(title='Python Developer').exists())
    
    def test_vacancy_salary_validation(self):
        """Негативный тест: минимальная зарплата больше максимальной"""
        self.client.login(username='hr', password='Hr1234')
        response = self.client.post(reverse('hr:vacancy_create'), {
            'title': 'Developer',
            'description': 'Test',
            'salary_min': 100000,  # Больше максимальной
            'salary_max': 50000,
            'status': 'open',
        })
        self.assertEqual(response.status_code, 200)  # Остается на странице с ошибкой
        self.assertFalse(Vacancy.objects.filter(title='Developer').exists())


class TrainingCRUDTests(TestCase):
    """Тесты CRUD операций для обучения"""
    
    def setUp(self):
        self.hr_manager = User.objects.create_user(
            username='hr',
            email='hr@example.com',
            password='Hr1234',
            role='hr_manager'
        )
        self.employee = Employee.objects.create(
            first_name='John',
            last_name='Doe',
            date_of_birth='1990-01-01',
            email='john@example.com',
            phone='+79991234567',
            hire_date=date.today(),
        )
    
    def test_create_training(self):
        """Позитивный тест: создание обучения"""
        self.client.login(username='hr', password='Hr1234')
        start_date = date.today()
        end_date = start_date + timedelta(days=30)
        response = self.client.post(reverse('hr:training_create'), {
            'title': 'Python Basics',
            'description': 'Learn Python',
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'status': 'planned',
            'responsible': self.hr_manager.id,
            'participants': [self.employee.id],
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Training.objects.filter(title='Python Basics').exists())
    
    def test_training_date_validation(self):
        """Негативный тест: дата начала позже даты окончания"""
        self.client.login(username='hr', password='Hr1234')
        start_date = date.today() + timedelta(days=30)
        end_date = date.today()
        response = self.client.post(reverse('hr:training_create'), {
            'title': 'Training',
            'description': 'Test',
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),  # Раньше начала
            'status': 'planned',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Training.objects.filter(title='Training').exists())


class RoleAccessTests(TestCase):
    """Тесты доступа по ролям"""
    
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='Admin1234',
            role='admin'
        )
        self.hr_manager = User.objects.create_user(
            username='hr',
            email='hr@example.com',
            password='Hr1234',
            role='hr_manager'
        )
        self.employee = User.objects.create_user(
            username='employee',
            email='employee@example.com',
            password='Emp1234',
            role='employee'
        )
    
    def test_admin_access_to_all(self):
        """Позитивный тест: администратор имеет доступ ко всему"""
        self.client.login(username='admin', password='Admin1234')
        self.assertEqual(self.client.get(reverse('hr:employees_list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('hr:vacancies_list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('hr:trainings_list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('hr:reports')).status_code, 200)
    
    def test_hr_manager_access(self):
        """Позитивный тест: HR-менеджер имеет доступ к модулям"""
        self.client.login(username='hr', password='Hr1234')
        self.assertEqual(self.client.get(reverse('hr:employees_list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('hr:vacancies_list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('hr:trainings_list')).status_code, 200)
    
    def test_employee_no_access_to_hr_modules(self):
        """Негативный тест: обычный сотрудник не имеет доступа к HR модулям"""
        self.client.login(username='employee', password='Emp1234')
        self.assertEqual(self.client.get(reverse('hr:employees_list')).status_code, 302)  # Редирект
        self.assertEqual(self.client.get(reverse('hr:vacancies_list')).status_code, 302)
        self.assertEqual(self.client.get(reverse('hr:trainings_list')).status_code, 302)

