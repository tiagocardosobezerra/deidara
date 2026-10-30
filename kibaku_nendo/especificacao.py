"""
A argila: lê o argila.json (a especificação do painel), confere cada nome
contra o catálogo da fonte de cada tabela (catalogo.py) e devolve o modelo
resolvido que os geradores (protótipo, SQL, TMDL, PBIR, documentação) usam.

Regras que valem aqui:
- tabela ou coluna que não está no catálogo da fonte é ERRO, nunca palpite;
- relacionamento só com prova do catálogo (FK do banco ou relação do modelo
  Power BI de origem); entre fontes diferentes, ou sem prova, só DECLARADO
  ("declarada": quem afirma e por quê), e isso vira aviso e documentação;
- nenhum dado: o argila.json descreve estrutura e regra, não conteúdo.

Formato completo do argila.json: referencias/argila.md.
"""

import re
from collections import deque

from tecnicas import sasori as dicionario
from tecnicas.luneta import prova

from kibaku_nendo.desenhos import (COR_BOA, COR_RUIM, PREFIXO_SVG, FORMATO_DAX,
                                    _texto_dax, _html_kpis, _svg_barra_meta, _svg_bolha, _svg_dispersao,
                                    _svg_espinha, _svg_estrelas, _svg_iniciais, _svg_pilula, _svg_posicao,
                                    _svg_progresso, _svg_radar, _svg_seta, _svg_variacao, conferir_svg)  # noqa: F401  (reexporta para quem já usa)
from kibaku_nendo.util import (FORMATOS, numero_br, NUMERICAS, SQL_POR_FAMILIA, chave, dax_coluna, dax_medida, dax_tabela,
                   familia_da_coluna, sql_tipo, tipo_tmdl)

TIPOS_TABELA = {'fato', 'dimensao'}
AGREGACOES = {
    'soma': 'SUM', 'media': 'AVERAGE', 'minimo': 'MIN', 'maximo': 'MAX',
    'contagem': 'COUNT', 'contagem_distinta': 'DISTINCTCOUNTNOBLANK', 'contagem_linhas': 'COUNTROWS',
}
AGREGACOES_NUMERICAS = {'soma', 'media'}
TEMPO = {'acumulado_ano', 'ano_anterior', 'variacao_ano_anterior', 'variacao_mes_anterior', 'media_mensal',
         'movel_12m'}

TIPOS_VISUAL = {
    'cartao': 'card', 'barras': 'clusteredBarChart', 'colunas': 'clusteredColumnChart',
    'linha': 'lineChart', 'rosca': 'donutChart', 'tabela': 'tableEx', 'matriz': 'pivotTable',
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
def _pista_medida(nome, nomes):
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


def _depende_de(ref):
    """Chaves de raiz de que uma referência 'Tabela[Coluna]' depende."""
    mt = re.fullmatch(r"\s*'?(.+?)'?\[(.+)\]\s*", ref or '') or re.fullmatch(r'([^.\[]+)\.(.+)', ref or '')
    if not mt:
        return ()
    return (chave_tabela(mt.group(1)), chave_coluna(mt.group(1), mt.group(2)))


def _familia(oc):
    return oc.get('familia') or familia_da_coluna(oc)


def resolver(argila, catalogos):
    """`catalogos`: {nome da fonte: catalogo.Fonte}. Devolve (modelo, problemas).
    Com erro, o modelo não deve ser usado."""
    p = Problemas()
    m = {
        'projeto': (argila.get('projeto') or '').strip(),
        'descricao': argila.get('descricao', ''),
        'publico': argila.get('publico', ''),
        'responsavel': argila.get('responsavel', ''),
        'versao': str(argila.get('versao', '')),
        'fontes': _fontes(argila, catalogos, p),
        '_catalogos': catalogos,
        'tema': {'cores': ['#118DFF', '#12239E', '#E66C37', '#6B007B', '#E044A7', '#744EC2', '#D9B300',
                           '#D64550'], 'fundo': '#FFFFFF', 'texto': '#252423',
                 **{k: v for k, v in (argila.get('tema') if isinstance(argila.get('tema'), dict) else {}).items()
                    if k != 'paleta'}},
        'tabelas': [], 'relacionamentos': [], 'medidas': [], 'paginas': [], 'seguranca': [], 'pendencias': [],
    }
    if not m['projeto']:
        p.erro('projeto', 'informe o nome do projeto')
    _modelo(argila, m, p)
    _tabelas(argila, catalogos, m, p)
    _calendario(argila, m, p)
    _relacionamentos(argila, catalogos, m, p)
    _medidas(argila, m, p)
    _grupo_calculo(argila, m, p)
    _seguranca(argila, m, p)
    _paginas(argila, m, p)
    _privacidade(m, p)
    _design(argila, m, p)
    _tours(m, p)
    if not m['versao']:
        p.aviso('versao', 'sem "versao" no argila.json: informe (ex.: "1.0") para o histórico de mudanças')
    for campo in ('descricao', 'publico'):
        if not (m[campo] or '').strip() or m[campo].strip().upper().startswith('A DEFINIR'):
            m['pendencias'].append(f'painel: "{campo}" pendente')
            p.aviso(f'painel {campo}', f'definição pendente: escreva {"para que serve o painel" if campo == "descricao" else "para quem é o painel"} '
                                       '(aparece no protótipo e no Memory Card); o aprovar recusa sem ela')
    for f in m['fontes'].values():
        if f['tipo'] == 'sqlserver' and any(t.get('fonte') == f['nome'] for t in m['tabelas']) and \
                ('SEU_' in str(f.get('servidor')) or 'SEU_' in str(f.get('banco'))):
            p.aviso(f'fonte {f["nome"]}', 'servidor/banco ainda de exemplo (SEU_SERVIDOR/SEU_BANCO): informe em "fontes" '
                                         '(são os valores iniciais dos parâmetros do Power BI e aparecem no LEIA-ME)')
    return m, p


def _fontes(argila, catalogos, p):
    out = {}
    for nome, cat in catalogos.items():
        cfg = dict((argila.get('fontes') or {}).get(nome) or {})
        cfg.pop('catalogo', None)
        f = {'nome': nome, 'tipo': cat.tipo, 'receita': cat.receita, 'expressoes': cat.expressoes, **cfg}
        if cat.tipo == 'sqlserver':
            f = {'servidor': 'SEU_SERVIDOR', 'banco': 'SEU_BANCO', 'esquema_origem': 'dbo', 'esquema_views': 'bi', **f}
        out[nome] = f
    return out


def _privacidade(m, p):
    """Dado pessoal (CPF, e-mail, nome de pessoa...) no modelo sem nenhum uso: aviso."""
    from tecnicas.te_no_kuchi import pessoal as _pessoal
    usados = set()
    for pg in m['paginas']:
        for v in pg['visuais']:
            for x in [v['categoria'], v['legenda']] + v['linhas'] + v['colunas'] + v['campos']:
                if x and x['tipo'] == 'coluna':
                    usados.add((x['tabela'], x['nome']))
    for md in m['medidas']:
        for tn, n in referencias_dax(md.get('dax') or ''):
            if tn:
                usados.add((tn, n))
    for papel in m.get('seguranca', []):
        for r in papel['regras']:
            for tn, n in referencias_dax(r['filtro']):
                usados.add((tn or r['tabela'], n))
    for t in m['tabelas']:
        if not t.get('origem'):
            continue
        for c in t['colunas']:
            if c['origem'] and not c['oculta'] and (t['nome'], c['nome']) not in usados and \
                    _pessoal({'nome': t['origem']}, {'coluna': c['origem']}):
                p.aviso(f'tabela {t["nome"]}', f'[Privacidade] "{c["nome"]}" identifica uma pessoa e não é usada em '
                                              'nenhum visual: tire do modelo (LGPD: só o necessário)')


def _seguranca(argila, m, p):
    """RLS: cada papel filtra uma ou mais tabelas com uma expressão DAX booleana."""
    nomes = set()
    for i, papel in enumerate(argila.get('seguranca') or []):
        nome = (papel.get('papel') or '').strip()
        onde = f'seguranca[{i}] {nome}'
        if not nome or chave(nome) in nomes:
            p.erro(onde, 'papel sem nome ou repetido')
            continue
        nomes.add(chave(nome))
        regras = []
        for j, r in enumerate(papel.get('regras') or []):
            t = tabela_do_modelo(m, r.get('tabela', ''))
            if not t or not r.get('filtro'):
                p.erro(onde, f'regra {j + 1}: informe "tabela" (do modelo) e "filtro" (DAX booleano)')
                continue
            for tn, cn in referencias_dax(r['filtro']):
                tt = tabela_do_modelo(m, tn or t['nome'])
                if not tt or not coluna_do_modelo(tt, cn):
                    p.erro(onde, f'regra {j + 1}: {tn or t["nome"]}[{cn}] não é coluna do modelo')
            _conferir_funcoes(r['filtro'], p, f'{onde} regra {j + 1}')
            regras.append({'tabela': t['nome'], 'filtro': r['filtro'].strip()})
            if 'USERPRINCIPALNAME' not in r['filtro'].upper() and 'USERNAME' not in r['filtro'].upper():
                p.aviso(onde, f'regra {j + 1} não usa USERPRINCIPALNAME(): o filtro vale igual para todos do papel')
        if not regras:
            p.erro(onde, 'papel sem nenhuma regra válida')
            continue
        m['seguranca'].append({'papel': nome, 'descricao': papel.get('descricao', ''), 'regras': regras})


# ------------------------------------------------------------------ tabelas
def _tabelas(argila, catalogos, m, p):
    nomes = set()
    unica = next(iter(catalogos)) if len(catalogos) == 1 else None
    if not argila.get('tabelas'):
        p.erro('tabelas', 'nenhuma tabela no modelo')
    for i, t in enumerate(argila.get('tabelas') or []):
        onde = f'tabelas[{i}]'
        nome = (t.get('nome') or '').strip()
        if not nome:
            p.erro(onde, 'tabela sem "nome"')
            continue
        onde = f'tabela {nome}'
        if chave(nome) in nomes:
            p.erro(onde, 'nome repetido no modelo')
        nomes.add(chave(nome))
        tipo = t.get('tipo', 'dimensao')
        if tipo not in TIPOS_TABELA:
            p.erro(onde, f'tipo "{tipo}" inválido (use fato ou dimensao)')
        nome_fonte = t.get('fonte') or unica
        fonte = catalogos.get(nome_fonte or '')
        if not fonte:
            p.erro(onde, f'fonte "{t.get("fonte")}" não está em "fontes" ({", ".join(catalogos) or "nenhuma"})'
                   if t.get('fonte') else 'informe "fonte" (o argila.json tem mais de uma)')
            continue
        origem = fonte.tabela(t.get('origem', ''))
        if not origem:
            sug = fonte.parecidas(t.get('origem', ''))
            p.erro(onde, f'origem "{t.get("origem")}" não está no catálogo da fonte {fonte.nome}'
                         + (f'; parecidas: {", ".join(sug)}' if sug else
                            '; rode a receita com essa tabela e o `catalogar` de novo'), raiz=chave_tabela(nome))
            continue
        tab = {'nome': nome, 'tipo': tipo, 'origem': origem['nome'], 'fonte': fonte.nome, 'fonte_tipo': fonte.tipo,
               'expressao_m': origem['expressao_m'], 'descricao': t.get('descricao') or origem['descricao'] or '',
               'filtro': t.get('filtro'), 'colunas': [], 'calendario': False, 'pk': origem['pk']}
        if t.get('filtro') and fonte.tipo != 'sqlserver':
            p.erro(onde, '"filtro" (WHERE da view) só vale para fonte sqlserver; filtre na própria consulta Power Query')
        elif t.get('filtro'):
            p.aviso(onde, 'o "filtro" entra no WHERE da view sem conferência de nomes: revise o SQL gerado')
        if fonte.tipo != 'sqlserver' and not origem['expressao_m']:
            p.erro(onde, f'a fonte {fonte.nome} não tem a consulta Power Query de {origem["nome"]}: rode o '
                         '`catalogar` com --m (receita m) ou use a receita dax')
        cols = set()
        for j, c in enumerate(t.get('colunas') or []):
            if isinstance(c, str):
                c = {'coluna': c}
            oc = fonte.coluna(origem['nome'], c.get('coluna', ''))
            ondec = f'{onde}.colunas[{j}]'
            if not oc:
                sug = fonte.colunas_parecidas(origem['nome'], c.get('coluna', ''))
                p.erro(ondec, f'coluna "{c.get("coluna")}" não existe em {origem["nome"]}'
                              + (f'; parecidas: {", ".join(sug)}' if sug else ''),
                       raiz=chave_coluna(nome, c.get('nome') or c.get('coluna', '')))
                continue
            familia = _familia(oc)
            if c.get('tipo'):
                familia = c['tipo']
            elif not familia or oc.get('tipo_indefinido'):
                familia = 'texto'
                p.aviso(ondec, f'{origem["nome"]}.{oc["coluna"]} veio sem tipo da fonte {fonte.nome}: tratada como '
                               'texto; defina o tipo na consulta de origem ou informe "tipo" aqui')
            col = _coluna(c.get('nome') or oc['coluna'], oc['coluna'], familia,
                          descricao=c.get('descricao') or oc.get('descricao') or '',
                          oculta=bool(c.get('oculta')), formato=c.get('formato') or oc.get('formato_sugerido'))
            col['sql_tipo'] = sql_tipo(oc) if fonte.tipo == 'sqlserver' else None
            if chave(col['nome']) in cols:
                p.erro(ondec, f'nome de coluna "{col["nome"]}" repetido')
            cols.add(chave(col['nome']))
            if col['formato'] and col['formato'] not in FORMATOS:
                p.erro(ondec, f'formato "{col["formato"]}" inválido ({", ".join(FORMATOS)})')
            tab['colunas'].append(col)
        if not tab['colunas']:
            p.erro(onde, 'nenhuma coluna válida')
        m['tabelas'].append(tab)


def _coluna(nome, origem, familia, descricao='', oculta=False, formato=None, expressao_sql=None):
    if not formato:
        formato = {'inteiro': None, 'decimal': 'decimal', 'real': 'decimal', 'data': 'data',
                   'datahora': 'data', 'hora': 'hora'}.get(familia)
    return {'nome': nome, 'origem': origem, 'familia': familia, 'tipo_tmdl': tipo_tmdl(familia),
            'descricao': descricao, 'oculta': oculta, 'formato': formato, 'expressao_sql': expressao_sql,
            'como_data': False, 'gerada': origem is None, 'sql_tipo': None, 'cast_sql': None, 'chave_campos': None}


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


# --------------------------------------------------------------- calendário
COLUNAS_CALENDARIO = [
    ('Data', 'data', 'data'), ('Ano', 'inteiro', None), ('Mês', 'inteiro', None),
    ('Nome do Mês', 'texto', None), ('Trimestre', 'texto', None), ('Ano-Mês', 'texto', None),
    ('Mês/Ano', 'texto', None), ('Ano-Trimestre', 'texto', None), ('Ano-Mês Num', 'inteiro', None),
    ('Ano-Trimestre Num', 'inteiro', None),
]
CALENDARIO_OCULTAS = {'Ano-Mês Num', 'Ano-Trimestre Num'}
# colunas do calendário que repetem todo ano: sem o ano no filtro, somam todos os anos
CALENDARIO_SEM_ANO = {'Mês', 'Nome do Mês', 'Trimestre'}


def _calendario(argila, m, p):
    cal = argila.get('calendario')
    if not cal:
        m['calendario'] = None
        return
    nome = cal.get('nome', 'dCalendario')
    inicio, fim = int(cal.get('inicio', 2018)), int(cal.get('fim', 2030))
    if fim < inicio:
        p.erro('calendario', 'fim antes do início')
    tab = {'nome': nome, 'tipo': 'dimensao', 'origem': None, 'descricao': 'Calendário gerado pelo Deidara',
           'filtro': None, 'colunas': [], 'calendario': True, 'pk': [], 'inicio': inicio, 'fim': fim}
    for n, fam, fmt in COLUNAS_CALENDARIO:
        c = _coluna(n, None, fam, formato=fmt)
        c['oculta'] = n in CALENDARIO_OCULTAS
        tab['colunas'].append(c)
    if tabela_do_modelo(m, nome):
        p.erro('calendario', f'já existe tabela chamada {nome}')
    m['tabelas'].append(tab)
    m['calendario'] = {'tabela': nome, 'datas': []}
    ativas = {}
    for i, d in enumerate(cal.get('datas') or []):
        onde = f'calendario.datas[{i}]'
        t = tabela_do_modelo(m, d.get('tabela', ''))
        c = coluna_do_modelo(t, d.get('coluna', '')) if t else None
        if not c:
            p.erro(onde, f'{d.get("tabela")}[{d.get("coluna")}] não está no modelo',
                   depende=_depende_de(f'{d.get("tabela")}[{d.get("coluna")}]'))
            continue
        if c['familia'] not in ('data', 'datahora'):
            p.erro(onde, f'{t["nome"]}[{c["nome"]}] não é data ({c["familia"]})')
            continue
        c['como_data'] = True
        c['familia'] = 'data'
        ativo = d.get('ativo', t['nome'] not in ativas)
        if ativo and t['nome'] in ativas:
            p.erro(onde, f'{t["nome"]} já tem uma data ativa ({ativas[t["nome"]]}); marque "ativo": false '
                         'e use USERELATIONSHIP na medida')
        if ativo:
            ativas[t['nome']] = c['nome']
        m['relacionamentos'].append({'de': t['nome'], 'de_coluna': c['nome'], 'para': nome, 'para_coluna': 'Data',
                                     'ativo': ativo, 'prova': 'calendário (gerado)', 'composta': False,
                                     'campos': [], 'aviso': None})
        m['calendario']['datas'].append({'tabela': t['nome'], 'coluna': c['nome'], 'ativo': ativo})
    if not m['calendario']['datas']:
        p.aviso('calendario', 'calendário sem nenhuma data ligada: as medidas de tempo não vão funcionar')


# ---------------------------------------------------------- relacionamentos
def _relacionamentos(argila, catalogos, m, p):
    for i, r in enumerate(argila.get('relacionamentos') or []):
        onde = f'relacionamentos[{i}] {r.get("de")} -> {r.get("para")}'
        de, para = tabela_do_modelo(m, r.get('de', '')), tabela_do_modelo(m, r.get('para', ''))
        if not de or not para:
            p.erro(onde, 'as duas pontas precisam ser tabelas do modelo ("de" = lado muitos, "para" = lado um)',
                   depende=(chave_tabela(r.get('de', '')), chave_tabela(r.get('para', ''))))
            continue
        if not de['origem'] or not para['origem']:
            p.erro(onde, 'use "calendario.datas" para ligar ao calendário')
            continue
        if r.get('declarada'):
            _declarada(catalogos, m, de, para, r, p, onde)
            continue
        if de['fonte'] != para['fonte']:
            p.erro(onde, f'{de["nome"]} ({de["fonte"]}) e {para["nome"]} ({para["fonte"]}) vêm de fontes diferentes: '
                         'não existe FK entre elas. Confirme os campos com o dono do dado e declare: "declarada": '
                         '{"campos": [["CAMPO_DA_FILHA", "CAMPO_DA_MAE"]], "por": "quem confirmou", "motivo": "..."}')
            continue
        fonte = catalogos[de['fonte']]
        fks = fonte.fks_entre(de['origem'], para['origem'])
        via = [chave(x) for x in (r.get('via') or [])]
        if via:
            fks = [fk for fk in fks if sorted(chave(x['campo_filho']) for x in fk['colunas']) == sorted(via)]
        if not fks:
            if fonte.fks_entre(para['origem'], de['origem']):
                p.erro(onde, f'a ligação vai de {para["origem"]} (filha) para {de["origem"]} (mãe): inverta '
                             '"de" e "para" (o "para" é sempre o lado um, a tabela mãe)')
            else:
                p.erro(onde, f'o catálogo da fonte {fonte.nome} não tem ligação de {de["origem"]} para {para["origem"]}: '
                             'não invente. Se o dono do dado confirmar os campos, use "declarada"')
            continue
        if len(fks) > 1:
            p.erro(onde, 'mais de uma ligação entre as tabelas; escolha com "via": '
                         + ' | '.join('[' + ', '.join(x['campo_filho'] for x in fk['colunas']) + ']' for fk in fks))
            continue
        fk = fks[0]
        campos = [(x['campo_filho'], x['campo_mae']) for x in fk['colunas']]
        regra = dict(r)
        regra.setdefault('ativo', fk.get('ativa', True))
        _ligar(catalogos, m, de, para, campos, regra,
               f'{fk["origem"]}' + (f' ({fk["nome"]})' if fk.get('nome') and fk['origem'] == 'constraint' else ''),
               p, onde)
    _conferir_ativos(m, p)


def _declarada(catalogos, m, de, para, r, p, onde):
    d = r['declarada']
    campos = [tuple(x) for x in d.get('campos') or [] if isinstance(x, (list, tuple)) and len(x) == 2]
    if not campos or not d.get('por'):
        p.erro(onde, '"declarada" pede "campos" ([["CAMPO_DA_FILHA", "CAMPO_DA_MAE"]]) e "por" (quem confirmou)')
        return
    if d['por'].strip().upper() == 'A CONFIRMAR':
        p.erro(onde, f'ligação sugerida ainda não confirmada: confira os campos com o dono do dado e rode '
                     f'`deidara.py confirmar <argila> --ligacao {de["nome"]}->{para["nome"]} --por "<quem confirmou>"` '
                     '(ou --remover)')
        return
    ok = True
    for filho, mae in campos:
        for t, campo in ((de, filho), (para, mae)):
            if not catalogos[t['fonte']].coluna(t['origem'], campo):
                sug = catalogos[t['fonte']].colunas_parecidas(t['origem'], campo)
                p.erro(onde, f'campo "{campo}" não existe em {t["origem"]} (fonte {t["fonte"]})'
                             + (f'; parecidas: {", ".join(sug)}' if sug else ''))
                ok = False
    if not ok:
        return
    rotulo = f'declarada por {d["por"]}'
    medida_na_fonte = d.get('prova')
    if medida_na_fonte:
        veredito, explicacao = prova.avaliar(medida_na_fonte)
        rotulo += '; ' + prova.texto(medida_na_fonte)
        if veredito == 'reprovada':
            p.erro(onde, f'a receita de prova reprovou a ligação: {explicacao}')
            return
        if veredito != 'provada':
            p.aviso(onde, f'ligação declarada por {d["por"]}, prova {veredito}: {explicacao}')
    else:
        p.aviso(onde, f'ligação DECLARADA por {d["por"]}, sem prova na fonte ({d.get("motivo") or "sem motivo informado"}): '
                      'rode a receita de prova (`deidara.py receita prova`) ou confira na primeira atualização (chave '
                      'repetida no lado um derruba a atualização; código sem par some do corte)')
    _ligar(catalogos, m, de, para, campos, r, rotulo, p, onde)


def _ligar(catalogos, m, de, para, campos, r, prova, p, onde):
    if len(campos) == 1:
        filho, mae = campos[0]
        cf = _garantir_coluna(catalogos, de, filho, p, onde)
        cm = _garantir_coluna(catalogos, para, mae, p, onde)
        if not cf or not cm:
            return
        if cf['tipo_tmdl'] != cm['tipo_tmdl']:
            # o modelo tabular não relaciona tipos diferentes: a filha é convertida para o tipo da mãe
            # (na view, se a filha vem do SQL Server; no Power Query, nos outros casos)
            alvo = cm.get('sql_tipo') or SQL_POR_FAMILIA.get(cm['familia'], 'nvarchar(4000)')
            if de['fonte_tipo'] == 'sqlserver':
                cf['cast_sql'] = alvo
            cf['familia'], cf['tipo_tmdl'] = cm['familia'], cm['tipo_tmdl']
            onde_conv = f'na view ({alvo})' if de['fonte_tipo'] == 'sqlserver' else 'no Power Query'
            p.aviso(onde, f'tipos diferentes nas pontas: {de["nome"]}[{cf["nome"]}] é convertida para {cm["familia"]} '
                          f'{onde_conv} (o Power BI não relaciona tipos diferentes); confira se a conversão não perde valor')
        de_col, para_col, composta = cf['nome'], cm['nome'], False
    else:
        nome = f'Chave {para["nome"]}'
        de_col = _chave_composta(catalogos, de, nome, [f for f, _ in campos])
        para_col = _chave_composta(catalogos, para, nome, [mm for _, mm in campos])
        composta = True
    m['relacionamentos'].append({'de': de['nome'], 'de_coluna': de_col, 'para': para['nome'], 'para_coluna': para_col,
                                 'ativo': r.get('ativo', True), 'prova': prova, 'composta': composta,
                                 'campos': campos, 'aviso': None})


def _garantir_coluna(catalogos, t, origem, p, onde):
    c = coluna_por_origem(t, origem)
    if c:
        return c
    # a coluna de ligação não foi pedida: entra oculta, com o tipo do catálogo
    oc = catalogos[t['fonte']].coluna(t['origem'], origem) or {}
    c = _coluna(oc.get('coluna', origem), oc.get('coluna', origem), _familia(oc) or 'texto',
                descricao=oc.get('descricao') or '', oculta=True)
    c['sql_tipo'] = sql_tipo(oc) if t['fonte_tipo'] == 'sqlserver' else None
    c['auto'] = True
    if coluna_do_modelo(t, origem):
        p.erro(onde, f'{t["nome"]} já tem uma coluna chamada {origem} com outra origem')
        return None
    t['colunas'].append(c)
    return c


def _chave_composta(catalogos, t, nome, campos):
    existente = coluna_do_modelo(t, nome)
    if existente:
        return existente['nome']
    expr = None
    if t['fonte_tipo'] == 'sqlserver':
        expr = 'CONCAT(' + ", N'|', ".join(_parte_da_chave(catalogos, t, c) for c in campos) + ')'
    c = _coluna(nome, None, 'texto', descricao='Chave composta gerada pelo Deidara: ' + ' + '.join(campos),
                oculta=True, expressao_sql=expr)
    c['chave_campos'] = list(campos)
    t['colunas'].append(c)
    return nome


def _parte_da_chave(catalogos, t, campo):
    """Um campo da chave composta como texto estável: data em ISO (independe do
    idioma da sessão), sem espaço à direita (char) e NULL marcado (senão NULL e
    '' viram a mesma chave)."""
    familia = _familia(catalogos[t['fonte']].coluna(t['origem'], campo) or {})
    estilo = ', 126' if familia in ('data', 'datahora', 'hora') else ''
    return f"ISNULL(RTRIM(CONVERT(nvarchar(100), t.[{campo}]{estilo})), N'∅')"


def _conferir_ativos(m, p):
    vistos = {}
    for r in m['relacionamentos']:
        if not r['ativo']:
            continue
        k = (chave(r['de']), chave(r['para']))
        if k in vistos:
            p.erro(f'relacionamentos {r["de"]} -> {r["para"]}', 'duas relações ativas entre as mesmas tabelas; '
                   'marque uma com "ativo": false')
        vistos[k] = r


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


def _medidas(argila, m, p):
    fatos = [t for t in m['tabelas'] if t['tipo'] == 'fato']
    nomes = {}
    brutas = argila.get('medidas') or []
    for i, md in enumerate(brutas):
        nome = (md.get('nome') or '').strip()
        if not nome:
            p.erro(f'medidas[{i}]', 'medida sem "nome"')
            continue
        if chave(nome) in nomes:
            p.erro(f'medida {nome}', 'nome repetido')
        nomes[chave(nome)] = md
    for i, md in enumerate(brutas):
        nome = (md.get('nome') or '').strip()
        if not nome:
            continue
        onde = f'medida {nome}'
        formato = md.get('formato') or _formato_padrao(md, nomes)
        if formato not in FORMATOS:
            p.erro(onde, f'formato "{formato}" inválido ({", ".join(FORMATOS)})')
        r = {'nome': nome, 'formato': formato, 'descricao': md.get('descricao', ''),
             'pasta': md.get('pasta', ''), 'tabela': md.get('tabela'), 'dax': None,
             'conferencia_sql': None, 'tipo': None, 'meta': md.get('meta'),
             'polaridade': md.get('polaridade', 'maior_melhor'), 'oculta': bool(md.get('oculta')),
             'meta_medida': None, 'cor_medida': None}
        try:
            if 'agregacao' in md:
                _medida_agregacao(m, md, r, p, onde)
            elif md.get('tipo') == 'divisao':
                r['tipo'] = 'divisao'
                for k in ('numerador', 'denominador'):
                    if chave(md.get(k, '')) not in nomes:
                        p.erro(onde, f'{k} "{md.get(k)}" não é uma medida do modelo' + _pista_medida(md.get(k), nomes))
                r['dax'] = f'DIVIDE({dax_medida(md.get("numerador", ""))}, {dax_medida(md.get("denominador", ""))})'
                r['depende'] = [md.get('numerador'), md.get('denominador')]
            elif md.get('tipo') in TEMPO:
                _medida_tempo(m, md, r, p, onde, nomes)
            elif md.get('tipo') == 'estoque_na_data':
                _medida_estoque(m, md, r, p, onde)
            elif md.get('tipo') in SVG_GERADAS:
                r['tipo'], r['formato'], r['imagem'], r['dax'] = md['tipo'], None, True, ''
                r['svg'] = {'medida': md.get('medida') or (md.get('medidas') or [None])[0], 'categoria': md.get('categoria'),
                            'comparar': md.get('comparar'), 'ordem': md.get('ordem'), 'medidas': md.get('medidas'),
                            'coluna_matriz': md.get('colunas'), 'maximo': md.get('maximo')}
            elif md.get('tipo') in EXTRAS:
                r['tipo'], r['dax'], r['extra'] = md['tipo'], '', dict(md)
                if md['tipo'] in ('svg_iniciais', 'svg_dispersao', 'svg_espinha'):
                    r['imagem'], r['formato'] = True, None
                if md['tipo'] in ('cor_destaque', 'aviso', 'html_kpis'):
                    r['formato'] = None
            elif md.get('tipo') in RANKINGS:
                r['tipo'], r['dax'] = md['tipo'], ''
                r['ranking'] = {'medida': md.get('medida'), 'categoria': md.get('categoria'), 'ordem': md.get('ordem'),
                                'n': md.get('n', 5), 'formato_dado': md.get('formato'), 'comparar': md.get('comparar')}
            elif md.get('dax'):
                r['tipo'] = 'dax'
                r['dax'] = md['dax'].strip()
                _conferir_refs(m, r, nomes, p, onde)
                if 'data:image/svg+xml' in r['dax']:
                    r['imagem'], r['formato'] = True, None
                    conferir_svg(r['dax'], p, onde)
            else:
                p.erro(onde, 'informe "agregacao", "tipo" (divisao, acumulado_ano, ano_anterior, '
                             'variacao_ano_anterior, variacao_mes_anterior, estoque_na_data, media_mensal, '
                             'svg_barra_meta...) ou "dax"')
                continue
        except KeyError as e:
            p.erro(onde, f'falta o campo {e}')
            continue
        if not r['tabela']:
            r['tabela'] = fatos[0]['nome'] if fatos else (m['tabelas'][0]['nome'] if m['tabelas'] else '')
        home = tabela_do_modelo(m, r['tabela'])
        if not home:
            p.erro(onde, f'tabela "{r["tabela"]}" não está no modelo')
        elif coluna_do_modelo(home, nome):
            p.erro(onde, f'{home["nome"]} já tem uma coluna chamada "{nome}": renomeie a medida')
        else:
            r['tabela'] = home['nome']
        m['medidas'].append(r)
    _metas(m, p)
    _svgs(m, p)
    _extras(m, p)
    _ciclos(m, p)
    for md in m['medidas']:
        if md.get('tipo') not in ('cor', 'meta') and (not (md.get('descricao') or '').strip()
                                                      or md['descricao'].strip().upper().startswith('A DEFINIR')):
            m['pendencias'].append(f'medida {md["nome"]}: definição de negócio pendente')
            p.aviso(f'medida {md["nome"]}', 'definição pendente: escreva o que o número significa (numerador, '
                                            'filtro, período) antes de mostrar ao gestor; o aprovar recusa sem ela')


SVG_GERADAS = ('svg_barra_meta', 'svg_pilula', 'svg_seta', 'svg_posicao', 'svg_radar', 'svg_bolha', 'svg_variacao',
               'svg_estrelas', 'svg_progresso')
RANKINGS = ('posicao', 'pareto', 'melhores_piores', 'lista_top', 'jitter', 'impacto')
DIAGNOSTICOS = ('jitter', 'impacto')        # da causa raiz: feitas para o eixo do gráfico, não para a tabela


def _svgs(m, p):
    """As medidas que o Deidara escreve a partir de outra medida e da coluna das linhas da tabela: as imagens SVG
    (barra contra a meta, pílula de status, seta de variação, selo de posição; referencias/svg.md) e as de
    classificação (posição, Pareto, melhores e piores, jitter, impacto; dicionario/visuais.json). Todas param no
    total."""
    todas = {chave(x['nome']): x for x in m['medidas'] if x['tipo'] not in ('cor',)}
    novas = []
    for md in m['medidas']:
        if md.get('tipo') not in SVG_GERADAS + RANKINGS:
            continue
        onde = f'medida {md["nome"]}'
        cfg = md.get('svg') or md.get('ranking')
        base = medida(m, cfg.get('medida') or '')
        if not base:
            p.erro(onde, f'"medida" ("{cfg.get("medida")}") não é uma medida do modelo' + _pista_medida(cfg.get('medida'), todas))
            continue
        tc, cc = _resolver_coluna(m, cfg.get('categoria'))
        if not cc:
            p.erro(onde, f'"categoria" ("{cfg.get("categoria")}") precisa ser a coluna das linhas da tabela'
                         + pista_coluna(m, cfg.get('categoria')))
            continue
        col = dax_coluna(tc['nome'], cc['nome'])
        maior = base['polaridade'] == 'maior_melhor'
        ordem = cfg.get('ordem') or ('maior_primeiro' if maior else 'menor_primeiro')
        if ordem not in ('maior_primeiro', 'menor_primeiro'):
            p.erro(onde, '"ordem" deve ser maior_primeiro ou menor_primeiro')
            continue
        sentido = 'DESC' if ordem == 'maior_primeiro' else 'ASC'
        b = dax_medida(base['nome'])
        cfg.update({'base': base['nome'], 'tabela': tc['nome'], 'coluna': cc['nome'], 'ordem': ordem})
        md['polaridade'] = base['polaridade']
        md['depende'] = [base['nome']]
        tipo = md['tipo']
        if tipo == 'svg_radar':
            eixos = [medida(m, x) for x in (cfg.get('medidas') or [])]
            if not 3 <= len(eixos) <= 8 or not all(eixos):
                p.erro(onde, '"medidas" pede de 3 a 8 medidas do modelo (um eixo do radar por medida)')
                continue
            cfg['medidas'] = [x['nome'] for x in eixos]
            md['depende'] = list(cfg['medidas'])
        if tipo == 'svg_bolha':
            tl, cl = _resolver_coluna(m, cfg.get('coluna_matriz'))
            if not cl:
                p.erro(onde, '"colunas" precisa ser a coluna das colunas da matriz' + pista_coluna(m, cfg.get('coluna_matriz')))
                continue
            cfg['coluna_matriz'] = [tl['nome'], cl['nome']]
        maximo = cfg.get('maximo')
        if tipo == 'svg_estrelas' and maximo is not None and (isinstance(maximo, bool)
                                                              or not isinstance(maximo, (int, float)) or maximo <= 0):
            p.erro(onde, '"maximo" deve ser um número maior que zero (a nota que vale cinco estrelas)')
            continue
        if tipo in ('svg_barra_meta', 'svg_pilula', 'svg_progresso') and not base.get('meta_medida'):
            p.erro(onde, f'a medida "{base["nome"]}" não tem meta: dê "meta" (número ou medida) a ela primeiro')
            continue
        if tipo in ('svg_seta', 'svg_variacao', 'impacto'):
            comp = medida(m, cfg.get('comparar') or '')
            if not comp:
                p.erro(onde, f'"comparar" ("{cfg.get("comparar")}") precisa ser a medida do valor anterior '
                             '(ex.: a de ano anterior)' + _pista_medida(cfg.get('comparar'), todas))
                continue
            cfg['comparar'] = comp['nome']
            md['depende'].append(comp['nome'])
        if base.get('meta_medida'):
            cfg['meta'] = base['meta_medida']
        op = '>=' if maior else '<='
        if tipo == 'svg_barra_meta':
            md['depende'].append(base['meta_medida'])
            md['dax'] = _svg_barra_meta(b, dax_medida(base['meta_medida']), col, op)
        elif tipo == 'svg_pilula':
            md['depende'].append(base['meta_medida'])
            md['dax'] = _svg_pilula(b, dax_medida(base['meta_medida']), col, op)
        elif tipo == 'svg_seta':
            md['dax'] = _svg_seta(b, dax_medida(cfg['comparar']), col, op)
        elif tipo == 'svg_posicao':
            md['dax'] = _svg_posicao(b, col, sentido, (m['tema']['cores'] or ['#118DFF'])[0])
        elif tipo == 'svg_radar':
            md['dax'] = _svg_radar([dax_medida(x) for x in cfg['medidas']], col, (m['tema']['cores'] or ['#118DFF'])[0])
        elif tipo == 'svg_bolha':
            md['dax'] = _svg_bolha(b, col, dax_coluna(*cfg['coluna_matriz']), (m['tema']['cores'] or ['#118DFF'])[0])
        elif tipo == 'svg_variacao':
            md['dax'] = _svg_variacao(b, dax_medida(cfg['comparar']), col, '>=' if maior else '<=')
        elif tipo == 'svg_estrelas':
            md['dax'] = _svg_estrelas(b, col, maior, maximo)
        elif tipo == 'svg_progresso':
            md['depende'].append(base['meta_medida'])
            md['dax'] = _svg_progresso(b, dax_medida(base['meta_medida']), col, op)
        elif tipo == 'lista_top':
            n = cfg.get('n')
            if not isinstance(n, int) or n < 1:
                p.erro(onde, '"n" deve ser um número inteiro (quantos itens na lista)')
                continue
            md['formato'] = None
            fmt = {'inteiro': '#,0', 'percentual': '0.0%', 'moeda': 'R$ #,0', 'decimal': '#,0.00'}.get(base['formato'], '#,0.00')
            md['dax'] = (f'VAR _primeiros = TOPN({n}, ALLSELECTED({col}), {b}, {sentido})\n'
                         f'RETURN\n    CONCATENATEX(_primeiros, {col} & ": " & FORMAT({b}, "{fmt}"), "  ·  ", {b}, {sentido})')
        elif tipo == 'posicao':
            md['formato'] = 'inteiro'
            md['dax'] = (f'IF(\n    HASONEVALUE({col}) && NOT ISBLANK({b}),\n'
                         f'    RANKX(ALLSELECTED({col}), {b}, , {sentido}, Dense)\n)')
        elif tipo == 'pareto':
            md['formato'] = 'percentual'
            md['dax'] = (f'VAR _valor = {b}\nVAR _total = CALCULATE({b}, ALLSELECTED({col}))\n'
                         f'VAR _acumulado = SUMX(FILTER(ALLSELECTED({col}), {b} >= _valor), {b})\n'
                         f'RETURN\n    IF(HASONEVALUE({col}) && NOT ISBLANK(_valor), DIVIDE(_acumulado, _total))')
        elif tipo == 'melhores_piores':
            n = cfg.get('n')
            if not isinstance(n, int) or n < 1:
                p.erro(onde, '"n" deve ser um número inteiro (quantos melhores e quantos piores)')
                continue
            md['formato'] = cfg.get('formato_dado') or base['formato']
            md['dax'] = (f'VAR _posicao = RANKX(ALLSELECTED({col}), {b}, , {sentido}, Dense)\n'
                         f'VAR _linhas = COUNTROWS(ALLSELECTED({col}))\n'
                         f'RETURN\n    IF(HASONEVALUE({col}) && (_posicao <= {n} || _posicao > _linhas - {n}), {b})')
        elif tipo == 'jitter':                         # o X do jitter plot: espalha os pontos sem sorteio
            md['formato'] = 'decimal'
            md['dax'] = (f'VAR _posicao = RANKX(ALLSELECTED({col}), {b}, , {sentido}, Skip)\n'
                         f'RETURN\n    IF(HASONEVALUE({col}) && NOT ISBLANK({b}), MOD(_posicao * 37, 101) / 100)')
        elif tipo == 'impacto':                        # quanto cada item mexeu no total entre os dois períodos
            md['formato'] = cfg.get('formato_dado') or base['formato']
            md['depende'].append(cfg['comparar'])
            md['dax'] = (f'VAR _antes = {dax_medida(cfg["comparar"])}\nVAR _agora = {b}\n'
                         f'RETURN\n    IF(HASONEVALUE({col}) && NOT (ISBLANK(_agora) && ISBLANK(_antes)), _agora - _antes)')
            cor = f'Cor {md["nome"]}'
            novas.append({'nome': cor, 'tipo': 'cor', 'formato': None, 'pasta': md.get('pasta'), 'tabela': md['tabela'],
                          'descricao': f'Cor do impacto de {md["nome"]}: verde quando ajudou o indicador, vermelho quando '
                                       'atrapalhou.',
                          'dax': (f'VAR _impacto = {dax_medida(md["nome"])}\n'
                                  f'RETURN\n    IF(ISBLANK(_impacto), BLANK(), IF(_impacto {op} 0, "{COR_BOA}", "{COR_RUIM}"))'),
                          'depende': [md['nome']], 'meta': None, 'polaridade': base['polaridade'], 'oculta': True,
                          'meta_medida': None, 'cor_medida': None, 'conferencia_sql': None})
            md['cor_medida'] = cor
        _conferir_funcoes(md['dax'], p, onde)
        if md.get('imagem'):
            conferir_svg(md['dax'], p, onde)
    m['medidas'].extend(novas)


EXTRAS = ('escolha', 'alternar', 'cor_destaque', 'aviso', 'svg_iniciais', 'svg_dispersao', 'html_kpis', 'svg_espinha')
COR_APAGADA = '#C8C6C4'


def _tabela_auxiliar(m, p, onde, nome, dax, colunas, descricao):
    """Tabela calculada em DAX que o Deidara cria para uma técnica (opções das abas, chave de alternar, cópia
    solta da coluna do destaque). Não tem fonte nem relacionamento: só as medidas leem a escolha."""
    if tabela_do_modelo(m, nome):
        p.erro(onde, f'já existe uma tabela chamada "{nome}"')
        return None
    t = {'nome': nome, 'tipo': 'dimensao', 'origem': None, 'fonte': None, 'descricao': descricao, 'filtro': None,
         'colunas': [], 'pk': [], 'auxiliar': True, 'calculada': dax}
    for c in colunas:
        col = _coluna(c['nome'], None, c.get('familia', 'texto'), oculta=c.get('oculta', False))
        col['ordenar_por'] = c.get('ordenar_por')
        t['colunas'].append(col)
    m['tabelas'].append(t)
    _conferir_funcoes(dax, p, onde)
    return t





def _extras(m, p):
    """As técnicas que pedem mais que uma medida: escolha (abas), alternar, destaque, aviso, imagens e HTML.
    Cada uma escreve a medida e, quando precisa, a tabela auxiliar que o segmentador de botões usa."""
    novas = []
    acento = (m['tema']['cores'] or ['#118DFF'])[0]
    for md in m['medidas']:
        if md.get('tipo') not in EXTRAS:
            continue
        cfg, onde, nome = md['extra'], f'medida {md["nome"]}', md['nome']
        tipo = md['tipo']
        md['depende'] = []
        if tipo == 'escolha':
            ops = cfg.get('opcoes')
            pares = list(ops.items()) if isinstance(ops, dict) else [(x, x) for x in (ops or [])]
            alvos = [(r, medida(m, x)) for r, x in pares]
            if len(alvos) < 2 or not all(a for _, a in alvos):
                p.erro(onde, '"opcoes" pede de 2 em diante medidas do modelo (lista, ou {"rótulo": "medida"})')
                continue
            tab = cfg.get('tabela_opcoes') or f'{nome} (opções)'
            linhas = ', '.join(f'{{ {_texto_dax(r)}, {k} }}' for k, (r, _) in enumerate(alvos, 1))
            if not _tabela_auxiliar(m, p, onde, tab, f'DATATABLE("Opção", STRING, "Ordem", INTEGER, {{ {linhas} }})',
                                    [{'nome': 'Opção', 'ordenar_por': 'Ordem'}, {'nome': 'Ordem', 'familia': 'inteiro',
                                                                                  'oculta': True}],
                                    f'Opções de "{nome}" (uma por botão).'):
                continue
            col = dax_coluna(tab, 'Opção')
            ramos = ', '.join(f'{_texto_dax(r)}, {dax_medida(a["nome"])}' for r, a in alvos)
            md['dax'] = (f'VAR _escolha = SELECTEDVALUE({col}, {_texto_dax(alvos[0][0])})\n'
                         f'RETURN\n    SWITCH(_escolha, {ramos})')
            formatos = {a['formato'] for _, a in alvos}
            md['formato'] = alvos[0][1]['formato']
            if len(formatos) > 1:                     # cada opção com o próprio formato (formato dinâmico)
                md['formato_dinamico'] = (f'SWITCH(SELECTEDVALUE({col}, {_texto_dax(alvos[0][0])}), '
                                          + ', '.join(f'{_texto_dax(r)}, {_texto_dax(FORMATO_DAX.get(a["formato"], "#,0.00"))}'
                                                      for r, a in alvos) + ')')
            md['depende'] = [a['nome'] for _, a in alvos]
            md['polaridade'] = alvos[0][1]['polaridade']
            cfg.update({'tabela': tab, 'coluna': 'Opção', 'rotulos': [r for r, _ in alvos], 'medidas': md['depende']})
        elif tipo == 'alternar':
            lig, des = medida(m, cfg.get('ligado') or ''), medida(m, cfg.get('desligado') or '')
            if not lig or not des:
                p.erro(onde, '"ligado" e "desligado" pedem as duas medidas do modelo (a de quando a chave está ligada '
                             'e a de quando está desligada)')
                continue
            rotulo = cfg.get('rotulo') or lig['nome']
            tab = cfg.get('tabela_opcoes') or f'{nome} (chave)'
            if not _tabela_auxiliar(m, p, onde, tab, f'DATATABLE("Estado", STRING, {{ {{ {_texto_dax(rotulo)} }} }})',
                                    [{'nome': 'Estado'}], f'Chave de "{nome}": ligada quando o botão está selecionado.'):
                continue
            col = dax_coluna(tab, 'Estado')
            md['dax'] = f'IF(ISFILTERED({col}), {dax_medida(lig["nome"])}, {dax_medida(des["nome"])})'
            md['formato'] = des['formato']
            if lig['formato'] != des['formato']:
                md['formato_dinamico'] = (f'IF(ISFILTERED({col}), {_texto_dax(FORMATO_DAX.get(lig["formato"], "#,0.00"))}, '
                                          f'{_texto_dax(FORMATO_DAX.get(des["formato"], "#,0.00"))})')
            md['depende'] = [lig['nome'], des['nome']]
            md['polaridade'] = des['polaridade']
            for sufixo, cor, cx in ((' · chave', '%23C8C6C4', 18), (' · chave ligada', '%23' + acento[1:], 46)):
                svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='64' height='36' viewBox='0 0 64 36'>"
                       f"<rect x='2' y='4' width='60' height='28' rx='14' fill='{cor}'/>"
                       f"<circle cx='{cx}' cy='18' r='11' fill='%23FFFFFF'/></svg>")
                novas.append({'nome': nome + sufixo, 'tipo': 'svg_iniciais', 'formato': None, 'imagem': True,
                              'pasta': md['pasta'], 'tabela': md['tabela'], 'depende': [], 'extra': {},
                              'dax': f'"{PREFIXO_SVG}{svg}"',
                              'descricao': f'Imagem da chave de "{nome}" ({"ligada" if cx > 20 else "desligada"}).',
                              'meta': None, 'polaridade': 'maior_melhor', 'oculta': True, 'meta_medida': None,
                              'cor_medida': None, 'conferencia_sql': None})
            md['chave'] = (nome + ' · chave', nome + ' · chave ligada')
            cfg.update({'tabela': tab, 'coluna': 'Estado', 'rotulo': rotulo, 'ligado': lig['nome'], 'desligado': des['nome']})
        elif tipo == 'cor_destaque':
            tc, cc = _resolver_coluna(m, cfg.get('categoria'))
            if not cc:
                p.erro(onde, '"categoria" precisa ser a coluna das barras' + pista_coluna(m, cfg.get('categoria')))
                continue
            tab = cfg.get('tabela_opcoes') or f'Destacar {cc["nome"]}'
            if not _tabela_auxiliar(m, p, onde, tab, f'DISTINCT({dax_coluna(tc["nome"], cc["nome"])})',
                                    [{'nome': cc['nome']}],
                                    f'Cópia solta de {tc["nome"]}[{cc["nome"]}]: o segmentador escolhe o que fica em destaque '
                                    'sem filtrar o gráfico.'):
                continue
            solta, real = dax_coluna(tab, cc['nome']), dax_coluna(tc['nome'], cc['nome'])
            md['dax'] = (f'IF(\n    NOT ISFILTERED({solta}) || SELECTEDVALUE({real}) IN VALUES({solta}),\n'
                         f'    "{acento}",\n    "{COR_APAGADA}"\n)')
            md['oculta'] = True
            cfg.update({'tabela': tab, 'coluna': cc['nome'], 'origem': [tc['nome'], cc['nome']]})
        elif tipo == 'aviso':
            base = medida(m, cfg.get('medida') or '')
            tc, cc = _resolver_coluna(m, cfg.get('categoria'))
            if not base or not base.get('meta_medida') or not cc:
                p.erro(onde, '"aviso" pede "medida" (com meta) e "categoria" (a coluna em que o aviso procura quem está '
                             'fora da meta)')
                continue
            col, b, mt = dax_coluna(tc['nome'], cc['nome']), dax_medida(base['nome']), dax_medida(base['meta_medida'])
            op = '<' if base['polaridade'] == 'maior_melhor' else '>'
            md['dax'] = (f'VAR _fora = FILTER(ALLSELECTED({col}), NOT ISBLANK({b}) && {b} {op} {mt})\n'
                         f'VAR _n = COUNTROWS(_fora)\n'
                         f'RETURN\n    IF(\n        _n > 0,\n'
                         f'        UNICHAR(9888) & " " & _n & " de " & COUNTROWS(ALLSELECTED({col})) & " fora da meta de '
                         f'{base["nome"]}: " & CONCATENATEX(TOPN(3, _fora, ABS({b} - {mt}), DESC), {col}, ", ", '
                         f'ABS({b} - {mt}), DESC) & IF(_n > 3, "…"),\n        ""\n    )')
            md['depende'] = [base['nome'], base['meta_medida']]
            cor = f'{nome} · fundo'
            novas.append({'nome': cor, 'tipo': 'cor', 'formato': None, 'pasta': md['pasta'] or 'Avisos', 'tabela': md['tabela'],
                          'descricao': f'Fundo do aviso "{nome}": vermelho claro quando há algo fora da meta.',
                          'dax': f'IF({dax_medida(nome)} <> "", "#FDE7E9", "{m["tema"]["fundo"]}")', 'depende': [nome],
                          'meta': None, 'polaridade': 'maior_melhor', 'oculta': True, 'meta_medida': None,
                          'cor_medida': None, 'conferencia_sql': None})
            md['cor_fundo'] = cor
            cfg.update({'base': base['nome'], 'tabela': tc['nome'], 'coluna': cc['nome'], 'meta': base['meta_medida']})
        elif tipo == 'svg_iniciais':
            tc, cc = _resolver_coluna(m, cfg.get('categoria'))
            if not cc:
                p.erro(onde, '"categoria" precisa ser a coluna dos botões' + pista_coluna(m, cfg.get('categoria')))
                continue
            col = dax_coluna(tc['nome'], cc['nome'])
            for sufixo, fundo, texto in (('', '%23EDEBE9', '%23605E5C'), (' (ligado)', '%23' + acento[1:], '%23FFFFFF')):
                dax = _svg_iniciais(col, fundo, texto)
                if sufixo:
                    novas.append({'nome': nome + sufixo, 'tipo': 'svg_iniciais', 'formato': None, 'imagem': True,
                                  'pasta': md['pasta'], 'tabela': md['tabela'], 'dax': dax, 'depende': [],
                                  'descricao': f'{md["descricao"]} (botão selecionado)'.strip(), 'meta': None,
                                  'polaridade': 'maior_melhor', 'oculta': True, 'meta_medida': None, 'cor_medida': None,
                                  'conferencia_sql': None, 'extra': {}})
                else:
                    md['dax'] = dax
            md['ligado'] = nome + ' (ligado)'
            cfg.update({'tabela': tc['nome'], 'coluna': cc['nome']})
        elif tipo == 'svg_dispersao':
            tc, cc = _resolver_coluna(m, cfg.get('categoria'))
            mx, my = medida(m, cfg.get('x') or ''), medida(m, cfg.get('y') or '')
            if not cc or not mx or not my:
                p.erro(onde, '"svg_dispersao" pede "categoria" (os pontos), "x" e "y" (medidas do modelo)')
                continue
            img = cfg.get('imagem')
            img_md = medida(m, img) if img and '[' not in img else None
            ti, ci = _resolver_coluna(m, img) if img and '[' in img else (None, None)
            if img and not (img_md or ci):
                p.erro(onde, '"imagem" precisa ser a coluna (ou a medida) com a imagem de cada ponto, em data:image/...')
                continue
            fonte_img = (dax_medida(img_md['nome']) if img_md else f'MAX({dax_coluna(ti["nome"], ci["nome"])})') if img else None
            md['dax'] = _svg_dispersao(dax_coluna(tc['nome'], cc['nome']), dax_medida(mx['nome']), dax_medida(my['nome']),
                                       fonte_img, acento, mx['nome'], my['nome'])
            md['depende'] = [mx['nome'], my['nome']] + ([img_md['nome']] if img_md else [])
            cfg.update({'tabela': tc['nome'], 'coluna': cc['nome'], 'x': mx['nome'], 'y': my['nome']})
            if img:
                p.aviso(onde, '[Design] a imagem de cada ponto precisa vir em data:image/... (base64): link externo não '
                              'carrega dentro de uma imagem SVG no Power BI')
        elif tipo == 'html_kpis':
            itens = [medida(m, x) for x in (cfg.get('medidas') or [])]
            if not itens or not all(itens):
                p.erro(onde, '"medidas" pede as medidas do modelo que viram os blocos do HTML')
                continue
            md['dax'] = _html_kpis(itens, acento)
            md['depende'] = [x['nome'] for x in itens] + [x['meta_medida'] for x in itens if x.get('meta_medida')]
            cfg['medidas'] = [x['nome'] for x in itens]
        elif tipo == 'svg_espinha':
            base = medida(m, cfg.get('medida') or '')
            cortes = [_resolver_coluna(m, x) for x in (cfg.get('cortes') or [])]
            n = cfg.get('n', 3)
            if not base or not 2 <= len(cortes) <= 6 or not all(c for _, c in cortes):
                p.erro(onde, '"svg_espinha" pede "medida" e "cortes": de 2 a 6 colunas do modelo (uma espinha por coluna)')
                continue
            if not isinstance(n, int) or not 1 <= n <= 5:
                p.erro(onde, '"n" deve ser um número inteiro de 1 a 5 (quantos itens em cada espinha)')
                continue
            md['dax'] = _svg_espinha(dax_medida(base['nome']), [(dax_coluna(t['nome'], c['nome']), c['nome']) for t, c in cortes],
                                     n, base['polaridade'] == 'maior_melhor', base['nome'], acento)
            md['depende'] = [base['nome']]
            md['polaridade'] = base['polaridade']
            cfg.update({'base': base['nome'], 'cortes': [[t['nome'], c['nome']] for t, c in cortes], 'n': n})
        _conferir_funcoes(md['dax'], p, onde)
        if md.get('imagem'):                               # a dispersão e a espinha são o gráfico inteiro
            conferir_svg(md['dax'], p, onde, por_linha=tipo not in ('svg_dispersao', 'svg_espinha'))
    m['medidas'].extend(novas)



def _modelo(argila, m, p):
    """O modelo de layout (referencias/modelos.md). A história longa é escura: sem tema próprio, ganha o escuro."""
    from tecnicas.arte.modelos import ESCURO, MODELOS
    modelo = argila.get('modelo') or 'padrao'
    if modelo not in MODELOS:
        import difflib
        perto = difflib.get_close_matches(str(modelo), MODELOS, n=1)
        p.erro('modelo', f'"{modelo}" não é um modelo de layout' + (f'; quis dizer "{perto[0]}"?' if perto else '')
               + f' (modelos: {", ".join(MODELOS)}; `deidara.py modelos`)')
        modelo = 'padrao'
    m['modelo'] = modelo
    dado = argila.get('tema') or {}
    if isinstance(dado, str):
        dado = {'paleta': dado}
    if dado.get('arquivo'):                        # tema JSON do time ou da comunidade (BIBB, Zebra BI...), usado inteiro
        import json
        import os
        caminho = os.path.join(argila.get('_pasta') or '.', dado['arquivo'])
        try:
            with open(caminho, encoding='utf-8-sig') as f:
                tema = json.load(f)
        except (OSError, ValueError) as e:
            p.erro('tema', f'não consegui ler o tema "{dado["arquivo"]}" ({e.__class__.__name__}): aponte um JSON de tema '
                           'do Power BI, com o caminho a partir do argila.json')
            tema = None
        if tema is not None:
            cores = [c for c in tema.get('dataColors') or [] if isinstance(c, str) and c.startswith('#')]
            if not cores:
                p.erro('tema', f'"{dado["arquivo"]}" não tem "dataColors": não parece um tema do Power BI')
            else:
                m['tema'].update({'cores': cores, 'json': tema,
                                  **{k: tema[c] for k, c in (('fundo', 'background'), ('texto', 'foreground'))
                                     if isinstance(tema.get(c), str)}})
                m['tema'].pop('arquivo', None)
                p.aviso('tema', f'[Design] o tema "{dado["arquivo"]}" vai inteiro no relatório: confira a licença de quem '
                                'fez e dê o crédito no LEIA-ME')
    elif dado.get('paleta'):                       # as paletas dos temas do Power BI Design Files (dicionario/paletas.json)
        from tecnicas.sasori import paletas
        todas = paletas()['paletas']
        pal = todas.get(dado['paleta'])
        if not pal:
            p.erro('tema', f'paleta "{dado["paleta"]}" não existe (paletas: {", ".join(todas)})')
        else:
            m['tema'].update({k: pal[k] for k in ('cores', 'fundo', 'texto')})
            m['tema'].update({k: v for k, v in dado.items() if k != 'paleta'})
    elif modelo == 'historia-longa':
        for k, v in ESCURO.items():
            if k not in dado:
                m['tema'][k] = v


def _contraste(c1, c2):
    def lum(c):
        c = c.lstrip('#')
        if len(c) == 3:
            c = ''.join(x * 2 for x in c)
        rgb = [int(c[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        lin = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in rgb]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    a, b = sorted((lum(c1), lum(c2)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def _design(argila, m, p):
    """Tema legível: texto sobre o fundo com contraste de 4,5:1; as cores dos dados escolhidas pelo time, 3:1."""
    t, dado = m['tema'], argila.get('tema') if isinstance(argila.get('tema'), dict) else {}
    hexa = re.compile(r'#?[0-9A-Fa-f]{6}$|#?[0-9A-Fa-f]{3}$')
    cores = [t.get('texto'), t.get('fundo')] + list(t.get('cores') or [])
    ruins = [c for c in cores if not isinstance(c, str) or not hexa.match(c)]
    if ruins:
        p.erro('tema', f'cor inválida: {", ".join(map(str, ruins))} (use #RRGGBB)')
        return
    r = _contraste(t['texto'], t['fundo'])
    if r < 4.5:
        p.aviso('tema', f'[Design] o texto ({t["texto"]}) sobre o fundo ({t["fundo"]}) tem contraste '
                        f'{numero_br(r, 1)}:1; o mínimo para leitura é 4,5:1')
    if dado.get('cores'):
        fracas = [c for c in t['cores'] if _contraste(c, t['fundo']) < 3]
        if fracas:
            p.aviso('tema', f'[Design] cores de dados com pouco contraste sobre o fundo (menos de 3:1): '
                            f'{", ".join(fracas)}; elas somem em barras finas e linhas')


def _metas(m, p):
    """Meta numérica vira a medida `Meta X`; toda meta ganha `Cor X` (oculta), que
    pinta o valor de verde ou vermelho conforme a polaridade, no cartão, na
    tabela e na matriz (formatação condicional por valor do campo)."""
    for md in list(m['medidas']):
        meta = md.get('meta')
        if meta is None:
            continue
        onde = f'medida {md["nome"]}'
        if md['polaridade'] not in ('maior_melhor', 'menor_melhor'):
            p.erro(onde, 'polaridade deve ser maior_melhor ou menor_melhor')
            continue
        if isinstance(meta, (int, float)) and not isinstance(meta, bool):
            nome_meta = f'Meta {md["nome"]}'
            if medida(m, nome_meta):
                p.erro(onde, f'já existe uma medida "{nome_meta}": use "meta": "{nome_meta}"')
                continue
            m['medidas'].append({'nome': nome_meta, 'tipo': 'meta', 'dax': repr(float(meta)).rstrip('0').rstrip('.'),
                                 'formato': md['formato'], 'descricao': f'Meta de {md["nome"]}.', 'pasta': 'Metas',
                                 'tabela': md['tabela'], 'depende': [], 'meta': None, 'polaridade': md['polaridade'],
                                 'oculta': False, 'meta_medida': None, 'cor_medida': None, 'conferencia_sql': None})
        elif isinstance(meta, str) and medida(m, meta):
            nome_meta = medida(m, meta)['nome']
        else:
            p.erro(onde, f'meta "{meta}" deve ser um número ou o nome de uma medida do modelo')
            continue
        op = '>=' if md['polaridade'] == 'maior_melhor' else '<='
        cor = f'Cor {md["nome"]}'
        m['medidas'].append({
            'nome': cor, 'tipo': 'cor', 'formato': None, 'pasta': 'Metas', 'tabela': md['tabela'],
            'descricao': f'Cor do status de {md["nome"]} contra a meta ({md["polaridade"].replace("_", " ")}).',
            'dax': (f'VAR _valor = {dax_medida(md["nome"])}\nVAR _meta = {dax_medida(nome_meta)}\n'
                    f'RETURN\n    IF(\n        ISBLANK(_valor) || ISBLANK(_meta),\n        BLANK(),\n'
                    f'        IF(_valor {op} _meta, "{COR_BOA}", "{COR_RUIM}")\n    )'),
            'depende': [md['nome'], nome_meta], 'meta': None, 'polaridade': md['polaridade'], 'oculta': True,
            'meta_medida': None, 'cor_medida': None, 'conferencia_sql': None})
        md['meta_medida'], md['cor_medida'] = nome_meta, cor
        alvo = medida(m, nome_meta)
        if alvo and alvo.get('tipo') != 'meta':             # meta de outra medida: o título do cartão mostra o valor
            fmt = {'percentual': '0.0%', 'inteiro': '#,0', 'moeda': '"R$" #,0.00'}.get(alvo.get('formato'), '#,0.00')
            rotulo = f'Rótulo {cor}'
            m['medidas'].append({
                'nome': rotulo, 'tipo': 'cor', 'formato': None, 'pasta': 'Metas', 'tabela': md['tabela'],
                'descricao': f'Texto "Meta: ..." do cartão de {md["nome"]}.',
                'dax': f'"Meta: " & FORMAT({dax_medida(nome_meta)}, "{fmt}")', 'depende': [nome_meta], 'meta': None,
                'polaridade': md['polaridade'], 'oculta': True, 'meta_medida': None, 'cor_medida': None,
                'conferencia_sql': None})
            md['rotulo_meta'] = rotulo


def _formato_padrao(md, nomes, vistos=()):
    """Contagem é inteiro; variação é percentual; medida de tempo herda o formato da base."""
    if str(md.get('agregacao', '')).startswith('contagem') or md.get('tipo') == 'estoque_na_data':
        return 'inteiro'
    if md.get('tipo') == 'media_mensal':
        return 'decimal'
    if str(md.get('tipo', '')).startswith('variacao'):
        return 'percentual'
    base = nomes.get(chave(md.get('base', '')))
    if md.get('tipo') in TEMPO and base and chave(md['base']) not in vistos:
        return base.get('formato') or _formato_padrao(base, nomes, tuple(vistos) + (chave(md['base']),))
    return 'decimal'


def _resolver_coluna(m, ref, padrao=None):
    """'Tabela[Coluna]', 'Tabela.Coluna' ou 'Coluna' (na tabela padrão) -> (tabela, coluna) do modelo."""
    ref = (ref or '').strip()
    mt = re.fullmatch(r"'?(.+?)'?\[(.+)\]", ref) or re.fullmatch(r'([^.]+)\.(.+)', ref)
    tn, cn = (mt.group(1), mt.group(2)) if mt else (padrao, ref)
    t = tabela_do_modelo(m, tn or '')
    c = coluna_do_modelo(t, cn) if t else None
    return t, c


def _medida_agregacao(m, md, r, p, onde):
    ag = md['agregacao']
    r['tipo'] = 'agregacao'
    if ag not in AGREGACOES:
        p.erro(onde, f'agregacao "{ag}" inválida ({", ".join(AGREGACOES)})')
        return
    if ag == 'contagem_linhas':
        t = tabela_do_modelo(m, md.get('tabela', ''))
        if not t:
            p.erro(onde, 'contagem_linhas pede "tabela" do modelo')
            return
        r['tabela'] = t['nome']
        r['dax'] = f'COUNTROWS({dax_tabela(t["nome"])})'
        r['conferencia'] = {'tabela': t['nome'], 'sql': 'COUNT_BIG(*)'}
        return
    t, c = _resolver_coluna(m, md.get('coluna'), md.get('tabela'))
    if not c:
        dep = _depende_de(md.get('coluna')) or ((chave_coluna(md.get('tabela') or '', md.get('coluna') or ''),))
        p.erro(onde, f'coluna "{md.get("coluna")}" não está no modelo (use Tabela[Coluna])', depende=dep,
               raiz=('medida', chave(md.get('nome', ''))))
        origem_raiz = next((p.raizes[d] for d in dep if d in p.raizes), None)
        if origem_raiz:
            p.raizes.setdefault(('medida', chave(md.get('nome', ''))), origem_raiz)
        return
    if ag in AGREGACOES_NUMERICAS and c['familia'] not in NUMERICAS:
        p.erro(onde, f'{ag} pede coluna numérica; {t["nome"]}[{c["nome"]}] é {c["familia"]}')
        return
    r['tabela'] = md.get('tabela') or t['nome']
    r['dax'] = f'{AGREGACOES[ag]}({dax_coluna(t["nome"], c["nome"])})'
    sql = {'soma': 'SUM(CAST({} AS decimal(38,6)))', 'media': 'AVG(CAST({} AS decimal(38,6)))', 'minimo': 'MIN({})',
           'maximo': 'MAX({})', 'contagem': 'COUNT_BIG({})', 'contagem_distinta': 'COUNT_BIG(DISTINCT {})'}[ag]
    if ag in ('minimo', 'maximo') and c['familia'] not in NUMERICAS:
        return                      # data/texto: a conferência numérica não se aplica
    r['conferencia'] = {'tabela': t['nome'], 'sql': sql.format(f'[{c["nome"]}]')}


def _medida_tempo(m, md, r, p, onde, nomes):
    r['tipo'] = md['tipo']
    base = md.get('base', '')
    if chave(base) not in nomes:
        p.erro(onde, f'base "{base}" não é uma medida do modelo' + _pista_medida(base, nomes))
    if not m.get('calendario'):
        p.erro(onde, 'medida de tempo pede "calendario" no argila.json')
        return
    data = dax_coluna(m['calendario']['tabela'], 'Data')
    b = dax_medida(base)
    r['depende'] = [base]
    expr = {
        'acumulado_ano': f'TOTALYTD({b}, {data})',
        'ano_anterior': f'CALCULATE({b}, SAMEPERIODLASTYEAR({data}))',
        'variacao_ano_anterior': (f'VAR _atual = {b}\nVAR _anterior = CALCULATE({b}, SAMEPERIODLASTYEAR({data}))\n'
                                  'RETURN DIVIDE(_atual - _anterior, _anterior)'),
        'variacao_mes_anterior': (f'VAR _atual = {b}\nVAR _anterior = CALCULATE({b}, DATEADD({data}, -1, MONTH))\n'
                                  'RETURN DIVIDE(_atual - _anterior, _anterior)'),
        # média dos valores de fim de mês no período (ex.: HC médio para o turnover)
        'media_mensal': f'AVERAGEX(VALUES({dax_coluna(m["calendario"]["tabela"], "Ano-Mês")}), {b})',
        'movel_12m': f'CALCULATE({b}, DATESINPERIOD({data}, MAX({data}), -12, MONTH))',
    }[md['tipo']]
    # período futuro: sem isso o acumulado repete nos meses que ainda não aconteceram e a
    # variação dá -100% (atual em branco contra um ano anterior com valor)
    corpo = '\n'.join('    ' + l for l in expr.split('\n'))
    r['dax'] = f'IF(\n    MIN({data}) > TODAY(),\n    BLANK(),\n{corpo}\n)'


def _medida_estoque(m, md, r, p, onde):
    """Quantos estão "dentro" no fim do período: entradas até a data, menos as
    saídas até a data (headcount ativo, contratos vigentes, ativos em uso).
    A saída pode ser uma coluna da mesma tabela (`fim`) ou outra tabela
    (`saidas`, ex.: a fato de desligamentos)."""
    r['tipo'] = 'estoque_na_data'
    if not m.get('calendario'):
        p.erro(onde, 'estoque_na_data pede "calendario" no argila.json')
        return
    cal = m['calendario']['tabela']
    te, ce = _resolver_coluna(m, md.get('entradas'))
    datas = ('data', 'datahora')
    if md.get('saidas'):                                   # as duas pontas no mesmo relatório, não uma por vez
        ts0, cs0 = _resolver_coluna(m, md['saidas'])
        if not cs0 or cs0['familia'] not in datas:
            p.erro(onde, f'"saidas" ("{md.get("saidas")}") precisa ser uma coluna de data do modelo'
                         + pista_coluna(m, md['saidas'], datas))
            if ce and ce['familia'] in datas:
                return
    if not ce or ce['familia'] not in datas:
        p.erro(onde, f'"entradas" ("{md.get("entradas")}") precisa ser uma coluna de data do modelo'
                     + pista_coluna(m, md.get('entradas'), datas))
        return
    lidas = [te['nome']]
    fim_ref = ''
    if md.get('fim'):
        tf, cf = _resolver_coluna(m, md['fim'])
        if not cf or tf['nome'] != te['nome'] or cf['familia'] not in ('data', 'datahora'):
            p.erro(onde, '"fim" precisa ser uma coluna de data da mesma tabela das entradas')
            return
        fim_ref = (f',\n        OR(ISBLANK({dax_coluna(tf["nome"], cf["nome"])}), '
                   f'{dax_coluna(tf["nome"], cf["nome"])} > _fim)')
    dax = (f'VAR _fim = MAX({dax_coluna(cal, "Data")})\nVAR _entradas =\n    CALCULATE(\n'
           f'        COUNTROWS({dax_tabela(te["nome"])}),\n        {dax_coluna(te["nome"], ce["nome"])} <= _fim{fim_ref},\n'
           f'        REMOVEFILTERS({dax_tabela(cal)})\n    )\n')
    if md.get('saidas'):
        ts, cs = _resolver_coluna(m, md['saidas'])
        if not cs or cs['familia'] not in ('data', 'datahora'):
            return                                          # já relatado acima
        if not _alcanca(_grafo_de_filtro(m), te['nome'], ts['nome']):
            p.aviso(onde, f'{te["nome"]} não filtra {ts["nome"]}: um corte por {te["nome"]} vai tirar as saídas de '
                          'todo mundo; confira o relacionamento')
        lidas.append(ts['nome'])
        dax += (f'VAR _saidas =\n    CALCULATE(\n        COUNTROWS({dax_tabela(ts["nome"])}),\n'
                f'        {dax_coluna(ts["nome"], cs["nome"])} <= _fim,\n        REMOVEFILTERS({dax_tabela(cal)})\n    )\n'
                'RETURN\n    IF(MIN(' + dax_coluna(cal, 'Data') + ') > TODAY(), BLANK(), _entradas - _saidas)')
    else:
        dax += 'RETURN\n    IF(MIN(' + dax_coluna(cal, 'Data') + ') > TODAY(), BLANK(), _entradas)'
    r['estoque'] = {'entradas': (te['nome'], ce['nome']),
                    'fim': (tf['nome'], cf['nome']) if md.get('fim') else None,
                    'saidas': (ts['nome'], cs['nome']) if md.get('saidas') else None}
    r['dax'], r['tabela'] = dax, md.get('tabela') or te['nome']
    r['tabelas_lidas'], r['le_calendario'], r['depende'] = lidas, True, []


def _conferir_funcoes(dax, p, onde):
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
    return out


def _conferir_refs(m, r, nomes, p, onde):
    for problema in sintaxe_dax(r['dax']):
        p.erro(onde, f'DAX mal escrito: {problema}')
    _conferir_funcoes(r['dax'], p, onde)
    deps = []
    for tn, n in referencias_dax(r['dax']):
        if tn:
            t = tabela_do_modelo(m, tn)
            if not t:
                p.erro(onde, f'tabela "{tn}" do DAX não está no modelo')
            elif not coluna_do_modelo(t, n) and chave(n) not in nomes:
                p.erro(onde, f'coluna "{tn}[{n}]" do DAX não está no modelo', depende=_depende_de(f'{tn}[{n}]'))
        elif chave(n) in nomes:
            deps.append(n)
        elif not any(coluna_do_modelo(t, n) for t in m['tabelas']):
            p.erro(onde, f'"[{n}]" do DAX não é medida nem coluna do modelo')
    r['depende'] = deps


def _ciclos(m, p):
    por_nome = {chave(x['nome']): x for x in m['medidas']}
    estado = {}

    def visita(k, pilha):
        if estado.get(k) == 1:
            p.erro(f'medida {por_nome[k]["nome"]}', 'dependência circular: ' + ' -> '.join(pilha + [por_nome[k]['nome']]))
            return
        if estado.get(k) == 2 or k not in por_nome:
            return
        estado[k] = 1
        for d in por_nome[k].get('depende') or []:
            visita(chave(d), pilha + [por_nome[k]['nome']])
        estado[k] = 2

    for k in por_nome:
        visita(k, [])


def medida(m, nome):
    for x in m['medidas']:
        if chave(x['nome']) == chave(nome):
            return x
    return None


# ------------------------------------------------------------------ páginas
def _campo(m, ref):
    """Coluna ('Tabela[Coluna]') ou medida (nome solto)."""
    if re.search(r'\[.+\]$', ref or '') or ('.' in (ref or '') and not medida(m, ref)):
        t, c = _resolver_coluna(m, ref)
        if c:
            return {'tipo': 'coluna', 'tabela': t['nome'], 'nome': c['nome'], 'familia': c['familia']}
        return None
    md = medida(m, ref or '')
    if md:
        return {'tipo': 'medida', 'tabela': md['tabela'], 'nome': md['nome'], 'formato': md['formato']}
    return None


def _paginas(argila, m, p):
    if not argila.get('paginas'):
        p.erro('paginas', 'nenhuma página no painel')
    filtra = _grafo_de_filtro(m)
    nomes = set()
    for i, pg in enumerate(argila.get('paginas') or []):
        nome = (pg.get('nome') or f'Página {i + 1}').strip()
        onde = f'página {nome}'
        if chave(nome) in nomes:
            p.erro(onde, 'nome de página repetido')
        nomes.add(chave(nome))
        pagina = {'nome': nome, 'descricao': pg.get('descricao', ''), 'visuais': [], 'ajuda': bool(pg.get('ajuda')),
                  'tour': bool(pg.get('tour')), 'dica': bool(pg.get('dica')), 'detalhe': None}
        if pg.get('detalhe'):                          # página de detalhamento (drillthrough) por esta coluna
            c = _campo(m, pg['detalhe'])
            if not c or c['tipo'] != 'coluna':
                p.erro(onde, f'"detalhe" ("{pg["detalhe"]}") precisa ser uma coluna (Tabela[Coluna]): a página abre '
                             'filtrada pelo item em que a pessoa clicou' + pista_coluna(m, pg['detalhe']))
            else:
                pagina['detalhe'] = c
        if pagina['dica'] and (pagina['detalhe'] or pagina['tour'] or pagina['ajuda']):
            p.erro(onde, 'página de dica ("dica": true) não leva "detalhe", "tour" nem "ajuda": ela aparece só ao passar '
                         'o mouse')
        if pagina['dica'] and len(pg.get('visuais') or []) > 4:
            p.aviso(onde, '[Design] página de dica com mais de 4 visuais não cabe em 320 x 240: deixe só o essencial')
        vis = pg.get('visuais') or []
        if not vis:
            p.erro(onde, 'página sem visuais')
        if len(vis) > LIMITE_VISUAIS_POR_PAGINA:
            p.aviso(onde, f'{len(vis)} visuais: acima de {LIMITE_VISUAIS_POR_PAGINA} a página fica lenta e '
                          'poluída; considere dividir')
        for j, v in enumerate(vis):
            r = _visual(m, v, p, f'{onde}, visual {j + 1} ({v.get("tipo")})', filtra)
            if r:
                pagina['visuais'].append(r)
        _conferir_pagina(m, pagina, p, onde, filtra)
        m['paginas'].append(pagina)
    dicas = {pg['nome'] for pg in m['paginas'] if pg['dica']}
    for pg in m['paginas']:                        # visual com "dica": a página de dica que aparece ao passar o mouse
        for v in pg['visuais']:
            if v.get('dica') and v['dica'] not in dicas:
                p.erro(f'página {pg["nome"]}', f'"dica" ("{v["dica"]}") precisa ser o nome de uma página com "dica": true'
                       + (f' (páginas de dica: {", ".join(sorted(dicas))})' if dicas else ''))
        if pg['detalhe'] and (m.get('modelo') or 'padrao') == 'historia-longa':
            p.aviso(f'página {pg["nome"]}', '[Design] a história longa junta tudo numa página: o detalhamento fica de fora')
    _conferir_snowflake(m, p)


ITENS_DE_TEMPO = {                 # item do grupo de cálculo: (rótulo, DAX com {d} = coluna de data, é percentual)
    'atual': ('Atual', 'SELECTEDMEASURE()', False),
    'acumulado_ano': ('Acumulado no ano', 'CALCULATE(SELECTEDMEASURE(), DATESYTD({d}))', False),
    'ano_anterior': ('Ano anterior', 'CALCULATE(SELECTEDMEASURE(), SAMEPERIODLASTYEAR({d}))', False),
    'variacao_ano_anterior': ('Var. ano anterior', 'VAR _atual = SELECTEDMEASURE()\n'
                              'VAR _anterior = CALCULATE(SELECTEDMEASURE(), SAMEPERIODLASTYEAR({d}))\n'
                              'RETURN\n    IF(ISNUMBER(_atual), DIVIDE(_atual - _anterior, _anterior), _atual)', True),
    'mes_anterior': ('Mês anterior', 'CALCULATE(SELECTEDMEASURE(), DATEADD({d}, -1, MONTH))', False),
    'variacao_mes_anterior': ('Var. mês anterior', 'VAR _atual = SELECTEDMEASURE()\n'
                              'VAR _anterior = CALCULATE(SELECTEDMEASURE(), DATEADD({d}, -1, MONTH))\n'
                              'RETURN\n    IF(ISNUMBER(_atual), DIVIDE(_atual - _anterior, _anterior), _atual)', True),
    'movel_12m': ('Últimos 12 meses', 'CALCULATE(SELECTEDMEASURE(), DATESINPERIOD({d}, MAX({d}), -12, MONTH))', False),
}


def _grupo_calculo(argila, m, p):
    """"grupo_calculo": a mesma conta de tempo para todas as medidas, escolhida num segmentador (como o Time
    Intelligence do Awesome Chocolates, no Power BI Design Files). Vira uma tabela de grupo de cálculo."""
    cfg = argila.get('grupo_calculo')
    if not cfg:
        return
    onde = 'grupo_calculo'
    if not isinstance(cfg, dict):
        p.erro(onde, 'use {"nome": "Período", "itens": ["atual", "acumulado_ano", "ano_anterior", ...]}')
        return
    if not m.get('calendario'):
        p.erro(onde, 'o grupo de cálculo de tempo pede "calendario" no argila.json')
        return
    nome = cfg.get('nome') or 'Período'
    itens = cfg.get('itens') or ['atual', 'acumulado_ano', 'ano_anterior', 'variacao_ano_anterior']
    errados = [x for x in itens if x not in ITENS_DE_TEMPO]
    if errados or not itens:
        p.erro(onde, f'item desconhecido: {", ".join(map(str, errados))} (itens: {", ".join(ITENS_DE_TEMPO)})')
        return
    if tabela_do_modelo(m, nome):
        p.erro(onde, f'já existe uma tabela chamada "{nome}"')
        return
    data = dax_coluna(m['calendario']['tabela'], 'Data')
    lista = []
    for k, x in enumerate(itens):
        rotulo, dax, pct = ITENS_DE_TEMPO[x]
        dax = dax.replace('{d}', data)
        _conferir_funcoes(dax, p, onde)
        lista.append({'chave': x, 'rotulo': rotulo, 'dax': dax, 'ordem': k,
                      'formato': ('IF(ISNUMBER(SELECTEDMEASURE()), "0.0%", SELECTEDMEASUREFORMATSTRING())'
                                  if pct else None)})
    t = {'nome': nome, 'tipo': 'dimensao', 'origem': None, 'fonte': None, 'filtro': None, 'pk': [], 'auxiliar': True,
         'descricao': cfg.get('descricao') or 'Grupo de cálculo: a conta de tempo que vale para todas as medidas.',
         'colunas': [], 'grupo_calculo': {'itens': lista, 'precedencia': cfg.get('precedencia', 1)}}
    col = _coluna(nome, None, 'texto')
    col['ordenar_por'] = 'Ordem'
    t['colunas'] = [col, _coluna('Ordem', None, 'inteiro', oculta=True)]
    m['tabelas'].append(t)
    p.aviso(onde, f'[Modelagem] o grupo de cálculo "{nome}" muda TODAS as medidas do visual pelo item escolhido; '
                  'ponha o segmentador dele na página (de botões, de seleção única) e deixe as medidas de tempo '
                  'prontas para quando só uma medida precisa da conta')


def _tours(m, p):
    """Página com "tour": true ganha a medida HTML do tour guiado (um passo por visual, na posição do layout) e,
    no relatório, uma página escondida com os mesmos visuais e o tour por cima."""
    pedidas = [pg for pg in m['paginas'] if pg.get('tour')]
    if not pedidas:
        return
    from tecnicas.arte.modelos import montar, paginas_do_relatorio
    from kibaku_nendo.relato import nota_de_ajuda as _nota_de_ajuda
    from tecnicas.c1.tour import dax_do_tour, html_do_tour, passos
    if (m.get('modelo') or 'padrao') == 'historia-longa':
        p.aviso('tour', '[Design] a história longa é uma página só e rola: o tour guiado fica de fora; use "ajuda"')
        return
    rel = paginas_do_relatorio(m)
    fatos = [t['nome'] for t in m['tabelas'] if t['tipo'] == 'fato'] or [t['nome'] for t in m['tabelas']]
    for pg in pedidas:
        onde = f'página {pg["nome"]}'
        i = next((k for k, x in enumerate(rel) if x['nome'] == pg['nome'] and not x['oculta']), None)
        if i is None or not fatos:
            continue
        lay = montar(m, rel, i)
        lista = passos(lay['posicoes'], lambda v: _nota_de_ajuda(m, v))
        nome = f'Tour · {pg["nome"]}'
        if medida(m, nome):
            p.erro(onde, f'já existe uma medida chamada "{nome}"')
            continue
        texto = html_do_tour(lista, lay['w'], lay['h'], (m['tema']['cores'] or ['#118DFF'])[0])
        dax = dax_do_tour(texto)
        m['medidas'].append({'nome': nome, 'tipo': 'html_tour', 'formato': None, 'pasta': 'Tour', 'tabela': fatos[0],
                             'descricao': f'HTML do tour guiado da página {pg["nome"]} (um passo por visual).',
                             'dax': dax, 'depende': [], 'meta': None, 'polaridade': 'maior_melhor', 'oculta': True,
                             'meta_medida': None, 'cor_medida': None, 'conferencia_sql': None,
                             'extra': {'pagina': pg['nome'], 'passos': len(lista), 'html': texto}})
        pg['tour'] = nome
        _conferir_funcoes(dax, p, onde)
        p.aviso(onde, '[Design] o tour usa o HTML Content (versão certificada), visual do AppSource: o administrador '
                      'do Power BI precisa liberar, e quem abre baixa o visual na primeira vez')
        if len(lay['posicoes']) > len(lista):
            p.aviso(onde, f'[Design] o tour mostra os {len(lista)} primeiros visuais da página; o resto fica sem passo')


def medidas_do_visual(r):
    return _medidas_do_visual(r)


def _medidas_do_visual(r):
    return [x for x in r['valores'] + r['campos'] + ([r['meta']] if r.get('meta') else []) if x and x['tipo'] == 'medida']


def _conferir_pagina(m, pagina, p, onde, filtra):
    auxiliares = {t['nome'] for t in m['tabelas'] if t.get('auxiliar')}
    segs = [v['categoria'] for v in pagina['visuais'] if v['tipo'] in SEGMENTADORES and v['categoria']
            and v['categoria']['tabela'] not in auxiliares]
    medidas = {md['nome'] for v in pagina['visuais'] for md in _medidas_do_visual(v)}
    metas = {x['meta_medida'] for x in m['medidas'] if x.get('meta_medida')}
    paradas = {}                                   # meta que não muda com o segmentador: um aviso só por meta
    for s in segs:
        for nome in sorted(medidas):
            alvo = _tabelas_da_medida(m, nome)
            faltam = sorted(a for a in alvo if not chega(m, filtra, s['tabela'], a, nome))
            if faltam and nome in metas and len(faltam) == len(alvo):
                paradas.setdefault(nome, []).append(f'{s["tabela"]}[{s["nome"]}]')
            elif faltam:
                parte = 'a medida inteira' if len(faltam) == len(alvo) else 'parte da medida (' + ', '.join(faltam) + ')'
                efeito = ('o número fica parado' if len(faltam) == len(alvo) else
                          'o número fica distorcido (ex.: só o numerador muda)')
                p.aviso(onde, f'o segmentador {s["tabela"]}[{s["nome"]}] não filtra {parte} de "{nome}": '
                              f'ao escolher um valor, {efeito}')
    for nome, cols in paradas.items():
        p.aviso(onde, f'a meta "{nome}" não muda com {", ".join(cols)}: confirme com o dono do indicador que ela vale '
                      'igual para todos esses cortes (se não, a fonte da meta precisa trazer a coluna e a ligação)')
    cal = (m.get('calendario') or {}).get('tabela')
    tem_ano = any(s['tabela'] == cal and s['nome'] in ('Ano', 'Ano-Mês', 'Mês/Ano', 'Ano-Trimestre', 'Data')
                  for s in segs)
    if cal and not tem_ano:
        for v in pagina['visuais']:
            for c in [v['categoria'], v['legenda']] + v['linhas'] + v['colunas']:
                if c and c['tabela'] == cal and c['nome'] in CALENDARIO_SEM_ANO and v['tipo'] not in SEGMENTADORES:
                    p.aviso(onde, f'"{v["titulo"]}" usa {cal}[{c["nome"]}] sem segmentador de ano na página: '
                                  f'soma todos os anos; prefira {cal}[Ano-Trimestre] ou {cal}[Mês/Ano], ou ponha um '
                                  'segmentador de Ano')


def _conferir_snowflake(m, p):
    """Dimensão que chega no fato passando por outra dimensão mostra o valor ATUAL do cadastro."""
    por_nome = {t['nome']: t for t in m['tabelas']}
    for r in m['relacionamentos']:
        de = por_nome.get(r['de'])
        if de and de['tipo'] == 'dimensao' and r['ativo']:
            fatos = sorted(t['nome'] for t in m['tabelas'] if t['tipo'] == 'fato'
                           and _alcanca(_grafo_de_filtro(m), de['nome'], t['nome']))
            if fatos:
                p.aviso(f'relacionamentos {r["de"]} -> {r["para"]}',
                        f'{r["para"]} chega em {", ".join(fatos)} através de {r["de"]}: o corte por {r["para"]} mostra o '
                        f'valor ATUAL do cadastro de {r["de"]}, não o da data do evento. Se a fato tiver o código '
                        'histórico, ligue direto nela; senão, registre isso na definição do indicador')


def _visual(m, v, p, onde, filtra):
    tipo = v.get('tipo')
    if tipo not in TIPOS_VISUAL:
        p.erro(onde, f'tipo inválido ({", ".join(TIPOS_VISUAL)})')
        return None
    r = {'tipo': tipo, 'titulo': v.get('titulo'), 'id': v.get('id'), 'categoria': None, 'legenda': None, 'valores': [],
         'campos': [], 'linhas': [], 'colunas': [], 'meta': None, 'dica': v.get('dica')}
    ok = True
    if tipo in VISUAIS_DE_TERCEIROS:
        p.aviso(onde, f'[Design] {"HTML Content" if tipo == "html" else "Deneb"} é um visual certificado do AppSource, não '
                      'nativo: o administrador do Power BI precisa liberar visuais do AppSource, e quem abre o painel '
                      'baixa o visual na primeira vez')

    def campo(ref, quer, rotulo):
        nonlocal ok
        c = _campo(m, ref)
        if not c:
            p.erro(onde, f'{rotulo} "{ref}" não é {"coluna (Tabela[Coluna])" if quer == "coluna" else "medida"} do modelo'
                   + (pista_coluna(m, ref) if '[' in (ref or '') else _pista_medida(ref, {chave(x['nome']): x for x in m['medidas']
                                                                                            if x['tipo'] != 'cor'})),
                   depende=_depende_de(ref) + tuple(('medida', chave(ref)) for _ in [0] if ref))
            ok = False
        elif quer and c['tipo'] != quer:
            p.erro(onde, f'{rotulo} "{ref}" precisa ser {quer}, veio {c["tipo"]}')
            ok = False
            return None
        return c

    if tipo in ('cartao', 'medidor'):
        r['valores'] = [campo(v.get('medida'), 'medida', 'medida')]
        alvo = medida(m, v.get('medida') or '')
        if v.get('meta'):
            r['meta'] = campo(v['meta'], 'medida', 'meta')
        elif alvo and alvo.get('meta_medida'):
            r['meta'] = _campo(m, alvo['meta_medida'])
    elif tipo in SEGMENTADORES:
        r['categoria'] = campo(v.get('campo'), 'coluna', 'campo')
        r['icone'] = bool(v.get('icone'))              # ícone de selecionado no botão
        if v.get('imagem'):                            # imagem por item, de uma medida SVG (svg_iniciais) ou de URL
            img = medida(m, v['imagem'])
            if not img or not img.get('imagem'):
                p.erro(onde, f'"imagem" ("{v["imagem"]}") precisa ser uma medida de imagem (svg_iniciais ou DAX com '
                             'data:image/...)')
                ok = False
            else:
                r['imagem'] = img['nome']
        if tipo == 'segmentador' and (r['icone'] or v.get('imagem')):
            p.aviso(onde, '[Design] ícone e imagem só aparecem no segmentador de botões: use "tipo": "botoes"')
    elif tipo in ('abas', 'alternar'):                  # o segmentador de botões sobre a tabela auxiliar da medida
        alvo = medida(m, v.get('medida') or '')
        quer = 'escolha' if tipo == 'abas' else 'alternar'
        if not alvo or alvo.get('tipo') != quer or not (alvo.get('extra') or {}).get('tabela'):
            p.erro(onde, f'{tipo} pede "medida": uma medida do tipo {quer}')
            return None
        cfg = alvo['extra']
        r['categoria'] = _campo(m, f'{cfg["tabela"]}[{cfg["coluna"]}]')
        r['controla'] = alvo['nome']
        if not r['titulo']:
            r['titulo'] = cfg.get('rotulo') if tipo == 'alternar' else ''
    elif tipo == 'setas':                              # do valor anterior ao atual, com barras de erro nativas
        r['categoria'] = campo(v.get('categoria'), 'coluna', 'categoria')
        r['valores'] = [campo(v.get('comparar'), 'medida', 'comparar'), campo(v.get('medida'), 'medida', 'medida')]
    elif tipo in ('imagem', 'aviso', 'html'):
        r['valores'] = [campo(v.get('medida'), 'medida', 'medida')]
        alvo = medida(m, v.get('medida') or '')
        if alvo and tipo == 'imagem' and not alvo.get('imagem'):
            p.erro(onde, f'imagem pede uma medida de imagem (svg_dispersao, svg_radar...), veio "{alvo["nome"]}"')
            ok = False
        if alvo and tipo == 'aviso' and alvo.get('tipo') != 'aviso':
            p.erro(onde, f'aviso pede uma medida do tipo aviso, veio "{alvo["nome"]}"')
            ok = False
        if alvo and tipo == 'aviso':
            r['cor_fundo'] = alvo.get('cor_fundo')
    elif tipo == 'vegalite':
        r['categoria'] = campo(v.get('categoria'), 'coluna', 'categoria')
        r['valores'] = [campo(x, 'medida', 'valor') for x in v.get('valores') or []][:2]
        r['spec'] = v.get('spec')
        if not r['valores']:
            p.erro(onde, 'vegalite pede "valores" (as medidas do gráfico)')
            ok = False
    elif tipo == 'cartoes':
        r['valores'] = [campo(x, 'medida', 'medida') for x in v.get('medidas') or []]
        if not r['valores']:
            p.erro(onde, 'cartoes pede "medidas" (a lista de indicadores do cartão)')
            ok = False
    elif tipo == 'decomposicao':
        r['valores'] = [campo(v.get('medida'), 'medida', 'medida')]
        r['linhas'] = [campo(x, 'coluna', 'corte') for x in v.get('cortes') or []]
        if not r['linhas']:
            p.erro(onde, 'decomposicao pede "cortes" (as colunas para abrir o número, na ordem)')
            ok = False
    elif tipo == 'dispersao':
        r['categoria'] = campo(v.get('categoria'), 'coluna', 'categoria')
        r['valores'] = [campo(v.get(k), 'medida', k) for k in ('x', 'y')]
        if v.get('tamanho'):
            r['valores'].append(campo(v['tamanho'], 'medida', 'tamanho'))
    elif tipo == 'mapa':
        r['categoria'] = campo(v.get('local'), 'coluna', 'local')
        r['valores'] = [campo(x, 'medida', 'valor') for x in v.get('valores') or []][:1]
        if v.get('marcador'):                          # cada ponto vira a imagem SVG da medida (estrelas, progresso...)
            img = medida(m, v['marcador'])
            cfg = (img or {}).get('svg') or (img or {}).get('extra') or {}
            if not img or not img.get('imagem'):
                p.erro(onde, f'"marcador" ("{v["marcador"]}") precisa ser uma medida de imagem (svg_estrelas, '
                             'svg_progresso, svg_seta...) feita para a coluna do local')
                ok = False
            else:
                r['marcador'] = img['nome']
                if r['categoria'] and cfg.get('coluna') and (cfg.get('tabela'), cfg['coluna']) != \
                        (r['categoria']['tabela'], r['categoria']['nome']):
                    p.aviso(onde, f'o marcador "{img["nome"]}" foi feito para {cfg["tabela"]}[{cfg["coluna"]}], não para '
                                  f'o local do mapa: o ponto fica sem imagem')
            if v.get('legenda'):
                p.erro(onde, 'mapa com "marcador" não leva "legenda": a pizza e a imagem disputam o mesmo ponto')
                ok = False
        elif not r['valores']:
            p.erro(onde, 'mapa pede "valores" (a medida que dá o tamanho da bolha) ou "marcador" (a medida de imagem)')
            ok = False
        if v.get('legenda') and not v.get('marcador'):  # cada ponto vira uma pizza com a composição
            r['legenda'] = campo(v['legenda'], 'coluna', 'legenda')
        camada = v.get('camada') or 'bolhas'           # colunas: a camada de colunas 3D do Azure Maps
        if camada not in ('bolhas', 'colunas'):
            p.erro(onde, '"camada" deve ser bolhas ou colunas')
            ok = False
        elif camada == 'colunas' and (v.get('marcador') or v.get('legenda')):
            p.erro(onde, '"camada": "colunas" não leva "marcador" nem "legenda": a coluna é o próprio valor')
            ok = False
        r['camada'] = camada
        p.aviso(onde, '[Design] o mapa (Azure Maps) precisa estar liberado pelo administrador do Power BI e de uma '
                      'coluna de local confiável (cidade com UF, ou país)')
    elif tipo == 'tabela':
        r['campos'] = [campo(x, None, 'campo') for x in v.get('campos') or []]
        if not r['campos']:
            p.erro(onde, 'tabela sem "campos"')
            ok = False
    elif tipo == 'matriz':
        r['linhas'] = [campo(x, 'coluna', 'linha') for x in v.get('linhas') or []]
        r['colunas'] = [campo(x, 'coluna', 'coluna') for x in v.get('colunas') or []]
        r['valores'] = [campo(x, 'medida', 'valor') for x in v.get('valores') or []]
        if not r['linhas'] or not r['valores']:
            p.erro(onde, 'matriz pede "linhas" e "valores"')
            ok = False
    else:
        r['categoria'] = campo(v.get('categoria'), 'coluna', 'categoria')
        r['valores'] = [campo(x, 'medida', 'valor') for x in v.get('valores') or []]
        if v.get('legenda'):
            r['legenda'] = campo(v['legenda'], 'coluna', 'legenda')
        if tipo == 'skyline' and not v.get('legenda'):
            p.erro(onde, 'skyline pede "legenda": a coluna de cada bloco empilhado (ex.: o projeto, o tipo)')
            ok = False
        if v.get('cor'):                               # cor de cada barra por medida (ex.: cor_destaque)
            cor = medida(m, v['cor'])
            if not cor or cor.get('tipo') not in ('cor', 'cor_destaque'):
                p.erro(onde, f'"cor" ("{v["cor"]}") precisa ser uma medida de cor (cor_destaque)')
                ok = False
            else:
                r['cor'] = cor['nome']
                if len(v.get('valores') or []) > 1 or v.get('legenda'):
                    p.aviso(onde, '[Design] a cor por medida só vale para gráfico de uma série (sem legenda)')
        if v.get('meta'):                              # linha de meta constante no gráfico ("meta": true usa a do valor)
            nome_meta = v['meta']
            if nome_meta is True:
                base = medida(m, (v.get('valores') or [''])[0])
                nome_meta = (base or {}).get('meta_medida')
                if not nome_meta:
                    p.erro(onde, '"meta": true pede que a medida do gráfico tenha meta; ou dê o nome da medida de meta')
                    return None
            r['meta'] = campo(nome_meta, 'medida', 'meta')
            alvo = medida(m, nome_meta)
            if alvo and alvo.get('tipo') != 'meta':
                p.aviso(onde, f'[Design] a linha de meta só sai com meta fixa (número); "{nome_meta}" muda com o filtro: '
                              'use a barra contra a meta na tabela (svg_barra_meta)')
        if not r['valores']:
            p.erro(onde, 'informe "valores" (medidas)')
            ok = False
        if tipo == 'rosca' and len(r['valores']) > 1:
            p.aviso(onde, 'rosca com mais de uma medida: só a primeira aparece bem')
    if not ok:
        return None
    for x in r['valores'] + r['campos']:
        md = medida(m, x['nome']) if x and x['tipo'] == 'medida' else None
        if md and md.get('imagem') and tipo not in ('tabela', 'matriz', 'imagem'):
            p.erro(onde, f'"{md["nome"]}" é uma imagem (SVG): só aparece em tabela ou matriz')
            return None
        if md and md.get('tipo') in SVG_GERADAS + RANKINGS and (md.get('svg') or md.get('ranking') or {}).get('coluna'):
            cfg = md.get('svg') or md.get('ranking')
            cols = [c for c in r['campos'] if c and c['tipo'] == 'coluna']
            if md['tipo'] == 'lista_top':
                pass
            elif (tipo not in ('tabela', 'matriz') and md['tipo'] not in DIAGNOSTICOS) or not any(
                    (c['tabela'], c['nome']) == (cfg['tabela'], cfg['coluna'])
                    for c in cols + [x for x in r['linhas'] if x]
                    + ([r['categoria']] if md['tipo'] in DIAGNOSTICOS and r['categoria'] else [])):
                p.aviso(onde, f'"{md["nome"]}" foi feita para as linhas de {cfg["tabela"]}[{cfg["coluna"]}]: '
                              'ponha essa coluna na mesma tabela, senão o valor some')
    if not r['titulo']:
        vals = [x['nome'] for x in r['valores'] if x] or [x['nome'] for x in r['campos'] if x]
        cat = r['categoria']['nome'] if r['categoria'] else ''
        r['titulo'] = cat if tipo in SEGMENTADORES else (' e '.join(vals[:2]) + (f' por {cat}' if cat and vals else ''))
    # a coluna filtra a medida? (a categoria de um gráfico precisa chegar na tabela da medida)
    filtros = [x for x in [r['categoria'], r['legenda']] + r['linhas'] + r['colunas'] + r['campos']
               if x and x['tipo'] == 'coluna']
    for f in filtros:
        for md in _medidas_do_visual(r):
            alvo = _tabelas_da_medida(m, md['nome'])
            faltam = sorted(a for a in alvo if not chega(m, filtra, f['tabela'], a, md['nome']))
            if faltam and len(faltam) == len(alvo):
                p.aviso(onde, f'{f["tabela"]}[{f["nome"]}] não filtra a medida "{md["nome"]}" (nenhum relacionamento '
                              f'leva de {f["tabela"]} até {", ".join(faltam)}): o valor vai repetir em toda linha')
            elif faltam:
                p.aviso(onde, f'{f["tabela"]}[{f["nome"]}] filtra só parte de "{md["nome"]}" (não chega em '
                              f'{", ".join(faltam)}): confira se a conta continua fazendo sentido em cada linha')
    return r


def _grafo_de_filtro(m):
    g = {}
    for r in m['relacionamentos']:
        if r['ativo']:
            g.setdefault(r['para'], set()).add(r['de'])     # o lado um filtra o lado muitos
    return g


def _alcanca(g, de, para):
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
    if _alcanca(filtra, tabela_filtro, alvo):
        return True
    cal = (m.get('calendario') or {}).get('tabela')
    return bool(cal) and tabela_filtro == cal and le_calendario(m, nome_medida)


def distorcoes(avisos):
    """Os avisos de número distorcido (o corte filtra só parte da conta): o aprovar não aceita em bloco."""
    return [x for x in avisos if 'filtra só parte' in x or 'fica distorcido' in x]


def grafo_de_filtro(m, extras=()):
    """Quem filtra quem (o lado um filtra o lado muitos); `extras`: ligações [(de, para)] ainda a confirmar."""
    g = _grafo_de_filtro(m)
    for de, para in extras:
        g.setdefault(para, set()).add(de)
    return g


def alcance(m, filtra, tabela_filtro, nome_medida):
    """'total' quando a coluna filtra a medida inteira, 'parcial' quando só parte dela, 'nenhum' quando nada."""
    alvo = _tabelas_da_medida(m, nome_medida)
    faltam = [a for a in alvo if not chega(m, filtra, tabela_filtro, a, nome_medida)]
    return 'total' if not faltam else 'nenhum' if len(faltam) == len(alvo) else 'parcial'


def tabelas_da_medida(m, nome):
    return _tabelas_da_medida(m, nome)


def _tabelas_da_medida(m, nome, vistos=None):
    """Tabelas que a medida lê (seguindo as medidas de que depende)."""
    vistos = vistos or set()
    if chave(nome) in vistos:
        return set()
    vistos.add(chave(nome))
    md = medida(m, nome)
    if not md:
        return set()
    out = set()
    if md.get('tipo') in SVG_GERADAS + RANKINGS + EXTRAS:   # a coluna das linhas só organiza; os dados vêm das medidas
        for n in md.get('depende') or []:
            out |= _tabelas_da_medida(m, n, vistos)
        return out or {md['tabela']}
    for tn, n in referencias_dax(md['dax'] or ''):
        if tn and tabela_do_modelo(m, tn):
            out.add(tabela_do_modelo(m, tn)['nome'])
        elif not tn and medida(m, n):
            out |= _tabelas_da_medida(m, n, vistos)
    if md['dax'] and md['dax'].startswith('COUNTROWS('):
        out.add(md['tabela'])
    out |= set(md.get('tabelas_lidas') or [])
    # CALCULATE de tempo lê o calendário, mas o valor vem da base
    auxiliares = {t['nome'] for t in m['tabelas'] if t.get('auxiliar')}        # a escolha não traz dados
    return {t for t in out if not (m.get('calendario') and t == m['calendario']['tabela']) and t not in auxiliares}         or {md['tabela']}
