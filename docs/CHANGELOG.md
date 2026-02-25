# Changelog — BR Service CLI

## [Unreleased]

### Corrigido

#### `Processador.atualizar_conta` — Falha COM/RPC em arquivos no OneDrive (`processador.py`)
- **Problema:** O método usava `wb.save()` via xlwings/COM para salvar o arquivo após atualizar a conta. Em arquivos localizados em pastas sincronizadas pelo OneDrive (`C:\Users\...\OneDrive\...`), o Excel COM interceptava a operação de save e exibia um diálogo interativo "Salvar como", bloqueando o processo por ~30 segundos até falhar com:
  ```
  (-2147023174, 'O servidor RPC não está disponível.')   # RPC_S_SERVER_UNAVAILABLE
  (-2147023170, 'Falha na chamada de procedimento remoto.')  # RPC_S_CALL_FAILED
  ```
- **Causa raiz:** O OneDrive intercepta operações COM de save em arquivos sincronizados. Caminhos com caracteres especiais (ex: `Área de Trabalho`) agravam o problema na interface COM.
- **Tentativa intermediária:** Substituir `wb.save()` por `wb.api.SaveAs(Filename=..., FileFormat=51)` + `wb.api.Close(SaveChanges=False)` — reduziu o problema mas não resolveu para todos os caminhos OneDrive.
- **Correção final:** Estratégia copy-modify-replace:
  1. Copia o arquivo original para um path temporário em `%TEMP%` (sem acentos, fora do OneDrive) via `shutil.copy2`
  2. Abre e modifica o arquivo temporário via xlwings/COM
  3. Salva com `wb.save()` no path temporário (sem interferência do OneDrive)
  4. Copia o arquivo temporário modificado de volta para o destino original via `shutil.copy2`
  5. Remove o arquivo temporário no bloco `finally`
- **Resultado:** Operação funciona corretamente em qualquer path, incluindo OneDrive, caminhos com acentos e caminhos UNC.

---

### Adicionado

#### Testes unitários — Python (`tests/`)
- **`test_gerador_extra.py`** (21 testes): cobre `_datetime_to_excel_serial` — valores relativos entre datas sequenciais, fração de dia (hora 12h = 0.5), ajuste do bug de 1900, tipo de retorno `float`; e `gerar_arquivos_csv` — extensão `.csv`, separador `;`, encoding UTF-8, formato de data `DD/MM/YYYY`, colunas derivadas de `Data Crédito`, valor com 2 casas decimais, estrutura de pastas, versionamento, bloco vazio ignorado, callback de progresso, contagem de linhas.
- **`test_atualizar_conta.py`** (14 testes): cobre `atualizar_conta` com mocks de `xw.App`, `shutil.copy2` e `os.remove` — fluxo copy→modify→replace, arquivo temp removido no `finally` mesmo em caso de exceção, `xw.App(visible=False)`, `wb.save()` + `wb.close()` chamados, valor escrito em B1; testes de integração real (pulados automaticamente se Excel COM não disponível no ambiente).
