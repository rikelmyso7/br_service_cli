# Guia de Uso: Filtros por Documento-Plano Financeiro

Este guia explica como usar os filtros aprimorados do BR Service CLI que agora suportam filtros por **documento-Plano Financeiro** em vez de apenas documento.

## 📋 Resumo da Correção

**Problema anterior:** O filtro considerava apenas o documento (ex: "AZ", "ADTC"), causando conflitos quando havia múltiplos documentos com a mesma sigla mas planos diferentes.

**Solução atual:** O filtro agora usa a combinação **"documento-Plano Financeiro"** (ex: "AZ-1.01.02.01", "ADTC-1.04.01.07"), permitindo distinção precisa entre documentos similares.

## 🚀 Como Usar

### 1. Consultar Opções Disponíveis

```bash
python main.py --input "arquivo.xlsx" --get-options
```

**Exemplo de saída:**
```json
{
  "documentos": [
    "ADTC-1.04.01.07",
    "ADTC-2.01.09.15", 
    "AZ-1.01.02.01",
    "EO-2.01.09.13",
    "REG-1.04.01.08",
    "TX-2.01.09.20"
  ],
  "planos_por_documento": {
    "AZ-1.01.02.01": ["1.01.02.01"],
    "ADTC-1.04.01.07": ["1.04.01.07"],
    "ADTC-2.01.09.15": ["2.01.09.15"],
    ...
  },
  "datas": ["02/05/2025", "05/05/2025", ...]
}
```

### 2. Filtrar por Documento-Plano Específico

```bash
python main.py \
  --input "arquivo.xlsx" \
  --output "./saida" \
  --documentos "AZ-1.01.02.01" \
  --datas "05/05/2025"
```

### 3. Filtrar Múltiplos Documentos-Plano

```bash
python main.py \
  --input "arquivo.xlsx" \
  --output "./saida" \
  --documentos "AZ-1.01.02.01,ADTC-1.04.01.07,REG-1.04.01.08" \
  --datas "05/05/2025,06/05/2025"
```

### 4. Distinguir Documentos com Mesma Sigla

**Cenário:** Você tem dois documentos ADTC diferentes:
- `ADTC-1.04.01.07` (Plano: 1.04.01.07)
- `ADTC-2.01.09.15` (Plano: 2.01.09.15)

```bash
# Processar apenas o primeiro ADTC
python main.py \
  --input "arquivo.xlsx" \
  --output "./saida" \
  --documentos "ADTC-1.04.01.07"

# Processar apenas o segundo ADTC  
python main.py \
  --input "arquivo.xlsx" \
  --output "./saida" \
  --documentos "ADTC-2.01.09.15"

# Processar ambos os ADTCs
python main.py \
  --input "arquivo.xlsx" \
  --output "./saida" \
  --documentos "ADTC-1.04.01.07,ADTC-2.01.09.15"
```

## 📊 Exemplos Práticos

### Exemplo 1: Arquivo com Múltiplos Documentos

**Input Excel contém:**
- AZ-1.01.02.01 (386 contratos)
- ADTC-1.04.01.07 (106 contratos) 
- ADTC-2.01.09.15 (2 contratos)
- REG-1.04.01.08 (123 contratos)
- EO-2.01.09.13 (44 contratos)
- TX-2.01.09.20 (7 contratos)

**Comando:**
```bash
python main.py \
  --input "Itau_CRI_Rivello_2025-05.xlsx" \
  --output "./output" \
  --documentos "AZ-1.01.02.01,ADTC-1.04.01.07" \
  --datas "05/05/2025"
```

**Output:**
```
✅ Arquivos gerados:
- ./output/Itau_CRI_Rivello_2025-05/AZ-1.01.02.01.xlsx
- ./output/Itau_CRI_Rivello_2025-05/ADTC-1.04.01.07.xlsx
```

### Exemplo 2: Filtro por Data Específica

**Comando:**
```bash
python main.py \
  --input "arquivo.xlsx" \
  --output "./output" \
  --documentos "REG-1.04.01.08" \
  --datas "05/05/2025,06/05/2025,07/05/2025"
```

**Output:** Apenas contratos do documento REG com plano 1.04.01.08 nas datas especificadas.

### Exemplo 3: Processar Todos os Documentos

**Comando (sem filtros):**
```bash
python main.py \
  --input "arquivo.xlsx" \
  --output "./output"
```

**Output:** Todos os documentos-plano disponíveis serão processados.

## 🔍 Logs e Validação

### Logs do Sistema
```
INFO | Bloco AZ-1.01.02.01 possui 386 contratos válidos.
INFO | Bloco ADTC-1.04.01.07 possui 106 contratos válidos.  
INFO | Bloco ADTC-2.01.09.15 possui 2 contratos válidos.
INFO | Processador gerou 2 blocos após filtros.
```

### Validação de Entrada
O sistema agora valida:
- ✅ Documento-plano existe no arquivo
- ✅ Datas existem no arquivo  
- ✅ Combinação documento-plano + data tem dados válidos

**Exemplo de erro:**
```json
{"erro": "Documentos inválidos: AZ-1.01.02.99"}
```

## 📝 Notas Importantes

1. **Formato do Filtro:** Use sempre `Documento-PlanoFinanceiro` (ex: "AZ-1.01.02.01")
2. **Separador:** Use vírgula para múltiplos valores
3. **Case Sensitive:** Os nomes são sensíveis a maiúsculas/minúsculas
4. **Validação:** O sistema valida se o documento-plano existe antes de processar

## 🆚 Comparação: Antes vs Depois

### Antes (Problema)
```bash
# Filtrava por documento apenas - causava ambiguidade
--documentos "ADTC"  # ❌ Qual ADTC? 1.04.01.07 ou 2.01.09.15?
```

### Depois (Solução)
```bash  
# Filtra por documento-plano específico - sem ambiguidade
--documentos "ADTC-1.04.01.07"  # ✅ Especifica exatamente qual ADTC
--documentos "ADTC-2.01.09.15"  # ✅ Especifica o outro ADTC
```

## ⚡ Performance

- **Leitura:** ~1.5s para arquivos grandes
- **Processamento:** Filtros reduzem significativamente o tempo de processamento
- **Geração:** Apenas documentos-plano selecionados são processados

---

**Versão:** Atualizada em Agosto 2025  
**Compatibilidade:** BR Service CLI v3+