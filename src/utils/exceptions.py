"""
Módulo de exceções customizadas para o sistema BR_SERVICE.
Define exceções específicas para diferentes tipos de erros.
"""

from typing import Optional, List


class BRServiceException(Exception):
    """Exceção base para o sistema BR_SERVICE."""
    
    def __init__(self, message: str, details: Optional[str] = None):
        """
        Inicializa a exceção.
        
        Args:
            message: Mensagem principal do erro
            details: Detalhes adicionais do erro
        """
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def __str__(self) -> str:
        """Retorna a representação string da exceção."""
        if self.details:
            return f"{self.message}. Detalhes: {self.details}"
        return self.message


class ArquivoNaoEncontradoError(BRServiceException):
    """Exceção para quando um arquivo não é encontrado."""
    
    def __init__(self, caminho_arquivo: str):
        message = f"Arquivo não encontrado: {caminho_arquivo}"
        super().__init__(message)


class FormatoArquivoInvalidoError(BRServiceException):
    """Exceção para quando o formato do arquivo é inválido."""
    
    def __init__(self, formato_esperado: str, formato_encontrado: str):
        message = f"Formato de arquivo inválido. Esperado: {formato_esperado}, Encontrado: {formato_encontrado}"
        super().__init__(message)


class PlanilhaNaoEncontradaError(BRServiceException):
    """Exceção para quando uma planilha obrigatória não é encontrada."""
    
    def __init__(self, nome_planilha: str, planilhas_disponiveis: List[str]):
        message = f"Planilha '{nome_planilha}' não encontrada"
        details = f"Planilhas disponíveis: {', '.join(planilhas_disponiveis)}"
        super().__init__(message, details)


class ColunaNaoEncontradaError(BRServiceException):
    """Exceção para quando uma coluna obrigatória não é encontrada."""
    
    def __init__(self, nome_coluna: str, nome_planilha: str, colunas_disponiveis: List[str]):
        message = f"Coluna '{nome_coluna}' não encontrada na planilha '{nome_planilha}'"
        details = f"Colunas disponíveis: {', '.join(colunas_disponiveis)}"
        super().__init__(message, details)


class DadosVaziosError(BRServiceException):
    """Exceção para quando não há dados para processar no período selecionado."""
    
    def __init__(self, periodo: str = None):
        if periodo:
            message = f"Não há dados para processar no período selecionado: {periodo}"
        else:
            message = "Não há dados para processar no período selecionado"
        super().__init__(message)


class ValidacaoError(BRServiceException):
    """Exceção para erros de validação de dados."""
    
    def __init__(self, campo: str, valor: str, regra: str):
        message = f"Erro de validação no campo '{campo}'"
        details = f"Valor: {valor}, Regra: {regra}"
        super().__init__(message, details)


class ProcessamentoError(BRServiceException):
    """Exceção para erros durante o processamento de dados."""
    
    def __init__(self, etapa: str, detalhes: str):
        message = f"Erro durante o processamento na etapa: {etapa}"
        super().__init__(message, detalhes)


class GeracaoArquivoError(BRServiceException):
    """Exceção para erros durante a geração de arquivos."""
    
    def __init__(self, nome_arquivo: str, detalhes: str):
        message = f"Erro ao gerar arquivo: {nome_arquivo}"
        super().__init__(message, detalhes)


class ConfiguracaoError(BRServiceException):
    """Exceção para erros de configuração."""
    
    def __init__(self, parametro: str, detalhes: str):
        message = f"Erro de configuração no parâmetro: {parametro}"
        super().__init__(message, detalhes)

