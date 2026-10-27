#!/usr/bin/env python3
"""
Empacota a skill num .zip para subir no claude.ai (área de Skills das
configurações). Leva só o que a skill usa: nada de git, cache, saídas geradas,
aprovações locais, imagens do README nem zip dentro de zip (o claude.ai recusa).

Uso:
    python3 ferramentas/empacotar.py [-o deidara-skill.zip]
"""

import argparse
import os
import sys
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTAS_FORA = {'.git', '.github', '__pycache__', 'local', 'saida', '.pbi', 'assets', '.claude'}
ARQUIVOS_FORA = {'.gitignore', '.gitattributes', 'README.en.md'}


def fica_de_fora(nome):
    return nome in ARQUIVOS_FORA or nome.endswith(('.pyc', '.aprovacao.json', '.zip'))


def empacotar(destino):
    n = 0
    with zipfile.ZipFile(destino, 'w', zipfile.ZIP_DEFLATED) as z:
        for pasta, subpastas, arquivos in os.walk(RAIZ):
            subpastas[:] = sorted(x for x in subpastas if x not in PASTAS_FORA)
            for nome in sorted(arquivos):
                caminho = os.path.join(pasta, nome)
                if fica_de_fora(nome) or os.path.abspath(caminho) == os.path.abspath(destino):
                    continue
                z.write(caminho, 'deidara/' + os.path.relpath(caminho, RAIZ).replace(os.sep, '/'))
                n += 1
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description='empacota a skill para o claude.ai')
    ap.add_argument('-o', '--saida', default=os.path.join(os.path.dirname(RAIZ), 'deidara-skill.zip'))
    a = ap.parse_args(argv)
    n = empacotar(a.saida)
    print(f'{n} arquivos, {os.path.getsize(a.saida) // 1024} KB: {a.saida}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
