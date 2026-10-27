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

from . import dicionario, prova

from .util import (FORMATOS, NUMERICAS, SQL_POR_FAMILIA, chave, dax_coluna, dax_medida, dax_tabela,
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
}
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
                           '#D64550'], 'fundo': '#FFFFFF', 'texto': '#252423', **(argila.get('tema') or {})},
        'tabelas': [], 'relacionamentos': [], 'medidas': [], 'paginas': [], 'seguranca': [], 'pendencias': [],
    }
    if not m['projeto']:
        p.erro('projeto', 'informe o nome do projeto')
    _tabelas(argila, catalogos, m, p)
    _calendario(argila, m, p)
    _relacionamentos(argila, catalogos, m, p)
    _medidas(argila, m, p)
    _seguranca(argila, m, p)
    _paginas(argila, m, p)
    _privacidade(m, p)
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
    from .esboco import _pessoal
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
            elif md.get('dax'):
                r['tipo'] = 'dax'
                r['dax'] = md['dax'].strip()
                _conferir_refs(m, r, nomes, p, onde)
            else:
                p.erro(onde, 'informe "agregacao", "tipo" (divisao, acumulado_ano, ano_anterior, '
                             'variacao_ano_anterior, variacao_mes_anterior) ou "dax"')
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
    _ciclos(m, p)
    for md in m['medidas']:
        if md.get('tipo') not in ('cor', 'meta') and (not (md.get('descricao') or '').strip()
                                                      or md['descricao'].strip().upper().startswith('A DEFINIR')):
            m['pendencias'].append(f'medida {md["nome"]}: definição de negócio pendente')
            p.aviso(f'medida {md["nome"]}', 'definição pendente: escreva o que o número significa (numerador, '
                                            'filtro, período) antes de mostrar ao gestor; o aprovar recusa sem ela')


COR_BOA, COR_RUIM = '#107C10', '#D13438'


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


def _conferir_refs(m, r, nomes, p, onde):
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
        pagina = {'nome': nome, 'descricao': pg.get('descricao', ''), 'visuais': []}
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
    _conferir_snowflake(m, p)


def _medidas_do_visual(r):
    return [x for x in r['valores'] + r['campos'] + ([r['meta']] if r.get('meta') else []) if x and x['tipo'] == 'medida']


def _conferir_pagina(m, pagina, p, onde, filtra):
    segs = [v['categoria'] for v in pagina['visuais'] if v['tipo'] == 'segmentador' and v['categoria']]
    medidas = {md['nome'] for v in pagina['visuais'] for md in _medidas_do_visual(v)}
    for s in segs:
        for nome in sorted(medidas):
            alvo = _tabelas_da_medida(m, nome)
            faltam = sorted(a for a in alvo if not chega(m, filtra, s['tabela'], a, nome))
            if faltam:
                parte = 'a medida inteira' if len(faltam) == len(alvo) else 'parte da medida (' + ', '.join(faltam) + ')'
                efeito = ('o número fica parado' if len(faltam) == len(alvo) else
                          'o número fica distorcido (ex.: só o numerador muda)')
                p.aviso(onde, f'o segmentador {s["tabela"]}[{s["nome"]}] não filtra {parte} de "{nome}": '
                              f'ao escolher um valor, {efeito}')
    cal = (m.get('calendario') or {}).get('tabela')
    tem_ano = any(s['tabela'] == cal and s['nome'] in ('Ano', 'Ano-Mês', 'Mês/Ano', 'Ano-Trimestre', 'Data')
                  for s in segs)
    if cal and not tem_ano:
        for v in pagina['visuais']:
            for c in [v['categoria'], v['legenda']] + v['linhas'] + v['colunas']:
                if c and c['tabela'] == cal and c['nome'] in CALENDARIO_SEM_ANO and v['tipo'] != 'segmentador':
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
         'campos': [], 'linhas': [], 'colunas': [], 'meta': None}
    ok = True

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
    elif tipo == 'segmentador':
        r['categoria'] = campo(v.get('campo'), 'coluna', 'campo')
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
        if not r['valores']:
            p.erro(onde, 'informe "valores" (medidas)')
            ok = False
        if tipo == 'rosca' and len(r['valores']) > 1:
            p.aviso(onde, 'rosca com mais de uma medida: só a primeira aparece bem')
    if not ok:
        return None
    if not r['titulo']:
        vals = [x['nome'] for x in r['valores'] if x] or [x['nome'] for x in r['campos'] if x]
        cat = r['categoria']['nome'] if r['categoria'] else ''
        r['titulo'] = cat if tipo == 'segmentador' else (' e '.join(vals[:2]) + (f' por {cat}' if cat and vals else ''))
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
    for tn, n in referencias_dax(md['dax'] or ''):
        if tn and tabela_do_modelo(m, tn):
            out.add(tabela_do_modelo(m, tn)['nome'])
        elif not tn and medida(m, n):
            out |= _tabelas_da_medida(m, n, vistos)
    if md['dax'] and md['dax'].startswith('COUNTROWS('):
        out.add(md['tabela'])
    out |= set(md.get('tabelas_lidas') or [])
    # CALCULATE de tempo lê o calendário, mas o valor vem da base
    return {t for t in out if not (m.get('calendario') and t == m['calendario']['tabela'])} or {md['tabela']}
