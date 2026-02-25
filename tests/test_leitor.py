"""
test_leitor.py — Testes unitários para src/processamento/leitor.py
"""
import datetime
import pytest
import pandas as pd

from processamento.leitor import LeitorExcel, _parse_valor, _parse_valor_vetorizado
from utils.exceptions import ErroLeituraArquivo
from conftest import BASE_DATE, _layout_rows, _write_tmp_xlsx


# ===========================================================================
# _parse_valor — conversão de valores individuais
# ===========================================================================

class TestParseValor:
    def test_inteiro(self):
        assert _parse_valor(100) == 100.0

    def test_float_duas_casas(self):
        assert _parse_valor(628.91) == 628.91

    def test_string_ponto_decimal(self):
        assert _parse_valor("20166.12") == 20166.12

    def test_string_virgula_decimal(self):
        assert _parse_valor("628,91") == 628.91

    def test_string_formato_br_milhar(self):
        assert _parse_valor("1.234,56") == 1234.56

    def test_negativo_parenteses(self):
        assert _parse_valor("(500,00)") == -500.0

    def test_valor_zero(self):
        assert _parse_valor(0) == 0.0

    def test_nan_retorna_na(self):
        import pandas as pd
        result = _parse_valor(float("nan"))
        assert pd.isna(result)

    def test_string_vazia_retorna_na(self):
        import pandas as pd
        assert pd.isna(_parse_valor(""))

    def test_string_invalida_retorna_na(self):
        import pandas as pd
        assert pd.isna(_parse_valor("abc"))

    def test_arredondamento_tres_casas(self):
        # 3 casas decimais devem ser arredondadas para 2
        result = _parse_valor("123.456")
        assert result == round(123.456, 2)

    def test_nbsp_removido(self):
        # Non-breaking space deve ser tratado
        assert _parse_valor("1\u00A0000,00") == 1000.0


class TestParseValorVetorizado:
    def _s(self, vals):
        return pd.Series(vals)

    def test_numericos_arredonda(self):
        result = _parse_valor_vetorizado(self._s([1.005, 2.0, 3.999]))
        assert result.tolist() == pytest.approx([1.0, 2.0, 4.0], abs=0.01)

    def test_strings_mistas(self):
        result = _parse_valor_vetorizado(self._s(["1.234,56", "628,91", "(100,00)"]))
        assert result.tolist() == pytest.approx([1234.56, 628.91, -100.0])

    def test_vazio_vira_nan(self):
        result = _parse_valor_vetorizado(self._s(["", None, float("nan")]))
        assert result.isna().all()

    def test_serie_ja_numerica(self):
        s = pd.Series([100.0, 200.0, 300.0])
        result = _parse_valor_vetorizado(s)
        assert result.tolist() == pytest.approx([100.0, 200.0, 300.0])


# ===========================================================================
# LeitorExcel — encontrar cabeçalho e índices de blocos
# ===========================================================================

class TestEncontrarCabecalho:
    def _df(self, rows):
        return pd.DataFrame(rows)

    def test_cabecalho_primeira_linha(self):
        df = self._df([
            ["Contrato", "Valor", "Data Crédito"],
            ["CTR-001", 1000, "2025-07-01"],
        ])
        leitor = LeitorExcel()
        assert leitor._encontrar_linha_cabecalho(df) == 0

    def test_cabecalho_apos_metadados(self):
        df = self._df([
            ["AZ", "1.01.02.01", None],
            ["Contrato", "Valor", "Data Crédito"],
        ])
        leitor = LeitorExcel()
        assert leitor._encontrar_linha_cabecalho(df) == 1

    def test_variacao_colunas_minusculas(self):
        df = self._df([
            ["contrato", "valor", "data credito"],
            ["CTR-001", 100, "2025-07-01"],
        ])
        leitor = LeitorExcel()
        assert leitor._encontrar_linha_cabecalho(df) == 0

    def test_variacao_data_dt_credito(self):
        df = self._df([
            ["Contrato", "Valor", "Dt Crédito"],
            ["CTR-001", 100, "2025-07-01"],
        ])
        leitor = LeitorExcel()
        assert leitor._encontrar_linha_cabecalho(df) == 0

    def test_cabecalho_nao_encontrado_levanta_erro(self):
        df = self._df([
            ["ColA", "ColB", "ColC"],
            ["X", "Y", "Z"],
        ])
        leitor = LeitorExcel()
        with pytest.raises(ErroLeituraArquivo):
            leitor._encontrar_linha_cabecalho(df)

    def test_cabecalho_parcial_levanta_erro(self):
        # Só 2 das 3 colunas obrigatórias
        df = self._df([
            ["Contrato", "Valor", "OutraColuna"],
        ])
        leitor = LeitorExcel()
        with pytest.raises(ErroLeituraArquivo):
            leitor._encontrar_linha_cabecalho(df)


class TestIndicesInicioBloco:
    def test_unico_bloco(self):
        df = pd.DataFrame([["Contrato", "Valor", "Data Crédito"]])
        leitor = LeitorExcel()
        assert leitor._indices_inicio_blocos(df, 0) == [0]

    def test_dois_blocos_horizontais(self):
        df = pd.DataFrame([[
            "Contrato", "Valor", "Data Crédito",
            "Contrato", "Valor", "Data Crédito",
        ]])
        leitor = LeitorExcel()
        assert leitor._indices_inicio_blocos(df, 0) == [0, 3]

    def test_sem_contrato_retorna_vazio(self):
        df = pd.DataFrame([["ColA", "ColB", "ColC"]])
        leitor = LeitorExcel()
        assert leitor._indices_inicio_blocos(df, 0) == []


class TestExtrairMetadados:
    def test_metadados_uma_linha_acima(self):
        df = pd.DataFrame([
            ["AZ", "1.01.02.01", None],
            ["Contrato", "Valor", "Data Crédito"],
        ])
        leitor = LeitorExcel()
        doc, plano = leitor._extrair_metadados(df, linha_cabecalho=1, col_ini=0)
        assert doc == "AZ"
        assert plano == "1.01.02.01"

    def test_metadados_ausentes_retorna_none(self):
        df = pd.DataFrame([
            ["Contrato", "Valor", "Data Crédito"],
        ])
        leitor = LeitorExcel()
        doc, plano = leitor._extrair_metadados(df, linha_cabecalho=0, col_ini=0)
        assert doc is None
        assert plano is None


# ===========================================================================
# LeitorExcel.ler_planilha_layout — integração com arquivos reais
# ===========================================================================

class TestLerPlanilhaLayout:
    def test_leitura_basica(self, layout_simples_xlsx):
        leitor = LeitorExcel()
        dados, opcoes = leitor.ler_planilha_layout(str(layout_simples_xlsx))

        assert len(dados) == 1
        (doc, plano), df = next(iter(dados.items()))
        assert doc == "AZ"
        assert plano == "1.01.02.01"
        assert len(df) == 3
        assert list(df.columns) == ["Contrato", "Valor", "Data Crédito"]

    def test_opcoes_ui_retornadas(self, layout_simples_xlsx):
        leitor = LeitorExcel()
        _, opcoes = leitor.ler_planilha_layout(str(layout_simples_xlsx))

        assert "documentos" in opcoes
        assert "planos_por_documento" in opcoes
        assert "datas" in opcoes
        assert "AZ" in opcoes["documentos"]

    def test_dois_blocos_horizontais(self, layout_multiplos_blocos_xlsx):
        leitor = LeitorExcel()
        dados, _ = leitor.ler_planilha_layout(str(layout_multiplos_blocos_xlsx))

        assert len(dados) == 2
        docs = {doc for doc, _ in dados}
        assert "AZ" in docs
        assert "REG" in docs

    def test_valores_numericos_convertidos(self, layout_simples_xlsx):
        leitor = LeitorExcel()
        dados, _ = leitor.ler_planilha_layout(str(layout_simples_xlsx))
        df = list(dados.values())[0]
        assert pd.api.types.is_float_dtype(df["Valor"])

    def test_datas_convertidas_para_datetime(self, layout_simples_xlsx):
        leitor = LeitorExcel()
        dados, _ = leitor.ler_planilha_layout(str(layout_simples_xlsx))
        df = list(dados.values())[0]
        assert pd.api.types.is_datetime64_any_dtype(df["Data Crédito"])

    def test_formato_br_valores(self, layout_valor_formato_br_xlsx):
        leitor = LeitorExcel()
        dados, _ = leitor.ler_planilha_layout(str(layout_valor_formato_br_xlsx))
        df = list(dados.values())[0]
        valores = df["Valor"].tolist()
        assert 1234.56 in valores
        assert 628.91 in valores
        assert -500.0 in valores

    def test_sem_cabecalho_levanta_erro(self, layout_sem_cabecalho_xlsx):
        leitor = LeitorExcel()
        with pytest.raises(ErroLeituraArquivo):
            leitor.ler_planilha_layout(str(layout_sem_cabecalho_xlsx))

    def test_arquivo_inexistente_levanta_erro(self, tmp_path):
        leitor = LeitorExcel()
        with pytest.raises(Exception):
            leitor.ler_planilha_layout(str(tmp_path / "nao_existe.xlsx"))


# ===========================================================================
# LeitorExcel.ler_e_validar_dados_validos
# ===========================================================================

class TestLerEValidarDadosValidos:
    def test_retorna_estrutura_correta(self, layout_simples_xlsx):
        leitor = LeitorExcel()
        resultado = leitor.ler_e_validar_dados_validos(str(layout_simples_xlsx))

        assert "documentos" in resultado
        assert "planos_por_documento" in resultado
        assert "datas" in resultado
        assert "colunas_obrigatorias" in resultado
        assert resultado["colunas_obrigatorias"]["todas_presentes"] is True

    def test_valores_zerados_excluidos(self, layout_valor_zerado_xlsx):
        leitor = LeitorExcel()
        resultado = leoco = leitor.ler_e_validar_dados_validos(str(layout_valor_zerado_xlsx))
        # AZ-1.01.02.01 deve aparecer nos documentos válidos (tem dados não-zero)
        assert len(resultado["documentos"]) > 0

    def test_arquivo_sem_cabecalho_retorna_erro_sem_raise(self, layout_sem_cabecalho_xlsx):
        leitor = LeitorExcel()
        resultado = leitor.ler_e_validar_dados_validos(str(layout_sem_cabecalho_xlsx))
        assert resultado["documentos"] == []
        assert resultado["colunas_obrigatorias"]["todas_presentes"] is False
