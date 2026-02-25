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
| `--input` | string | **(Obrigatório, exceto em `--daemon`)** Caminho do arquivo Excel de entrada |
| `--output` | string | Pasta de destino dos arquivos gerados |
| `--get-options` | flag | Retorna documentos, planos e datas disponíveis (JSON) |
| `--get-all` | flag | Retorna todos os dados de análise em uma única chamada — combina `get-options` + `get-datas` + `get-contas` |
| `--get-preview` | flag | Retorna cabeçalhos e linhas da planilha Layout para preview (JSON) |
| `--get-datas` | flag | Retorna datas separadas por documento-plano (JSON) |
| `--get-contas` | flag | Analisa e retorna contas ativas/inativas (JSON) |
| `--daemon` | flag | Inicia em modo daemon: lê comandos JSON de stdin e responde em stdout (elimina cold start) |
| `--documentos` | string | Filtro de documentos (separados por vírgula) |
| `--datas` | string | Filtro de datas no formato DD/MM/AAAA (separadas por vírgula) |
| `--nome-pasta` | string | Nome personalizado para pasta de saída |
| `--progress` | flag | Emite eventos NDJSON de progresso no stdout |
| `--quiet` | flag | Suprime logs no console (apenas arquivo) |
| `--conta` | int | Atualiza o número da conta na planilha Layout |

### Exemplos

**Obter todos os dados em uma única chamada (recomendado):**
```bash
br_service_cli.exe --input planilha.xlsx --get-all --quiet
```

Retorna JSON com documentos, planos, datas, contas e contagens:
```json
{
  "documentos": ["AZ-1.01.02.01", "REG-1.04.01.08"],
  "planos_por_documento": {"AZ-1.01.02.01": ["1.01.02.01"]},
  "datas": ["05/05/2025", "27/05/2025"],
  "datas_por_documento": {"AZ-1.01.02.01": ["05/05/2025"]},
  "block_counts": {},
  "contas_ativas": {},
  "contas_inativas": {}
}
```

**Obter preview da planilha para exibição:**
```bash
br_service_cli.exe --input planilha.xlsx --get-preview --quiet
```

Retorna JSON com cabeçalhos e linhas:
```json
{
  "headers": ["Contrato", "Valor", "Data Crédito"],
  "rows": [["ABC123", "1500.00", "05/05/2025"]]
}
```

**Modo daemon (elimina cold start — usado pela UI):**
```bash
br_service_cli.exe --daemon
```

Protocolo stdin/stdout (NDJSON, uma linha por mensagem):
```json
→ stdin:  {"cmd": "get-all", "input": "C:\\planilha.xlsx"}
← stdout: {"documentos": [...], "planos_por_documento": {...}, ...}

→ stdin:  {"cmd": "get-preview", "input": "C:\\planilha.xlsx"}
← stdout: {"headers": [...], "rows": [[...]]}
```

Comandos suportados no daemon: `get-all`, `get-preview`, `get-options`, `get-datas`, `get-contas`.

**Gerar arquivos com filtros:**
```bash
br_service_cli.exe --input planilha.xlsx --output ./saida --documentos AZ-1.01.02.01 --datas 05/05/2025
```

**Gerar todos os arquivos com progresso:**
```bash
br_service_cli.exe --input planilha.xlsx --output ./saida --progress
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
br_service_cli.exe --input planilha.xlsx --conta 12345
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
python build.py --name br_service --onefile --console --clean --noconfirm --icon "assets/app_icon.ico"
```

O executável será criado na pasta `dist/` como `br_service.exe`.

> **Nota:** Após gerar o executável, copie `dist/br_service.exe` para `lib/assets/br_service_cli.exe` no projeto Flutter antes de compilar a UI.

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

## Observações sobre OneDrive

O comando `--conta` usa automação COM do Excel (xlwings) para atualizar a célula B1 da aba Layout. Em arquivos localizados em pastas sincronizadas pelo **OneDrive**, o Excel COM pode interceptar a operação de save e exibir um diálogo interativo, travando o processo.

A implementação atual resolve isso com uma estratégia **copy-modify-replace**: o arquivo é copiado para `%TEMP%`, modificado lá, e depois copiado de volta para o destino original via `shutil.copy2` — sem envolver o COM do Excel no save final.

## Changelog

Veja o histórico completo de alterações em [docs/CHANGELOG.md](docs/CHANGELOG.md).

## Licença

Projeto proprietário - Todos os direitos reservados.
