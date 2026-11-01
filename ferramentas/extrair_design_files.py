#!/usr/bin/env python3
"""
Rascunho de estilos a partir dos .pbix do Power BI Design Files (Sajjad Ahmadi, MIT): a formatação de cada tipo
de visual nos dashboards que deram origem aos modelos de layout, para comparar com
terceiros/power-bi-design-files/estilos.json (a curadoria, que é o que o Deidara usa) ou começar um modelo novo.

A curadoria de 29/10/2026 escolheu à mão qual visual de cada dashboard vale e tirou objetos ligados aos dados de
origem; este rascunho não a reproduz igual. Ele serve para ver o que mudou numa versão nova do repositório de
origem e levar para a curadoria só o que fizer sentido.

Lê só a formatação (objects e o contêiner de cada visual), nunca dados, campos nem imagens. Regra que tira o que
depende do dashboard de origem: entrada com seletor de campo ou de série (metadata, data) fica de fora, porque
aponta para uma coluna que o painel do usuário não tem. Do mesmo tipo de visual, vale o primeiro da primeira página
(como o autor formatou o visual principal).

Aceita os dois formatos de relatório que um .pbix guarda: o PBIR (Report/definition/pages/*/visuals/*/visual.json)
e o antigo (Report/Layout, JSON em UTF-16 com o config de cada visual como texto).

Uso (os .pbix baixados numa pasta, sem rodar nada deles):
    python3 ferramentas/extrair_design_files.py PASTA_DOS_PBIX [-o estilos.rascunho.json]

O `base` (o estilo de quem não escolheu modelo) é o do visual mais formatado entre os modelos, tipo a tipo.
"""

import argparse
import json
import os
import re
import sys
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = 'estilos.rascunho.json'

# o modelo do Deidara e o .pbix que deu origem a ele (referencias/modelos.md)
ORIGEM = {
    'faixa-de-kpis': 'Agents Performance - Dashboard.pbix',
    'coluna-de-kpis': 'IT_Support_Ticket_Desk.pbix',
    'secoes-com-rolagem': 'Ecommerce Conversion Dashboard.pbix',
    'trilho-escuro': 'Inventory Analysis in Power BI.pbix',
    'kpis-clicaveis': 'Interactive Dashboard Tour.pbix',
    'historia-longa': 'World Champs BCN 26 - Round 3 - THE MOVIE SUCCESS MATRIX.pbix',
    'executivo': 'Exceutive Sales Report - Toast Notifictaion.pbix',
    'mapa-central': 'GeoSales Dashboard - Azure Map.pbix',
    'causa-raiz': 'Root Cause Analysis Dashboard.pbix',
    'equipes': 'Sales Teams Quarterly Performance.pbix',
    'tabela-lateral': 'Awesome Chocolates - Performance Dashboard - Chandoo.org.pbix',
}

# os tipos de visual que o Deidara gera
TIPOS = ['clusteredBarChart', 'clusteredColumnChart', 'card', 'cardVisual', 'slicer', 'advancedSlicerVisual',
         'tableEx', 'pivotTable', 'lineChart', 'areaChart', 'donutChart', 'scatterChart', 'decompositionTreeVisual',
         'azureMap']


def _limpar(entradas):
    """Sem as entradas que apontam para um campo ou série do dashboard de origem."""
    out = []
    for e in entradas or []:
        sel = e.get('selector') or {}
        if set(sel) - {'id'}:
            continue
        out.append({k: v for k, v in e.items() if k in ('properties', 'selector')})
    return [e for e in out if e.get('properties')]


def _estilo(objects, container):
    obj = {k: v for k, v in ((k, _limpar(v)) for k, v in (objects or {}).items()) if v}
    cont = {k: v for k, v in ((k, _limpar(v)) for k, v in (container or {}).items()) if v}
    return {'objects': obj, 'container': cont}


def visuais_do_pbix(caminho):
    """[(página, posição, tipo, objects, container)] na ordem do relatório."""
    out = []
    with zipfile.ZipFile(caminho) as z:
        nomes = z.namelist()
        if 'Report/Layout' in nomes:
            layout = json.loads(z.read('Report/Layout').decode('utf-16-le').lstrip('﻿'))
            for k, sec in enumerate(layout.get('sections', [])):
                for vc in sec.get('visualContainers', []):
                    cfg = json.loads(vc.get('config') or '{}')
                    sv = cfg.get('singleVisual') or {}
                    if sv.get('visualType'):
                        out.append((k, (vc.get('y', 0), vc.get('x', 0)), sv['visualType'], sv.get('objects'),
                                    sv.get('vcObjects')))
        else:
            ordem = []
            if 'Report/definition/pages/pages.json' in nomes:
                ordem = json.loads(z.read('Report/definition/pages/pages.json')).get('pageOrder', [])
            for n in nomes:
                m = re.match(r'Report/definition/pages/([^/]+)/visuals/[^/]+/visual\.json$', n)
                if not m:
                    continue
                doc = json.loads(z.read(n).decode('utf-8-sig'))
                v = doc.get('visual') or {}
                if v.get('visualType'):
                    pos = doc.get('position') or {}
                    pagina = ordem.index(m.group(1)) if m.group(1) in ordem else len(ordem)
                    out.append((pagina, (pos.get('y', 0), pos.get('x', 0)), v['visualType'], v.get('objects'),
                                v.get('visualContainerObjects')))
    return sorted(out, key=lambda x: (x[0], x[1]))


def extrair(pasta):
    modelos, faltam = {}, []
    for modelo, arq in ORIGEM.items():
        caminho = os.path.join(pasta, arq)
        if not os.path.exists(caminho):
            faltam.append(arq)
            continue
        estilos = {}
        for _, _, tipo, objects, container in visuais_do_pbix(caminho):
            if tipo in TIPOS and tipo not in estilos:
                e = _estilo(objects, container)
                if e['objects'] or e['container']:
                    estilos[tipo] = e
        modelos[modelo] = estilos
    base = {}
    for tipo in TIPOS:                                # o mais formatado entre os modelos, tipo a tipo
        candidatos = [m[tipo] for m in modelos.values() if tipo in m]
        if candidatos:
            base[tipo] = max(candidatos, key=lambda e: len(json.dumps(e)))
    return {'formato': 'deidara-estilos/1',
            'sobre': 'RASCUNHO extraído dos dashboards de Sajjad Ahmadi (Power BI Design Files, MIT), para comparar '
                     'com a curadoria em terceiros/power-bi-design-files/estilos.json.',
            'origem': dict(ORIGEM), 'base': base, 'modelos': modelos}, faltam


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument('pasta', help='a pasta com os .pbix baixados do Power BI Design Files')
    ap.add_argument('-o', '--saida', default=DESTINO)
    a = ap.parse_args(argv)
    estilos, faltam = extrair(a.pasta)
    if faltam:
        print('Faltam .pbix na pasta: ' + ', '.join(faltam))
        return 1
    with open(a.saida, 'w', encoding='utf-8') as f:
        f.write(json.dumps(estilos, ensure_ascii=False, indent=1) + '\n')
    n = sum(len(x) for x in estilos['modelos'].values())
    print(f'{len(estilos["modelos"])} modelos, {n} estilos de visual: {a.saida}')
    return 0


if __name__ == '__main__':
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, 'reconfigure'):
            fluxo.reconfigure(encoding='utf-8')
    sys.exit(main())
