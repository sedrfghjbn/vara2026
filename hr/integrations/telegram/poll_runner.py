"""Фоновый long-polling для локальной разработки."""

import logging
import time

from hr.integrations.telegram.client import TelegramAPIError, TelegramClient
from hr.integrations.telegram.linking import process_telegram_update
from hr.integrations.telegram.poll_lock import TelegramPollLock

logger = logging.getLogger('hr.integrations.telegram')

POLL_LOCK_MESSAGE = (
    'Telegram polling уже запущен в другом процессе. '
    'Оставьте только один: либо runserver (авто-polling), либо telegram_poll — не оба сразу.'
)


def run_poll_loop(timeout=30, stdout_write=None):
    """
    Основной цикл polling. Используется management command и auto-poll.
    stdout_write — опциональный callable для вывода в консоль (management command).
    """
    def say(msg, style=None):
        if stdout_write:
            stdout_write(msg, style)
        else:
            if style == 'error':
                logger.error(msg)
            elif style == 'warning':
                logger.warning(msg)
            else:
                logger.info(msg)

    client = TelegramClient()
    if not client.enabled:
        say('TELEGRAM_BOT_TOKEN не задан в .env', 'error')
        return False

    poll_lock = TelegramPollLock()
    if not poll_lock.acquire():
        say(POLL_LOCK_MESSAGE, 'warning')
        return False

    try:
        try:
            me = client._request('getMe')
            bot_username = me.get('result', {}).get('username', '?')
            client.delete_webhook(drop_pending_updates=False)
            say(f'Telegram bot: @{bot_username} — polling активен', 'success')
        except TelegramAPIError as exc:
            if exc.status_code == 401 or '401' in str(exc):
                say(
                    'Ошибка 401: неверный TELEGRAM_BOT_TOKEN в .env. '
                    'Обновите токен и перезапустите сервер.',
                    'error',
                )
            else:
                say(f'Не удалось подключиться к Telegram: {exc}', 'error')
            return False
        except Exception as exc:
            say(f'Не удалось запустить polling: {exc}', 'error')
            return False

        offset = None
        while True:
            try:
                result = client.get_updates(offset=offset, timeout=timeout)
                for update in result.get('result', []):
                    update_id = update.get('update_id')
                    if update_id is not None:
                        offset = update_id + 1
                    try:
                        process_telegram_update(update, client=client)
                    except Exception as exc:
                        logger.exception('Polling update error: %s', exc)
            except KeyboardInterrupt:
                say('Polling остановлен.', 'warning')
                break
            except TelegramAPIError as exc:
                if exc.status_code == 401 or '401' in str(exc):
                    say('Ошибка 401: неверный токен. Остановка polling.', 'error')
                    return False
                if exc.status_code == 409 or '409' in str(exc):
                    say(POLL_LOCK_MESSAGE, 'warning')
                    return False
                logger.exception('Polling error: %s', exc)
                time.sleep(2)
            except Exception as exc:
                logger.exception('Polling error: %s', exc)
                time.sleep(2)
    finally:
        poll_lock.release()

    return True
