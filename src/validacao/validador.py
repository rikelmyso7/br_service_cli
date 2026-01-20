from __future__ import annotations

from pathlib import Path
from typing import Iterable, Set
import datetime as dt

from utils.exceptions import ErroValidacaoDados
from utils.logger import configurar_logger

logger = configurar_logger(__name__)

def _to_path(p) -> Path:
    """
    Converte entrada em Path, preservando se já for Path.
    """
    return p if isinstance(p, Path) else Path(p)

def _parse_date_str_br(s: str) -> dt.date | None:
    """
    Converte string 'DD/MM/AAAA' para date. Retorna None se inválida.
    """
    try:
        return dt.datetime.strptime(s.strip(), "%d/%m/%Y").date()
    except Exception:
        return None

def _as_date_set(datas: Iterable) -> Set[dt.date]:
    """
    Normaliza coleção de datas: aceita date, datetime ou 'DD/MM/AAAA'.
    Retorna conjunto de date.
    """
    out: Set[dt.date] = set()
    for d in (datas or []):
        if isinstance(d, dt.datetime):
            out.add(d.date())
        elif isinstance(d, dt.date):
            out.add(d)
        elif isinstance(d, str):
            parsed = _parse_date_str_br(d)
            if parsed:
                out.add(parsed)
    return out

class Validador:
    """
    Funções de validação de entradas do usuário e pré-condições
    para processamento e geração de arquivos.
    """

    def validar_pasta_saida(self, pasta_destino) -> Path:
        """
        Garante que a pasta de saída existe (cria se necessário) e é gravável.

        Args:
            pasta_destino: str | PathLike

        Returns:
            Path: caminho normalizado.

        Raises:
            ErroValidacaoDados: se não for possível criar ou gravar.
        """
        path = _to_path(pasta_destino)
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ErroValidacaoDados(f"Não foi possível criar a pasta '{path}': {e}")
        if not path.exists():
            raise ErroValidacaoDados(f"Pasta de saída '{path}' não existe e não pôde ser criada.")
        if not path.is_dir():
            raise ErroValidacaoDados(f"'{path}' não é uma pasta.")
        # Testa permissão de escrita
        test = path / ".perm_teste.tmp"
        try:
            test.write_text("ok", encoding="utf-8")
        except PermissionError as e:
            raise ErroValidacaoDados(f"Sem permissão de escrita em '{path}': {e}")
        except OSError as e:
            raise ErroValidacaoDados(f"Erro ao testar escrita em '{path}': {e}")
        finally:
            # Garante remoção do arquivo temporário mesmo em caso de exceção
            try:
                test.unlink(missing_ok=True)
            except OSError:
                pass  # Ignora se não conseguir remover

        logger.debug(f"Pasta de saída válida: {path}")
        return path

    def validar_selecoes(
        self,
        documentos_disponiveis: Iterable[str],
        datas_disponiveis: Iterable,
        documentos_selecionados: Iterable[str] | None,
        datas_selecionadas: Iterable | None
    ) -> None:
        """
        Valida se seleções do usuário existem entre as opções disponíveis.

        Args:
            documentos_disponiveis: lista de documentos válidos.
            datas_disponiveis: lista/iterável de datas (date, datetime ou 'DD/MM/AAAA').
            documentos_selecionados: selecionados pelo usuário (pode ser None).
            datas_selecionadas: selecionadas pelo usuário (pode ser None).

        Raises:
            ErroValidacaoDados: se houver documentos ou datas inválidas.
        """
        docs_disp = set(map(lambda s: str(s).strip(), documentos_disponiveis or []))
        docs_sel = set(map(lambda s: str(s).strip(), documentos_selecionados or [])) if documentos_selecionados else set()

        datas_disp = _as_date_set(datas_disponiveis or [])
        datas_sel = _as_date_set(datas_selecionadas or [])

        docs_invalid = [d for d in docs_sel if d not in docs_disp]
        datas_invalid = [d for d in datas_sel if d not in datas_disp]

        msgs = []
        if docs_invalid:
            msgs.append(f"Documentos inválidos: {', '.join(docs_invalid)}")
        if datas_invalid:
            msgs.append("Datas inválidas: " + ", ".join(d.strftime("%d/%m/%Y") for d in sorted(datas_invalid)))
        if msgs:
            raise ErroValidacaoDados(" | ".join(msgs))

        logger.debug(f"Seleções válidas: docs={sorted(docs_sel)}, datas={[d.isoformat() for d in sorted(datas_sel)]}")

    def validar_dados_processados(self, dados_por_bloco: dict) -> None:
        """
        Garante que o dicionário de dados processados contém ao menos
        um DataFrame não vazio com colunas essenciais.

        Args:
            dados_por_bloco: dict[(doc, plano), DataFrame]

        Raises:
            ErroValidacaoDados: se estiver vazio/inválido.
        """
        if not dados_por_bloco:
            raise ErroValidacaoDados("Não há dados processados.")
        total_ok = 0
        for key, df in dados_por_bloco.items():
            if getattr(df, "empty", True):
                continue
            faltantes = [c for c in ("Contrato", "Valor", "Data Crédito") if c not in df.columns]
            if faltantes:
                raise ErroValidacaoDados(f"Bloco {key} sem colunas obrigatórias: {faltantes}")
            total_ok += len(df)
        if total_ok == 0:
            raise ErroValidacaoDados("Todos os blocos estão vazios após o processamento.")
        logger.debug(f"Dados processados válidos. Linhas totais: {total_ok}") 