"""Сервис отправки Telegram-уведомлений."""

import logging
from dataclasses import dataclass

from django.utils import timezone

from .client import TelegramAPIError, TelegramClient
from .formatter import format_notification
from .keyboards import build_event_keyboard
from .models import NotificationLog

logger = logging.getLogger('hr.integrations.telegram')


@dataclass
class SendTarget:
    chat_id: int
    recipient_role: str
    user: object = None
    employee: object = None


class NotificationService:
    """Отправка уведомлений с логированием и retry (через TelegramClient)."""

    def __init__(self, client=None):
        self.client = client or TelegramClient()

    def send_to_target(self, event_type, target: SendTarget, payload: dict):
        message = format_notification(event_type, payload, target.recipient_role)
        reply_markup = build_event_keyboard(
            event_type, payload, target.recipient_role,
        )

        log_entry = NotificationLog.objects.create(
            event_type=event_type,
            recipient_role=target.recipient_role,
            recipient_user=target.user,
            recipient_employee=target.employee,
            telegram_chat_id=target.chat_id,
            message_text=message,
            status=NotificationLog.STATUS_PENDING,
            payload=payload,
        )

        if not self.client.enabled:
            log_entry.status = NotificationLog.STATUS_FAILED
            log_entry.error_message = 'TELEGRAM_BOT_TOKEN не настроен'
            log_entry.attempt_count = 0
            log_entry.save(update_fields=['status', 'error_message'])
            logger.error('Notification skipped: bot token missing (%s)', event_type)
            return log_entry

        try:
            self.client.send_message(
                target.chat_id,
                message,
                reply_markup=reply_markup,
            )
            log_entry.status = NotificationLog.STATUS_SENT
            log_entry.sent_at = timezone.now()
            log_entry.attempt_count = self.client.MAX_RETRIES + 1
            log_entry.save(update_fields=['status', 'sent_at', 'attempt_count'])
            logger.info(
                'Notification sent: %s → chat_id=%s role=%s',
                event_type,
                target.chat_id,
                target.recipient_role,
            )
        except TelegramAPIError as exc:
            log_entry.status = NotificationLog.STATUS_FAILED
            log_entry.error_message = str(exc)[:2000]
            log_entry.attempt_count = self.client.MAX_RETRIES + 1
            log_entry.save(update_fields=['status', 'error_message', 'attempt_count'])
            logger.exception(
                'Notification failed: %s → chat_id=%s: %s',
                event_type,
                target.chat_id,
                exc,
            )
        except Exception as exc:
            log_entry.status = NotificationLog.STATUS_FAILED
            log_entry.error_message = str(exc)[:2000]
            log_entry.save(update_fields=['status', 'error_message'])
            logger.exception('Unexpected notification error: %s', exc)

        return log_entry

    def send_bulk(self, event_type, targets, payload: dict):
        """Массовая отправка (последовательно, готово к async-обёртке)."""
        results = []
        for target in targets:
            try:
                results.append(self.send_to_target(event_type, target, payload))
            except Exception as exc:
                logger.exception('Bulk send error for chat_id=%s: %s', target.chat_id, exc)
        return results
