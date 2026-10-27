"""
O relatório do Power BI em PBIR (pasta `<Projeto>.Report`): o formato texto
de relatório do .pbip, com um arquivo JSON por página e por visual.

Cada arquivo segue o JSON Schema público da Microsoft que vai no `$schema`
(github.com/microsoft/json-schemas, pasta fabric/item/report). A posição de
cada visual vem de `layout.posicionar`, a mesma do protótipo aprovado.
"""

import os

from .especificacao import TIPOS_VISUAL, medida
from .layout import LARGURA, altura_da_pagina, posicionar
from .prototipo import titulo_do_cartao
from .util import curto, gravar_json

S = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition'

# Papéis (buckets) de dados de cada visual nativo.
PAPEIS = {
    'card': {'valores': 'Values'},
    'gauge': {'valores': 'Y', 'meta': 'TargetValue'},
    'slicer': {'categoria': 'Values'},
    'tableEx': {'campos': 'Values'},
    'pivotTable': {'linhas': 'Rows', 'colunas': 'Columns', 'valores': 'Values'},
    'clusteredBarChart': {'categoria': 'Category', 'legenda': 'Series', 'valores': 'Y'},
    'clusteredColumnChart': {'categoria': 'Category', 'legenda': 'Series', 'valores': 'Y'},
    'lineChart': {'categoria': 'Category', 'legenda': 'Series', 'valores': 'Y'},
    'donutChart': {'categoria': 'Category', 'valores': 'Y'},
}


def _lit(valor):
    if isinstance(valor, bool):
        return {'expr': {'Literal': {'Value': 'true' if valor else 'false'}}}
    if isinstance(valor, (int, float)):
        return {'expr': {'Literal': {'Value': f'{valor}D'}}}
    return {'expr': {'Literal': {'Value': "'" + str(valor).replace("'", "''") + "'"}}}


def _projecao(campo):
    if campo['tipo'] == 'medida':
        field = {'Measure': {'Expression': {'SourceRef': {'Entity': campo['tabela']}}, 'Property': campo['nome']}}
    else:
        field = {'Column': {'Expression': {'SourceRef': {'Entity': campo['tabela']}}, 'Property': campo['nome']}}
    return {'field': field, 'queryRef': f'{campo["tabela"]}.{campo["nome"]}', 'nativeQueryRef': campo['nome']}


def _query(v):
    tipo = TIPOS_VISUAL[v['tipo']]
    estado = {}
    for chave_v, papel in PAPEIS[tipo].items():
        valor = v.get(chave_v)
        campos = valor if isinstance(valor, list) else ([valor] if valor else [])
        if campos:
            estado.setdefault(papel, {'projections': []})['projections'].extend(_projecao(c) for c in campos)
    q = {'queryState': estado}
    if tipo in ('clusteredBarChart', 'donutChart') and v.get('valores'):
        q['sortDefinition'] = {'sort': [{'field': _projecao(v['valores'][0])['field'], 'direction': 'Descending'}],
                               'isDefaultSort': True}
    return q


def _cor_da_medida(m, nome_cor):
    md = medida(m, nome_cor)
    return {'solid': {'color': {'expr': {'Measure': {'Expression': {'SourceRef': {'Entity': md['tabela']}},
                                                     'Property': md['nome']}}}}}


def visual(m, v, pos, nome, ordem):
    tipo = TIPOS_VISUAL[v['tipo']]
    container = {'title': [{'properties': {'show': _lit(True), 'text': _lit(v['titulo'])}}]}
    vis = {'visualType': tipo, 'query': _query(v), 'visualContainerObjects': container,
           'drillFilterOtherVisuals': True}
    if tipo == 'slicer':
        vis['objects'] = {'data': [{'properties': {'mode': _lit('Dropdown')}}]}
    if tipo == 'card':
        meta = titulo_do_cartao(m, v)
        container['title'] = [{'properties': {'show': _lit(bool(meta)), **({'text': _lit(meta)} if meta else {})}}]
        cor = (medida(m, v['valores'][0]['nome']) or {}).get('cor_medida')
        if cor:
            vis['objects'] = {'labels': [{'properties': {'color': _cor_da_medida(m, cor)}}]}
    if tipo in ('tableEx', 'pivotTable'):
        regras = []
        for c in v['campos'] + v['valores']:
            cor = c and c['tipo'] == 'medida' and (medida(m, c['nome']) or {}).get('cor_medida')
            if cor:
                regras.append({'properties': {'fontColor': _cor_da_medida(m, cor)},
                               'selector': {'metadata': f'{c["tabela"]}.{c["nome"]}'}})
        if regras:
            vis['objects'] = {'values': regras}
    return {
        '$schema': f'{S}/visualContainer/2.0.0/schema.json',
        'name': nome,
        'position': {'x': pos['x'], 'y': pos['y'], 'z': ordem * 1000, 'width': pos['w'], 'height': pos['h'],
                     'tabOrder': ordem * 1000},
        'visual': vis,
    }


def _tema(m):
    t = m['tema']
    return {'name': 'Deidara', 'dataColors': t['cores'], 'background': t['fundo'], 'foreground': t['texto'],
            'tableAccent': t['cores'][0],
            'textClasses': {'title': {'fontFace': 'Segoe UI Semibold', 'fontSize': 12, 'color': t['texto']},
                            'callout': {'fontFace': 'Segoe UI Semibold', 'fontSize': 32, 'color': t['texto']}}}


def gravar(m, pasta_projeto, nome):
    raiz = os.path.join(pasta_projeto, f'{nome}.Report')
    defi = os.path.join(raiz, 'definition')
    os.makedirs(os.path.join(defi, 'pages'), exist_ok=True)
    gravar_json(os.path.join(raiz, 'definition.pbir'), {
        '$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/1.0.0/schema.json',
        'version': '4.0', 'datasetReference': {'byPath': {'path': f'../{nome}.SemanticModel'}}})
    gravar_json(os.path.join(defi, 'version.json'), {'$schema': f'{S}/versionMetadata/1.0.0/schema.json',
                                                     'version': '2.0.0'})
    tema_dir = os.path.join(raiz, 'StaticResources', 'RegisteredResources')
    os.makedirs(tema_dir, exist_ok=True)
    gravar_json(os.path.join(tema_dir, 'Deidara.json'), _tema(m))
    gravar_json(os.path.join(defi, 'report.json'), {
        '$schema': f'{S}/report/1.0.0/schema.json',
        'themeCollection': {'customTheme': {'name': 'Deidara.json', 'reportVersionAtImport': '5.59',
                                            'type': 'RegisteredResources'}},
        'layoutOptimization': 'None',
        'resourcePackages': [{'name': 'RegisteredResources', 'type': 'RegisteredResources',
                              'items': [{'name': 'Deidara.json', 'path': 'Deidara.json', 'type': 'CustomTheme'}]}],
        'settings': {'useStylableVisualContainerHeader': True, 'defaultDrillFilterOtherVisuals': True,
                     'allowChangeFilterTypes': True, 'useEnhancedTooltips': True},
    })
    ordem = []
    for i, pg in enumerate(m['paginas']):
        pid = curto('pagina', pg['nome'])
        ordem.append(pid)
        pdir = os.path.join(defi, 'pages', pid)
        os.makedirs(pdir, exist_ok=True)
        posicoes = posicionar(pg['visuais'])
        gravar_json(os.path.join(pdir, 'page.json'), {
            '$schema': f'{S}/page/2.0.0/schema.json', 'name': pid, 'displayName': pg['nome'],
            'displayOption': 'FitToWidth' if altura_da_pagina(posicoes) > 720 else 'FitToPage',
            'height': altura_da_pagina(posicoes), 'width': LARGURA})
        usados = set()
        for k, (v, pos) in enumerate(posicoes):
            vid = v.get('id') or curto('visual', pg['nome'], v['tipo'], v['titulo'] or '')
            n = 1
            while vid in usados:              # dois visuais iguais na página
                n += 1
                vid = curto('visual', pg['nome'], v['tipo'], v['titulo'] or '', str(n))
            usados.add(vid)
            vdir = os.path.join(pdir, 'visuals', vid)
            os.makedirs(vdir, exist_ok=True)
            gravar_json(os.path.join(vdir, 'visual.json'), visual(m, v, pos, vid, k))
    gravar_json(os.path.join(defi, 'pages', 'pages.json'), {
        '$schema': f'{S}/pagesMetadata/1.0.0/schema.json', 'pageOrder': ordem, 'activePageName': ordem[0]})
    return raiz
