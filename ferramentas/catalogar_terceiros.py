#!/usr/bin/env python3
"""
Refaz terceiros/catalogo.json: um item por modelo Deneb, por pacote de funções DAX (daxlib), por modelo de
calendário (Bravo) e por coleção de SVG, com o que cada um pede e etiquetas em português para a busca
(`deidara.py galeria cascata`).

Uso:
    python3 ferramentas/catalogar_terceiros.py
"""

import glob
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TERCEIROS = os.path.join(RAIZ, 'terceiros')

# palavra em inglês do modelo -> como o time procura
ETIQUETAS = {
    'waterfall': 'cascata ponte variação explica', 'sparkline': 'minigráfico tendência', 'trend': 'tendência minigráfico',
    'bullet': 'meta alvo bala atingimento', 'target': 'meta alvo atingimento', 'progress': 'progresso meta',
    'viz.line': 'minigráfico tendência', 'viz.area': 'minigráfico área', 'viz.bars': 'minigráfico barras',
    'heatmap': 'mapa de calor intensidade', 'heat-map': 'mapa de calor', 'calendar': 'calendário dia',
    'slope': 'inclinação antes e depois comparação', 'bump': 'ranking no tempo posição', 'ranking': 'ranking posição',
    'boxplot': 'caixa distribuição quartil', 'violin': 'violino distribuição', 'histogram': 'histograma distribuição',
    'distribution': 'distribuição', 'jitter': 'jitter distribuição pontos', 'beeswarm': 'enxame distribuição',
    'treemap': 'árvore parte do todo', 'waffle': 'waffle parte do todo percentual', 'gridplot': 'waffle grade',
    'part-to-whole': 'parte do todo participação', 'pie': 'pizza', 'donut': 'rosca', 'sankey': 'fluxo sankey',
    'gantt': 'cronograma projeto', 'timeline': 'linha do tempo cronograma', 'variance': 'variação desvio',
    'deviation': 'desvio variação', 'diverging': 'divergente desvio', 'small': 'múltiplos pequenos',
    'smallmultiple': 'múltiplos pequenos', 'lollipop': 'pirulito', 'radar': 'radar', 'funnel': 'funil conversão',
    'choropleth': 'mapa região', 'map': 'mapa', 'spatial': 'mapa território', 'kpi': 'kpi indicador cartão',
    'ibcs': 'ibcs real orçado ano anterior variação', 'pill': 'pílula status', 'chips': 'selo pílula',
    'gauge': 'medidor velocímetro', 'mekko': 'marimekko', 'marimekko': 'marimekko', 'sixsigma': 'seis sigma controle',
    'significant': 'significância fora da curva', 'outlier': 'fora da curva', 'benford': 'benford auditoria fraude',
    'abc': 'curva abc pareto classificação', 'rfm': 'rfm clientes segmentação', 'moving': 'média móvel',
    'calendar-table': 'calendário', 'holiday': 'feriado dia útil', 'timeintelligence': 'inteligência de tempo',
    'parliament': 'parlamento', 'population': 'pirâmide etária', 'pyramid': 'pirâmide', 'network': 'rede',
    'org': 'organograma', 'tree': 'árvore organograma', 'pictogram': 'pictograma', 'symbol': 'símbolo',
    'column': 'colunas', 'bar': 'barras', 'line': 'linha', 'area': 'área', 'scatter': 'dispersão',
    'bubble': 'bolha', 'connected': 'dispersão conectada', 'candlestick': 'candle', 'surplus': 'superávit déficit',
    'color': 'cor', 'colour': 'cor', 'alttext': 'texto alternativo acessibilidade', 'contrast': 'contraste',
    'flag': 'bandeira país', 'country': 'país mapa', 'stats': 'estatística resumo', 'finance': 'finanças',
}
IMAGEM = re.compile(r'svg|ibcs|waterfall|progress|target|kpi|html|flag', re.I)


def _etiquetas(*textos):
    t = ' '.join(x or '' for x in textos).lower()
    return ' '.join(sorted({v for k, v in ETIQUETAS.items() if k in t}))


def _deneb():
    out = []
    for arq in sorted(glob.glob(os.path.join(TERCEIROS, '**', '*.json'), recursive=True)):
        try:
            with open(arq, encoding='utf-8-sig') as f:
                d = json.load(f)
        except (ValueError, UnicodeDecodeError):
            continue
        if not isinstance(d, dict) or not ('usermeta' in d or str(d.get('$schema', '')).startswith('https://vega')):
            continue
        rel = os.path.relpath(arq, TERCEIROS).replace('\\', '/')
        um = d.get('usermeta') or {}
        info = um.get('information') or {}
        prov = (um.get('deneb') or {}).get('provider') or ('vegaLite' if 'vega-lite' in str(d.get('$schema')) else 'vega')
        ident = re.sub(r'(\.deneb-template)?\.json$', '', rel)
        nome = info.get('name') or os.path.splitext(os.path.basename(os.path.dirname(arq) if
                                                                     os.path.basename(arq).lower().startswith('spec')
                                                                     else arq))[0]
        out.append({'tipo': 'deneb', 'id': ident, 'nome': nome, 'descricao': info.get('description') or '',
                    'autor': info.get('author') or '', 'provider': prov, 'fonte': rel.split('/')[0],
                    'caminho': f'terceiros/{rel}',
                    'campos': [{k: c.get(k) for k in ('key', 'name', 'description', 'type', 'kind')}
                               for c in um.get('dataset') or []],
                    'pronto_para_usar': bool(um.get('dataset')),
                    'previa': bool(info.get('previewImageBase64PNG')),
                    'etiquetas': _etiquetas(ident, nome, info.get('description'))})
    return out


def _daxlib():
    out = []
    for man in sorted(glob.glob(os.path.join(TERCEIROS, 'daxlib', 'packages', '*', '*', '*', 'manifest.daxlib'))):
        with open(man, encoding='utf-8-sig') as f:
            m = json.load(f)
        lib = os.path.join(os.path.dirname(man), 'lib', 'functions.tmdl')
        funcoes = []
        if os.path.exists(lib):
            with open(lib, encoding='utf-8-sig') as f:
                texto = f.read()
            for doc, nome in re.findall(r"((?:^///[^\n]*\n)*)^FUNCTION\s+'?([\w.]+)'?\s*=", texto, re.M | re.I):
                primeira = next((x[3:].strip() for x in doc.splitlines() if x[3:].strip()), '')
                funcoes.append({'nome': nome, 'sobre': primeira})
        rel = os.path.relpath(os.path.dirname(man), TERCEIROS).replace('\\', '/')
        out.append({'tipo': 'funcoes_dax', 'id': m['id'], 'nome': m['id'], 'versao': m.get('version'),
                    'descricao': m.get('description') or '', 'autor': m.get('authors') or '', 'fonte': 'daxlib',
                    'caminho': f'terceiros/{rel}/lib/functions.tmdl', 'funcoes': funcoes,
                    'imagem': bool(IMAGEM.search(m['id'] + ' ' + (m.get('tags') or ''))),
                    'etiquetas': _etiquetas(m['id'], m.get('description'), m.get('tags'),
                                            ' '.join(f['nome'] for f in funcoes))})
    return out


def _bravo():
    out = []
    for arq in sorted(glob.glob(os.path.join(TERCEIROS, 'bravo-calendario', '*.json'))):
        nome = os.path.splitext(os.path.basename(arq))[0]
        with open(arq, encoding='utf-8-sig') as f:
            d = json.load(f)
        desc = d.get('Description') or d.get('description') or '' if isinstance(d, dict) else ''
        paises = sorted({h.get('IsoCountry') for h in (d.get('Holidays') or [])}) if isinstance(d, dict) else []
        out.append({'tipo': 'calendario', 'id': f'bravo-calendario/{nome}', 'nome': nome, 'descricao': desc,
                    'autor': 'SQLBI', 'fonte': 'bravo-calendario', 'caminho': f'terceiros/bravo-calendario/{nome}.json',
                    'paises': paises, 'etiquetas': _etiquetas(nome, desc, 'calendar holiday' if paises else 'calendar')})
    return out


def _svg():
    pasta = os.path.join(TERCEIROS, 'powerbi-svg')
    svgs = glob.glob(os.path.join(pasta, '**', '*.svg'), recursive=True)
    return [{'tipo': 'svg', 'id': 'powerbi-svg', 'nome': 'Fronteiras de países e bandeiras (SVG)',
             'descricao': f'{len(svgs)} arquivos SVG e data/flags.json, para mapa e tabela por país',
             'autor': 'Jurgen Folz', 'fonte': 'powerbi-svg', 'caminho': 'terceiros/powerbi-svg',
             'etiquetas': _etiquetas('svg country flag map')}] if svgs else []


def main():
    itens = _deneb() + _daxlib() + _bravo() + _svg()
    dados = {'formato': 'deidara-terceiros/1',
             'sobre': 'Conteúdo aberto (MIT) trazido para o Deidara; licença e origem em terceiros/<fonte>/. '
                      'Refaça com ferramentas/catalogar_terceiros.py.',
             'itens': itens}
    with open(os.path.join(TERCEIROS, 'catalogo.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)
        f.write('\n')
    por = {}
    for x in itens:
        por[x['tipo']] = por.get(x['tipo'], 0) + 1
    print('Catálogo: ' + ', '.join(f'{n} {t}' for t, n in sorted(por.items())))
    return 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
