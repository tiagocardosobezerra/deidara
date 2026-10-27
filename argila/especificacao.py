"""
A argila: lê o argila.json (a especificação do painel), confere cada nome
contra a estrutura que veio do Vegapunk e devolve o modelo resolvido que os
geradores (protótipo, SQL, TMDL, PBIR, documentação) usam.

Regras que valem aqui, as mesmas do Vegapunk:
- tabela ou coluna que não está no `detalhar` é ERRO, nunca palpite;
- relacionamento só com FK de agrupamento provado; sem prova é erro, a não
  ser que o argila.json diga `"aceitar_sem_prova": true` (vira aviso);
- nenhum dado: o argila.json descreve estrutura e regra, não conteúdo.

Formato completo do argila.json: referencias/argila.md.
"""

import re
from collections import deque

from .util import (FORMATOS, NUMERICAS, chave, dax_coluna, dax_medida, dax_tabela, familia_da_coluna,
                   sql_tipo, tipo_tmdl)

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
    def __init__(self):
        self.erros, self.avisos = [], []

    def erro(self, onde, msg):
        self.erros.append(f'{onde}: {msg}')

    def aviso(self, onde, msg):
        self.avisos.append(f'{onde}: {msg}')


# ============================================================================
def resolver(argila, schema):
    """Devolve (modelo, problemas). Com erro, o modelo não deve ser usado."""
    p = Problemas()
    m = {
        'projeto': (argila.get('projeto') or '').strip(),
        'descricao': argila.get('descricao', ''),
        'publico': argila.get('publico', ''),
        'responsavel': argila.get('responsavel', ''),
        'versao': str(argila.get('versao', '')),
        'fonte': {'servidor': 'SEU_SERVIDOR', 'banco': 'SEU_BANCO', 'esquema_origem': 'dbo',
                  'esquema_views': 'bi', **(argila.get('fonte') or {})},
        'tema': {'cores': ['#118DFF', '#12239E', '#E66C37', '#6B007B', '#E044A7', '#744EC2', '#D9B300',
                           '#D64550'], 'fundo': '#FFFFFF', 'texto': '#252423', **(argila.get('tema') or {})},
        'tabelas': [], 'relacionamentos': [], 'medidas': [], 'paginas': [], 'seguranca': [],
    }
    if not m['projeto']:
        p.erro('projeto', 'informe o nome do projeto')
    _tabelas(argila, schema, m, p)
    _calendario(argila, m, p)
    _relacionamentos(argila, schema, m, p)
    _medidas(argila, m, p)
    _seguranca(argila, m, p)
    _paginas(argila, m, p)
    if not m['versao']:
        p.aviso('versao', 'sem "versao" no argila.json: informe (ex.: "1.0") para o histórico de mudanças')
    return m, p


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
            regras.append({'tabela': t['nome'], 'filtro': r['filtro'].strip()})
            if 'USERPRINCIPALNAME' not in r['filtro'].upper() and 'USERNAME' not in r['filtro'].upper():
                p.aviso(onde, f'regra {j + 1} não usa USERPRINCIPALNAME(): o filtro vale igual para todos do papel')
        if not regras:
            p.erro(onde, 'papel sem nenhuma regra válida')
            continue
        m['seguranca'].append({'papel': nome, 'descricao': papel.get('descricao', ''), 'regras': regras})


# ------------------------------------------------------------------ tabelas
def _tabelas(argila, schema, m, p):
    nomes = set()
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
        origem = schema.tabela(t.get('origem', ''))
        if not origem:
            sug = schema.parecidas(t.get('origem', ''))
            p.erro(onde, f'origem "{t.get("origem")}" não veio do Vegapunk (detalhar)'
                         + (f'; parecidas: {", ".join(schema.tabelas[s]["nome"] for s in sug)}' if sug else
                            '; rode o `detalhar` com essa tabela antes'))
            continue
        tab = {'nome': nome, 'tipo': tipo, 'origem': origem['nome'], 'descricao': t.get('descricao')
               or origem['descricao'] or '', 'filtro': t.get('filtro'), 'colunas': [], 'calendario': False,
               'pk': origem['pk']}
        if t.get('filtro'):
            p.aviso(onde, 'o "filtro" entra no WHERE da view sem conferência de nomes: revise o SQL gerado')
        cols = set()
        for j, c in enumerate(t.get('colunas') or []):
            if isinstance(c, str):
                c = {'coluna': c}
            oc = schema.coluna(origem['nome'], c.get('coluna', ''))
            ondec = f'{onde}.colunas[{j}]'
            if not oc:
                sug = schema.colunas_parecidas(origem['nome'], c.get('coluna', ''))
                p.erro(ondec, f'coluna "{c.get("coluna")}" não existe em {origem["nome"]}'
                              + (f'; parecidas: {", ".join(sug)}' if sug else ''))
                continue
            familia = familia_da_coluna(oc)
            if c.get('tipo'):
                familia = c['tipo']
            elif not familia:
                familia = 'texto'
                p.aviso(ondec, f'{origem["nome"]}.{oc["coluna"]} veio sem tipo (base não enriquecida): '
                               'tratada como texto; informe "tipo" ou rode o `york.py enriquecer` no Vegapunk')
            col = _coluna(c.get('nome') or oc['coluna'], oc['coluna'], familia,
                          descricao=c.get('descricao') or oc.get('descricao') or '',
                          oculta=bool(c.get('oculta')), formato=c.get('formato'))
            col['sql_tipo'] = sql_tipo(oc)
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
            'como_data': False, 'gerada': origem is None, 'sql_tipo': None, 'cast_sql': None}


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
        if c['origem'] and chave(c['origem']) == chave(origem) and not c['expressao_sql']:
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
            p.erro(onde, f'{d.get("tabela")}[{d.get("coluna")}] não está no modelo')
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
def _relacionamentos(argila, schema, m, p):
    for i, r in enumerate(argila.get('relacionamentos') or []):
        onde = f'relacionamentos[{i}] {r.get("de")} -> {r.get("para")}'
        de, para = tabela_do_modelo(m, r.get('de', '')), tabela_do_modelo(m, r.get('para', ''))
        if not de or not para:
            p.erro(onde, 'as duas pontas precisam ser tabelas do modelo ("de" = lado muitos, "para" = lado um)')
            continue
        if not de['origem'] or not para['origem']:
            p.erro(onde, 'use "calendario.datas" para ligar ao calendário')
            continue
        fks = schema.fks_entre(de['origem'], para['origem'])
        via = [chave(x) for x in (r.get('via') or [])]
        if via:
            fks = [fk for fk in fks if sorted(chave(x['campo_filho']) for x in fk['colunas']) == sorted(via)]
        if not fks:
            invertida = schema.fks_entre(para['origem'], de['origem'])
            sem = schema.sem_prova_entre(de['origem'], para['origem'])
            if invertida:
                p.erro(onde, f'a FK vai de {para["origem"]} (filha) para {de["origem"]} (mãe): inverta '
                             '"de" e "para" (o "para" é sempre o lado um, a tabela mãe)')
                continue
            if sem and r.get('aceitar_sem_prova'):
                campos = [(l['campo_filho'], l['campo_mae']) for l in sem]
                if via:
                    campos = [c for c in campos if chave(c[0]) in via]
                p.aviso(onde, 'ligação SEM agrupamento provado (' + ', '.join(sorted({l.get('motivo', '?')
                              for l in sem})) + '), aceita no argila.json: confira os campos com o dono do dado')
                _ligar(schema, m, de, para, campos, r, f'sem prova ({sem[0].get("motivo")})', p, onde)
                continue
            if sem:
                p.erro(onde, 'só existe ligação sem agrupamento provado (motivo: '
                             + ', '.join(sorted({l.get('motivo', '?') for l in sem}))
                             + '); confirme os campos com o usuário e use "aceitar_sem_prova": true + "via"')
            else:
                p.erro(onde, f'nenhuma FK de {de["origem"]} para {para["origem"]} no detalhar: não invente a '
                             'ligação (rode o `detalhar` com as duas tabelas e veja os `caminhos`)')
            continue
        if len(fks) > 1:
            p.erro(onde, 'mais de uma FK entre as tabelas; escolha com "via": '
                         + ' | '.join('[' + ', '.join(x['campo_filho'] for x in fk['colunas']) + ']' for fk in fks))
            continue
        fk = fks[0]
        if fk.get('cobre_chave_da_mae') is False:
            p.aviso(onde, 'a FK não cobre a PK inteira da mãe: o lado "um" pode ter duplicatas e o Power BI '
                          'vai recusar a relação 1:*; confirme com o dono do dado')
        campos = [(x['campo_filho'], x['campo_mae']) for x in fk['colunas']]
        _ligar(schema, m, de, para, campos, r, f'{fk["origem"]}' + (f' ({fk["constraint"]})' if fk.get('constraint') else ''),
               p, onde)
    _conferir_ativos(m, p)


def _ligar(schema, m, de, para, campos, r, prova, p, onde):
    if len(campos) == 1:
        filho, mae = campos[0]
        cf = _garantir_coluna(schema, de, filho, p, onde)
        cm = _garantir_coluna(schema, para, mae, p, onde)
        if not cf or not cm:
            return
        if cf['tipo_tmdl'] != cm['tipo_tmdl']:
            # o modelo tabular não relaciona tipos diferentes: a view da filha converte para o tipo da mãe
            if not cm.get('sql_tipo'):
                p.erro(onde, f'tipos diferentes nas pontas ({cf["familia"]} x {cm["familia"]}) e a mãe veio sem tipo '
                             'no detalhar: informe "tipo" nas duas colunas')
                return
            cf['cast_sql'], cf['familia'], cf['tipo_tmdl'] = cm['sql_tipo'], cm['familia'], cm['tipo_tmdl']
            p.aviso(onde, f'tipos diferentes nas pontas: {de["nome"]}[{cf["nome"]}] é convertida para {cm["sql_tipo"]} '
                          'na view (o Power BI não relaciona tipos diferentes); confira se a conversão não perde valor')
        de_col, para_col, composta = cf['nome'], cm['nome'], False
    else:
        nome = f'Chave {para["nome"]}'
        de_col = _chave_composta(schema, de, nome, [f for f, _ in campos])
        para_col = _chave_composta(schema, para, nome, [mm for _, mm in campos])
        composta = True
    m['relacionamentos'].append({'de': de['nome'], 'de_coluna': de_col, 'para': para['nome'], 'para_coluna': para_col,
                                 'ativo': r.get('ativo', True), 'prova': prova, 'composta': composta,
                                 'campos': campos, 'aviso': None})


def _garantir_coluna(schema, t, origem, p, onde):
    c = coluna_por_origem(t, origem)
    if c:
        return c
    # a coluna de ligação não foi pedida: entra oculta, com o tipo do detalhar
    oc = schema.coluna(t['origem'], origem) or {}
    c = _coluna(oc.get('coluna', origem), oc.get('coluna', origem), familia_da_coluna(oc) or 'texto',
                descricao=oc.get('descricao') or '', oculta=True)
    c['sql_tipo'] = sql_tipo(oc)
    c['auto'] = True
    if coluna_do_modelo(t, origem):
        p.erro(onde, f'{t["nome"]} já tem uma coluna chamada {origem} com outra origem')
        return None
    t['colunas'].append(c)
    return c


def _chave_composta(schema, t, nome, campos):
    existente = coluna_do_modelo(t, nome)
    if existente:
        return existente['nome']
    expr = 'CONCAT(' + ", N'|', ".join(_parte_da_chave(schema, t, c) for c in campos) + ')'
    c = _coluna(nome, None, 'texto', descricao='Chave composta gerada pelo Deidara: ' + ' + '.join(campos),
                oculta=True, expressao_sql=expr)
    t['colunas'].append(c)
    return nome


def _parte_da_chave(schema, t, campo):
    """Um campo da chave composta como texto estável: data em ISO (independe do
    idioma da sessão), sem espaço à direita (char) e NULL marcado (senão NULL e
    '' viram a mesma chave)."""
    familia = familia_da_coluna(schema.coluna(t['origem'], campo) or {})
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
                        p.erro(onde, f'{k} "{md.get(k)}" não é uma medida do modelo')
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
        p.erro(onde, f'coluna "{md.get("coluna")}" não está no modelo (use Tabela[Coluna])')
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
        p.erro(onde, f'base "{base}" não é uma medida do modelo')
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
    if not ce or ce['familia'] not in ('data', 'datahora'):
        p.erro(onde, f'"entradas" ("{md.get("entradas")}") precisa ser uma coluna de data do modelo (Tabela[Coluna])')
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
            p.erro(onde, f'"saidas" ("{md.get("saidas")}") precisa ser uma coluna de data do modelo (Tabela[Coluna])')
            return
        if not _alcanca(_grafo_de_filtro(m), te['nome'], ts['nome']):
            p.aviso(onde, f'{te["nome"]} não filtra {ts["nome"]}: um corte por {te["nome"]} vai tirar as saídas de '
                          'todo mundo; confira o relacionamento')
        lidas.append(ts['nome'])
        dax += (f'VAR _saidas =\n    CALCULATE(\n        COUNTROWS({dax_tabela(ts["nome"])}),\n'
                f'        {dax_coluna(ts["nome"], cs["nome"])} <= _fim,\n        REMOVEFILTERS({dax_tabela(cal)})\n    )\n'
                'RETURN\n    IF(MIN(' + dax_coluna(cal, 'Data') + ') > TODAY(), BLANK(), _entradas - _saidas)')
    else:
        dax += 'RETURN\n    IF(MIN(' + dax_coluna(cal, 'Data') + ') > TODAY(), BLANK(), _entradas)'
    r['dax'], r['tabela'] = dax, md.get('tabela') or te['nome']
    r['tabelas_lidas'], r['le_calendario'], r['depende'] = lidas, True, []


def _conferir_refs(m, r, nomes, p, onde):
    deps = []
    for tn, n in referencias_dax(r['dax']):
        if tn:
            t = tabela_do_modelo(m, tn)
            if not t:
                p.erro(onde, f'tabela "{tn}" do DAX não está no modelo')
            elif not coluna_do_modelo(t, n) and chave(n) not in nomes:
                p.erro(onde, f'coluna "{tn}[{n}]" do DAX não está no modelo')
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
                p.aviso(onde, f'o segmentador {s["tabela"]}[{s["nome"]}] não filtra {parte} de "{nome}": '
                              'ao escolher um valor, o número fica parado ou distorcido (ex.: só o numerador muda)')
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
            p.erro(onde, f'{rotulo} "{ref}" não é {"coluna (Tabela[Coluna])" if quer == "coluna" else "medida"} do modelo')
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
