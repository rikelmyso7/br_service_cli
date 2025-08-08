
import pandas as pd
import openpyxl

from ..utils.exceptions import (
    ArquivoNaoEncontradoError, 
    PlanilhaNaoEncontradaError, 
    ColunaNaoEncontradaError,
    DadosVaziosError,
    ProcessamentoError
)
from ..utils.logger import get_logger, get_user_logger

# Configurar loggers
logger = get_logger()
user_logger = get_user_logger()

def encontrar_linha_cabecalho(df):
    """Encontra a linha que contém os cabeçalhos das colunas"""
    user_logger.progress_user("Procurando linha de cabeçalho...")
    
    for i in range(min(20, len(df))):
        row = df.iloc[i]
        # Procura por uma linha que contenha 'Contrato', 'Valor' e 'Data Crédito'
        row_str = ' '.join([str(x) for x in row if pd.notna(x)])
        if 'Contrato' in row_str and 'Valor' in row_str and 'Data Crédito' in row_str:
            user_logger.success_user(f"Linha de cabeçalho encontrada na linha {i}")
            logger.info(f"Linha de cabeçalho encontrada na linha {i}")
            return i
    
    user_logger.error_user("Linha de cabeçalho não encontrada")
    raise ColunaNaoEncontradaError("Contrato, Valor, Data Crédito", "Layout", [])

def extrair_documentos_planos(df):
    """Extrai os documentos e planos financeiros da planilha"""
    user_logger.progress_user("Extraindo documentos e planos financeiros...")
    documentos_planos = []
    
    # Procura na linha 3 (baseado na análise do arquivo)
    if len(df) > 3:
        row = df.iloc[3]
        for i in range(0, len(row), 4):  # Assumindo que cada bloco tem 4 colunas
            if i < len(row) and pd.notna(row.iloc[i]):
                documento = str(row.iloc[i]).strip()
                plano = str(row.iloc[i+1]).strip() if i+1 < len(row) and pd.notna(row.iloc[i+1]) else ""
                if documento and plano:
                    documentos_planos.append((documento, plano))
                    user_logger.info_user(f"Documento encontrado: {documento}-{plano}")
    
    if not documentos_planos:
        user_logger.error_user("Nenhum documento/plano financeiro encontrado")
        raise ProcessamentoError("Extração de documentos", "Não foi possível encontrar documentos e planos financeiros na planilha")
    
    user_logger.success_user(f"{len(documentos_planos)} documentos/planos encontrados")
    return documentos_planos

def ler_dados_layout(caminho_arquivo):
    try:
        user_logger.progress_user("Iniciando leitura do arquivo Excel...")
        logger.info(f"Iniciando leitura do arquivo: {caminho_arquivo}")
        
        xls = pd.ExcelFile(caminho_arquivo)
        if 'Layout' not in xls.sheet_names:
            user_logger.error_user("Planilha 'Layout' não encontrada")
            raise PlanilhaNaoEncontradaError("Layout", xls.sheet_names)
        
        user_logger.success_user("Planilha 'Layout' encontrada")
        
        # Lê sem cabeçalho para analisar a estrutura
        user_logger.progress_user("Analisando estrutura da planilha...")
        df_raw = pd.read_excel(xls, sheet_name='Layout', header=None)
        
        # Encontra a linha de cabeçalho
        linha_cabecalho = encontrar_linha_cabecalho(df_raw)
        
        # Extrai documentos e planos financeiros
        documentos_planos = extrair_documentos_planos(df_raw)
        
        # Lê os dados a partir da linha de cabeçalho
        user_logger.progress_user("Carregando dados da planilha...")
        df_layout = pd.read_excel(xls, sheet_name='Layout', header=linha_cabecalho, skiprows=range(0, linha_cabecalho))
        
        # Processa cada bloco de dados (cada documento/plano)
        user_logger.progress_user("Processando blocos de dados...")
        dados_processados = []
        
        for i, (documento, plano) in enumerate(documentos_planos):
            user_logger.progress_user(f"Processando {documento}-{plano}...")
            
            # Calcula as colunas para este bloco (assumindo 4 colunas por bloco: Contrato, Valor, Data Crédito, vazia)
            col_inicio = i * 4
            col_contrato = col_inicio
            col_valor = col_inicio + 1
            col_data = col_inicio + 2
            
            if col_data < len(df_layout.columns):
                # Extrai dados deste bloco
                df_bloco = df_layout.iloc[:, [col_contrato, col_valor, col_data]].copy()
                df_bloco.columns = ['Contrato', 'Valor', 'Data Crédito']
                
                # Remove linhas vazias
                df_bloco = df_bloco.dropna(subset=['Contrato', 'Valor', 'Data Crédito'])
                
                # Adiciona colunas de documento e plano
                df_bloco['Documento'] = documento
                df_bloco['Plano Financeiro'] = plano
                
                # Converte tipos
                try:
                    df_bloco['Valor'] = pd.to_numeric(df_bloco['Valor'], errors='coerce')
                    df_bloco['Data Crédito'] = pd.to_datetime(df_bloco['Data Crédito'], errors='coerce')
                except Exception as e:
                    user_logger.warning_user(f"Aviso na conversão de tipos para {documento}-{plano}: {str(e)}")
                    logger.warning(f"Erro na conversão de tipos para {documento}-{plano}: {str(e)}")
                
                # Remove linhas com dados inválidos
                df_bloco = df_bloco.dropna(subset=['Valor', 'Data Crédito'])
                
                if not df_bloco.empty:
                    dados_processados.append(df_bloco)
                    user_logger.success_user(f"{len(df_bloco)} registros válidos para {documento}-{plano}")
                else:
                    user_logger.warning_user(f"Nenhum dado válido encontrado para {documento}-{plano}")
        
        if not dados_processados:
            user_logger.error_user("Nenhum dado válido encontrado em toda a planilha")
            raise DadosVaziosError()
        
        # Combina todos os blocos
        user_logger.progress_user("Combinando todos os dados...")
        df_final = pd.concat(dados_processados, ignore_index=True)
        
        user_logger.success_user(f"Leitura concluída: {len(df_final)} registros totais processados")
        logger.info(f"Leitura concluída com sucesso: {len(df_final)} registros, {len(documentos_planos)} documentos/planos")
        
        return df_final, documentos_planos
        
    except Exception as e:
        if isinstance(e, (ArquivoNaoEncontradoError, PlanilhaNaoEncontradaError, ColunaNaoEncontradaError, DadosVaziosError, ProcessamentoError)):
            # Re-raise exceções customizadas
            raise
        else:
            # Converte outras exceções em ProcessamentoError
            user_logger.error_user(f"Erro inesperado na leitura: {str(e)}")
            logger.error(f"Erro inesperado na leitura do arquivo: {str(e)}")
            raise ProcessamentoError("Leitura de arquivo", str(e))

def obter_opcoes(caminho_arquivo):
    try:
        user_logger.progress_user("Obtendo opções disponíveis...")
        logger.info(f"Obtendo opções do arquivo: {caminho_arquivo}")
        
        df_dados, documentos_planos = ler_dados_layout(caminho_arquivo)
        if df_dados is None:
            user_logger.error_user("Não foi possível obter opções - dados não carregados")
            return {'documentos': [], 'datas': [], 'combinacoes': []}

        # Agrupa as datas por documento
        opcoes_documentos = []
        for doc, plano in documentos_planos:
            df_doc = df_dados[(df_dados['Documento'] == doc) & (df_dados['Plano Financeiro'] == plano)]
            datas = df_doc['Data Crédito'].dt.strftime('%d/%m/%Y').unique().tolist()
            opcoes_documentos.append({
                'documento': f"{doc}-{plano}",
                'datas': sorted(datas)
            })

        user_logger.success_user(f"Opções obtidas para {len(opcoes_documentos)} documentos")
        logger.info(f"Opções extraídas para {len(opcoes_documentos)} documentos")
        
        return {
            'opcoes_documentos': opcoes_documentos
        }
        
    except Exception as e:
        user_logger.error_user(f"Erro ao obter opções: {str(e)}")
        logger.error(f"Erro ao obter opções: {str(e)}")
        return {'opcoes_documentos': []}


