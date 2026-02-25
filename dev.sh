#!/bin/bash

# ========================================
# Script de Desenvolvimento - BR Service CLI
# ========================================
#
# Este script fornece opcoes para:
# 1. Buildar o projeto (gerar executavel)
# 2. Rodar testes
# 3. Rodar testes com arquivo real
# 4. Limpar arquivos de build
#
# Uso: ./dev.sh
#

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ========================================
# FUNCAO: Mostrar Menu
# ========================================
show_menu() {
    clear
    echo ""
    echo "========================================"
    echo "  BR SERVICE - MENU DE DESENVOLVIMENTO"
    echo "========================================"
    echo ""
    echo "[1] Buildar projeto (gerar executavel)"
    echo "[2] Rodar testes (pytest + cobertura)"
    echo "[3] Testar com arquivo real"
    echo "[4] Limpar builds e cache"
    echo "[5] Instalar/Atualizar dependencias"
    echo "[0] Sair"
    echo ""
    echo "========================================"
    echo ""
}

# ========================================
# FUNCAO: Verificar Python
# ========================================
check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}[ERRO]${NC} Python3 nao encontrado!"
        echo "Por favor, instale Python 3.x"
        exit 1
    fi
    echo -e "${GREEN}[OK]${NC} Python encontrado:"
    python3 --version
}

# ========================================
# FUNCAO: Ativar ambiente virtual
# ========================================
activate_venv() {
    if [ -f ".venv/bin/activate" ]; then
        echo -e "${BLUE}[INFO]${NC} Ativando ambiente virtual..."
        source .venv/bin/activate
    else
        echo -e "${YELLOW}[AVISO]${NC} Ambiente virtual nao encontrado"
        echo -e "${BLUE}[INFO]${NC} Criando ambiente virtual..."
        python3 -m venv .venv
        source .venv/bin/activate
        echo -e "${BLUE}[INFO]${NC} Instalando dependencias..."
        python3 -m pip install --upgrade pip
        pip install -r requirements.txt
    fi
}

# ========================================
# OPCAO 1: BUILD
# ========================================
build_project() {
    clear
    echo ""
    echo "========================================"
    echo "  BUILDANDO PROJETO"
    echo "========================================"
    echo ""

    check_python
    activate_venv

    echo ""
    echo -e "${BLUE}[INFO]${NC} Verificando PyInstaller..."
    if ! python3 -c "import PyInstaller" &> /dev/null; then
        echo -e "${BLUE}[INFO]${NC} PyInstaller nao encontrado. Instalando..."
        pip install pyinstaller
    fi

    echo ""
    echo -e "${BLUE}[INFO]${NC} Limpando builds anteriores..."
    rm -rf dist build *.spec

    echo ""
    echo -e "${BLUE}[INFO]${NC} Iniciando build..."
    echo -e "${BLUE}[INFO]${NC} Isso pode levar alguns minutos..."
    echo ""

    python3 build.py --name br_service --onefile --console --clean --noconfirm --icon "assets/app_icon.ico"

    if [ $? -ne 0 ]; then
        echo ""
        echo -e "${RED}[ERRO]${NC} Build falhou!"
        read -p "Pressione Enter para continuar..."
        return
    fi

    echo ""
    echo "========================================"
    echo "  BUILD CONCLUIDO COM SUCESSO!"
    echo "========================================"
    echo ""

    if [ -f "dist/br_service" ]; then
        echo -e "${GREEN}[OK]${NC} Executavel gerado: dist/br_service"
        size=$(du -h dist/br_service | cut -f1)
        echo -e "${BLUE}[INFO]${NC} Tamanho: $size"
        echo ""
        echo -e "${BLUE}[INFO]${NC} Testando executavel..."
        ./dist/br_service --help
    fi

    echo ""
    read -p "Pressione Enter para continuar..."
}

# ========================================
# OPCAO 2: TESTES (pytest + cobertura)
# ========================================
run_tests() {
    clear
    echo ""
    echo "========================================"
    echo "  RODANDO TESTES (pytest + cobertura)"
    echo "========================================"
    echo ""

    check_python
    activate_venv

    echo ""
    echo -e "${BLUE}[INFO]${NC} Verificando pytest e pytest-cov..."
    if ! python3 -c "import pytest" &> /dev/null; then
        echo -e "${BLUE}[INFO]${NC} pytest nao encontrado. Instalando..."
        pip install pytest pytest-cov
    fi
    if ! python3 -c "import pytest_cov" &> /dev/null; then
        echo -e "${BLUE}[INFO]${NC} pytest-cov nao encontrado. Instalando..."
        pip install pytest-cov
    fi

    echo ""
    echo -e "${BLUE}[INFO]${NC} Verificando xlrd (necessario para testes do gerador)..."
    if ! python3 -c "import xlrd" &> /dev/null; then
        echo -e "${BLUE}[INFO]${NC} xlrd nao encontrado. Instalando..."
        pip install xlrd
    fi

    echo ""
    echo -e "${BLUE}[INFO]${NC} Escolha o grupo de testes:"
    echo "  [a] Todos (unitarios + integracao daemon)"
    echo "  [u] Apenas unitarios (leitor, processador, validador, gerador)"
    echo "  [d] Apenas integracao daemon/CLI (requer arquivo real)"
    echo ""
    read -p "Grupo [a/u/d] (Enter = unitarios): " grupo

    echo ""
    case "$grupo" in
        d)
            echo -e "${BLUE}[INFO]${NC} Rodando testes de integracao daemon/CLI..."
            python3 -m pytest tests/test_daemon_protocol.py -v --tb=short -s
            ;;
        a)
            echo -e "${BLUE}[INFO]${NC} Rodando todos os testes com cobertura..."
            python3 -m pytest tests/ \
                -v --tb=short \
                --cov=src --cov-report=term-missing --cov-report=html:htmlcov
            ;;
        *)
            echo -e "${BLUE}[INFO]${NC} Rodando testes unitarios com cobertura..."
            python3 -m pytest \
                tests/test_leitor.py \
                tests/test_processador.py \
                tests/test_validador.py \
                tests/test_gerador.py \
                -v --tb=short \
                --cov=src --cov-report=term-missing --cov-report=html:htmlcov
            ;;
    esac

    EXIT_CODE=$?

    if [ $EXIT_CODE -ne 0 ]; then
        echo ""
        echo -e "${YELLOW}[AVISO]${NC} Alguns testes falharam. Verifique o output acima."
    else
        echo ""
        echo "========================================"
        echo -e "  ${GREEN}TODOS OS TESTES PASSARAM!${NC}"
        echo "========================================"
    fi

    echo ""
    if [ -f "htmlcov/index.html" ]; then
        echo -e "${BLUE}[INFO]${NC} Relatorio HTML gerado em: htmlcov/index.html"
        read -p "Abrir relatorio de cobertura? (S/N): " abrir_cov
        if [[ "$abrir_cov" =~ ^[Ss]$ ]]; then
            if command -v xdg-open &> /dev/null; then
                xdg-open htmlcov/index.html
            elif command -v open &> /dev/null; then
                open htmlcov/index.html
            fi
        fi
    fi

    echo ""
    read -p "Pressione Enter para continuar..."
}

# ========================================
# OPCAO 3: TESTE COM ARQUIVO REAL
# ========================================
test_real_file() {
    clear
    echo ""
    echo "========================================"
    echo "  TESTE COM ARQUIVO REAL"
    echo "========================================"
    echo ""

    check_python
    activate_venv

    echo ""
    read -p "Digite o caminho do arquivo Excel para testar (ou Enter para cancelar): " arquivo_teste

    if [ -z "$arquivo_teste" ]; then
        echo -e "${BLUE}[INFO]${NC} Teste cancelado"
        read -p "Pressione Enter para continuar..."
        return
    fi

    if [ ! -f "$arquivo_teste" ]; then
        echo -e "${RED}[ERRO]${NC} Arquivo nao encontrado: $arquivo_teste"
        read -p "Pressione Enter para continuar..."
        return
    fi

    echo ""
    echo -e "${BLUE}[INFO]${NC} Testando leitura de arquivo..."
    echo -e "${BLUE}[INFO]${NC} Arquivo: $arquivo_teste"
    echo ""

    # Teste 1: Get Options
    echo -e "${BLUE}[TEST 1]${NC} Obtendo opcoes do arquivo..."
    echo "----------------------------------------"
    python3 main.py --input "$arquivo_teste" --get-options --quiet

    if [ $? -ne 0 ]; then
        echo -e "${RED}[ERRO]${NC} Falha ao obter opcoes"
        read -p "Pressione Enter para continuar..."
        return
    fi

    echo ""
    echo -e "${GREEN}[OK]${NC} Opcoes obtidas com sucesso!"
    echo ""

    # Teste 2: Get Datas
    echo -e "${BLUE}[TEST 2]${NC} Obtendo datas por documento..."
    echo "----------------------------------------"
    python3 main.py --input "$arquivo_teste" --get-datas --quiet

    if [ $? -ne 0 ]; then
        echo -e "${RED}[ERRO]${NC} Falha ao obter datas"
        read -p "Pressione Enter para continuar..."
        return
    fi

    echo ""
    echo -e "${GREEN}[OK]${NC} Datas obtidas com sucesso!"
    echo ""

    # Pergunta se quer processar
    read -p "Deseja processar e gerar arquivos? (S/N): " processar
    if [[ ! "$processar" =~ ^[Ss]$ ]]; then
        read -p "Pressione Enter para continuar..."
        return
    fi

    read -p "Digite a pasta de saida (ou Enter para usar 'test_output'): " pasta_saida
    if [ -z "$pasta_saida" ]; then
        pasta_saida="test_output"
    fi

    echo ""
    echo -e "${BLUE}[TEST 3]${NC} Processando e gerando arquivos..."
    echo "----------------------------------------"
    echo -e "${BLUE}[INFO]${NC} Pasta de saida: $pasta_saida"
    python3 main.py --input "$arquivo_teste" --output "$pasta_saida"

    if [ $? -ne 0 ]; then
        echo -e "${RED}[ERRO]${NC} Falha no processamento"
        read -p "Pressione Enter para continuar..."
        return
    fi

    echo ""
    echo -e "${GREEN}[OK]${NC} Arquivos gerados em: $pasta_saida"
    echo ""

    # Abre a pasta de saida
    read -p "Deseja abrir a pasta de saida? (S/N): " abrir
    if [[ "$abrir" =~ ^[Ss]$ ]]; then
        if command -v xdg-open &> /dev/null; then
            xdg-open "$pasta_saida"
        elif command -v open &> /dev/null; then
            open "$pasta_saida"
        else
            echo -e "${YELLOW}[AVISO]${NC} Nao foi possivel abrir a pasta automaticamente"
        fi
    fi

    echo ""
    echo "========================================"
    echo "  TESTE COMPLETO!"
    echo "========================================"
    echo ""
    read -p "Pressione Enter para continuar..."
}

# ========================================
# OPCAO 4: LIMPAR
# ========================================
clean_files() {
    clear
    echo ""
    echo "========================================"
    echo "  LIMPANDO ARQUIVOS"
    echo "========================================"
    echo ""

    echo -e "${BLUE}[INFO]${NC} Removendo builds..."
    rm -rf dist build *.spec
    echo -e "${GREEN}[OK]${NC} Builds removidos"

    echo ""
    echo -e "${BLUE}[INFO]${NC} Removendo cache Python..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null
    find . -type f -name "*.pyc" -delete 2>/dev/null
    echo -e "${GREEN}[OK]${NC} Cache Python removido"

    echo ""
    echo -e "${BLUE}[INFO]${NC} Removendo arquivos de teste..."
    rm -rf test_output
    echo -e "${GREEN}[OK]${NC} test_output/ removido"

    echo ""
    echo -e "${BLUE}[INFO]${NC} Removendo logs antigos..."
    if [ -d "logs" ]; then
        rm -f logs/*.log
        echo -e "${GREEN}[OK]${NC} Logs limpos"
    fi

    echo ""
    echo "========================================"
    echo "  LIMPEZA CONCLUIDA!"
    echo "========================================"
    echo ""
    read -p "Pressione Enter para continuar..."
}

# ========================================
# OPCAO 5: INSTALAR/ATUALIZAR DEPENDENCIAS
# ========================================
install_deps() {
    clear
    echo ""
    echo "========================================"
    echo "  INSTALANDO/ATUALIZANDO DEPENDENCIAS"
    echo "========================================"
    echo ""

    check_python
    activate_venv

    echo ""
    echo -e "${BLUE}[INFO]${NC} Atualizando pip..."
    python3 -m pip install --upgrade pip

    echo ""
    echo -e "${BLUE}[INFO]${NC} Instalando dependencias do requirements.txt..."
    pip install -r requirements.txt

    echo ""
    echo -e "${BLUE}[INFO]${NC} Dependencias instaladas:"
    echo "----------------------------------------"
    pip list | grep -E "(pandas|openpyxl|pyinstaller|pytest|xlsxwriter|click|pydantic)"

    echo ""
    echo "========================================"
    echo "  DEPENDENCIAS ATUALIZADAS!"
    echo "========================================"
    echo ""
    read -p "Pressione Enter para continuar..."
}

# ========================================
# LOOP PRINCIPAL
# ========================================
main() {
    while true; do
        show_menu
        read -p "Escolha uma opcao: " opcao

        case $opcao in
            1)
                build_project
                ;;
            2)
                run_tests
                ;;
            3)
                test_real_file
                ;;
            4)
                clean_files
                ;;
            5)
                install_deps
                ;;
            0)
                clear
                echo ""
                echo "========================================"
                echo "  BR SERVICE - Desenvolvimento"
                echo "========================================"
                echo ""
                echo "Ate logo!"
                echo ""
                exit 0
                ;;
            *)
                echo -e "${RED}[ERRO]${NC} Opcao invalida!"
                sleep 2
                ;;
        esac
    done
}

# Executa o script
main