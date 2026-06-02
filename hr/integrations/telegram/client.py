"""Telegram Bot API client with retry support."""

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger('hr.integrations.telegram')


class TelegramAPIError(Exception):
    def __init__(self, message, status_code=None, response_body=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class TelegramClient:
    """HTTP-клиент для Telegram Bot API (готов к замене на async)."""

    MAX_RETRIES = 2
    RETRY_DELAY_SECONDS = 0.5

    def __init__(self, token=None):
        self.token = token or getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        if not self.token:
            logger.warning('TELEGRAM_BOT_TOKEN не задан — отправка уведомлений отключена')

    @property
    def enabled(self):
        return bool(self.token)

    def _api_url(self, method):
        return f'https://api.telegram.org/bot{self.token}/{method}'

    def _request(self, method, payload=None, timeout=10):
        if not self.enabled:
            raise TelegramAPIError('Telegram bot token is not configured')

        url = self._api_url(method)
        data = json.dumps(payload or {}).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )

        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 2):
            try:
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    body = json.loads(response.read().decode('utf-8'))
                    if not body.get('ok'):
                        raise TelegramAPIError(
                            body.get('description', 'Unknown Telegram API error'),
                            response_body=body,
                        )
                    return body
            except urllib.error.HTTPError as exc:
                body_text = ''
                try:
                    body_text = exc.read().decode('utf-8')
                except Exception:
                    pass
                api_error = TelegramAPIError(
                    f'HTTP Error {exc.code}: {exc.reason}',
                    status_code=exc.code,
                    response_body=body_text,
                )
                # 409 Conflict — другой polling/webhook; retry бесполезен
                if exc.code in (409, 401):
                    raise api_error from exc
                last_error = api_error
                logger.warning(
                    'Telegram API %s attempt %s/%s failed: %s',
                    method,
                    attempt,
                    self.MAX_RETRIES + 1,
                    api_error,
                )
                if attempt <= self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY_SECONDS * attempt)
            except (urllib.error.URLError, TelegramAPIError, TimeoutError) as exc:
                last_error = exc
                logger.warning(
                    'Telegram API %s attempt %s/%s failed: %s',
                    method,
                    attempt,
                    self.MAX_RETRIES + 1,
                    exc,
                )
                if attempt <= self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY_SECONDS * attempt)

        raise TelegramAPIError(str(last_error))

    def send_message(self, chat_id, text, parse_mode='HTML', reply_markup=None):
        payload = {
            'chat_id': chat_id,
            'text': text,
            'disable_web_page_preview': True,
        }
        if parse_mode:
            payload['parse_mode'] = parse_mode
        if reply_markup:
            payload['reply_markup'] = reply_markup
        return self._request('sendMessage', payload)

    def answer_callback_query(self, callback_query_id, text=None, show_alert=False):
        payload = {
            'callback_query_id': callback_query_id,
            'show_alert': show_alert,
        }
        if text:
            payload['text'] = text[:200]
        return self._request('answerCallbackQuery', payload)

    def delete_webhook(self, drop_pending_updates=False):
        return self._request('deleteWebhook', {
            'drop_pending_updates': drop_pending_updates,
        })

    def get_updates(self, offset=None, timeout=30):
        payload = {'timeout': timeout}
        if offset is not None:
            payload['offset'] = offset
        return self._request('getUpdates', payload, timeout=timeout + 5)

    def set_webhook(self, url, secret_token=None):
        payload = {'url': url}
        if secret_token:
            payload['secret_token'] = secret_token
        return self._request('setWebhook', payload)
