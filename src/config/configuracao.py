"""
configuracao.py

Gerencia as configurações da aplicação BR Service.
- Lê JSON de config (ou cria um padrão se não existir).
- Expande variáveis de ambiente nos valores.
- Permite sobrescrever chaves por variáveis de ambiente prefixadas (BR_SERVICE_...).
"""

from __future__ import annotations

import json
import os
import sys
import logging
from pathlib import Path
from typing import Any, Dict
from platformdirs import user_config_dir

ENV_PREFIX = "BR_SERVICE_"

DEFAULTS: Dict[str, Any] = {
    "diretorio_logs": "logs",
    "nivel_log": "INFO",
    "formato_data_excel": "%d/%m/%Y",
    "colunas_saida": ["Contrato", "Valor", "Emissão", "Vencimento", "Competência"],
}


def _coerce_env_value(val: str) -> Any:
    """Converte string de env em tipos úteis: bool, int, float, list (CSV) ou JSON."""
    s = val.strip()
    if s.lower() in {"true", "false"}:
        return s.lower() == "true"
    try:
        return int(s)
    except Exception:
        pass
    try:
        return float(s)
    except Exception:
        pass
    if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
        try:
            return json.loads(s)
        except Exception:
            pass
    if "," in s:
        return [p.strip() for p in s.split(",")]
    return s


def _expand_value(v: Any) -> Any:
    """Expande variáveis de ambiente em strings; mantém outros tipos."""
    if isinstance(v, str):
        return os.path.expandvars(v)
    if isinstance(v, list):
        return [_expand_value(x) for x in v]
    if isinstance(v, dict):
        return {k: _expand_value(x) for k, x in v.items()}
    return v


def get_log_level(level: str | int, default=logging.INFO) -> int:
    """Converte 'INFO' → logging.INFO. Se int, retorna direto."""
    if isinstance(level, int):
        return level
    table = {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "NOTSET": logging.NOTSET,
    }
    return table.get(str(level).upper(), default)


def _is_frozen() -> bool:
    """Retorna True quando rodando como executável PyInstaller."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def _bundle_dir() -> Path:
    """
    Diretório base do bundle PyInstaller (somente leitura).
    Em modo dev, usa a pasta do próprio arquivo.
    """
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


class Configuracao:
    """
    Carrega configs a partir de:
    1) Config do usuário (gravável) em %APPDATA%/BR_SERVICE/config.json (Windows) ou equivalente no SO.
    2) Config empacotada no executável (somente leitura), se existir.
    3) DEFAULTS (fallback).
    Overrides por env (prefixo BR_SERVICE_).
    """

    def __init__(self, caminho_config: str | os.PathLike[str] | None = None, app_name: str = "BR_SERVICE") -> None:
        self.app_name = app_name
        # Caminho gravável do usuário
        self.user_config_dir = Path(user_config_dir(app_name, app_name))
        self.user_config_path = self.user_config_dir / "config.json"

        # Caminho passado ou padrão (para modo não-frozen/DEV)
        if caminho_config:
            self.dev_config_path = Path(caminho_config)
        else:
            # raiz do projeto em dev: .../src/config/configuracao.py -> sobe 3 níveis
            self.dev_config_path = Path(__file__).resolve().parent.parent.parent / "config.json"

        # Caminho empacotado (read-only) no bundle (quando frozen)
        self.bundle_config_path = _bundle_dir() / "config.json"

        self.config: Dict[str, Any] = {}
        self._carregar_configuracao()

    def _carregar_configuracao(self) -> None:
        base: Dict[str, Any] = DEFAULTS.copy()

        # 1) Tente carregar config do usuário (gravável)
        if self.user_config_path.exists():
            try:
                base.update(json.loads(self.user_config_path.read_text(encoding="utf-8")))
            except Exception:
                # se corrompido, ignora e continua com defaults/bundle
                pass
        else:
            # 2) Se não há config do usuário, tente o empacotado (somente leitura) ou o dev
            src = None
            if _is_frozen() and self.bundle_config_path.exists():
                src = self.bundle_config_path
            elif self.dev_config_path.exists():
                src = self.dev_config_path

            if src:
                try:
                    base.update(json.loads(src.read_text(encoding="utf-8")))
                except Exception:
                    pass
                # Cria a cópia do usuário na primeira execução (em local gravável)
                try:
                    self.user_config_dir.mkdir(parents=True, exist_ok=True)
                    self.user_config_path.write_text(json.dumps(base, indent=2, ensure_ascii=False), encoding="utf-8")
                except Exception:
                    # se não conseguir escrever, segue apenas em memória
                    pass
            else:
                # nenhum arquivo encontrado; cria o do usuário com DEFAULTS
                try:
                    self.user_config_dir.mkdir(parents=True, exist_ok=True)
                    self.user_config_path.write_text(json.dumps(base, indent=2, ensure_ascii=False), encoding="utf-8")
                except Exception:
                    pass

        # 3) Overrides por variáveis de ambiente
        for key in list(base.keys()):
            env_key = ENV_PREFIX + key.upper()
            if env_key in os.environ:
                base[key] = _coerce_env_value(os.environ[env_key])

        # Expande variáveis de ambiente nos valores string
        self.config = _expand_value(base)

    def obter_config(self, chave: str, valor_padrao: Any = None) -> Any:
        return self.config.get(chave, valor_padrao)

    def definir_config(self, chave: str, valor: Any) -> None:
        """Grava somente na config do usuário (gravável)."""
        self.config[chave] = valor
        try:
            self.user_config_dir.mkdir(parents=True, exist_ok=True)
            self.user_config_path.write_text(json.dumps(self.config, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            # mantém em memória se não der para gravar
            pass
