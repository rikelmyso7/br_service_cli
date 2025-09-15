# BR SERVICE

Sistema Python para **processamento de arquivos Excel**, voltado à extração, transformação e geração de dados financeiros para importação em sistemas externos como o **Sienge**.
Desenvolvido com arquitetura modular, robusta e integrável a uma **UI Flutter** via **Standard I/O**.

## 🚀 Funcionalidades

- **Análise de Arquivos Excel**: leitura inteligente da planilha `Layout`.
- **Extração Dinâmica**: identificação automática de blocos `Contrato | Valor | Data Crédito` e metadados `(Documento, Plano Financeiro)`.
- **Processamento e Normalização**:
  - Conversão segura de formatos numéricos (BR → padrão).
  - Tratamento de datas (`datetime`, `date` ou strings).
  - Filtragem por documentos, planos, datas exatas e intervalos.
- **Geração de Saída Excel**:
  - Arquivos `.xlsx` formatados (datas, números, largura de colunas, cabeçalho fixo).
  - Organização por pasta de documento.
  - Controle de versionamento automático para evitar sobrescrita.
- **Validação Avançada**:
  - Conferência de pastas de saída.
  - Checagem de colunas obrigatórias.
  - Identificação de seleções inválidas (documentos/datas).
- **Configuração Flexível**:
  - Arquivo `config.json` com defaults.
  - Sobrescrita por variáveis de ambiente (`BR_SERVICE_*`).
- **Logs Estruturados**:
  - Console + arquivo (opcionalmente rotativo).
  - Formatação clara com timestamp, módulo e linha.

## 📂 Estrutura do Projeto

```
BR_SERVICE/
├── src/
│   ├── processamento/
│   │   ├── leitor.py        # Leitura e interpretação da planilha Layout
│   │   ├── processador.py   # Filtros e normalização dos dados
│   │   └── gerador.py       # Geração dos arquivos Excel formatados
│   ├── validacao/
│   │   └── validador.py     # Regras de validação e pré-condições
│   ├── config/
│   │   └── configuracao.py  # Gestão de configurações (arquivo/env)
│   └── utils/
│       ├── exceptions.py    # Exceções personalizadas com códigos
│       └── logger.py        # Configuração de logging centralizado
├── config.json              # Parâmetros globais
├── logs/                    # Arquivos de log
├── tests/                   # Testes unitários/integrados
├── build.py                 # Empacotamento (PyInstaller)
├── requirements.txt         # Dependências Python
└── README.md
```

## 🛠️ Descrição dos Módulos

### `src/processamento/`

- **`leitor.py`** – Lê o Excel e divide os dados em blocos por `(Documento, Plano Financeiro)`.
- **`processador.py`** – Aplica filtros de seleção, intervalos de datas e normaliza formatos.
- **`gerador.py`** – Cria arquivos `.xlsx` de saída, formata colunas, congela cabeçalho e organiza pastas.

### `src/validacao/`

- **`validador.py`** – Valida arquivos, pastas, seleções e dados processados.

### `src/config/`

- **`configuracao.py`** – Lê/salva configurações em JSON; expande variáveis de ambiente; permite override via `BR_SERVICE_*`.

### `src/utils/`

- **`exceptions.py`** – Exceções com códigos (`LEITURA_ARQUIVO`, `PROCESSAMENTO_DADOS`, etc.) e suporte a serialização para JSON.
- **`logger.py`** – Logger idempotente com suporte a console e arquivo rotativo.

---

## ⚙️ Configuração

O arquivo `config.json` define parâmetros padrão, ex.:

```json
{
  "diretorio_logs": "logs",
  "nivel_log": "INFO",
  "formato_data_excel": "%d/%m/%Y",
  "colunas_saida": ["Contrato", "Valor", "Emissão", "Vencimento", "Competência"]
}
```

Você pode sobrescrever qualquer chave via variável de ambiente prefixada:

```bash
export BR_SERVICE_NIVEL_LOG=DEBUG
export BR_SERVICE_DIRETORIO_LOGS="/var/log/br_service"
```

---

## 💻 Uso via CLI

Instale as dependências:

```bash
pip install -r requirements.txt
```

### Obter opções de documentos/datas

```bash
python main.py --input caminho/arquivo.xlsx --get-options
```

Saída (JSON):

```json
{
  "documentos": ["AZ", "REG"],
  "planos_por_documento": {
    "AZ": ["1.01.02.01"],
    "REG": ["1.04.01.08"]
  },
  "datas": ["05/05/2025", "27/05/2025"]
}
```

### Processar e gerar arquivos

```bash
python main.py   --input caminho/arquivo.xlsx   --output pasta/saida   --documentos AZ,REG   --datas 05/05/2025,27/05/2025
```

---

## 🧪 Testes

Os testes ficam em `tests/` e cobrem:

- Leitura de arquivos com espaçadores entre blocos.
- Filtros por datas em diferentes formatos.
- Geração de arquivos `.xlsx` e validação de colunas/formatos.

Execute:

```bash
pytest
```
