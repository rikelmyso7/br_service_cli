from enum import Enum
from typing import Any, Dict, List, Optional


class StatusProcessamento(Enum):
    SUCESSO = "sucesso"
    ERRO = "erro"
    AVISO = "aviso"
    CONCLUIDO = "concluido"
    EM_ANDAMENTO = "em_andamento"


class ProcessamentoResponse:
    def __init__(self,
                 status: StatusProcessamento,
                 etapa: str,
                 mensagens_sucesso: Optional[List[str]] = None,
                 mensagens_erro: Optional[List[str]] = None,
                 mensagens_aviso: Optional[List[str]] = None,
                 dados: Optional[Dict[str, Any]] = None):
        self.status = status
        self.etapa = etapa
        self.mensagens_sucesso = mensagens_sucesso if mensagens_sucesso is not None else []
        self.mensagens_erro = mensagens_erro if mensagens_erro is not None else []
        self.mensagens_aviso = mensagens_aviso if mensagens_aviso is not None else []
        self.dados = dados if dados is not None else {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "etapa": self.etapa,
            "mensagens": {
                "sucesso": self.mensagens_sucesso,
                "erro": self.mensagens_erro,
                "aviso": self.mensagens_aviso
            },
            "dados": self.dados
        }


class JSONResponseBuilder:
    def __init__(self):
        self._response: Dict[str, Any] = {
            "status": StatusProcessamento.EM_ANDAMENTO.value,
            "etapa": "Inicial",
            "mensagens": {
                "sucesso": [],
                "erro": [],
                "aviso": []
            },
            "dados": {}
        }

    def set_status(self, status: StatusProcessamento) -> 'JSONResponseBuilder':
        self._response["status"] = status.value
        return self

    def set_etapa(self, etapa: str) -> 'JSONResponseBuilder':
        self._response["etapa"] = etapa
        return self

    def add_sucesso(self, mensagem: str) -> 'JSONResponseBuilder':
        self._response["mensagens"]["sucesso"].append(mensagem)
        return self

    def add_erro(self, mensagem: str) -> 'JSONResponseBuilder':
        self._response["mensagens"]["erro"].append(mensagem)
        return self

    def add_aviso(self, mensagem: str) -> 'JSONResponseBuilder':
        self._response["mensagens"]["aviso"].append(mensagem)
        return self

    def add_dados(self, chave: str, valor: Any) -> 'JSONResponseBuilder':
        self._response["dados"][chave] = valor
        return self

    def build(self) -> Dict[str, Any]:
        return self._response



