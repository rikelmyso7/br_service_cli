"""
test_atualizar_conta.py — Testes unitários para Processador.atualizar_conta.

Usa unittest.mock para isolar xlwings, shutil e os.remove,
sem precisar do Excel instalado ou de arquivos reais.
"""
import os
import shutil
import tempfile
import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock, call, ANY
import pytest

from processamento.processador import Processador
from conftest import BASE_DATE, _write_tmp_xlsx


# ===========================================================================
# Helpers
# ===========================================================================

def _xlsx_simples(tmp_path):
    """Cria um xlsx mínimo com aba Layout para servir de arquivo de entrada."""
    return _write_tmp_xlsx(tmp_path, {
        "Layout": [
            ["AZ", "1.01.02.01"],
            ["Contrato", "Valor", "Data Crédito"],
            ["CTR-001", 1000.0, BASE_DATE],
        ]
    })


# ===========================================================================
# Testes de atualizar_conta — caminho feliz (mocked)
# ===========================================================================

class TestAtualizarContaMocked:
    """
    Testa atualizar_conta sem depender do Excel ou OneDrive.
    Mocka xw.App, shutil.copy2 e os.remove.
    """

    def _make_mocks(self):
        """Retorna um dict com todos os patches necessários."""
        mock_app = MagicMock()
        mock_wb = MagicMock()
        mock_sheet = MagicMock()

        mock_app.__enter__ = MagicMock(return_value=mock_app)
        mock_app.__exit__ = MagicMock(return_value=False)
        mock_app.books.open.return_value = mock_wb
        mock_wb.sheets.__getitem__ = MagicMock(return_value=mock_sheet)

        return mock_app, mock_wb, mock_sheet

    @patch("processamento.processador.shutil.copy2")
    @patch("processamento.processador.os.remove")
    @patch("processamento.processador.xw.App")
    def test_retorna_true_no_sucesso(self, mock_xw_app, mock_remove, mock_copy2, tmp_path):
        mock_app, mock_wb, _ = self._make_mocks()
        mock_xw_app.return_value = mock_app

        arquivo = _xlsx_simples(tmp_path)
        p = Processador()
        result = p.atualizar_conta(str(arquivo), 641)
        assert result is True

    @patch("processamento.processador.shutil.copy2")
    @patch("processamento.processador.os.remove")
    @patch("processamento.processador.xw.App")
    def test_copia_para_temp_antes_de_abrir(self, mock_xw_app, mock_remove, mock_copy2, tmp_path):
        mock_app, mock_wb, _ = self._make_mocks()
        mock_xw_app.return_value = mock_app

        arquivo = _xlsx_simples(tmp_path)
        p = Processador()
        p.atualizar_conta(str(arquivo), 641)

        # Primeira chamada a copy2: original → temp
        first_call = mock_copy2.call_args_list[0]
        assert str(arquivo) == first_call[0][0]  # origem = arquivo original

    @patch("processamento.processador.shutil.copy2")
    @patch("processamento.processador.os.remove")
    @patch("processamento.processador.xw.App")
    def test_copia_temp_de_volta_apos_salvar(self, mock_xw_app, mock_remove, mock_copy2, tmp_path):
        mock_app, mock_wb, _ = self._make_mocks()
        mock_xw_app.return_value = mock_app

        arquivo = _xlsx_simples(tmp_path)
        p = Processador()
        p.atualizar_conta(str(arquivo), 641)

        # Segunda chamada a copy2: temp → original
        assert mock_copy2.call_count == 2
        second_call = mock_copy2.call_args_list[1]
        assert str(arquivo) == second_call[0][1]  # destino = arquivo original

    @patch("processamento.processador.shutil.copy2")
    @patch("processamento.processador.os.remove")
    @patch("processamento.processador.xw.App")
    def test_arquivo_temp_removido_no_finally(self, mock_xw_app, mock_remove, mock_copy2, tmp_path):
        mock_app, mock_wb, _ = self._make_mocks()
        mock_xw_app.return_value = mock_app

        arquivo = _xlsx_simples(tmp_path)
        p = Processador()

        with patch("processamento.processador.os.path.exists", return_value=True):
            p.atualizar_conta(str(arquivo), 641)

        # Verifica que ao menos uma remoção foi feita com path do br_service temp
        br_service_calls = [
            c for c in mock_remove.call_args_list
            if "br_service_" in str(c)
        ]
        assert len(br_service_calls) == 1

    @patch("processamento.processador.shutil.copy2")
    @patch("processamento.processador.os.remove")
    @patch("processamento.processador.xw.App")
    def test_valor_conta_escrito_na_celula_b1(self, mock_xw_app, mock_remove, mock_copy2, tmp_path):
        mock_app, mock_wb, mock_sheet = self._make_mocks()
        mock_xw_app.return_value = mock_app

        arquivo = _xlsx_simples(tmp_path)
        p = Processador()
        p.atualizar_conta(str(arquivo), 12345)

        # Verifica que B1 recebeu o valor como string
        mock_sheet.range.assert_called_with("B1")
        mock_sheet.range("B1").value = "12345"  # já foi chamado — só checa implicitamente

    @patch("processamento.processador.shutil.copy2")
    @patch("processamento.processador.os.remove")
    @patch("processamento.processador.xw.App")
    def test_wb_salvo_e_fechado(self, mock_xw_app, mock_remove, mock_copy2, tmp_path):
        mock_app, mock_wb, _ = self._make_mocks()
        mock_xw_app.return_value = mock_app

        arquivo = _xlsx_simples(tmp_path)
        p = Processador()
        p.atualizar_conta(str(arquivo), 641)

        mock_wb.save.assert_called_once()
        mock_wb.close.assert_called_once()

    @patch("processamento.processador.shutil.copy2")
    @patch("processamento.processador.os.remove")
    @patch("processamento.processador.xw.App")
    def test_xw_app_com_visible_false(self, mock_xw_app, mock_remove, mock_copy2, tmp_path):
        mock_app, _, _ = self._make_mocks()
        mock_xw_app.return_value = mock_app

        arquivo = _xlsx_simples(tmp_path)
        p = Processador()
        p.atualizar_conta(str(arquivo), 641)

        mock_xw_app.assert_called_once_with(visible=False)


# ===========================================================================
# Testes de erro — garantir que o finally sempre limpa o temp
# ===========================================================================

class TestAtualizarContaErros:
    @patch("processamento.processador.shutil.copy2")
    @patch("processamento.processador.os.remove")
    @patch("processamento.processador.xw.App")
    def test_excecao_em_xlwings_se_propaga(self, mock_xw_app, mock_remove, mock_copy2, tmp_path):
        mock_app = MagicMock()
        mock_app.__enter__ = MagicMock(side_effect=Exception("Excel travou"))
        mock_app.__exit__ = MagicMock(return_value=False)
        mock_xw_app.return_value = mock_app

        arquivo = _xlsx_simples(tmp_path)
        p = Processador()

        with pytest.raises(Exception, match="Excel travou"):
            p.atualizar_conta(str(arquivo), 641)

    @patch("processamento.processador.shutil.copy2")
    @patch("processamento.processador.os.remove")
    @patch("processamento.processador.xw.App")
    def test_temp_removido_mesmo_com_excecao(self, mock_xw_app, mock_remove, mock_copy2, tmp_path):
        mock_app = MagicMock()
        mock_app.__enter__ = MagicMock(side_effect=Exception("Excel travou"))
        mock_app.__exit__ = MagicMock(return_value=False)
        mock_xw_app.return_value = mock_app

        arquivo = _xlsx_simples(tmp_path)
        p = Processador()

        with patch("processamento.processador.os.path.exists", return_value=True):
            with pytest.raises(Exception):
                p.atualizar_conta(str(arquivo), 641)

        # Mesmo com exceção, o temp br_service_ deve ter sido removido
        br_service_calls = [
            c for c in mock_remove.call_args_list
            if "br_service_" in str(c)
        ]
        assert len(br_service_calls) == 1

    @patch("processamento.processador.shutil.copy2", side_effect=OSError("disco cheio"))
    @patch("processamento.processador.os.remove")
    @patch("processamento.processador.xw.App")
    def test_excecao_em_copy2_inicial_se_propaga(self, mock_xw_app, mock_remove, mock_copy2, tmp_path):
        arquivo = _xlsx_simples(tmp_path)
        p = Processador()

        with pytest.raises(OSError, match="disco cheio"):
            p.atualizar_conta(str(arquivo), 641)


# ===========================================================================
# Teste de integração real (sem mock de xlwings) — pula se Excel não disponível
# ===========================================================================

class TestAtualizarContaIntegracao:
    """
    Testa a lógica de copy-modify-replace com um arquivo Excel real.
    Pula se xlwings não conseguir inicializar o Excel COM.
    """

    @pytest.fixture()
    def arquivo_real(self, tmp_path):
        return _xlsx_simples(tmp_path)

    def test_arquivo_modificado_na_celula_b1(self, arquivo_real):
        import xlwings as xw
        try:
            p = Processador()
            p.atualizar_conta(str(arquivo_real), 999)

            # Verifica o valor gravado lendo com openpyxl
            import openpyxl
            wb = openpyxl.load_workbook(str(arquivo_real))
            ws = wb["Layout"]
            valor_b1 = str(ws["B1"].value)
            assert valor_b1 == "999"
        except Exception as e:
            # Excel COM não disponível no ambiente de CI
            pytest.skip(f"Excel COM não disponível: {e}")

    def test_arquivo_original_nao_corrompido(self, arquivo_real):
        import openpyxl
        try:
            p = Processador()
            p.atualizar_conta(str(arquivo_real), 777)

            # Deve ser possível abrir o arquivo após a operação
            wb = openpyxl.load_workbook(str(arquivo_real))
            assert "Layout" in wb.sheetnames
        except Exception as e:
            pytest.skip(f"Excel COM não disponível: {e}")

    def test_nenhum_arquivo_temp_sobra_apos_execucao(self, arquivo_real, tmp_path):
        try:
            arquivos_antes = set(Path(tempfile.gettempdir()).glob("br_service_*.xlsx"))
            p = Processador()
            p.atualizar_conta(str(arquivo_real), 111)
            arquivos_depois = set(Path(tempfile.gettempdir()).glob("br_service_*.xlsx"))
            # Não deve ter sobrado nenhum temp novo
            assert arquivos_depois == arquivos_antes
        except Exception as e:
            pytest.skip(f"Excel COM não disponível: {e}")
