"""
test_validador.py — Testes unitários para src/validacao/validador.py
"""
import datetime
import pytest
import pandas as pd
from pathlib import Path

from validacao.validador import Validador, _parse_date_str_br, _as_date_set
from utils.exceptions import ErroValidacaoDados


# ===========================================================================
# Funções auxiliares internas
# ===========================================================================

class TestParseDateStrBr:
    def test_data_valida(self):
        result = _parse_date_str_br("05/07/2025")
        assert result == datetime.date(2025, 7, 5)

    def test_data_invalida_retorna_none(self):
        assert _parse_date_str_br("nao-e-data") is None
        assert _parse_date_str_br("") is None
        assert _parse_date_str_br("2025-07-05") is None  # formato ISO não suportado

    def test_data_com_espacos(self):
        result = _parse_date_str_br("  01/01/2025  ")
        assert result == datetime.date(2025, 1, 1)


class TestAsDateSet:
    def test_aceita_strings_br(self):
        result = _as_date_set(["01/07/2025", "02/07/2025"])
        assert datetime.date(2025, 7, 1) in result
        assert datetime.date(2025, 7, 2) in result

    def test_aceita_date_objects(self):
        d = datetime.date(2025, 7, 1)
        result = _as_date_set([d])
        assert d in result

    def test_aceita_datetime_objects(self):
        dt = datetime.datetime(2025, 7, 1, 10, 0, 0)
        result = _as_date_set([dt])
        assert datetime.date(2025, 7, 1) in result

    def test_strings_invalidas_ignoradas(self):
        result = _as_date_set(["invalida", "xyz"])
        assert len(result) == 0

    def test_none_retorna_vazio(self):
        assert _as_date_set(None) == set()

    def test_lista_vazia(self):
        assert _as_date_set([]) == set()


# ===========================================================================
# Validador.validar_pasta_saida
# ===========================================================================

class TestValidarPastaSaida:
    def test_cria_pasta_inexistente(self, tmp_path):
        v = Validador()
        nova = tmp_path / "nova" / "pasta"
        result = v.validar_pasta_saida(str(nova))
        assert result.exists()
        assert result.is_dir()

    def test_pasta_existente_ok(self, tmp_path):
        v = Validador()
        result = v.validar_pasta_saida(str(tmp_path))
        assert result == tmp_path

    def test_retorna_path_object(self, tmp_path):
        v = Validador()
        result = v.validar_pasta_saida(str(tmp_path))
        assert isinstance(result, Path)

    def test_aceita_path_object(self, tmp_path):
        v = Validador()
        result = v.validar_pasta_saida(tmp_path)
        assert result == tmp_path


# ===========================================================================
# Validador.validar_selecoes
# ===========================================================================

class TestValidarSelecoes:
    DOCS = ["AZ-1.01.02.01", "REG-1.04.01.08"]
    DATAS = ["01/07/2025", "02/07/2025", "03/07/2025"]

    def test_selecao_valida_nao_levanta(self):
        v = Validador()
        v.validar_selecoes(self.DOCS, self.DATAS, ["AZ-1.01.02.01"], ["01/07/2025"])

    def test_documento_invalido_levanta_erro(self):
        v = Validador()
        with pytest.raises(ErroValidacaoDados, match="Documentos inválidos"):
            v.validar_selecoes(self.DOCS, self.DATAS, ["NAOEXISTE"], None)

    def test_data_invalida_levanta_erro(self):
        v = Validador()
        with pytest.raises(ErroValidacaoDados, match="Datas inválidas"):
            v.validar_selecoes(self.DOCS, self.DATAS, None, ["31/12/2099"])

    def test_selecao_none_nao_valida(self):
        v = Validador()
        # None significa "sem filtro" — não deve levantar erro
        v.validar_selecoes(self.DOCS, self.DATAS, None, None)

    def test_selecao_vazia_nao_levanta(self):
        v = Validador()
        v.validar_selecoes(self.DOCS, self.DATAS, [], [])

    def test_mensagem_erro_combina_doc_e_data(self):
        v = Validador()
        with pytest.raises(ErroValidacaoDados) as exc_info:
            v.validar_selecoes(self.DOCS, self.DATAS, ["RUIM"], ["31/12/2099"])
        msg = str(exc_info.value)
        assert "Documentos inválidos" in msg
        assert "Datas inválidas" in msg

    def test_data_como_date_object_valida(self):
        v = Validador()
        d = datetime.date(2025, 7, 1)
        # datas_disponiveis como strings, selecionada como date — deve funcionar
        v.validar_selecoes(self.DOCS, self.DATAS, None, [d])

    def test_espacos_em_documentos_ignorados(self):
        v = Validador()
        v.validar_selecoes(self.DOCS, self.DATAS, ["  AZ-1.01.02.01  "], None)


# ===========================================================================
# Validador.validar_dados_processados
# ===========================================================================

class TestValidarDadosProcessados:
    def _df_ok(self):
        return pd.DataFrame({
            "Contrato": ["CTR-001"],
            "Valor": [1000.0],
            "Data Crédito": pd.to_datetime(["2025-07-01"]),
        })

    def test_dados_validos_nao_levanta(self):
        v = Validador()
        v.validar_dados_processados({("AZ", "1.01"): self._df_ok()})

    def test_dict_vazio_levanta_erro(self):
        v = Validador()
        with pytest.raises(ErroValidacaoDados, match="Não há dados processados"):
            v.validar_dados_processados({})

    def test_todos_blocos_vazios_levanta_erro(self):
        v = Validador()
        df_vazio = pd.DataFrame(columns=["Contrato", "Valor", "Data Crédito"])
        with pytest.raises(ErroValidacaoDados, match="vazios"):
            v.validar_dados_processados({("AZ", "1.01"): df_vazio})

    def test_coluna_faltante_levanta_erro(self):
        v = Validador()
        df = pd.DataFrame({"Contrato": ["CTR-001"], "Valor": [100.0]})  # sem Data Crédito
        with pytest.raises(ErroValidacaoDados, match="colunas obrigatórias"):
            v.validar_dados_processados({("AZ", "1.01"): df})

    def test_bloco_vazio_entre_validos_ok(self):
        v = Validador()
        df_vazio = pd.DataFrame(columns=["Contrato", "Valor", "Data Crédito"])
        dados = {
            ("AZ", "1.01"): df_vazio,
            ("REG", "2.02"): self._df_ok(),
        }
        v.validar_dados_processados(dados)  # não deve levantar
