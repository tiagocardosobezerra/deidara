"""
C0 · anatomia: desmonta cada medida. O que ela chama (funções, colunas, outras medidas), a árvore até as
colunas de origem, o padrão do Deidara que ela imita (soma, divisão, estoque, tempo, meta...) e a leitura em
português do que o número é. É texto sobre texto: nenhuma conta é feita, nenhum dado é lido.
"""

import re

from kibaku_nendo.modelo import referencias_dax
from kibaku_nendo.util import chave
from tecnicas.sasori import funcoes_usadas

TEMPO = ('TOTALYTD', 'TOTALQTD', 'TOTALMTD', 'DATESYTD', 'DATESQTD', 'DATESMTD', 'SAMEPERIODLASTYEAR', 'DATEADD',
         'PARALLELPERIOD', 'DATESINPERIOD', 'DATESBETWEEN', 'PREVIOUSMONTH', 'PREVIOUSYEAR', 'PREVIOUSQUARTER',
         'OPENINGBALANCEMONTH', 'CLOSINGBALANCEMONTH', 'OPENINGBALANCEYEAR', 'CLOSINGBALANCEYEAR', 'NEXTMONTH')
AGREGA = {'SUM': 'soma', 'AVERAGE': 'media', 'COUNTROWS': 'contagem_linhas', 'COUNT': 'contagem',
          'COUNTA': 'contagem', 'DISTINCTCOUNT': 'contagem_distinta', 'DISTINCTCOUNTNOBLANK': 'contagem_distinta',
          'MIN': 'minimo', 'MAX': 'maximo', 'MEDIAN': 'mediana'}
_SEM_TEXTO = re.compile(r'"(?:[^"]|"")*"|//[^\n]*|--[^\n]*|/\*.*?\*/', re.S)


def limpo(dax):
    """O DAX sem comentários e com espaços normalizados (para comparar e reconhecer formas)."""
    sem = re.sub(r'//[^\n]*|--[^\n]*|/\*.*?\*/', '', dax or '', flags=re.S)
    return re.sub(r'\s+', ' ', sem).strip()


def sem_texto(dax):
    return _SEM_TEXTO.sub('""', dax or '')


def refs(dax, medidas):
    """{'colunas': [(tabela, coluna)], 'medidas': [nome], 'tabelas': [nome]} citadas no DAX."""
    nomes = {chave(n): n for n in medidas}
    cols, meds = [], []
    for t, n in referencias_dax(dax or ''):
        if t:
            cols.append((t, n))
        elif chave(n) in nomes:
            meds.append(nomes[chave(n)])
        else:
            cols.append((None, n))                     # [Coluna] sem tabela (contexto de linha) ou nome que não existe
    tabelas = sorted(set(re.findall(r"(?:COUNTROWS|ALL|FILTER|VALUES|RELATEDTABLE|ALLSELECTED|REMOVEFILTERS|"
                                    r"SUMMARIZE|ADDCOLUMNS|CALCULATETABLE|DISTINCT)\s*\(\s*('(?:[^']|'')+'|[\w]+)\s*[,)]",
                                    sem_texto(dax), re.I)))
    return {'colunas': list(dict.fromkeys(cols)), 'medidas': list(dict.fromkeys(meds)),
            'tabelas': [x.strip("'").replace("''", "'") for x in tabelas]}


def refs_de(nome, legado):
    """As referências de uma medida, calculadas uma vez por modelo (o mesmo DAX é lido por várias regras)."""
    cache = legado.setdefault('_refs', {})
    if nome not in cache:
        md = legado['medidas'].get(nome)
        cache[nome] = refs(md['dax'], legado['medidas']) if md else {'colunas': [], 'medidas': [], 'tabelas': []}
    return cache[nome]


def dependencias(nome, legado):
    """Todas as medidas de que ela depende (direta ou indiretamente), sem repetir: o fecho do grafo, memorizado.
    Num modelo grande, refazer a árvore inteira por medida cresce exponencialmente; o grafo, não."""
    cache = legado.setdefault('_deps', {})
    if nome in cache:
        return cache[nome]
    vistos, fila = [], list(refs_de(nome, legado)['medidas'])
    conj = set()
    while fila:
        d = fila.pop()
        if d in conj or d == nome:
            continue
        conj.add(d)
        vistos.append(d)
        if d in cache:                                     # já fechada: junta de uma vez
            novos = [x for x in cache[d] if x not in conj and x != nome]
            conj.update(novos)
            vistos.extend(novos)
            continue
        fila.extend(refs_de(d, legado)['medidas'])
    cache[nome] = list(dict.fromkeys(vistos))
    return cache[nome]


def em_ciclo(legado):
    """As medidas que fazem parte de um ciclo (A cita B, B cita A), calculado uma vez (DFS em cores)."""
    if '_ciclos' in legado:
        return legado['_ciclos']
    cor, out = {}, set()
    for inicio in legado['medidas']:
        if cor.get(inicio):
            continue
        pilha = [(inicio, iter(refs_de(inicio, legado)['medidas']))]
        caminho = [inicio]
        cor[inicio] = 1
        while pilha:
            no, filhos = pilha[-1]
            proximo = next(filhos, None)
            if proximo is None:
                cor[no] = 2
                pilha.pop()
                caminho.pop()
            elif cor.get(proximo) == 1:
                out.update(caminho[caminho.index(proximo):])
            elif not cor.get(proximo) and proximo in legado['medidas']:
                cor[proximo] = 1
                caminho.append(proximo)
                pilha.append((proximo, iter(refs_de(proximo, legado)['medidas'])))
    legado['_ciclos'] = out
    return out


def arvore(nome, legado, profundidade=4, _vistos=None, _caminho=()):
    """A árvore de dependência para mostrar: cada medida aparece uma vez (a repetida fica marcada) e até
    `profundidade` níveis. {'nome', 'medidas': [subárvores], 'colunas': [...], 'ciclo', 'repetida', 'cortada'}."""
    vistos = set() if _vistos is None else _vistos
    md = legado['medidas'].get(nome)
    if not md:
        return {'nome': nome, 'medidas': [], 'colunas': [], 'ciclo': False, 'faltando': True}
    if nome in _caminho:
        return {'nome': nome, 'medidas': [], 'colunas': [], 'ciclo': True}
    if nome in vistos:
        return {'nome': nome, 'medidas': [], 'colunas': [], 'ciclo': False, 'repetida': True}
    vistos.add(nome)
    r = refs_de(nome, legado)
    if profundidade <= 0 and r['medidas']:
        return {'nome': nome, 'medidas': [], 'colunas': r['colunas'], 'ciclo': False, 'cortada': True}
    return {'nome': nome, 'colunas': r['colunas'], 'tabelas': r['tabelas'], 'ciclo': False,
            'medidas': [arvore(x, legado, profundidade - 1, vistos, tuple(_caminho) + (nome,))
                        for x in r['medidas'] if x != nome]}


def folhas(no):
    """As colunas de origem de toda a árvore."""
    out = list(no.get('colunas') or [])
    for sub in no.get('medidas') or []:
        out += folhas(sub)
    return list(dict.fromkeys(out))


def desenhar(no, recuo=0):
    """A árvore em texto, para o relatório."""
    marca = (' (ciclo!)' if no.get('ciclo') else ' (não existe no modelo)' if no.get('faltando') else
             ' (já mostrada acima)' if no.get('repetida') else ' (…)' if no.get('cortada') else '')
    linhas = [('  ' * recuo) + ('└ ' if recuo else '') + f'[{no["nome"]}]{marca}']
    filhos = no.get('medidas') or []
    for sub in filhos[:10]:                        # árvore larga: os 10 primeiros e quantos faltam
        linhas += desenhar(sub, recuo + 1)
    if len(filhos) > 10:
        linhas.append(('  ' * (recuo + 1)) + f'└ ... e mais {len(filhos) - 10} medida(s)')
    cols = [f'{t}[{c}]' if t else f'[{c}]' for t, c in no.get('colunas') or []]
    if cols:
        linhas.append(('  ' * (recuo + 1)) + '└ ' + ', '.join(cols))
    return linhas


def desembrulhar(dax):
    """Tira a proteção de período futuro: IF(MIN(Data) > corte, BLANK(), conta) -> conta."""
    mt = re.fullmatch(r"IF\s*\(\s*MIN\s*\([^()]+\)\s*>\s*(?:TODAY\s*\(\s*\)|\[[^\]]+\]|[\w]+)\s*,\s*BLANK\s*\(\s*\)\s*,"
                      r"\s*(.*)\)", dax, re.I | re.S)
    return mt.group(1).strip() if mt else dax


def padrao(md, legado):
    """O padrão do Deidara que a medida imita, com as partes: {'tipo', ...}. 'livre' quando não encaixa."""
    dax = desembrulhar(limpo(md['dax']))
    up = sem_texto(dax).upper()
    r = refs(dax, legado['medidas'])
    fns = [f.upper() for f in funcoes_usadas(dax)]
    if 'data:image/svg' in dax.lower() or any('SVG' in f or 'IBCS' in f for f in fns if '.' in f):
        return {'tipo': 'svg'}
    corte = [m for m in r['medidas'] if re.search(r'corte|cutoff|last ?date|ultima data', m, re.I)]
    r['medidas'] = [m for m in r['medidas'] if m not in corte]     # a data de corte é apoio, não a base
    if re.fullmatch(r'-?\d+(\.\d+)?%?', dax):
        return {'tipo': 'meta_fixa', 'valor': dax}
    mt = re.fullmatch(r"(SUM|AVERAGE|COUNTROWS|COUNT|COUNTA|DISTINCTCOUNT|DISTINCTCOUNTNOBLANK|MIN|MAX|MEDIAN)\s*\(\s*"
                      r"((?:'(?:[^']|'')+'|[\w]+)(?:\s*\[[^\]]+\])?)\s*\)", dax, re.I)
    if mt:
        return {'tipo': 'agregacao', 'agregacao': AGREGA[mt.group(1).upper()], 'alvo': mt.group(2)}
    mt = re.fullmatch(r"DIVIDE\s*\(\s*\[([^\]]+)\]\s*,\s*\[([^\]]+)\]\s*(?:,\s*[^()]*)?\)", dax, re.I) or \
        re.fullmatch(r"\[([^\]]+)\]\s*/\s*\[([^\]]+)\]", dax)
    if mt:
        return {'tipo': 'divisao', 'numerador': mt.group(1), 'denominador': mt.group(2),
                'barra': '/' in dax and not dax.upper().startswith('DIVIDE')}
    tempo = [f for f in fns if f in TEMPO]
    if tempo and len(r['medidas']) == 1:
        base = r['medidas'][0]
        if 'TOTALYTD' in tempo or 'DATESYTD' in tempo:
            return {'tipo': 'acumulado_ano', 'base': base}
        if ('SAMEPERIODLASTYEAR' in tempo or ('DATEADD' in tempo and re.search(r'-\s*1\s*,\s*YEAR', up)) or
                ('PARALLELPERIOD' in tempo and 'YEAR' in up)):
            variacao = re.search(r'DIVIDE\s*\(|/', up) and re.search(r'-', up)
            return {'tipo': 'variacao_ano_anterior' if variacao else 'ano_anterior', 'base': base}
        if 'DATEADD' in tempo and re.search(r'-\s*1\s*,\s*MONTH', up) or 'PREVIOUSMONTH' in tempo:
            variacao = re.search(r'DIVIDE\s*\(|/', up) and re.search(r'-', up)
            return {'tipo': 'variacao_mes_anterior' if variacao else 'mes_anterior', 'base': base}
        if 'DATESINPERIOD' in tempo and re.search(r'-\s*12\s*,\s*MONTH', up):
            return {'tipo': 'movel_12m', 'base': base}
        return {'tipo': 'tempo', 'base': base, 'funcoes': tempo}
    mt = re.search(r"AVERAGEX\s*\(\s*VALUES\s*\(\s*('?[^'\[]+'?)\s*\[([^\]]+)\]", up)
    calendario = mt and (re.search(r'CALEND|DATE|DATA', mt.group(1)) or
                         re.search(r'M[EÊ]S|MONTH|ANO-M|YEARMONTH|PER[IÍ]ODO', mt.group(2)))
    if mt and calendario and len(r['medidas']) == 1:
        return {'tipo': 'media_mensal', 'base': r['medidas'][0]}
    if re.search(r'MAX\s*\(', up) and up.count('<=') >= 1 and 'COUNTROWS' in up and \
            any(re.search(r'admiss|inicio|início|entrada|contrata|start|hire', c, re.I) for _, c in r['colunas']):
        return {'tipo': 'estoque_na_data'}
    if fns[:1] == ['CALCULATE'] and len(r['medidas']) == 1:
        return {'tipo': 'filtrada', 'base': r['medidas'][0]}
    if any(f in fns for f in ('RANKX', 'TOPN', 'RANK')):
        return {'tipo': 'ranking'}
    if re.search(r'#[0-9A-F]{6}', dax, re.I) and fns[:1] in (['IF'], ['SWITCH']):
        return {'tipo': 'cor'}
    if fns[:1] == ['FORMAT'] or (fns and fns[0] in ('SELECTEDVALUE', 'CONCATENATEX')):
        return {'tipo': 'texto'}
    return {'tipo': 'livre'}


def leitura(nome, md, p):
    """O que o número é, em português, a partir do padrão (o ponto de partida da ficha; a pessoa confirma)."""
    t = p['tipo']
    if t == 'agregacao':
        verbo = {'soma': 'Soma de', 'media': 'Média simples de', 'contagem_linhas': 'Quantidade de linhas de',
                 'contagem': 'Quantidade de valores em', 'contagem_distinta': 'Quantidade de valores distintos de',
                 'minimo': 'Menor valor de', 'maximo': 'Maior valor de', 'mediana': 'Mediana de'}[p['agregacao']]
        return f'{verbo} {p["alvo"]}, no filtro do visual.'
    if t == 'divisao':
        return f'[{p["numerador"]}] dividido por [{p["denominador"]}], no mesmo filtro.'
    if t in ('acumulado_ano', 'ano_anterior', 'variacao_ano_anterior', 'mes_anterior', 'variacao_mes_anterior',
             'movel_12m', 'media_mensal'):
        frase = {'acumulado_ano': 'acumulado do início do ano até o fim do período', 'ano_anterior':
                 'no mesmo período do ano anterior', 'variacao_ano_anterior': 'variação contra o mesmo período do ano anterior',
                 'mes_anterior': 'no mês anterior', 'variacao_mes_anterior': 'variação contra o mês anterior',
                 'movel_12m': 'nos últimos 12 meses', 'media_mensal': 'média dos valores de cada mês do período'}[t]
        return f'[{p["base"]}] {frase}.'
    if t == 'filtrada':
        return f'[{p["base"]}] só com um recorte (os filtros do CALCULATE).'
    return {'meta_fixa': f'Número fixo ({p.get("valor")}), provavelmente uma meta escrita no código.',
            'estoque_na_data': 'Quantos estão "dentro" no fim do período (entradas até a data menos saídas).',
            'svg': 'Imagem (SVG) desenhada pela medida, para tabela ou cartão.',
            'ranking': 'Posição ou lista dos primeiros num ranking.', 'cor': 'Cor de formatação condicional.',
            'texto': 'Texto montado pela medida (rótulo, título ou frase).',
            'tempo': f'[{p.get("base")}] com uma conta de tempo ({", ".join(p.get("funcoes") or [])}).'}.get(
        t, 'Conta própria (não segue um padrão conhecido): leia a fórmula com o dono do indicador.')
