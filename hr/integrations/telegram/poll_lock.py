"""Единственный экземпляр Telegram polling на машине (избегает HTTP 409)."""

import fcntl
import os
from pathlib import Path

from django.conf import settings

LOCK_PATH = Path(settings.BASE_DIR) / '.telegram_poll.lock'


class TelegramPollLock:
    """Неперекрывающаяся блокировка: только один getUpdates на токен бота."""

    def __init__(self):
        self._fd = None
        self.acquired = False

    def acquire(self):
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._fd = open(LOCK_PATH, 'w')
        try:
            fcntl.flock(self._fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self._fd.close()
            self._fd = None
            return False
        self._fd.write(str(os.getpid()))
        self._fd.flush()
        self.acquired = True
        return True

    def release(self):
        if not self._fd or not self.acquired:
            return
        try:
            fcntl.flock(self._fd.fileno(), fcntl.LOCK_UN)
            self._fd.close()
        finally:
            self._fd = None
            self.acquired = False

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError('telegram_poll_lock_busy')
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
        return False
