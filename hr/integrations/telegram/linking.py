"""Привязка Telegram и обработка входящих сообщений (/start, команды, кнопки)."""

import logging
import re

from django.contrib.auth import get_user_model

from .client import TelegramClient
from .commands import cmd_help, cmd_mytrainings, cmd_status
from .menu import get_main_keyboard, process_menu_button
from .models import EmployeeTelegramLink, TelegramLinkSession, UserTelegramLink

logger = logging.getLogger('hr.integrations.telegram')
User = get_user_model()

START_PATTERN = re.compile(r'^/start(?:@\w+)?(?:\s+.*)?$', re.IGNORECASE)
COMMAND_PATTERN = re.compile(
    r'^/(status|help|mytrainings)(?:@\w+)?\s*$',
    re.IGNORECASE,
)
CODE_PATTERN = re.compile(r'^[A-Za-z0-9_-]{6,16}$')
MENU_BUTTONS = ['📄 Мой профиль', '🎓 Мои обучения', '📞 HR', 'ℹ️ Помощь']


def get_user_bind_code(user):
    """Постоянный код привязки пользователя (не меняется)."""
    return user.ensure_telegram_bind_code()


def complete_telegram_link(code: str, chat_id: int, client=None):
    """
    Завершает привязку chat_id к пользователю/сотруднику.
    Returns (success, message).
    """
    code = code.strip().upper()
    user = User.objects.filter(telegram_bind_code__iexact=code).first()

    if not user:
        return False, (
            '❌ Код не найден\n\n'
            'Проверьте код в профиле HR-системы и попробуйте ещё раз.'
        )

    employee = None
    try:
        employee = user.employee_profile
    except Exception:
        pass

    UserTelegramLink.objects.update_or_create(
        user=user,
        defaults={'telegram_chat_id': chat_id, 'is_active': True},
    )

    if employee:
        EmployeeTelegramLink.objects.update_or_create(
            employee=employee,
            defaults={'telegram_chat_id': chat_id, 'is_active': True},
        )

    TelegramLinkSession.objects.filter(telegram_chat_id=chat_id).delete()

    logger.info('Telegram linked: user=%s chat_id=%s', user.pk, chat_id)
    return True, (
        '🎉 Готово!\n\n'
        'Ваш Telegram успешно подключён к HR-системе.\n\n'
        'Теперь вы будете получать все уведомления автоматически.'
    )


def _send(client, chat_id, text, parse_mode=None):
    client.send_message(chat_id, text, parse_mode=parse_mode)


def _start_link_session(chat_id):
    TelegramLinkSession.objects.update_or_create(
        telegram_chat_id=chat_id,
        defaults={'awaiting_code': True},
    )


def _is_awaiting_code(chat_id):
    return TelegramLinkSession.objects.filter(
        telegram_chat_id=chat_id,
        awaiting_code=True,
    ).exists()


def _handle_start(chat_id, client):
    existing = UserTelegramLink.objects.filter(
        telegram_chat_id=chat_id,
        is_active=True,
    ).select_related('user').first()

    if existing:
        try:
            from .menu import handle_my_profile
            profile_text = handle_my_profile(chat_id)
            client.send_message(
                chat_id,
                profile_text,
                reply_markup=get_main_keyboard(),
                parse_mode='HTML',
            )
        except Exception:
            _send(
                client,
                chat_id,
                '✅ Аккаунт подключён\n\n'
                f'📧 {existing.user.email}',
                parse_mode=None,
            )
        _start_link_session(chat_id)
        return

    _start_link_session(chat_id)
    _send(
        client,
        chat_id,
        '👋 Добро пожаловать в HR-бот.\n\n'
        'Чтобы получать уведомления, отправьте код привязки '
        'из своего профиля в HR-системе.',
        parse_mode=None,
    )


def _handle_code_input(chat_id, code_text, client):
    if not CODE_PATTERN.match(code_text.strip()):
        _send(
            client,
            chat_id,
            '⚠️ Неверный формат кода\n\n'
            'Скопируйте код из профиля HR-системы и отправьте его одним сообщением.',
            parse_mode=None,
        )
        return False

    success, reply = complete_telegram_link(code_text, chat_id, client)
    client.send_message(
        chat_id,
        reply,
        reply_markup=get_main_keyboard() if success else None,
        parse_mode=None,
    )
    return success


def _handle_command(chat_id, command_name, client):
    command_name = command_name.lower()
    if command_name == 'status':
        text = cmd_status(chat_id)
    elif command_name == 'mytrainings':
        text = cmd_mytrainings(chat_id)
    else:
        text = cmd_help()
    _send(client, chat_id, text, parse_mode=None)


def process_telegram_message(message: dict, client):
    chat = message.get('chat', {})
    chat_id = chat.get('id')
    text = (message.get('text') or '').strip()

    if not chat_id or not text:
        return

    if START_PATTERN.match(text):
        _handle_start(chat_id, client)
        return

    # Обработка кнопок главного меню
    if text in MENU_BUTTONS:
        linked = UserTelegramLink.objects.filter(
            telegram_chat_id=chat_id,
            is_active=True,
        ).exists()
        if linked:
            if process_menu_button(chat_id, text, client):
                return

    command_match = COMMAND_PATTERN.match(text)
    if command_match:
        _handle_command(chat_id, command_match.group(1), client)
        return

    if text.startswith('/'):
        _send(
            client,
            chat_id,
            '🤔 Команда не распознана\n\n'
            'Доступные команды:\n'
            '• /status\n'
            '• /mytrainings\n'
            '• /help',
            parse_mode=None,
        )
        return

    if _is_awaiting_code(chat_id):
        _handle_code_input(chat_id, text, client)
        return

    linked = UserTelegramLink.objects.filter(
        telegram_chat_id=chat_id,
        is_active=True,
    ).exists()
    if linked:
        _send(
            client,
            chat_id,
            'Используйте команды: /status /mytrainings /help\n'
            'или нажимайте кнопки меню снизу.',
            parse_mode=None,
        )
    else:
        _send(
            client,
            chat_id,
            'Для привязки аккаунта отправьте /start',
            parse_mode=None,
        )


def process_telegram_update(update: dict, client=None):
    """Обрабатывает входящее update от Telegram (webhook / polling)."""
    client = client or TelegramClient()

    message = update.get('message') or update.get('edited_message')
    if not message:
        return

    try:
        process_telegram_message(message, client)
    except Exception as exc:
        logger.exception('Telegram update processing error: %s', exc)
