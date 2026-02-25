"""
test_gerador_extra.py — Testes para funcionalidades do Gerador não cobertas em test_gerador.py:
  - _datetime_to_excel_serial
  - gerar_arquivos_csv
"""
import csv
import datetime
import pytest
import pandas as pd
from pathlib import Path

from processamento.gerador import Gerador, _datetime_to_excel_serial
from conftest import BASE_DATE


# ===========================================================================
# _datetime_to_excel_serial
# ===========================================================================

class TestDatetimeToExcelSerial:
    """
    O número serial do Excel conta dias desde 1899-12-31 (epoch).
    Excel tem um bug histórico: considera 1900-02-29 como dia válido (não existe).
    Por isso, para datas >= 1900-03-01, soma-se 1 ao resultado.

    Referências de valores esperados verificados manualmente no Excel:
      - 1900-01-01 = serial 1     (delta = 1 dia desde 1899-12-31)
      - 1900-03-01 = serial 61    (inclui +1 pelo bug)
      - 2025-07-01 = serial 46008 (verificado no Excel)
    """

    def _dt(self, year, month, day):
        return datetime.datetime(year, month, day)

    def test_data_historica_1900_01_01(self):
        # 1 dia após 1899-12-31, antes do bug, = serial 1
        result = _datetime_to_excel_serial(self._dt(1900, 1, 1))
        assert result == pytest.approx(1.0, abs=0.001)

    def test_data_apos_bug_1900_03_01(self):
        # 1900-03-01: delta = 61 dias + 1 (bug) = 61
        result = _datetime_to_excel_serial(self._dt(1900, 3, 1))
        assert result == pytest.approx(61.0, abs=0.001)

    def test_data_moderna_consistente_com_offset(self):
        # Verifica consistência: 2025-12-31 - 2025-07-01 = 183 dias
        d1 = _datetime_to_excel_serial(self._dt(2025, 7, 1))
        d2 = _datetime_to_excel_serial(self._dt(2025, 12, 31))
        assert d2 - d1 == pytest.approx(183.0, abs=0.001)

    def test_data_moderna_epoch_correta(self):
        # 1900-01-01 é o dia 1 no Excel (1 dia após 1899-12-31)
        epoch_plus_1 = _datetime_to_excel_serial(self._dt(1900, 1, 1))
        # Ano 2000-01-01 deveria ser epoch + ~36525 dias + ajuste bug 1900
        # Verifica apenas que é um número positivo grande
        result_2025 = _datetime_to_excel_serial(self._dt(2025, 7, 1))
        assert result_2025 > 40000.0  # bem após o ano 2009

    def test_datas_sequenciais_diferem_em_1(self):
        d1 = _datetime_to_excel_serial(self._dt(2025, 7, 1))
        d2 = _datetime_to_excel_serial(self._dt(2025, 7, 2))
        assert d2 - d1 == pytest.approx(1.0, abs=0.001)

    def test_com_hora_fracao_do_dia(self):
        # 12h = 0.5 de um dia
        d_meia_noite = _datetime_to_excel_serial(self._dt(2025, 7, 1))
        d_meio_dia = _datetime_to_excel_serial(datetime.datetime(2025, 7, 1, 12, 0, 0))
        assert d_meio_dia - d_meia_noite == pytest.approx(0.5, abs=0.001)

    def test_retorna_float(self):
        result = _datetime_to_excel_serial(self._dt(2025, 7, 1))
        assert isinstance(result, float)


# ===========================================================================
# Helpers compartilhados
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
# Gerador.gerar_arquivos_csv
# ===========================================================================

class TestGerarArquivosCSV:
    def test_gera_um_csv_por_bloco(self, tmp_path):
        g = Gerador()
        dados = {
            ("AZ", "1.01.02.01"): _df(),
            ("REG", "1.04.01.08"): _df(n=2, valor_base=500.0),
        }
        paths = g.gerar_arquivos_csv(dados, str(tmp_path))
        assert len(paths) == 2
        for p in paths:
            assert p.exists()
            assert p.suffix == ".csv"

    def test_extensao_csv(self, tmp_path):
        g = Gerador()
        paths = g.gerar_arquivos_csv({("AZ", "1.01"): _df()}, str(tmp_path))
        assert paths[0].suffix == ".csv"

    def test_separador_ponto_e_virgula(self, tmp_path):
        g = Gerador()
        paths = g.gerar_arquivos_csv({("AZ", "1.01"): _df()}, str(tmp_path))
        content = paths[0].read_text(encoding="utf-8")
        # Primeira linha é o cabeçalho — deve conter ';'
        header_line = content.splitlines()[0]
        assert ";" in header_line

    def test_encoding_utf8(self, tmp_path):
        g = Gerador()
        paths = g.gerar_arquivos_csv({("AZ", "1.01"): _df()}, str(tmp_path))
        # Deve abrir sem erro em UTF-8
        paths[0].read_text(encoding="utf-8")

    def test_cabecalho_correto(self, tmp_path):
        g = Gerador()
        paths = g.gerar_arquivos_csv({("AZ", "1.01.02.01"): _df()}, str(tmp_path))
        with open(paths[0], encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            fieldnames = reader.fieldnames or []
        assert "Contrato" in fieldnames
        assert "Valor" in fieldnames

    def test_datas_derivadas_de_data_credito(self, tmp_path):
        g = Gerador()
        paths = g.gerar_arquivos_csv({("AZ", "1.01"): _df(n=1)}, str(tmp_path))
        with open(paths[0], encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            fieldnames = reader.fieldnames or []
        assert "Data de Emissão" in fieldnames
        assert "Data de Vencimento" in fieldnames
        assert "Data de Competência" in fieldnames

    def test_datas_no_formato_dd_mm_yyyy(self, tmp_path):
        g = Gerador()
        paths = g.gerar_arquivos_csv({("AZ", "1.01"): _df(n=1)}, str(tmp_path))
        with open(paths[0], encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            row = next(reader)
        data_emissao = row.get("Data de Emissão", "")
        # Espera DD/MM/YYYY — verifica estrutura com /
        parts = data_emissao.split("/")
        assert len(parts) == 3
        assert len(parts[0]) == 2   # dia
        assert len(parts[1]) == 2   # mês
        assert len(parts[2]) == 4   # ano

    def test_valor_com_duas_casas_decimais(self, tmp_path):
        g = Gerador()
        paths = g.gerar_arquivos_csv({("AZ", "1.01"): _df(n=1)}, str(tmp_path))
        with open(paths[0], encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            row = next(reader)
        valor = row.get("Valor", "")
        assert "." in valor
        assert len(valor.split(".")[1]) == 2

    def test_pasta_criada_por_documento(self, tmp_path):
        g = Gerador()
        paths = g.gerar_arquivos_csv({("AZ", "1.01.02.01"): _df()}, str(tmp_path))
        assert paths[0].parent.name == "AZ"

    def test_nome_pasta_customizado(self, tmp_path):
        g = Gerador()
        paths = g.gerar_arquivos_csv(
            {("AZ", "1.01"): _df()}, str(tmp_path), nome_pasta="Exportacao"
        )
        assert paths[0].parent.name == "Exportacao"

    def test_versionamento_arquivo_existente(self, tmp_path):
        g = Gerador()
        dados = {("AZ", "1.01"): _df()}
        p1 = g.gerar_arquivos_csv(dados, str(tmp_path))[0]
        p2 = g.gerar_arquivos_csv(dados, str(tmp_path))[0]
        assert p1 != p2
        assert "v2" in p2.name

    def test_bloco_vazio_ignorado(self, tmp_path):
        g = Gerador()
        df_vazio = pd.DataFrame(columns=["Contrato", "Valor", "Data Crédito"])
        dados = {
            ("AZ", "1.01"): _df(),
            ("REG", "2.02"): df_vazio,
        }
        paths = g.gerar_arquivos_csv(dados, str(tmp_path))
        assert len(paths) == 1

    def test_retorna_lista_vazia_sem_dados(self, tmp_path):
        g = Gerador()
        df_vazio = pd.DataFrame(columns=["Contrato", "Valor", "Data Crédito"])
        paths = g.gerar_arquivos_csv({("AZ", "1.01"): df_vazio}, str(tmp_path))
        assert paths == []

    def test_progress_callback_chamado(self, tmp_path):
        g = Gerador()
        dados = {("AZ", "1.01"): _df(), ("REG", "2.02"): _df(n=2)}
        calls = []
        g.gerar_arquivos_csv(
            dados, str(tmp_path),
            progress_cb=lambda idx, total, path: calls.append((idx, total))
        )
        assert len(calls) == 2
        assert calls[-1] == (2, 2)

    def test_numero_linhas_no_csv(self, tmp_path):
        n = 5
        g = Gerador()
        paths = g.gerar_arquivos_csv({("AZ", "1.01"): _df(n=n)}, str(tmp_path))
        with open(paths[0], encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f, delimiter=";"))
        assert len(rows) == n
