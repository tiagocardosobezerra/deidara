"""
Descoberta: achar as tabelas de um pedido e sugerir as ligações que faltam.

Tudo a partir dos catálogos (só estrutura). Nada aqui liga tabela sozinho:
`buscar` ranqueia, `relacionar` sugere com a evidência de cada ponto, e quem
confirma é uma pessoa (a sugestão vira "declarada" com "por"). A receita de
prova (receitas.receita_prova) mede a candidata na fonte, com números
agregados (percentuais e sim/não), nunca linhas.

Evidências de uma ligação filha[a] -> mãe[b]:
- núcleo do nome igual ("CODEMPRESA" ≈ "Cód. Empresa" ≈ "cod_empresa" -> empresa);
- a coluna "aponta" para a tabela mãe (empresa ⊂ N_EMPRESA);
- a ponta mãe é a PK da tabela (só o catálogo SQL sabe; nos outros, desconhecido);
- tipos compatíveis (texto contra inteiro pesa contra: parece nome, não código);
- descrições parecidas;
- sinônimos do time (dicionario/sinonimos.json).
"""

import json
import math
import os
import re
from collections import Counter, defaultdict
from functools import lru_cache

from kibaku_nendo.util import sem_acento
from tecnicas.luneta import treino

PASTA_DICIONARIO = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'dicionario')

# prefixos que marcam código/chave e que vêm colados no nome (CODEMPRESA, IDCLIENTE, NRPEDIDO);
# saem do núcleo do nome. Chaves naturais (MATRICULA, CPF) ficam no núcleo, mas também contam como chave.
MARCAS_CHAVE = ('codigo', 'cod', 'cd', 'id', 'chave', 'num', 'nr', 'numero', 'sk')
CHAVES_NATURAIS = ('matricula', 'chapa', 'cpf', 'cnpj', 'sku', 'placa')
PREFIXOS_COLADOS = ('codigo', 'cod', 'cd', 'id', 'num', 'nr', 'dt', 'data', 'vl', 'valor', 'qtd', 'desc',
                    'descricao', 'nome', 'nm', 'tipo', 'sigla')
GENERICAS = {'nome', 'nm', 'descricao', 'desc', 'observacao', 'obs', 'valor', 'vl', 'data', 'dt', 'qtd', 'quantidade',
             'status', 'situacao', 'tipo', 'sigla', 'fk', 'pk', 'ativo', 'flag'}
VAZIAS = {'de', 'da', 'do', 'das', 'dos', 'e', 'a', 'o', 'as', 'os', 'por', 'com', 'em', 'para', 'no', 'na', 'nos',
          'nas', 'um', 'uma', 'ao', 'que', 'quero', 'painel', 'indicador', 'indicadores', 'mostrar', 'ver', 'f', 'd',
          'n', 't', 's'}


@lru_cache(maxsize=1)
def _sinonimos():
    arq = os.path.join(PASTA_DICIONARIO, 'sinonimos.json')
    if not os.path.exists(arq):
        return {}
    with open(arq, encoding='utf-8') as f:
        grupos = json.load(f).get('grupos', [])
    out = {}
    for g in grupos:
        normal = [_raiz(sem_acento(x).lower()) for x in g]
        for x in normal:
            out.setdefault(x, set()).update(normal)
    return out


def _raiz(p):
    """Plural simples -> singular (colaboradores -> colaborador, motivos -> motivo)."""
    if len(p) > 4 and p.endswith('oes'):
        return p[:-3] + 'ao'
    if len(p) > 4 and p.endswith('es') and p[-3] in 'rsz':
        return p[:-2]
    if len(p) > 3 and p.endswith('s') and not p.endswith('ss'):
        return p[:-1]
    return p


def tokens(texto):
    """'CODEMPRESA' -> ['cod', 'empresa']; 'Cód. Empresa' -> ['cod', 'empresa']; 'dCargo' -> ['cargo']."""
    return list(_tokens(texto or ''))


@lru_cache(maxsize=200000)
def _tokens(texto):
    texto = re.sub(r'([a-z])([A-Z])', r'\1 \2', texto or '')
    out = []
    for p in re.split(r'[^a-z0-9]+', sem_acento(texto).lower()):
        if not p:
            continue
        for pre in sorted(PREFIXOS_COLADOS, key=len, reverse=True):     # descricao antes de desc
            if p.startswith(pre) and len(p) - len(pre) >= 3 and p != pre:
                out += [pre, _raiz(p[len(pre):])]
                break
        else:
            out.append(_raiz(p))
    return tuple(t for t in out if t not in VAZIAS)


@lru_cache(maxsize=200000)
def nucleo(nome_coluna):
    """O que a coluna identifica, sem as marcas de chave: 'CODEMPRESA_FK' -> {'empresa'}."""
    return frozenset(t for t in tokens(nome_coluna) if t not in MARCAS_CHAVE and t not in GENERICAS)


def tem_marca_de_chave(nome_coluna):
    return any(t in MARCAS_CHAVE or t in CHAVES_NATURAIS for t in tokens(nome_coluna))


def _expandir(conj, sin):
    return _expandir_cache(frozenset(conj)) if sin is _sinonimos() else _expandir_sem_cache(conj, sin)


@lru_cache(maxsize=200000)
def _expandir_cache(conj):
    return frozenset(_expandir_sem_cache(conj, _sinonimos()))


def termos_do_pedido(pedido):
    """As palavras do pedido mais os sinônimos do time (e os aprendidos): o que a busca procura."""
    return _expandir(frozenset(tokens(pedido)), _sinonimos())


def _expandir_sem_cache(conj, sin):
    out = set(conj)
    for t in conj:
        out |= sin.get(t, set())
    return out


# ===================================================================== buscar
def buscar(catalogos, pedido, limite=10):
    """Ranqueia as tabelas de todos os catálogos para um pedido em português.
    Devolve [{'fonte','tabela','pontos','colunas':[...],'motivo'}]."""
    sin = _sinonimos()
    toks = tokens(pedido)
    literais = set(toks) | {a + b for a, b in zip(toks, toks[1:])}     # "razão social" acha RAZAOSOCIAL
    termos = set(_expandir(set(toks), sin)) | literais
    docs = []
    for fonte in catalogos.values():
        for t in fonte.tabelas.values():
            peso = Counter()
            for x in tokens(t['nome']):
                peso[x] += 3
            for x in tokens(t['descricao']):
                peso[x] += 2
            cols = {}
            for c in t['colunas'].values():
                cs = set(tokens(c['coluna'])) | set(tokens(c.get('descricao', '')))
                cols[c['coluna']] = cs
                for x in cs:
                    peso[x] += 1
            docs.append((fonte, t, peso, cols))
    n = max(1, len(docs))
    df = Counter(x for _, _, peso, _ in docs for x in peso)
    palavras = set(tokens(pedido)) - VAZIAS
    out = []
    for fonte, t, peso, cols in docs:
        pontos, achados = 0.0, []
        for x in termos:
            if x in peso:                          # a palavra dita vale mais que o sinônimo dela
                pontos += min(peso[x], 6) * math.log(1 + n / df[x]) * (1.0 if x in literais else 0.6)
                achados.append(x)
        extra = treino.bonus(palavras, t['nome'])     # a pessoa já escolheu esta tabela para estas palavras
        if extra:
            pontos += extra
            achados += sorted(p for p in palavras if treino.bonus([p], t['nome']))
        if not pontos:
            continue
        colunas = [c for c, cs in cols.items() if cs & termos]
        out.append({'fonte': fonte.nome, 'tabela': t['nome'], 'pontos': round(pontos, 2), 'colunas': colunas,
                    'descricao': t['descricao'], 'termos': sorted(set(achados))})
    out.sort(key=lambda x: (-x['pontos'], x['tabela']))
    return out[:limite]


# ================================================================= relacionar
def _pontuar(fa, ta, ca, fb, tb, cb, sin):
    """Pontos e motivos da ligação ta[ca] (filha) -> tb[cb] (mãe)."""
    na, nb = nucleo(ca['coluna']), nucleo(cb['coluna'])
    if not na or not nb:
        return 0, []
    fam_a, fam_b = ca.get('familia'), cb.get('familia')
    if fam_a in ('data', 'datahora', 'hora', 'logico', 'real') or fam_b in ('data', 'datahora', 'hora', 'logico', 'real'):
        return 0, []                     # chave de relação não é data, lógico nem número quebrado
    pontos, motivos = 0, []
    ea, eb = _expandir(na, sin), _expandir(nb, sin)
    if na == nb:
        pontos += 40
        motivos.append(f'mesmo nome ({", ".join(sorted(na))})')
    elif ea & eb:
        pontos += 25
        motivos.append(f'nomes equivalentes ({", ".join(sorted(ea & eb))})')
    else:
        return 0, []
    nome_mae = _expandir(set(tokens(tb['nome'])), sin)
    if na & nome_mae or ea & nome_mae:
        pontos += 20
        motivos.append(f'a coluna aponta para a tabela {tb["nome"]}')
    pk = [p.upper() for p in tb.get('pk') or []]
    if pk == [cb['coluna'].upper()]:
        pontos += 25
        motivos.append(f'{cb["coluna"]} é a chave primária de {tb["nome"]}')
    elif cb['coluna'].upper() in pk:
        pontos += 5
        motivos.append(f'{cb["coluna"]} é parte de uma chave composta de {tb["nome"]}: pode faltar campo')
    elif fb.tipo == 'sqlserver':
        pontos -= 20
        motivos.append(f'{cb["coluna"]} NÃO é a chave de {tb["nome"]}: o lado "um" pode repetir')
    else:
        motivos.append('não se sabe se o lado "um" é único (rode a receita de prova)')
    if [p.upper() for p in ta.get('pk') or []] == [ca['coluna'].upper()] and pk != [cb['coluna'].upper()]:
        pontos -= 15
        motivos.append(f'{ca["coluna"]} é a chave de {ta["nome"]}: talvez a direção seja a contrária')
    if fam_a == fam_b:
        pontos += 10
        motivos.append(f'mesmo tipo ({fam_a})')
    elif {fam_a, fam_b} == {'inteiro', 'texto'}:
        if not tem_marca_de_chave(ca['coluna']) and fam_a == 'texto':
            pontos -= 35
            motivos.append(f'{ca["coluna"]} é texto e parece nome, não código')
        else:
            pontos -= 10
            motivos.append('tipos diferentes (texto x inteiro): a ligação pede conversão')
    if tem_marca_de_chave(ca['coluna']) or tem_marca_de_chave(cb['coluna']):
        pontos += 5
    da, db = set(tokens(ca.get('descricao', ''))), set(tokens(cb.get('descricao', '')))
    if da and db and len(da & db) / len(da | db) >= 0.4:
        pontos += 5
        motivos.append('descrições parecidas')
    return pontos, motivos


def confianca(pontos):
    return 'alta' if pontos >= 70 else 'média' if pontos >= 45 else 'baixa' if pontos >= 30 else None


def relacionar(catalogos, tabelas, ja_ligadas=(), por_par=2):
    """Sugere ligações entre as tabelas pedidas.

    `tabelas`: [(fonte, origem, nome_no_modelo)]; `ja_ligadas`: pares
    {(nome_filha, nome_mae)} que não devem ser sugeridos. Devolve as
    sugestões ordenadas: {'de','para','campo_filho','campo_mae','pontos',
    'confianca','motivos','fonte_de','fonte_para','origem_de','origem_para','provada_no_catalogo'}."""
    sin = _sinonimos()
    ja = {(a.upper(), b.upper()) for a, b in ja_ligadas}
    # tabelas que já se alcançam por algum caminho de ligações existentes não precisam de outra
    grupo = {}
    for a, b in ja:
        ga, gb = grupo.get(a, {a}), grupo.get(b, {b})
        uniao = ga | gb
        for x in uniao:
            grupo[x] = uniao
    ja |= {(x, y) for g in grupo.values() for x in g for y in g if x != y}
    itens = []
    for fonte_nome, origem, nome in tabelas:
        f = catalogos[fonte_nome]
        t = f.tabela(origem)
        if t:
            itens.append((f, t, nome))
    indice = defaultdict(list)                 # termo (com sinônimos) -> [(item, coluna)]
    for k, (f, t, nome) in enumerate(itens):
        for c in t['colunas'].values():
            for termo in _expandir(nucleo(c['coluna']), sin):
                indice[termo].append((k, c))
    por_par_tab = defaultdict(list)
    for ka, (fa, ta, nome_a) in enumerate(itens):
        for ca in ta['colunas'].values():
            vistos = set()
            for termo in _expandir(nucleo(ca['coluna']), sin):
                for kb, cb in indice.get(termo, ()):
                    if kb == ka or (kb, cb['coluna']) in vistos:
                        continue
                    vistos.add((kb, cb['coluna']))
                    por_par_tab[(ka, kb)].append((ca, cb))
    out = []
    for (ka, kb), pares in por_par_tab.items():
        (fa, ta, nome_a), (fb, tb, nome_b) = itens[ka], itens[kb]
        if (nome_a.upper(), nome_b.upper()) in ja or (nome_b.upper(), nome_a.upper()) in ja:
            continue
        provada = fa is fb and bool(fa.fks_entre(ta['nome'], tb['nome']))
        cands = []
        for ca, cb in pares:
            pts, mot = _pontuar(fa, ta, ca, fb, tb, cb, sin)
            visto = treino.veredito(ta['nome'], ca['coluna'], tb['nome'], cb['coluna'])
            if visto == 'recusada':                    # o dono do dado já disse que não
                continue
            if visto == 'confirmada':
                pts += 30
                mot = mot + ['o dono do dado já confirmou esta ligação antes']
            if confianca(pts):
                cands.append({'de': nome_a, 'para': nome_b, 'campo_filho': ca['coluna'],
                              'campo_mae': cb['coluna'], 'pontos': pts, 'confianca': confianca(pts),
                              'motivos': mot, 'fonte_de': fa.nome, 'fonte_para': fb.nome,
                              'origem_de': ta['nome'], 'origem_para': tb['nome'],
                              'provada_no_catalogo': provada})
        cands.sort(key=lambda x: -x['pontos'])
        out += cands[:por_par]
    # por par de tabelas: a melhor e só as alternativas que chegam perto dela (as outras são ruído)
    melhor = {}
    for s in out:
        k = frozenset((s['de'], s['para']))
        melhor[k] = max(melhor.get(k, 0), s['pontos'])
    out = [s for s in out if s['pontos'] >= melhor[frozenset((s['de'], s['para']))] - 25]
    # par com ligação provada no catálogo: só ela (a direção contrária é ruído)
    provados = {frozenset((s['de'], s['para'])) for s in out if s['provada_no_catalogo']}
    out = [s for s in out if s['provada_no_catalogo'] or frozenset((s['de'], s['para'])) not in provados]
    out.sort(key=lambda x: (-x['pontos'], x['de'], x['para']))
    # aceitando as melhores em ordem, as que ligariam tabelas já ligadas ficam redundantes
    raiz = {}

    def acha(x):
        while raiz.get(x, x) != x:
            x = raiz[x]
        return x

    for a, b in ja:
        raiz[acha(a)] = acha(b)
    for s in out:
        a, b = acha(s['de'].upper()), acha(s['para'].upper())
        s['redundante'] = a == b
        if a != b:
            raiz[a] = b
    out.sort(key=lambda x: (x['redundante'], -x['pontos'], x['de'], x['para']))
    return out


def trecho_argila(s, por='<quem confirmou>'):
    """A sugestão no formato do argila.json (relação declarada, a confirmar)."""
    if s['provada_no_catalogo']:
        return {'de': s['de'], 'para': s['para']}
    return {'de': s['de'], 'para': s['para'],
            'declarada': {'campos': [[s['campo_filho'], s['campo_mae']]], 'por': por,
                          'motivo': '; '.join(s['motivos'])}}
