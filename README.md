# BR SERVICE

Este projeto implementa um sistema Python para processamento de arquivos Excel, focado na extração, transformação e geração de dados financeiros para importação em sistemas externos, como o Sienge. A aplicação é projetada para ser modular, robusta e se comunicar com uma interface gráfica desenvolvida em Flutter.

## Funcionalidades Principais

- **Análise de Arquivos Excel**: Leitura e interpretação de planilhas financeiras, com foco na planilha 'Layout'.
- **Extração Dinâmica de Dados**: Identificação flexível de colunas chave ('Contrato', 'Valor', 'Data Crédito') e metadados ('Documento', 'Plano Financeiro').
- **Processamento e Normalização**: Tratamento de valores numéricos e datas para garantir consistência e formatação adequada.
- **Geração de Arquivos de Saída**: Criação de arquivos Excel (.xls) formatados para importação, com base em seleções do usuário.
- **Comunicação com UI (Flutter)**: Interface via Standard I/O para troca de opções e parâmetros.
- **Tratamento de Erros e Logs**: Mecanismos robustos para validação de dados e registro de eventos.

## Estrutura do Projeto

A arquitetura do projeto segue um design modular, onde cada componente possui responsabilidades bem definidas, promovendo a manutenibilidade e escalabilidade do sistema.

```
BR_SERVICE/
├── src/
│   ├── processamento/
│   │   ├── leitor.py
│   │   ├── processador.py
│   │   └── gerador.py
│   ├── validacao/
│   │   └── validador.py
│   ├── config/
│   │   └── configuracao.py
│   └── utils/
│       ├── exceptions.py
│       └── logger.py
├── config.json
├── logs/
├── tests/
├── build.py
├── requirements.txt
└── README.md
```

### Descrição dos Módulos:

- **`src/processamento/`**:
    - `leitor.py`: Responsável pela leitura e interpretação inicial dos arquivos Excel. Identifica a estrutura da planilha 'Layout', extrai os cabeçalhos e os metadados (Documento e Plano Financeiro).
    - `processador.py`: Realiza a transformação e limpeza dos dados extraídos. Inclui a normalização de valores numéricos, formatação de datas e filtragem de dados com base nas seleções do usuário.
    - `gerador.py`: Encarregado da criação dos arquivos de saída (.xls). Formata os dados processados de acordo com o layout de importação e organiza os arquivos nas pastas de destino.

- **`src/validacao/`**:
    - `validador.py`: Contém as regras de validação para os dados de entrada e saída. Garante a consistência dos dados e identifica possíveis inconsistências ou erros.

- **`src/config/`**:
    - `configuracao.py`: Gerencia as configurações da aplicação, como caminhos de arquivos, formatos padrão e outras definições que podem ser parametrizadas.

- **`src/utils/`**:
    - `exceptions.py`: Define exceções personalizadas para o tratamento de erros específicos da aplicação, proporcionando mensagens de erro claras e informativas.
    - `logger.py`: Implementa um sistema de log centralizado para registrar eventos, avisos e erros, facilitando a depuração e o monitoramento da aplicação.

- **`config.json`**: Arquivo de configuração em formato JSON para parâmetros globais da aplicação.
- **`logs/`**: Diretório para armazenar os arquivos de log gerados pela aplicação.
- **`tests/`**: Diretório para os testes unitários e de integração do sistema.
- **`build.py`**: Script para empacotar a aplicação Python em um executável (usando PyInstaller).
- **`requirements.txt`**: Lista de dependências Python necessárias para o projeto.

## Como Usar

(Instruções detalhadas serão adicionadas após a implementação completa do sistema.)

## Desenvolvimento

### Pré-requisitos

- Python 3.x
- `pip` (gerenciador de pacotes Python)

### Instalação de Dependências

```bash
pip install -r requirements.txt
```

### Execução

O sistema será executado via linha de comando, comunicando-se com a UI Flutter. Exemplos de comandos:

- **Obter opções de documentos e datas:**
  ```bash
  python main.py --input <caminho_arquivo.xlsx> --output <pasta_destino> --get-options
  ```

- **Processar seleções e gerar arquivos:**
  ```bash
  python main.py --input <caminho_arquivo.xlsx> --output <pasta_destino> --documentos AZ,REG --datas 05/05/2025,27/05/2025
  ```

## Testes

(Instruções para execução dos testes serão adicionadas.)

## Contribuição

(Diretrizes para contribuição serão adicionadas.)

## Licença

(Informações sobre a licença serão adicionadas.)


