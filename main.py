import argparse
import json
import os
import sys
from datetime import datetime
import pandas as pd

from src.processamento.leitor import ler_dados_layout, obter_opcoes
from src.processamento.processador import processar_dados
from src.processamento.gerador import gerar_arquivos_saida
from src.validacao.validador import ValidadorDados, JSONResponseBuilder, StatusProcessamento
from src.utils.exceptions import (
    ArquivoNaoEncontradoError, 
    PlanilhaNaoEncontradaError, 
    ColunaNaoEncontradaError,
    DadosVaziosError,
    ProcessamentoError,
    ValidacaoError
)
from src.utils.logger import get_logger, get_user_logger

# Configurar loggers
logger = get_logger()
user_logger = get_user_logger()
validador = ValidadorDados()

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        return super().default(obj)

def main():
    parser = argparse.ArgumentParser(description="Processamento de dados financeiros para importação no Sienge.")
    parser.add_argument("--input", required=True, help="Caminho para o arquivo Excel de entrada.")
    parser.add_argument("--output", help="Pasta de destino para os arquivos gerados.")
    parser.add_argument("--get-options", action="store_true", help="Retorna opções de documentos e datas em JSON.")
    parser.add_argument("--documentos", help="Documentos selecionados, separados por vírgula.")
    parser.add_argument("--data-inicio", help="Data de início para filtro (DD/MM/AAAA).")
    parser.add_argument("--data-fim", help="Data de fim para filtro (DD/MM/AAAA).")
    parser.add_argument("--extract-only", action="store_true", help="Extrai os dados e retorna em JSON sem gerar arquivos.")

    args = parser.parse_args()

    input_file = args.input
    output_dir = args.output

    response_builder = JSONResponseBuilder()
    response_builder.set_etapa("Inicialização")

    try:
        # Validação inicial do arquivo de entrada
        user_logger.progress_user("Validando arquivo de entrada...")
        arquivo_valido, mensagens_arquivo = validador.validar_arquivo_entrada(input_file)
        for msg in mensagens_arquivo:
            if "❌" in msg:
                user_logger.error_user(msg)
            elif "⚠️" in msg:
                user_logger.warning_user(msg)
            else:
                user_logger.info_user(msg)

        if not arquivo_valido:
            response_builder.set_status(StatusProcessamento.ERRO)
            response_builder.add_erro(f"Arquivo de entrada inválido: {input_file}")
            print(json.dumps(response_builder.build()))
            sys.exit(1)

        if args.get_options:
            response_builder.set_etapa("Obtenção de Opções")
            opcoes = obter_opcoes(input_file)
            response_builder.set_status(StatusProcessamento.CONCLUIDO)
            response_builder.add_dados("opcoes", opcoes)
            response_builder.add_sucesso("Opções de documentos e datas retornadas com sucesso.")
            print(json.dumps(response_builder.build()))

        else:
            # Validação e criação da pasta de destino
            if not args.extract_only and not output_dir:
                response_builder.set_status(StatusProcessamento.ERRO)
                response_builder.add_erro("A pasta de destino é obrigatória para o processamento.")
                print(json.dumps(response_builder.build()))
                sys.exit(1)

            if output_dir:
                user_logger.progress_user("Validando pasta de destino...")
                pasta_valida, mensagens_pasta = validador.validar_selecao_usuario([], None, None, output_dir)
                for msg in mensagens_pasta:
                    if "❌" in msg:
                        user_logger.error_user(msg)
                    elif "⚠️" in msg:
                        user_logger.warning_user(msg)
                    else:
                        user_logger.info_user(msg)
                
                if not pasta_valida:
                    response_builder.set_status(StatusProcessamento.ERRO)
                    response_builder.add_erro(f"Pasta de destino inválida ou não pôde ser criada: {output_dir}")
                    print(json.dumps(response_builder.build()))
                    sys.exit(1)
            response_builder.set_etapa("Processamento de Dados")
            documentos_selecionados = args.documentos.split(",") if args.documentos else []
            
            data_inicio = None
            if args.data_inicio:
                try:
                    data_inicio = datetime.strptime(args.data_inicio, "%d/%m/%Y")
                except ValueError:
                    user_logger.error_user(f"Formato de data de início inválido: {args.data_inicio}. Use DD/MM/AAAA.")
                    raise ValidacaoError("Data de Início", "Formato inválido")

            data_fim = None
            if args.data_fim:
                try:
                    data_fim = datetime.strptime(args.data_fim, "%d/%m/%Y")
                except ValueError:
                    user_logger.error_user(f"Formato de data de fim inválido: {args.data_fim}. Use DD/MM/AAAA.")
                    raise ValidacaoError("Data de Fim", "Formato inválido")

            df_dados, documentos_planos = ler_dados_layout(input_file)

            dados_processados = processar_dados(df_dados, documentos_selecionados, data_inicio, data_fim)

            if args.extract_only:
                response_builder.set_etapa("Extração de Dados")
                response_builder.set_status(StatusProcessamento.CONCLUIDO)
                # Converter DataFrames para um formato serializável em JSON
                dados_serializaveis = {
                    chave: df.to_dict(orient='records') 
                    for chave, df in dados_processados.items()
                }
                response_builder.add_dados("dados_extraidos", dados_serializaveis)
                response_builder.add_sucesso("Dados extraídos com sucesso.")
                print(json.dumps(response_builder.build(), indent=4, cls=CustomJSONEncoder))
            else:
                arquivos_gerados = gerar_arquivos_saida(dados_processados, output_dir)
                
                response_builder.set_etapa("Finalização")
                if arquivos_gerados:
                    response_builder.set_status(StatusProcessamento.CONCLUIDO)
                    response_builder.add_sucesso(f"Processamento concluído com sucesso! {len(arquivos_gerados)} arquivo(s) gerado(s).")
                    response_builder.add_dados("arquivos_gerados", arquivos_gerados)
                else:
                    response_builder.set_status(StatusProcessamento.AVISO)
                    response_builder.add_aviso("Nenhum arquivo foi gerado.")
                
                print(json.dumps(response_builder.build()))

    except (ArquivoNaoEncontradoError, PlanilhaNaoEncontradaError, ColunaNaoEncontradaError, DadosVaziosError, ProcessamentoError, ValidacaoError) as e:
        response_builder.set_status(StatusProcessamento.ERRO)
        response_builder.add_erro(f"Erro no processamento: {e.message}")
        logger.error(f"Erro específico: {e.__class__.__name__} - {e.message}")
        print(json.dumps(response_builder.build()))
        sys.exit(1)
    except Exception as e:
        response_builder.set_status(StatusProcessamento.ERRO)
        response_builder.add_erro(f"Erro inesperado: {str(e)}")
        logger.critical(f"Erro inesperado e crítico: {str(e)}", exc_info=True)
        print(json.dumps(response_builder.build()))
        sys.exit(1)


if __name__ == "__main__":
    main()


