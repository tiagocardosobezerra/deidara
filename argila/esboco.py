"""
Esboço: um primeiro argila.json a partir dos catálogos e de um pedido em
português, para chegar rápido ao primeiro protótipo.

É um ponto de partida, não uma decisão: o que precisa de uma pessoa sai
marcado e o `validar` não deixa passar:
- ligação sugerida (sem prova no catálogo) -> "declarada" com por "A CONFIRMAR";
- definição de indicador -> "A DEFINIR: ...".
"""

import re

from . import descoberta
from .util import chave, sem_acento

PENDENTE_POR = 'A CONFIRMAR'
PENDENTE_DEF = 'A DEFINIR'
PREFIXOS_TABELA = re.compile(r'^(tb|tbl|dim|fato|fact|vw|[a-z])_', re.I)


def _camel(texto):
    partes = [p for p in re.split(r'[^A-Za-z0-9]+', sem_acento(texto)) if p]
    return ''.join(p[:1].upper() + p[1:].lower() for p in partes) or 'Tabela'


def nome_no_modelo(origem, tipo):
    base = PREFIXOS_TABELA.sub('', origem)
    return ('f' if tipo == 'fato' else 'd') + _camel(base)


ACENTOS = {
    'descricao': 'descrição', 'codigo': 'código', 'admissao': 'admissão', 'razao': 'razão', 'remuneracao': 'remuneração',
    'matricula': 'matrícula', 'funcao': 'função', 'situacao': 'situação', 'numero': 'número', 'mes': 'mês',
    'periodo': 'período', 'salario': 'salário', 'demissao': 'demissão', 'rescisao': 'rescisão', 'endereco': 'endereço',
    'emissao': 'emissão', 'previsao': 'previsão', 'operacao': 'operação', 'unidade': 'unidade', 'secao': 'seção',
    'credito': 'crédito', 'debito': 'débito', 'historico': 'histórico', 'servico': 'serviço', 'preco': 'preço',
    'orcamento': 'orçamento', 'responsavel': 'responsável', 'ultimo': 'último', 'media': 'média', 'contratacao':
    'contratação', 'producao': 'produção', 'avaliacao': 'avaliação', 'deligamento': 'desligamento',
}
PESSOAIS = {'cpf', 'rg', 'cnh', 'pis', 'email', 'telefone', 'celular', 'nascimento', 'endereco', 'logradouro', 'cep',
            'mae', 'pai', 'sexo', 'genero', 'raca', 'religiao'}
TABELAS_DE_PESSOA = {'funcionario', 'colaborador', 'empregado', 'pessoa', 'cliente', 'paciente', 'aluno', 'candidato',
                     'fornecedor_pf', 'usuario', 'chapa'}


def _acentuar(texto):
    return ' '.join(ACENTOS.get(p.lower(), p) if p.lower() in ACENTOS else p for p in texto.split())


def nome_amigavel(coluna):
    """Nome de exibição curto e com acento: 'Descricao do motivo de desligamento' -> 'Motivo';
    'Codigo da empresa' -> 'Cód. Empresa'."""
    d = (coluna.get('descricao') or '').strip()
    toks = descoberta.tokens(coluna['coluna'])
    base = d if 3 <= len(d) <= 40 else (' '.join(toks) if toks else coluna['coluna'])
    base = re.sub(r'\s+(do|da|de|dos|das)\s+(colaborador|funcion[aá]rio|empregado|empresa|cliente)$', '', base, flags=re.I)
    codigo = re.match(r'^(c[oó]digo|cod\.?|id)\s+(do|da|de|dos|das)?\s*(.+)$', base, flags=re.I)
    if codigo:
        resto = re.sub(r'\s+(de|do|da)\s+.*$', '', codigo.group(3))
        return 'Cód. ' + _acentuar(resto)[:1].upper() + _acentuar(resto)[1:]
    desc = re.match(r'^(descri[cç][aã]o|nome|raz[aã]o social)\s+(do|da|de|dos|das)?\s*(.+)$', base, flags=re.I)
    if desc:
        base = re.sub(r'\s+(de|do|da)\s+.*$', '', desc.group(3))
    texto = _acentuar(base)
    return texto[:1].upper() + texto[1:]


def _pessoal(t, coluna):
    """Coluna que identifica uma pessoa (CPF, e-mail... e o nome numa tabela de pessoas)."""
    toks = set(descoberta.tokens(coluna['coluna']))
    if toks & PESSOAIS:
        return True
    de_pessoa = bool(set(descoberta.tokens(t['nome'])) & TABELAS_DE_PESSOA)
    return de_pessoa and bool(toks & {'nome', 'nm', 'apelido'})


def _datas(t):
    return [c for c in t['colunas'].values() if c.get('familia') in ('data', 'datahora')]


def _valores(t):
    pk = {x.upper() for x in t['pk']}
    return [c for c in t['colunas'].values() if c.get('familia') in ('decimal', 'real')
            and c['coluna'].upper() not in pk and not descoberta.tem_marca_de_chave(c['coluna'])]


def _rotulo(t):
    """A coluna que dá nome ao registro de uma dimensão (descrição, nome, razão social); nunca dado pessoal."""
    pk = {x.upper() for x in t['pk']}
    textos = [c for c in t['colunas'].values() if c.get('familia') == 'texto' and c['coluna'].upper() not in pk
              and not _pessoal(t, c)]
    for c in textos:
        if any(t.startswith(('descricao', 'nome', 'razao', 'titulo', 'apelido', 'fantasia'))
               for t in descoberta.tokens(c['coluna'])):
            return c
    return textos[0] if textos else None


def esbocar(catalogos, pedido, projeto=None, tabelas=None, limite=6):
    """Devolve (argila, notas). `tabelas`: [(fonte, origem)] para escolher à mão; senão, a busca escolhe."""
    notas = []
    if tabelas:
        escolhidas = [(f, catalogos[f].tabela(o)['nome']) for f, o in tabelas if catalogos[f].tabela(o)]
    else:
        achados = descoberta.buscar(catalogos, pedido, limite)
        literais = set(descoberta.tokens(pedido))
        # só as tabelas que batem com uma palavra DITA no pedido (não só por sinônimo)
        diretas = [r for r in achados if literais & set(r['termos'])]
        fora = [r['tabela'] for r in achados if r not in diretas]
        achados = diretas or achados
        if fora and diretas:
            notas.append('ficaram de fora (só batiam por sinônimo): ' + ', '.join(fora) + ' — inclua com --tabelas')
        escolhidas = [(r['fonte'], r['tabela']) for r in achados]
        notas.append('tabelas escolhidas pela busca: ' + ', '.join(t for _, t in escolhidas)
                     + ' (confirme com o usuário; troque com --tabelas)')
    if not escolhidas:
        raise ValueError('nenhuma tabela encontrada para o pedido: use palavras do negócio ou --tabelas')
    # mãe de outra escolhida (com chave) é dimensão; filha (ou sem chave) com data ou valor é fato
    filhas, maes = set(), set()
    for f, o in escolhidas:
        for fk in catalogos[f].fks:
            if fk['tabela_filha'] == o and any(fk['tabela_mae'] == x for g, x in escolhidas if g == f):
                filhas.add((f, o))
                maes.add((f, fk['tabela_mae']))
    tipos = {}
    for f, o in escolhidas:
        t = catalogos[f].tabela(o)
        mede = bool(_datas(t) or _valores(t))
        if (f, o) in maes and t['pk']:
            tipos[(f, o)] = 'dimensao'
        else:
            tipos[(f, o)] = 'fato' if mede and ((f, o) in filhas or not t['pk']) else 'dimensao'
    if 'fato' not in tipos.values():
        candidata = max(escolhidas, key=lambda x: len(_datas(catalogos[x[0]].tabela(x[1]))))
        tipos[candidata] = 'fato'
    nomes = {k: nome_no_modelo(k[1], tipos[k]) for k in escolhidas}

    tabs = []
    for (f, o) in escolhidas:
        t = catalogos[f].tabela(o)
        cols, usados = [], set()

        def add(c):
            if c and c['coluna'] not in usados:
                usados.add(c['coluna'])
                nome = nome_amigavel(c)
                if chave(nome) in {chave(x.get('nome', '')) for x in cols}:
                    nome = c['coluna']
                cols.append({'coluna': c['coluna'], 'nome': nome})

        if tipos[(f, o)] == 'dimensao':
            for p in t['pk']:
                add(t['colunas'].get(chave(p)))
            add(_rotulo(t))
        else:
            for c in _datas(t)[:2] + _valores(t)[:4]:
                add(c)
        if not cols:
            add(next(iter(t['colunas'].values()), None))
        tabs.append({'nome': nomes[(f, o)], 'tipo': tipos[(f, o)], 'fonte': f, 'origem': o, 'colunas': cols})

    # ligações: as provadas no catálogo e, entre fontes, as sugeridas (a confirmar)
    rels = []
    sug = descoberta.relacionar(catalogos, [(f, o, nomes[(f, o)]) for f, o in escolhidas])
    for s in sug:
        if s.get('redundante') or s['confianca'] == 'baixa':
            continue
        de_k = next(k for k in escolhidas if nomes[k] == s['de'])
        para_k = next(k for k in escolhidas if nomes[k] == s['para'])
        if tipos[para_k] == 'fato' and tipos[de_k] == 'dimensao':
            continue                                   # dimensão não aponta para fato
        if s['provada_no_catalogo']:
            rels.append({'de': s['de'], 'para': s['para']})
        else:
            rels.append({'de': s['de'], 'para': s['para'], 'declarada': {
                'campos': [[s['campo_filho'], s['campo_mae']]], 'por': PENDENTE_POR,
                'motivo': 'sugerida pelo Deidara: ' + '; '.join(s['motivos'])}})
            notas.append(f'ligação {s["de"]} -> {s["para"]} SUGERIDA (confiança {s["confianca"]}): confirme os campos '
                         f'com o dono do dado e rode `deidara.py confirmar <argila> --ligacao {s["de"]}->{s["para"]} '
                         f'--por "<quem confirmou>"` (ou --remover)')

    # calendário: a primeira data de cada fato
    datas = []
    for tb in tabs:
        if tb['tipo'] != 'fato':
            continue
        t = catalogos[tb['fonte']].tabela(tb['origem'])
        d = next((c for c in tb['colunas'] if t['colunas'][chave(c['coluna'])].get('familia') in ('data', 'datahora')), None)
        if d:
            datas.append({'tabela': tb['nome'], 'coluna': d['nome']})

    # medidas: contagem de cada fato e soma de cada valor
    medidas = []
    for tb in tabs:
        if tb['tipo'] != 'fato':
            continue
        rotulo = re.sub(r'^f', '', tb['nome'])
        t = catalogos[tb['fonte']].tabela(tb['origem'])
        if _datas(t):                                   # contagem só faz sentido em fato de evento (com data)
            medidas.append({'nome': f'Qtd {rotulo}', 'agregacao': 'contagem_linhas', 'tabela': tb['nome'],
                            'descricao': f'{PENDENTE_DEF}: o que cada linha de {tb["origem"]} representa e o que conta',
                            'pasta': rotulo})
        for c in tb['colunas']:
            if t['colunas'][chave(c['coluna'])].get('familia') in ('decimal', 'real'):
                toks = set(descoberta.tokens(c['coluna'])) | set(descoberta.tokens(c['nome']))
                taxa = toks & {'meta', 'percentual', 'pct', 'taxa', 'indice', 'perc', 'media', 'aliquota'}
                nome_md = (f'Meta de {re.sub(r"^meta\s*", "", c["nome"], flags=re.I).strip() or rotulo}'
                           if 'meta' in toks else f'{"Média" if taxa else "Total"} {c["nome"]}')
                medidas.append({'nome': nome_md,
                                'agregacao': 'media' if taxa else 'soma', 'coluna': f'{tb["nome"]}[{c["nome"]}]',
                                'formato': 'percentual' if taxa - {'media', 'indice'} else 'decimal',
                                'descricao': f'{PENDENTE_DEF}: o que este número significa para o negócio',
                                'pasta': rotulo})

    # página de visão geral: o fato principal (o primeiro com data) e só os cortes que chegam nele
    fato = next((d['tabela'] for d in datas), next((tb['nome'] for tb in tabs if tb['tipo'] == 'fato'), None))
    chega = {fato}
    mudou = True
    while mudou:
        mudou = False
        for r in rels:
            if r['de'] in chega and r['para'] not in chega and 'declarada' not in r:
                chega.add(r['para'])
                mudou = True
    principais = [md for md in medidas if md['tabela' if 'tabela' in md else 'coluna'].split('[')[0] == fato]
    vis = []
    if datas and any(d['tabela'] == fato for d in datas):
        vis.append({'tipo': 'segmentador', 'campo': 'dCalendario[Ano]'})
    dims = [tb for tb in tabs if tb['tipo'] == 'dimensao' and len(tb['colunas']) > 1 and tb['nome'] in chega]
    for d in dims[:2]:
        vis.append({'tipo': 'segmentador', 'campo': f'{d["nome"]}[{d["colunas"][-1]["nome"]}]'})
    for md in principais[:4]:
        vis.append({'tipo': 'cartao', 'medida': md['nome']})
    medidas_pagina = principais
    if medidas_pagina:
        principal = medidas_pagina[0]['nome']
        if datas:
            vis.append({'tipo': 'colunas', 'categoria': 'dCalendario[Mês/Ano]', 'valores': [principal]})
        literais = descoberta._expandir(frozenset(descoberta.tokens(pedido)), descoberta._sinonimos())
        citadas = [d for d in dims if literais & set(descoberta.tokens(d['origem']) + descoberta.tokens(d['nome']))]
        for d in (citadas or dims[:1])[:3]:                    # um visual por corte citado no pedido
            vis.append({'tipo': 'barras', 'categoria': f'{d["nome"]}[{d["colunas"][-1]["nome"]}]',
                        'valores': [principal]})
        if dims:
            vis.append({'tipo': 'tabela', 'campos': [f'{dims[0]["nome"]}[{dims[0]["colunas"][-1]["nome"]}]']
                        + [m['nome'] for m in medidas_pagina[:3]]})
    outras = [md for md in medidas if md not in principais]
    if outras:
        notas.append('medidas de outras tabelas fato (' + ', '.join(m['nome'] for m in outras)
                     + ') ficaram fora da página: ponha numa página própria ou ligue os cortes a elas')

    argila = {'projeto': projeto or pedido[:60].strip().capitalize(), 'versao': '0.1',
              'descricao': f'{PENDENTE_DEF}: para que serve o painel e que decisão ele apoia',
              'publico': PENDENTE_DEF, 'fontes': {}, 'tabelas': tabs, 'relacionamentos': rels,
              'medidas': medidas, 'paginas': [{'nome': 'Visão Geral', 'visuais': vis}]}
    if datas:
        anos = 2018, 2026
        argila['calendario'] = {'inicio': anos[0], 'fim': anos[1], 'datas': datas}
    notas.append('defina cada indicador (descrição, polaridade, meta) antes de mostrar ao gestor: '
                 f'os "{PENDENTE_DEF}" viram aviso no validar')
    return argila, notas
