# BR SERVICE

Este projeto implementa um sistema para processamento de dados financeiros de arquivos Excel, com foco na geração de arquivos de importação para o Sienge.

## Arquitetura do Sistema

A arquitetura do sistema é modular, dividida em componentes com responsabilidades específicas:

```
BR_SERVICE/
├── src/
│   ├── processamento/       # Módulos para leitura, processamento e geração de dados
│   │   ├── leitor.py        # Responsável pela leitura do arquivo Excel e extração de dados da planilha 'Layout'
│   │   ├── processador.py   # Responsável pelo processamento e transformação dos dados extraídos
│   │   └── gerador.py       # Responsável pela geração dos arquivos de saída no formato Excel
│   ├── validacao/           # Módulos para validação de dados
│   │   └── validador.py     # Contém funções para validar colunas, formatos de data e valores numéricos
│   ├── config/              # Módulos de configuração
│   │   └── configuracao.py  # Pode ser usado para armazenar configurações globais do sistema
│   └── utils/               # Utilitários gerais
│       ├── exceptions.py    # Definições de exceções personalizadas para o sistema
│       └── logger.py        # Configuração e funções para registro de logs
├── config.json              # Arquivo de configuração (atualmente não utilizado, mas pode ser expandido)
├── logs/                    # Diretório para armazenar arquivos de log
├── tests/                   # Diretório para testes unitários e de integração
├── build.py                 # Script para empacotamento da aplicação (ex: com PyInstaller)
├── requirements.txt         # Lista de dependências Python do projeto
└── README.md                # Documentação do projeto
```

## Fluxo de Trabalho

O sistema opera através de um fluxo de trabalho que interage com uma interface gráfica (Flutter Desktop):

1.  **Seleção de Arquivo de Entrada**: O usuário seleciona um arquivo Excel contendo os dados financeiros.
2.  **Extração de Opções**: O sistema Python lê o arquivo e extrai opções de 'Documentos' e 'Datas de Crédito' disponíveis, enviando-as para a interface gráfica em formato JSON.
3.  **Seleção do Usuário**: A interface gráfica exibe as opções, permitindo ao usuário selecionar quais documentos e datas devem ser processados. O usuário também define a pasta de destino.
4.  **Processamento de Dados**: As seleções do usuário são enviadas de volta ao Python. O sistema filtra e processa os dados da planilha 'Layout', aplicando formatação numérica e replicando datas para as colunas 'Emissão', 'Vencimento' e 'Competência'.
5.  **Geração de Arquivos de Saída**: Para cada combinação de 'Documento' e 'Plano Financeiro' (ou para o arquivo inteiro, dependendo da granularidade da extração), um novo arquivo Excel é gerado na pasta de destino especificada, seguindo a nomenclatura `Documento-PlanoFinanceiro.xls`.
6.  **Validação e Logs**: O sistema realiza validações durante o processo e registra quaisquer erros ou avisos em arquivos de log, que podem ser exibidos ao usuário.

## Regras de Negócio Principais

-   **Leitura de Dados**: Foco na planilha 'Layout' de arquivos Excel. Colunas como 'Contrato', 'Valor' e 'Data Crédito' são identificadas dinamicamente.
-   **Extração de Metadados**: 'Documento' e 'Plano Financeiro' são extraídos para nomeação dos arquivos de saída.
-   **Filtragem**: Os dados podem ser filtrados por 'Documento' e 'Data de Crédito' selecionados pelo usuário.
-   **Formatação Numérica**: Valores numéricos são formatados com ponto como separador decimal e duas casas decimais.
-   **Formatação de Datas**: Datas são formatadas como 'DD/MM/AAAA'.
-   **Colunas de Saída**: Os arquivos gerados contêm as colunas 'Contrato', 'Valor', 'Emissão', 'Vencimento' e 'Competência'. As três últimas replicam o valor da 'Data Crédito'.
-   **Comunicação UI-Python**: Realizada via Standard I/O (entrada/saída padrão) usando JSON para troca de opções e argumentos de linha de comando para seleções.
-   **Tratamento de Erros**: O sistema lida com colunas ausentes, formatos inválidos e seleções vazias, fornecendo mensagens de erro amigáveis.

## Dependências

As dependências Python necessárias estão listadas no `requirements.txt`:

-   `pandas`: Para manipulação e análise de dados.
-   `openpyxl`: Backend para leitura de arquivos `.xlsx` pelo pandas.
-   `xlsxwriter`: Backend para escrita de arquivos `.xlsx` pelo pandas.

## Como Executar (Exemplo)

Para obter as opções de documentos e datas:

```bash
python main.py --input "caminho/para/seu/arquivo.xlsx" --output "caminho/para/pasta/destino" --get-options
```

Para processar dados com seleções específicas:

```bash
python main.py --input "caminho/para/seu/arquivo.xlsx" --output "caminho/para/pasta/destino" --documentos "AZ,REG" --datas "05/05/2025,27/05/2025"
```

## Considerações de Desempenho

O sistema é projetado para processar arquivos Excel grandes de forma eficiente, minimizando o uso de memória e o tempo de processamento, utilizando bibliotecas otimizadas como Pandas.


