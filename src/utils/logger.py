"""
logger.py

Configura e fornece um logger centralizado para o sistema BR Service.
- Evita handlers duplicados.
- Suporta arquivo de log (com criação de diretório).
- Suporte opcional a RotatingFileHandler.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
import json, sys

_HANDLER_KEYS: set[str] = set()  # para evitar duplicar handlers em reconfigurações

def emit_event(ev: str, *, msg: str | None = None, progress: float | None = None, **extra):
    """
    Emite uma linha JSON (NDJSON) no stdout com flush imediato.
    Ex.: {"event":"READ","msg":"Lendo ...","progress":0.10}
    """
    payload = {"event": ev, "ts": datetime.now(timezone.utc).isoformat()}
    if msg is not None:
        payload["msg"] = msg
    if progress is not None:
        # clamp e arredonda para estética
        progress = max(0.0, min(1.0, float(progress)))
        payload["progress"] = round(progress, 4)
    payload.update(extra)
    print(json.dumps(payload, ensure_ascii=False), flush=True)

def configurar_logger(
    nome_logger: str = "br_service",
    nivel: int | str = logging.INFO,
    caminho_log: Optional[str | os.PathLike[str]] = None,
    rotating: bool = False,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
) -> logging.Logger:
    """
    Configura e retorna uma instância de logger.

    Args:
        nome_logger: Nome do logger (namespace).
        nivel: nível mínimo de log (int ou "INFO"/"DEBUG"...).
        caminho_log: caminho para arquivo de log (se None, sem arquivo).
        rotating: se True, usa RotatingFileHandler.
        max_bytes: tamanho máximo do arquivo de log antes de rotacionar.
        backup_count: quantidade de arquivos de histórico mantidos.

    Returns:
        logging.Logger configurado.
    """
    if isinstance(nivel, str):
        from ..config.configuracao import get_log_level  # evita dependência circular no import global
        nivel = get_log_level(nivel)

    logger = logging.getLogger(nome_logger)
    logger.setLevel(nivel)
    logger.propagate = False  # não propagar para root para evitar logs duplicados no console

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(module)s:%(lineno)d | %(message)s"
    )

    # Console handler (sempre)
    console_key = f"{nome_logger}::console"
    if console_key not in _HANDLER_KEYS:
        ch = logging.StreamHandler()
        ch.setLevel(nivel)
        ch.setFormatter(fmt)
        logger.addHandler(ch)
        _HANDLER_KEYS.add(console_key)

    # File handler (opcional)
    if caminho_log:
        log_path = Path(caminho_log)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_key = f"{nome_logger}::file::{log_path.resolve()}::{rotating}"
        if file_key not in _HANDLER_KEYS:
            if rotating:
                fh = logging.handlers.RotatingFileHandler(
                    log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
                )
            else:
                fh = logging.FileHandler(log_path, encoding="utf-8")
            fh.setLevel(nivel)
            fh.setFormatter(fmt)
            logger.addHandler(fh)
            _HANDLER_KEYS.add(file_key)

    return logger
