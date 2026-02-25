"""
test_gerador.py — Testes unitários para src/processamento/gerador.py
"""
import datetime
import pytest
import pandas as pd
from pathlib import Path

from processamento.gerador import Gerador, _sanitize
from utils.exceptions import BRServiceError
from conftest import BASE_DATE


# ===========================================================================
# _sanitize
# ===========================================================================

class TestSanitize:
    def test_remove_caracteres_invalidos_windows(self):
        assert _sanitize('nome:arq?*') == 'nomearq'

    def test_string_normal_inalterada(self):
        assert _sanitize("AZ-1.01.02.01") == "AZ-1.01.02.01"

    def test_barras_removidas(self):
        assert "/" not in _sanitize("a/b\\c")
        assert "\\" not in _sanitize("a/b\\c")

    def test_string_vazia(self):
        assert _sanitize("") == ""


# ===========================================================================
# Helpers
# ===========================================================================

def _df(n=3, valor_base=1000.0):
    return pd.DataFrame({
        "Contrato": [f"CTR-{i+1:03d}" for i in range(n)],
        "Valor": [valor_base + i * 100 for i in range(n)],
        "Data Crédito": pd.to_datetime([
            BASE_DATE + datetime.timedelta(days=i) for i in range(n)
        ]),
    })


# ===========================================================================
# Gerador.gerar_arquivos_saida (saída .xls)
# ===========================================================================

class TestGerarArquivosSaida:
    def test_gera_um_arquivo_por_bloco(self, tmp_path):
        g = Gerador()
        dados = {
            ("AZ", "1.01.02.01"): _df(),
            ("REG", "1.04.01.08"): _df(n=2, valor_base=500.0),
        }
        paths = g.gerar_arquivos_saida(dados, str(tmp_path))
        assert len(paths) == 2
        for p in paths:
            assert p.exists()
            assert p.suffix == ".xls"

    def test_cria_pasta_por_documento(self, tmp_path):
        g = Gerador()
        dados = {("AZ", "1.01.02.01"): _df()}
        paths = g.gerar_arquivos_saida(dados, str(tmp_path))
        assert paths[0].parent.name == "AZ"

    def test_nome_pasta_customizado(self, tmp_path):
        g = Gerador()
        dados = {("AZ", "1.01.02.01"): _df()}
        paths = g.gerar_arquivos_saida(dados, str(tmp_path), nome_pasta="MinhaPasta")
        assert paths[0].parent.name == "MinhaPasta"

    def test_versionamento_arquivo_existente(self, tmp_path):
        g = Gerador()
        dados = {("AZ", "1.01.02.01"): _df()}
        p1 = g.gerar_arquivos_saida(dados, str(tmp_path))[0]
        p2 = g.gerar_arquivos_saida(dados, str(tmp_path))[0]
        assert p1 != p2
        assert "v2" in p2.name

    def test_bloco_vazio_ignorado(self, tmp_path):
        g = Gerador()
        df_vazio = pd.DataFrame(columns=["Contrato", "Valor", "Data Crédito"])
        dados = {
            ("AZ", "1.01"): _df(),
            ("REG", "2.02"): df_vazio,
        }
        paths = g.gerar_arquivos_saida(dados, str(tmp_path))
        assert len(paths) == 1

    def test_colunas_saida_no_arquivo(self, tmp_path):
        import xlrd
        g = Gerador()
        dados = {("AZ", "1.01.02.01"): _df()}
        path = g.gerar_arquivos_saida(dados, str(tmp_path))[0]
        wb = xlrd.open_workbook(str(path))
        ws = wb.sheet_by_index(0)
        header = [ws.cell_value(0, c) for c in range(ws.ncols)]
        assert "Contrato" in header
        assert "Valor" in header

    def test_datas_derivadas_de_data_credito(self, tmp_path):
        """Data de Emissão, Vencimento e Competência devem ser derivadas de Data Crédito."""
        import xlrd
        g = Gerador()
        dados = {("AZ", "1.01"): _df(n=1)}
        path = g.gerar_arquivos_saida(dados, str(tmp_path))[0]
        wb = xlrd.open_workbook(str(path))
        ws = wb.sheet_by_index(0)
        header = [ws.cell_value(0, c) for c in range(ws.ncols)]
        assert "Data de Emissão" in header
        assert "Data de Vencimento" in header
        assert "Data de Competência" in header

    def test_retorna_lista_vazia_sem_dados(self, tmp_path):
        g = Gerador()
        df_vazio = pd.DataFrame(columns=["Contrato", "Valor", "Data Crédito"])
        paths = g.gerar_arquivos_saida({("AZ", "1.01"): df_vazio}, str(tmp_path))
        assert paths == []

    def test_progress_callback_chamado(self, tmp_path):
        g = Gerador()
        dados = {
            ("AZ", "1.01"): _df(),
            ("REG", "2.02"): _df(n=2),
        }
        calls = []
        g.gerar_arquivos_saida(dados, str(tmp_path), progress_cb=lambda idx, total, path: calls.append((idx, total)))
        assert len(calls) == 2
        assert calls[0] == (1, 2)
        assert calls[1] == (2, 2)

    def test_colunas_saida_customizadas(self, tmp_path):
        import xlrd
        colunas = ["Contrato", "Valor"]
        g = Gerador(colunas_saida=colunas)
        dados = {("AZ", "1.01"): _df()}
        path = g.gerar_arquivos_saida(dados, str(tmp_path))[0]
        wb = xlrd.open_workbook(str(path))
        ws = wb.sheet_by_index(0)
        header = [ws.cell_value(0, c) for c in range(ws.ncols)]
        assert header == colunas
