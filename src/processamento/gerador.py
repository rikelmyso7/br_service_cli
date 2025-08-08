import pandas as pd
import os
from typing import Dict, List
from pathlib import Path

from ..utils.exceptions import ProcessamentoError
from ..utils.logger import get_logger, get_user_logger
from ..validacao.validador import ValidadorDados

logger = get_logger()
user_logger = get_user_logger()
validador = ValidadorDados()

def gerar_arquivos_saida(dados_processados: Dict[str, pd.DataFrame], pasta_destino: str) -> List[str]:
    """
    Gera arquivos de saída para cada combinação documento-plano financeiro.
    
    Args:
        dados_processados: Dicionário onde a chave é 'Documento-PlanoFinanceiro' e o valor é o DataFrame.
        pasta_destino: Caminho da pasta onde os arquivos serão salvos.
        
    Returns:
        Lista de caminhos dos arquivos gerados.
    """
    user_logger.progress_user("Iniciando geração de arquivos de saída...")
    logger.info(f"Iniciando geração de arquivos na pasta: {pasta_destino}")

    arquivos_gerados = []
    
    try:
        # Valida e cria a pasta de destino
        validacao_pasta_ok, mensagens_pasta = validador.validar_selecao_usuario(
            [], None, None, pasta_destino
        )
        for msg in mensagens_pasta:
            if "❌" in msg:
                user_logger.error_user(msg)
            elif "⚠️" in msg:
                user_logger.warning_user(msg)
            else:
                user_logger.info_user(msg)

        if not validacao_pasta_ok:
            raise ProcessamentoError("Geração de arquivos", f"Pasta de destino inválida: {pasta_destino}")

        if not dados_processados:
            user_logger.warning_user("Nenhum dado processado para gerar arquivos.")
            return []

        for chave, df_saida in dados_processados.items():
            documento, plano = chave.split("-", 1) # Divide apenas no primeiro hífen

            nome_arquivo = f"{documento}-{plano}.xls"
            caminho_completo = Path(pasta_destino) / nome_arquivo

            # Seleciona apenas as colunas necessárias para o arquivo de saída
            # As colunas 'Emissão', 'Vencimento', 'Competência' são adicionadas no processador.py
            colunas_saida = ["Contrato", "Valor", "Emissão", "Vencimento", "Competência"]
            df_final_saida = df_saida[colunas_saida].copy()

            df_final_saida = df_final_saida[df_final_saida["Valor"] > 0]

            df_final_saida["Valor"] = df_final_saida["Valor"].round(2)

            if df_final_saida.empty:
                user_logger.warning_user(f"Aviso: Nenhum dado para gerar para {documento}-{plano}.xls")
                continue

            try:
                # Usa xlsxwriter para gerar arquivo .xls (na verdade .xlsx)
                df_final_saida.to_excel(caminho_completo, index=False, engine='xlsxwriter')
                user_logger.success_user(f"Arquivo gerado com sucesso: {caminho_completo}")
                logger.info(f"Arquivo gerado: {caminho_completo}")
                arquivos_gerados.append(str(caminho_completo))
            except Exception as e:
                user_logger.error_user(f"Erro ao gerar o arquivo {nome_arquivo}: {str(e)}")
                logger.error(f"Erro ao gerar o arquivo {nome_arquivo}: {str(e)}")
                # Não levanta exceção para permitir que outros arquivos sejam gerados
        
        if not arquivos_gerados:
            user_logger.warning_user("Nenhum arquivo de saída foi gerado com sucesso.")

        user_logger.success_user(f"Geração de arquivos concluída. Total de {len(arquivos_gerados)} arquivos gerados.")
        logger.info(f"Geração de arquivos concluída. Total de {len(arquivos_gerados)} arquivos gerados.")
        return arquivos_gerados

    except Exception as e:
        user_logger.error_user(f"Erro inesperado na geração de arquivos: {str(e)}")
        logger.error(f"Erro inesperado na geração de arquivos: {str(e)}")
        raise ProcessamentoError("Geração de arquivos", str(e))


