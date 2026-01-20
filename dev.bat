@echo off
setlocal enabledelayedexpansion

REM ========================================
REM Script de Desenvolvimento - BR Service CLI
REM ========================================
REM
REM Este script fornece opcoes para:
REM 1. Buildar o projeto (gerar executavel .exe)
REM 2. Rodar testes
REM 3. Rodar testes com arquivo real
REM 4. Limpar arquivos de build
REM
REM Uso: dev.bat
REM

:MENU
cls
echo.
echo ========================================
echo   BR SERVICE - MENU DE DESENVOLVIMENTO
echo ========================================
echo.
echo [1] Buildar projeto (gerar .exe)
echo [2] Rodar testes basicos
echo [3] Testar com arquivo real
echo [4] Limpar builds e cache
echo [5] Instalar/Atualizar dependencias
echo [0] Sair
echo.
echo ========================================
echo.

set /p opcao="Escolha uma opcao: "

if "%opcao%"=="1" goto BUILD
if "%opcao%"=="2" goto TEST
if "%opcao%"=="3" goto TEST_REAL
if "%opcao%"=="4" goto CLEAN
if "%opcao%"=="5" goto INSTALL_DEPS
if "%opcao%"=="0" goto EXIT
goto MENU

REM ========================================
REM FUNCAO: Verificar Python
REM ========================================
:CHECK_PYTHON
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado!
    echo Por favor, instale Python 3.x e adicione ao PATH
    pause
    exit /b 1
)
echo [OK] Python encontrado:
python --version
goto :eof

REM ========================================
REM FUNCAO: Ativar ambiente virtual
REM ========================================
:ACTIVATE_VENV
if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Ativando ambiente virtual...
    call .venv\Scripts\activate.bat
) else (
    echo [AVISO] Ambiente virtual nao encontrado
    echo [INFO] Criando ambiente virtual...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    echo [INFO] Instalando dependencias...
    python -m pip install --upgrade pip
    pip install -r requirements.txt
)
goto :eof

REM ========================================
REM OPCAO 1: BUILD
REM ========================================
:BUILD
cls
echo.
echo ========================================
echo   BUILDANDO PROJETO
echo ========================================
echo.

call :CHECK_PYTHON
call :ACTIVATE_VENV

echo.
echo [INFO] Verificando PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo [INFO] PyInstaller nao encontrado. Instalando...
    pip install pyinstaller
)

echo.
echo [INFO] Limpando builds anteriores...
if exist "dist" rmdir /s /q dist
if exist "build" rmdir /s /q build
if exist "*.spec" del /q *.spec

echo.
echo [INFO] Iniciando build...
echo [INFO] Isso pode levar alguns minutos...
echo.

python build.py --name br_service --onefile --console --clean --noconfirm --icon "assets/app_icon.ico"

if errorlevel 1 (
    echo.
    echo [ERRO] Build falhou!
    pause
    goto MENU
)

echo.
echo ========================================
echo   BUILD CONCLUIDO COM SUCESSO!
echo ========================================
echo.

if exist "dist\br_service.exe" (
    echo [OK] Executavel gerado: dist\br_service.exe
    for %%I in (dist\br_service.exe) do (
        set size=%%~zI
        set /a size_mb=!size! / 1048576
        echo [INFO] Tamanho: !size_mb! MB
    )
    echo.
    echo [INFO] Testando executavel...
    dist\br_service.exe --help
)

echo.
pause
goto MENU

REM ========================================
REM OPCAO 2: TESTES BASICOS
REM ========================================
:TEST
cls
echo.
echo ========================================
echo   RODANDO TESTES BASICOS
echo ========================================
echo.

call :CHECK_PYTHON
call :ACTIVATE_VENV

echo.
echo [INFO] Verificando pytest...
python -c "import pytest" >nul 2>&1
if errorlevel 1 (
    echo [INFO] pytest nao encontrado. Instalando...
    pip install pytest
)

echo.
echo [TEST 1] Importacao de modulos
echo ----------------------------------------
python -c "from src.processamento.leitor import LeitorExcel; from src.processamento.processador import Processador; from src.processamento.gerador import Gerador; print('[OK] Todos os modulos importados com sucesso')"
if errorlevel 1 (
    echo [ERRO] Falha na importacao de modulos
    pause
    goto MENU
)

echo.
echo [TEST 2] Validacao de configuracao
echo ----------------------------------------
python -c "from src.config.configuracao import Configuracao; c = Configuracao('config.json'); print('[OK] Configuracao carregada:', c.obter_config('sheet_name'))"
if errorlevel 1 (
    echo [ERRO] Falha ao carregar configuracao
    pause
    goto MENU
)

echo.
echo [TEST 3] Teste de parse de valores
echo ----------------------------------------
python -c "from src.processamento.leitor import _parse_valor; import pandas as pd; v1 = _parse_valor('1.234,56'); v2 = _parse_valor('628.91'); print(f'[OK] Parse BR: {v1}, Parse US: {v2}')"
if errorlevel 1 (
    echo [ERRO] Falha no parse de valores
    pause
    goto MENU
)

echo.
echo [TEST 4] Verificacao de dependencias
echo ----------------------------------------
python -c "import pandas; import openpyxl; import xlsxwriter; print(f'[OK] pandas {pandas.__version__}')"
python -c "import openpyxl; print(f'[OK] openpyxl {openpyxl.__version__}')"
if errorlevel 1 (
    echo [ERRO] Dependencias faltando
    pause
    goto MENU
)

echo.
echo ========================================
echo   TODOS OS TESTES PASSARAM!
echo ========================================
echo.
pause
goto MENU

REM ========================================
REM OPCAO 3: TESTE COM ARQUIVO REAL
REM ========================================
:TEST_REAL
cls
echo.
echo ========================================
echo   TESTE COM ARQUIVO REAL
echo ========================================
echo.

call :CHECK_PYTHON
call :ACTIVATE_VENV

echo.
set /p arquivo_teste="Digite o caminho do arquivo Excel para testar (ou Enter para cancelar): "

if "%arquivo_teste%"=="" (
    echo [INFO] Teste cancelado
    pause
    goto MENU
)

if not exist "%arquivo_teste%" (
    echo [ERRO] Arquivo nao encontrado: %arquivo_teste%
    pause
    goto MENU
)

echo.
echo [INFO] Testando leitura de arquivo...
echo [INFO] Arquivo: %arquivo_teste%
echo.

REM Teste 1: Get Options
echo [TEST 1] Obtendo opcoes do arquivo...
echo ----------------------------------------
python main.py --input "%arquivo_teste%" --get-options --quiet

if errorlevel 1 (
    echo [ERRO] Falha ao obter opcoes
    pause
    goto MENU
)

echo.
echo [OK] Opcoes obtidas com sucesso!
echo.

REM Teste 2: Get Datas
echo [TEST 2] Obtendo datas por documento...
echo ----------------------------------------
python main.py --input "%arquivo_teste%" --get-datas --quiet

if errorlevel 1 (
    echo [ERRO] Falha ao obter datas
    pause
    goto MENU
)

echo.
echo [OK] Datas obtidas com sucesso!
echo.

REM Pergunta se quer processar
set /p processar="Deseja processar e gerar arquivos? (S/N): "
if /i not "%processar%"=="S" goto TEST_REAL_END

set /p pasta_saida="Digite a pasta de saida (ou Enter para usar 'test_output'): "
if "%pasta_saida%"=="" set pasta_saida=test_output

echo.
echo [TEST 3] Processando e gerando arquivos...
echo ----------------------------------------
echo [INFO] Pasta de saida: %pasta_saida%
python main.py --input "%arquivo_teste%" --output "%pasta_saida%"

if errorlevel 1 (
    echo [ERRO] Falha no processamento
    pause
    goto MENU
)

echo.
echo [OK] Arquivos gerados em: %pasta_saida%
echo.

REM Abre a pasta de saida
set /p abrir="Deseja abrir a pasta de saida? (S/N): "
if /i "%abrir%"=="S" start "" "%pasta_saida%"

:TEST_REAL_END
echo.
echo ========================================
echo   TESTE COMPLETO!
echo ========================================
echo.
pause
goto MENU

REM ========================================
REM OPCAO 4: LIMPAR
REM ========================================
:CLEAN
cls
echo.
echo ========================================
echo   LIMPANDO ARQUIVOS
echo ========================================
echo.

echo [INFO] Removendo builds...
if exist "dist" (
    rmdir /s /q dist
    echo [OK] dist/ removido
)
if exist "build" (
    rmdir /s /q build
    echo [OK] build/ removido
)
if exist "*.spec" (
    del /q *.spec
    echo [OK] arquivos .spec removidos
)

echo.
echo [INFO] Removendo cache Python...
for /d /r %%d in (__pycache__) do @if exist "%%d" (
    rmdir /s /q "%%d"
    echo [OK] %%d removido
)

for /d /r %%d in (*.egg-info) do @if exist "%%d" (
    rmdir /s /q "%%d"
    echo [OK] %%d removido
)

echo.
echo [INFO] Removendo arquivos de teste...
if exist "test_output" (
    rmdir /s /q test_output
    echo [OK] test_output/ removido
)

echo.
echo [INFO] Removendo logs antigos...
if exist "logs" (
    for %%f in (logs\*.log) do (
        del /q "%%f"
    )
    echo [OK] Logs limpos
)

echo.
echo ========================================
echo   LIMPEZA CONCLUIDA!
echo ========================================
echo.
pause
goto MENU

REM ========================================
REM OPCAO 5: INSTALAR/ATUALIZAR DEPENDENCIAS
REM ========================================
:INSTALL_DEPS
cls
echo.
echo ========================================
echo   INSTALANDO/ATUALIZANDO DEPENDENCIAS
echo ========================================
echo.

call :CHECK_PYTHON
call :ACTIVATE_VENV

echo.
echo [INFO] Atualizando pip...
python -m pip install --upgrade pip

echo.
echo [INFO] Instalando dependencias do requirements.txt...
pip install -r requirements.txt

echo.
echo [INFO] Dependencias instaladas:
echo ----------------------------------------
pip list | findstr /i "pandas openpyxl pyinstaller pytest xlsxwriter click pydantic"

echo.
echo ========================================
echo   DEPENDENCIAS ATUALIZADAS!
echo ========================================
echo.
pause
goto MENU

REM ========================================
REM SAIR
REM ========================================
:EXIT
cls
echo.
echo ========================================
echo   BR SERVICE - Desenvolvimento
echo ========================================
echo.
echo Ate logo!
echo.
exit /b 0