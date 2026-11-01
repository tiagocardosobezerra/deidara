"""
Os comandos da Arte: os modelos de layout e as técnicas de visual.
"""

import json
from tecnicas import sasori as dicionario
from tecnicas.arte.modelos import MODELOS


def cmd_modelos(a):
    print('Modelos de layout ("modelo" no argila.json; ver referencias/modelos.md):')
    for k, v in MODELOS.items():
        print(f'  {k:<20} {v}')
    return 0


def cmd_visuais(a):
    achados = dicionario.visuais_para(a.termo or '')
    if not achados:
        print(f'Nenhuma técnica para "{a.termo}". Sem assunto, `deidara.py visuais` lista todas.')
        return 1
    for v in achados:
        selo = 'o Deidara gera' if v['deidara'].get('gera') else ('nativo' if v['nativo'] else 'visual personalizado')
        print(f'\n{v["nome"]}  [{v["id"]}] · {selo}')
        print(f'  Quando: {v["quando"]}')
        if v['deidara'].get('argila'):
            print(f'  argila.json (medida): {json.dumps(v["deidara"]["argila"], ensure_ascii=False)}')
        if v['deidara'].get('visual'):
            print(f'  argila.json (visual): {json.dumps(v["deidara"]["visual"], ensure_ascii=False)}')
        if v['deidara'].get('raiz'):
            print(f'  argila.json (raiz): {json.dumps(v["deidara"]["raiz"], ensure_ascii=False)}')
        if v['deidara'].get('pagina'):
            print(f'  argila.json (página): {json.dumps(v["deidara"]["pagina"], ensure_ascii=False)}')
        print(f'  No Power BI: {v["power_bi"]}')
        for x in v.get('cuidados') or []:
            print(f'  Atenção: {x}')
    print('\nGuia de design: referencias/design.md · medidas SVG: referencias/svg.md')
    return 0


def registrar(sub):
    mo = sub.add_parser('modelos', help='os modelos de layout (faixa de KPIs, coluna de KPIs, história longa...)')
    mo.set_defaults(func=cmd_modelos)
    vs = sub.add_parser('visuais', help='técnicas de visual (meta, ranking, causa, status...) e como fazer')
    vs.add_argument('termo', nargs='?')
    vs.set_defaults(func=cmd_visuais)
