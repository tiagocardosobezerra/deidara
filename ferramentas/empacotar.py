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
import json
import os
import subprocess
import sys
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTAS_FORA = {'.git', '.github', '__pycache__', 'local', 'saida', '.pbi', 'assets', '.claude', 'schemas', 'roteiros'}
ARQUIVOS_FORA = {'.gitignore', '.gitattributes', 'README.en.md', 'ruff.toml'}
# vitrines grandes da galeria ficam no repositório (a galeria mostra só o que está instalado); no pacote vão as
# funções DAX, os modelos Deneb prontos e o calendário
TERCEIROS_FORA = {'deneb-showcase', 'powerbi-svg', 'dataviz-vega', 'deneb-vega-showcase'}
TERCEIROS_MAX = 1_000_000                          # mapa com o mundo inteiro dentro (2,7 MB cada) fica de fora
MAX_ARQUIVOS = 200                                 # o claude.ai recusa zip com mais arquivos que isso
# em terceiros/, só a licença, a origem e o catálogo vão soltos; o resto vai junto em terceiros/pacote.json
TERCEIROS_SOLTOS = {'LICENSE', 'ORIGEM.md', 'catalogo.json'}


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
                  and os.path.exists(os.path.join(RAIZ, x)) and not _terceiro_fora(x))


def _terceiro_fora(rel):
    partes = rel.split('/')
    if partes[0] != 'terceiros' or len(partes) < 3:
        return False
    return partes[1] in TERCEIROS_FORA or os.path.getsize(os.path.join(RAIZ, rel)) > TERCEIROS_MAX


PASTAS_DE_CODIGO = ('tecnicas/', 'kibaku_nendo/', 'dicionario/', 'referencias/', 'ferramentas/', 'terceiros/',
                    'exemplos/', 'deidara.py', 'SKILL.md')


def codigo_fora_do_git():
    """Código da skill que ainda não está no git: o pacote sai só com o que está no git (proteção contra levar um
    arquivo de cliente esquecido na pasta), então código novo sem `git add` deixaria o pacote incompleto."""
    try:
        saida = subprocess.run(['git', '-C', RAIZ, 'ls-files', '-z', '--others', '--exclude-standard'],
                               capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return []
    return sorted(x for x in saida.decode('utf-8').split(chr(0))
                  if x.startswith(PASTAS_DE_CODIGO) and x.endswith(('.py', '.md', '.json', '.tmdl', '.daxlib')))


def empacotar(destino, exigir_git=True):
    faltam = codigo_fora_do_git() if exigir_git else []
    if faltam:
        raise SystemExit('Código da skill fora do git (o pacote sairia incompleto): '
                         + ', '.join(faltam[:8]) + (f' e mais {len(faltam) - 8}' if len(faltam) > 8 else '')
                         + '. Faça `git add` (e o commit) antes de empacotar.')
    soltos, juntos = [], {}
    for rel in arquivos_da_skill():
        if os.path.abspath(os.path.join(RAIZ, rel)) == os.path.abspath(destino):
            continue
        if rel == 'terceiros/pacote.json':              # empacotando de uma cópia já instalada
            with open(os.path.join(RAIZ, rel), encoding='utf-8') as f:
                juntos.update(json.load(f))
        elif rel.startswith('terceiros/') and rel.split('/')[-1] not in TERCEIROS_SOLTOS:
            with open(os.path.join(RAIZ, rel), encoding='utf-8-sig') as f:
                juntos[rel] = f.read()
        else:
            soltos.append(rel)
    n = len(soltos) + bool(juntos)
    if n > MAX_ARQUIVOS:
        raise SystemExit(f'O pacote teria {n} arquivos e o claude.ai aceita no máximo {MAX_ARQUIVOS}: '
                         'tire pastas do pacote (PASTAS_FORA) ou junte arquivos.')
    with zipfile.ZipFile(destino, 'w', zipfile.ZIP_DEFLATED) as z:
        for rel in soltos:
            z.write(os.path.join(RAIZ, rel), 'deidara/' + rel)
        if juntos:
            z.writestr('deidara/terceiros/pacote.json', json.dumps(juntos, ensure_ascii=False))
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description='empacota a skill para o claude.ai')
    sys.path.insert(0, RAIZ)
    from kibaku_nendo import VERSAO
    ap.add_argument('-o', '--saida', default=os.path.join(os.path.dirname(RAIZ), f'deidara-skill-{VERSAO}.zip'))
    ap.add_argument('--sem-conferir-git', action='store_true', help='empacota mesmo com código novo fora do git')
    a = ap.parse_args(argv)
    n = empacotar(a.saida, exigir_git=not a.sem_conferir_git)
    print(f'{n} arquivos, {os.path.getsize(a.saida) // 1024} KB: {a.saida}')
    return 0


if __name__ == '__main__':
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, 'reconfigure'):
            fluxo.reconfigure(encoding='utf-8')
    sys.exit(main())
