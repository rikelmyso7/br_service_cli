"""
Módulo de validação para o sistema BR_SERVICE.
Responsável por validar dados e regras de negócio.
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from ..config.configuracao import config
from ..utils.exceptions import ValidacaoError
from ..utils.logger import get_logger, get_user_logger
from ..utils.json_response import JSONResponseBuilder, StatusProcessamento, ProcessamentoResponse


class ValidadorDados:
    """Classe responsável por validar dados e regras de negócio."""
    
    def __init__(self):
        """Inicializa o validador."""
        self.logger = get_logger()
        self.user_logger = get_user_logger()
    
    def validacao_completa_com_resposta_json(self, 
                                            caminho_arquivo: str,
                                            planilhas: Dict[str, pd.DataFrame] = None) -> Dict[str, Any]:
        """
        Executa validação completa e retorna resposta JSON padronizada.
        
        Args:
            caminho_arquivo: Caminho do arquivo a validar
            planilhas: Planilhas já carregadas (opcional)
            
        Returns:
            Dicionário com resposta JSON padronizada
        """
        builder = JSONResponseBuilder()
        builder.set_etapa("Validação de dados")
        
        try:
            builder.set_progresso(20)
            builder.add_progresso("Validando arquivo de entrada...")
            
            # Valida arquivo
            arquivo_valido, mensagens_arquivo = self.validar_arquivo_entrada(caminho_arquivo)
            
            builder.set_progresso(40)
            builder.add_progresso("Validando estrutura das planilhas...")
            
            # Valida estrutura se planilhas fornecidas
            estrutura_valida = True
            mensagens_estrutura = []
            if planilhas:
                estrutura_valida, mensagens_estrutura = self.validar_estrutura_planilhas(planilhas)
            
            builder.set_progresso(60)
            builder.add_progresso("Validando dados da planilha Layout...")
            
            # Valida dados se estrutura válida
            dados_validos = True
            mensagens_dados = []
            if estrutura_valida and planilhas and 'Layout' in planilhas:
                dados_validos, mensagens_dados = self.validar_dados_layout(planilhas['Layout'])
            
            builder.set_progresso(80)
            builder.add_progresso("Gerando checklist de validação...")
            
            # Gera checklist
            checklist = self.gerar_checklist_validacao(arquivo_valido, estrutura_valida, dados_validos)
            
            builder.set_progresso(100)
            
            # Define status final
            todas_validacoes_ok = arquivo_valido and estrutura_valida and dados_validos
            if todas_validacoes_ok:
                builder.set_status(StatusProcessamento.CONCLUIDO)
                builder.add_sucesso("Todas as validações foram aprovadas")
            else:
                builder.set_status(StatusProcessamento.AVISO)
                builder.add_aviso("Algumas validações falharam")
            
            # Adiciona dados à resposta
            builder.add_dados("validacao_arquivo", arquivo_valido)
            builder.add_dados("validacao_estrutura", estrutura_valida)
            builder.add_dados("validacao_dados", dados_validos)
            builder.add_dados("pronto_para_processar", todas_validacoes_ok)
            builder.add_dados("checklist_validacao", checklist)
            
            # Adiciona todas as mensagens
            todas_mensagens = mensagens_arquivo + mensagens_estrutura + mensagens_dados
            for mensagem in todas_mensagens:
                if mensagem.startswith("❌"):
                    builder.add_erro(mensagem)
                elif mensagem.startswith("⚠️"):
                    builder.add_aviso(mensagem)
                else:
                    builder.add_info(mensagem)
            
            return builder.build()
            
        except Exception as e:
            builder.set_status(StatusProcessamento.ERRO)
            builder.add_erro(f"Erro na validação: {str(e)}")
            return builder.build()
    
    def validar_arquivo_entrada(self, caminho_arquivo: str) -> Tuple[bool, List[str]]:
        """
        Valida o arquivo de entrada.
        
        Args:
            caminho_arquivo: Caminho do arquivo a validar
            
        Returns:
            Tupla (é_válido, lista_de_mensagens)
        """
        mensagens = []
        arquivo_path = Path(caminho_arquivo)
        
        # Verifica se arquivo existe
        if not arquivo_path.exists():
            mensagens.append("❌ Arquivo não encontrado")
            return False, mensagens
        
        # Verifica extensão
        if arquivo_path.suffix.lower() not in ['.xlsx', '.xls']:
            mensagens.append("❌ Formato de arquivo inválido. Use .xlsx ou .xls")
            return False, mensagens
        
        # Verifica tamanho do arquivo
        tamanho_mb = arquivo_path.stat().st_size / (1024 * 1024)
        if tamanho_mb > 100:  # Limite de 100MB
            mensagens.append(f"⚠️ Arquivo muito grande ({tamanho_mb:.1f}MB). Pode demorar para processar")
        
        mensagens.append("✅ Arquivo válido")
        return True, mensagens
    
    def validar_estrutura_planilhas(self, planilhas: Dict[str, pd.DataFrame]) -> Tuple[bool, List[str]]:
        """
        Valida a estrutura das planilhas carregadas.
        
        Args:
            planilhas: Dicionário com planilhas carregadas
            
        Returns:
            Tupla (é_válido, lista_de_mensagens)
        """
        mensagens = []
        is_valid = True
        
        # Verifica planilhas obrigatórias
        planilhas_obrigatorias = config.planilhas_obrigatorias
        planilhas_encontradas = list(planilhas.keys())
        
        for planilha_obrigatoria in planilhas_obrigatorias:
            if planilha_obrigatoria in planilhas_encontradas:
                mensagens.append(f"✅ Planilha '{planilha_obrigatoria}' encontrada")
            else:
                mensagens.append(f"❌ Planilha obrigatória '{planilha_obrigatoria}' não encontrada")
                is_valid = False
        
        # Verifica planilha principal (Layout)
        planilha_principal = config.planilha_principal
        if planilha_principal in planilhas:
            df_layout = planilhas[planilha_principal]
            
            # Verifica se não está vazia
            if df_layout.empty:
                mensagens.append(f"❌ Planilha '{planilha_principal}' está vazia")
                is_valid = False
            else:
                mensagens.append(f"✅ Planilha '{planilha_principal}' contém {len(df_layout)} registros")
            
            # Verifica colunas obrigatórias com variações
            colunas_obrigatorias = config.obter_colunas_obrigatorias_planilha(planilha_principal)
            colunas_encontradas = df_layout.columns.tolist()
            
            # Para planilhas com estrutura de documentos separados, valida de forma diferente
            if self._is_estrutura_documentos_separados(df_layout):
                mensagens.append("ℹ️ Detectada estrutura de documentos separados - validação adaptada")
                
                # Procura por colunas que contenham os dados esperados
                colunas_data = []
                colunas_valor = []
                colunas_contrato = []
                
                # Primeiro, procura nos nomes das colunas
                for coluna in colunas_encontradas:
                    coluna_str = str(coluna)
                    if any(palavra in coluna_str.lower() for palavra in ['data', 'crédito', 'credito', 'dt']):
                        colunas_data.append(coluna)
                    if any(palavra in coluna_str.lower() for palavra in ['valor', 'vlr']):
                        colunas_valor.append(coluna)
                    if any(palavra in coluna_str.lower() for palavra in ['contrato']):
                        colunas_contrato.append(coluna)
                
                # Se não encontrou nos nomes, procura nas primeiras linhas de dados
                if not colunas_data or not colunas_valor or not colunas_contrato:
                    for linha_idx in range(min(5, len(df_layout))):
                        linha_atual = df_layout.iloc[linha_idx]
                        for col_idx, valor in enumerate(linha_atual):
                            valor_str = str(valor).lower()
                            
                            # Procura por padrões de data
                            if not colunas_data and any(palavra in valor_str for palavra in ['data', 'crédito', 'credito', 'dt']):
                                colunas_data.append(df_layout.columns[col_idx])
                            
                            # Procura por padrões de valor
                            if not colunas_valor and any(palavra in valor_str for palavra in ['valor', 'vlr']):
                                colunas_valor.append(df_layout.columns[col_idx])
                            
                            # Procura por padrões de contrato
                            if not colunas_contrato and any(palavra in valor_str for palavra in ['contrato']):
                                colunas_contrato.append(df_layout.columns[col_idx])
                
                if colunas_data:
                    mensagens.append(f"✅ Colunas de data encontradas: {', '.join([str(c) for c in colunas_data])}")
                else:
                    mensagens.append("⚠️ Nenhuma coluna de data identificada")
                
                if colunas_valor:
                    mensagens.append(f"✅ Colunas de valor encontradas: {', '.join([str(c) for c in colunas_valor])}")
                else:
                    mensagens.append("⚠️ Nenhuma coluna de valor identificada")
                
                if colunas_contrato:
                    mensagens.append(f"✅ Colunas de contrato encontradas: {', '.join([str(c) for c in colunas_contrato])}")
                else:
                    mensagens.append("⚠️ Nenhuma coluna de contrato identificada")
                
                # Se encontrou pelo menos data e valor, considera válido
                if colunas_data and colunas_valor:
                    mensagens.append("✅ Estrutura de dados válida para processamento")
                else:
                    mensagens.append("❌ Estrutura de dados insuficiente para processamento")
                    is_valid = False
            else:
                # Validação tradicional para planilhas com estrutura tabular
                for coluna_canonica in colunas_obrigatorias:
                    variacoes = config.obter_variacoes_coluna(planilha_principal, coluna_canonica)
                    coluna_encontrada = None
                    
                    # Procura pela coluna canônica ou suas variações
                    for variacao in variacoes:
                        if variacao in colunas_encontradas:
                            coluna_encontrada = variacao
                            break
                    
                    if coluna_encontrada:
                        if coluna_encontrada == coluna_canonica:
                            mensagens.append(f"✅ Coluna '{coluna_canonica}' encontrada")
                        else:
                            mensagens.append(f"✅ Coluna '{coluna_canonica}' encontrada como '{coluna_encontrada}'")
                    else:
                        # Tenta encontrar coluna similar como fallback
                        coluna_similar = self._encontrar_coluna_similar(coluna_canonica, colunas_encontradas)
                        if coluna_similar:
                            mensagens.append(f"⚠️ Coluna '{coluna_canonica}' não encontrada, mas '{coluna_similar}' pode ser similar")
                        else:
                            mensagens.append(f"❌ Coluna obrigatória '{coluna_canonica}' não encontrada")
                            is_valid = False
        
        return is_valid, mensagens
    
    def validar_dados_layout(self, df_layout: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Valida os dados da planilha Layout.
        
        Args:
            df_layout: DataFrame da planilha Layout
            
        Returns:
            Tupla (é_válido, lista_de_mensagens)
        """
        mensagens = []
        is_valid = True
        
        if df_layout.empty:
            mensagens.append("❌ Planilha Layout está vazia")
            return False, mensagens
        
        # Identifica colunas importantes
        colunas_mapeamento = self._mapear_colunas_layout(df_layout)
        
        # Valida coluna de data
        if colunas_mapeamento.get('data'):
            coluna_data = colunas_mapeamento['data']
            datas_validas, datas_invalidas = self._validar_coluna_data(df_layout[coluna_data])
            
            if datas_invalidas > 0:
                mensagens.append(f"⚠️ {datas_invalidas} datas inválidas na coluna '{coluna_data}'")
            
            if datas_validas > 0:
                mensagens.append(f"✅ {datas_validas} datas válidas encontradas")
            else:
                mensagens.append(f"❌ Nenhuma data válida encontrada na coluna '{coluna_data}'")
                is_valid = False
        else:
            mensagens.append("❌ Coluna de data não identificada")
            is_valid = False
        
        # Valida coluna de valor
        if colunas_mapeamento.get('valor'):
            coluna_valor = colunas_mapeamento['valor']
            valores_validos, valores_invalidos = self._validar_coluna_valor(df_layout[coluna_valor])

            valores_positivos = len(df_layout[df_layout[coluna_valor] > 0])
            
            if valores_invalidos > 0:
                mensagens.append(f"⚠️ {valores_invalidos} valores inválidos na coluna '{coluna_valor}'")
            
            if valores_positivos > 0:
                mensagens.append(f"✅ {valores_positivos} valores válidos encontrados")
            else:
                mensagens.append(f"❌ Nenhum valor válido encontrado na coluna '{coluna_valor}'")
                is_valid = False
        else:
            mensagens.append("❌ Coluna de valor não identificada")
            is_valid = False
        
        # Valida coluna de contrato
        if colunas_mapeamento.get('contrato'):
            coluna_contrato = colunas_mapeamento['contrato']
            contratos_unicos = df_layout[coluna_contrato].nunique()
            mensagens.append(f"✅ {contratos_unicos} contratos únicos encontrados na coluna '{coluna_contrato}'")
        else:
            mensagens.append("⚠️ Coluna de contrato não identificada")
        
        # Valida coluna de plano financeiro
        if colunas_mapeamento.get('plano_financeiro'):
            coluna_plano = colunas_mapeamento['plano_financeiro']
            planos_unicos = df_layout[coluna_plano].nunique()
            mensagens.append(f"✅ {planos_unicos} planos financeiros únicos encontrados na coluna '{coluna_plano}'")
        else:
            mensagens.append("⚠️ Coluna de plano financeiro não identificada")
        
        # Valida documentos/planos
        documentos_identificados = self._identificar_documentos_planos(df_layout)
        if documentos_identificados:
            mensagens.append(f"✅ {len(documentos_identificados)} documentos/planos identificados:")
            for doc in documentos_identificados[:5]:  # Mostra apenas os primeiros 5
                mensagens.append(f"   - {doc}")
            if len(documentos_identificados) > 5:
                mensagens.append(f"   ... e mais {len(documentos_identificados) - 5}")
        else:
            mensagens.append("⚠️ Nenhum documento/plano identificado claramente")
        
        return is_valid, mensagens
    
    def validar_selecao_usuario(self, 
                               documentos_selecionados: List[str],
                               data_inicio: Optional[datetime],
                               data_fim: Optional[datetime],
                               pasta_destino: str) -> Tuple[bool, List[str]]:
        """
        Valida as seleções feitas pelo usuário.
        
        Args:
            documentos_selecionados: Lista de documentos selecionados
            data_inicio: Data de início selecionada
            data_fim: Data de fim selecionada
            pasta_destino: Pasta de destino selecionada
            
        Returns:
            Tupla (é_válido, lista_de_mensagens)
        """
        mensagens = []
        is_valid = True
        
        # Valida documentos selecionados
        if not documentos_selecionados:
            mensagens.append("⚠️ Nenhum documento selecionado - todos serão processados")
        else:
            mensagens.append(f"✅ {len(documentos_selecionados)} documentos selecionados")
        
        # Valida datas
        if data_inicio and data_fim:
            if data_inicio > data_fim:
                mensagens.append("❌ Data de início não pode ser posterior à data de fim")
                is_valid = False
            else:
                periodo = (data_fim - data_inicio).days
                mensagens.append(f"✅ Período selecionado: {periodo} dias")
        elif data_inicio:
            mensagens.append("✅ Filtro a partir de data específica")
        elif data_fim:
            mensagens.append("✅ Filtro até data específica")
        else:
            mensagens.append("ℹ️ Nenhum filtro de data - todos os períodos serão processados")
        
        # Valida pasta de destino
        pasta_path = Path(pasta_destino)
        try:
            pasta_path.mkdir(parents=True, exist_ok=True)
            mensagens.append("✅ Pasta de destino válida e acessível")
        except Exception as e:
            mensagens.append(f"❌ Erro na pasta de destino: {e}")
            is_valid = False
        
        return is_valid, mensagens
    
    def _encontrar_coluna_similar(self, coluna_procurada: str, colunas_disponiveis: List[str]) -> Optional[str]:
        """
        Encontra uma coluna similar à procurada.
        
        Args:
            coluna_procurada: Nome da coluna procurada
            colunas_disponiveis: Lista de colunas disponíveis
            
        Returns:
            Nome da coluna similar ou None
        """
        coluna_lower = coluna_procurada.lower()
        
        # Palavras-chave para cada tipo de coluna
        palavras_chave = {
            'data': ['data', 'dt', 'date'],
            'valor': ['valor', 'vlr', 'value', 'montante'],
            'credito': ['credito', 'crédito', 'credit'],
            'contrato': ['contrato', 'contract', 'documento', 'doc'],
            'plano': ['plano', 'plan', 'financeiro']
        }
        
        # Identifica o tipo da coluna procurada
        tipo_coluna = None
        for tipo, palavras in palavras_chave.items():
            if any(palavra in coluna_lower for palavra in palavras):
                tipo_coluna = tipo
                break
        
        if not tipo_coluna:
            return None
        
        # Procura coluna similar do mesmo tipo
        for coluna_disponivel in colunas_disponiveis:
            if not isinstance(coluna_disponivel, str):
                continue
            coluna_disp_lower = coluna_disponivel.lower()
            if any(palavra in coluna_disp_lower for palavra in palavras_chave[tipo_coluna]):
                return coluna_disponivel
        
        return None
    
    def _is_estrutura_documentos_separados(self, df: pd.DataFrame) -> bool:
        """
        Verifica se a planilha tem estrutura de documentos separados
        (cada documento tem suas próprias colunas).
        
        Args:
            df: DataFrame da planilha
            
        Returns:
            True se a estrutura for de documentos separados
        """
        colunas = df.columns.tolist()
        
        # Verifica se há colunas que parecem ser códigos de documento
        codigos_documento = ['AZ', 'ADTC', 'REG']
        colunas_com_codigos = [col for col in colunas if str(col) in codigos_documento]
        
        # Verifica se há colunas que parecem ser códigos de plano
        codigos_plano = ['1.01.02.01', '1.04.01.07', '1.04.01.08']
        colunas_com_planos = [col for col in colunas if str(col) in codigos_plano]
        
        # Se encontrou pelo menos 2 códigos de documento ou plano, considera estrutura separada
        return len(colunas_com_codigos) >= 2 or len(colunas_com_planos) >= 2
    
    def _mapear_colunas_layout(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Mapeia as colunas da planilha Layout, identificando blocos de dados e seus respectivos documentos.
        
        Args:
            df: DataFrame da planilha Layout
            
        Returns:
            Dicionário com mapeamento de colunas (tipo -> nome_real_coluna)
        """
        mapeamento = {}
        colunas = [str(col) for col in df.columns.tolist()]  # Garante que todas as colunas são strings
        
        # Identifica blocos de colunas na estrutura de documentos separados
        blocos = self._identificar_blocos_documentos(df, colunas)
        
        if blocos:
            # Estrutura de documentos separados encontrada
            self.logger.info(f"Estrutura de blocos identificada: {len(blocos)} blocos encontrados")
            
            # Adiciona mapeamento para cada bloco
            for i, bloco in enumerate(blocos):
                doc = bloco.get('documento', f'DOC_{i+1}')
                
                # Mapeia as colunas do bloco
                for col_type, col_name in bloco['colunas'].items():
                    mapeamento[f'{col_type}_{doc}'] = col_name
            
            # Adiciona metadados sobre a estrutura de blocos
            mapeamento['_estrutura'] = 'blocos'
            mapeamento['_blocos'] = [b['documento'] for b in blocos if 'documento' in b]
            
        else:
            # Tenta mapear usando o sistema de variações da configuração (estrutura tradicional)
            planilha_principal = config.planilha_principal
            
            # Mapeia coluna de data
            variacoes_data = config.obter_variacoes_coluna(planilha_principal, "Data de Crédito")
            for variacao in variacoes_data:
                if variacao in colunas:
                    mapeamento['data'] = variacao
                    break
            
            # Mapeia coluna de valor
            variacoes_valor = config.obter_variacoes_coluna(planilha_principal, "Valor")
            for variacao in variacoes_valor:
                if variacao in colunas:
                    mapeamento['valor'] = variacao
                    break
            
            # Mapeia coluna de contrato
            variacoes_contrato = config.obter_variacoes_coluna(planilha_principal, "Contrato")
            for variacao in variacoes_contrato:
                if variacao in colunas:
                    mapeamento['contrato'] = variacao
                    break
            
            # Mapeia coluna de plano financeiro
            variacoes_plano = config.obter_variacoes_coluna(planilha_principal, "Plano Financeiro")
            for variacao in variacoes_plano:
                if variacao in colunas:
                    mapeamento['plano_financeiro'] = variacao
                    break
            
            # Marca como estrutura tradicional
            mapeamento['_estrutura'] = 'tradicional'
        
        self.logger.info(f"Mapeamento de colunas: {mapeamento}")
        return mapeamento
    
    def _identificar_blocos_documentos(self, df: pd.DataFrame, colunas: List[str]) -> List[Dict]:
        """
        Identifica blocos de colunas para cada documento na planilha.
        
        Args:
            df: DataFrame da planilha
            colunas: Lista de nomes de colunas
            
        Returns:
            Lista de dicionários com informações dos blocos identificados
        """
        blocos = []
        
        # Padrões para identificar tipos de colunas
        padroes_colunas = {
            'contrato': r'(?i)contrato',
            'valor': r'(?i)valor',
            'data': r'(?i)(data.*crédito|crédito.*data|data)'
        }
        
        # Identifica a linha de cabeçalho (linha 4, índice 3) e a linha de documentos (linha 3, índice 2)
        linha_cabecalho = -1
        
        # Verifica as primeiras 5 linhas para encontrar a linha de cabeçalho
        for linha_idx in range(min(5, len(df))):
            linha = df.iloc[linha_idx].astype(str).str.strip()
            
            # Conta quantas colunas de cada tipo encontrou nesta linha
            contagem = {tipo: linha.str.contains(padrao, regex=True).sum() 
                       for tipo, padrao in padroes_colunas.items()}
            
            # Se encontrou pelo menos 2 tipos de colunas, esta é provavelmente a linha de cabeçalho
            if sum(contagem.values()) >= 2:
                linha_cabecalho = linha_idx
                self.logger.info(f"Linha de cabeçalho identificada na linha {linha_idx} com {contagem}")
                break
        
        # Se não encontrou uma linha de cabeçalho óbvia, tenta a linha 4 (índice 3) como padrão
        if linha_cabecalho == -1 and len(df) > 3:
            linha_cabecalho = 3
            self.logger.info(f"Usando linha {linha_cabecalho} como linha de cabeçalho (padrão)")
        
        # Se encontrou uma linha de cabeçalho, processa os blocos
        if linha_cabecalho >= 0:
            linha = df.iloc[linha_cabecalho].astype(str).str.strip()
            
            # Mapeia cada coluna para seu tipo
            colunas_por_tipo = {tipo: [] for tipo in padroes_colunas}
            
            for col_idx, nome_coluna in enumerate(linha):
                for tipo, padrao in padroes_colunas.items():
                    if pd.Series([nome_coluna]).str.contains(padrao, regex=True).any():
                        colunas_por_tipo[tipo].append((col_idx, nome_coluna))
            
            # Se não encontrou colunas, tenta com a linha 3 (índice 2) como linha de cabeçalho
            if sum(len(cols) for cols in colunas_por_tipo.values()) == 0 and linha_cabecalho > 0:
                self.logger.info("Nenhuma coluna identificada, tentando com a linha anterior")
                linha = df.iloc[linha_cabecalho-1].astype(str).str.strip()
                for col_idx, nome_coluna in enumerate(linha):
                    for tipo, padrao in padroes_colunas.items():
                        if pd.Series([nome_coluna]).str.contains(padrao, regex=True).any():
                            colunas_por_tipo[tipo].append((col_idx, nome_coluna))
            
            # Agrupa colunas que estão próximas como parte do mesmo bloco
            todas_colunas = []
            for tipo, cols in colunas_por_tipo.items():
                for col_idx, nome_col in cols:
                    todas_colunas.append((col_idx, tipo, nome_col))
            
            # Se não encontrou colunas pelos padrões, tenta identificar blocos de 3 colunas
            if not todas_colunas:
                self.logger.info("Nenhuma coluna identificada pelos padrões, tentando identificar blocos de 3 colunas")
                
                # Procura por sequências de 3 colunas que possam ser Contrato, Valor, Data
                for col_idx in range(len(df.columns) - 2):
                    # Verifica se as próximas 3 colunas têm valores não vazios na linha de cabeçalho
                    if (pd.notna(df.iloc[linha_cabecalho, col_idx]) and 
                        pd.notna(df.iloc[linha_cabecalho, col_idx+1]) and 
                        pd.notna(df.iloc[linha_cabecalho, col_idx+2])):
                        # Adiciona como bloco genérico
                        todas_colunas.extend([
                            (col_idx, 'contrato', f'Coluna {col_idx+1}'),
                            (col_idx+1, 'valor', f'Coluna {col_idx+2}'),
                            (col_idx+2, 'data', f'Coluna {col_idx+3}')
                        ])
                        self.logger.info(f"Bloco genérico identificado nas colunas {col_idx+1}-{col_idx+3}")
                        break
            
            # Ordena por índice de coluna
            todas_colunas.sort()
            
            # Agrupa colunas próximas em blocos
            if todas_colunas:
                bloco_atual = [todas_colunas[0]]
                
                for col in todas_colunas[1:]:
                    # Se a coluna atual está próxima da anterior, adiciona ao bloco atual
                    if col[0] - bloco_atual[-1][0] <= 3:  # Máximo de 2 colunas de distância
                        bloco_atual.append(col)
                    else:
                        # Fecha o bloco atual e inicia um novo
                        if len(bloco_atual) >= 2:  # Pelo menos 2 colunas por bloco
                            self._processar_bloco(bloco_atual, blocos, df, linha_cabecalho)
                        bloco_atual = [col]
                
                # Adiciona o último bloco
                if len(bloco_atual) >= 2:
                    self._processar_bloco(bloco_atual, blocos, df, linha_cabecalho)
        
        return blocos
    
    def _processar_bloco(self, colunas_bloco: List[tuple], blocos: List[Dict], 
                        df: pd.DataFrame, linha_cabecalho: int) -> None:
        """
        Processa um bloco de colunas identificado.
        
        Args:
            colunas_bloco: Lista de tuplas (índice, tipo, nome) das colunas do bloco
            blocos: Lista de blocos para adicionar o bloco processado
            df: DataFrame com os dados
            linha_cabecalho: Índice da linha que contém os cabeçalhos
        """
        # Ordena as colunas pelo índice
        colunas_bloco.sort()
        
        # Extrai índices e tipos
        indices = [c[0] for c in colunas_bloco]
        tipos = [c[1] for c in colunas_bloco]
        
        # Tenta identificar o documento/plano financeiro
        documento = None
        plano = None
        
        # Verifica a linha 3 (índice 2) que contém os códigos dos documentos/planos
        if linha_cabecalho > 2:  # Se linha_cabecalho é 4 (índice 3), a linha 3 é índice 2
            linha_documentos = df.iloc[2]  # Linha 3 (0-based index 2)
            
            # Pega o valor da primeira coluna do bloco na linha de documentos
            primeira_col = indices[0]
            if primeira_col < len(linha_documentos):
                valor = linha_documentos.iloc[primeira_col]
                if pd.notna(valor) and str(valor).strip():
                    documento = str(valor).strip()
                    self.logger.info(f"Documento identificado na linha 3: {documento}")
        
        # Se não encontrou na linha 3, verifica a linha acima do cabeçalho (linha 3 se linha_cabecalho for 4)
        if not documento and linha_cabecalho > 0:
            linha_acima = df.iloc[linha_cabecalho-1]
            
            # Pega o valor da primeira coluna do bloco na linha acima
            primeira_col = indices[0]
            if primeira_col < len(linha_acima):
                valor = linha_acima.iloc[primeira_col]
                if pd.notna(valor) and str(valor).strip():
                    documento = str(valor).strip()
                    self.logger.info(f"Documento identificado na linha acima do cabeçalho: {documento}")
        
        # Se ainda não encontrou, tenta extrair do nome da coluna
        if not documento and indices:
            primeira_col = indices[0]
            if primeira_col < len(df.columns):
                nome_coluna = str(df.columns[primeira_col])
                # Tenta extrair um código de documento do nome da coluna
                if re.match(r'^[A-Z]{2,}', nome_coluna):
                    documento = re.match(r'^([A-Z]{2,})', nome_coluna).group(1)
                    self.logger.info(f"Documento extraído do nome da coluna: {documento}")
        
        # Se ainda não encontrou, usa um identificador baseado na posição
        if not documento:
            documento = f"DOC_{len(blocos)+1}"
            self.logger.warning(f"Documento não identificado, usando identificador gerado: {documento}")
        
        # Normaliza o nome do documento removendo espaços extras e caracteres inválidos
        documento = re.sub(r'[^\w-]', '', str(documento).strip())
        
        # Se o documento contiver um hífen, separa em documento e plano
        if '-' in documento and documento.count('-') == 1:
            doc_parts = documento.split('-')
            if len(doc_parts[0]) > 0 and len(doc_parts[1]) > 0:
                documento = doc_parts[0]
                plano = doc_parts[1]
                self.logger.info(f"Documento e plano separados: {documento} - {plano}")
        
        # Cria o mapeamento de colunas para o bloco
        mapeamento = {}
        for idx, col_idx in enumerate(indices):
            if col_idx < len(df.columns):
                col_name = df.columns[col_idx]
                mapeamento[tipos[idx]] = col_name
        
        # Adiciona o bloco à lista
        if mapeamento:
            blocos.append({
                'documento': documento,
                'colunas': mapeamento,
                'indices': indices
            })
            
            self.logger.info(f"Bloco identificado - Documento: {documento}, Colunas: {mapeamento}")
    
    def _validar_coluna_data(self, serie_data: pd.Series) -> Tuple[int, int]:
        """
        Valida uma coluna de datas.
        
        Args:
            serie_data: Série com dados de data
            
        Returns:
            Tupla (datas_válidas, datas_inválidas)
        """
        datas_validas = 0
        datas_invalidas = 0
        
        for valor in serie_data:
            if pd.isna(valor):
                datas_invalidas += 1
                continue
            
            try:
                if isinstance(valor, (datetime, pd.Timestamp)):
                    datas_validas += 1
                elif isinstance(valor, str):
                    # Tenta converter string para data
                    pd.to_datetime(valor)
                    datas_validas += 1
                else:
                    datas_invalidas += 1
            except:
                datas_invalidas += 1
        
        return datas_validas, datas_invalidas
    
    def _validar_coluna_valor(self, serie_valor: pd.Series) -> Tuple[int, int]:
        """
        Valida uma coluna de valores.
        
        Args:
            serie_valor: Série com dados de valor
            
        Returns:
            Tupla (valores_válidos, valores_inválidos)
        """
        valores_validos = 0
        valores_invalidos = 0
        
        for valor in serie_valor:
            if pd.isna(valor):
                valores_invalidos += 1
                continue
            
            try:
                if isinstance(valor, (int, float)):
                    if valor > 0:  # Adiciona condição
                        valores_validos += 1
                    else:
                        valores_invalidos += 1
                elif isinstance(valor, str):
                    # Tenta converter string para número
                    valor_limpo = valor.replace(',', '.').strip()
                    float(valor_limpo)
                    valores_validos += 1
                else:
                    valores_invalidos += 1
            except:
                valores_invalidos += 1
        
        return valores_validos, valores_invalidos
    
    def _identificar_documentos_planos(self, df: pd.DataFrame) -> List[str]:
        """
        Identifica documentos e planos financeiros no DataFrame.
        
        Args:
            df: DataFrame para analisar
            
        Returns:
            Lista de códigos identificados
        """
        documentos_planos = set()
        
        # Procura em todas as colunas de texto
        for coluna in df.columns:
            if df[coluna].dtype == 'object':  # Coluna de texto
                for valor in df[coluna].dropna().unique():
                    if isinstance(valor, str):
                        # Procura padrão DOCUMENTO-PLANO
                        if '-' in valor and '.' in valor:
                            # Verifica se parece com o padrão esperado
                            partes = valor.split('-')
                            if len(partes) == 2 and len(partes[0]) <= 10 and len(partes[1]) <= 20:
                                documentos_planos.add(valor.strip())
        
        return sorted(list(documentos_planos))
    
    def gerar_checklist_validacao(self, 
                                 arquivo_valido: bool,
                                 estrutura_valida: bool,
                                 dados_validos: bool) -> List[Dict[str, Any]]:
        """
        Gera um checklist de validação para exibir na UI.
        
        Args:
            arquivo_valido: Se o arquivo é válido
            estrutura_valida: Se a estrutura é válida
            dados_validos: Se os dados são válidos
            
        Returns:
            Lista de itens do checklist
        """
        checklist = [
            {
                'item': 'Arquivo de entrada',
                'status': 'ok' if arquivo_valido else 'erro',
                'descricao': 'Arquivo Excel válido e acessível'
            },
            {
                'item': 'Estrutura das planilhas',
                'status': 'ok' if estrutura_valida else 'erro',
                'descricao': 'Planilhas obrigatórias presentes'
            },
            {
                'item': 'Dados da planilha Layout',
                'status': 'ok' if dados_validos else 'erro',
                'descricao': 'Dados válidos para processamento'
            },
            {
                'item': 'Pronto para processamento',
                'status': 'ok' if (arquivo_valido and estrutura_valida and dados_validos) else 'pendente',
                'descricao': 'Sistema pronto para gerar arquivos de importação'
            }
        ]
        
        return checklist

