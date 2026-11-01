"""
C0 · leitura: o que existe, em qualquer das formas que a pessoa tiver.

- DAX colado (.dax/.txt, ou o texto direto): "Nome = expressão", "[Nome] =" em blocos, ou o DEFINE MEASURE
  'Tabela'[Nome] = ... da Exibição de consulta DAX e do DAX Studio;
- pasta de um projeto Power BI (.pbip, a pasta .SemanticModel ou a definition/ dela): o TMDL inteiro (tabelas,
  colunas, colunas e tabelas calculadas, medidas, relacionamentos, partições, expressões) e, se houver, o
  relatório em PBIR (páginas e visuais);
- o resultado da receita DAX (`deidara.py receita dax`), que traz também as medidas e as colunas calculadas.

Tudo vira o mesmo "legado": {'origem', 'tabelas', 'medidas', 'relacoes', 'expressoes', 'paginas', 'avisos'}.
Só estrutura: nenhuma linha de dado é lida.
"""

import glob
import json
import os
import re
from tecnicas.luneta.receitas import detectar_receita, ler_colado

NOME = r"('(?:[^']|'')+'|[^\s'=.\[\]]+)"


def _nome(n):
    n = (n or '').strip()
    return n[1:-1].replace("''", "'") if len(n) >= 2 and n[0] == n[-1] == "'" else n


def novo(origem):
    return {'origem': origem, 'tabelas': {}, 'medidas': {}, 'relacoes': [], 'expressoes': {}, 'paginas': [],
            'avisos': [], 'data_automatica': False, 'funcoes': []}


def _tabela(leg, nome):
    return leg['tabelas'].setdefault(nome, {'descricao': '', 'colunas': {}, 'calculada': None, 'particao': None,
                                            'particao_tipo': None, 'oculta': False, 'calendario': False,
                                            'grupo_calculo': False})


# =================================================================== DAX colado
_DEFINE = re.compile(r"^\s*MEASURE\s+" + NOME + r"\s*\[((?:[^\]]|\]\])+)\]\s*=", re.I | re.M)
_BLOCO = re.compile(r"^(?:\[((?:[^\]]|\]\])+)\]|'((?:[^']|'')+)'|([A-Za-zÀ-ÿ_][\wÀ-ÿ .%/&()\-]*?))\s*(?::=|=)(?!=)",
                    re.M)


def de_dax(texto, nome_padrao='Medida'):
    """Medidas de um texto DAX. Aceita o DEFINE MEASURE da consulta DAX e blocos "Nome = expressão" (um nome no
    começo da linha abre a medida seguinte); sem nome nenhum, o texto inteiro é uma medida só."""
    leg = novo('dax')
    texto = texto.replace('\r\n', '\n').strip()
    texto = re.sub(r'^\s*//[^\n]*$', '', texto, flags=re.M).strip() if not re.search(r'=', texto) else texto
    achados = list(_DEFINE.finditer(texto))
    if achados:
        for i, mt in enumerate(achados):
            fim = achados[i + 1].start() if i + 1 < len(achados) else len(texto)
            corpo = texto[mt.end():fim]
            corpo = re.split(r'^\s*(EVALUATE|DEFINE|VAR\s+\w+\s*=\s*\n)', corpo, maxsplit=1, flags=re.I | re.M)[0] \
                if re.search(r'^\s*EVALUATE', corpo, re.I | re.M) else corpo
            leg['medidas'][mt.group(2).replace(']]', ']')] = _medida(_nome(mt.group(1)), corpo)
        return leg
    blocos = [m for m in _BLOCO.finditer(texto) if _comeca_medida(texto, m)]
    if not blocos:
        if re.sub(r'//[^\n]*|--[^\n]*', '', texto).strip():
            leg['medidas'][nome_padrao] = _medida(None, texto)
        return leg
    for i, mt in enumerate(blocos):
        fim = blocos[i + 1].start() if i + 1 < len(blocos) else len(texto)
        nome = (mt.group(1) or '').replace(']]', ']') or _nome(f"'{mt.group(2)}'" if mt.group(2) else '') \
            or mt.group(3).strip()
        if texto[mt.end():fim].strip():          # "Nome =" sem fórmula não é medida
            leg['medidas'][nome] = _medida(None, texto[mt.end():fim])
    return leg


_PALAVRAS_DAX = {'VAR', 'RETURN', 'IF', 'SWITCH', 'CALCULATE', 'EVALUATE', 'DEFINE', 'ORDER', 'TRUE', 'FALSE'}


def _comeca_medida(texto, mt):
    """O "Nome =" está no começo de uma linha e não é um VAR nem uma comparação dentro de outra medida."""
    nome = (mt.group(3) or '').strip()
    if mt.group(3) and (nome.split()[0].upper() in _PALAVRAS_DAX or nome.upper().startswith('VAR ')):
        return False
    antes = texto[:mt.start()].rstrip()
    return not antes or antes.endswith(('\n', ')')) or texto[mt.start() - 1:mt.start()] in ('\n', '')


def _medida(tabela, corpo, **extra):
    dax = re.sub(r'\n[ \t]*//\s*(tabela|formato|pasta):[^\n]*', '', corpo).strip().rstrip(',')
    dax = re.sub(r'^```\s*|\s*```$', '', dax).strip()
    return {'tabela': tabela, 'dax': dax, 'descricao': extra.get('descricao', ''), 'formato': extra.get('formato', ''),
            'pasta': extra.get('pasta', ''), 'oculta': bool(extra.get('oculta'))}


# ======================================================================= TMDL
def _recuo(linha):
    return len(linha) - len(linha.lstrip('\t'))


def _expressao(linhas, i, base, primeira):
    """A expressão de um objeto TMDL: o que vem depois do "=" e as linhas mais recuadas que as propriedades.
    Devolve (texto, próximo índice)."""
    partes = [primeira] if primeira.strip() else []
    cerca = primeira.strip() == '```'
    if cerca:
        partes = []
    j = i + 1
    while j < len(linhas):
        l = linhas[j]
        if cerca:
            if l.strip() == '```':
                return '\n'.join(partes).strip('\n'), j + 1
            partes.append(l)
            j += 1
            continue
        if l.strip() and _recuo(l) <= base + 1:
            break
        partes.append(l)
        j += 1
    mn = min((_recuo(x) for x in partes[1:] if x.strip()), default=0)
    texto = '\n'.join([partes[0].strip()] + [x[mn:] for x in partes[1:]] if partes else [])
    return texto.strip('\n').strip(), j


def _propriedades(linhas, j, base):
    """As propriedades (nível base+1) de um objeto: {nome: valor}, até o próximo objeto do mesmo nível."""
    props = {}
    while j < len(linhas):
        l = linhas[j]
        if l.strip() and _recuo(l) <= base:
            break
        if _recuo(l) == base + 1 and l.strip() and not l.strip().startswith('///'):
            mt = re.match(r'^\s*(\w+)\s*(?::\s*(.*))?$', l)
            if mt and not re.match(r'^\s*(annotation|changedProperty|extendedProperty)\b', l):
                props[mt.group(1)] = (mt.group(2) or 'true').strip()
            elif re.match(r'^\s*(column|measure|partition|hierarchy|calculationGroup|calculationItem)\b', l):
                break
        j += 1
    return props, j


def de_tmdl(pasta):
    """O modelo semântico de um projeto: aceita a pasta do .pbip, a .SemanticModel ou a definition/."""
    defi = _definition(pasta)
    leg = novo('pbip')
    if not defi:
        raise ValueError(f'{pasta}: não achei a pasta definition/ de um modelo em TMDL (.SemanticModel)')
    for arq in sorted(glob.glob(os.path.join(defi, 'tables', '*.tmdl'))):
        _ler_tabela(leg, _ler(arq))
    rel = os.path.join(defi, 'relationships.tmdl')
    if os.path.exists(rel):
        _ler_relacoes(leg, _ler(rel))
    fn = os.path.join(defi, 'functions.tmdl')         # funções DAX definidas pelo usuário (daxlib e afins)
    if os.path.exists(fn):
        leg['funcoes'] = [_nome(x) for x in re.findall(r'^function\s+' + NOME + r'\s*=', '\n'.join(_ler(fn)),
                                                        re.M | re.I)]
    exp = os.path.join(defi, 'expressions.tmdl')
    if os.path.exists(exp):
        linhas = _ler(exp)
        for i, l in enumerate(linhas):
            mt = re.match(r'^expression\s+' + NOME + r'\s*=\s*(.*)$', l)
            if mt:
                leg['expressoes'][_nome(mt.group(1))] = _expressao(linhas, i, 0, mt.group(2))[0]
    leg['data_automatica'] = any(n.startswith(('LocalDateTable_', 'DateTableTemplate_')) for n in leg['tabelas'])
    for n in [n for n in leg['tabelas'] if n.startswith(('LocalDateTable_', 'DateTableTemplate_'))]:
        del leg['tabelas'][n]
    leg['relacoes'] = [r for r in leg['relacoes'] if r['de'] in leg['tabelas'] and r['para'] in leg['tabelas']]
    rep = _relatorio(pasta, defi)
    if rep:
        leg['paginas'] = _ler_relatorio(rep, leg)
    elif glob.glob(os.path.join(os.path.dirname(os.path.dirname(defi)), '*.Report', 'report.json')):
        leg['avisos'].append('o relatório está no formato antigo (report.json), que o C0 não lê: no Power BI Desktop, '
                             'ligue o formato PBIR (Opções > Recursos em versão prévia, se pedir) e salve o projeto de novo')
    for n, t in leg['tabelas'].items():
        if t.get('particao_tipo') == 'entity':
            leg['avisos'].append(f'tabela {n} é Direct Lake: o Deidara gera o projeto em Import; aponte a origem dela '
                                 '(view SQL ou consulta) no catálogo antes de gerar')
    return leg


def _definition(pasta):
    pasta = os.path.abspath(pasta)
    if os.path.isfile(pasta) and pasta.lower().endswith('.pbip'):
        pasta = os.path.dirname(pasta)
    candidatos = [pasta, os.path.join(pasta, 'definition')] + glob.glob(os.path.join(pasta, '*.SemanticModel', 'definition'))
    return next((c for c in candidatos if os.path.isdir(os.path.join(c, 'tables'))), None)


def _relatorio(pasta, defi):
    raiz = os.path.dirname(os.path.dirname(defi))
    achados = glob.glob(os.path.join(raiz, '*.Report', 'definition'))
    return achados[0] if achados else None


def _ler(arq):
    with open(arq, encoding='utf-8-sig') as f:
        return f.read().replace('\r\n', '\n').split('\n')


def _ler_tabela(leg, linhas):
    doc, t = [], None
    i = 0
    while i < len(linhas):
        l = linhas[i]
        s = l.strip()
        if s.startswith('///'):
            doc.append(s[3:].strip())
            i += 1
            continue
        mt = re.match(r'^table\s+' + NOME + r'\s*$', l)
        if mt:
            t = _tabela(leg, _nome(mt.group(1)))
            t['descricao'] = ' '.join(doc)
            props, _ = _propriedades(linhas, i + 1, 0)
            t['oculta'] = 'isHidden' in props
            t['calendario'] = props.get('dataCategory', '').lower() == 'time'
            doc, i = [], i + 1
            continue
        if t is None:
            i += 1
            continue
        mt = re.match(r'^\tmeasure\s+' + NOME + r'\s*=\s*(.*)$', l)
        if mt:
            dax, j = _expressao(linhas, i, 1, mt.group(2))
            props, j = _propriedades(linhas, j, 1)
            nome_t = next(n for n, x in leg['tabelas'].items() if x is t)
            leg['medidas'][_nome(mt.group(1))] = _medida(
                nome_t, dax, descricao=' '.join(doc), formato=props.get('formatString', ''),
                pasta=props.get('displayFolder', ''), oculta='isHidden' in props)
            doc, i = [], j
            continue
        mt = re.match(r'^\tcolumn\s+' + NOME + r'\s*(?:=\s*(.*))?$', l)
        if mt:
            expr, j = (_expressao(linhas, i, 1, mt.group(2)) if mt.group(2) is not None else (None, i + 1))
            props, j = _propriedades(linhas, j, 1)
            t['colunas'][_nome(mt.group(1))] = {'tipo': props.get('dataType', ''), 'calculada': expr,
                                                'oculta': 'isHidden' in props, 'descricao': ' '.join(doc),
                                                'chave': 'isKey' in props,
                                                'categoria': props.get('dataCategory', ''),
                                                'resumo': props.get('summarizeBy', '')}
            doc, i = [], j
            continue
        mt = re.match(r'^\tpartition\s+' + NOME + r'\s*=\s*(\w+)', l)
        if mt:
            tipo = mt.group(2).lower()
            props, j = _propriedades(linhas, i + 1, 1)
            k = next((x for x in range(i + 1, j) if re.match(r'^\t\tsource\s*=', linhas[x])), None)
            fonte = _expressao(linhas, k, 2, re.sub(r'^\t\tsource\s*=\s*', '', linhas[k]))[0] if k is not None else ''
            t['particao_tipo'] = tipo
            if tipo == 'calculated':
                t['calculada'] = fonte
            elif tipo == 'calculationgroup':
                t['grupo_calculo'] = True
            else:
                t['particao'] = t['particao'] or fonte
            doc, i = [], j
            continue
        if re.match(r'^\tcalculationGroup\b', l):
            t['grupo_calculo'] = True
        doc = [] if s and not s.startswith('///') else doc
        i += 1


def _ler_relacoes(leg, linhas):
    atual = None
    for l in linhas + ['relationship fim']:
        if re.match(r'^relationship\b', l):
            if atual and atual.get('de') and atual.get('para'):
                leg['relacoes'].append(atual)
            atual = {'ativa': True, 'cruzado': 'oneDirection', 'de_card': 'many', 'para_card': 'one'}
            continue
        mt = re.match(r'^\t(fromColumn|toColumn):\s*' + NOME + r'\.' + NOME + r'\s*$', l)
        if mt and atual is not None:
            lado = 'de' if mt.group(1) == 'fromColumn' else 'para'
            atual[lado], atual[lado + '_coluna'] = _nome(mt.group(2)), _nome(mt.group(3))
            continue
        mt = re.match(r'^\t(isActive|crossFilteringBehavior|fromCardinality|toCardinality):\s*(\S+)', l)
        if mt and atual is not None:
            chave = {'isActive': 'ativa', 'crossFilteringBehavior': 'cruzado', 'fromCardinality': 'de_card',
                     'toCardinality': 'para_card'}[mt.group(1)]
            atual[chave] = (mt.group(2).lower() != 'false') if chave == 'ativa' else mt.group(2)


# =========================================================== relatório (PBIR)
VISUAIS = {'card': 'cartao', 'cardVisual': 'cartoes', 'multiRowCard': 'cartoes', 'kpi': 'cartao',
           'clusteredBarChart': 'barras', 'barChart': 'barras', 'stackedBarChart': 'barras',
           'clusteredColumnChart': 'colunas', 'columnChart': 'colunas', 'stackedColumnChart': 'colunas',
           'lineChart': 'linha', 'areaChart': 'area', 'stackedAreaChart': 'area', 'donutChart': 'rosca',
           'pieChart': 'rosca', 'tableEx': 'tabela', 'pivotTable': 'matriz', 'slicer': 'segmentador',
           'advancedSlicerVisual': 'botoes', 'gauge': 'medidor', 'scatterChart': 'dispersao',
           'decompositionTreeVisual': 'decomposicao', 'azureMap': 'mapa', 'map': 'mapa',
           'lineClusteredColumnComboChart': 'colunas', 'lineStackedColumnComboChart': 'colunas'}


def _campos(query):
    out = []
    for papel, bloco in ((query or {}).get('queryState') or {}).items():
        for pr in (bloco or {}).get('projections') or []:
            f = pr.get('field') or {}
            for tipo in ('Measure', 'Column', 'Aggregation'):
                if tipo in f:
                    x = f[tipo]
                    if tipo == 'Aggregation':
                        x = (x.get('Expression') or {}).get('Column') or {}
                    ent = (((x.get('Expression') or {}).get('SourceRef')) or {}).get('Entity')
                    if ent and x.get('Property'):
                        out.append({'papel': papel, 'tipo': 'medida' if tipo == 'Measure' else 'coluna',
                                    'tabela': ent, 'nome': x['Property'], 'agregada': tipo == 'Aggregation'})
    return out


def _ler_relatorio(defi, leg):
    paginas = []
    ordem = []
    pj = os.path.join(defi, 'pages', 'pages.json')
    if os.path.exists(pj):
        with open(pj, encoding='utf-8-sig') as f:
            ordem = json.load(f).get('pageOrder') or []
    pastas = sorted(glob.glob(os.path.join(defi, 'pages', '*', 'page.json')),
                    key=lambda p: ordem.index(os.path.basename(os.path.dirname(p)))
                    if os.path.basename(os.path.dirname(p)) in ordem else 999)
    for pj in pastas:
        with open(pj, encoding='utf-8-sig') as f:
            pg = json.load(f)
        vis = []
        for vj in sorted(glob.glob(os.path.join(os.path.dirname(pj), 'visuals', '*', 'visual.json'))):
            with open(vj, encoding='utf-8-sig') as f:
                v = json.load(f)
            corpo = v.get('visual') or {}
            tipo = corpo.get('visualType', '')
            pos = v.get('position') or {}
            vis.append({'tipo_pbi': tipo, 'tipo': VISUAIS.get(tipo), 'campos': _campos(corpo.get('query')),
                        'x': pos.get('x', 0), 'y': pos.get('y', 0)})
        vis.sort(key=lambda x: (round(x['y'] / 40), x['x']))
        paginas.append({'nome': pg.get('displayName') or pg.get('name'), 'oculta': pg.get('visibility') == 'HiddenInViewMode',
                        'visuais': vis})
    return paginas


# ========================================================= resultado da receita
def de_receita(linhas):
    """As linhas do resultado da receita DAX (secao, tabela, coluna, tipo, descricao, extra, expressao)."""
    leg = novo('receita')
    for l in linhas:
        sec, tab = l.get('secao'), l.get('tabela') or ''
        if tab.startswith(('LocalDateTable_', 'DateTableTemplate_')):
            leg['data_automatica'] = True
            continue
        if sec == 'tabela':
            t = _tabela(leg, tab)
            t['descricao'], t['oculta'] = l.get('descricao', ''), l.get('extra') == 'oculta'
            if l.get('extra') == 'calculada':
                t['calculada'] = l.get('expressao') or '(tabela calculada)'
        elif sec == 'coluna':
            if (l.get('coluna') or '').startswith('RowNumber-'):
                continue
            _tabela(leg, tab)['colunas'][l['coluna']] = {
                'tipo': l.get('tipo', ''), 'calculada': (l.get('expressao') or '(coluna calculada)')
                if l.get('extra') == 'calculada' else None, 'oculta': l.get('extra') == 'oculta',
                'descricao': l.get('descricao', ''), 'chave': False, 'categoria': '', 'resumo': ''}
        elif sec == 'medida':
            fmt, _, pasta = (l.get('extra') or '').partition('|')
            leg['medidas'][l.get('coluna') or ''] = _medida(tab, l.get('expressao', ''), descricao=l.get('descricao', ''),
                                                            formato=fmt, pasta=pasta,
                                                            oculta=l.get('tipo') == 'oculta')
        elif sec == 'relacao':
            mt = re.fullmatch(r'(.*)\[(.*)\]', l.get('descricao', ''))
            if mt:
                de_c, para_c = (l.get('tipo') or 'many>one').split('>', 1) if '>' in (l.get('tipo') or '') else ('many', 'one')
                leg['relacoes'].append({'de': tab, 'de_coluna': l.get('coluna'), 'para': mt.group(1),
                                        'para_coluna': mt.group(2), 'ativa': l.get('extra') != 'inativa',
                                        'cruzado': l.get('cruzado') or 'oneDirection',
                                        'de_card': de_c.lower(), 'para_card': para_c.lower()})
        elif sec == 'particao':
            t = _tabela(leg, tab)
            t['particao'] = t['particao'] or l.get('expressao')
        elif sec == 'expressao':
            leg['expressoes'][tab] = l.get('expressao', '')
        elif sec == 'calendario' and tab in leg['tabelas']:
            leg['tabelas'][tab]['calendario'] = True
    return leg


# ===================================================================== entrada
def ler(alvo):
    """Lê o que a pessoa passou: pasta de projeto, arquivo .pbip, resultado da receita, arquivo DAX ou o texto."""
    if os.path.isdir(alvo) or (os.path.isfile(alvo) and alvo.lower().endswith('.pbip')):
        return de_tmdl(alvo)
    if os.path.isfile(alvo):
        with open(alvo, 'rb') as f:
            inicio = f.read(4096)
        if alvo.lower().endswith(('.pbix', '.pbit')) or inicio[:2] == b'PK' or b'\x00' in inicio:
            raise ValueError(f'{alvo}: o .pbix é um arquivo binário, que o C0 não abre. Duas saídas: no Power BI Desktop, '
                             'Arquivo > Salvar como > Projeto do Power BI (.pbip) e passe a pasta; ou rode a receita '
                             '(`deidara.py receita dax`) na Exibição de consulta DAX e passe o resultado colado')
        try:
            cab, linhas = ler_colado(alvo)
            if detectar_receita(cab) == 'dax':
                return de_receita(linhas)
        except (ValueError, UnicodeDecodeError):
            pass
        with open(alvo, encoding='utf-8-sig', errors='replace') as f:
            return de_dax(f.read(), os.path.splitext(os.path.basename(alvo))[0])
    if len(alvo) > 260 or '(' in alvo or '\n' in alvo:
        return de_dax(alvo)
    raise ValueError(f'{alvo}: não achei arquivo nem pasta com esse nome (passe a pasta do .pbip, o resultado da '
                     'receita DAX, um arquivo .dax ou o próprio DAX entre aspas)')
