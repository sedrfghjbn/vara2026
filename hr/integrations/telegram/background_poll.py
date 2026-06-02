"""Автозапуск Telegram polling вместе с runserver (только DEBUG)."""

import logging
import os
import threading

logger = logging.getLogger('hr.integrations.telegram')

_thread_started = False


def start_background_polling():
    global _thread_started
    if _thread_started:
        return
    _thread_started = True

    def _runner():
        from hr.integrations.telegram.poll_runner import run_poll_loop
        run_poll_loop(timeout=30)

    thread = threading.Thread(
        target=_runner,
        name='telegram-auto-poll',
        daemon=True,
    )
    thread.start()
    logger.info('Telegram background polling thread started')
