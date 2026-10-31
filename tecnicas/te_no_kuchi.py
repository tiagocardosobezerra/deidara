"""
================================================================================
 TE NO KUCHI — as bocas das mãos
================================================================================
Nome de referência: as mãos do Deidara têm bocas que mastigam a argila e dão a
ela a primeira forma. Aqui é o esboço: um primeiro argila.json a partir dos
catálogos e de um pedido em português, para chegar rápido ao primeiro
protótipo.

É um ponto de partida, não uma decisão: o que precisa de uma pessoa sai
marcado e o `validar` não deixa passar:
- ligação sugerida (sem prova no catálogo) -> "declarada" com por "A CONFIRMAR";
- definição de indicador -> "A DEFINIR: ...".
"""

import datetime
import re

from tecnicas.luneta import descoberta
from kibaku_nendo.privacidade import pessoal
from kibaku_nendo.util import chave, sem_acento

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
    'liquido': 'líquido', 'liquida': 'líquida', 'cancelamento': 'cancelamento', 'cotacao': 'cotação',
}


def _acentuar(texto):
    return ' '.join(ACENTOS.get(p.lower(), p) if p.lower() in ACENTOS else p for p in texto.split())


def nome_amigavel(coluna):
    """Nome de exibição curto e com acento: 'Descricao do motivo de desligamento' -> 'Motivo';
    'Codigo da empresa' -> 'Cód. Empresa'."""
    d = (coluna.get('descricao') or '').strip().replace('_', ' ')
    if re.sub(r'[\s_]', '', chave(d)) == re.sub(r'[\s_]', '', chave(coluna['coluna'])):
        d = ''                                       # a descrição só repete o código (META_VALOR): usa os pedaços
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
              and not pessoal(t, c)]
    for c in textos:
        if any(t.startswith(('descricao', 'nome', 'razao', 'titulo', 'apelido', 'fantasia'))
               for t in descoberta.tokens(c['coluna'])):
            return c
    return textos[0] if textos else None


REF = re.compile(r'^(\w+)\[(.+)\]$')


def _papeis_do_padrao(p):
    """As tabelas que a cadeia de um padrão usa ('fDesligamento', 'dColaborador') e as colunas de cada uma."""
    papeis = {}
    for md in p['cadeia']:
        if md.get('tabela'):
            papeis.setdefault(md['tabela'], [])
        for k in ('entradas', 'saidas', 'coluna'):
            mt = REF.match(md.get(k) or '')
            if mt:
                papeis.setdefault(mt.group(1), [])
                if mt.group(2) not in papeis[mt.group(1)]:
                    papeis[mt.group(1)].append(mt.group(2))
    return papeis


# palavra do padrão -> como ela costuma aparecer na coluna do ERP (VALORLIQUIDO faz o papel de "Receita Líquida")
SINONIMOS_PAPEL = {'receita': {'valor', 'faturamento', 'venda', 'vendas', 'vlr', 'receita'},
                   'custo': {'custo', 'cmv', 'cpv'}, 'pedido': {'pedido', 'nota', 'documento'},
                   'cliente': {'cliente', 'consumidor'}, 'chamado': {'chamado', 'ticket', 'ocorrencia'}}


def _radical(t):
    return t[:5] if len(t) >= 5 else t


def _casa(q, tem):
    """O token `q` do papel aparece na coluna, pelo nome, por sinônimo ou pelo radical (líquida ~ líquido)."""
    opcoes = SINONIMOS_PAPEL.get(q, {q})
    return bool(opcoes & tem) or any(_radical(q) == _radical(x) for x in tem)


def _coluna_do_papel(t, nome):
    """A coluna do catálogo que faz o papel de `nome` ('Data de Admissão' -> DATAADMISSAO), ou None."""
    quer = set(descoberta.tokens(nome))
    datas = 'data' in quer
    candidatas = _datas(t) if datas else list(t['colunas'].values())
    pontos = []
    for c in candidatas:
        tem = set(descoberta.tokens(c['coluna'])) | set(descoberta.tokens(c.get('descricao') or ''))
        pontos.append((sum(1 for q in quer if _casa(q, tem)), c))
    pontos.sort(key=lambda x: -x[0])
    if pontos and pontos[0][0] >= min(2, len(quer)) and (len(pontos) == 1 or pontos[1][0] < pontos[0][0]):
        return pontos[0][1]
    return candidatas[0] if datas and len(candidatas) == 1 else None


def _unificar_colunas(cadeias):
    """A mesma coluna da origem com dois nomes em dois padrões (VALORLIQUIDO é "Receita" no ticket médio e
    "Receita Líquida" na margem): fica o primeiro nome, e as medidas da segunda cadeia passam a citá-lo."""
    nome_de = {}
    for cd in cadeias:
        for papel, (f, o, _) in cd['tabelas'].items():
            novas = []
            for orig, n in cd['colunas'].get(papel, []):
                primeiro = nome_de.setdefault((f, o, chave(orig)), (papel, n))
                if primeiro != (papel, n):
                    for m in cd['medidas']:
                        for k in ('coluna', 'entradas', 'saidas', 'fim'):
                            if m.get(k) == f'{papel}[{n}]':
                                m[k] = f'{primeiro[0]}[{primeiro[1]}]'
                        if isinstance(m.get('dax'), str):
                            m['dax'] = m['dax'].replace(f'{papel}[{n}]', f'{primeiro[0]}[{primeiro[1]}]')
                    n = primeiro[1]
                novas.append((orig, n))
            cd['colunas'][papel] = novas


def _sem_colisao(argila):
    """Coluna e medida com o mesmo nome na mesma tabela (a cadeia do padrão chama a coluna e a soma de "Custo"):
    a coluna vira "Valor de Custo" e as medidas passam a citar o nome novo."""
    nomes = {chave(m['nome']) for m in argila['medidas']}
    for t in argila['tabelas']:
        for c in t['colunas']:
            if isinstance(c, dict) and chave(c.get('nome') or '') in nomes:
                velho, c['nome'] = c['nome'], f'Valor de {c["nome"]}'
                for m in argila['medidas']:
                    for k in ('coluna', 'entradas', 'saidas', 'fim', 'categoria', 'por'):
                        if m.get(k) == f'{t["nome"]}[{velho}]':
                            m[k] = f'{t["nome"]}[{c["nome"]}]'
                    if isinstance(m.get('dax'), str):
                        m['dax'] = m['dax'].replace(f'{t["nome"]}[{velho}]', f'{t["nome"]}[{c["nome"]}]')
                for pg in argila['paginas']:
                    for v in pg['visuais']:
                        for k, x in list(v.items()):
                            if x == f'{t["nome"]}[{velho}]':
                                v[k] = f'{t["nome"]}[{c["nome"]}]'


def _renomear(medidas, de, para):
    """Troca a referência a [de] por [para] nas medidas (numerador, denominador, base, DAX)."""
    for m in medidas:
        for k in ('numerador', 'denominador', 'base', 'meta'):
            if m.get(k) == de:
                m[k] = para
        if isinstance(m.get('dax'), str):
            m['dax'] = m['dax'].replace(f'[{de}]', f'[{para}]')


def _meta_ponderada(meta, alvo, rels, tabs, notas):
    """Meta de taxa vinda de planilha por área (uma linha por empresa): no total, a média simples pesa igual a área
    pequena e a grande. O esboço já sai com a média pesada pelo denominador da taxa, item a item da área."""
    if meta.get('agregacao') != 'media' or alvo.get('tipo') != 'divisao' or not alvo.get('denominador'):
        return
    tm = meta['coluna'].split('[')[0]
    r = next((r for r in rels if r['de'] == tm), None)
    dim = next((t for t in tabs if r and t['nome'] == r['para']), None)
    if not dim or not dim['colunas']:
        return
    orig = ((r.get('declarada') or {}).get('campos') or [[None, None]])[0][1]
    col = next((c['nome'] for c in dim['colunas'] if chave(c['coluna']) == chave(orig or '')), dim['colunas'][0]['nome'])
    meta.pop('agregacao')
    meta.update({'tipo': 'media_ponderada', 'peso': alvo['denominador'], 'por': f'{dim["nome"]}[{col}]'})
    meta['descricao'] = (f'Meta de {alvo["nome"]} da fonte ({meta["coluna"]}); com várias linhas de {dim["nome"]} no '
                         f'filtro, a média das metas pesada por {alvo["denominador"]}.')
    notas.append(f'meta "{meta["nome"]}" pesada por {alvo["denominador"]} em cada {dim["nome"]} (a média simples '
                 'daria à área pequena o peso da grande)')


def cadeias_do_pedido(catalogos, pedido, dentro=None):
    """Os padrões com a cadeia inteira (dicionario/padroes.json) que o pedido cita, com cada papel já achado nos
    catálogos: [{'padrao', 'tabelas': {papel: (fonte, origem, tipo)}, 'colunas': {papel: [(coluna, nome)]},
    'medidas'}] e as notas do que não deu para achar. `dentro`: só estas (fonte, origem) (escolha à mão)."""
    from tecnicas.sasori import padroes
    # o padrão entra pela palavra que a pessoa escreveu; o sinônimo só vale se nenhuma palavra bater ("meta" é
    # sinônimo de "orçamento" na busca de tabelas, mas um pedido de turnover com meta não é orçado x realizado)
    com_cadeia = [p for p in padroes()['padroes'] if p.get('cadeia')]
    proprias = set(descoberta.tokens(pedido))
    termos = proprias if any(proprias & {x for t in p['termos'] for x in descoberta.tokens(t)} for p in com_cadeia) \
        else descoberta.termos_do_pedido(pedido)
    achadas, notas = [], []
    for p in com_cadeia:
        if not termos & {x for t in p['termos'] for x in descoberta.tokens(t)}:
            continue
        tabelas, colunas, falta = {}, {}, []
        usadas = set()
        for papel, cols in _papeis_do_padrao(p).items():
            tipo = 'fato' if papel.startswith('f') else 'dimensao'
            achado = None
            for r in descoberta.buscar(catalogos, ' '.join(descoberta.tokens(papel)), 6):
                k = (r['fonte'], r['tabela'])
                t = catalogos[r['fonte']].tabela(r['tabela'])
                if k in usadas or (dentro is not None and k not in dentro) or (tipo == 'fato' and not _datas(t)):
                    continue
                pares = [(_coluna_do_papel(t, c), c) for c in cols]
                if all(c for c, _ in pares):
                    achado = k
                    colunas[papel] = [(c['coluna'], n) for c, n in pares]
                    break
            if not achado:
                falta.append(papel)
                continue
            usadas.add(achado)
            tabelas[papel] = (achado[0], achado[1], tipo)
        if falta:
            notas.append(f'padrão "{p["id"]}": não achei nos catálogos o papel de {", ".join(falta)} '
                         f'(veja `deidara.py padroes {p["id"]}` e escolha as tabelas com --tabelas)')
            continue
        achadas.append({'padrao': p['id'], 'tabelas': tabelas, 'colunas': colunas,
                        'medidas': [dict(md) for md in p['cadeia']]})
    return achadas, notas


def _aplicar_briefing(argila, briefing, notas):
    """As respostas do gestor (painel.json, "briefing") entram no esboço: definição, polaridade e meta de cada
    indicador, para que serve o painel e para quem."""
    if (briefing.get('decisao') or '').strip():
        argila['descricao'] = briefing['decisao'].strip()
    if (briefing.get('publico') or '').strip():
        argila['publico'] = briefing['publico'].strip()
    por_nome = {chave(md['nome']): md for md in argila['medidas']}
    for ind in briefing.get('indicadores') or []:
        nome = (ind.get('nome') or '').strip()
        if not nome:
            continue
        md = por_nome.get(chave(nome))
        if not md:                                        # "turnover" no briefing, "Turnover" na cadeia; ou só parecido
            quer = set(descoberta.tokens(nome))
            md = next((x for x in argila['medidas'] if quer and quer <= set(descoberta.tokens(x['nome']))), None)
        if not md and quer:                               # "Receita" no briefing = a soma de VALORLIQUIDO no esboço
            soma = [x for x in argila['medidas'] if x.get('agregacao') == 'soma' and x.get('coluna')
                    and not x['nome'].lower().startswith('meta')
                    and all(_casa(q, set(descoberta.tokens(x['coluna'].split('[', 1)[-1]))) for q in quer)]
            if len(soma) == 1:
                md = soma[0]
                notas.append(f'"{md["nome"]}" virou "{nome}", como o gestor chama (confirme que é a mesma conta)')
                _renomear(argila['medidas'], md['nome'], nome)
                for pg in argila['paginas']:
                    for v in pg['visuais']:
                        for k, val in list(v.items()):
                            if val == md['nome']:
                                v[k] = nome
                            elif isinstance(val, list):
                                v[k] = [nome if y == md['nome'] else y for y in val]
                md['nome'] = nome
                por_nome[chave(nome)] = md
        if not md:
            notas.append(f'indicador "{nome}" do briefing ainda sem medida no esboço: `deidara.py padroes {nome}` e '
                         'acrescente em "medidas"')
            continue
        if (ind.get('definicao') or '').strip():
            md['descricao'] = ind['definicao'].strip()
        if ind.get('polaridade') in ('maior_melhor', 'menor_melhor'):
            md['polaridade'] = ind['polaridade']
        meta = ind.get('meta')
        if isinstance(meta, (int, float)) and not isinstance(meta, bool):
            if isinstance(md.get('meta'), str):
                notas.append(f'meta de "{md["nome"]}": o briefing diz {meta}; a da fonte ("{md["meta"]}") ficou de '
                             'lado (troque em "meta" se a da fonte é a oficial)')
            md['meta'] = meta
        elif isinstance(meta, str) and meta.strip():
            alvo = por_nome.get(chave(meta)) or next(
                (x for x in argila['medidas'] if x['nome'].lower().startswith('meta')
                 and set(descoberta.tokens(nome)) <= set(descoberta.tokens(x['nome']))), None)
            metas = [x for x in argila['medidas'] if x['nome'].lower().startswith('meta') and x is not md]
            if not alvo and len(metas) == 1 and not any(x.get('meta') == metas[0]['nome'] for x in argila['medidas']):
                alvo = metas[0]                           # uma meta só na fonte: é a deste indicador
                novo = f'Meta de {md["nome"]}'
                if chave(novo) not in {chave(x['nome']) for x in argila['medidas']}:
                    _renomear(argila['medidas'], alvo['nome'], novo)
                    alvo['nome'] = novo
                    if alvo.get('descricao', '').startswith(PENDENTE_DEF):
                        alvo['descricao'] = f'Meta de {md["nome"]} da planilha de metas, somada nos meses do filtro.'
                notas.append(f'"{md["nome"]}" ligado à "{alvo["nome"]}" (a única meta da fonte; confirme com o dono)')
            if alvo:
                md['meta'] = alvo['nome']
                if alvo.get('formato') in (None, 'decimal') and md.get('formato'):
                    alvo['formato'] = md['formato']
            else:
                notas.append(f'meta de "{nome}" ("{meta}") não achada nos catálogos: catalogue a fonte da meta')


def _do_cartao(argila, do_cartao, notas):
    """Indicador que o time já aprovou (Memory Card, oficial ou em uso) entra com a mesma definição e fórmula: dois
    painéis não calculam o mesmo indicador de jeitos diferentes sem ninguém perceber."""
    for i, md in enumerate(argila['medidas']):
        achado = (do_cartao or {}).get(chave(md['nome']))
        if not achado:
            continue
        ref, ficha = achado
        if ficha.get('status') not in ('oficial', 'em-uso') or not ficha.get('especificacao'):
            continue
        novo = dict(ficha['especificacao'], nome=md['nome'])
        if (md.get('descricao') or '').strip() and not md['descricao'].startswith(PENDENTE_DEF)                 and md['descricao'].strip() != (novo.get('descricao') or '').strip():
            notas.append(f'"{md["nome"]}": o briefing trazia outra definição; vale a do Memory Card ({ficha["status"]}). '
                         'Se o gestor quer outra conta, é outro indicador: dê outro nome')
        argila['medidas'][i] = novo
        notas.append(f'"{md["nome"]}" veio do Memory Card ({ficha["status"]}, {ref}, v{ficha.get("versao", 1)}): a mesma '
                     'definição e fórmula dos outros painéis do time')


def pedido_do_briefing(briefing):
    """O pedido em português montado do briefing (indicadores e cortes), quando não vem --pedido."""
    inds = [i.get('nome') for i in briefing.get('indicadores') or [] if (i.get('nome') or '').strip()]
    cortes = [c for c in briefing.get('cortes') or [] if str(c).strip()]
    if not inds:
        return ''
    return ' e '.join(inds) + (' por ' + ' e '.join(cortes) if cortes else '') + \
        (' contra a meta' if any(i.get('meta') for i in briefing.get('indicadores') or []) else '')


def _sem_distorcao(argila, catalogos, notas):
    """O esboço não sai com corte que distorce o número: segmentador que filtra só parte de uma medida da página
    sai; gráfico ou tabela troca a medida por uma da página que o corte filtra inteira, ou sai. A meta pode não
    mudar com o corte (vira um aviso só no validar). Ligação a confirmar conta como ligada."""
    import copy
    from kibaku_nendo.especificacao import alcance, grafo_de_filtro, medida, resolver
    try:
        m, _ = resolver(copy.deepcopy(argila), catalogos)
    except Exception:                                   # esboço que nem resolve: o validar mostra por quê
        return
    filtra = grafo_de_filtro(m, [(r['de'], r['para']) for r in argila['relacionamentos'] if 'declarada' in r])
    metas = {x['meta_medida'] for x in m['medidas'] if x.get('meta_medida')}

    def inteira(ref, nome):
        if nome in metas or not medida(m, nome) or '[' not in ref:
            return True
        return alcance(m, filtra, ref.split('[')[0], nome) == 'total'

    def medidas_de(v):
        return ([v['medida']] if v.get('medida') else []) + list(v.get('valores') or []) + \
               [x for x in v.get('campos') or [] if '[' not in x]

    for pg in argila['paginas']:
        da_pagina = [n for v in pg['visuais'] for n in medidas_de(v)]
        ficam = []
        for v in pg['visuais']:
            if v['tipo'] == 'segmentador':
                ruins = sorted({n for n in da_pagina if not inteira(v['campo'], n)})
                if ruins:
                    notas.append(f'segmentador {v["campo"]} fora do esboço: ele filtra só parte de {", ".join(ruins)} '
                                 '(o número ficaria distorcido)')
                    continue
            elif v['tipo'] in ('barras', 'colunas'):
                bons = [n for n in v['valores'] if inteira(v['categoria'], n)]
                if not bons:
                    troca = next((n for n in da_pagina if n not in metas and inteira(v['categoria'], n)), None)
                    if not troca:
                        notas.append(f'gráfico por {v["categoria"]} fora do esboço: nenhuma medida da página é filtrada '
                                     'inteira por esse corte')
                        continue
                    notas.append(f'gráfico por {v["categoria"]} mostra "{troca}" em vez de "{v["valores"][0]}" '
                                 f'({v["categoria"]} filtra só parte de "{v["valores"][0]}")')
                    bons = [troca]
                v['valores'] = bons
            elif v['tipo'] == 'tabela':
                cols = [x for x in v['campos'] if '[' in x]
                fora = [x for x in v['campos'] if '[' not in x and not all(inteira(c, x) for c in cols)]
                v['campos'] = [x for x in v['campos'] if x not in fora]
                if len(v['campos']) == len(cols):
                    continue
                if fora:
                    notas.append(f'tabela por {", ".join(cols)} sem {", ".join(fora)} (o corte filtra só parte delas)')
            ficam.append(v)
        pg['visuais'] = ficam


def _pela_chave(catalogos, achados, do_padrao, pedido):
    """Numa fonte com chaves estrangeiras, a tabela que só bate pelas COLUNAS e não se liga a nenhuma outra achada
    (nem às do padrão) sai, se houver outra que se ligue: num ERP de milhares de tabelas, uma tabela solta com colunas CARGO1..CARGO9
    não é a dimensão de cargo. E a mãe de uma tabela do padrão com uma palavra do pedido no nome (F_CARGO, mãe do
    cadastro, para "por cargo") entra mesmo fora da busca. Fonte sem FK (planilha) fica como está."""
    palavras = set(descoberta.tokens(pedido)) - descoberta.VAZIAS
    vistas = {(r['fonte'], r['tabela']) for r in achados}
    vizinhas = []
    for nome, fonte in catalogos.items():
        for fk in fonte.fks:
            mae = (nome, fk['tabela_mae'])
            if (nome, fk['tabela_filha']) in do_padrao and mae not in vistas and mae not in do_padrao:
                t = fonte.tabela(fk['tabela_mae']) or {'nome': '', 'descricao': ''}
                bate = palavras & (set(descoberta.tokens(t['nome'])) | set(descoberta.tokens(t.get('descricao') or '')))
                if bate:
                    vistas.add(mae)
                    vizinhas.append({'fonte': nome, 'tabela': t['nome'], 'pontos': 0, 'colunas': [],
                                     'descricao': t.get('descricao') or '', 'termos': sorted(bate)})
    achadas = {(r['fonte'], r['tabela']) for r in achados} | set(do_padrao)
    ligadas = set()
    for nome, fonte in catalogos.items():
        for fk in fonte.fks:
            a, b = (nome, fk['tabela_filha']), (nome, fk['tabela_mae'])
            if a in achadas and b in achadas:
                ligadas |= {a, b}

    def ilha(r):
        fonte = catalogos[r['fonte']]
        if not fonte.fks or (r['fonte'], r['tabela']) in ligadas | set(do_padrao):
            return False
        t = fonte.tabela(r['tabela'])
        no_nome = set(descoberta.tokens(t['nome'])) | set(descoberta.tokens(t.get('descricao') or ''))
        return not (no_nome & set(r['termos']))
    boas = [r for r in achados if not ilha(r)] + vizinhas
    return boas or achados


def esbocar(catalogos, pedido, projeto=None, tabelas=None, limite=6, briefing=None, do_cartao=None):
    """Devolve (argila, notas). `tabelas`: [(fonte, origem)] para escolher à mão; senão, a busca escolhe.
    `briefing`: as respostas do gestor (painel.json); sem pedido, o pedido sai dele. `do_cartao`: os indicadores do
    Memory Card ({chave do nome: (ref, ficha)}), que entram no lugar dos que o esboço escreveria."""
    notas = []
    briefing = briefing or {}
    pedido = pedido or pedido_do_briefing(briefing)
    if not pedido:
        raise ValueError('diga o que o painel mostra: --pedido "..." ou os indicadores no briefing (painel.json)')
    if tabelas:
        escolhidas = [(f, catalogos[f].tabela(o)['nome']) for f, o in tabelas if catalogos[f].tabela(o)]
    else:
        cadeias, notas_cadeia = cadeias_do_pedido(catalogos, pedido)
        do_padrao = {(f, o) for cd in cadeias for f, o, _ in cd['tabelas'].values()}
        achados = _pela_chave(catalogos, descoberta.buscar(catalogos, pedido, limite * 5), do_padrao, pedido)[:limite]
        literais = set(descoberta.tokens(pedido))
        # só as tabelas que batem com uma palavra DITA no pedido (não só por sinônimo) ou que o padrão pede
        diretas = [r for r in achados if literais & set(r['termos']) or (r['fonte'], r['tabela']) in do_padrao]
        fora = [r['tabela'] for r in achados if r not in diretas]
        achados = diretas or achados
        if fora and diretas:
            notas.append('ficaram de fora (só batiam por sinônimo): ' + ', '.join(fora) + ' — inclua com --tabelas')
        escolhidas = [(r['fonte'], r['tabela']) for r in achados]
        escolhidas += [k for k in sorted(do_padrao) if k not in escolhidas]
        notas.append('tabelas escolhidas pela busca' + (' e pelo padrão' if do_padrao else '') + ': '
                     + ', '.join(t for _, t in escolhidas) + ' (confirme com o usuário; troque com --tabelas)')
    if not escolhidas:
        raise ValueError('nenhuma tabela encontrada para o pedido: use palavras do negócio ou --tabelas')
    if tabelas:
        cadeias, notas_cadeia = cadeias_do_pedido(catalogos, pedido, set(escolhidas))
    notas += notas_cadeia
    _unificar_colunas(cadeias)
    papel_de = {(f, o): (papel, tipo) for cd in cadeias for papel, (f, o, tipo) in cd['tabelas'].items()}
    cols_do_papel = {}
    for cd in cadeias:
        for papel, (f, o, _) in cd['tabelas'].items():
            cols_do_papel.setdefault((f, o), []).extend(cd['colunas'].get(papel, []))
        notas.append(f'padrão "{cd["padrao"]}": a cadeia inteira entrou ({", ".join(md["nome"] for md in cd["medidas"])}), '
                     'com ' + ', '.join(f'{o} como {p}' for p, (_, o, _) in cd['tabelas'].items())
                     + ' (confira a fórmula com o dono do indicador)')
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
    for k, (_, tipo) in papel_de.items():               # o padrão sabe o que é evento e o que é cadastro
        tipos[k] = tipo
    if 'fato' not in tipos.values():
        candidata = max(escolhidas, key=lambda x: len(_datas(catalogos[x[0]].tabela(x[1]))))
        tipos[candidata] = 'fato'
    nomes = {k: papel_de[k][0] if k in papel_de else nome_no_modelo(k[1], tipos[k]) for k in escolhidas}

    tabs, rotulos = [], {}
    for (f, o) in escolhidas:
        t = catalogos[f].tabela(o)
        cols, usados = [], set()

        def add(c, nome=None):
            if c and c['coluna'] not in usados:
                usados.add(c['coluna'])
                nome = nome or nome_amigavel(c)
                if chave(nome) in {chave(x.get('nome', '')) for x in cols}:
                    nome = c['coluna']
                cols.append({'coluna': c['coluna'], 'nome': nome})
                return nome

        for coluna, nome in cols_do_papel.get((f, o), []):   # as colunas que a cadeia do padrão usa, com o nome dela
            add(t['colunas'].get(chave(coluna)), nome)
        if tipos[(f, o)] == 'dimensao':
            for p in t['pk']:
                add(t['colunas'].get(chave(p)))
            rotulo = _rotulo(t)
            if rotulo:
                rotulos[nomes[(f, o)]] = add(rotulo) or next(
                    (x['nome'] for x in cols if x['coluna'] == rotulo['coluna']), None)
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

    # medidas: a cadeia dos padrões citados primeiro; depois contagem de cada fato e soma de cada valor
    medidas, iguais = [], {}
    for md in (md for cd in cadeias for md in cd['medidas']):
        chave_conta = (md.get('agregacao'), md.get('coluna') or md.get('tabela')) if md.get('agregacao') else None
        if chave_conta and chave_conta in iguais:       # "Receita Líquida" da margem = "Receita" do ticket médio
            _renomear(medidas + [md for cd in cadeias for md in cd['medidas']], md['nome'], iguais[chave_conta])
            continue
        if chave_conta:
            iguais[chave_conta] = md['nome']
        medidas.append(md)
    fatos_do_padrao = {nomes[k] for k, (_, tipo) in papel_de.items() if tipo == 'fato'}
    for tb in tabs:
        if tb['tipo'] != 'fato' or tb['nome'] in fatos_do_padrao:
            continue
        rotulo = re.sub(r'^f', '', tb['nome'])
        t = catalogos[tb['fonte']].tabela(tb['origem'])
        de_metas = bool(set(descoberta.tokens(tb['origem'])) & {'meta', 'orcamento', 'budget', 'plano', 'objetivo'})
        if _datas(t) and not de_metas:                  # contagem só faz sentido em fato de evento (com data)
            medidas.append({'nome': f'Qtd {rotulo}', 'agregacao': 'contagem_linhas', 'tabela': tb['nome'],
                            'descricao': f'{PENDENTE_DEF}: o que cada linha de {tb["origem"]} representa e o que conta',
                            'pasta': rotulo})
        for c in tb['colunas']:
            if t['colunas'][chave(c['coluna'])].get('familia') in ('decimal', 'real'):
                toks = set(descoberta.tokens(c['coluna'])) | set(descoberta.tokens(c['nome']))
                taxa = toks & {'percentual', 'pct', 'taxa', 'indice', 'perc', 'media', 'aliquota', 'turnover', 'margem'}
                eh_meta = 'meta' in toks or de_metas
                sem_meta = re.sub(r'^meta[\s_]*', '', c['nome'], flags=re.I).replace('_', ' ').strip()   # Python 3.8
                if sem_meta.lower() in ('valor', 'vl', 'total', ''):
                    sem_meta = ''
                rot_meta = re.sub(r'^metas?_?', '', rotulo, flags=re.I) or rotulo
                nome_md = (f'Meta de {sem_meta or rot_meta}' if eh_meta
                           else f'{"Média" if taxa else "Total"} {c["nome"]}')
                # meta de taxa (turnover) faz média das linhas; meta de valor (receita do mês) soma no período
                medidas.append({'nome': nome_md,
                                'agregacao': 'media' if taxa else 'soma', 'coluna': f'{tb["nome"]}[{c["nome"]}]',
                                'formato': 'percentual' if taxa - {'media', 'indice'} else (
                                    'moeda' if eh_meta and toks & {'valor', 'receita', 'venda', 'faturamento'} else 'decimal'),
                                'descricao': f'{PENDENTE_DEF}: o que este número significa para o negócio',
                                'pasta': rotulo})

    vistos = set()
    medidas = [md for md in medidas if not (chave(md['nome']) in vistos or vistos.add(chave(md['nome'])))]
    # a meta que veio da fonte liga no indicador do padrão com o mesmo nome ("Meta de turnover" -> Turnover)
    for cd in cadeias:
        alvo = cd['medidas'][-1]
        quer = set(descoberta.tokens(alvo['nome']))
        meta = next((md for md in medidas if md['nome'].lower().startswith('meta')
                     and quer <= set(descoberta.tokens(md['nome']))), None)
        for md in cd['medidas']:
            md.setdefault('pasta', alvo['nome'])
        if meta and 'meta' not in alvo:
            alvo['meta'] = meta['nome']
            meta['formato'] = alvo.get('formato', meta.get('formato'))
            if meta['descricao'].startswith(PENDENTE_DEF):
                meta['descricao'] = (f'Meta de {alvo["nome"]} da fonte, coluna {meta["coluna"]} '
                                     f'({"média" if meta["agregacao"] == "media" else "soma"} das linhas no filtro).')
            _meta_ponderada(meta, alvo, rels, tabs, notas)
            notas.append(f'"{alvo["nome"]}" ligado à meta "{meta["nome"]}" (a meta precisa chegar pelos mesmos cortes)')

    # página de visão geral: o fato principal (o do padrão, ou o primeiro com data) e só os cortes que chegam nele
    fato = next((d['tabela'] for d in datas if d['tabela'] in fatos_do_padrao),
                next((d['tabela'] for d in datas), next((tb['nome'] for tb in tabs if tb['tipo'] == 'fato'), None)))
    chega = {fato}
    mudou = True
    while mudou:
        mudou = False
        for r in rels:
            if r['de'] in chega and r['para'] not in chega and 'declarada' not in r:
                chega.add(r['para'])
                mudou = True
    if cadeias:                                        # o indicador do padrão na frente, e a cadeia dele em seguida
        principais = [cd['medidas'][-1] for cd in cadeias] + [md for cd in cadeias for md in cd['medidas'][:-1]]
    else:
        principais = [md for md in medidas if md['tabela' if 'tabela' in md else 'coluna'].split('[')[0] == fato]
    vis = []
    if datas and any(d['tabela'] == fato for d in datas):
        vis.append({'tipo': 'segmentador', 'campo': 'dCalendario[Ano]'})
    literais = descoberta.termos_do_pedido(pedido)
    dims = [tb for tb in tabs if tb['tipo'] == 'dimensao' and tb['nome'] in rotulos and tb['nome'] in chega]
    citadas = [d for d in dims if literais & set(descoberta.tokens(d['origem']) + descoberta.tokens(d['nome']))]
    papeis = {p for p, _ in papel_de.values()}
    citadas = [d for d in citadas if d['nome'] not in papeis] or citadas    # o cadastro de pessoas não é corte
    cortes = citadas or [d for d in dims if d['nome'] not in papeis][:2] or dims[:2]

    def campo(d):
        return f'{d["nome"]}[{rotulos[d["nome"]]}]'

    for d in cortes[:2]:
        vis.append({'tipo': 'segmentador', 'campo': campo(d)})
    for md in principais[:4]:
        vis.append({'tipo': 'cartao', 'medida': md['nome']})
    medidas_pagina = principais
    if medidas_pagina:
        principal = medidas_pagina[0]['nome']
        if datas:
            vis.append({'tipo': 'colunas', 'categoria': 'dCalendario[Mês/Ano]', 'valores': [principal]})
        for d in (cortes or dims[:1])[:3]:                     # um visual por corte citado no pedido
            vis.append({'tipo': 'barras', 'categoria': campo(d), 'valores': [principal]})
        if cortes:
            vis.append({'tipo': 'tabela', 'campos': [campo(cortes[0])] + [m['nome'] for m in medidas_pagina[:3]]})
    ligadas = {md.get('meta') for md in medidas}
    outras = [md for md in medidas if md not in principais and md['nome'] not in ligadas]
    if outras:
        notas.append('medidas de outras tabelas fato (' + ', '.join(m['nome'] for m in outras)
                     + ') ficaram fora da página: ponha numa página própria ou ligue os cortes a elas')

    argila = {'projeto': projeto or pedido[:60].strip().capitalize(), 'versao': '0.1', 'modelo': 'faixa-de-kpis',
              'descricao': f'{PENDENTE_DEF}: para que serve o painel e que decisão ele apoia',
              'publico': PENDENTE_DEF, 'fontes': {}, 'tabelas': tabs, 'relacionamentos': rels,
              'medidas': medidas, 'paginas': [{'nome': 'Visão Geral', 'visuais': vis}]}
    if datas:                                        # sem "fim": o calendário acompanha o ano corrente
        argila['calendario'] = {'inicio': datetime.date.today().year - 5, 'datas': datas}
        notas.append(f'o calendário começa em {argila["calendario"]["inicio"]}: confirme com o dono do dado o ano do '
                     'registro mais antigo que o painel precisa (o 03_qualidade.sql conta as datas fora dele)')
    _aplicar_briefing(argila, briefing, notas)
    _sem_colisao(argila)
    _do_cartao(argila, do_cartao, notas)
    _sem_distorcao(argila, catalogos, notas)
    from tecnicas import c2                          # o dragão escolhe os visuais pela pergunta do painel
    c2.soltar(argila, c2.intencoes(pedido, briefing.get('decisao')), notas)
    _sem_distorcao(argila, catalogos, notas)
    pendentes =[md['nome'] for md in medidas if (md.get('descricao') or '').startswith(PENDENTE_DEF)]
    if pendentes or argila['publico'] == PENDENTE_DEF or argila['descricao'].startswith(PENDENTE_DEF):
        notas.append('defina ' + (f'{", ".join(pendentes)} ' if pendentes else 'o painel ')
                     + f'(descrição, polaridade, meta) antes de mostrar ao gestor: os "{PENDENTE_DEF}" viram aviso no '
                     'validar; o jeito mais rápido é o briefing no painel.json')
    return argila, notas
