
"""
main.py

Ponto de entrada principal para o sistema BR Service.
Orquestra a leitura, processamento, validação e geração de arquivos Excel.
Lida com argumentos de linha de comando e comunicação via Standard I/O.
"""

import argparse, json, logging, os, sys
from pathlib import Path
import pandas as pd
import xlwings as xw
from shutil import copyfile

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

# Nome do logger usado em todo o módulo - configurado em main()
LOGGER_NAME = "br_service"

def get_logger():
    """Retorna o logger do módulo. Mais testável que variável global."""
    return logging.getLogger(LOGGER_NAME)

def configurar_logger_com_quiet(quiet_mode: bool):
    """Configura o logger baseado no modo quiet."""
    from src.utils.logger import configurar_logger

    if quiet_mode:
        # Em modo quiet, redireciona console logs para stderr e reduz nível
        logger_instance = logging.getLogger(LOGGER_NAME)
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
            get_logger().warning("Nenhum dado válido encontrado na planilha Layout para extrair opções.")
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
        get_logger().info("Opções com dados válidos enviadas para a UI.")
    except BRServiceError as e:
        get_logger().error(f"Erro ao obter opções: {e.mensagem}")
        print(json.dumps({"erro": e.mensagem}, ensure_ascii=False))
    except (IOError, OSError, PermissionError) as e:
        get_logger().error(f"Erro de I/O ao obter opções: {e}")
        print(json.dumps({"erro": f"Erro de acesso ao arquivo: {e}"}, ensure_ascii=False))
    except Exception as e:
        get_logger().critical(f"Erro inesperado ao obter opções: {e}")
        print(json.dumps({"erro": f"Erro inesperado: {e}"}, ensure_ascii=False))

def obter_datas(caminho_arquivo: str):
    """Lê o Excel e retorna as datas separadas por cada documento-plano."""
    leitor = LeitorExcel()
    try:
        # Usa o novo método que filtra apenas dados válidos
        dados_validos = leitor.ler_e_validar_dados_validos(caminho_arquivo)

        if not dados_validos.get("documentos"):
            get_logger().warning("Nenhum dado válido encontrado na planilha Layout para extrair datas.")
            print(json.dumps({"datas_por_documento": {}}, ensure_ascii=False))
            return

        # Retorna apenas as datas por documento
        datas_resposta = {
            "datas_por_documento": dados_validos.get("datas_por_documento", {})
        }

        print(json.dumps(datas_resposta, ensure_ascii=False))
        get_logger().info("Datas por documento enviadas para a UI.")
    except BRServiceError as e:
        get_logger().error(f"Erro ao obter datas: {e.mensagem}")
        print(json.dumps({"erro": e.mensagem}, ensure_ascii=False))
    except (IOError, OSError, PermissionError) as e:
        get_logger().error(f"Erro de I/O ao obter datas: {e}")
        print(json.dumps({"erro": f"Erro de acesso ao arquivo: {e}"}, ensure_ascii=False))
    except Exception as e:
        get_logger().critical(f"Erro inesperado ao obter datas: {e}")
        print(json.dumps({"erro": f"Erro inesperado: {e}"}, ensure_ascii=False))


def obter_todos_dados(caminho_arquivo: str):
    """
    Retorna todos os dados de análise em uma única chamada.
    Combina: get-options + get-datas + get-contas
    Reduz overhead de múltiplas chamadas ao CLI.
    """
    leitor = LeitorExcel()
    processador = Processador()

    resultado = {
        "documentos": [],
        "planos_por_documento": {},
        "datas": [],
        "datas_por_documento": {},
        "block_counts": {},
        "colunas_obrigatorias": {
            "todas_presentes": False,
            "presentes": [],
            "ausentes": []
        },
        "contas_ativas": {},
        "contas_inativas": {},
    }

    try:
        # 1. Obtém dados válidos (documentos, planos, datas)
        get_logger().info("Obtendo dados válidos do arquivo...")
        dados_validos = leitor.ler_e_validar_dados_validos(caminho_arquivo)

        if dados_validos.get("documentos"):
            resultado["documentos"] = dados_validos["documentos"]
            resultado["planos_por_documento"] = dados_validos["planos_por_documento"]
            resultado["datas"] = dados_validos["datas"]
            resultado["datas_por_documento"] = dados_validos.get("datas_por_documento", {})
            resultado["block_counts"] = dados_validos.get("block_counts", {})
            resultado["colunas_obrigatorias"] = dados_validos.get("colunas_obrigatorias", resultado["colunas_obrigatorias"])

        # 2. Obtém análise de contas
        get_logger().info("Analisando contas...")
        try:
            contas_json = processador.analisar_contas(caminho_arquivo)
            contas_data = json.loads(contas_json)
            resultado["contas_ativas"] = contas_data.get("contas_ativas", {})
            resultado["contas_inativas"] = contas_data.get("contas_inativas", {})
        except Exception as e:
            get_logger().warning(f"Erro ao analisar contas (não crítico): {e}")
            # Continua mesmo se falhar a análise de contas

        print(json.dumps(resultado, ensure_ascii=False))
        get_logger().info("Todos os dados enviados para a UI via --get-all.")

    except BRServiceError as e:
        get_logger().error(f"Erro ao obter todos os dados: {e.mensagem}")
        print(json.dumps({"erro": e.mensagem}, ensure_ascii=False))
        sys.exit(1)
    except (IOError, OSError, PermissionError) as e:
        get_logger().error(f"Erro de I/O ao obter todos os dados: {e}")
        print(json.dumps({"erro": f"Erro de acesso ao arquivo: {e}"}, ensure_ascii=False))
        sys.exit(1)
    except Exception as e:
        get_logger().critical(f"Erro inesperado ao obter todos os dados: {e}")
        print(json.dumps({"erro": f"Erro inesperado: {e}"}, ensure_ascii=False))
        sys.exit(1)

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
        # OTIMIZAÇÃO: Loop único para extrair documentos e datas (ao invés de dois loops separados)
        # Nota: Data Crédito já é datetime (convertido em leitor.py), evita reconversão
        documentos_disponiveis = []
        todas_datas = []
        for (doc, plano), df_bloco in dados_brutos_por_bloco.items():
            documentos_disponiveis.append(f"{doc}-{plano}")
            # Usa diretamente .dt pois a coluna já é datetime
            datas_bloco = df_bloco["Data Crédito"].dropna()
            if not datas_bloco.empty:
                todas_datas.extend(datas_bloco.dt.strftime(fmt).tolist())
        documentos_disponiveis = sorted(documentos_disponiveis)
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
        get_logger().info("Processamento e geração concluídos.")
        if not progress:
            print(json.dumps({"sucesso": "Arquivos gerados com sucesso!"}, ensure_ascii=False))

    except BRServiceError as e:
        if progress: emit_event("ERROR", msg=e.mensagem or "Erro")
        get_logger().error(f"Erro ao processar: {e.mensagem}")
        print(json.dumps({"codigo": e.codigo, "mensagem": e.mensagem, "detalhes": e.detalhes}, ensure_ascii=False))
        sys.exit(1)

    except Exception as e:
        if progress: emit_event("ERROR", msg=str(e))
        get_logger().critical(f"Erro inesperado: {e}")
        print(json.dumps({"erro": f"Erro inesperado: {e}"}, ensure_ascii=False))
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Sistema BR Service para processamento de arquivos Excel.")
    parser.add_argument("--input", required=True, help="Caminho do Excel de entrada.")
    parser.add_argument("--output", help="Pasta de destino dos arquivos gerados.")
    parser.add_argument("--get-options", action="store_true", help="Mostra documentos/planos/datas disponíveis.")
    parser.add_argument("--get-datas", action="store_true", help="Mostra datas separadas por cada documento-plano.")
    parser.add_argument("--get-all", action="store_true", help="Retorna todos os dados de análise em uma única chamada (combina get-options + get-datas + get-contas).")
    parser.add_argument("--documentos", help="Ex: AZ,REG")
    parser.add_argument("--datas", help="Ex: 05/05/2025,27/05/2025")
    parser.add_argument("--nome-pasta", help="Nome da pasta que será criada para os arquivos gerados")
    parser.add_argument("--progress", action="store_true", help="Emite eventos NDJSON de progresso no stdout")
    parser.add_argument("--quiet", action="store_true", help="Suprime logs no console quando usado com --get-options (logs vão apenas para arquivo)")
    parser.add_argument("--conta", type=int, help="Atualiza a conta na planilha Layout")
    parser.add_argument("--get-contas", action="store_true", help="Analisa contas e retorna JSON com contas ativas e inativas")

    args = parser.parse_args()

    # Configura o logger baseado nos argumentos
    quiet_mode = args.quiet and (args.get_options or args.get_datas or args.get_all)
    configurar_logger_com_quiet(quiet_mode)
    
    input_path = args.input.strip('"') if args.input else None
    output_path = args.output.strip('"') if args.output else None

    # Validação do arquivo de entrada
    if input_path:
        input_file = Path(input_path)
        if not input_file.exists():
            get_logger().error(f"Arquivo de entrada não encontrado: {input_path}")
            print(json.dumps({"erro": f"Arquivo de entrada não encontrado: {input_path}"}, ensure_ascii=False))
            sys.exit(1)
        if not input_file.is_file():
            get_logger().error(f"O caminho informado não é um arquivo: {input_path}")
            print(json.dumps({"erro": f"O caminho informado não é um arquivo: {input_path}"}, ensure_ascii=False))
            sys.exit(1)
        if not input_file.suffix.lower() in ('.xlsx', '.xls', '.xlsm'):
            get_logger().warning(f"Extensão de arquivo não reconhecida: {input_file.suffix}")

    # Validação do argumento --conta
    if args.conta is not None and args.conta <= 0:
        get_logger().error(f"O valor de --conta deve ser um número positivo, recebido: {args.conta}")
        print(json.dumps({"erro": f"O valor de --conta deve ser um número positivo, recebido: {args.conta}"}, ensure_ascii=False))
        sys.exit(1)

    documentos_selecionados = args.documentos.split(",") if args.documentos else None
    datas_selecionadas = args.datas.split(",") if args.datas else None

    # Se o usuário não passar --nome-pasta, usa o nome do arquivo de entrada (sem extensão)
    nome_pasta = args.nome_pasta or Path(args.input).stem

    if args.get_all:
        obter_todos_dados(input_path)
    elif args.get_options:
        obter_opcoes(input_path)
    elif args.get_datas:
        obter_datas(input_path)
    elif args.conta:
        try:
            processador = Processador()
            processador.atualizar_conta(input_path, args.conta)
            print(json.dumps({"sucesso": f"Conta atualizada para {args.conta}"}, ensure_ascii=False))
        except BRServiceError as e:
            get_logger().error(f"Erro ao atualizar conta: {e.mensagem}")
            print(json.dumps({"erro": e.mensagem}, ensure_ascii=False))
            sys.exit(1)
        except (IOError, OSError, PermissionError) as e:
            get_logger().error(f"Erro de I/O ao atualizar conta: {e}")
            print(json.dumps({"erro": f"Erro de acesso ao arquivo: {e}"}, ensure_ascii=False))
            sys.exit(1)
        except Exception as e:
            get_logger().critical(f"Erro inesperado ao atualizar conta: {e}")
            print(json.dumps({"erro": f"Erro inesperado: {e}"}, ensure_ascii=False))
            sys.exit(1)
    elif args.get_contas:
        try:
            processador = Processador()
            result = processador.analisar_contas(input_path)
            print(result)
        except BRServiceError as e:
            get_logger().error(f"Erro ao analisar contas: {e.mensagem}")
            print(json.dumps({"erro": e.mensagem}, ensure_ascii=False))
            sys.exit(1)
        except (IOError, OSError, PermissionError) as e:
            get_logger().error(f"Erro de I/O ao analisar contas: {e}")
            print(json.dumps({"erro": f"Erro de acesso ao arquivo: {e}"}, ensure_ascii=False))
            sys.exit(1)
        except Exception as e:
            get_logger().critical(f"Erro inesperado ao analisar contas: {e}")
            print(json.dumps({"erro": f"Erro inesperado: {e}"}, ensure_ascii=False))
            sys.exit(1)
    else:
        if not output_path:
            print(json.dumps({"erro":"Parâmetro --output é obrigatório para gerar arquivos."}, ensure_ascii=False))
            sys.exit(2)
        processar_e_gerar(input_path, output_path, documentos_selecionados, datas_selecionadas, nome_pasta, progress=args.progress)

if __name__ == "__main__":
    main()
