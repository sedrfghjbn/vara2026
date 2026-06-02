"""Long-polling Telegram updates (для локальной разработки без webhook)."""

from django.core.management.base import BaseCommand

from hr.integrations.telegram.poll_runner import run_poll_loop


class Command(BaseCommand):
    help = 'Запуск long-polling Telegram Bot API для обработки /start <code>'

    def add_arguments(self, parser):
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Long-polling timeout в секундах',
        )

    def handle(self, *args, **options):
        def stdout_write(msg, style=None):
            if style == 'error':
                self.stderr.write(self.style.ERROR(msg))
            elif style == 'success':
                self.stdout.write(self.style.SUCCESS(msg))
            elif style == 'warning':
                self.stdout.write(self.style.WARNING(msg))
            else:
                self.stdout.write(msg)

        run_poll_loop(timeout=options['timeout'], stdout_write=stdout_write)
