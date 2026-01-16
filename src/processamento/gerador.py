from __future__ import annotations

from pathlib import Path
import pandas as pd
import xlwt
from typing import Callable, Optional
from datetime import datetime

from utils.logger import configurar_logger

logger = configurar_logger(__name__)

def _sanitize(s: str) -> str:
    """
    Remove caracteres inválidos para nomes de arquivo/pasta no Windows/macOS.
    """
    return "".join(c for c in str(s) if c not in '\\/:*?"<>|').strip()

from datetime import datetime

def _datetime_to_excel_serial(dt):
    """Converte datetime para número serial do Excel, ajustando pelo bug de 1900."""
    excel_epoch = datetime(1899, 12, 31)  # Mudar para 31/12/1899
    delta = dt - excel_epoch
    serial = delta.days + (delta.seconds / 86400.0)
    if dt >= datetime(1900, 3, 1):
        serial += 1
    return serial

class Gerador:
    """
    Gera arquivos Excel de saída a partir dos DataFrames processados por bloco.
    
    Recursos:
    - Garante a presença de colunas de data esperadas (Data de Emissão, Data de Vencimento, Data de Competência).
    - Aplica formatação de data e número no Excel.
    - Cria pastas por documento e versiona arquivo se já existir.
    """

    def __init__(self, colunas_saida: list[str] | None = None):
        """
        Args:
            colunas_saida (list[str] | None): Ordem de colunas na saída.
                Se None, usa um conjunto padrão comum.
        """
        self.colunas_saida = colunas_saida or [
            "Contrato",
            "Valor",
            "Data de Emissão",
            "Data de Vencimento",
            "Data de Competência",
        ]


    def gerar_arquivos_saida(self, dados: dict, pasta_destino, nome_pasta:  str | None = None, sheet_name: str = "Dados", progress_cb: Optional[Callable[[int, int, str], None]] = None,) -> list[Path]:
        """
        Gera um arquivo Excel por bloco (Documento, Plano) com colunas padronizadas.

        Args:
            dados: dict[(Documento, Plano), pd.DataFrame]
            pasta_destino: str | PathLike — pasta raiz de saída
            sheet_name: nome da planilha no Excel

        Returns:
            list[Path]: caminhos dos arquivos gerados.
        """
        out_paths: list[Path] = []
        root = Path(pasta_destino)
        root.mkdir(parents=True, exist_ok=True)

        total = len(dados)

        for idx, ((doc, plano), df) in enumerate(dados.items(), start=1):
            if df.empty:
                logger.warning(f"Sem linhas para {doc}-{plano}. Pulando geração.")
                continue

            df_out = df.copy()

            # Garante colunas de data derivadas de 'Data Crédito' se não existirem
            for col in ("Data de Emissão", "Data de Vencimento", "Data de Competência"):
                if col not in df_out.columns:
                    df_out[col] = df_out.get("Data Crédito")

            # Converte colunas de data para datetime (mantém como datetime para Excel)
            for col in ("Data de Emissão", "Data de Vencimento", "Data de Competência"):
                if col in df_out.columns:
                    df_out[col] = pd.to_datetime(df_out[col], errors="coerce")

            # Garante todas as colunas de saída
            faltantes = [c for c in self.colunas_saida if c not in df_out.columns]
            for m in faltantes:
                df_out[m] = ""

            # Converte coluna Valor para string com 2 casas decimais
            if "Valor" in df_out.columns:
                df_out["Valor"] = df_out["Valor"].apply(lambda x: f"{float(x):.2f}" if pd.notna(x) and x != "" else str(x))

            df_out = df_out[self.colunas_saida]

            # Pasta de destino do arquivo
            if nome_pasta:
                dir_doc = root / _sanitize(nome_pasta)
            else:
                dir_doc = root / _sanitize(doc)
            dir_doc.mkdir(parents=True, exist_ok=True)

            base = f"{_sanitize(doc)}-{_sanitize(plano)}.xls"
            path = dir_doc / base

            # Versiona se já existir
            k = 2
            while path.exists():
                path = dir_doc / f"{_sanitize(doc)}-{_sanitize(plano)}-v{k}.xls"
                k += 1

            # Usar xlwt para criar arquivo XLS
            workbook = xlwt.Workbook()
            worksheet = workbook.add_sheet(sheet_name)
            
            # Criar estilos
            date_style = xlwt.XFStyle()
            date_style.num_format_str = 'dd/mm/YYYY'
            
            # Definir colunas de data
            date_columns = {"Data de Emissão", "Data de Vencimento", "Data de Competência"}
            
            # Escrever cabeçalhos
            for col_idx, col_name in enumerate(df_out.columns):
                worksheet.write(0, col_idx, col_name)
            
            # Escrever dados com formatação apropriada
            for row_idx, row in enumerate(df_out.itertuples(index=False), start=1):
                for col_idx, value in enumerate(row):
                    col_name = df_out.columns[col_idx]
                    
                    if pd.isna(value):
                        worksheet.write(row_idx, col_idx, "")
                    elif col_name in date_columns and pd.notna(value):
                        # Converter data para número serial do Excel
                        try:
                            if isinstance(value, str):
                                date_obj = pd.to_datetime(value)
                            else:
                                date_obj = value
                            
                            if pd.notna(date_obj):
                                # Converter para número serial do Excel e aplicar formato de data
                                excel_serial = _datetime_to_excel_serial(date_obj)
                                worksheet.write(row_idx, col_idx, excel_serial, date_style)
                            else:
                                worksheet.write(row_idx, col_idx, "")
                        except:
                            worksheet.write(row_idx, col_idx, str(value) if value else "")
                    else:
                        worksheet.write(row_idx, col_idx, value)
            
            # Definir larguras das colunas
            for i, col in enumerate(df_out.columns):
                worksheet.col(i).width = max(3000, min(10000, len(col) * 256 + 512))
            
            # Salvar arquivo
            workbook.save(str(path))

        # Progresso por arquivo
        if progress_cb:
            progress_cb(idx, total, str(path))

        logger.info(f"Arquivo gerado: {path}")
        out_paths.append(path)

        if not out_paths:
            logger.warning("Nenhum arquivo foi gerado (todos os blocos estavam vazios).")
        return out_paths

    def gerar_arquivos_csv(self, dados: dict, pasta_destino, nome_pasta: str | None = None, progress_cb: Optional[Callable[[int, int, str], None]] = None) -> list[Path]:
        """
        Gera arquivos CSV com separador ; a partir dos DataFrames processados por bloco.
        
        Args:
            dados: dict[(Documento, Plano), pd.DataFrame]
            pasta_destino: str | PathLike — pasta raiz de saída
            progress_cb: callback de progresso opcional
            
        Returns:
            list[Path]: caminhos dos arquivos gerados.
        """
        out_paths: list[Path] = []
        root = Path(pasta_destino)
        root.mkdir(parents=True, exist_ok=True)
        
        total = len(dados)
        
        for idx, ((doc, plano), df) in enumerate(dados.items(), start=1):
            if df.empty:
                logger.warning(f"Sem linhas para {doc}-{plano}. Pulando geração.")
                continue
                
            df_out = df.copy()
            
            # Garante colunas de data derivadas de 'Data Crédito' se não existirem
            for col in ("Data de Emissão", "Data de Vencimento", "Data de Competência"):
                if col not in df_out.columns:
                    df_out[col] = df_out.get("Data Crédito")

            # Converte colunas de data para formato MM/DD/YYYY (string para CSV)
            for col in ("Data de Emissão", "Data de Vencimento", "Data de Competência"):
                if col in df_out.columns:
                    df_out[col] = pd.to_datetime(df_out[col], errors="coerce").dt.strftime("%d/%m/%Y")
            
            # Garante todas as colunas de saída
            faltantes = [c for c in self.colunas_saida if c not in df_out.columns]
            for m in faltantes:
                df_out[m] = ""
            
            # Converte coluna Valor para string com 2 casas decimais
            if "Valor" in df_out.columns:
                df_out["Valor"] = df_out["Valor"].apply(lambda x: f"{float(x):.2f}" if pd.notna(x) and x != "" else str(x))
            
            df_out = df_out[self.colunas_saida]
            
            # Pasta de destino do arquivo
            if nome_pasta:
                dir_doc = root / _sanitize(nome_pasta)
            else:
                dir_doc = root / _sanitize(doc)
            dir_doc.mkdir(parents=True, exist_ok=True)
            
            base = f"{_sanitize(doc)}-{_sanitize(plano)}.csv"
            path = dir_doc / base
            
            # Versiona se já existir
            k = 2
            while path.exists():
                path = dir_doc / f"{_sanitize(doc)}-{_sanitize(plano)}-v{k}.csv"
                k += 1
            
            # Salva como CSV com separador ;
            df_out.to_csv(path, sep=';', index=False, encoding='utf-8', lineterminator='\n')
            
            # Progresso por arquivo
            if progress_cb:
                progress_cb(idx, total, str(path))
                
            logger.info(f"Arquivo CSV gerado: {path}")
            out_paths.append(path)
        
        if not out_paths:
            logger.warning("Nenhum arquivo CSV foi gerado (todos os blocos estavam vazios).")
        return out_paths
