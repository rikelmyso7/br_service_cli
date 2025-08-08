#!/usr/bin/env python3
"""
Script para empacotamento da aplicação BR_SERVICE usando PyInstaller
"""

import os
import subprocess
import sys

def build_executable():
    """Constrói o executável usando PyInstaller"""
    
    # Verifica se PyInstaller está instalado
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller não encontrado. Instalando...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Comando PyInstaller
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name=br_service",
        "--add-data=src:src",
        "--hidden-import=pandas",
        "--hidden-import=openpyxl",
        "--hidden-import=xlsxwriter",
        "--hidden-import=xlrd",
        "main.py"
    ]
    
    print("Construindo executável...")
    print(f"Comando: {' '.join(cmd)}")
    
    try:
        subprocess.check_call(cmd)
        print("\nExecutável construído com sucesso!")
        print("Localização: dist/br_service.exe (Windows) ou dist/br_service (Linux/Mac)")
    except subprocess.CalledProcessError as e:
        print(f"Erro ao construir executável: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if build_executable():
        print("\nBuild concluído com sucesso!")
    else:
        print("\nFalha no build.")
        sys.exit(1)

