"""
Módulo de logging para o sistema BR_SERVICE.
Configura e gerencia os logs da aplicação.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class LoggerConfig:
    """Configuração do sistema de logging."""
    
    def __init__(self, 
                 log_level: str = "INFO",
                 log_dir: str = "logs",
                 log_filename: Optional[str] = None,
                 console_output: bool = True):
        """
        Inicializa a configuração do logger.
        
        Args:
            log_level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Diretório para salvar os arquivos de log
            log_filename: Nome do arquivo de log (se None, usa timestamp)
            console_output: Se deve exibir logs no console
        """
        self.log_level = getattr(logging, log_level.upper())
        self.log_dir = Path(log_dir)
        self.console_output = console_output
        
        # Cria o diretório de logs se não existir
        self.log_dir.mkdir(exist_ok=True)
        
        # Define o nome do arquivo de log
        if log_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_filename = f"br_service_{timestamp}.log"
        else:
            self.log_filename = log_filename
        
        self.log_filepath = self.log_dir / self.log_filename
    
    def setup_logger(self, logger_name: str = "br_service") -> logging.Logger:
        """
        Configura e retorna o logger.
        
        Args:
            logger_name: Nome do logger
            
        Returns:
            Logger configurado
        """
        logger = logging.getLogger(logger_name)
        logger.setLevel(self.log_level)
        
        # Remove handlers existentes para evitar duplicação
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Formato das mensagens de log
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler para arquivo
        file_handler = logging.FileHandler(
            self.log_filepath, 
            encoding='utf-8'
        )
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Handler para console (se habilitado)
        if self.console_output:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.log_level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        return logger


class UserFriendlyLogger:
    """
    Logger amigável para o usuário final.
    Fornece mensagens de log formatadas para exibição na UI.
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Inicializa o logger amigável.
        
        Args:
            logger: Logger base para registrar mensagens técnicas
        """
        self.logger = logger
        self.user_messages = []
    
    def info_user(self, message: str, technical_details: str = None):
        """
        Registra uma mensagem informativa para o usuário.
        
        Args:
            message: Mensagem amigável para o usuário
            technical_details: Detalhes técnicos para o log
        """
        self.user_messages.append(f"ℹ️ {message}")
        log_msg = f"[USER INFO] {message}"
        if technical_details:
            log_msg += f" | Detalhes: {technical_details}"
        self.logger.info(log_msg)
    
    def success_user(self, message: str, technical_details: str = None):
        """
        Registra uma mensagem de sucesso para o usuário.
        
        Args:
            message: Mensagem amigável para o usuário
            technical_details: Detalhes técnicos para o log
        """
        self.user_messages.append(f"✅ {message}")
        log_msg = f"[USER SUCCESS] {message}"
        if technical_details:
            log_msg += f" | Detalhes: {technical_details}"
        self.logger.info(log_msg)
    
    def warning_user(self, message: str, technical_details: str = None):
        """
        Registra uma mensagem de aviso para o usuário.
        
        Args:
            message: Mensagem amigável para o usuário
            technical_details: Detalhes técnicos para o log
        """
        self.user_messages.append(f"⚠️ {message}")
        log_msg = f"[USER WARNING] {message}"
        if technical_details:
            log_msg += f" | Detalhes: {technical_details}"
        self.logger.warning(log_msg)
    
    def error_user(self, message: str, technical_details: str = None):
        """
        Registra uma mensagem de erro para o usuário.
        
        Args:
            message: Mensagem amigável para o usuário
            technical_details: Detalhes técnicos para o log
        """
        self.user_messages.append(f"❌ {message}")
        log_msg = f"[USER ERROR] {message}"
        if technical_details:
            log_msg += f" | Detalhes: {technical_details}"
        self.logger.error(log_msg)
    
    def progress_user(self, message: str, percentage: int = None):
        """
        Registra uma mensagem de progresso para o usuário.
        
        Args:
            message: Mensagem de progresso
            percentage: Percentual de progresso (0-100)
        """
        if percentage is not None:
            formatted_message = f"🔄 {message} ({percentage}%)"
        else:
            formatted_message = f"🔄 {message}"
        
        self.user_messages.append(formatted_message)
        self.logger.info(f"[USER PROGRESS] {message} | Progresso: {percentage}%")
    
    def get_user_messages(self) -> list:
        """
        Retorna todas as mensagens para o usuário.
        
        Returns:
            Lista de mensagens formatadas para o usuário
        """
        return self.user_messages.copy()
    
    def clear_user_messages(self):
        """Limpa as mensagens do usuário."""
        self.user_messages.clear()


# Instância global do logger
_logger_config = None
_logger = None
_user_logger = None


def get_logger(log_level: str = "INFO") -> logging.Logger:
    """
    Retorna o logger configurado.
    
    Args:
        log_level: Nível de log
        
    Returns:
        Logger configurado
    """
    global _logger_config, _logger
    
    if _logger is None:
        _logger_config = LoggerConfig(log_level=log_level)
        _logger = _logger_config.setup_logger()
    
    return _logger


def get_user_logger(log_level: str = "INFO") -> UserFriendlyLogger:
    """
    Retorna o logger amigável para o usuário.
    
    Args:
        log_level: Nível de log
        
    Returns:
        Logger amigável configurado
    """
    global _user_logger
    
    if _user_logger is None:
        base_logger = get_logger(log_level)
        _user_logger = UserFriendlyLogger(base_logger)
    
    return _user_logger

