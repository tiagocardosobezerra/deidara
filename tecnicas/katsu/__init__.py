"""
================================================================================
 KATSU — a palavra que detona
================================================================================
Nome de referência: "Katsu!" é o que o Deidara diz para a argila explodir.
Nada explode antes dele. Aqui é o aceite: o "sim" do usuário que libera a
geração (C3), com o retrato do que foi aprovado e a diferença entre duas
versões.

O retrato é só o que importa para quem consome o painel (tabelas e colunas,
relacionamentos, definição e DAX de cada indicador, páginas e visuais, papéis
de segurança), em forma comparável. Ele vai no registro de aprovação; o
`deidara.py diff` compara o argila.json atual com ele, e o dicionário de
indicadores ganha o histórico de mudanças.
"""


def retrato(m):
    return {
        'versao': m.get('versao', ''),
        'tabelas': {t['nome']: {'origem': t['origem'], 'colunas': {c['nome']: c['origem'] or c['expressao_sql'] or ''
                                                                    for c in t['colunas'] if not c.get('auto')}}
                    for t in m['tabelas']},
        'relacionamentos': sorted(f'{r["de"]}[{r["de_coluna"]}] -> {r["para"]}[{r["para_coluna"]}]'
                                  + ('' if r['ativo'] else ' (inativa)') for r in m['relacionamentos']),
        'medidas': {x['nome']: {'dax': x['dax'], 'descricao': x['descricao'], 'formato': x['formato']}
                    for x in m['medidas'] if x['tipo'] != 'cor'},
        'paginas': {p['nome']: [f'{v["tipo"]}: {v["titulo"]}' for v in p['visuais']] for p in m['paginas']},
        'seguranca': {r['papel']: r['regras'] for r in m.get('seguranca', [])},
    }


def _dicts(rot, a, b, oque):
    out = []
    for k in sorted(set(a) - set(b)):
        out.append(f'{rot} removida: {k}' if oque == 'f' else f'{rot} removido: {k}')
    for k in sorted(set(b) - set(a)):
        out.append(f'{rot} nova: {k}' if oque == 'f' else f'{rot} novo: {k}')
    return out


def diferencas(antes, depois):
    """Lista de mudanças em linguagem simples (vazia = nada mudou para o consumidor)."""
    out = []
    if antes.get('versao') != depois.get('versao'):
        out.append(f'versão: {antes.get("versao") or "—"} → {depois.get("versao") or "—"}')
    ta, tb = antes.get('tabelas', {}), depois.get('tabelas', {})
    out += _dicts('tabela', ta, tb, 'f')
    for t in sorted(set(ta) & set(tb)):
        if ta[t]['origem'] != tb[t]['origem']:
            out.append(f'tabela {t}: origem {ta[t]["origem"]} → {tb[t]["origem"]}')
        out += [f'{x} em {t}' for x in _dicts('coluna', ta[t]['colunas'], tb[t]['colunas'], 'f')]
    ra, rb = set(antes.get('relacionamentos', [])), set(depois.get('relacionamentos', []))
    out += [f'relacionamento removido: {x}' for x in sorted(ra - rb)]
    out += [f'relacionamento novo: {x}' for x in sorted(rb - ra)]
    ma, mb = antes.get('medidas', {}), depois.get('medidas', {})
    out += _dicts('indicador', ma, mb, 'm')
    for k in sorted(set(ma) & set(mb)):
        if ma[k]['dax'] != mb[k]['dax']:
            out.append(f'indicador {k}: FÓRMULA mudou (o número muda)')
        if ma[k]['descricao'] != mb[k]['descricao']:
            out.append(f'indicador {k}: definição mudou')
        if ma[k]['formato'] != mb[k]['formato']:
            out.append(f'indicador {k}: formato {ma[k]["formato"]} → {mb[k]["formato"]}')
    pa, pb = antes.get('paginas', {}), depois.get('paginas', {})
    out += _dicts('página', pa, pb, 'f')
    for k in sorted(set(pa) & set(pb)):
        for v in pa[k]:
            if v not in pb[k]:
                out.append(f'página {k}: saiu "{v}"')
        for v in pb[k]:
            if v not in pa[k]:
                out.append(f'página {k}: entrou "{v}"')
    sa, sb = antes.get('seguranca', {}), depois.get('seguranca', {})
    out += _dicts('papel de segurança', sa, sb, 'm')
    for k in sorted(set(sa) & set(sb)):
        if sa[k] != sb[k]:
            out.append(f'papel de segurança {k}: regra mudou')
    return out
