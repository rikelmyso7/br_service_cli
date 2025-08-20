from __future__ import annotations

from typing import Iterable, Dict, Tuple
import pandas as pd
from datetime import datetime

from utils.logger import configurar_logger

logger = configurar_logger(__name__)

def _to_date_series(s: pd.Series) -> pd.Series:
    """
    Normaliza uma série de datas para `datetime64[ns]` e retorna `.dt.date`.
    Aceita série object com strings; tenta parsear sob dayfirst=True.
    """
    if s.dtype == "O":
        s = pd.to_datetime(s, errors="coerce", dayfirst=True)
    return s.dt.date

class Processador:
    """
    Realiza o pós-processamento e o filtro dos dados lidos do Excel
    por Documento, Plano e Data(s).
    """

    def processar_dados(
        self,
        dados_por_bloco: Dict[Tuple[str, str], pd.DataFrame],
        documentos_selecionados: Iterable[str] | None = None,
        datas_selecionadas: Iterable | None = None,
        data_inicial: str | pd.Timestamp | None = None,
        data_final: str | pd.Timestamp | None = None,
        planos_selecionados: Iterable[str] | None = None,
    ) -> Dict[Tuple[str, str], pd.DataFrame]:
        """
        Aplica filtros opcionais e devolve novos DataFrames por bloco.

        Args:
            dados_por_bloco: dicionário {(Documento, Plano): DataFrame}
            documentos_selecionados: filtra por documentos (exatos).
            datas_selecionadas: coleção de datas específicas (date/datetime/'DD/MM/AAAA').
            data_inicial: data mínima (inclusive) — pode ser 'DD/MM/AAAA'.
            data_final: data máxima (inclusive) — pode ser 'DD/MM/AAAA'.
            planos_selecionados: filtra por planos (exatos).

        Returns:
            dict[(Documento, Plano), DataFrame]: blocos filtrados e normalizados.
        """
        documentos_sel = set(map(str, documentos_selecionados)) if documentos_selecionados else None
        planos_sel = set(map(str, planos_selecionados)) if planos_selecionados else None

        # Normaliza datas específicas
        datas_sel = set()
        if datas_selecionadas:
            s = pd.Series(list(datas_selecionadas))
            if s.dtype == "O":
                s = pd.to_datetime(s, errors="coerce", dayfirst=True)
            datas_sel = set(s.dropna().dt.date.tolist())

        # Normaliza intervalos
        di = pd.to_datetime(data_inicial, errors="coerce", dayfirst=True).date() if data_inicial is not None else None
        df_ = pd.to_datetime(data_final, errors="coerce", dayfirst=True).date() if data_final is not None else None

        resultado: Dict[Tuple[str, str], pd.DataFrame] = {}
        for (doc, plano), df in dados_por_bloco.items():
            doc_plano_chave = f"{doc}-{plano}"
            # Permite filtrar tanto por documento individual quanto por documento-plano
            if documentos_sel and doc not in documentos_sel and doc_plano_chave not in documentos_sel:
                continue
            if planos_sel and plano not in planos_sel:
                continue

            temp = df.copy()

            # Garante colunas essenciais
            obrig = ["Contrato", "Valor", "Data Crédito"]
            falt = [c for c in obrig if c not in temp.columns]
            if falt:
                logger.warning(f"Bloco {(doc, plano)} sem colunas obrigatórias: {falt}. Ignorando.")
                continue

            # Normaliza datas para date
            temp["__date"] = _to_date_series(temp["Data Crédito"])

            # Filtros de datas
            if datas_sel:
                temp = temp[temp["__date"].isin(datas_sel)]
            if di:
                temp = temp[temp["__date"] >= di]
            if df_:
                temp = temp[temp["__date"] <= df_]

            if temp.empty:
                continue

            # Valor numérico com 2 casas
            temp["Valor"] = pd.to_numeric(temp["Valor"], errors="coerce")

            # Identifica e loga contratos com valor zerado
            df_zerado = temp[temp["Valor"] == 0]
            if not df_zerado.empty:
                contratos_zero = df_zerado["Contrato"].dropna().astype(str).tolist()
                logger.warning(
                    f"Bloco {(doc, plano)} possui contratos com valor zerado: {', '.join(contratos_zero)}. Ignorando essas linhas."
                )
                temp = temp[temp["Valor"].notna() & (temp["Valor"] != 0)]

            temp = temp.dropna(subset=["Valor"])

            # Ordenação previsível
            temp = temp.sort_values(["__date", "Contrato"]).drop(columns="__date")
            resultado[(doc, plano)] = temp

        if not resultado:
            logger.warning("Processador retornou vazio após aplicação dos filtros.")
        else:
            logger.info(f"Processador gerou {len(resultado)} blocos após filtros.")
        return resultado

    def identificar_dados_validos(
        self,
        dados_por_bloco: Dict[Tuple[str, str], pd.DataFrame],
    ) -> Dict[str, any]:
        """
        Identifica quais combinações de documentos e datas possuem dados válidos (não zerados).
        
        Args:
            dados_por_bloco: dicionário {(Documento, Plano): DataFrame}
            
        Returns:
            dict: estrutura com documentos, datas e combinações que possuem dados válidos
        """
        documentos_validos = set()
        datas_validas = set()
        doc_planos_validos = []
        planos_por_documento_validos = {}
        datas_por_documento = {}
        
        for (doc, plano), df in dados_por_bloco.items():
            if df.empty:
                continue
                
            # Verifica se há registros com valor != 0
            temp = df.copy()
            temp["Valor"] = pd.to_numeric(temp["Valor"], errors="coerce")
            temp = temp.dropna(subset=["Valor"])
            temp = temp[temp["Valor"] != 0]
            
            if not temp.empty:
                # Esta combinação tem dados válidos
                doc_plano_chave = f"{doc}-{plano}"
                documentos_validos.add(doc_plano_chave)
                doc_planos_validos.append(doc_plano_chave)
                
                if doc_plano_chave not in planos_por_documento_validos:
                    planos_por_documento_validos[doc_plano_chave] = set()
                planos_por_documento_validos[doc_plano_chave].add(plano)
                
                # Normaliza datas e adiciona às válidas
                temp["__date"] = pd.to_datetime(temp["Data Crédito"], errors="coerce", dayfirst=True)
                datas_do_bloco = temp["__date"].dropna().dt.strftime("%d/%m/%Y").unique()
                datas_validas.update(datas_do_bloco)
                
                # Armazena datas específicas para este documento-plano
                datas_por_documento[doc_plano_chave] = sorted(list(datas_do_bloco))
                
                logger.info(f"Bloco {doc}-{plano} possui {len(temp)} registros válidos")
            else:
                logger.warning(f"Bloco {doc}-{plano} não possui dados válidos (todos zerados)")
                # Adiciona entrada vazia para documentos sem dados válidos
                doc_plano_chave = f"{doc}-{plano}"
                datas_por_documento[doc_plano_chave] = []
        
        # Converte sets para listas ordenadas
        planos_por_documento_final = {k: sorted(list(v)) for k, v in planos_por_documento_validos.items()}
        
        resultado = {
            "documentos": sorted(list(documentos_validos)),
            "planos_por_documento": planos_por_documento_final,
            "datas": sorted(list(datas_validas)),
            "datas_por_documento": datas_por_documento,
            "doc_planos": sorted(doc_planos_validos)
        }
        
        logger.info(f"Dados válidos identificados: {len(documentos_validos)} documentos, {len(datas_validas)} datas")
        return resultado
