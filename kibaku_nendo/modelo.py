"""
O modelo resolvido por dentro: os nomes (tabela, coluna, medida), os tipos aceitos, quem filtra quem
e até onde cada corte chega em cada medida. É a base das outras partes do motor; não depende delas.
"""

import re
from collections import deque
from kibaku_nendo.util import chave, familia_da_coluna, tipo_tmdl
from tecnicas import sasori as dicionario


TIPOS_TABELA = {'fato', 'dimensao'}


AGREGACOES = {
    'soma': 'SUM', 'media': 'AVERAGE', 'minimo': 'MIN', 'maximo': 'MAX',
    'mediana': 'MEDIAN', 'quartil_1': 'PERCENTILE.INC', 'quartil_3': 'PERCENTILE.INC',
    'contagem': 'COUNT', 'contagem_distinta': 'DISTINCTCOUNTNOBLANK', 'contagem_linhas': 'COUNTROWS',
}


AGREGACOES_NUMERICAS = {'soma', 'media', 'mediana', 'quartil_1', 'quartil_3'}


TEMPO = {'acumulado_ano', 'ano_anterior', 'variacao_ano_anterior', 'variacao_mes_anterior', 'media_mensal',
         'movel_12m'}


TIPOS_VISUAL = {
    'cartao': 'card', 'barras': 'clusteredBarChart', 'colunas': 'clusteredColumnChart',
    'linha': 'lineChart', 'controle': 'lineChart', 'rosca': 'donutChart', 'tabela': 'tableEx', 'matriz': 'pivotTable',
    'segmentador': 'slicer', 'medidor': 'gauge',
    'botoes': 'advancedSlicerVisual', 'cartoes': 'cardVisual', 'decomposicao': 'decompositionTreeVisual',
    'dispersao': 'scatterChart', 'area': 'areaChart', 'mapa': 'azureMap',
    'abas': 'advancedSlicerVisual', 'alternar': 'advancedSlicerVisual', 'skyline': 'columnChart',
    'setas': 'clusteredBarChart', 'imagem': 'cardVisual', 'aviso': 'cardVisual',
    'html': 'htmlContent443BE3AD55E043BF878BED274D3A6865', 'vegalite': 'deneb7E15AEF80B9E4D4F8E12924291ECE89A',
}


VISUAIS_DE_TERCEIROS = ('html', 'vegalite')           # visual certificado do AppSource, só quando a pessoa pede


SEGMENTADORES = ('segmentador', 'botoes')


LIMITE_VISUAIS_POR_PAGINA = 12


class Problemas:
    """Erros (bloqueiam), avisos (decisão do usuário) e consequências: erros que
    só existem porque outro erro (a raiz) quebrou uma tabela ou coluna. As
    consequências não entram em `erros`: somem sozinhas quando a raiz é corrigida."""

    def __init__(self):
        self.erros, self.avisos = [], []
        self.raizes = {}            # chave -> texto do erro raiz
        self.consequencias = {}     # texto do erro raiz -> [consequências]

    def erro(self, onde, msg, raiz=None, depende=()):
        texto = f'{onde}: {msg}'
        for d in depende:
            if d in self.raizes:
                self.consequencias.setdefault(self.raizes[d], []).append(texto)
                return
        self.erros.append(texto)
        if raiz:
            self.raizes[raiz] = texto

    def aviso(self, onde, msg):
        self.avisos.append(f'{onde}: {msg}')


# ============================================================================
def pista_medida(nome, nomes):
    import difflib
    todas = [x.get('nome', '') for x in nomes.values()]
    parecidas = difflib.get_close_matches(nome or '', todas, n=3, cutoff=0.5)
    if parecidas:
        return f'; parecidas: {", ".join(parecidas)}'
    return f'; medidas do modelo: {", ".join(todas[:10])}' if todas else ''


def pista_coluna(m, ref, familias=None):
    """O que existe para 'Tabela[Coluna]': colunas do modelo e as do catálogo que ainda não entraram nele."""
    import difflib
    mt = re.fullmatch(r"\s*'?(.+?)'?\[(.+)\]\s*", ref or '')
    if not mt:
        return ' (use Tabela[Coluna])'
    t = tabela_do_modelo(m, mt.group(1))
    if not t:
        return f'; tabelas do modelo: {", ".join(x["nome"] for x in m["tabelas"])}'
    do_modelo = [c['nome'] for c in t['colunas'] if not c['oculta'] and (not familias or c['familia'] in familias)]
    texto = ''
    parecidas = difflib.get_close_matches(mt.group(2), do_modelo, n=3, cutoff=0.5)
    if parecidas:
        texto = f'; parecidas em {t["nome"]}: {", ".join(parecidas)}'
    elif do_modelo:
        texto = f'; em {t["nome"]}: {", ".join(do_modelo[:8])}'
    fonte = (m.get('_catalogos') or {}).get(t.get('fonte'))
    if fonte and t.get('origem'):
        cat = fonte.tabela(t['origem'])
        no_modelo = {chave(c['origem']) for c in t['colunas'] if c['origem']}
        fora = [c for c in cat['colunas'].values() if chave(c['coluna']) not in no_modelo
                and (not familias or c.get('familia') in familias)]
        alvo = difflib.get_close_matches(chave(mt.group(2)), [chave(c['coluna']) for c in fora] +
                                         [chave(c.get('descricao') or '') for c in fora], n=1, cutoff=0.3)
        escolhida = next((c for c in fora if alvo and alvo[0] in (chave(c['coluna']), chave(c.get('descricao') or ''))),
                         fora[0] if len(fora) == 1 else None)
        if escolhida:
            texto += (f'. No catálogo, {t["origem"]}.{escolhida["coluna"]} ("{escolhida.get("descricao") or ""}") ainda não '
                      f'está no modelo: acrescente em tabelas[{t["nome"]}].colunas: '
                      f'{{"coluna": "{escolhida["coluna"]}", "nome": "{mt.group(2)}"}}')
        elif fora:
            texto += f'. No catálogo, fora do modelo: {", ".join(c["coluna"] for c in fora[:8])}'
    return texto


def chave_tabela(tabela):
    return ('tabela', chave(tabela))


def chave_coluna(tabela, coluna):
    return ('coluna', chave(tabela), chave(coluna))


def depende_de(ref):
    """Chaves de raiz de que uma referência 'Tabela[Coluna]' depende."""
    mt = re.fullmatch(r"\s*'?(.+?)'?\[(.+)\]\s*", ref or '') or re.fullmatch(r'([^.\[]+)\.(.+)', ref or '')
    if not mt:
        return ()
    return (chave_tabela(mt.group(1)), chave_coluna(mt.group(1), mt.group(2)))


def familia_declarada(oc):
    return oc.get('familia') or familia_da_coluna(oc)


def tabela_do_modelo(m, nome):
    for t in m['tabelas']:
        if chave(t['nome']) == chave(nome):
            return t
    return None


def coluna_do_modelo(t, nome):
    for c in t['colunas']:
        if chave(c['nome']) == chave(nome):
            return c
    return None


def coluna_por_origem(t, origem):
    for c in t['colunas']:
        if c['origem'] and chave(c['origem']) == chave(origem) and not c.get('chave_campos'):
            return c
    return None


# ------------------------------------------------------------------ medidas
_REF = re.compile(r"('(?:[^']|'')+'|[A-Za-z_][A-Za-z0-9_]*)?\[((?:[^\]]|\]\])+)\]")


def referencias_dax(dax):
    """[(tabela|None, nome)] referenciados num DAX (fora de strings)."""
    sem_strings = re.sub(r'"(?:[^"]|"")*"', '""', dax)
    out = []
    for t, n in _REF.findall(sem_strings):
        if t.startswith("'"):
            t = t[1:-1].replace("''", "'")
        out.append((t or None, n.replace(']]', ']')))
    return out


SVG_GERADAS = ('svg_barra_meta', 'svg_pilula', 'svg_seta', 'svg_posicao', 'svg_radar', 'svg_bolha', 'svg_variacao',
               'svg_estrelas', 'svg_progresso')


RANKINGS = ('posicao', 'pareto', 'melhores_piores', 'lista_top', 'jitter', 'impacto', 'leitura')


DIAGNOSTICOS = ('jitter', 'impacto')        # da causa raiz: feitas para o eixo do gráfico, não para a tabela


EXTRAS = ('escolha', 'alternar', 'cor_destaque', 'aviso', 'svg_iniciais', 'svg_dispersao', 'html_kpis', 'svg_espinha',
          'controle', 'fora_da_curva')


COR_APAGADA = '#C8C6C4'


def medida(m, nome):
    for x in m['medidas']:
        if chave(x['nome']) == chave(nome):
            return x
    return None


# ------------------------------------------------------------------ páginas
def campo_do_modelo(m, ref):
    """Coluna ('Tabela[Coluna]') ou medida (nome solto)."""
    if re.search(r'\[.+\]$', ref or '') or ('.' in (ref or '') and not medida(m, ref)):
        t, c = resolver_coluna(m, ref)
        if c:
            return {'tipo': 'coluna', 'tabela': t['nome'], 'nome': c['nome'], 'familia': c['familia']}
        return None
    md = medida(m, ref or '')
    if md:
        return {'tipo': 'medida', 'tabela': md['tabela'], 'nome': md['nome'], 'formato': md['formato']}
    return None


def resolver_coluna(m, ref, padrao=None):
    """'Tabela[Coluna]', 'Tabela.Coluna' ou 'Coluna' (na tabela padrão) -> (tabela, coluna) do modelo."""
    ref = (ref or '').strip()
    mt = re.fullmatch(r"'?(.+?)'?\[(.+)\]", ref) or re.fullmatch(r'([^.]+)\.(.+)', ref)
    tn, cn = (mt.group(1), mt.group(2)) if mt else (padrao, ref)
    t = tabela_do_modelo(m, tn or '')
    c = coluna_do_modelo(t, cn) if t else None
    return t, c


def alcanca(g, de, para):
    if de == para:
        return True
    vistos, fila = {de}, deque([de])
    while fila:
        x = fila.popleft()
        for y in g.get(x, ()):
            if y == para:
                return True
            if y not in vistos:
                vistos.add(y)
                fila.append(y)
    return False


def le_calendario(m, nome, vistos=None):
    """A medida (ou uma de que depende) lê o calendário por MAX(Data), sem relacionamento."""
    vistos = vistos or set()
    md = medida(m, nome)
    if not md or chave(nome) in vistos:
        return False
    vistos.add(chave(nome))
    return bool(md.get('le_calendario')) or any(le_calendario(m, d, vistos) for d in md.get('depende') or [])


def chega(m, filtra, tabela_filtro, alvo, nome_medida):
    if alcanca(filtra, tabela_filtro, alvo):
        return True
    cal = (m.get('calendario') or {}).get('tabela')
    return bool(cal) and tabela_filtro == cal and le_calendario(m, nome_medida)


def distorcoes(avisos):
    """Os avisos de número distorcido (o corte filtra só parte da conta): o aprovar não aceita em bloco."""
    return [x for x in avisos if 'filtra só parte' in x or 'fica distorcido' in x]


def grafo_de_filtro(m, extras=()):
    """Quem filtra quem (o lado um filtra o lado muitos); `extras`: ligações [(de, para)] ainda a confirmar."""
    g = {}
    for r in m['relacionamentos']:
        if r['ativo']:
            g.setdefault(r['para'], set()).add(r['de'])     # o lado um filtra o lado muitos
    for de, para in extras:
        g.setdefault(para, set()).add(de)
    return g


def alcance(m, filtra, tabela_filtro, nome_medida):
    """'total' quando a coluna filtra a medida inteira, 'parcial' quando só parte dela, 'nenhum' quando nada."""
    alvo = tabelas_da_medida(m, nome_medida)
    faltam = [a for a in alvo if not chega(m, filtra, tabela_filtro, a, nome_medida)]
    return 'total' if not faltam else 'nenhum' if len(faltam) == len(alvo) else 'parcial'


def tabelas_da_medida(m, nome, vistos=None):
    """Tabelas que a medida lê (seguindo as medidas de que depende). `vistos` é o caminho até aqui (só para não
    entrar em ciclo): duas dependências que levam à mesma medida contam as duas."""
    vistos = set(vistos or ())
    if chave(nome) in vistos:
        return set()
    vistos.add(chave(nome))
    md = medida(m, nome)
    if not md:
        return set()
    if md.get('tipo') in ('meta', 'corte'):        # meta fixa é um número; a data de corte ignora todo filtro
        return set()
    if md.get('tipo') == 'meta_periodo':           # a meta do período só multiplica a meta de base pelos meses
        return tabelas_da_medida(m, md['base'], vistos)
    out = set()
    if md.get('tipo') in SVG_GERADAS + RANKINGS + EXTRAS:   # a coluna das linhas só organiza; os dados vêm das medidas
        for n in md.get('depende') or []:
            out |= tabelas_da_medida(m, n, vistos)
        return out or {md['tabela']}
    for tn, n in referencias_dax(md['dax'] or ''):
        if tn and tabela_do_modelo(m, tn):
            out.add(tabela_do_modelo(m, tn)['nome'])
        elif not tn and medida(m, n):
            out |= tabelas_da_medida(m, n, vistos)
    if md['dax'] and md['dax'].startswith('COUNTROWS('):
        out.add(md['tabela'])
    out |= set(md.get('tabelas_lidas') or [])
    # CALCULATE de tempo lê o calendário, mas o valor vem da base
    auxiliares = {t['nome'] for t in m['tabelas'] if t.get('auxiliar')}        # a escolha não traz dados
    return {t for t in out if not (m.get('calendario') and t == m['calendario']['tabela']) and t not in auxiliares}         or {md['tabela']}


def medidas_do_visual(r):
    return [x for x in r['valores'] + r['campos'] + ([r['meta']] if r.get('meta') else []) if x and x['tipo'] == 'medida']


def conferir_funcoes(dax, p, onde):
    """Função que não está no dicionário DAX é erro: nunca se inventa função."""
    for fn, sug in dicionario.desconhecidas(dax):
        p.erro(onde, f'função {fn} não está no dicionário DAX' + (f'; parecidas: {", ".join(sug)}' if sug else '')
               + ' (deidara.py funcoes buscar "<o que você quer fazer>")')


def sintaxe_dax(dax):
    """Os erros de escrita que o Power BI recusa e que dá para ver sem o motor: aspas, colchetes e parênteses que
    não fecham, ";" no lugar da vírgula e operador no fim. Devolve a lista de problemas."""
    # texto e comentário saem juntos, na ordem em que aparecem ("http://..." dentro do texto não é comentário)
    texto = re.sub(r'"(?:[^"]|"")*"|//[^\n]*|--[^\n]*|/\*.*?\*/', lambda x: '""' if x.group(0)[0] == '"' else '',
                   dax, flags=re.S)
    if texto.count('"') % 2:
        return ['aspas duplas sem fechar']
    if texto.count("'") % 2:
        return ["aspas simples (nome de tabela) sem fechar"]
    texto = re.sub(r"'(?:[^']|'')*'", "''", texto)
    out, pilha = [], []
    for ch in re.sub(r'\[(?:[^\]]|\]\])*\]', '[]', texto) if texto.count('[') == texto.count(']') else texto:
        if ch in '([':
            pilha.append(ch)
        elif ch in ')]':
            if not pilha or pilha.pop() != {')': '(', ']': '['}[ch]:
                return [f'"{ch}" sem a abertura correspondente']
    if pilha:
        out.append(f'"{pilha[-1]}" aberto sem fechar ({len(pilha)} no total)')
    if ';' in texto:
        out.append('";" no lugar de "," entre os argumentos (o projeto é gravado em TMDL, que só aceita vírgula, '
                   'mesmo com o Power BI em português)')
    if re.search(r'[-+*/&,(]\s*$', texto.strip()):
        out.append('a expressão termina num operador ou vírgula: falta o fim da conta')
    out += _filtro_booleano_com_medida(texto)
    return out


# argumentos de CALCULATE que já são tabela ou modificador (não são filtro True/False)
_FILTRO_TABELA = re.compile(r'\s*(FILTER|ALL\w*|VALUES|DISTINCT|REMOVEFILTERS|USERELATIONSHIP|CROSSFILTER|TREATAS|'
                            r'DATES\w*|SAMEPERIODLASTYEAR|DATEADD|PARALLELPERIOD|PREVIOUS\w*|NEXT\w*|CALCULATETABLE|'
                            r'TOPN|SUMMARIZE\w*|ADDCOLUMNS|SELECTCOLUMNS|KEEPFILTERS\s*\(\s*FILTER|\{)\b', re.I)


def _argumentos(texto, inicio):
    """Os argumentos da chamada cujo "(" está em `inicio`, separados nas vírgulas do primeiro nível."""
    args, nivel, atual = [], 0, ''
    for ch in texto[inicio + 1:]:
        if ch in '([{':
            nivel += 1
        elif ch in ')]}':
            if nivel == 0:
                args.append(atual)
                return args
            nivel -= 1
        if ch == ',' and nivel == 0:
            args.append(atual)
            atual = ''
        else:
            atual += ch
    return args


def _filtro_booleano_com_medida(texto):
    """Filtro True/False do CALCULATE com medida ou CALCULATE dentro: o Power BI recusa ("uma função PLACEHOLDER foi
    usada numa expressão True/False usada como filtro de tabela"). O certo é guardar o valor numa VAR antes."""
    texto = re.sub(r'"(?:[^"]|"")*"|//[^\n]*|--[^\n]*|/\*.*?\*/', '""', texto, flags=re.S)
    texto = re.sub(r"'(?:[^']|'')*'", "''", texto)
    out = []
    for achado in re.finditer(r'\b(CALCULATE|CALCULATETABLE)\s*\(', texto, re.I):
        for arg in _argumentos(texto, achado.end() - 1)[1:]:
            miolo = re.sub(r'^\s*KEEPFILTERS\s*\((.*)\)\s*$', r'\1', arg, flags=re.S | re.I)
            if _FILTRO_TABELA.match(miolo) or not re.search(r'<>|<=|>=|[=<>]|\bIN\b', miolo, re.I):
                continue
            sem_colunas = re.sub(r"(\w|'')\s*\[(?:[^\]]|\]\])*\]", r'\1', miolo)
            if re.search(r'\[(?:[^\]]|\]\])*\]', sem_colunas) or re.search(r'\bCALCULATE\s*\(', miolo, re.I):
                out.append(f'filtro True/False com medida ou CALCULATE dentro ("{miolo.strip()[:60]}"): o Power BI '
                           'recusa; guarde o valor numa VAR antes do CALCULATE e compare com a VAR')
    return out


def boas_praticas_dax(dax):
    """As regras de DAX do Best Practice Analyzer da Microsoft (microsoft/Analysis-Services, BPARules.json) que dá
    para conferir no texto, sem o motor. Devolve [(regra, conselho)]."""
    texto = re.sub(r'"(?:[^"]|"")*"|//[^\n]*|--[^\n]*|/\*.*?\*/', '""', dax, flags=re.S)
    texto = re.sub(r"'(?:[^']|'')*'", "''", texto)
    sem_nomes = re.sub(r'\[(?:[^\]]|\]\])*\]', '[]', texto)
    out = []
    if re.search(r'[\])\w]\s*/\s*(?!\d+(?:\.\d+)?\b(?!\s*[(\[]))[\[(\w]', sem_nomes):   # ÷ número fixo (365.25) é seguro
        out.append(('divisão com "/"', 'use DIVIDE(numerador, denominador): não dá erro quando o denominador é zero '
                                       'ou vazio'))
    if re.search(r'\b(IFERROR|ISERROR)\s*\(', texto, re.I):
        out.append(('IFERROR/ISERROR', 'evite: esconde o erro e deixa a medida lenta; trate o caso (DIVIDE, ISBLANK, '
                                       'IF) antes de ele acontecer'))
    if re.search(r'\bEARLIER\s*\(', texto, re.I):
        out.append(('EARLIER', 'troque por VAR: mais claro e não depende de contexto de linha aninhado'))
    if re.search(r'\bCALCULATE\s*\([^()]*(?:\([^()]*\)[^()]*)*,\s*FILTER\s*\(\s*(?:\'\'|\w+)\s*,', texto, re.I):
        out.append(('FILTER na tabela inteira dentro do CALCULATE', 'filtre a coluna (Tabela[Coluna] = valor) em vez '
                                                                    'da tabela inteira: mais rápido e não traz junto '
                                                                    'filtros que você não pediu'))
    if re.search(r'\b(SUMX|AVERAGEX|COUNTX|MINX|MAXX)\s*\(\s*FILTER\s*\(', texto, re.I) is None and \
            re.search(r'\bSUMX\s*\(\s*VALUES\s*\(', texto, re.I) is None and \
            re.search(r'\bCOUNTROWS\s*\(\s*DISTINCT\s*\(', texto, re.I):
        out.append(('COUNTROWS(DISTINCT())', 'use DISTINCTCOUNT: mesmo resultado, mais rápido'))
    return out


def nova_coluna(nome, origem, familia, descricao='', oculta=False, formato=None, expressao_sql=None):
    if not formato:
        formato = {'inteiro': None, 'decimal': 'decimal', 'real': 'decimal', 'data': 'data',
                   'datahora': 'data', 'hora': 'hora'}.get(familia)
    return {'nome': nome, 'origem': origem, 'familia': familia, 'tipo_tmdl': tipo_tmdl(familia),
            'descricao': descricao, 'oculta': oculta, 'formato': formato, 'expressao_sql': expressao_sql,
            'como_data': False, 'gerada': origem is None, 'sql_tipo': None, 'cast_sql': None, 'chave_campos': None}


# --------------------------------------------------------------- calendário
COLUNAS_CALENDARIO = [
    ('Data', 'data', 'data'), ('Ano', 'inteiro', None), ('Mês', 'inteiro', None),
    ('Nome do Mês', 'texto', None), ('Trimestre', 'texto', None), ('Ano-Mês', 'texto', None),
    ('Mês/Ano', 'texto', None), ('Ano-Trimestre', 'texto', None), ('Ano-Mês Num', 'inteiro', None),
    ('Ano-Trimestre Num', 'inteiro', None),
]


# ano fiscal que não começa em janeiro ("mes_inicio_fiscal"): o ano fiscal leva o nome do ano em que termina
COLUNAS_FISCAIS = [('Ano Fiscal', 'inteiro', None), ('Mês Fiscal', 'inteiro', None)]


CALENDARIO_OCULTAS = {'Ano-Mês Num', 'Ano-Trimestre Num', 'Mês Fiscal'}


# colunas do calendário que repetem todo ano: sem o ano no filtro, somam todos os anos
CALENDARIO_SEM_ANO = {'Mês', 'Nome do Mês', 'Trimestre', 'Mês Fiscal'}
