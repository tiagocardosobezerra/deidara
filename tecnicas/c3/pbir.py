"""
O relatório do Power BI em PBIR (pasta `<Projeto>.Report`): o formato texto
de relatório do .pbip, com um arquivo JSON por página e por visual.

Cada arquivo segue o JSON Schema público da Microsoft que vai no `$schema`
(github.com/microsoft/json-schemas, pasta fabric/item/report). A posição de
cada visual vem de `layout.posicionar`, a mesma do protótipo aprovado.
"""

import copy
import os

from kibaku_nendo.especificacao import TIPOS_VISUAL, medida
from kibaku_nendo.relato import nota_de_ajuda
from tecnicas.arte.modelos import montar, paginas_do_relatorio
from tecnicas.c1.prototipo import titulo_do_cartao
from kibaku_nendo.util import curto, gravar_json

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
    'advancedSlicerVisual': {'categoria': 'Values'},
    'cardVisual': {'valores': 'Data'},
    'decompositionTreeVisual': {'valores': 'Analyze', 'linhas': 'ExplainBy'},
    'areaChart': {'categoria': 'Category', 'legenda': 'Series', 'valores': 'Y'},
    'azureMap': {'categoria': 'Category', 'legenda': 'Series', 'valores': 'Size'},
    'scatterChart': {'categoria': 'Category'},          # X, Y e Size saem de "valores", na ordem
    'columnChart': {'categoria': 'Category', 'legenda': 'Series', 'valores': 'Y'},
    'htmlContent443BE3AD55E043BF878BED274D3A6865': {'valores': 'content'},
    'deneb7E15AEF80B9E4D4F8E12924291ECE89A': {'categoria': 'dataset', 'valores': 'dataset'},
}


def _lit(valor):
    if isinstance(valor, bool):
        return {'expr': {'Literal': {'Value': 'true' if valor else 'false'}}}
    if isinstance(valor, (int, float)):
        return {'expr': {'Literal': {'Value': f'{valor}D'}}}
    return {'expr': {'Literal': {'Value': "'" + str(valor).replace("'", "''") + "'"}}}


def _int(valor):
    return {'expr': {'Literal': {'Value': f'{int(valor)}L'}}}


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
    if tipo == 'scatterChart':
        for papel, c in zip(('X', 'Y', 'Size'), v.get('valores') or []):
            if c:
                estado[papel] = {'projections': [_projecao(c)]}
    q = {'queryState': estado}
    if tipo in ('clusteredBarChart', 'donutChart') and v.get('valores'):
        principal = v['valores'][-1] if v['tipo'] == 'setas' else v['valores'][0]    # setas: ordena pelo atual
        q['sortDefinition'] = {'sort': [{'field': _projecao(principal)['field'], 'direction': 'Descending'}],
                               'isDefaultSort': True}
    return q


def _estilo(m, tipo):
    """Estilo do tipo de visual no modelo do painel; o layout padrão fica com a formatação do Power BI."""
    modelo = m.get('modelo') or 'padrao'
    if modelo == 'padrao':
        return None
    from tecnicas.sasori import estilos
    dados = estilos()
    return (dados['modelos'].get(modelo) or {}).get(tipo) or dados['base'].get(tipo)


def _medida_expr(m, nome):
    md = medida(m, nome)
    return {'expr': {'Measure': {'Expression': {'SourceRef': {'Entity': md['tabela']}}, 'Property': md['nome']}}}


def _filtro_padrao(tabela, coluna, valor):
    """O valor que já vem selecionado no segmentador (a primeira aba)."""
    return {'filter': {'Version': 2, 'From': [{'Name': 'o', 'Entity': tabela, 'Type': 0}],
                       'Where': [{'Condition': {'In': {
                           'Expressions': [{'Column': {'Expression': {'SourceRef': {'Source': 'o'}}, 'Property': coluna}}],
                           'Values': [[_lit(valor)['expr']]]}}}]}}


def _imagens_por_estado(m, apagada, acesa):
    """A imagem de cada botão vem de uma medida: uma para o botão em repouso, outra para o selecionado."""
    base = {'sourceType': _lit('imageUrl'), 'enhancedFit': _lit('Fit'), 'show': _lit(True), 'padding': _int(4)}
    out = []
    for estado, nome in (('interaction:rest', apagada), ('interaction:hover', acesa), ('selection:selected', acesa)):
        out += [{'properties': base, 'selector': {'id': estado}},
                {'properties': {'url': _medida_expr(m, nome)},
                 'selector': {'data': [{'dataViewWildcard': {'matchingOption': 1}}], 'id': estado, 'hierarchyMatching': 1}}]
    return out


def _tecnicas(m, v, vis, container, pos):
    """A formatação das técnicas do Power BI Design Files que saem prontas (dicionario/visuais.json)."""
    objs = vis.setdefault('objects', {})
    acento = m['tema']['cores'][0]
    if v['tipo'] == 'abas':                  # abas: uma por opção, barra de destaque em cima da escolhida
        alvo = medida(m, v['controla'])
        rotulos = alvo['extra']['rotulos']
        objs['layout'] = [{'properties': {'autoGrid': _lit(False), 'rowCount': _int(1), 'columnCount': _int(len(rotulos)),
                                          'cellPadding': _int(4)}}]
        objs['selection'] = [{'properties': {'strictSingleSelect': _lit(True)}}]
        objs['fillCustom'] = [{'properties': {'show': _lit(False)}, 'selector': {'id': 'default'}},
                              {'properties': {'show': _lit(True), 'fillColor': {'solid': {'color': _lit(acento)}},
                                              'transparency': _lit(90)}, 'selector': {'id': 'selection:selected'}}]
        objs['outline'] = [{'properties': {'show': _lit(False)}, 'selector': {'id': 'default'}}]
        objs['accentBar'] = [{'properties': {'show': _lit(False), 'position': _lit('Top')}, 'selector': {'id': 'default'}},
                             {'properties': {'show': _lit(True), 'color': {'solid': {'color': _lit(acento)}},
                                             'width': _lit(5)}, 'selector': {'id': 'selection:selected'}}]
        objs['general'] = [{'properties': _filtro_padrao(alvo['extra']['tabela'], alvo['extra']['coluna'], rotulos[0])}]
        objs['value'] = [{'properties': {'fontColor': {'solid': {'color': _lit(m['tema']['texto'])}}, 'fontSize': _lit(14)},
                          'selector': {'id': 'default'}},
                         {'properties': {'fontColor': {'solid': {'color': _lit(acento)}}, 'bold': _lit(True)},
                          'selector': {'id': 'selection:selected'}}]
    elif v['tipo'] == 'alternar':            # chave liga/desliga: um botão só, com a imagem de cada estado
        objs['layout'] = [{'properties': {'autoGrid': _lit(False), 'rowCount': _int(1), 'columnCount': _int(1),
                                          'cellPadding': _int(2)}}]
        objs['selection'] = [{'properties': {'singleSelect': _lit(True)}}]
        objs['value'] = [{'properties': {'fontColor': {'solid': {'color': _lit(m['tema']['texto'])}}, 'fontSize': _lit(13)},
                          'selector': {'id': 'default'}}]               # o rótulo ("Ver custo") ao lado da chave
        objs['fillCustom'] = [{'properties': {'show': _lit(False)}, 'selector': {'id': 'default'}}]
        objs['outline'] = [{'properties': {'show': _lit(False)}, 'selector': {'id': 'default'}}]
        desligada, ligada = medida(m, v['controla'])['chave']
        objs['image'] = _imagens_por_estado(m, desligada, ligada)
        container['title'] = [{'properties': {'show': _lit(False)}}]
    elif v['tipo'] == 'botoes':
        if v.get('icone'):                   # o ícone de "selecionado" no próprio botão
            objs['selectionIcon'] = [
                {'properties': {'show': _lit(True)}},
                {'properties': {'size': _int(15), 'spacing': _int(6)}, 'selector': {'id': 'default'}},
                {'properties': {'color': {'solid': {'color': _lit('#A19F9D')}}}, 'selector': {'id': 'interaction:rest'}},
                {'properties': {'color': {'solid': {'color': _lit(acento)}}}, 'selector': {'id': 'selection:selected'}}]
        if v.get('imagem'):                  # uma imagem por item, da medida (apagada) e da (ligado), se houver
            img = medida(m, v['imagem'])
            ligada = medida(m, img.get('ligado') or '') or img
            objs['image'] = _imagens_por_estado(m, img['nome'], ligada['nome'])
    elif v['tipo'] == 'skyline':             # blocos empilhados com um respiro entre eles
        objs['layout'] = [{'properties': {'stackedGapSize': _lit(3), 'stackedGapExplodes': _lit(False)}}]
        objs['categoryAxis'] = [{'properties': {'innerPadding': _int(8), 'showAxisTitle': _lit(False)}}]
        objs['valueAxis'] = [{'properties': {'showAxisTitle': _lit(False)}}]
        objs['dataPoint'] = [{'properties': {'borderShow': _lit(True), 'borderColorMatchFill': _lit(False),
                                             'borderColor': {'solid': {'color': _lit('#FFFFFF')}}, 'borderSize': _lit(1)}}]
    elif v['tipo'] == 'setas':               # barras invisíveis; a barra de erro liga o anterior (cinza) ao atual
        ant, atual = v['valores']
        qa, qb = f'{ant["tabela"]}.{ant["nome"]}', f'{atual["tabela"]}.{atual["nome"]}'
        def ate(nome):                       # a barra de erro vai do valor da série até o limite; o marcador fica no limite
            return {'errorRange': {'kind': 'ErrorRange', 'explicit': {
                'isRelative': _lit(False), 'lowerBound': _medida_expr(m, nome), 'upperBound': _medida_expr(m, nome)}}}
        todos = [{'dataViewWildcard': {'matchingOption': 0}}]
        objs['dataPoint'] = [{'properties': {'fillTransparency': _lit(100)}}]
        objs['layout'] = [{'properties': {'clusteredGapSize': _lit(100), 'clusteredGapOverlaps': _lit(True)}}]
        objs['legend'] = [{'properties': {'show': _lit(False)}}]
        objs['valueAxis'] = [{'properties': {'showAxisTitle': _lit(False), 'gridlineShow': _lit(True),
                                             'gridlineColor': {'solid': {'color': _lit('#E1E1E1')}}}}]
        objs['categoryAxis'] = [{'properties': {'showAxisTitle': _lit(False), 'innerPadding': _int(53)}}]
        objs['error'] = [                    # do atual até o anterior: ponto cinza no anterior
            {'properties': {'enabled': _lit(True), 'markerSize': _lit(8), 'markerShape': _lit('circle'),
                            'barColor': {'solid': {'color': _lit('#A19F9D')}}, 'barWidth': _int(2), 'barBorderSize': _int(0),
                            'labelShow': _lit(False)}, 'selector': {'metadata': qb}},
            {'properties': ate(ant['nome']), 'selector': {'data': todos, 'metadata': qb, 'highlightMatching': 1}},
            # do anterior até o atual: ponto colorido no atual, com a variação em percentual
            {'properties': {'enabled': _lit(True), 'markerSize': _lit(9), 'markerShape': _lit('circle'),
                            'barColor': {'solid': {'color': _lit(acento)}}, 'barWidth': _int(3), 'barBorderSize': _int(0),
                            'labelShow': _lit(True), 'labelFormat': _lit('relativePercentage'),
                            'labelMatchSeriesColor': _lit(False)}, 'selector': {'metadata': qa}},
            {'properties': ate(atual['nome']), 'selector': {'data': todos, 'metadata': qa, 'highlightMatching': 1}}]
    elif v['tipo'] == 'imagem':              # a medida SVG ocupa o cartão novo inteiro
        objs['value'] = [{'properties': {'show': _lit(False)}}]
        objs['label'] = [{'properties': {'show': _lit(False)}, 'selector': {'id': 'default'}}]
        objs['image'] = [{'properties': {'show': _lit(True), 'imageType': _lit('imageUrl'),
                                         'imageUrl': _medida_expr(m, v['valores'][0]['nome']), 'imageAreaSize': _int(100),
                                         'padding': _int(0), 'position': _lit('Left')}, 'selector': {'id': 'default'}}]
    elif v['tipo'] == 'aviso':               # a faixa de aviso: texto vermelho, fundo vermelho claro só quando avisa
        objs['value'] = [{'properties': {'fontSize': _lit(14), 'fontColor': {'solid': {'color': _lit('#A4262C')}},
                                         'horizontalAlignment': _lit('left')}, 'selector': {'id': 'default'}}]
        objs['label'] = [{'properties': {'show': _lit(False)}, 'selector': {'id': 'default'}}]
        container['title'] = [{'properties': {'show': _lit(False)}}]
        if v.get('cor_fundo'):
            container['background'] = [{'properties': {'show': _lit(True), 'transparency': _lit(0),
                                                       'color': _cor_da_medida(m, v['cor_fundo'])}}]
    elif v['tipo'] == 'vegalite':            # Deneb: a especificação Vega-Lite vai pronta
        objs['vega'] = [{'properties': {'provider': _lit('vegaLite'), 'renderMode': _lit('svg'),
                                        'jsonSpec': _lit(_spec_vegalite(v)), 'jsonConfig': _lit('{}'),
                                        'isNewDialogOpen': _lit(False)}}]
    elif v['tipo'] == 'mapa' and v.get('marcador'):   # cada ponto vira a imagem SVG da medida
        objs['bubbleLayer'] = [{'properties': {'show': _lit(True), 'markerType': _lit('image'), 'bubbleRadius': _int(45),
                                               'clusteringEnabled': _lit(False)}},
                               {'properties': {'imageUrl': _medida_expr(m, v['marcador'])},
                                'selector': {'data': [{'dataViewWildcard': {'matchingOption': 1}}]}}]
    elif v['tipo'] == 'mapa' and v.get('camada') == 'colunas':   # colunas 3D no lugar das bolhas
        objs['bubbleLayer'] = [{'properties': {'show': _lit(False)}}]
        objs['barChart'] = [{'properties': {'show': _lit(True), 'barHeight': _int(4), 'thickness': _int(2),
                                            'maxZoom': _int(22)}}]
    elif v['tipo'] == 'controle':            # C4 Karura: o indicador na cor do tema, o centro cinza, os limites vermelhos
        cores = (acento, '#605E5C', '#D13438', '#D13438')
        objs['dataPoint'] = [{'properties': {'fill': {'solid': {'color': _lit(cor)}}},
                              'selector': {'metadata': f'{x["tabela"]}.{x["nome"]}'}}
                             for x, cor in zip(v['valores'], cores) if x]
    elif v['tipo'] == 'dispersao' and (medida(m, v['valores'][0]['nome']) or {}).get('tipo') == 'jitter':
        objs['categoryAxis'] = [{'properties': {'show': _lit(False)}}]   # jitter: o X só espalha os pontos
    primeira = medida(m, v['valores'][0]['nome']) if v['valores'] and v['valores'][0] else None
    cor = v.get('cor') or ((primeira or {}).get('tipo') in ('impacto', 'fora_da_curva') and len(v['valores']) == 1
                           and primeira['cor_medida'])
    if cor:                                  # cor de cada barra pela medida (o destaque do item escolhido, o impacto)
        objs['dataPoint'] = [{'properties': {'fill': _cor_da_medida(m, cor)},
                              'selector': {'data': [{'dataViewWildcard': {'matchingOption': 1}}]}}]
    if not objs:
        vis.pop('objects')


def _spec_vegalite(v):
    """Pirulito (linha e ponto) da primeira medida por categoria, maior primeiro; a segunda medida vira o tamanho."""
    import json
    if v.get('spec'):
        return v['spec'] if isinstance(v['spec'], str) else json.dumps(v['spec'], ensure_ascii=False)
    cat, val = v['categoria']['nome'], v['valores'][0]['nome']
    ordem = {'field': val, 'order': 'descending'}
    spec = {'$schema': 'https://vega.github.io/schema/vega-lite/v5.json', 'data': {'name': 'dataset'},
            'encoding': {'y': {'field': cat, 'type': 'nominal', 'sort': ordem, 'title': None},
                         'x': {'field': val, 'type': 'quantitative', 'title': None}},
            'layer': [{'mark': {'type': 'rule', 'color': '#C8C6C4'}},
                      {'mark': {'type': 'circle', 'size': 160, 'opacity': 1}},
                      {'mark': {'type': 'text', 'align': 'left', 'dx': 10}, 'encoding': {'text': {'field': val, 'format': ',.0f'}}}]}
    return json.dumps(spec, ensure_ascii=False)


def _cor_da_medida(m, nome_cor):
    md = medida(m, nome_cor)
    return {'solid': {'color': {'expr': {'Measure': {'Expression': {'SourceRef': {'Entity': md['tabela']}},
                                                     'Property': md['nome']}}}}}


def visual(m, v, pos, nome, ordem, transparente=False):
    tipo = TIPOS_VISUAL[v['tipo']]
    container = {'title': [{'properties': {'show': _lit(bool(v['titulo'])), 'text': _lit(v['titulo'] or '')}}]}
    vis = {'visualType': tipo, 'query': _query(v), 'visualContainerObjects': container,
           'drillFilterOtherVisuals': True}
    if tipo == 'slicer':
        vis['objects'] = {'data': [{'properties': {'mode': _lit('Dropdown')}}],
                          'header': [{'properties': {'show': _lit(False)}}]}
    if tipo == 'card':
        meta = titulo_do_cartao(m, v)
        rotulo = (medida(m, v['valores'][0]['nome']) or {}).get('rotulo_meta')
        texto = _cor_da_medida(m, rotulo)['solid']['color'] if rotulo else (_lit(meta) if meta else None)
        container['title'] = [{'properties': {'show': _lit(bool(meta)), **({'text': texto} if texto else {})}}]
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
        if any(c and c['tipo'] == 'medida' and (medida(m, c['nome']) or {}).get('imagem') for c in v['campos'] + v['valores']):
            # medida SVG (Image URL): o tamanho padrão da imagem na tabela é pequeno demais para a barra
            tipos_img = {(medida(m, c['nome']) or {}).get('tipo') for c in v['campos'] + v['valores'] if c and c['tipo'] == 'medida'}
            alto, largo = (64, 64) if 'svg_radar' in tipos_img else (24, 24) if tipos_img & {'svg_bolha'} else (24, 180)
            vis.setdefault('objects', {})['grid'] = [{'properties': {'imageHeight': _lit(alto), 'imageWidth': _lit(largo)}}]
    if tipo == 'advancedSlicerVisual':       # botões: uma linha se o espaço é largo, duas se é estreito; sem título repetido
        minimo = 130 if v.get('imagem') or v.get('icone') else 80   # ícone e imagem tomam parte do botão
        colunas = max(2, min(7, int(pos['w'] // minimo)))       # cada botão com pelo menos 80 px (130 com imagem)
        vis['objects'] = {'layout': [{'properties': {'autoGrid': _lit(False), 'rowCount': _int(1 if colunas >= 7 or pos['h'] < 90 else 2),
                                                     'columnCount': _int(colunas), 'cellPadding': _int(6)}}],
                          # o botão é claro por padrão: o texto segue a cor de texto do tema, nunca a do estilo de origem
                          'value': [{'properties': {'fontColor': {'solid': {'color': _lit(m['tema']['texto'])}},
                                                    'fontSize': _lit(12 if pos['h'] < 90 else 14)}}]}
        container['title'] = [{'properties': {'show': _lit(False)}}]
        if pos['h'] < 90:                    # faixa baixa (canto dos filtros): o respiro de 20 px do estilo de origem
            container['padding'] = [{'properties': {k: _lit(2) for k in ('top', 'bottom', 'left', 'right')}}]
            vis['objects']['padding'] = [{'properties': {'paddingSelection': _lit('Custom'), 'topMargin': _int(2),
                                                         'bottomMargin': _int(2), 'leftMargin': _int(6), 'rightMargin': _int(6)},
                                          'selector': {'id': 'default'}}]                      # não deixa o botão cortar o texto
    meta = v.get('meta') and medida(m, v['meta']['nome'])
    if tipo in ('clusteredBarChart', 'clusteredColumnChart', 'lineChart', 'areaChart') and meta and meta.get('tipo') == 'meta':
        vis.setdefault('objects', {})['y1AxisReferenceLine'] = [{'properties': {
            'show': _lit(True), 'displayName': _lit('Meta'), 'value': _lit(float(meta['dax'])),
            'lineColor': {'solid': {'color': _lit('#252423')}}, 'style': _lit('dashed'),
            'dataLabelShow': _lit(True)}, 'selector': {'id': '1'}}]
    if tipo == 'cardVisual':                 # número do cartão novo legível em qualquer estilo de origem
        vis['objects'] = {'value': [{'properties': {'fontSize': _lit(max(16, min(30, round(pos['h'] / 4))))}}]}
    if transparente:                         # o fundo desenhado da página faz o painel (referencias/modelos.md)
        container['background'] = [{'properties': {'show': _lit(False)}}]
    if v.get('dica'):                        # ao passar o mouse, a página de dica no lugar da dica padrão
        container['visualTooltip'] = [{'properties': {'show': _lit(True), 'section': _lit(curto('pagina', v['dica']))}}]
    _tecnicas(m, v, vis, container, pos)
    est = _estilo(m, tipo)
    if est:                                  # a formatação do dashboard de origem do modelo (dicionario/estilos.json)
        objetos = copy.deepcopy(est['objects'])
        objetos.update(vis.get('objects') or {})
        if objetos:
            vis['objects'] = objetos
        cont = copy.deepcopy(est['container'])
        for k, valor in container.items():
            if k == 'title' and cont.get('title'):
                props = dict(cont['title'][0]['properties'])
                props.update(valor[0]['properties'])
                cont['title'] = [{'properties': props}]
            else:
                cont[k] = valor
        vis['visualContainerObjects'] = cont
    return {
        '$schema': f'{S}/visualContainer/2.0.0/schema.json',
        'name': nome,
        'position': {'x': pos['x'], 'y': pos['y'], 'z': ordem * 1000, 'width': pos['w'], 'height': pos['h'],
                     'tabOrder': ordem * 1000},
        'visual': vis,
    }


def _tema(m):
    t = m['tema']
    tema = {'name': 'Deidara', 'dataColors': t['cores'], 'background': t['fundo'], 'foreground': t['texto'],
            'tableAccent': t['cores'][0],
            'textClasses': {'title': {'fontFace': 'Segoe UI Semibold', 'fontSize': 12, 'color': t['texto']},
                            'callout': {'fontFace': 'Segoe UI Semibold', 'fontSize': 32, 'color': t['texto']}}}
    if (m.get('modelo') or 'padrao') != 'padrao':     # página de 1920: letras maiores, como nos modelos de origem
        tema['textClasses'] = {'title': {'fontFace': 'Segoe UI Semibold', 'fontSize': 16, 'color': t['texto']},
                               'callout': {'fontFace': 'Segoe UI Semibold', 'fontSize': 44, 'color': t['texto']},
                               'header': {'fontFace': 'Segoe UI Semibold', 'fontSize': 14, 'color': t['texto']},
                               'label': {'fontFace': 'Segoe UI', 'fontSize': 13, 'color': t['texto']}}
    if t.get('json'):                        # tema de arquivo: vai inteiro (estilos, ícones, predefinições); o
        base = copy.deepcopy(t['json'])      # Deidara só completa o que faltar
        base['name'] = 'Deidara'
        for k, valor in tema.items():
            base.setdefault(k, valor)
        return base
    return tema


def botao(n, destino, nome, ordem):
    """Botão transparente sobre o desenho da navegação, que leva a outra página."""
    return {
        '$schema': f'{S}/visualContainer/2.0.0/schema.json',
        'name': nome,
        'position': {'x': n['x'], 'y': n['y'], 'z': 90000 + ordem, 'width': n['w'], 'height': n['h'],
                     'tabOrder': 90000 + ordem},
        'visual': {
            'visualType': 'actionButton',
            'objects': {'icon': [{'properties': {'shapeType': _lit('blank')}, 'selector': {'id': 'default'}},
                                 {'properties': {'show': _lit(False)}}],
                        'outline': [{'properties': {'show': _lit(False)}}],
                        'fill': [{'properties': {'show': _lit(False)}}]},
            'visualContainerObjects': {'visualLink': [{'properties': {
                'show': _lit(True), 'type': _lit('PageNavigation'), 'navigationSection': _lit(destino),
                'tooltip': _lit(n['rotulo'])}}]},
            'drillFilterOtherVisuals': True},
        'howCreated': 'InsertVisualButton',
    }


def _texto(nome, pos, paragrafos, z, fundo='#FFFFFF'):
    """Caixa de texto (a nota da tela de ajuda)."""
    corpo = []
    for k, t in enumerate(paragrafos):
        estilo = {'fontWeight': 'bold', 'fontSize': '13pt'} if k == 0 else {'fontSize': '11pt'}
        corpo.append({'textRuns': [{'value': t, 'textStyle': dict(estilo, color='#252423')}]})
    return {'$schema': f'{S}/visualContainer/2.0.0/schema.json', 'name': nome,
            'position': {'x': pos['x'], 'y': pos['y'], 'z': z, 'width': pos['w'], 'height': pos['h'], 'tabOrder': z},
            'visual': {'visualType': 'textbox', 'objects': {'general': [{'properties': {'paragraphs': corpo}}]},
                       'visualContainerObjects': {
                           'background': [{'properties': {'show': _lit(True), 'color': {'solid': {'color': _lit(fundo)}},
                                                          'transparency': _lit(4)}}],
                           'border': [{'properties': {'show': _lit(True), 'color': {'solid': {'color': _lit('#118DFF')}},
                                                      'radius': _lit(8)}}]},
                       'drillFilterOtherVisuals': True}}


def _botao_ajuda(nome, pos, destino, icone, rotulo, z):
    return {'$schema': f'{S}/visualContainer/2.0.0/schema.json', 'name': nome,
            'position': {'x': pos['x'], 'y': pos['y'], 'z': z, 'width': pos['w'], 'height': pos['h'], 'tabOrder': z},
            'visual': {'visualType': 'actionButton',
                       'objects': {'icon': [{'properties': {'shapeType': _lit(icone), 'lineWeight': _int(2)},
                                             'selector': {'id': 'default'}}],
                                   'text': [{'properties': {'show': _lit(icone in ('back', 'blank'))}},
                                            {'properties': {'text': _lit(rotulo)}, 'selector': {'id': 'default'}}]},
                       'visualContainerObjects': {'visualLink': [{'properties': {
                           'show': _lit(True), 'type': _lit('PageNavigation'), 'navigationSection': _lit(destino),
                           'tooltip': _lit(rotulo)}}]},
                       'drillFilterOtherVisuals': True},
            'howCreated': 'InsertVisualButton'}




def _fundo_da_pagina(arquivo):
    return {'background': [{'properties': {
        'image': {'image': {'name': _lit(arquivo),
                            'url': {'expr': {'ResourcePackageItem': {'PackageName': 'RegisteredResources', 'PackageType': 1,
                                                                     'ItemName': arquivo}}},
                            'scaling': _lit('Fit')}},
        'transparency': {'expr': {'Literal': {'Value': '0D'}}}}}]}


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
    rel = paginas_do_relatorio(m)
    ordem = [curto('pagina', pg['nome']) for pg in rel]
    imagens, ajudas, tour_pags = [], [], []
    tours = {pg['nome']: pg['tour'] for pg in m['paginas'] if isinstance(pg.get('tour'), str) and medida(m, pg['tour'])}
    visuais = [v for pg in m['paginas'] for v in pg['visuais']]
    for i, pg in enumerate(rel):
        pid = ordem[i]
        pdir = os.path.join(defi, 'pages', pid)
        os.makedirs(pdir, exist_ok=True)
        lay = montar(m, rel, i)
        alto = 720 if lay['w'] <= 1280 else 1080
        page = {'$schema': f'{S}/page/2.0.0/schema.json', 'name': pid, 'displayName': pg['nome'],
                'displayOption': 'FitToWidth' if lay['h'] > alto else 'FitToPage',
                'height': lay['h'], 'width': lay['w']}
        if pg['oculta']:
            page['visibility'] = 'HiddenInViewMode'
        if pg.get('dica'):                     # página de dica (tooltip): aparece ao passar o mouse no visual
            page.update({'type': 'Tooltip', 'displayOption': 'FitToPage',
                         'pageBinding': {'name': curto('dica', pg['nome']), 'type': 'Tooltip'}})
        detalhe = pg.get('detalhe')
        if detalhe:                            # detalhamento: a página abre filtrada pelo item clicado
            campo = {'Column': {'Expression': {'SourceRef': {'Entity': detalhe['tabela']}}, 'Property': detalhe['nome']}}
            filtro = curto('filtro_detalhe', pg['nome'])
            page.update({'type': 'Drillthrough',
                         'pageBinding': {'name': curto('detalhe', pg['nome']), 'type': 'Drillthrough',
                                         'parameters': [{'name': curto('parametro_detalhe', pg['nome']),
                                                         'boundFilter': filtro, 'fieldExpr': campo}]},
                         'filterConfig': {'filters': [{'name': filtro, 'field': campo, 'type': 'Categorical',
                                                       'howCreated': 'Drillthrough'}]}})
        if lay['fundo']:
            arquivo = f'fundo_{pid}.svg'
            with open(os.path.join(tema_dir, arquivo), 'w', encoding='utf-8', newline='\n') as f:
                f.write(lay['fundo'])
            imagens.append(arquivo)
            page['objects'] = _fundo_da_pagina(arquivo)
        gravar_json(os.path.join(pdir, 'page.json'), page)
        if detalhe:                            # o Voltar do detalhamento (volta para a página de onde veio)
            bid = curto('voltar_detalhe', pg['nome'])
            os.makedirs(os.path.join(pdir, 'visuals', bid), exist_ok=True)
            corpo = _botao_ajuda(bid, {'x': lay['w'] - 184, 'y': 16, 'w': 164, 'h': 44}, '', 'back', 'Voltar', 95000)
            corpo['visual']['visualContainerObjects']['visualLink'] = [{'properties': {
                'show': _lit(True), 'type': _lit('Back'), 'tooltip': _lit('Voltar')}}]
            gravar_json(os.path.join(pdir, 'visuals', bid, 'visual.json'), corpo)
        for k, n in enumerate(lay['nav']):
            bid = curto('navegacao', pg['nome'], str(k))
            os.makedirs(os.path.join(pdir, 'visuals', bid), exist_ok=True)
            gravar_json(os.path.join(pdir, 'visuals', bid, 'visual.json'), botao(n, ordem[n['alvo']], bid, k))
        if pg.get('ajuda'):                    # tela de ajuda: o botão "?" leva a uma página escondida com as notas
            aid = curto('ajuda', pg['nome'])
            ajudas.append((pg, lay, aid, pid, page.get('objects')))
            bid = curto('botao_ajuda', pg['nome'])
            os.makedirs(os.path.join(pdir, 'visuals', bid), exist_ok=True)
            gravar_json(os.path.join(pdir, 'visuals', bid, 'visual.json'),
                        _botao_ajuda(bid, {'x': lay['w'] - 64, 'y': lay['h'] - 104, 'w': 44, 'h': 44}, aid, 'help',
                                     'Como ler esta página', 95000))
        tour = None if pg['oculta'] else tours.get(pg['nome'])
        if tour:                               # tour guiado: o botão leva à página escondida com o tour por cima
            tid = curto('tour', pg['nome'])
            tour_pags.append((pg, lay, tid, pid, page.get('objects'), tour))
            bid = curto('botao_tour', pg['nome'])
            os.makedirs(os.path.join(pdir, 'visuals', bid), exist_ok=True)
            x = lay['w'] - (248 if pg.get('ajuda') else 184)
            gravar_json(os.path.join(pdir, 'visuals', bid, 'visual.json'),
                        _botao_ajuda(bid, {'x': x, 'y': lay['h'] - 104, 'w': 164, 'h': 44}, tid, 'blank', '▶ Tour guiado',
                                     95001))
        usados = set()
        posicoes = [(dict(v, titulo='') if id(v) in lay['sem_titulo'] else v, p) for v, p in lay['posicoes']]
        for k, (v, pos) in enumerate(posicoes):
            vid = v.get('id') or curto('visual', pg['nome'], v['tipo'], v['titulo'] or '')
            n = 1
            while vid in usados:              # dois visuais iguais na página
                n += 1
                vid = curto('visual', pg['nome'], v['tipo'], v['titulo'] or '', str(n))
            usados.add(vid)
            vdir = os.path.join(pdir, 'visuals', vid)
            os.makedirs(vdir, exist_ok=True)
            gravar_json(os.path.join(vdir, 'visual.json'), visual(m, v, pos, vid, k, transparente=bool(lay['fundo'])))
    for pg, lay, aid, pid, fundo in ajudas:
        adir = os.path.join(defi, 'pages', aid)
        os.makedirs(adir, exist_ok=True)
        page = {'$schema': f'{S}/page/2.0.0/schema.json', 'name': aid, 'displayName': f'Ajuda · {pg["nome"]}',
                'displayOption': 'FitToPage', 'height': lay['h'], 'width': lay['w'], 'visibility': 'HiddenInViewMode'}
        if fundo:
            page['objects'] = fundo
        gravar_json(os.path.join(adir, 'page.json'), page)
        for k, (v, pos) in enumerate(lay['posicoes']):
            tid = curto('nota', pg['nome'], str(k))
            os.makedirs(os.path.join(adir, 'visuals', tid), exist_ok=True)
            gravar_json(os.path.join(adir, 'visuals', tid, 'visual.json'), _texto(tid, pos, nota_de_ajuda(m, v), k * 1000))
        vid = curto('voltar', pg['nome'])
        os.makedirs(os.path.join(adir, 'visuals', vid), exist_ok=True)
        gravar_json(os.path.join(adir, 'visuals', vid, 'visual.json'),
                    _botao_ajuda(vid, {'x': lay['w'] - 184, 'y': 16, 'w': 164, 'h': 44}, pid, 'back', 'Voltar', 95000))
        ordem.append(aid)
    for pg, lay, tid, pid, fundo, nome_tour in tour_pags:
        tdir = os.path.join(defi, 'pages', tid)
        os.makedirs(tdir, exist_ok=True)
        page = {'$schema': f'{S}/page/2.0.0/schema.json', 'name': tid, 'displayName': f'Tour · {pg["nome"]}',
                'displayOption': 'FitToPage', 'height': lay['h'], 'width': lay['w'], 'visibility': 'HiddenInViewMode'}
        if fundo:
            page['objects'] = fundo
        gravar_json(os.path.join(tdir, 'page.json'), page)
        for k, (v, pos) in enumerate(lay['posicoes']):  # os mesmos visuais, embaixo do tour
            vid = curto('tour_visual', pg['nome'], str(k))
            os.makedirs(os.path.join(tdir, 'visuals', vid), exist_ok=True)
            gravar_json(os.path.join(tdir, 'visuals', vid, 'visual.json'),
                        visual(m, v, pos, vid, k, transparente=bool(lay['fundo'])))
        md = medida(m, nome_tour)
        v_tour = {'tipo': 'html', 'titulo': '', 'id': None, 'categoria': None, 'legenda': None, 'campos': [],
                  'linhas': [], 'colunas': [], 'meta': None,
                  'valores': [{'tipo': 'medida', 'tabela': md['tabela'], 'nome': md['nome'], 'formato': None}]}
        hid = curto('tour_html', pg['nome'])
        os.makedirs(os.path.join(tdir, 'visuals', hid), exist_ok=True)
        corpo = visual(m, v_tour, {'x': 0, 'y': 0, 'w': lay['w'], 'h': lay['h']}, hid, 90, transparente=True)
        corpo['visual']['visualContainerObjects']['padding'] = [{'properties': {k: _lit(0) for k in
                                                                                ('top', 'bottom', 'left', 'right')}}]
        gravar_json(os.path.join(tdir, 'visuals', hid, 'visual.json'), corpo)
        vid = curto('voltar_tour', pg['nome'])
        os.makedirs(os.path.join(tdir, 'visuals', vid), exist_ok=True)
        gravar_json(os.path.join(tdir, 'visuals', vid, 'visual.json'),
                    _botao_ajuda(vid, {'x': lay['w'] - 184, 'y': 16, 'w': 164, 'h': 44}, pid, 'back', 'Voltar', 95000))
        ordem.append(tid)
    terceiros = sorted({TIPOS_VISUAL[v['tipo']] for v in visuais if v['tipo'] in ('html', 'vegalite')}
                       | ({TIPOS_VISUAL['html']} if tour_pags else set()))
    gravar_json(os.path.join(defi, 'report.json'), {
        '$schema': f'{S}/report/1.0.0/schema.json',
        'themeCollection': {'customTheme': {'name': 'Deidara.json', 'reportVersionAtImport': '5.59',
                                            'type': 'RegisteredResources'}},
        'layoutOptimization': 'None',
        'resourcePackages': [{'name': 'RegisteredResources', 'type': 'RegisteredResources',
                              'items': [{'name': 'Deidara.json', 'path': 'Deidara.json', 'type': 'CustomTheme'}]
                              + [{'name': a, 'path': a, 'type': 'Image'} for a in imagens]}],
        'settings': {'useStylableVisualContainerHeader': True, 'defaultDrillFilterOtherVisuals': True,
                     'allowChangeFilterTypes': True, 'useEnhancedTooltips': True},
        **({'publicCustomVisuals': terceiros} if terceiros else {}),
    })
    gravar_json(os.path.join(defi, 'pages', 'pages.json'), {
        '$schema': f'{S}/pagesMetadata/1.0.0/schema.json', 'pageOrder': ordem, 'activePageName': ordem[0]})
    return raiz
