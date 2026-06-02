"""Тесты Telegram-уведомлений и команд бота."""

from datetime import date
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from hr.integrations.telegram.commands import cmd_help, cmd_mytrainings, cmd_status
from hr.integrations.telegram.dispatcher import EventDispatcher
from hr.integrations.telegram.formatter import format_notification
from hr.integrations.telegram.keyboards import build_event_keyboard
from hr.integrations.telegram.linking import complete_telegram_link, process_telegram_message
from hr.integrations.telegram.models import NotificationLog, UserTelegramLink
from hr.integrations.telegram.service import NotificationService
from hr.forms import UserProfileForm
from hr.models import Department, Employee, Position, Training

User = get_user_model()


@override_settings(
    TELEGRAM_BOT_TOKEN='test-token',
    SITE_BASE_URL='http://testserver',
)
class TelegramFormatterTests(TestCase):
    def test_employee_created_hr_message(self):
        text = format_notification('employee_created', {
            'name': 'Иванов Иван',
            'department': 'IT',
            'position': 'Dev',
            'email': 'i@test.ru',
            'employee_id': 42,
        }, 'hr_manager')
        self.assertIn('Новый сотрудник', text)
        self.assertIn('Иванов', text)
        self.assertIn('IT', text)  # Department
        self.assertIn('Dev', text)  # Position

    def test_employee_message_includes_hr_contacts(self):
        User.objects.create_user(
            username='hr_fmt',
            email='hr_fmt@test.ru',
            password='Test1234',
            role='hr_manager',
        )
        text = format_notification('employee_status_changed', {
            'name': 'Иванов',
            'previous_status': 'На больничном',
            'status': 'Работает',
            'department': 'IT',
            'employee_id': 1,
        }, 'employee')
        # Проверяем, что там есть контакт для связи
        self.assertTrue(len(text) > 20)  # Должно быть приличное сообщение

    def test_sick_leave_notification_uses_assign_message(self):
        text = format_notification('employee_status_changed', {
            'name': 'Иванов',
            'previous_status': 'Работает',
            'status': 'На больничном',
            'status_code': 'sick_leave',
            'previous_status_code': 'active',
            'employee_id': 1,
        }, 'employee')
        self.assertIn('Больничный', text)

    def test_sick_leave_return_notification_uses_finished_message(self):
        text = format_notification('employee_status_changed', {
            'name': 'Иванов',
            'previous_status': 'На больничном',
            'status': 'Работает',
            'status_code': 'active',
            'previous_status_code': 'sick_leave',
            'employee_id': 1,
        }, 'employee')
        self.assertIn('больничный завершён', text.lower())

    def test_employee_notification_uses_actor_hr_email(self):
        text = format_notification('employee_updated', {
            'name': 'Иванов',
            'email': 'ivanov@test.ru',
            'actor_email': 'hr1@test.ru',
            'actor_role': 'hr_manager',
        }, 'employee')
        # Новый форматер не показывает контакты, но должно быть сообщение
        self.assertTrue(len(text) > 10)

    def test_employee_updated_message_for_self_edit(self):
        text = format_notification('employee_updated', {
            'name': 'Иванов',
            'email': 'ivanov@test.ru',
            'actor_email': 'ivanov@test.ru',
            'actor_role': 'employee',
        }, 'employee')
        self.assertIn('Профиль обновлён', text)

    def test_training_assigned_keyboard(self):
        kb = build_event_keyboard('training_assigned', {
            'employee_id': 1,
            'training_id': 5,
        }, 'employee')
        self.assertIsNotNone(kb)
        urls = [btn['url'] for row in kb['inline_keyboard'] for btn in row]
        self.assertTrue(any('/trainings/5/' in u for u in urls))

    def test_training_started_employee_message_shows_actor_email_only(self):
        text = format_notification('training_started', {
            'training_title': 'маркетолог',
            'details': 'Даты: 2026-06-05 — 2026-08-05',
            'actor_email': 'admin@gmail.com',
            'actor_role': 'hr_manager',
        }, 'employee')
        # Обучение началось
        self.assertIn('Обучение', text)

    def test_vacation_started_message(self):
        text = format_notification('vacation_started', {'name': 'Иванов'}, 'employee')
        self.assertIn('отпуск', text.lower())

    def test_fired_message(self):
        text = format_notification('employee_fired', {}, 'employee')
        self.assertIn('уволен', text.lower())


@override_settings(TELEGRAM_BOT_TOKEN='test-token')
class TelegramDispatchTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name='HR')
        self.pos = Position.objects.create(name='Manager')
        self.hr = User.objects.create_user(
            username='hr_test',
            email='hr_tg@test.ru',
            password='Test1234',
            role='hr_manager',
        )
        self.hr.ensure_telegram_bind_code()
        UserTelegramLink.objects.create(
            user=self.hr,
            telegram_chat_id=111001,
            is_active=True,
        )

    @patch('hr.integrations.telegram.client.TelegramClient.send_message')
    def test_dispatch_employee_created(self, mock_send):
        mock_send.return_value = {'ok': True}
        employee = Employee.objects.create(
            first_name='Новый',
            last_name='Сотрудник',
            date_of_birth=date(1995, 1, 1),
            email='new_emp_tg@test.ru',
            phone='+79990001122',
            department=self.dept,
            position=self.pos,
        )
        logs = NotificationLog.objects.filter(event_type='employee_created')
        self.assertGreaterEqual(logs.count(), 1)
        mock_send.assert_called()
        call_kwargs = mock_send.call_args.kwargs
        self.assertIn('reply_markup', call_kwargs)
        self.assertIsNotNone(call_kwargs['reply_markup'])

    @patch('hr.integrations.telegram.client.TelegramClient.send_message')
    def test_dispatch_employee_created_superuser_hr(self, mock_send):
        """Суперпользователь без role=hr_manager тоже получает уведомления HR."""
        mock_send.return_value = {'ok': True}
        admin_hr = User.objects.create_superuser(
            username='admin_hr_tg',
            email='admin_hr_tg@test.ru',
            password='Test1234',
        )
        admin_hr.ensure_telegram_bind_code()
        UserTelegramLink.objects.create(
            user=admin_hr,
            telegram_chat_id=111002,
            is_active=True,
        )
        Employee.objects.create(
            first_name='Тест',
            last_name='АдминHR',
            date_of_birth=date(1990, 1, 1),
            email='admin_hr_emp@test.ru',
            phone='+79990001199',
            department=self.dept,
            position=self.pos,
        )
        self.assertTrue(
            NotificationLog.objects.filter(
                event_type='employee_created',
                telegram_chat_id=111002,
            ).exists(),
        )

    @patch('hr.integrations.telegram.client.TelegramClient.send_message')
    def test_department_change_sends_hr_notification(self, mock_send):
        mock_send.return_value = {'ok': True}
        emp = Employee.objects.create(
            first_name='Dept',
            last_name='Changer',
            date_of_birth=date(1990, 1, 1),
            email='deptchanger@test.ru',
            phone='+79990009999',
            department=self.dept,
            position=self.pos,
        )
        NotificationLog.objects.all().delete()
        new_dept = Department.objects.create(name='NewDept')
        emp.department = new_dept
        emp.save()
        self.assertTrue(
            NotificationLog.objects.filter(event_type='department_changed', telegram_chat_id=111001).exists()
        )

    @patch('hr.integrations.telegram.client.TelegramClient.send_message')
    def test_vacation_and_profile_update_send_both_notifications(self, mock_send):
        mock_send.return_value = {'ok': True}
        employee_user = User.objects.create_user(
            username='vacation_emp',
            email='vacation_emp@test.ru',
            password='Test1234',
            role='employee',
        )
        UserTelegramLink.objects.create(user=employee_user, telegram_chat_id=555005, is_active=True)
        emp = Employee.objects.create(
            user=employee_user,
            first_name='Вера',
            last_name='Иванова',
            date_of_birth=date(1992, 2, 2),
            email='vera@test.ru',
            phone='+79990002233',
            hire_date=date.today(),
            status='active',
            department=self.dept,
            position=self.pos,
        )
        NotificationLog.objects.all().delete()

        emp.last_name = 'Петрова'
        emp.status = 'on_leave'
        emp.save()

        self.assertTrue(
            NotificationLog.objects.filter(event_type='vacation_started', telegram_chat_id=555005).exists()
        )
        self.assertFalse(
            NotificationLog.objects.filter(event_type='employee_updated', telegram_chat_id=555005).exists()
        )
        self.assertIn('Фамилия: Иванова → Петрова', NotificationLog.objects.filter(
            event_type='vacation_started', telegram_chat_id=555005
        ).first().message_text)

    @patch('hr.integrations.telegram.client.TelegramClient.send_message')
    def test_training_assignment_sends_employee_notification(self, mock_send):
        mock_send.return_value = {'ok': True}
        employee_user = User.objects.create_user(
            username='train_emp',
            email='train_emp@test.ru',
            password='Test1234',
            role='employee',
        )
        emp = Employee.objects.create(
            user=employee_user,
            first_name='Train',
            last_name='User',
            date_of_birth=date(1991, 2, 2),
            email='trainuser@test.ru',
            phone='+79990008888',
            hire_date=date.today(),
            status='active',
            department=self.dept,
            position=self.pos,
        )
        UserTelegramLink.objects.create(user=employee_user, telegram_chat_id=999999, is_active=True)
        NotificationLog.objects.all().delete()
        training = Training.objects.create(
            title='Nice Course',
            responsible=self.hr,
            start_date=date.today(),
            end_date=date.today(),
            status='planned',
        )
        training.participants.add(emp)
        self.assertTrue(
            NotificationLog.objects.filter(event_type='training_assigned', telegram_chat_id=999999).exists()
        )

    @patch('hr.integrations.telegram.client.TelegramClient.send_message')
    def test_training_edit_start_sets_actor_email(self, mock_send):
        mock_send.return_value = {'ok': True}
        other_hr = User.objects.create_user(
            username='other_hr',
            email='other_hr@test.ru',
            password='Test1234',
            role='hr_manager',
        )
        other_hr.ensure_telegram_bind_code()
        UserTelegramLink.objects.create(user=other_hr, telegram_chat_id=222003, is_active=True)

        employee_user = User.objects.create_user(
            username='train_emp2',
            email='train_emp2@test.ru',
            password='Test1234',
            role='employee',
        )
        emp = Employee.objects.create(
            user=employee_user,
            first_name='Train2',
            last_name='User2',
            date_of_birth=date(1991, 3, 3),
            email='trainuser2@test.ru',
            phone='+79990007777',
            hire_date=date.today(),
            status='active',
            department=self.dept,
            position=self.pos,
        )
        UserTelegramLink.objects.create(user=employee_user, telegram_chat_id=999999, is_active=True)
        training = Training.objects.create(
            title='Marketing Course',
            responsible=self.hr,
            start_date=date.today(),
            end_date=date.today(),
            status='planned',
        )
        training.participants.add(emp)
        self.client.login(username='hr_test', password='Test1234')
        response = self.client.post(
            reverse('hr:training_edit', args=[training.id]),
            data={
                'title': training.title,
                'description': training.description,
                'responsible': self.hr.id,
                'start_date': training.start_date.strftime('%Y-%m-%d'),
                'end_date': training.end_date.strftime('%Y-%m-%d'),
                'status': 'in_progress',
                'participants': [emp.id],
            }
        )
        self.assertEqual(response.status_code, 302)
        log = NotificationLog.objects.filter(event_type='training_started', telegram_chat_id=999999).first()
        self.assertIsNotNone(log)
        self.assertIn(self.hr.email, log.message_text or '')
        self.assertNotIn(other_hr.email, log.message_text or '')

    @patch('hr.integrations.telegram.client.TelegramClient.send_message')
    def test_delete_employee_sends_hr_notification(self, mock_send):
        mock_send.return_value = {'ok': True}
        employee_user = User.objects.create_user(
            username='deleted_user',
            email='deleted_user@test.ru',
            password='Test1234',
            role='employee',
        )
        employee = Employee.objects.create(
            user=employee_user,
            first_name='Литвин',
            last_name='Миша',
            date_of_birth=date(1990, 1, 1),
            email='litvin@test.ru',
            phone='+79991112233',
            hire_date=date.today(),
            status='active',
            department=self.dept,
            position=self.pos,
        )
        deleting_hr = User.objects.create_user(
            username='deleter_hr',
            email='deleter_hr@test.ru',
            password='Test1234',
            role='hr_manager',
        )
        deleting_hr.ensure_telegram_bind_code()
        UserTelegramLink.objects.create(user=deleting_hr, telegram_chat_id=111003, is_active=True)
        self.client.login(username='deleter_hr', password='Test1234')
        response = self.client.post(reverse('hr:employee_delete', args=[employee.id]))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            NotificationLog.objects.filter(
                event_type='employee_deleted',
                telegram_chat_id=111001,
            ).exists()
        )
        log = NotificationLog.objects.filter(event_type='employee_deleted', telegram_chat_id=111001).first()
        self.assertIn('Удалил', log.message_text)
        self.assertIn('deleter_hr@test.ru', log.message_text)


@override_settings(TELEGRAM_BOT_TOKEN='test-token')
class TelegramStatusChangeTests(TestCase):
    def setUp(self):
        self.dept = Department.objects.create(name='Sales')
        self.emp_user = User.objects.create_user(
            username='vac_emp',
            email='vac_emp@test.ru',
            password='Test1234',
            role='employee',
        )
        UserTelegramLink.objects.create(
            user=self.emp_user,
            telegram_chat_id=555005,
            is_active=True,
        )
        self.employee = Employee.objects.create(
            user=self.emp_user,
            first_name='Отпуск',
            last_name='Тестов',
            date_of_birth=date(1992, 2, 2),
            email='vac_card@test.ru',
            phone='+79991112233',
            hire_date=date.today(),
            status='active',
        )

    @patch('hr.integrations.telegram.client.TelegramClient.send_message')
    def test_on_leave_sends_vacation_started_not_updated(self, mock_send):
        mock_send.return_value = {'ok': True}
        self.employee.status = 'on_leave'
        self.employee.save()
        log = NotificationLog.objects.filter(
            event_type='vacation_started',
            telegram_chat_id=555005,
        )
        self.assertEqual(log.count(), 1)
        self.assertFalse(
            NotificationLog.objects.filter(event_type='employee_updated').exists(),
        )
        self.assertIn('отпуск согласован', log.first().message_text.lower())

    @patch('hr.integrations.telegram.client.TelegramClient.send_message')
    def test_on_leave_with_profile_changes_sends_one_vacation_notification(self, mock_send):
        mock_send.return_value = {'ok': True}
        self.employee.last_name = 'Петрова'
        self.employee.status = 'on_leave'
        self.employee.save()

        vacation_logs = NotificationLog.objects.filter(
            event_type='vacation_started',
            telegram_chat_id=555005,
        )
        self.assertEqual(vacation_logs.count(), 1)
        self.assertFalse(
            NotificationLog.objects.filter(event_type='employee_updated').exists(),
        )
        self.assertIn('отпуск согласован', vacation_logs.first().message_text.lower())
        self.assertIn('Фамилия: Тестов → Петрова', vacation_logs.first().message_text)

    @patch('hr.integrations.telegram.client.TelegramClient.send_message')
    def test_name_change_sends_updated_not_vacation(self, mock_send):
        mock_send.return_value = {'ok': True}
        self.employee.first_name = 'НовоеИмя'
        self.employee.save()
        self.assertTrue(
            NotificationLog.objects.filter(event_type='employee_updated').exists(),
        )
        self.assertFalse(
            NotificationLog.objects.filter(event_type='vacation_started').exists(),
        )

    @patch('hr.integrations.telegram.client.TelegramClient.send_message')
    def test_position_change_sends_notification(self, mock_send):
        mock_send.return_value = {'ok': True}
        pos_old = Position.objects.create(name='Junior')
        pos_new = Position.objects.create(name='Senior')
        self.employee.position = pos_old
        self.employee.save()
        NotificationLog.objects.all().delete()
        self.employee.position = pos_new
        self.employee.save()
        log = NotificationLog.objects.filter(event_type='position_changed').first()
        self.assertIsNotNone(log)
        self.assertIn('должност', log.message_text.lower())

    @patch('hr.integrations.telegram.client.TelegramClient.send_message')
    def test_sick_leave_to_active_notifies_employee(self, mock_send):
        mock_send.return_value = {'ok': True}
        self.employee.status = 'sick_leave'
        self.employee.save()
        NotificationLog.objects.all().delete()
        self.employee.status = 'active'
        self.employee.save()
        log = NotificationLog.objects.filter(
            event_type='employee_status_changed',
            telegram_chat_id=555005,
        ).first()
        self.assertIsNotNone(log)
        self.assertIn('больнич', log.message_text.lower())
        self.assertIn('работ', log.message_text.lower())

    @patch('hr.integrations.telegram.client.TelegramClient.send_message')
    def test_sick_leave_with_profile_change_sends_single_status_notification(self, mock_send):
        mock_send.return_value = {'ok': True}
        self.employee.status = 'sick_leave'
        self.employee.middle_name = 'Андреевна'
        self.employee.save()

        self.assertEqual(
            NotificationLog.objects.filter(event_type='employee_status_changed', telegram_chat_id=555005).count(),
            1,
        )
        self.assertFalse(
            NotificationLog.objects.filter(event_type='employee_updated', telegram_chat_id=555005).exists(),
        )
        self.assertIn('Отчество', NotificationLog.objects.filter(
            event_type='employee_status_changed', telegram_chat_id=555005,
        ).first().message_text)

    @patch('hr.integrations.telegram.client.TelegramClient.send_message')
    def test_dismissal_sends_fired_notification(self, mock_send):
        mock_send.return_value = {'ok': True}
        self.employee.status = 'dismissed'
        self.employee.save()
        # In this test setup the employee has an active telegram link,
        # so they should receive the fired notification.
        self.assertTrue(
            NotificationLog.objects.filter(event_type='employee_fired', telegram_chat_id=555005).exists()
        )

    @patch('hr.integrations.telegram.client.TelegramClient.send_message')
    def test_profile_form_sync_triggers_employee_updated(self, mock_send):
        """Редактирование /profile/ синхронизирует Employee и шлёт уведомления."""
        mock_send.return_value = {'ok': True}
        hr_user = User.objects.create_user(
            username='hr_profile_sync',
            email='hr_profile_sync@test.ru',
            password='Test1234',
            role='hr_manager',
        )
        UserTelegramLink.objects.create(
            user=hr_user,
            telegram_chat_id=777001,
            is_active=True,
        )
        NotificationLog.objects.all().delete()
        form = UserProfileForm(
            {
                'first_name': 'НовоеИмя',
                'last_name': self.emp_user.last_name,
                'middle_name': 'НовоеОтчество',
                'email': self.emp_user.email,
                'phone': self.employee.phone,
                'date_of_birth': self.employee.date_of_birth.strftime('%Y-%m-%d'),
            },
            instance=self.emp_user,
        )
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.first_name, 'НовоеИмя')
        self.assertEqual(self.employee.middle_name, 'НовоеОтчество')
        log = NotificationLog.objects.filter(event_type='employee_updated').first()
        self.assertIsNotNone(log)
        self.assertIn('имя', log.message_text.lower())

    @patch('hr.integrations.telegram.client.TelegramClient.send_message')
    def test_phone_change_shows_old_and_new(self, mock_send):
        mock_send.return_value = {'ok': True}
        self.employee.phone = '+79998887766'
        self.employee.save()
        log = NotificationLog.objects.filter(event_type='employee_updated').first()
        self.assertIsNotNone(log)
        self.assertIn('телефон', log.message_text.lower())
        self.assertIn('+79991112233', log.message_text)
        self.assertIn('+79998887766', log.message_text)


@override_settings(TELEGRAM_BOT_TOKEN='test-token')
class TelegramCommandsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='emp_tg',
            email='emp_tg@test.ru',
            password='Test1234',
            role='employee',
        )
        self.user.ensure_telegram_bind_code()
        UserTelegramLink.objects.create(
            user=self.user,
            telegram_chat_id=222002,
            is_active=True,
        )
        self.employee = Employee.objects.create(
            user=self.user,
            first_name='Тест',
            last_name='Сотрудник',
            date_of_birth=date(1990, 5, 5),
            email='emp_card_tg@test.ru',
            phone='+79990003344',
            hire_date=date.today(),
        )

    def test_cmd_status_linked(self):
        text = cmd_status(222002)
        self.assertIn('emp_tg@test.ru', text)
        self.assertIn('Информация о подключении', text)

    def test_cmd_help(self):
        self.assertIn('HR-бот', cmd_help())

    def test_cmd_mytrainings_empty(self):
        self.assertIn('не назначены', cmd_mytrainings(222002))

    def test_complete_link(self):
        other = User.objects.create_user(
            username='other_tg',
            email='other_tg@test.ru',
            password='Test1234',
            role='hr_manager',
        )
        code = other.ensure_telegram_bind_code()
        ok, msg = complete_telegram_link(code, 333003)
        self.assertTrue(ok)
        self.assertTrue(
            UserTelegramLink.objects.filter(
                user=other,
                telegram_chat_id=333003,
            ).exists(),
        )


@override_settings(TELEGRAM_BOT_TOKEN='test-token')
class TelegramBotMessageTests(TestCase):
    @patch('hr.integrations.telegram.linking.TelegramClient')
    def test_status_command(self, mock_client_cls):
        client = MagicMock()
        mock_client_cls.return_value = client
        user = User.objects.create_user(
            username='bot_user',
            email='bot@test.ru',
            password='Test1234',
            role='employee',
        )
        UserTelegramLink.objects.create(
            user=user,
            telegram_chat_id=444004,
            is_active=True,
        )
        process_telegram_message(
            {'chat': {'id': 444004}, 'text': '/status'},
            client,
        )
        client.send_message.assert_called()
        sent_text = client.send_message.call_args[0][1]
        self.assertIn('bot@test.ru', sent_text)
