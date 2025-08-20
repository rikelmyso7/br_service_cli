
"""
main.py

Ponto de entrada principal para o sistema BR Service.
Orquestra a leitura, processamento, validação e geração de arquivos Excel.
Lida com argumentos de linha de comando e comunicação via Standard I/O.
"""

import argparse, json, os, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from src.processamento.leitor import LeitorExcel
from src.processamento.processador import Processador
from src.processamento.gerador import Gerador
from src.validacao.validador import Validador
from src.utils.exceptions import BRServiceError, ErroValidacaoDados
from src.utils.logger import configurar_logger, emit_event
from src.config.configuracao import Configuracao

config_path = ROOT / 'config.json'
config_app = Configuracao(caminho_config=str(config_path))

log_dir = ROOT / config_app.obter_config('diretorio_logs')
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / f"br_service_{os.getpid()}.log"

# Logger será configurado depois de analisar argumentos para suporte ao --quiet
logger = None

def configurar_logger_com_quiet(quiet_mode: bool):
    """Configura o logger baseado no modo quiet."""
    from src.utils.logger import configurar_logger
    import logging
    
    if quiet_mode:
        # Em modo quiet, redireciona console logs para stderr e reduz nível
        logger_instance = logging.getLogger("br_service")
        logger_instance.setLevel(config_app.obter_config('nivel_log'))
        logger_instance.propagate = False
        
        # Remove handlers existentes para reconfigurar
        for handler in logger_instance.handlers[:]:
            logger_instance.removeHandler(handler)
            
        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(module)s:%(lineno)d | %(message)s"
        )
        
        # Console handler vai para stderr
        ch = logging.StreamHandler(sys.stderr)
        ch.setLevel(config_app.obter_config('nivel_log'))
        ch.setFormatter(fmt)
        logger_instance.addHandler(ch)
        
        # File handler
        fh = logging.FileHandler(str(log_file), encoding="utf-8")
        fh.setLevel(config_app.obter_config('nivel_log'))
        fh.setFormatter(fmt)
        logger_instance.addHandler(fh)
        
        return logger_instance
    else:
        # Modo normal
        return configurar_logger(caminho_log=str(log_file), nivel=config_app.obter_config('nivel_log'))

def obter_opcoes(caminho_arquivo: str):
    """Lê o Excel e retorna opções de documentos, planos e datas já formatadas."""
    leitor = LeitorExcel()
    try:
        # Usa o novo método que filtra apenas dados válidos
        dados_validos = leitor.ler_e_validar_dados_validos(caminho_arquivo)

        if not dados_validos.get("documentos"):
            logger.warning("Nenhum dado válido encontrado na planilha Layout para extrair opções.")
            print(json.dumps({"documentos": [], "planos_por_documento": {}, "datas": [], "dados_validos": dados_validos}, ensure_ascii=False))
            return
        
        # Inclui a seção dados_validos no retorno (sem datas_por_documento)
        opcoes_resposta = {
            "documentos": dados_validos["documentos"],
            "planos_por_documento": dados_validos["planos_por_documento"], 
            "datas": dados_validos["datas"],
            "dados_validos": dados_validos
        }
        
        print(json.dumps(opcoes_resposta, ensure_ascii=False))
        logger.info("Opções com dados válidos enviadas para a UI.")
    except BRServiceError as e:
        logger.error(f"Erro ao obter opções: {e.mensagem}")
        print(json.dumps({"erro": e.mensagem}, ensure_ascii=False))
    except Exception as e:
        logger.critical(f"Erro inesperado ao obter opções: {e}")
        print(json.dumps({"erro": f"Erro inesperado: {e}"}, ensure_ascii=False))

def obter_datas(caminho_arquivo: str):
    """Lê o Excel e retorna as datas separadas por cada documento-plano."""
    leitor = LeitorExcel()
    try:
        # Usa o novo método que filtra apenas dados válidos
        dados_validos = leitor.ler_e_validar_dados_validos(caminho_arquivo)

        if not dados_validos.get("documentos"):
            logger.warning("Nenhum dado válido encontrado na planilha Layout para extrair datas.")
            print(json.dumps({"datas_por_documento": {}}, ensure_ascii=False))
            return
        
        # Retorna apenas as datas por documento
        datas_resposta = {
            "datas_por_documento": dados_validos.get("datas_por_documento", {})
        }
        
        print(json.dumps(datas_resposta, ensure_ascii=False))
        logger.info("Datas por documento enviadas para a UI.")
    except BRServiceError as e:
        logger.error(f"Erro ao obter datas: {e.mensagem}")
        print(json.dumps({"erro": e.mensagem}, ensure_ascii=False))
    except Exception as e:
        logger.critical(f"Erro inesperado ao obter datas: {e}")
        print(json.dumps({"erro": f"Erro inesperado: {e}"}, ensure_ascii=False))

def processar_e_gerar(caminho_arquivo: str, pasta_destino: str, documentos_selecionados=None, datas_selecionadas=None, nome_pasta: str | None = None, progress: bool = False):
    """Processa e gera arquivos com base nas seleções."""
    leitor = LeitorExcel()
    processador = Processador()
    gerador = Gerador()
    validador = Validador()

    try:
        if progress: emit_event("start", msg="Iniciando processamento", progress=0.0)
        validador.validar_pasta_saida(pasta_destino)

        if progress: emit_event("read", msg="Lendo arquivo de entrada", progress=0.10)
        dados_brutos_por_bloco, doc_planos_ui = leitor.ler_planilha_layout(caminho_arquivo)
        if not dados_brutos_por_bloco:
            raise ErroValidacaoDados("Nenhum dado válido encontrado no arquivo de entrada.")
        
        if progress: emit_event("parse", msg="Validando seleções", progress=0.25)

        # Opções disponíveis para validar seleções
        fmt = config_app.obter_config('formato_data_excel')
        # Cria lista de documento-plano a partir das chaves dos dados processados
        documentos_disponiveis = []
        for (doc, plano) in dados_brutos_por_bloco.keys():
            documentos_disponiveis.append(f"{doc}-{plano}")
        documentos_disponiveis = sorted(documentos_disponiveis)
        todas_datas = []
        for df_bloco in dados_brutos_por_bloco.values():
            s = pd.to_datetime(df_bloco["Data Crédito"], errors="coerce", dayfirst=True).dropna().dt.strftime(fmt)
            todas_datas.extend(s.tolist())
        datas_disponiveis = sorted(set(todas_datas))

        if progress: emit_event("validate", msg="Validando seleções", progress=0.35)
        validador.validar_selecoes(
            documentos_disponiveis,
            datas_disponiveis,
            documentos_selecionados or [],
            datas_selecionadas or []
        )

        if progress: emit_event("process", msg="Processando dados", progress=0.55)
        dados_processados_filtrados = processador.processar_dados(
            dados_brutos_por_bloco,
            documentos_selecionados,
            datas_selecionadas
        )

        validador.validar_dados_processados(dados_processados_filtrados)

        
        def _progress_generate_cb(idx: int, total: int, path: str):
            base, top = 0.70, 0.95
            prog = base + (top - base) * (idx / max(1, total))
            emit_event("generate", msg=f"Gerado {Path(path).name}", progress=prog, file=path)

        if progress: emit_event("generate", msg="Iniciando geração", progress=0.70)

        arquivos = gerador.gerar_arquivos_saida(
            dados_processados_filtrados,
            pasta_destino,
            nome_pasta=nome_pasta,
            progress_cb=_progress_generate_cb if progress else None,
        )

        if progress: emit_event("done", msg="Concluído", progress=1.0, files=len(arquivos))
        logger.info("Processamento e geração concluídos.")
        if not progress:
            print(json.dumps({"sucesso": "Arquivos gerados com sucesso!"}, ensure_ascii=False))

    except BRServiceError as e:
        if progress: emit_event("ERROR", msg=e.mensagem or "Erro")
        logger.error(...)
        print(json.dumps({"codigo": e.codigo, "mensagem": e.mensagem, "detalhes": e.detalhes}, ensure_ascii=False))
        sys.exit(1)

    except Exception as e:
        if progress: emit_event("ERROR", msg=str(e))
        logger.critical(...)
        print(json.dumps({"erro": f"Erro inesperado: {e}"}, ensure_ascii=False))
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Sistema BR Service para processamento de arquivos Excel.")
    parser.add_argument("--input", required=True, help="Caminho do Excel de entrada.")
    parser.add_argument("--output", help="Pasta de destino dos arquivos gerados.")
    parser.add_argument("--get-options", action="store_true", help="Mostra documentos/planos/datas disponíveis.")
    parser.add_argument("--get-datas", action="store_true", help="Mostra datas separadas por cada documento-plano.")
    parser.add_argument("--documentos", help="Ex: AZ,REG")
    parser.add_argument("--datas", help="Ex: 05/05/2025,27/05/2025")
    parser.add_argument("--nome-pasta", help="Nome da pasta que será criada para os arquivos gerados")
    parser.add_argument("--progress", action="store_true", help="Emite eventos NDJSON de progresso no stdout")
    parser.add_argument("--quiet", action="store_true", help="Suprime logs no console quando usado com --get-options (logs vão apenas para arquivo)")

    args = parser.parse_args()
    
    # Configura o logger baseado nos argumentos
    global logger
    quiet_mode = args.quiet and (args.get_options or args.get_datas)
    logger = configurar_logger_com_quiet(quiet_mode)
    
    input_path = args.input.strip('"') if args.input else None
    output_path = args.output.strip('"') if args.output else None

    documentos_selecionados = args.documentos.split(",") if args.documentos else None
    datas_selecionadas = args.datas.split(",") if args.datas else None

    # Se o usuário não passar --nome-pasta, usa o nome do arquivo de entrada (sem extensão)
    nome_pasta = args.nome_pasta or Path(args.input).stem

    if args.get_options:
        obter_opcoes(input_path)
    elif args.get_datas:
        obter_datas(input_path)
    else:
        if not output_path:
            print(json.dumps({"erro":"Parâmetro --output é obrigatório para gerar arquivos."}, ensure_ascii=False))
            sys.exit(2)
        processar_e_gerar(input_path, output_path, documentos_selecionados, datas_selecionadas, nome_pasta, progress=args.progress)

if __name__ == "__main__":
    main()
