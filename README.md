# BR Service CLI

Sistema Python para processamento de arquivos Excel financeiros, focado na extração, transformação e geração de dados para importação em sistemas externos (como Sienge). Projetado para comunicação com interface gráfica Flutter via Standard I/O.

## Funcionalidades

- **Leitura de Arquivos Excel**: Interpretação automática da planilha 'Layout' com detecção flexível de colunas
- **Extração de Dados**: Identificação de 'Contrato', 'Valor', 'Data Crédito' e metadados (Documento, Plano)
- **Processamento**: Normalização de valores numéricos (formato BR/US) e datas
- **Geração de Arquivos**: Criação de arquivos .xls formatados por documento/plano
- **Gerenciamento de Contas**: Atualização e análise de contas na planilha
- **Comunicação JSON**: Interface via stdout para integração com UI Flutter
- **Eventos de Progresso**: Emissão de eventos NDJSON para acompanhamento em tempo real

## Estrutura do Projeto

```
br_service_cli/
├── main.py                 # Ponto de entrada CLI
├── config.json             # Configurações da aplicação
├── requirements.txt        # Dependências Python
├── build.py                # Script para gerar executável
├── src/
│   ├── processamento/
│   │   ├── leitor.py       # Leitura e parsing de Excel
│   │   ├── processador.py  # Filtros e transformações
│   │   └── gerador.py      # Geração de arquivos de saída
│   ├── validacao/
│   │   └── validador.py    # Validação de dados e pastas
│   ├── config/
│   │   └── configuracao.py # Gerenciamento de configurações
│   └── utils/
│       ├── exceptions.py   # Exceções personalizadas
│       └── logger.py       # Sistema de logging
├── logs/                   # Arquivos de log
└── tests/                  # Testes unitários
```

## Instalação

### Pré-requisitos

- Python 3.10+
- pip (gerenciador de pacotes)

### Dependências

```bash
pip install -r requirements.txt
```

**Principais dependências:**
- `pandas` - Manipulação de dados
- `openpyxl` - Leitura de arquivos .xlsx
- `xlwt` - Geração de arquivos .xls
- `xlwings` - Automação Excel (atualização de contas)
- `platformdirs` - Diretórios de configuração multiplataforma

## Uso

### Argumentos da CLI

| Argumento | Tipo | Descrição |
|-----------|------|-----------|
| `--input` | string | **(Obrigatório)** Caminho do arquivo Excel de entrada |
| `--output` | string | Pasta de destino dos arquivos gerados |
| `--get-options` | flag | Retorna documentos, planos e datas disponíveis (JSON) |
| `--get-datas` | flag | Retorna datas separadas por documento-plano (JSON) |
| `--documentos` | string | Filtro de documentos (separados por vírgula) |
| `--datas` | string | Filtro de datas no formato DD/MM/AAAA (separadas por vírgula) |
| `--nome-pasta` | string | Nome personalizado para pasta de saída |
| `--progress` | flag | Emite eventos NDJSON de progresso no stdout |
| `--quiet` | flag | Suprime logs no console (apenas arquivo) |
| `--conta` | int | Atualiza o número da conta na planilha Layout |
| `--get-contas` | flag | Analisa e retorna contas ativas/inativas (JSON) |

### Exemplos

**Obter opções disponíveis:**
```bash
python main.py --input planilha.xlsx --get-options --quiet
```

Retorna JSON:
```json
{
  "documentos": ["AZ-1.01.02.01", "REG-1.04.01.08"],
  "planos_por_documento": {"AZ-1.01.02.01": ["1.01.02.01"]},
  "datas": ["05/05/2025", "27/05/2025"]
}
```

**Gerar arquivos com filtros:**
```bash
python main.py --input planilha.xlsx --output ./saida --documentos AZ-1.01.02.01 --datas 05/05/2025
```

**Gerar todos os arquivos com progresso:**
```bash
python main.py --input planilha.xlsx --output ./saida --progress
```

Emite eventos NDJSON:
```json
{"event": "start", "msg": "Iniciando processamento", "progress": 0.0}
{"event": "read", "msg": "Lendo arquivo de entrada", "progress": 0.1}
{"event": "generate", "msg": "Gerado AZ-1.01.02.01.xls", "progress": 0.75, "file": "..."}
{"event": "done", "msg": "Concluído", "progress": 1.0, "files": 6}
```

**Atualizar conta na planilha:**
```bash
python main.py --input planilha.xlsx --conta 12345
```

**Analisar contas disponíveis:**
```bash
python main.py --input planilha.xlsx --get-contas
```

## Configuração

O arquivo `config.json` permite personalizar o comportamento:

```json
{
  "diretorio_logs": "logs",
  "nivel_log": "INFO",
  "formato_data_excel": "%d/%m/%Y",
  "colunas_saida": ["Contrato", "Valor", "Data de Emissão", "Data de Vencimento", "Data de Competência"]
}
```

| Configuração | Descrição | Padrão |
|--------------|-----------|--------|
| `diretorio_logs` | Pasta para arquivos de log | `logs` |
| `nivel_log` | Nível de logging (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `formato_data_excel` | Formato de data para exibição | `%d/%m/%Y` |
| `colunas_saida` | Colunas incluídas nos arquivos gerados | ver acima |

**Variáveis de ambiente:** Configurações podem ser sobrescritas com prefixo `BR_SERVICE_`:
```bash
export BR_SERVICE_NIVEL_LOG=DEBUG
```

## Formato de Entrada

O sistema espera um arquivo Excel com planilha "Layout" contendo:

1. **Cabeçalho** com colunas: `Contrato`, `Valor`, `Data Crédito` (ou variações)
2. **Metadados** nas linhas acima do cabeçalho: `Documento` e `Plano Financeiro`
3. **Múltiplos blocos** horizontais (cada bloco = 3 colunas)

Variações aceitas para nomes de colunas:
- Contrato: `contrato`, `contract`
- Valor: `valor`, `value`, `montante`
- Data Crédito: `data credito`, `dt credito`, `data`, `date`

## Formato de Saída

Arquivos `.xls` gerados com estrutura:

| Contrato | Valor | Data de Emissão | Data de Vencimento | Data de Competência |
|----------|-------|-----------------|--------------------|--------------------|
| ABC123   | 1500.00 | 05/05/2025 | 05/05/2025 | 05/05/2025 |

- Organizados em pastas por documento ou nome personalizado
- Versionamento automático se arquivo já existir (ex: `AZ-1.01.02.01-v2.xls`)

## Build

Para gerar executável standalone:

```bash
python build.py
```

O executável será criado na pasta `dist/`.

## Tratamento de Erros

O sistema retorna erros em formato JSON:

```json
{"erro": "Arquivo de entrada não encontrado: arquivo.xlsx"}
```

```json
{"codigo": "VALIDATION_ERROR", "mensagem": "Documentos inválidos: XYZ", "detalhes": null}
```

Códigos de saída:
- `0` - Sucesso
- `1` - Erro de processamento
- `2` - Erro de argumentos

## Logs

Logs são salvos em `logs/br_service_<pid>.log` com formato:
```
2025-05-05 10:30:00 | INFO | br_service | main:99 | Opções enviadas para a UI
```

## Licença

Projeto proprietário - Todos os direitos reservados.
