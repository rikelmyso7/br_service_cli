#!/usr/bin/env python3
"""
build.py

Empacota o projeto com PyInstaller.
Observação: PyInstaller não faz cross-compile. Rode este script em cada SO alvo.

Exemplos:
  - Windows (PowerShell):
      py -3 build.py --name BRService --onefile --console
  - macOS/Linux:
      python3 build.py --name BRService --onefile --console
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

def _sep_adddata() -> str:
    # PyInstaller usa ";" no Windows e ":" no POSIX para separar src e destino em --add-data
    return ";" if os.name == "nt" else ":"

def _as_add_data(src: Path, dest_rel: str) -> str:
    return f"{str(src)}{_sep_adddata()}{dest_rel}"

def main():
    try:
        from PyInstaller.__main__ import run as pyinstaller_run
    except Exception:
        print("PyInstaller não encontrado. Instale com: pip install pyinstaller", file=sys.stderr)
        sys.exit(1)

    root = Path(__file__).resolve().parent
    entry = root / "main.py"                        # ponto de entrada
    src_dir = root / "src"                          # seu pacote-fonte
    config_json = root / "config.json"              # incluído por padrão se existir
    readme_md = root / "README.md"                  # opcional

    parser = argparse.ArgumentParser(description="Empacotador PyInstaller para BR Service")
    parser.add_argument("--name", default="br_service", help="Nome do executável (default: br_service)")
    parser.add_argument("--onefile", action="store_true", help="Gera binário único (onefile)")
    parser.add_argument("--onedir", action="store_true", help="Gera pasta com binários (onedir)")
    parser.add_argument("--windowed", action="store_true", help="Sem console (GUI app)")
    parser.add_argument("--console", action="store_true", help="Com console (CLI app)")
    parser.add_argument("--clean", action="store_true", help="Limpa cache de builds do PyInstaller")
    parser.add_argument("--noconfirm", action="store_true", help="Não perguntar ao sobrescrever diretórios")
    parser.add_argument("--distpath", default=str(root / "dist"), help="Diretório de saída (default: ./dist)")
    parser.add_argument("--workpath", default=str(root / "build"), help="Diretório de trabalho (default: ./build)")
    parser.add_argument("--specpath", default=str(root), help="Onde salvar o .spec (default: raiz do projeto)")
    parser.add_argument("--icon", help="Caminho do ícone (.ico no Windows, .icns no macOS)")
    parser.add_argument("--add-data", action="append", default=[], help="Entradas extra de --add-data (src{sep}dest)")
    parser.add_argument("--hidden-import", action="append", default=[], help="Imports ocultos adicionais")
    parser.add_argument("--no-readme", action="store_true", help="Não incluir README.md")
    parser.add_argument("--no-config", action="store_true", help="Não incluir config.json")
    parser.add_argument("--exclude-module", action="append", default=[], help="Módulos a excluir do build")
    args = parser.parse_args()

    if not entry.exists():
        print(f"Arquivo de entrada não encontrado: {entry}", file=sys.stderr)
        sys.exit(2)

    # Decide onefile/onedir
    if args.onefile and args.onedir:
        print("Use apenas --onefile ou --onedir (não ambos).", file=sys.stderr)
        sys.exit(2)
    mode = "--onefile" if args.onefile or not args.onedir else "--onedir"

    # Decide console/windowed (por padrão, console)
    gui_flag = "--windowed" if args.windowed and not args.console else "--console"

    # Monta lista base de opções
    opts = [
        str(entry),
        "--name", args.name,
        "--paths", str(src_dir),           # garante que 'src' está visível
        "--distpath", args.distpath,
        "--workpath", args.workpath,
        "--specpath", args.specpath,
        gui_flag,
        mode,
    ]

    if args.clean:
        opts.append("--clean")
    if args.noconfirm:
        opts.append("--noconfirm")
    if args.icon:
        icon_path = Path(args.icon)
        if icon_path.exists():
            opts.extend(["--icon", str(icon_path)])
        else:
            print(f"Aviso: ícone não encontrado: {icon_path}", file=sys.stderr)

    # Add-data padrão (config.json e README.md, se existirem)
    if not args.no_config and config_json.exists():
        opts.extend(["--add-data", _as_add_data(config_json, "config.json")])
    if not args.no_readme and readme_md.exists():
        opts.extend(["--add-data", _as_add_data(readme_md, "README.md")])

    # Add-data extras fornecidos pelo usuário (já no formato src{sep}dest)
    for ad in args.add_data:
        # validação rápida
        if _sep_adddata() not in ad:
            print(f"Aviso: --add-data sem separador correto (use '{_sep_adddata()}'): {ad}", file=sys.stderr)
        opts.extend(["--add-data", ad])

    # Hidden imports comuns para evitar surpresas (ajuste conforme seu projeto)
    default_hidden = [
        "openpyxl",
        "pandas",
        "pkg_resources.py2_warn",  # às vezes necessário dependendo do ambiente
        "tzdata",
    ]
    for hi in default_hidden + args.hidden_import:
        opts.extend(["--hidden-import", hi])

    # Excluir bindings Qt (evita conflito PyQt6 x PySide6)
    qt_excludes = [
        "PyQt6",
        "PySide6",
        "PyQt5",
        "PySide2",
        "nltk",
        "scipy",
        # backends do matplotlib baseados em Qt
        "matplotlib.backends.backend_qtagg",
        "matplotlib.backends.backend_qt5agg",
        "matplotlib.backends.backend_qt5",
        "matplotlib.backends.qt_compat",
        "matplotlib.backends.backend_qt4agg",
    ]
    for mod in qt_excludes:
        opts.extend(["--exclude-module", mod])

    # (opcional) se você não usa matplotlib em nada:
    opts.extend(["--exclude-module", "matplotlib"])

    print("==> PyInstaller args:")
    for o in opts:
        print("  ", o)

    # Executa
    try:
        pyinstaller_run(opts)
        print(f"\nBuild concluído. Arquivos em: {args.distpath}")
    except SystemExit as e:
        # PyInstaller pode chamar sys.exit internamente; propague o código
        sys.exit(e.code)
    except Exception as e:
        print(f"Falha no build: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
