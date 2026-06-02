"""Возраст сотрудника (18–100) и уведомления о дате рождения."""

from datetime import date
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from hr.forms import EmployeeForm, RegisterForm, UserProfileForm, validate_employee_birth_date
from hr.integrations.telegram.models import NotificationLog, UserTelegramLink
from hr.models import Employee, User
from django.core.exceptions import ValidationError


class EmployeeAgeValidationTests(TestCase):
    def test_register_allows_under_18(self):
        """Регистрация без ограничения 18+."""
        today = timezone.now().date()
        young_dob = date(today.year - 16, today.month, min(today.day, 28))
        form = RegisterForm(data={
            'email': 'teen@example.com',
            'password1': 'Test1234A',
            'password2': 'Test1234A',
            'first_name': 'Юный',
            'last_name': 'Пользователь',
            'middle_name': 'Тест',
            'date_of_birth': young_dob.isoformat(),
            'phone': '+79991234567',
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_employee_card_rejects_under_18(self):
        today = timezone.now().date()
        young_dob = date(today.year - 16, today.month, min(today.day, 28))
        with self.assertRaises(ValidationError):
            validate_employee_birth_date(young_dob)

    def test_employee_card_rejects_over_100(self):
        today = timezone.now().date()
        old_dob = date(today.year - 101, 1, 1)
        with self.assertRaises(ValidationError):
            validate_employee_birth_date(old_dob)

    def test_employee_card_accepts_25(self):
        today = timezone.now().date()
        dob = date(today.year - 25, 6, 15)
        self.assertEqual(validate_employee_birth_date(dob), dob)

    def test_profile_rejects_under_18_for_employee(self):
        today = timezone.now().date()
        young_dob = date(today.year - 6, today.month, min(today.day, 28))
        user = User.objects.create_user(
            username='young_profile',
            email='young_profile@test.ru',
            password='Test1234',
            role='employee',
        )
        Employee.objects.create(
            user=user,
            first_name='Ребёнок',
            last_name='Тест',
            date_of_birth=date(1995, 1, 1),
            email='young_card@test.ru',
            phone='+79990006677',
            hire_date=today,
        )
        form = UserProfileForm(
            {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'middle_name': '',
                'email': user.email,
                'phone': user.phone,
                'date_of_birth': young_dob.isoformat(),
            },
            instance=user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('date_of_birth', form.errors)
        self.assertIn('18', str(form.errors['date_of_birth']))


@patch('hr.integrations.telegram.client.TelegramClient.send_message')
class EmployeeBirthDateNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='dob_emp',
            email='dob_emp@test.ru',
            password='Test1234',
            role='employee',
        )
        UserTelegramLink.objects.create(
            user=self.user,
            telegram_chat_id=777007,
            is_active=True,
        )
        self.employee = Employee.objects.create(
            user=self.user,
            first_name='Дата',
            last_name='Рождения',
            date_of_birth=date(1995, 3, 10),
            email='dob_card@test.ru',
            phone='+79990005566',
            hire_date=date.today(),
        )

    def test_dob_change_sends_telegram(self, mock_send):
        mock_send.return_value = {'ok': True}
        NotificationLog.objects.all().delete()
        self.employee.date_of_birth = date(1994, 3, 10)
        self.employee.save()
        log = NotificationLog.objects.filter(event_type='employee_updated').first()
        self.assertIsNotNone(log)
        self.assertIn('дата рождения', log.message_text.lower())
        self.assertIn('10.03.1995', log.message_text)
        self.assertIn('10.03.1994', log.message_text)
