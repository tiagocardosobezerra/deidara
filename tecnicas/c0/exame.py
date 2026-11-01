"""
C0 · exame: o que está errado ou arriscado em cada medida e no modelo, do mais grave para o menos.

Gravidade (e quanto tira da nota de 0 a 10):
- crítico  (−3,0): o número sai errado ou a medida nem calcula;
- alto     (−1,5): sai errado em parte dos cortes ou dos períodos, ou quebra uma regra (LGPD);
- médio    (−0,5): risco, desempenho ou governança (sem definição, meta escondida no código);
- baixo    (−0,1): estilo e manutenção.

Cada achado diz o EFEITO no número, em linguagem de negócio, e a CORREÇÃO. As regras são as mesmas que o
validar do Deidara aplica ao que ele gera (método dos indicadores, regras de texto do Best Practice Analyzer
da Microsoft), aplicadas aqui ao que já existe.
"""

import re

from kibaku_nendo.modelo import boas_praticas_dax, sintaxe_dax
from kibaku_nendo.util import chave
from tecnicas import sasori
from tecnicas.c0.anatomia import TEMPO, dependencias, em_ciclo, limpo, refs_de, sem_texto
from tecnicas.c0 import anatomia

PESO = {'critico': 3.0, 'alto': 1.5, 'medio': 0.5, 'baixo': 0.1}
ORDEM = {'critico': 0, 'alto': 1, 'medio': 2, 'baixo': 3}
ROTULO = {'critico': 'CRÍTICO', 'alto': 'ALTO', 'medio': 'MÉDIO', 'baixo': 'BAIXO'}
CADASTRO = re.compile(r'admiss|inicio|início|entrada|contrata|hire|start|ativa[çc]', re.I)
META = re.compile(r'\b(meta|alvo|objetivo|target|goal|budget|or[çc]ado|plano)\b', re.I)


def _achado(codigo, gravidade, titulo, efeito, correcao, evidencia=''):
    return {'codigo': codigo, 'gravidade': gravidade, 'titulo': titulo, 'efeito': efeito, 'correcao': correcao,
            'evidencia': evidencia}


TETO = {'critico': 4.0, 'alto': 7.0}          # número errado não passa de 4; errado em parte, não passa de 7


def nota(achados, base=10.0):
    n = base - sum(PESO[a['gravidade']] for a in achados)
    for g, teto in TETO.items():
        if any(a['gravidade'] == g for a in achados):
            n = min(n, teto)
    return max(0.0, round(n, 1))


# ===================================================================== modelo
def papeis(leg):
    """{'fatos', 'dimensoes', 'cadastros', 'calendarios'}: o papel de cada tabela, pelo desenho das ligações
    (calculado uma vez por modelo)."""
    if '_papeis' in leg:
        return leg['_papeis']
    leg['_papeis'] = _papeis(leg)
    return leg['_papeis']


def _papeis(leg):
    lado_um = {r['para'] for r in leg['relacoes'] if r.get('para_card', 'one') == 'one'}
    lado_muitos = {r['de'] for r in leg['relacoes']}
    calendarios = {n for n, t in leg['tabelas'].items() if t.get('calendario')} or \
        {n for n, t in leg['tabelas'].items() if re.search(r'calend|^d?_?date|^dim_?date|^datas?$', n, re.I)}
    fatos = {n for n in leg['tabelas'] if n in lado_muitos and n not in lado_um} | \
        {n for n in leg['tabelas'] if re.match(r'^(f|fato|fact)[_A-Z]', n)}
    fatos -= calendarios
    dims = {n for n in leg['tabelas'] if n not in fatos}
    cadastros = {n for n in dims - calendarios
                 if any(CADASTRO.search(c) and re.search(r'date|data', (x.get('tipo') or '') + c, re.I)
                        for c, x in leg['tabelas'][n]['colunas'].items())}
    return {'fatos': fatos, 'dimensoes': dims, 'cadastros': cadastros, 'calendarios': calendarios}


def _tabelas_da(nome, leg, vistos=()):
    """As tabelas que a medida lê, ela e tudo de que depende (pelo grafo memorizado)."""
    cache = leg.setdefault('_tabelas', {})
    if nome not in cache:
        out = set()
        for m in [nome] + dependencias(nome, leg):
            r = refs_de(m, leg)
            out |= {t for t, _ in r['colunas'] if t} | set(r['tabelas'])
        cache[nome] = out
    return cache[nome]


def _e_taxa(nome, leg):
    md = leg['medidas'].get(nome) or {}
    d = limpo(md.get('dax', '')).upper()
    return '%' in (md.get('formato') or '') or d.startswith('DIVIDE(') or bool(re.fullmatch(r'\[[^\]]+\]\s*/\s*\[[^\]]+\]', d))


def exame_modelo(leg):
    out = []
    usa_tempo = any(f.upper() in TEMPO for md in leg['medidas'].values() for f in sasori.funcoes_usadas(md['dax']))
    if leg['origem'] == 'dax':
        return out
    if usa_tempo and not any(t.get('calendario') for t in leg['tabelas'].values()):
        out.append(_achado('sem_calendario', 'alto', 'Conta de tempo sem tabela de datas marcada',
                           'acumulado no ano e ano anterior podem pular dias sem movimento e errar a comparação',
                           'tenha uma tabela de datas contínua, marcada como tabela de datas (o Deidara gera o '
                           'calendário pronto)'))
    if leg.get('data_automatica'):
        out.append(_achado('data_automatica', 'medio', 'Data/hora automática ligada',
                           'o modelo cria uma tabela de datas escondida por coluna de data: arquivo maior, e cada '
                           'visual pode usar um calendário diferente',
                           'desligue em Opções > Carga de dados > Data/hora automática e use uma tabela de datas'))
    for r in leg['relacoes']:
        if str(r.get('cruzado', '')).lower().startswith('both'):
            out.append(_achado('bidirecional', 'medio', f'Relação nos dois sentidos: {r["de"]} ↔ {r["para"]}',
                               'filtro que volta pela relação pode mudar números de outras tabelas sem ninguém ver e '
                               'deixa o modelo ambíguo',
                               'deixe num sentido só e use CROSSFILTER na medida que precisar',
                               f'{r["de"]}[{r.get("de_coluna")}] -> {r["para"]}[{r.get("para_coluna")}]'))
        if r.get('de_card') == 'many' and r.get('para_card') == 'many':
            out.append(_achado('muitos_para_muitos', 'alto', f'Relação muitos-para-muitos: {r["de"]} – {r["para"]}',
                               'o total pode não bater com a soma das linhas, e o mesmo item conta em vários lugares',
                               'crie a tabela ponte (uma linha por chave) e ligue as duas nela'))
    usadas = ' '.join(sem_texto(md['dax']) for md in leg['medidas'].values())
    for r in leg['relacoes']:
        if not r.get('ativa', True) and 'USERELATIONSHIP' not in usadas.upper():
            out.append(_achado('inativa_sem_uso', 'baixo', f'Relação inativa sem uso: {r["de"]} -> {r["para"]}',
                               'nenhuma medida usa esta ligação', 'use USERELATIONSHIP numa medida ou apague a relação'))
    for tn, t in leg['tabelas'].items():
        for cn, c in t['colunas'].items():
            expr = c.get('calculada') or ''
            if expr and re.search(r'\b(SUM|SUMX|CALCULATE|COUNTROWS|AVERAGE|AVERAGEX)\s*\(', expr, re.I):
                out.append(_achado('coluna_fazendo_medida', 'medio', f'Coluna calculada fazendo papel de medida: {tn}[{cn}]',
                                   'o valor fica congelado na atualização e não responde aos filtros do painel',
                                   'troque por uma medida (ou leve a conta para a view/Power Query, se for por linha)',
                                   limpo(expr)[:120]))
    return out


# ===================================================================== medida
def exame_medida(nome, leg, pad):
    md = leg['medidas'][nome]
    dax = md['dax']
    up = sem_texto(limpo(dax)).upper()
    out = []
    conhecido = leg['origem'] != 'dax'
    for problema in sintaxe_dax(dax):
        out.append(_achado('sintaxe', 'critico', 'DAX mal escrito', 'a medida não calcula no Power BI', problema))
    for fn, sug in sasori.desconhecidas(dax):
        out.append(_achado('funcao_desconhecida', 'critico', f'Função {fn} não existe no DAX',
                           'a medida dá erro', 'troque pela função certa' + (f' ({", ".join(sug)}?)' if sug else '')))
    r = refs_de(nome, leg)
    if conhecido:
        novas = set(re.findall(r'"(@?[^"]+)"\s*,', dax))         # colunas criadas no próprio DAX (ADDCOLUMNS...)
        for t, c in r['colunas']:
            if t and t not in leg['tabelas']:
                out.append(_achado('ref_inexistente', 'critico', f'Tabela {t} não existe no modelo', 'a medida dá erro',
                                   'corrija o nome da tabela', f"{t}[{c}]"))
            elif t and c not in leg['tabelas'][t]['colunas'] and not any(
                    m == c and leg['medidas'][m]['tabela'] == t for m in leg['medidas']):
                out.append(_achado('ref_inexistente', 'critico', f'Coluna {t}[{c}] não existe', 'a medida dá erro',
                                   'corrija o nome da coluna', f'{t}[{c}]'))
            elif not t and c not in novas and not c.startswith('@') and not _coluna_de_funcao(c, up) and \
                    not any(c in x['colunas'] for x in leg['tabelas'].values()):
                out.append(_achado('ref_inexistente', 'critico', f'[{c}] não é medida nem coluna do modelo',
                                   'a medida dá erro', 'corrija o nome', f'[{c}]'))
    for regra, conselho in boas_praticas_dax(dax):
        grav = {'divisão com "/"': 'medio', 'IFERROR/ISERROR': 'medio', 'EARLIER': 'baixo',
                'FILTER na tabela inteira dentro do CALCULATE': 'medio', 'COUNTROWS(DISTINCT())': 'baixo'}.get(regra, 'baixo')
        efeito = {'divisão com "/"': 'denominador zero ou vazio dá erro ou infinito no visual',
                  'IFERROR/ISERROR': 'esconde erro de verdade e deixa a medida lenta',
                  'FILTER na tabela inteira dentro do CALCULATE': 'lento em tabela grande e pode trazer filtros que '
                                                                   'não foram pedidos'}.get(regra, 'manutenção mais difícil')
        out.append(_achado('boa_pratica', grav, f'Boa prática: {regra}', efeito, conselho))
    # TODAY() ao lado do MAX de uma data é o teto da data de corte (o jeito certo); sozinho, é o fim do período
    if re.search(r'\b(TODAY|NOW|UTCNOW|UTCTODAY)\s*\(', up) and not re.search(r"\bMAX\s*\(\s*'?\w", up):
        out.append(_achado('hoje', 'alto', 'Usa a data de hoje como fim do período',
                           'se a fonte atualiza com atraso, o mês atual aparece vazio ou menor, e o acumulado e a '
                           'variação erram no fim do período',
                           'use a última data com dado (o Deidara cria a medida Data de Corte)'))
    tempo = [f for f in sasori.funcoes_usadas(dax) if f.upper() in TEMPO]
    if any(f.upper() in ('SAMEPERIODLASTYEAR', 'DATEADD', 'PARALLELPERIOD', 'PREVIOUSYEAR') for f in tempo) and \
            '<=' not in up:                        # qualquer "<=" junto: o período já está limitado (EDATE, MAX, corte)
        out.append(_achado('ano_anterior_parcial', 'alto', 'Compara com o período anterior inteiro',
                           'no ano (ou mês) em curso, o período atual tem só os dias com dado e o anterior tem todos: '
                           'a variação mostra uma queda que não aconteceu (em janeiro, perto de −90%)',
                           'limite o período anterior até o mesmo dia do último dado (padrão "previous year up to '
                           'a certain date" da SQLBI; o Deidara já gera assim)'))
    if tempo and conhecido:
        cal = papeis(leg)['calendarios']
        for t, c in r['colunas']:
            if t and t not in cal and re.search(r'\b(' + '|'.join(TEMPO) + r')\s*\(\s*' + re.escape(t), up.replace("'", ''), re.I):
                out.append(_achado('tempo_fora_do_calendario', 'alto', f'Conta de tempo sobre {t}[{c}], fora da tabela de datas',
                                   'dias sem movimento somem da conta e o ano anterior compara datas que não existem',
                                   'use a coluna de data da tabela de datas marcada', f'{t}[{c}]'))
                break
    if re.search(r"\]\s*\.\s*\[DATE\]", up):
        out.append(_achado('data_automatica_usada', 'alto', 'Usa a tabela de datas automática ([Data].[Date])',
                           'cada coluna tem o seu calendário escondido: cortes por ano não conversam entre visuais',
                           'use a tabela de datas do modelo'))
    p = papeis(leg) if conhecido else None
    if p and pad['tipo'] == 'divisao' and pad['denominador'] in leg['medidas']:
        den = leg['medidas'][pad['denominador']]
        dd = limpo(den['dax']).upper()
        mt = re.fullmatch(r"(COUNTROWS|DISTINCTCOUNT|COUNT)\s*\(\s*'?([^'\[\)]+)'?", dd.rstrip(')').split('[')[0] + '')
        tab_den = mt.group(2).strip() if mt else None
        tab_den = next((n for n in leg['tabelas'] if n.upper() == (tab_den or '').upper()), None)
        if tab_den in p['dimensoes'] and _tabelas_da(pad['numerador'], leg) & p['fatos']:
            out.append(_achado('taxa_sobre_cadastro', 'critico', f'Taxa dividida pela contagem do cadastro ({tab_den})',
                               'o denominador conta ativos e desligados de todos os tempos e não muda com o período: a '
                               'taxa sai menor do que é e não compara meses',
                               'divida pelo estoque médio do período (quem estava dentro no fim de cada mês): padrão '
                               'turnover do Deidara', f'[{pad["denominador"]}] = {limpo(den["dax"])}'))
    if p and pad['tipo'] == 'agregacao' and pad['agregacao'] in ('contagem_linhas', 'contagem', 'contagem_distinta') \
            and re.search(r'head ?count|ativos|quadro|efetivo|vigentes|em carteira|clientes ativos|\bhc\b', nome, re.I):
        alvo_t = re.sub(r"[\[\]'].*$", '', pad['alvo'].strip("'")).strip()
        if alvo_t in p['dimensoes'] and alvo_t not in p['calendarios']:
            out.append(_achado('estoque_contagem', 'alto', f'"{nome}" conta o cadastro inteiro ({alvo_t})',
                               'entram também os desligados (e quem ainda não entrou): o número não é quem está '
                               'ativo, e não muda com o período',
                               'conte quem está dentro no último dia do período: entradas até a data menos saídas até a '
                               'data ("estoque_na_data" no Deidara)'))
    if p:
        for t, c in r['colunas']:
            if t in p['cadastros'] and re.search(r'\b(SUM|AVERAGE)\s*\(\s*' + re.escape(t), up.replace("'", ''), re.I) \
                    and 'CALCULATE' not in up and 'FILTER' not in up:
                out.append(_achado('soma_cadastro', 'alto', f'Soma o cadastro inteiro ({t}[{c}])',
                                   'entram ativos e desligados: total e média ficam maiores (ou menores) do que a '
                                   'equipe de hoje',
                                   'some só quem está ativo no fim do período ("no_estoque" no Deidara)', f'{t}[{c}]'))
                break
    if p and pad['tipo'] == 'divisao' and pad['denominador'] in leg['medidas']:
        from tecnicas.c0.anatomia import padrao as _padrao
        pnum = _padrao(leg['medidas'][pad['numerador']], leg) if pad['numerador'] in leg['medidas'] else {}
        fluxo = pnum.get('tipo') == 'agregacao' and re.sub(r"[\['].*$", '', pnum.get('alvo', '').strip("'")) in p['fatos']
        if fluxo and _padrao(leg['medidas'][pad['denominador']], leg)['tipo'] == 'estoque_na_data':
            out.append(_achado('denominador_no_fim', 'medio', f'Divide pelo estoque do fim do período ([{pad["denominador"]}])',
                               'num mês com muita entrada ou saída, a taxa usa só o último dia: no ano, o denominador é '
                               'o de 31/12, não o do ano inteiro',
                               'divida pela média do estoque no fim de cada mês do período ("media_mensal" no Deidara)'))
        for onde, col in _cortes_parciais(nome, pad, leg):
            out.append(_achado('corte_parcial', 'alto', f'O corte {col} filtra só parte da taxa',
                               'em cada linha, o numerador muda e o denominador fica o do total (ou o contrário): a '
                               'taxa por linha sai distorcida',
                               'ligue a tabela do corte às duas partes da conta, ou tire o corte deste visual', onde))
    if pad['tipo'] == 'agregacao' and pad['agregacao'] in ('soma', 'media'):
        col = _alvo_coluna(pad['alvo'])
        if col and re.search(r'taxa|percent|%|pct|[íi]ndice|rate|ratio|margem', col, re.I):
            grav, tit = (('critico', 'Soma de uma coluna de taxa') if pad['agregacao'] == 'soma' else
                         ('alto', 'Média simples de uma coluna de taxa'))
            out.append(_achado('agrega_taxa', grav, f'{tit} ({col})',
                               'taxa somada passa de 100%; média simples pesa igual a linha pequena e a grande',
                               'guarde o numerador e o denominador e divida os totais'))
    if re.search(r'AVERAGEX\s*\([^,]+,\s*(DIVIDE\s*\(|\[)', up):
        alvo = re.search(r'AVERAGEX\s*\([^,]+,\s*\[([^\]]+)\]', limpo(dax), re.I)
        if not alvo or _e_taxa(alvo.group(1), leg):
            out.append(_achado('media_de_taxas', 'critico', 'Média de taxas',
                               'a média simples das taxas dá o mesmo peso à área de 10 pessoas e à de 5.000: o total '
                               'não é a taxa do grupo',
                               'divida o total do numerador pelo total do denominador (a taxa do total é recalculada, '
                               'nunca a média das linhas)'))
    alvo = re.search(r'SUMX\s*\([^,]+,\s*\[([^\]]+)\]', limpo(dax), re.I)
    if alvo and _e_taxa(alvo.group(1), leg):
        out.append(_achado('soma_de_taxas', 'critico', f'Soma de taxas ([{alvo.group(1)}])',
                           'percentual somado entre linhas não significa nada (passa de 100%)',
                           'recalcule a taxa no total: numerador total ÷ denominador total'))
    if META.search(nome) and re.match(r'AVERAGE\s*\(', up):
        usam = [n for n, x in leg['medidas'].items() if f'[{nome.upper()}]' in sem_texto(x['dax']).upper()
                and n != nome]
        if any(_e_taxa(u, leg) or re.search(r'\[[^\]]+\]\s*(<=|>=|<|>)', sem_texto(leg['medidas'][u]['dax']))
               for u in usam) or not usam:
            out.append(_achado('meta_media', 'alto', 'Meta do total pela média simples das metas',
                               'no total, a meta pesa igual a área pequena e a grande, mas a taxa do grupo pesa pelo '
                               'tamanho: o farol do total pode estar trocado',
                               'pese a meta de cada área pelo tamanho dela ("media_ponderada" no Deidara)'))
    # comparação de uma medida com número fixo: não conta 0 (> 0 é guarda contra vazio) nem coluna de calendário
    # comparada com ano ou ano-mês ([Ano-Mês Num] >= 202101 é um período, não uma meta)
    metas_fixas = [m for m in re.finditer(r'\[([^\]]+)\]\s*(<=|>=|<|>)\s*-?(\d+(?:\.\d+)?)\b', up)
                   if not re.fullmatch(r'0(?:\.0+)?', m.group(3))
                   and not re.search(r'ANO|M[EÊ]S|DATA|DATE|YEAR|MONTH|DIA|PER[IÍ]ODO', m.group(1))
                   and not re.fullmatch(r'(19|20)\d{2}(\d{2})?', m.group(3))]
    if metas_fixas and fns_condicao(up):
        out.append(_achado('meta_no_codigo', 'medio', 'Meta escrita dentro da fórmula',
                           'quando a meta mudar, alguém precisa achar e editar o DAX; o gestor não vê a meta no painel',
                           'leve a meta para uma medida própria (ou para a planilha de metas) e compare com ela',
                           re.search(r'\][^\n]{0,4}(<=|>=|<|>)\s*-?\d+(\.\d+)?', limpo(dax)).group(0)))
    if conhecido and not md.get('oculta'):
        if not (md.get('descricao') or '').strip():
            out.append(_achado('sem_descricao', 'medio', 'Sem descrição',
                               'quem lê o painel não sabe o que o número significa (numerador, filtro, período)',
                               'escreva a definição de negócio na descrição da medida'))
        texto = bool(re.search(r'"\s*&|&\s*"', dax))          # monta frase: formato de número não se aplica
        if not (md.get('formato') or '').strip() and pad['tipo'] not in ('svg', 'cor', 'texto') and not texto:
            out.append(_achado('sem_formato', 'baixo', 'Sem formato', 'cada visual mostra o número de um jeito',
                               'defina o formato (inteiro, percentual, moeda)'))
    literais = re.findall(r'"((?:[^"]|"")*)"', dax)
    for lit in literais:
        if re.search(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b', lit) or re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', lit):
            out.append(_achado('dado_pessoal', 'alto', 'Dado pessoal escrito na fórmula',
                               'CPF ou e-mail no DAX vai junto para quem abre o modelo (LGPD: só o necessário)',
                               'filtre por código ou por grupo, nunca por dado pessoal', '(valor omitido)'))
            break
    if nome in em_ciclo(leg):
        out.append(_achado('ciclo', 'critico', 'Dependência circular', 'a medida não calcula',
                       'quebre o ciclo: uma das medidas não pode citar a outra'))
    if '_limpos' not in leg:
        leg['_limpos'] = {}
        for n, x in leg['medidas'].items():
            leg['_limpos'].setdefault(limpo(x['dax']), []).append(n)
    gemeas = [n for n in leg['_limpos'].get(limpo(dax), []) if n != nome] if len(limpo(dax)) > 12 else []
    if gemeas:
        out.append(_achado('duplicada', 'baixo', f'Mesma fórmula de [{gemeas[0]}]',
                           'duas medidas iguais com nomes diferentes confundem quem escolhe no painel',
                           'fique com uma e apague a outra (ou explique a diferença na descrição)'))
    if re.search(r'DIVIDE\s*\(.*CALCULATE\s*\(.*\bALL\s*\(', up) and 'ALLSELECTED' not in up:
        out.append(_achado('participacao_all', 'baixo', '% do total com ALL',
                           'o total ignora também os segmentadores: com um filtro marcado, as linhas não somam 100%',
                           'se o total deve respeitar o filtro da página, use ALLSELECTED'))
    out.sort(key=lambda a: ORDEM[a['gravidade']])
    return out


def _coluna_de_funcao(c, up):
    """Colunas que uma função de tabela cria e o DAX lê depois ([Value] do construtor e do GENERATESERIES, o
    [Slope1] do LINESTX...): não são nome inventado."""
    if re.fullmatch(r'Value\d*', c):
        return True
    return bool(re.search(r'\bLINESTX?\s*\(', up)) and bool(re.fullmatch(
        r'Slope\d+|Intercept|CoefficientOfDetermination|StandardError\w*|DegreesOfFreedom|RegressionSumOfSquares|'
        r'ResidualSumOfSquares|FStatistic|StandardErrorY', c))


def _alvo_coluna(alvo):
    mt = re.search(r'\[([^\]]+)\]', alvo or '')
    return mt.group(1) if mt else None


def _alcanca(leg, de, para):
    """A tabela `de` filtra a tabela `para`? (do lado um para o lado muitos; nos dois sentidos, as duas vias)."""
    g = {}
    for r in leg['relacoes']:
        if not r.get('ativa', True):
            continue
        g.setdefault(r['para'], set()).add(r['de'])
        if str(r.get('cruzado', '')).lower().startswith('both'):
            g.setdefault(r['de'], set()).add(r['para'])
    vistos, fila = {de}, [de]
    while fila:
        t = fila.pop()
        for x in g.get(t, ()):
            if x not in vistos:
                vistos.add(x)
                fila.append(x)
    return para in vistos


def _cortes_parciais(nome, pad, leg):
    """Visuais do relatório em que uma coluna (eixo, linha, segmentador da página) chega no numerador e não no
    denominador da taxa (ou o contrário)."""
    num, den = _tabelas_da(pad['numerador'], leg), _tabelas_da(pad['denominador'], leg)
    cal = papeis(leg)['calendarios']

    def chega(t, tabs, medida):
        # o calendário chega na medida que lê a data dele (MAX/MIN da data, como o estoque na data)
        if t in cal and t in _tabelas_lidas_profundo(medida, leg):
            return True
        return all(_alcanca(leg, t, x) for x in tabs - cal)
    out = []
    for pg in leg.get('paginas') or []:
        segs = {(c['tabela'], c['nome']) for v in pg['visuais'] if v['tipo'] in ('segmentador', 'botoes')
                for c in v['campos'] if c['tipo'] == 'coluna'}
        for v in pg['visuais']:
            if not any(c['tipo'] == 'medida' and c['nome'] == nome for c in v['campos']):
                continue
            cols = segs | {(c['tabela'], c['nome']) for c in v['campos'] if c['tipo'] == 'coluna'}
            for t, c in sorted(cols):
                a, b = chega(t, num, pad['numerador']), chega(t, den, pad['denominador'])
                if num and den and a != b and (f'página {pg["nome"]}', f'{t}[{c}]') not in out:
                    out.append((f'página {pg["nome"]}', f'{t}[{c}]'))
    return out


def _tabelas_lidas_profundo(nome, leg, vistos=()):
    return _tabelas_da(nome, leg, vistos)


def fns_condicao(up):
    return bool(re.search(r'\b(IF|SWITCH|FILTER|CALCULATE)\s*\(', up))


def examinar(leg, so=None):
    """{'modelo': [achados], 'medidas': {nome: {...}}, 'nota_modelo', 'nota'}."""
    sasori.registrar_extras(leg.get('funcoes') or ())   # as funções do usuário do próprio modelo valem
    medidas = {}
    for nome, md in leg['medidas'].items():
        if so and chave(nome) not in {chave(x) for x in so}:
            continue
        pad = anatomia.padrao(md, leg)
        ach = exame_medida(nome, leg, pad)
        medidas[nome] = {'padrao': pad, 'leitura': anatomia.leitura(nome, md, pad), 'achados': ach,
                         'nota': nota(ach)}
    modelo = exame_modelo(leg)
    sasori.registrar_extras(())
    propria = {n: x['nota'] for n, x in medidas.items()}
    for nome, x in medidas.items():                          # o que vem das medidas de que ela depende
        deps = [d for d in dependencias(nome, leg) if d in medidas]
        x['herdados'] = list(dict.fromkeys((d, a['titulo']) for d in deps for a in medidas[d]['achados']
                                           if a['gravidade'] in ('critico', 'alto')))
        menor = min((propria[d] for d in deps), default=10.0)    # medida sobre medida errada também sai errada
        if menor < x['nota']:
            x['nota'], x['nota_herdada'] = menor, True
    visiveis = [x['nota'] for n, x in medidas.items() if not leg['medidas'][n].get('oculta')] or         [x['nota'] for x in medidas.values()]
    media = sum(visiveis) / len(visiveis) if visiveis else 10.0
    penal = sum({'critico': 1.0, 'alto': 0.5, 'medio': 0.2, 'baixo': 0.05}[a['gravidade']] for a in modelo)
    geral = media - penal
    todos = [a for x in medidas.values() for a in x['achados']] + modelo
    if any(a['gravidade'] == 'critico' for a in todos):      # um número errado no painel reprova o painel
        geral = min(geral, 4.5)
    elif any(a['gravidade'] == 'alto' for a in todos):
        geral = min(geral, 7.5)
    return {'modelo': modelo, 'medidas': medidas, 'nota_modelo': round(max(0.0, 10 - penal), 1),
            'nota': round(max(0.0, geral), 1)}



