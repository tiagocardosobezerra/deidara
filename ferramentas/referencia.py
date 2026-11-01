#!/usr/bin/env python3
"""
A referência do que o Deidara gera: o aurora e a vitrine, gerados do zero, comparados arquivo a arquivo com a
última geração conferida no Power BI Desktop.

Qualquer mudança na saída (um visual, uma medida, uma linha do LEIA-ME) aparece como arquivo mudado: ou foi de
propósito, e a referência é atualizada junto com o código, ou é um efeito que ninguém pediu. Datas, horas e a
versão do Deidara saem da comparação (mudam sozinhas). A virada do ano muda o calendário: aí a referência é
regravada depois da conferência.

    python3 ferramentas/referencia.py              compara e lista o que mudou (o teste faz o mesmo)
    python3 ferramentas/referencia.py --atualizar  grava a geração de agora como a nova referência

Atualize só depois de conferir a geração nova no Power BI Desktop (referencias/powerbi.md, "Roteiro de
conferência").
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
ARQUIVO = os.path.join(RAIZ, 'testes', 'referencia.json')
PROJETOS = {'aurora': os.path.join(RAIZ, 'exemplos', 'aurora'), 'vitrine': os.path.join(RAIZ, 'exemplos', 'vitrine')}
_DATA = re.compile(r'\d{2}/\d{2}/\d{4}( \d{2}:\d{2})?|\d{4}-\d{2}-\d{2}T[\d:.]+Z?')


def _normalizado(caminho):
    with open(caminho, 'rb') as f:
        dados = f.read()
    try:
        texto = dados.decode('utf-8-sig')
    except UnicodeDecodeError:
        return dados
    from kibaku_nendo import VERSAO
    texto = _DATA.sub('<data>', texto.replace('\r\n', '\n')).replace(VERSAO, '<versao>')
    return texto.encode('utf-8')


def gerar(nome, pasta_saida):
    """Gera o projeto `nome` do zero numa cópia (argila.json + catálogos) e devolve {arquivo: sha256}."""
    import deidara
    origem = PROJETOS[nome]
    trabalho = os.path.join(pasta_saida, nome)
    shutil.copytree(os.path.join(origem, 'catalogos'), os.path.join(trabalho, 'catalogos'))
    shutil.copy(os.path.join(origem, 'argila.json'), trabalho)
    arq = os.path.join(trabalho, 'argila.json')
    for comando in (['prototipar', arq], ['aprovar', arq, '--por', 'Referência', '--aceito-distorcao', 'referência']):
        if deidara.main(comando) != 0:
            raise SystemExit(f'{nome}: {comando[0]} falhou')
    saida = os.path.join(trabalho, 'pbi')
    if deidara.main(['gerar', arq, '-o', saida]) != 0:
        raise SystemExit(f'{nome}: o gerar falhou')
    out = {'argila.prototipo.html': hashlib.sha256(_normalizado(os.path.join(trabalho, 'argila.prototipo.html'))).hexdigest()}
    for pasta, _, nomes in os.walk(saida):
        for n in nomes:
            caminho = os.path.join(pasta, n)
            rel = os.path.relpath(caminho, saida).replace(os.sep, '/')
            out[rel] = hashlib.sha256(_normalizado(caminho)).hexdigest()
    return out


def comparar(atual, gravada):
    """[(projeto, arquivo, 'mudou' | 'novo' | 'sumiu')]"""
    out = []
    for proj in sorted(set(atual) | set(gravada)):
        a, g = atual.get(proj, {}), gravada.get(proj, {})
        out += [(proj, f, 'mudou') for f in sorted(set(a) & set(g)) if a[f] != g[f]]
        out += [(proj, f, 'novo') for f in sorted(set(a) - set(g))]
        out += [(proj, f, 'sumiu') for f in sorted(set(g) - set(a))]
    return out


def geracao_atual():
    import contextlib
    import io
    d = tempfile.mkdtemp(prefix='ref')
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return {nome: gerar(nome, d) for nome in PROJETOS}
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description='compara o que o Deidara gera com a referência conferida')
    ap.add_argument('--atualizar', action='store_true', help='grava a geração de agora como a referência')
    a = ap.parse_args(argv)
    atual = geracao_atual()
    if a.atualizar:
        with open(ARQUIVO, 'w', encoding='utf-8') as f:
            json.dump(atual, f, ensure_ascii=False, indent=1, sort_keys=True)
            f.write('\n')
        print(f'Referência gravada: {sum(len(x) for x in atual.values())} arquivos ({", ".join(atual)}).')
        return 0
    with open(ARQUIVO, encoding='utf-8') as f:
        gravada = json.load(f)
    diferencas = comparar(atual, gravada)
    for proj, arq, como in diferencas:
        print(f'  {como:6} {proj}/{arq}')
    print('✓ igual à referência' if not diferencas else
          f'✗ {len(diferencas)} arquivo(s) diferentes da referência: confira no Desktop e rode --atualizar')
    return 1 if diferencas else 0


if __name__ == '__main__':
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, 'reconfigure'):
            fluxo.reconfigure(encoding='utf-8')
    sys.exit(main())
