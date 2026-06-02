"""Webhook и HTTP-обработчики Telegram."""

import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .linking import process_telegram_update

logger = logging.getLogger('hr.integrations.telegram')


@csrf_exempt
@require_POST
def telegram_webhook(request):
    """POST /integrations/telegram/webhook/ — приём updates от Telegram."""
    secret = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', '')
    if secret:
        header_secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
        if header_secret != secret:
            logger.warning('Telegram webhook rejected: invalid secret token')
            return HttpResponse(status=403)

    try:
        update = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return HttpResponse(status=400)

    try:
        process_telegram_update(update)
    except Exception as exc:
        logger.exception('Telegram webhook processing error: %s', exc)

    return JsonResponse({'ok': True})
