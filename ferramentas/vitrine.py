#!/usr/bin/env python3
"""
Gera a vitrine (exemplos/vitrine) em cada modelo de layout e, com --desktop, confere cada uma no Power BI Desktop.

    python3 ferramentas/vitrine.py PASTA [--modelos faixa-de-kpis,executivo] [--desktop]

Para cada modelo: argila.json, protótipo, aceite de teste, projeto de demonstração (--demo) e validar_pbip. Com
--desktop (Windows, Power BI Desktop instalado), abre cada projeto, atualiza, roda o conferir-desktop e fecha.
A conferência visual de cada página segue o roteiro de referencias/powerbi.md.
"""

import argparse
import contextlib
import io
import json
import os
import shutil
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, 'exemplos', 'vitrine'))
sys.path.insert(0, os.path.join(RAIZ, 'ferramentas'))


def gerar(pasta, modelo):
    import deidara
    import montar
    import validar_pbip
    d = os.path.join(pasta, modelo)
    shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(os.path.join(RAIZ, 'exemplos', 'vitrine', 'catalogos'), os.path.join(d, 'catalogos'))
    arq = os.path.join(d, 'argila.json')
    with open(arq, 'w', encoding='utf-8') as f:
        json.dump(montar.argila(modelo), f, ensure_ascii=False, indent=2)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        for comando in (['prototipar', arq], ['aprovar', arq, '--por', 'Vitrine', '--aceito-distorcao', 'vitrine'],
                        ['gerar', arq, '-o', os.path.join(d, 'pbi'), '--demo']):
            if deidara.main(comando) != 0:
                return arq, None, [f'{comando[0]} falhou']
    return arq, os.path.join(d, 'pbi', 'Vitrine_Deidara.pbip'), validar_pbip.conferir(os.path.join(d, 'pbi'))


def main(argv=None):
    from tecnicas.arte.modelos import MODELOS
    ap = argparse.ArgumentParser(description='a vitrine em cada modelo de layout')
    ap.add_argument('pasta')
    ap.add_argument('--modelos', help='só estes (separados por vírgula); padrão: todos')
    ap.add_argument('--desktop', action='store_true', help='abre cada uma no Power BI Desktop e roda o conferir-desktop')
    a = ap.parse_args(argv)
    modelos = a.modelos.split(',') if a.modelos else list(MODELOS)
    falhas = 0
    for modelo in modelos:
        arq, pbip, erros = gerar(a.pasta, modelo)
        print(f'{"✓" if not erros else "✗"} {modelo:20} {pbip or ""}')
        for e in erros[:5]:
            print(f'    {e}')
        falhas += bool(erros)
        if a.desktop and pbip and not erros:
            import deidara
            codigo = deidara.main(['conferir-desktop', arq, '--abrir', pbip, '--fechar'])
            falhas += codigo != 0
    return 1 if falhas else 0


if __name__ == '__main__':
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, 'reconfigure'):
            fluxo.reconfigure(encoding='utf-8')
    sys.exit(main())
