"""Установка Telegram webhook."""

from django.core.management.base import BaseCommand
from django.urls import reverse

from django.conf import settings

from hr.integrations.telegram.client import TelegramClient


class Command(BaseCommand):
    help = 'Установить Telegram webhook URL'

    def add_arguments(self, parser):
        parser.add_argument(
            'base_url',
            help='Базовый URL сайта, например https://example.com',
        )

    def handle(self, *args, **options):
        client = TelegramClient()
        if not client.enabled:
            self.stderr.write(self.style.ERROR('TELEGRAM_BOT_TOKEN не задан в .env'))
            return

        base = options['base_url'].rstrip('/')
        path = reverse('hr:telegram_webhook')
        webhook_url = f'{base}{path}'

        secret = getattr(settings, 'TELEGRAM_WEBHOOK_SECRET', '') or None
        result = client.set_webhook(webhook_url, secret_token=secret)
        self.stdout.write(self.style.SUCCESS(f'Webhook set: {webhook_url}'))
        self.stdout.write(str(result))
