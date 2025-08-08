import pandas as pd
from datetime import datetime
from typing import List, Tuple, Dict, Any

from ..utils.exceptions import ProcessamentoError, ValidacaoError
from ..utils.logger import get_logger, get_user_logger
from ..validacao.validador import ValidadorDados

logger = get_logger()
user_logger = get_user_logger()
validador = ValidadorDados()

def processar_dados(df_dados: pd.DataFrame, 
                    documentos_selecionados: List[str],
                    data_inicio: datetime = None,
                    data_fim: datetime = None) -> Dict[str, pd.DataFrame]:
    """
    Processa os dados do DataFrame, aplicando filtros de documento e data.
    Retorna um dicionário de DataFrames, um para cada combinação documento-plano financeiro.
    """
    user_logger.progress_user("Iniciando processamento de dados...")
    logger.info("Iniciando processamento de dados com filtros.")

    dados_filtrados = {}
    
    try:
        # Validação das seleções do usuário
        # A validação da pasta de destino será feita no gerador, pois é onde a pasta é criada/usada.
        validacao_selecao_ok, mensagens_selecao = validador.validar_selecao_usuario(
            documentos_selecionados, data_inicio, data_fim, "temp_path" # temp_path é um placeholder
        )
        for msg in mensagens_selecao:
            if "❌" in msg:
                user_logger.error_user(msg)
            elif "⚠️" in msg:
                user_logger.warning_user(msg)
            else:
                user_logger.info_user(msg)

        if not validacao_selecao_ok:
            user_logger.warning_user("Validação da seleção do usuário encontrou problemas. O processamento pode não ser o esperado.")
            # Não levantamos erro aqui, apenas avisamos, pois o usuário pode querer processar tudo.

        # Se nenhum documento for selecionado, processa todos os documentos únicos
        if not documentos_selecionados:
            documentos_para_processar = df_dados["Documento"].unique().tolist()
            user_logger.info_user(f"Nenhum documento selecionado. Processando todos os {len(documentos_para_processar)} documentos únicos.")
        else:
            documentos_para_processar = documentos_selecionados
            user_logger.info_user(f"Processando documentos selecionados: {', '.join(documentos_selecionados)}")

        for documento in documentos_para_processar:
            df_doc = df_dados[df_dados["Documento"] == documento].copy()
            planos_financeiros = df_doc["Plano Financeiro"].unique().tolist()

            for plano in planos_financeiros:
                df_final = df_doc[df_doc["Plano Financeiro"] == plano].copy()

                # Aplicar filtro de data, se houver
                if data_inicio and data_fim:
                    logger.debug(f'Tipo de df_final["Data Crédito"]: {df_final["Data Crédito"].dtype}')
                    logger.debug(f'Data Crédito min: {df_final["Data Crédito"].min()}, max: {df_final["Data Crédito"].max()}')
                    logger.debug(f"data_inicio: {data_inicio}, data_fim: {data_fim}")
                    df_final = df_final[
                        (df_final["Data Crédito"] >= data_inicio) &
                        (df_final["Data Crédito"] <= data_fim)
                    ]
                    user_logger.info_user(f"Filtro de data aplicado para {documento}-{plano}: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}")
                elif data_inicio:
                    df_final = df_final[df_final["Data Crédito"] >= data_inicio]
                    user_logger.info_user(f"Filtro de data aplicado para {documento}-{plano}: a partir de {data_inicio.strftime('%d/%m/%Y')}")
                elif data_fim:
                    df_final = df_final[df_final["Data Crédito"] <= data_fim]
                    user_logger.info_user(f"Filtro de data aplicado para {documento}-{plano}: até {data_fim.strftime('%d/%m/%Y')}")

                # Adicionar colunas Emissão, Vencimento, Competência
                df_final["Emissão"] = df_final["Data Crédito"].dt.strftime("%d/%m/%Y")
                df_final["Vencimento"] = df_final["Data Crédito"].dt.strftime("%d/%m/%Y")
                df_final["Competência"] = df_final["Data Crédito"].dt.strftime("%d/%m/%Y")

                # Formatar valores com duas casas decimais
                df_final["Valor"] = df_final["Valor"].round(2)

                if not df_final.empty:
                    dados_filtrados[f"{documento}-{plano}"] = df_final
                    user_logger.success_user(f"Dados processados para {documento}-{plano}: {len(df_final)} registros.")
                else:
                    user_logger.warning_user(f"Nenhum registro encontrado para {documento}-{plano} após filtros.")

        if not dados_filtrados:
            user_logger.error_user("Nenhum dado processado após a aplicação de todos os filtros.")
            raise ProcessamentoError("Processamento de dados", "Nenhum dado resultou após a aplicação dos filtros de documento e data.")

        user_logger.success_user("Processamento de dados concluído com sucesso.")
        logger.info(f"Processamento concluído. {len(dados_filtrados)} combinações documento-plano geradas.")
        return dados_filtrados

    except Exception as e:
        user_logger.error_user(f"Erro inesperado no processamento de dados: {str(e)}")
        logger.error(f"Erro inesperado no processamento de dados: {str(e)}")
        raise ProcessamentoError("Processamento de dados", str(e))


