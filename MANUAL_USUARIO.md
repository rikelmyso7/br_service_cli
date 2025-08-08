# Manual do Usuário - BR SERVICE

## Visão Geral

O BR SERVICE é um sistema para processamento de dados financeiros de arquivos Excel, desenvolvido para gerar arquivos de importação compatíveis com o sistema Sienge. O sistema extrai dados da planilha "Layout" e gera arquivos Excel organizados por documento e plano financeiro.

## Funcionalidades Principais

- **Leitura Automática**: Analisa arquivos Excel e identifica automaticamente documentos e planos financeiros
- **Filtragem Flexível**: Permite selecionar documentos específicos e datas para processamento
- **Geração Múltipla**: Cria arquivos separados para cada combinação documento-plano financeiro
- **Validação de Dados**: Verifica a integridade dos dados antes do processamento
- **Logs Detalhados**: Registra todas as operações para auditoria e depuração

## Requisitos do Sistema

### Dependências Python
- Python 3.7 ou superior
- pandas
- openpyxl
- xlsxwriter
- xlrd

### Estrutura do Arquivo de Entrada
O arquivo Excel deve conter:
- Planilha chamada "Layout"
- Colunas "Contrato", "Valor" e "Data Crédito"
- Campos "Documento" e "Plano Financeiro" acima das colunas de dados

## Como Usar

### 1. Obter Opções Disponíveis

Para visualizar quais documentos e datas estão disponíveis no arquivo:

```bash
python main.py --input "caminho/arquivo.xlsx" --output "pasta_destino" --get-options
```

**Saída esperada:**
```json
{
  "documentos": ["AZ", "ADTC", "REG", "EO", "COND", "TX", "TTT"],
  "datas": ["01/05/2025", "02/05/2025", "03/05/2025", ...],
  "combinacoes": ["AZ-1.01.02.01", "ADTC-1.04.01.07", ...]
}
```

### 2. Processar Dados com Filtros

Para processar apenas documentos e datas específicos:

```bash
python main.py --input "arquivo.xlsx" --output "pasta_destino" --documentos "AZ,REG" --datas "05/05/2025,27/05/2025"
```

### 3. Processar Todos os Dados

Para processar todos os dados disponíveis:

```bash
python main.py --input "arquivo.xlsx" --output "pasta_destino"
```

## Parâmetros de Linha de Comando

| Parâmetro | Obrigatório | Descrição |
|-----------|-------------|-----------|
| `--input` | Sim | Caminho para o arquivo Excel de entrada |
| `--output` | Sim | Pasta onde os arquivos serão gerados |
| `--get-options` | Não | Retorna opções disponíveis em JSON |
| `--documentos` | Não | Lista de documentos separados por vírgula |
| `--datas` | Não | Lista de datas (DD/MM/AAAA) separadas por vírgula |

## Formato dos Arquivos de Saída

Os arquivos gerados seguem o padrão `Documento-PlanoFinanceiro.xls` e contêm as seguintes colunas:

| Coluna | Descrição |
|--------|-----------|
| Contrato | Código do contrato |
| Valor | Valor monetário (formato decimal com ponto) |
| Emissão | Data de emissão (DD/MM/AAAA) |
| Vencimento | Data de vencimento (DD/MM/AAAA) |
| Competência | Data de competência (DD/MM/AAAA) |

**Nota:** As colunas Emissão, Vencimento e Competência sempre replicam o valor da "Data Crédito" original.

## Códigos de Retorno

O sistema retorna mensagens em formato JSON indicando o status da operação:

### Sucesso
```json
{
  "status": "success",
  "message": "Processamento concluído com sucesso! 3 arquivo(s) gerado(s).",
  "arquivos": ["./output/AZ-1.01.02.01.xls", "./output/REG-1.04.01.08.xls"]
}
```

### Aviso
```json
{
  "status": "warning",
  "message": "Nenhum dado encontrado para os critérios de seleção fornecidos."
}
```

### Erro
```json
{
  "status": "error",
  "message": "Arquivo de entrada não encontrado: arquivo.xlsx"
}
```

## Solução de Problemas

### Erro: "Planilha 'Layout' não encontrada"
- Verifique se o arquivo Excel contém uma planilha chamada exatamente "Layout"

### Erro: "Colunas necessárias não encontradas"
- Confirme se a planilha Layout contém as colunas "Contrato", "Valor" e "Data Crédito"

### Erro: "Não foi possível encontrar 'Documento' e 'Plano Financeiro'"
- Verifique se os campos Documento e Plano Financeiro estão presentes acima das colunas de dados

### Nenhum arquivo gerado
- Confirme se há dados válidos para os filtros aplicados
- Verifique se as datas estão no formato correto (DD/MM/AAAA)

## Logs

O sistema gera logs detalhados em `logs/app.log` para auditoria e depuração. Os logs incluem:
- Operações realizadas
- Erros encontrados
- Arquivos gerados
- Filtros aplicados

## Integração com Flutter

O sistema foi projetado para integração com uma interface Flutter Desktop através de:
- Comunicação via Standard I/O
- Troca de dados em formato JSON
- Argumentos de linha de comando para seleções do usuário

### Fluxo de Integração
1. Flutter chama `--get-options` para obter opções
2. Usuário seleciona documentos e datas na interface
3. Flutter chama o processamento com os filtros selecionados
4. Sistema retorna status e lista de arquivos gerados

