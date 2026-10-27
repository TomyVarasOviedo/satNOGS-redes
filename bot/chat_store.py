from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def read_chat_id(path: Path) -> int | None:
    try:
        raw = Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        logger.warning("El archivo de chat id '%s' no es un número", path)
        return None


def write_chat_id(path: Path, chat_id: int) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    try:
        temp.write_text(f"{chat_id}\n", encoding="utf-8")
        os.replace(temp, path)
    except OSError as exc:
        logger.warning("No se pudo guardar el chat id en %s: %s", path, exc)
        temp.unlink(missing_ok=True)


class ChatStore:
    """Chat destinatario de las alertas.

    Precedencia: TELEGRAM_CHAT_ID (bloqueado) > chat_id.txt > último chat que habló.
    """

    def __init__(self, path: Path, env_chat_id: int | None = None):
        self.path = Path(path)
        self._locked = env_chat_id is not None
        self._chat_id = env_chat_id if env_chat_id is not None else read_chat_id(self.path)

    @property
    def chat_id(self) -> int | None:
        return self._chat_id

    @property
    def locked(self) -> bool:
        return self._locked

    def remember(self, chat_id: int) -> bool:
        if self._locked:
            return False
        changed = self._chat_id != chat_id
        self._chat_id = chat_id
        if changed:
            write_chat_id(self.path, chat_id)
            logger.info("Chat de alertas guardado: %s", chat_id)
        return changed
