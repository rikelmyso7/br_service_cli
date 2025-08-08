#!/usr/bin/env python3
"""
Testes básicos para o sistema BR_SERVICE
"""

import unittest
import os
import sys
import tempfile
import shutil
import pandas as pd

# Adiciona o diretório pai ao path para importar os módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.processamento.leitor import ler_dados_layout, obter_opcoes
from src.processamento.processador import processar_dados
from src.processamento.gerador import gerar_arquivos_saida

class TestSistema(unittest.TestCase):
    
    def setUp(self):
        """Configuração inicial para os testes"""
        self.arquivo_teste = "../upload/Itau_CRI_Rivello_2025-05.xlsx"
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Limpeza após os testes"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_obter_opcoes(self):
        """Testa a obtenção de opções do arquivo"""
        opcoes = obter_opcoes(self.arquivo_teste)
        
        self.assertIn('documentos', opcoes)
        self.assertIn('datas', opcoes)
        self.assertIn('combinacoes', opcoes)
        
        # Verifica se há documentos e datas
        self.assertGreater(len(opcoes['documentos']), 0)
        self.assertGreater(len(opcoes['datas']), 0)
        
        # Verifica se AZ está nos documentos (baseado na análise anterior)
        self.assertIn('AZ', opcoes['documentos'])
    
    def test_ler_dados_layout(self):
        """Testa a leitura dos dados da planilha Layout"""
        df_dados, documentos_planos = ler_dados_layout(self.arquivo_teste)
        
        self.assertIsNotNone(df_dados)
        self.assertIsNotNone(documentos_planos)
        
        # Verifica se o DataFrame tem as colunas esperadas
        colunas_esperadas = ['Contrato', 'Valor', 'Data Crédito', 'Documento', 'Plano Financeiro']
        for coluna in colunas_esperadas:
            self.assertIn(coluna, df_dados.columns)
        
        # Verifica se há dados
        self.assertGreater(len(df_dados), 0)
        self.assertGreater(len(documentos_planos), 0)
    
    def test_processar_dados(self):
        """Testa o processamento dos dados"""
        df_dados, _ = ler_dados_layout(self.arquivo_teste)
        
        # Testa processamento sem filtros
        df_processado = processar_dados(df_dados)
        
        # Verifica se as colunas de data foram adicionadas
        colunas_esperadas = ['Emissão', 'Vencimento', 'Competência']
        for coluna in colunas_esperadas:
            self.assertIn(coluna, df_processado.columns)
        
        # Testa processamento com filtros
        df_filtrado = processar_dados(df_dados, documentos_selecionados=['AZ'])
        
        # Verifica se apenas documentos AZ foram mantidos
        documentos_unicos = df_filtrado['Documento'].unique()
        self.assertEqual(len(documentos_unicos), 1)
        self.assertEqual(documentos_unicos[0], 'AZ')
    
    def test_gerar_arquivos_saida(self):
        """Testa a geração de arquivos de saída"""
        df_dados, _ = ler_dados_layout(self.arquivo_teste)
        df_processado = processar_dados(df_dados, documentos_selecionados=['AZ'])
        
        arquivos_gerados = gerar_arquivos_saida(df_processado, self.temp_dir)
        
        # Verifica se pelo menos um arquivo foi gerado
        self.assertGreater(len(arquivos_gerados), 0)
        
        # Verifica se o arquivo existe
        for arquivo in arquivos_gerados:
            self.assertTrue(os.path.exists(arquivo))
            
            # Verifica se o arquivo tem conteúdo válido
            df_arquivo = pd.read_excel(arquivo)
            colunas_esperadas = ['Contrato', 'Valor', 'Emissão', 'Vencimento', 'Competência']
            for coluna in colunas_esperadas:
                self.assertIn(coluna, df_arquivo.columns)

if __name__ == '__main__':
    unittest.main()

