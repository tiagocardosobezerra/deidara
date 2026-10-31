"""
C0 · importar: o legado vira um painel do Deidara. O modelo existente vira o catálogo da fonte (a estrutura
que ele já tem: tabelas, colunas, ligações, consultas), as medidas viram a proposta do C0 (os tipos prontos,
com as correções), as páginas e os visuais voltam como estavam, e a tabela de datas antiga dá lugar ao
calendário do Deidara. Daí em diante é o fluxo de sempre: validar, prototipar, aprovar, gerar.

Com `manter_antigas`, cada medida que muda de número ganha a gêmea "<nome> (antes)", oculta, com a fórmula
antiga: a homologação compara as duas lado a lado no mesmo modelo (docs/conferencia.dax).
"""

import datetime
import os
import re

from kibaku_nendo.util import chave, gravar_json, gravar_texto
from tecnicas.c0 import exame as ex
from tecnicas.c0 import proposta as pr

CAL = 'dCalendario'
COLUNAS_CAL = {'date': 'Data', 'data': 'Data', 'dia': 'Data', 'datas': 'Data', 'year': 'Ano', 'ano': 'Ano',
               'month': 'Mês', 'mes': 'Mês', 'mês': 'Mês', 'monthnumber': 'Mês', 'monthname': 'Nome do Mês',
               'nomemes': 'Nome do Mês', 'nome do mes': 'Nome do Mês', 'nome do mês': 'Nome do Mês',
               'quarter': 'Trimestre', 'trimestre': 'Trimestre', 'yearmonth': 'Ano-Mês', 'anomes': 'Ano-Mês',
               'ano-mes': 'Ano-Mês', 'ano-mês': 'Ano-Mês', 'mes/ano': 'Mês/Ano', 'mês/ano': 'Mês/Ano'}
SUFIXO = ' (antes)'


def linhas_de(leg):
    """O legado no formato do resultado da receita DAX (o catálogo sai do mesmo leitor)."""
    out = []
    for tn, t in leg['tabelas'].items():
        out.append({'secao': 'tabela', 'tabela': tn, 'descricao': t['descricao'],
                    'extra': 'calculada' if t['calculada'] else ('oculta' if t['oculta'] else '')})
        for cn, c in t['colunas'].items():
            out.append({'secao': 'coluna', 'tabela': tn, 'coluna': cn, 'tipo': c['tipo'], 'descricao': c['descricao'],
                        'extra': 'calculada' if c['calculada'] else ('oculta' if c['oculta'] else '')})
        if t['particao']:
            out.append({'secao': 'particao', 'tabela': tn, 'expressao': t['particao']})
    for r in leg['relacoes']:
        out.append({'secao': 'relacao', 'tabela': r['de'], 'coluna': r['de_coluna'],
                    'tipo': f'{r.get("de_card", "many")}>{r.get("para_card", "one")}',
                    'descricao': f'{r["para"]}[{r["para_coluna"]}]', 'extra': 'ativa' if r.get('ativa', True) else 'inativa'})
    for n, e in leg['expressoes'].items():
        out.append({'secao': 'expressao', 'tabela': n, 'expressao': e})
    return out


def _calendario_antigo(leg):
    p = ex.papeis(leg)
    return next(iter(sorted(p['calendarios'])), None)


def _trocar_calendario(texto, antigo, avisos, onde):
    """'Calendario'[Date] -> dCalendario[Data] (e as outras colunas que o calendário do Deidara tem)."""
    if not antigo:
        return texto
    padrao = r"(?:'" + re.escape(antigo).replace("'", "''") + r"'|\b" + re.escape(antigo) + r")\s*\[([^\]]+)\]"

    def troca(m):
        nova = COLUNAS_CAL.get(chave(m.group(1)))
        if not nova:
            avisos.append(f'{onde}: {antigo}[{m.group(1)}] não tem par no calendário do Deidara; ajuste à mão')
            return m.group(0)
        return f'{CAL}[{nova}]'
    return re.sub(padrao, troca, texto)


def _campo(c, antigo, avisos, onde):
    if c['tipo'] == 'medida':
        return c['nome']
    if c['tabela'] == antigo:
        nova = COLUNAS_CAL.get(chave(c['nome']))
        if nova:
            return f'{CAL}[{nova}]'
        avisos.append(f'{onde}: {antigo}[{c["nome"]}] não tem par no calendário do Deidara')
    return f'{c["tabela"]}[{c["nome"]}]'


def _visual(v, antigo, avisos, onde, implicitas):
    """O visual do relatório antigo no formato do argila.json (None quando o tipo não tem par)."""
    if not v['tipo']:
        avisos.append(f'{onde}: visual "{v["tipo_pbi"]}" sem par no Deidara (ficou de fora; refaça com `visuais` ou '
                      'a galeria)')
        return None
    cs = []
    for c in v['campos']:
        if c.get('agregada'):                      # campo arrastado sem medida: vira medida explícita
            nome = f'Soma de {c["nome"]}'
            implicitas[nome] = f'{c["tabela"]}[{c["nome"]}]'
            cs.append(dict(c, tipo='medida', nome=nome))
        else:
            cs.append(c)
    med = [_campo(c, antigo, avisos, onde) for c in cs if c['tipo'] == 'medida']
    col = [_campo(c, antigo, avisos, onde) for c in cs if c['tipo'] == 'coluna']
    t = v['tipo']
    if t in ('cartao', 'medidor'):
        return {'tipo': t, 'medida': med[0]} if med else None
    if t == 'cartoes':
        return {'tipo': t, 'medidas': med} if med else None
    if t in ('segmentador', 'botoes'):
        return {'tipo': t, 'campo': col[0]} if col else None
    if t == 'tabela':
        return {'tipo': t, 'campos': [_campo(c, antigo, avisos, onde) for c in cs]} if cs else None
    if t == 'matriz':
        linhas = [_campo(c, antigo, avisos, onde) for c in cs if c['tipo'] == 'coluna' and c['papel'] == 'Rows']
        colunas = [_campo(c, antigo, avisos, onde) for c in cs if c['tipo'] == 'coluna' and c['papel'] == 'Columns']
        return {'tipo': t, 'linhas': linhas or col[:1], 'colunas': colunas, 'valores': med} if med else None
    if t == 'decomposicao':
        return {'tipo': t, 'medida': med[0], 'cortes': col} if med else None
    if t in ('barras', 'colunas', 'linha', 'area', 'rosca'):
        cat = next((_campo(c, antigo, avisos, onde) for c in cs if c['tipo'] == 'coluna' and c['papel'] == 'Category'),
                   col[0] if col else None)
        leg_ = next((_campo(c, antigo, avisos, onde) for c in cs if c['tipo'] == 'coluna' and c['papel'] == 'Series'), None)
        if not cat or not med:
            return None
        out = {'tipo': t, 'categoria': cat, 'valores': med}
        if leg_:
            out['legenda'] = leg_
        return out
    if t == 'dispersao' and col and len(med) >= 2:
        return {'tipo': t, 'categoria': col[0], 'x': med[0], 'y': med[1]}
    avisos.append(f'{onde}: visual {t} sem campos suficientes; ficou de fora')
    return None


def importar(leg, pasta, fonte='legado', projeto=None, manter_antigas=False, estudo=None):
    """Grava a pasta do painel (catálogo, argila.json, relatório do C0). Devolve (argila, avisos)."""
    from tecnicas.c0 import relato
    from tecnicas.luneta.receitas import catalogo_de_dax
    avisos = list(leg.get('avisos') or [])
    estudo = estudo or ex.examinar(leg)
    os.makedirs(os.path.join(pasta, 'catalogos'), exist_ok=True)
    cat, av_cat = catalogo_de_dax(linhas_de(leg), fonte)
    antigo = _calendario_antigo(leg)
    avisos += [x for x in av_cat if not (antigo and f'tabela {antigo} ' in x)]   # o calendário antigo sai de propósito
    gravar_json(os.path.join(pasta, 'catalogos', f'{fonte}.json'), cat)
    if antigo:
        avisos.append(f'a tabela de datas {antigo} deu lugar ao calendário do Deidara ({CAL}: contínuo, marcado, para no '
                      'último dado); confira o "inicio" do calendário no argila.json')
    p = ex.papeis(leg)
    tabelas = []
    for tn, t in leg['tabelas'].items():
        if tn == antigo or t['calculada'] or t['grupo_calculo'] or tn not in cat['tabelas']:
            if t['grupo_calculo']:
                avisos.append(f'grupo de cálculo {tn}: refaça com "grupo_calculo" do Deidara')
            continue
        tabelas.append({'nome': tn, 'tipo': 'fato' if tn in p['fatos'] else 'dimensao', 'fonte': fonte, 'origem': tn,
                        'colunas': [c['coluna'] for c in cat['tabelas'][tn]['colunas']]})
    nomes_t = {t['nome'] for t in tabelas}
    rels, datas = [], []
    for r in leg['relacoes']:
        if r['para'] == antigo and r['de'] in nomes_t:
            datas.append({'tabela': r['de'], 'coluna': r['de_coluna'], **({} if r.get('ativa', True) else {'ativo': False})})
        elif r['de'] in nomes_t and r['para'] in nomes_t and not (r.get('de_card') == 'many' and r.get('para_card') == 'many'):
            rel = {'de': r['de'], 'para': r['para']}
            if sum(1 for x in leg['relacoes'] if {x['de'], x['para']} == {r['de'], r['para']}) > 1:
                rel['via'] = [r['de_coluna']]
            if not r.get('ativa', True):
                rel['ativo'] = False
            rels.append(rel)
    medidas, vistos, fora = [], set(), []
    quebra = {'sintaxe', 'funcao_desconhecida', 'ref_inexistente', 'ciclo'}
    for nome, x in estudo['medidas'].items():
        if {a['codigo'] for a in x['achados']} & quebra:
            fora.append(nome)
            continue
        prop = pr.propor(nome, leg, x, estudo['medidas'])
        for m in prop['argila']:
            if chave(m['nome']) in vistos:
                continue
            vistos.add(chave(m['nome']))
            for k in ('dax', 'entradas', 'saidas', 'fim', 'coluna'):
                if isinstance(m.get(k), str):
                    m[k] = _trocar_calendario(m[k], antigo, avisos, f'medida {m["nome"]}')
            if m['nome'] == nome and m.get('tabela') and m['tabela'] not in nomes_t:
                m.pop('tabela')
            medidas.append(m)
        if manter_antigas and prop['muda_o_numero'] and not leg['medidas'][nome].get('oculta'):
            medidas.append({'nome': nome + SUFIXO, 'oculta': True, 'pasta': 'C0 · antes',
                            'descricao': f'Fórmula antiga de [{nome}], para a homologação comparar (apague depois).',
                            'dax': _antes(nome, leg, antigo, avisos), 'formato': pr.formato(leg['medidas'][nome].get('formato')) or 'decimal'})
    if manter_antigas:                            # as gêmeas citam as gêmeas: a conta antiga fica inteira
        gemeas = {m['nome'][:-len(SUFIXO)] for m in medidas if m['nome'].endswith(SUFIXO)}
        for dep in _dependencias(gemeas, leg) - gemeas:
            if chave(dep + SUFIXO) not in vistos and dep in leg['medidas'] and dep not in fora:
                medidas.append({'nome': dep + SUFIXO, 'oculta': True, 'pasta': 'C0 · antes',
                                'descricao': f'Fórmula antiga de [{dep}] (apoio da homologação).',
                                'dax': _antes(dep, leg, antigo, avisos)})
                vistos.add(chave(dep + SUFIXO))
    _ligar_metas(medidas, leg, estudo, avisos)
    for nome, x in estudo['medidas'].items():
        if any(a['codigo'] == 'dado_pessoal' for a in x['achados']) and nome not in fora:
            avisos.append(f'medida {nome} filtra por dado pessoal (CPF ou e-mail): troque por código ou grupo antes do '
                          'protótipo (LGPD)')
    implicitas = {}
    paginas = []
    for pg in leg.get('paginas') or []:
        vis = [v for v in (_visual(v, antigo, avisos, f'página {pg["nome"]}', implicitas) for v in pg['visuais']) if v]
        if vis:
            paginas.append({'nome': pg['nome'], 'visuais': vis})
    for nome, col in implicitas.items():
        if chave(nome) not in vistos:
            medidas.append({'nome': nome, 'agregacao': 'soma', 'coluna': col,
                            'descricao': f'A DEFINIR: soma de {col} (era um campo arrastado direto no visual).'})
    if not [m for m in medidas if not m.get('oculta')] and tabelas:     # modelo sem medida: começa contando linhas
        t0 = next((t for t in tabelas if t['tipo'] == 'fato'), tabelas[0])
        medidas.append({'nome': f'Linhas de {t0["nome"]}', 'agregacao': 'contagem_linhas', 'tabela': t0['nome'],
                        'descricao': f'A DEFINIR: o que cada linha de {t0["nome"]} representa'})
        avisos.append('o modelo antigo não tinha medidas: o painel começa com a contagem de linhas; defina os '
                      'indicadores com o dono (`deidara.py padroes`)')
    if not paginas:
        paginas = [{'nome': 'Visão Geral', 'visuais': [{'tipo': 'cartao', 'medida': m['nome']} for m in medidas
                                                       if not m.get('oculta')][:4]}]
    argila = {'projeto': projeto or os.path.basename(os.path.abspath(pasta)), 'versao': '1.0', 'modelo': 'faixa-de-kpis',
              'descricao': 'A DEFINIR: para que serve o painel e que decisão ele apoia (refeito pelo C0 do Deidara)',
              'publico': 'A DEFINIR', 'fontes': {fonte: {'catalogo': f'catalogos/{fonte}.json'}},
              'tabelas': tabelas, 'relacionamentos': rels, 'medidas': medidas, 'paginas': paginas}
    if datas or antigo:
        argila['calendario'] = {'inicio': datetime.date.today().year - 5, 'datas': datas}
    if fora:
        avisos.append('medidas que não calculam no modelo antigo ficaram de fora (conserte e acrescente à mão): '
                      + ', '.join(fora))
    gravar_json(os.path.join(pasta, 'argila.json'), argila)
    gravar_texto(os.path.join(pasta, 'c0_relatorio.md'), relato.markdown(leg, estudo, propostas=True))
    if not os.path.exists(os.path.join(pasta, 'painel.json')):
        gravar_json(os.path.join(pasta, 'painel.json'), {'projeto': argila['projeto'], 'origem': 'c0 importar'})
    return argila, avisos


def _ligar_metas(medidas, leg, estudo, avisos):
    """A meta que estava escondida: a medida "Meta X" (ou o número escrito no IF) vira a "meta" da taxa X, com a
    polaridade que a comparação antiga usava. Sem como saber a polaridade, pergunta."""
    por_nome = {chave(m['nome']): m for m in medidas}
    tokens = lambda s: {w for w in re.findall(r'[a-z0-9]+', chave(s)) if w not in ('meta', 'de', 'do', 'da')}  # noqa: E731
    for nome, x in estudo['medidas'].items():
        for a in x['achados']:
            if a['codigo'] != 'meta_no_codigo':
                continue
            mt = re.search(r'\[([^\]]+)\]\s*(<=|>=|<|>)\s*(-?\d+(?:\.\d+)?)', leg['medidas'][nome]['dax'])
            alvo = por_nome.get(chave(mt.group(1))) if mt else None
            if alvo and 'meta' not in alvo:
                alvo['polaridade'] = 'menor_melhor' if mt.group(2).startswith('<') else 'maior_melhor'
                alvo['_meta_codigo'] = float(mt.group(3))
    for m in medidas:
        numero = m.pop('_meta_codigo', None)
        if m.get('oculta') or m['nome'].endswith(SUFIXO) or re.match(r'meta\b', chave(m['nome'])):
            continue
        # a meta "Meta Turnover" vai para a taxa que tem o mesmo nome ("Turnover %"), não para as vizinhas
        meta = next((x for x in medidas if re.match(r'meta\b', chave(x['nome'])) and tokens(x['nome'])
                     and tokens(x['nome']) == tokens(m['nome']) and m.get('tipo') == 'divisao'), None)
        if meta:
            m['meta'] = meta['nome']
        elif numero is not None:
            m['meta'] = numero
        if 'meta' in m and 'polaridade' not in m:
            avisos.append(f'[{m["nome"]}] ganhou a meta "{m["meta"]}": confirme a polaridade com o dono (menor é melhor? '
                          'ponha "polaridade": "menor_melhor"); sem isso, a cor trata maior como melhor')


def _dependencias(nomes, leg):
    from tecnicas.c0.anatomia import refs
    out, fila = set(), list(nomes)
    while fila:
        n = fila.pop()
        for d in refs((leg['medidas'].get(n) or {}).get('dax', ''), leg['medidas'])['medidas']:
            if d not in out:
                out.add(d)
                fila.append(d)
    return out


def _antes(nome, leg, antigo, avisos):
    """A fórmula antiga com as medidas citadas trocadas pelas gêmeas "(antes)"."""
    dax = leg['medidas'][nome]['dax']
    for dep in sorted(leg['medidas'], key=len, reverse=True):
        dax = re.sub(r'\[' + re.escape(dep) + r'\]', '[' + dep.replace(']', ']]') + SUFIXO + ']', dax)
    return _trocar_calendario(dax, antigo, avisos, f'medida {nome}{SUFIXO}')
