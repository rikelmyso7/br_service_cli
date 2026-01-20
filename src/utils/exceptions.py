"""
exceptions.py

Define exceções personalizadas para o sistema BR Service, com códigos e
método de serialização para dicionário (útil para retornar JSON no CLI/API).
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class BRServiceError(Exception):
    """
    Exceção base para erros específicos do sistema BR Service.

    Atributos:
        codigo: código curto do erro (ex.: 'LEITURA_ARQUIVO').
        mensagem: mensagem amigável/explicativa.
        detalhes: payload opcional com metadados adicionais.
    """
    codigo_padrao = "BR_SERVICE_ERRO"

    def __init__(self, mensagem: str = "Ocorreu um erro no sistema BR Service.",
                 codigo: Optional[str] = None,
                 detalhes: Optional[Dict[str, Any]] = None) -> None:
        self.codigo = codigo or self.codigo_padrao
        self.mensagem = mensagem
        self.detalhes = detalhes or {}
        super().__init__(self.mensagem)

    def __str__(self) -> str:
        return f"[{self.codigo}] {self.mensagem}"

    def to_dict(self) -> Dict[str, Any]:
        """
        Representação serializável (ex.: para JSON).
        """
        out = {"codigo": self.codigo, "mensagem": self.mensagem}
        if self.detalhes:
            out["detalhes"] = self.detalhes
        return out


class ErroLeituraArquivo(BRServiceError):
    """Erro ao ler o arquivo."""
    codigo_padrao = "LEITURA_ARQUIVO"


class ErroProcessamentoDados(BRServiceError):
    """Erro no processamento dos dados."""
    codigo_padrao = "PROCESSAMENTO_DADOS"


class ErroValidacaoDados(BRServiceError):
    """Erro na validação dos dados."""
    codigo_padrao = "VALIDACAO_DADOS"


class ErroGeracaoArquivo(BRServiceError):
    """Erro na geração do arquivo de saída."""
    codigo_padrao = "GERACAO_ARQUIVO"


class ErroConfiguracao(BRServiceError):
    """Erro nas configurações da aplicação."""
    codigo_padrao = "CONFIGURACAO"
