import re
import pandas as pd
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from utils.exceptions import ErroLeituraArquivo
from utils.logger import configurar_logger

logger = configurar_logger(__name__)

def _parse_valor(x):
    """
    Converte 'Valor' aceitando formatos BR/US e aplica round(2) SOMENTE
    se o número não tiver exatamente 2 casas decimais.

    Exemplos:
    - '293.947,68' -> 293947.68
    - '628,91'     -> 628.91
    - '20166.12'   -> 20166.12
    - '123.456'    -> 123.46 (arredonda pois tem 3 casas)
    - 100          -> 100.00 (arredonda pois tem 0 casas)
    """
    if pd.isna(x):
        return pd.NA

    # Se já vier numérico (int/float), converte via string para não perder escala
    if isinstance(x, (int, float)):
        try:
            d = Decimal(str(x))
        except InvalidOperation:
            return pd.NA
    else:
        s = str(x).strip()
        if not s:
            return pd.NA

        # Trata negativo entre parênteses: (1.234,56) -> -1234,56
        neg = False
        if s.startswith("(") and s.endswith(")"):
            neg = True
            s = s[1:-1].strip()

        # Remove NBSP e espaços esquisitos
        s = s.replace("\u00A0", "").replace(" ", "")

        # Heurística BR/US:
        # - Se tem '.' e ',' assume BR (ponto milhar, vírgula decimal)
        # - Se tem só ',', trata como vírgula decimal
        # - Se tem só '.', mantém como ponto decimal
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")

        try:
            d = Decimal(s)
        except InvalidOperation:
            return pd.NA

        if neg:
            d = -d

    # Verifica a quantidade de casas decimais
    exp = d.as_tuple().exponent
    frac = -exp if exp < 0 else 0  # casas decimais atuais

    if frac == 2:
        # Já tem 2 casas — retorna como float sem mexer
        return float(d)
    else:
        # Qualquer coisa diferente de 2 casas — arredonda para 2
        return float(d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


class LeitorExcel:
    """
    Classe responsável por ler e interpretar a planilha 'Layout' de um arquivo Excel.
    
    Objetivos:
    - Localizar a linha de cabeçalho que contém as colunas 'Contrato', 'Valor' e 'Data Crédito'.
    - Identificar múltiplos blocos de dados na horizontal (cada bloco = 3 colunas).
    - Extrair metadados (Documento e Plano Financeiro) associados a cada bloco.
    - Tratar e padronizar os dados (datas e valores numéricos).
    - Fornecer os dados processados por bloco e opções consolidadas para uso em UI.
    """

    def __init__(self, sheet_name: str = "Layout", meta_rows_up: int = 1):
        """
        Inicializa o leitor de Excel.
        
        Args:
            sheet_name (str): Nome da planilha a ser lida.
            meta_rows_up (int): Número máximo de linhas acima do cabeçalho
                                a serem analisadas para buscar Documento/Plano.
        """
        self.sheet_name = sheet_name
        self.meta_rows_up = meta_rows_up
        self.cols_alvo = ["Contrato", "Valor", "Data Crédito"]
        
        # Mapeamento flexível para variações de nomes de colunas
        self.variacoes_colunas = {
            "Contrato": [
                "contrato", "contrat", "contract"
            ],
            "Valor": [
                "valor", "val", "value", "montante"
            ],
            "Data Crédito": [
                "data credito", "data crédito", "dt credito", "dt crédito",
                "data", "dt", "date"
            ]
        }

    def _encontrar_linha_cabecalho(self, df: pd.DataFrame) -> int:
        """
        Localiza o índice (0-based) da linha de cabeçalho.
        
        A detecção é feita buscando, em uma mesma linha, a ocorrência
        das três colunas-alvo: 'Contrato', 'Valor', 'Data Crédito' ou suas variações.

        Raises:
            ErroLeituraArquivo: Se o cabeçalho não for encontrado.
        """
        for i, row in df.iterrows():
            vals = [str(x).strip().lower() for x in row.values if pd.notna(x)]
            
            colunas_encontradas = []
            for col_alvo in self.cols_alvo:
                # Verifica se encontrou a coluna alvo ou alguma de suas variações
                for variacao in self.variacoes_colunas[col_alvo]:
                    if any(variacao in val for val in vals):
                        colunas_encontradas.append(col_alvo)
                        break
            
            # Se encontrou todas as 3 colunas obrigatórias na mesma linha
            if len(colunas_encontradas) == len(self.cols_alvo):
                return i
                
        raise ErroLeituraArquivo("Cabeçalho com 'Contrato', 'Valor' e 'Data Crédito' (ou variações) não encontrado na planilha.")

    def _indices_inicio_blocos(self, df: pd.DataFrame, linha_cabecalho: int) -> list[int]:
        """
        Retorna os índices de coluna que iniciam cada bloco de dados.
        
        Args:
            df (pd.DataFrame): DataFrame da planilha.
            linha_cabecalho (int): Índice da linha de cabeçalho.
        
        Returns:
            list[int]: Lista de índices de colunas onde aparece 'Contrato' ou variações.
        """
        header = df.iloc[linha_cabecalho].fillna("")
        indices = []
        for j, v in enumerate(header):
            val = str(v).strip().lower()
            # Verifica se é uma das variações de "Contrato"
            for variacao in self.variacoes_colunas["Contrato"]:
                if variacao in val:
                    indices.append(j)
                    break
        return indices

    def _extrair_metadados(self, df: pd.DataFrame, linha_cabecalho: int, col_ini: int) -> tuple[str|None, str|None]:
        """
        Busca Documento e Plano Financeiro nas linhas acima do cabeçalho.
        
        A busca ocorre da linha imediatamente acima até `meta_rows_up` linhas acima.
        
        Args:
            df (pd.DataFrame): DataFrame da planilha.
            linha_cabecalho (int): Índice da linha de cabeçalho.
            col_ini (int): Índice inicial do bloco.
        
        Returns:
            tuple[str|None, str|None]: (Documento, Plano) ou (None, None) se não encontrado.
        """
        doc = plano = None
        for k in range(1, self.meta_rows_up + 2):
            r = linha_cabecalho - k
            if r < 0: break
            d = df.iat[r, col_ini] if col_ini < df.shape[1] else None
            p = df.iat[r, col_ini+1] if col_ini+1 < df.shape[1] else None
            d = str(d).strip() if pd.notna(d) else None
            p = str(p).strip() if pd.notna(p) else None
            if d and d.lower() != "nan" and p and p.lower() != "nan":
                doc, plano = d, p
                break
        return doc, plano

    def _parsear_bloco(self, df: pd.DataFrame, linha_cabecalho: int, col_ini: int) -> pd.DataFrame | None:
        """
        Extrai e trata um bloco de dados a partir de seu índice inicial de coluna.
        
        Processos:
        - Valida sequência de colunas ('Contrato', 'Valor', 'Data Crédito') ou variações.
        - Remove recabeçalhos e linhas vazias.
        - Converte 'Valor' para float, tratando formato brasileiro.
        - Converte 'Data Crédito' para datetime.
        - Filtra linhas com dados essenciais ausentes.
        
        Args:
            df (pd.DataFrame): DataFrame da planilha.
            linha_cabecalho (int): Índice da linha de cabeçalho.
            col_ini (int): Índice inicial do bloco.
        
        Returns:
            pd.DataFrame|None: DataFrame tratado ou None se inválido/vazio.
        """
        try:
            v1 = str(df.iat[linha_cabecalho, col_ini+1]).strip().lower()
            v2 = str(df.iat[linha_cabecalho, col_ini+2]).strip().lower()
        except Exception:
            return None
        
        # Verifica se v1 é uma variação de "Valor"
        valor_encontrado = any(variacao in v1 for variacao in self.variacoes_colunas["Valor"])
        
        # Verifica se v2 é uma variação de "Data Crédito"  
        data_encontrada = any(variacao in v2 for variacao in self.variacoes_colunas["Data Crédito"])
        
        if not valor_encontrado or not data_encontrada:
            return None

        sub = df.iloc[linha_cabecalho+1:, col_ini:col_ini+3].copy()
        sub.columns = self.cols_alvo

        # Remove recabeçalhos e linhas vazias usando variações de "Contrato"
        mask_recabecalho = pd.Series([False] * len(sub), index=sub.index)
        for variacao in self.variacoes_colunas["Contrato"]:
            mask_variacao = sub["Contrato"].astype(str).str.strip().str.lower().str.contains(variacao, na=False)
            mask_recabecalho = mask_recabecalho | mask_variacao
        
        sub = sub[~mask_recabecalho]
        sub = sub.dropna(how="all")

        # Trata Valor
        sub["Valor"] = sub["Valor"].apply(_parse_valor)
        sub = sub.dropna(subset=["Valor"])

        # Trata Data
        sub["Data Crédito"] = pd.to_datetime(sub["Data Crédito"], errors="coerce")

        # Filtra linhas essenciais
        sub = sub.dropna(subset=["Contrato", "Valor", "Data Crédito"])
        sub["Contrato"] = sub["Contrato"].astype(str).str.strip()

        return sub.reset_index(drop=True) if len(sub) else None

    def ler_planilha_layout(self, caminho_arquivo: str):
        """
        Lê a planilha 'Layout' e retorna os dados por bloco e as opções para UI.
        
        Args:
            caminho_arquivo (str): Caminho do arquivo Excel.
        
        Returns:
            tuple:
                - dict[(str, str), pd.DataFrame]: Dados por bloco, onde a chave é (Documento, Plano).
                - dict: Opções consolidadas para UI com 'documentos', 'planos_por_documento' e 'datas'.
        
        Raises:
            ErroLeituraArquivo: Se não houver blocos válidos ou ocorrer erro de leitura.
        """
        try:
            logger.info(f"Iniciando leitura do arquivo: {caminho_arquivo}")
            xls = pd.ExcelFile(caminho_arquivo, engine="openpyxl")
            df_original = pd.read_excel(xls, sheet_name=self.sheet_name, header=None)

            linha_cabecalho = self._encontrar_linha_cabecalho(df_original)
            logger.info(f"Cabeçalho encontrado na linha (0-based): {linha_cabecalho}")

            col_inicios = self._indices_inicio_blocos(df_original, linha_cabecalho)
            if not col_inicios:
                raise ErroLeituraArquivo("Nenhuma coluna 'Contrato' encontrada na linha do cabeçalho.")

            dados_por_bloco: dict[tuple[str, str], pd.DataFrame] = {}
            planos_por_documento: dict[str, set] = {}

            for col_ini in col_inicios:
                doc, plano = self._extrair_metadados(df_original, linha_cabecalho, col_ini)
                if not doc or not plano:
                    logger.warning(f"Metadados ausentes para bloco na coluna {col_ini}. Pulando.")
                    continue

                sub = self._parsear_bloco(df_original, linha_cabecalho, col_ini)
                if sub is None:
                    logger.warning(f"Bloco inválido ou vazio para {doc}-{plano} (coluna {col_ini}).")
                    continue

                key = (doc, plano)
                if key in dados_por_bloco:
                    dados_por_bloco[key] = pd.concat([dados_por_bloco[key], sub], ignore_index=True)
                else:
                    dados_por_bloco[key] = sub

                planos_por_documento.setdefault(doc, set()).add(plano)
                
                # Conta contratos válidos (valor != 0)
                contratos_validos = 0
                if not sub.empty and "Valor" in sub.columns:
                    valores_numericos = pd.to_numeric(sub["Valor"], errors="coerce")
                    contratos_validos = len(valores_numericos.dropna()[valores_numericos != 0])
                
                logger.info(f"Bloco {doc}-{plano} possui {contratos_validos} contratos válidos.")

            if not dados_por_bloco:
                raise ErroLeituraArquivo("Nenhum bloco de dados válido encontrado na planilha.")

            # Opções para UI
            documentos = sorted(planos_por_documento.keys())
            planos_por_documento = {k: sorted(list(v)) for k, v in planos_por_documento.items()}
            todas_datas = pd.concat(dados_por_bloco.values(), ignore_index=True)["Data Crédito"]
            datas_unicas = sorted(pd.to_datetime(todas_datas.dropna().unique()).tolist())

            opcoes_ui = {
                "documentos": documentos,
                "planos_por_documento": planos_por_documento,
                "datas": [d.date().isoformat() for d in datas_unicas],
            }

            logger.info(f"Total de blocos: {len(dados_por_bloco)}")
            return dados_por_bloco, opcoes_ui
        except ErroLeituraArquivo as e:
            logger.error(f"Erro na leitura do arquivo: {e.args[0] if e.args else str(e)}")
            raise ErroLeituraArquivo(f"Falha na leitura do arquivo Excel: {e}")
            
    def ler_e_validar_dados_validos(self, caminho_arquivo: str):
        """
        Lê a planilha e identifica apenas dados válidos (não zerados) para opções.
        Usa a validação existente do método ler_planilha_layout.
        
        Args:
            caminho_arquivo (str): Caminho do arquivo Excel.
            
        Returns:
            dict: Opções filtradas contendo apenas dados válidos e status das colunas.
        """
        from .processador import Processador
        
        try:
            # Usa o método existente que já valida as colunas corretamente
            dados_por_bloco, opcoes_completas = self.ler_planilha_layout(caminho_arquivo)
            
            # Se chegou até aqui, as colunas estão presentes (senão teria dado erro)
            colunas_obrigatorias = {
                "todas_presentes": True,
                "presentes": self.cols_alvo.copy(),
                "ausentes": []
            }
            
            # Usa o processador para identificar apenas dados válidos
            processador = Processador()
            dados_validos = processador.identificar_dados_validos(dados_por_bloco)
            
            # Adiciona informação das colunas ao resultado
            dados_validos["colunas_obrigatorias"] = colunas_obrigatorias
            
            logger.info("✅ Validação com dados válidos concluída com sucesso")
            return dados_validos
            
        except ErroLeituraArquivo as e:
            # Erro específico do leitor, provavelmente colunas ausentes
            logger.error(f"Erro na leitura do arquivo: {e.args[0] if e.args else str(e)}")
            
            # Identifica se é erro de colunas baseado na mensagem
            erro_msg = str(e)
            if "cabeçalho" in erro_msg.lower() or "contrato" in erro_msg.lower() or "valor" in erro_msg.lower() or "data" in erro_msg.lower():
                return {
                    "documentos": [],
                    "planos_por_documento": {},
                    "datas": [],
                    "doc_planos": [],
                    "colunas_obrigatorias": {
                        "todas_presentes": False, 
                        "presentes": [], 
                        "ausentes": self.cols_alvo
                    },
                    "erro": f"Colunas obrigatórias não encontradas: {erro_msg}"
                }
            else:
                return {
                    "documentos": [],
                    "planos_por_documento": {},
                    "datas": [],
                    "doc_planos": [],
                    "colunas_obrigatorias": {"todas_presentes": False, "presentes": [], "ausentes": self.cols_alvo},
                    "erro": f"Erro na leitura: {erro_msg}"
                }
        except Exception as e:
            logger.error(f"Erro inesperado ao validar dados: {e}")
            return {
                "documentos": [],
                "planos_por_documento": {},
                "datas": [],
                "doc_planos": [],
                "colunas_obrigatorias": {"todas_presentes": False, "presentes": [], "ausentes": self.cols_alvo},
                "erro": f"Erro inesperado: {e}"
            }

    def _verificar_colunas_obrigatorias(self, caminho_arquivo: str) -> dict:
        """
        Verifica se as colunas obrigatórias estão presentes na planilha.
        
        Args:
            caminho_arquivo (str): Caminho do arquivo Excel.
            
        Returns:
            dict: Status das colunas obrigatórias.
        """
        try:
            logger.info(f"Verificando colunas obrigatórias em: {caminho_arquivo}")
            xls = pd.ExcelFile(caminho_arquivo, engine="openpyxl")
            df_original = pd.read_excel(xls, sheet_name=self.sheet_name, header=None)

            # Procura por todas as colunas em todas as linhas
            colunas_encontradas = []
            
            for i, row in df_original.iterrows():
                vals = [str(x).strip().lower() for x in row.values if pd.notna(x)]
                for col in self.cols_alvo:
                    col_lower = col.lower()
                    if any(col_lower in v for v in vals) and col not in colunas_encontradas:
                        colunas_encontradas.append(col)
            
            colunas_ausentes = [col for col in self.cols_alvo if col not in colunas_encontradas]
            todas_presentes = len(colunas_ausentes) == 0
            
            resultado = {
                "todas_presentes": todas_presentes,
                "presentes": colunas_encontradas,
                "ausentes": colunas_ausentes
            }
            
            if todas_presentes:
                logger.info("✅ Todas as colunas obrigatórias estão presentes")
            else:
                logger.warning(f"❌ Colunas ausentes: {colunas_ausentes}")
                
            return resultado
            
        except Exception as e:
            logger.error(f"Erro ao verificar colunas: {e}")
            return {
                "todas_presentes": False,
                "presentes": [],
                "ausentes": self.cols_alvo,
                "erro": str(e)
            }

        except ErroLeituraArquivo:
            raise
        except Exception as e:
            logger.error(f"Erro ao ler o arquivo Excel: {e}")
            raise ErroLeituraArquivo(f"Falha na leitura do arquivo Excel: {e}")
