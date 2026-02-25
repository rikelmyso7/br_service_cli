"""
test_processador.py — Testes unitários para src/processamento/processador.py
"""
import json
import datetime
import pytest
import pandas as pd

from processamento.processador import Processador
from conftest import BASE_DATE


# ===========================================================================
# Helpers
# ===========================================================================

def _make_df(contratos, valores, datas):
    return pd.DataFrame({
        "Contrato": contratos,
        "Valor": valores,
        "Data Crédito": pd.to_datetime(datas),
    })


def _bloco(doc, plano, n=3, valor_base=1000.0, offset_days=0):
    contratos = [f"CTR-{i+1:03d}" for i in range(n)]
    valores = [valor_base + i * 100 for i in range(n)]
    datas = [
        BASE_DATE + datetime.timedelta(days=i + offset_days)
        for i in range(n)
    ]
    return (doc, plano), _make_df(contratos, valores, datas)


# ===========================================================================
# processar_dados
# ===========================================================================

class TestProcessarDados:
    @pytest.fixture()
    def dados(self):
        k1, df1 = _bloco("AZ", "1.01.02.01", n=3)
        k2, df2 = _bloco("REG", "1.04.01.08", n=2, offset_days=5)
        return {k1: df1, k2: df2}

    def test_sem_filtros_retorna_todos(self, dados):
        p = Processador()
        result = p.processar_dados(dados)
        assert len(result) == 2

    def test_filtro_por_documento(self, dados):
        p = Processador()
        result = p.processar_dados(dados, documentos_selecionados=["AZ"])
        assert len(result) == 1
        assert ("AZ", "1.01.02.01") in result

    def test_filtro_por_documento_plano(self, dados):
        p = Processador()
        result = p.processar_dados(dados, documentos_selecionados=["AZ-1.01.02.01"])
        assert ("AZ", "1.01.02.01") in result

    def test_filtro_por_data(self, dados):
        p = Processador()
        data_alvo = BASE_DATE.strftime("%d/%m/%Y")
        result = p.processar_dados(dados, datas_selecionadas=[data_alvo])
        # Apenas bloco AZ tem dado nesta data
        assert ("AZ", "1.01.02.01") in result
        df = result[("AZ", "1.01.02.01")]
        datas = df["Data Crédito"].dt.date.tolist()
        assert all(d == BASE_DATE for d in datas)

    def test_filtro_documento_inexistente_retorna_vazio(self, dados):
        p = Processador()
        result = p.processar_dados(dados, documentos_selecionados=["NAOEXISTE"])
        assert len(result) == 0

    def test_linhas_valor_zero_excluidas(self):
        _, df = _bloco("AZ", "1.01", n=3)
        df.loc[1, "Valor"] = 0.0
        p = Processador()
        result = p.processar_dados({("AZ", "1.01"): df})
        assert 0.0 not in result[("AZ", "1.01")]["Valor"].tolist()

    def test_linhas_valor_nan_excluidas(self):
        _, df = _bloco("AZ", "1.01", n=3)
        df.loc[0, "Valor"] = float("nan")
        p = Processador()
        result = p.processar_dados({("AZ", "1.01"): df})
        assert not result[("AZ", "1.01")]["Valor"].isna().any()

    def test_resultado_ordenado_por_data_contrato(self):
        # Insere dados fora de ordem
        df = _make_df(
            ["CTR-C", "CTR-A", "CTR-B"],
            [300.0, 100.0, 200.0],
            ["2025-07-03", "2025-07-01", "2025-07-02"],
        )
        p = Processador()
        result = p.processar_dados({("AZ", "1.01"): df})
        datas = result[("AZ", "1.01")]["Data Crédito"].dt.date.tolist()
        assert datas == sorted(datas)

    def test_bloco_sem_colunas_obrigatorias_ignorado(self):
        df = pd.DataFrame({"X": [1, 2], "Y": [3, 4]})
        p = Processador()
        result = p.processar_dados({("AZ", "1.01"): df})
        assert len(result) == 0

    def test_intervalo_data_inicial_final(self):
        _, df = _bloco("AZ", "1.01", n=5)
        di = BASE_DATE + datetime.timedelta(days=1)
        df_ = BASE_DATE + datetime.timedelta(days=3)
        p = Processador()
        result = p.processar_dados(
            {("AZ", "1.01"): df},
            data_inicial=di.strftime("%d/%m/%Y"),
            data_final=df_.strftime("%d/%m/%Y"),
        )
        datas = result[("AZ", "1.01")]["Data Crédito"].dt.date.tolist()
        assert all(di <= d <= df_ for d in datas)


# ===========================================================================
# identificar_dados_validos
# ===========================================================================

class TestIdentificarDadosValidos:
    def test_estrutura_retornada(self):
        _, df = _bloco("AZ", "1.01.02.01", n=3)
        p = Processador()
        result = p.identificar_dados_validos({("AZ", "1.01.02.01"): df})

        assert "documentos" in result
        assert "planos_por_documento" in result
        assert "datas" in result
        assert "datas_por_documento" in result

    def test_bloco_valido_incluido(self):
        _, df = _bloco("AZ", "1.01.02.01", n=3)
        p = Processador()
        result = p.identificar_dados_validos({("AZ", "1.01.02.01"): df})
        assert "AZ-1.01.02.01" in result["documentos"]

    def test_bloco_todos_zerados_excluido(self):
        df = _make_df(
            ["CTR-001", "CTR-002"],
            [0.0, 0.0],
            ["2025-07-01", "2025-07-02"],
        )
        p = Processador()
        result = p.identificar_dados_validos({("AZ", "1.01"): df})
        assert "AZ-1.01" not in result["documentos"]

    def test_datas_por_documento_corretas(self):
        _, df = _bloco("AZ", "1.01.02.01", n=2)
        p = Processador()
        result = p.identificar_dados_validos({("AZ", "1.01.02.01"): df})
        assert "AZ-1.01.02.01" in result["datas_por_documento"]
        assert len(result["datas_por_documento"]["AZ-1.01.02.01"]) == 2

    def test_bloco_vazio_ignorado(self):
        df = pd.DataFrame(columns=["Contrato", "Valor", "Data Crédito"])
        p = Processador()
        result = p.identificar_dados_validos({("AZ", "1.01"): df})
        assert len(result["documentos"]) == 0

    def test_dois_blocos_um_invalido(self):
        _, df1 = _bloco("AZ", "1.01", n=2)
        df2 = _make_df(["CTR-X"], [0.0], ["2025-07-01"])
        p = Processador()
        result = p.identificar_dados_validos({
            ("AZ", "1.01"): df1,
            ("REG", "2.02"): df2,
        })
        assert "AZ-1.01" in result["documentos"]
        assert "REG-2.02" not in result["documentos"]


# ===========================================================================
# analisar_contas — testa somente a serialização JSON e chaves do resultado
# ===========================================================================

class TestAnalisarContasSerializacao:
    def test_retorno_e_json_valido(self, tmp_path):
        """
        Como 'Resumo por Conta' provavelmente não existe no xlsx mínimo,
        verifica apenas que o retorno é um JSON com as chaves esperadas.
        """
        import io
        import openpyxl

        # Cria xlsx mínimo com aba Resumo por Conta
        wb = openpyxl.Workbook()
        ws_resumo = wb.active
        ws_resumo.title = "Resumo por Conta"
        ws_resumo.append(["Conta", 12345])

        # Aba de conta para mapear
        ws_conta = wb.create_sheet(title="12345-Teste")
        ws_conta.append(["Contrato", "Valor"])
        ws_conta.append(["CTR-001", 1000])
        ws_conta.append(["CTR-002", 2000])

        path = tmp_path / "contas.xlsx"
        wb.save(str(path))

        p = Processador()
        raw = p.analisar_contas(str(path))
        data = json.loads(raw)

        assert "contas_ativas" in data
        assert "contas_inativas" in data

    def test_sem_aba_resumo_levanta_excecao(self, layout_simples_xlsx):
        """Arquivo sem 'Resumo por Conta' deve levantar KeyError ou similar."""
        p = Processador()
        with pytest.raises(Exception):
            p.analisar_contas(str(layout_simples_xlsx))
