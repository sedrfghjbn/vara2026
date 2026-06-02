from django.apps import AppConfig


class HrConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hr'
    verbose_name = 'HR система'

    def ready(self):
        import os

        import hr.integrations.telegram.models  # noqa: F401
        import hr.signals  # noqa: F401

        from django.conf import settings

        if (
            settings.DEBUG
            and getattr(settings, 'TELEGRAM_AUTO_POLL', True)
            and getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
            and os.environ.get('RUN_MAIN') == 'true'
        ):
            from hr.integrations.telegram.background_poll import start_background_polling
            start_background_polling()