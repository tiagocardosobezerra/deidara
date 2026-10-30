#!/usr/bin/env python3
"""
Empacota a skill num .zip para subir no claude.ai (área de Skills das
configurações). Leva só o que a skill usa: nada de git, cache, saídas geradas,
aprovações locais, imagens do README nem zip dentro de zip (o claude.ai recusa).

Num clone git, só entra arquivo rastreado (`git ls-files`): pasta de cliente,
catálogo real ou rascunho deixado na pasta nunca vai junto. Fora do git (uma
cópia instalada), percorre a pasta com as mesmas exclusões.

Uso:
    python3 ferramentas/empacotar.py [-o deidara-skill.zip]   (padrão: deidara-skill-<versão>.zip)
"""

import argparse
import os
import subprocess
import sys
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTAS_FORA = {'.git', '.github', '__pycache__', 'local', 'saida', '.pbi', 'assets', '.claude', 'schemas'}
ARQUIVOS_FORA = {'.gitignore', '.gitattributes', 'README.en.md'}


def fica_de_fora(nome):
    return nome in ARQUIVOS_FORA or nome.endswith(('.pyc', '.aprovacao.json', '.zip'))


def arquivos_da_skill():
    """Caminhos relativos (com /) do que vai no pacote."""
    try:
        saida = subprocess.run(['git', '-C', RAIZ, 'ls-files', '-z'], capture_output=True, check=True).stdout
        todos = [x for x in saida.decode('utf-8').split(chr(0)) if x]
    except (OSError, subprocess.CalledProcessError):
        todos = []
        for pasta, subpastas, nomes in os.walk(RAIZ):
            subpastas[:] = sorted(x for x in subpastas if x not in PASTAS_FORA)
            todos += [os.path.relpath(os.path.join(pasta, x), RAIZ).replace(os.sep, '/') for x in nomes]
    return sorted(x for x in todos if not set(x.split('/')[:-1]) & PASTAS_FORA and not fica_de_fora(x.split('/')[-1])
                  and os.path.exists(os.path.join(RAIZ, x)))


def empacotar(destino):
    n = 0
    with zipfile.ZipFile(destino, 'w', zipfile.ZIP_DEFLATED) as z:
        for rel in arquivos_da_skill():
            caminho = os.path.join(RAIZ, rel)
            if os.path.abspath(caminho) == os.path.abspath(destino):
                continue
            z.write(caminho, 'deidara/' + rel)
            n += 1
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description='empacota a skill para o claude.ai')
    sys.path.insert(0, RAIZ)
    from kibaku_nendo import VERSAO
    ap.add_argument('-o', '--saida', default=os.path.join(os.path.dirname(RAIZ), f'deidara-skill-{VERSAO}.zip'))
    a = ap.parse_args(argv)
    n = empacotar(a.saida)
    print(f'{n} arquivos, {os.path.getsize(a.saida) // 1024} KB: {a.saida}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
