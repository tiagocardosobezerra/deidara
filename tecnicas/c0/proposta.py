"""
C0 · proposta: como fica cada medida no Deidara (o trecho do argila.json com os tipos prontos), o DAX
corrigido quando a correção é segura e as melhorias do portfólio (meta do período, meta ponderada, data de
corte, contra-indicador, visuais da galeria, gráfico de controle).

Quando a correção muda o número (o denominador do turnover passa a ser o estoque médio, por exemplo), a
proposta diz isso com todas as letras: o gestor precisa saber antes de trocar.
"""

import re

from kibaku_nendo.util import chave
from tecnicas.c0.anatomia import limpo, refs, sem_texto
from tecnicas.c0.exame import CADASTRO


def formato(fmt):
    f = (fmt or '').lower()
    if not f:
        return None
    if '%' in f:
        return 'percentual'
    if 'r$' in f or '$' in f or 'currency' in f:
        return 'moeda'
    if re.fullmatch(r'[#,0]+', f.replace('\\', '')):
        return 'inteiro'
    return 'decimal'


def _alvo(texto):
    """'T'[C] / T[C] / 'T' -> ('T', 'C' ou None)."""
    mt = re.fullmatch(r"'?((?:[^'\[]|'')+?)'?\s*(?:\[([^\]]+)\])?", texto.strip())
    return (mt.group(1).replace("''", "'"), mt.group(2)) if mt else (texto, None)


def _ref(t, c):
    return f'{t}[{c}]'


def dax_corrigido(dax):
    """As correções seguras (mesmo número, sem erro): "/" entre duas referências vira DIVIDE; IFERROR sobre uma
    divisão vira DIVIDE com o valor alternativo. Devolve (dax, [o que mudou])."""
    novo, mudou = dax, []
    mt = re.fullmatch(r"\s*IFERROR\s*\(\s*\((.+)\)\s*/\s*(\[[^\]]+\]|'?[\w ]+'?\[[^\]]+\])\s*,\s*([^,()]+)\)\s*", novo, re.S | re.I)
    if mt:
        novo = f'DIVIDE({mt.group(1).strip()}, {mt.group(2)}, {mt.group(3).strip()})'
        mudou.append('IFERROR sobre a divisão virou DIVIDE com o mesmo valor alternativo')
    ref = r"(\[[^\]]+\]|'?[\w ]+'?\[[^\]]+\])"
    alvo = re.sub(ref + r"\s*/\s*" + ref, lambda m: f'DIVIDE({m.group(1)}, {m.group(2)})', novo)
    if alvo != novo:
        novo = alvo
        mudou.append('divisão com "/" virou DIVIDE (denominador zero ou vazio não dá mais erro)')
    return novo, mudou


def _estoque(leg, tabela):
    """As pontas de um estoque sobre a tabela de cadastro: (entradas, fim na mesma tabela, saídas em outra)."""
    t = leg['tabelas'].get(tabela) or {'colunas': {}}
    datas = [c for c, x in t['colunas'].items() if re.search(r'date|data', (x.get('tipo') or '') + c, re.I)]
    entradas = next((c for c in datas if CADASTRO.search(c)), None)
    fim = next((c for c in datas if re.search(r'deslig|demiss|fim|saida|saída|termino|término|end|rescis', c, re.I)), None)
    saidas = None
    if not fim:
        for r in leg['relacoes']:
            if r['para'] == tabela and r['de'] != tabela:
                outra = leg['tabelas'].get(r['de']) or {'colunas': {}}
                c = next((c for c, x in outra['colunas'].items() if re.search(r'date|data', (x.get('tipo') or '') + c, re.I)
                          and re.search(r'deslig|demiss|saida|saída|cancel|rescis|baixa|end', c + r['de'], re.I)), None)
                if c:
                    saidas = _ref(r['de'], c)
                    break
    return (_ref(tabela, entradas) if entradas else None, _ref(tabela, fim) if fim else None, saidas)


def _medida_estoque(leg, nomes):
    """O estoque já existente no legado (ou o nome proposto)."""
    return next((n for n in nomes if re.search(r'head ?count|ativos|quadro|efetivo|vigentes', n, re.I)), 'Ativos')


def propor(nome, leg, estudo, tudo):
    """{'argila': [medidas no formato do argila.json], 'dax_sugerido', 'mudancas_dax', 'muda_o_numero',
    'melhorias': [texto]} para uma medida. `tudo` é o resultado do exame inteiro (para olhar as vizinhas)."""
    md = leg['medidas'][nome]
    pad, ach = estudo['padrao'], {a['codigo'] for a in estudo['achados']}
    base = {'nome': nome, 'descricao': md.get('descricao') or f'A DEFINIR: {estudo["leitura"]}'}
    if md.get('pasta'):
        base['pasta'] = md['pasta']
    fmt = formato(md.get('formato'))
    if fmt:
        base['formato'] = fmt
    if md.get('tabela'):
        base['tabela'] = md['tabela']
    novo, mudancas = dax_corrigido(md['dax'])
    argila, melhorias, muda = [], [], []
    t = pad['tipo']
    if t == 'agregacao' and 'estoque_contagem' in ach:
        tab = _alvo(pad['alvo'])[0]
        ent, fim, sai = _estoque(leg, tab)
        m = dict(base, tipo='estoque_na_data', entradas=ent or f'{tab}[<data de entrada>]')
        m.pop('formato', None)
        if fim:
            m['fim'] = fim
        elif sai:
            m['saidas'] = sai
        argila.append(m)
        muda.append(f'passa a contar só quem está ativo no fim do período (hoje conta o cadastro inteiro de {tab})')
    elif t == 'agregacao':
        tab, col = _alvo(pad['alvo'])
        m = dict(base, agregacao=pad['agregacao'])
        if pad['agregacao'] == 'contagem_linhas':
            m['tabela'] = tab
        else:
            m['coluna'] = _ref(tab, col)
        if 'soma_cadastro' in ach:
            m['no_estoque'] = _medida_estoque(leg, leg['medidas'])
            muda.append('passa a somar só quem está ativo no fim do período (hoje soma ativos e desligados)')
        if 'meta_media' in ach:
            usa = next((n for n, x in tudo.items() if x['padrao'].get('tipo') == 'divisao'
                        and f'[{chave(nome)}]' in chave(sem_texto(leg['medidas'][n]['dax']))), None)
            taxa = next((n for n, x in tudo.items() if x['padrao'].get('tipo') == 'divisao'), None)
            peso = tudo[taxa]['padrao']['denominador'] if taxa else '<denominador da taxa>'
            if taxa and any(a['codigo'] == 'taxa_sobre_cadastro' for a in tudo[taxa]['achados']):
                peso = f'{_medida_estoque(leg, [peso] + list(leg["medidas"]))} Médio'   # o denominador novo da taxa
            ligada = next((r for r in leg['relacoes'] if r['de'] == tab), None)
            m = dict(base, tipo='media_ponderada', coluna=_ref(tab, col), peso=peso,
                     por=_ref(ligada['para'], ligada['para_coluna']) if ligada else '<Tabela[Coluna] das áreas da meta>')
            muda.append(f'a meta do total passa a pesar cada área pelo tamanho ({peso})' + (f', como [{usa}]' if usa else ''))
        argila.append(m)
    elif t == 'divisao':
        m = dict(base, tipo='divisao', numerador=pad['numerador'], denominador=pad['denominador'])
        if 'taxa_sobre_cadastro' in ach:
            est = _medida_estoque(leg, [pad['denominador']] + list(leg['medidas']))
            m['denominador'] = f'{est} Médio'
            argila.append({'nome': f'{est} Médio', 'tipo': 'media_mensal', 'base': est,
                           'descricao': f'Média de {est} no fim de cada mês do período.'})
            muda.append(f'o denominador passa a ser o estoque médio do período ([{est} Médio]); a taxa muda de valor e '
                        'passa a comparar meses (hoje divide pelo cadastro inteiro)')
        if fmt == 'percentual':                   # não preenche: o validar pergunta ao dono (anual, mensal, período)
            melhorias.append(f'diga a que período a meta de [{nome}] se refere: "base_meta": "ano" ou "mes" se for '
                             'taxa sobre estoque (turnover, churn); "periodo" se vale para qualquer recorte')
        argila.insert(0, m)
    elif t in ('acumulado_ano', 'ano_anterior', 'variacao_ano_anterior', 'mes_anterior', 'variacao_mes_anterior',
               'movel_12m', 'media_mensal'):
        tipo = {'mes_anterior': 'variacao_mes_anterior'}.get(t, t) if t != 'mes_anterior' else None
        if tipo:
            argila.append(dict(base, tipo=tipo, base=pad['base']))
        else:
            argila.append(dict(base, dax=novo))
        if 'ano_anterior_parcial' in ach:
            muda.append('no ano em curso, o ano anterior passa a ir só até o mesmo dia do último dado: a variação deixa '
                        'de mostrar a queda falsa')
    else:
        argila.append(dict(base, dax=novo))
    if 'media_de_taxas' in ach:
        taxa = next((x for x in refs(md['dax'], leg['medidas'])['medidas']), None)
        if taxa:                                  # o total passa a ser a própria taxa (recalculada no total)
            argila = [dict(base, dax=f'[{taxa}]', descricao=(md.get('descricao') or nome)
                           + f' (era a média das taxas; agora é a própria [{taxa}], recalculada no total)')]
        melhorias.append(f'troque a média das taxas pela própria [{taxa}] no total: a taxa do total é recalculada '
                         '(numerador total ÷ denominador total)' if taxa else 'recalcule a taxa no total, sem média')
        muda.append('o total passa a ser a taxa do grupo, não a média das áreas')
    if 'meta_no_codigo' in ach:
        mt = re.search(r'\[([^\]]+)\]\s*(<=|>=|<|>)\s*(-?\d+(?:\.\d+)?)', limpo(md['dax']))
        if mt:
            melhorias.append(f'a meta {mt.group(3)} está escrita dentro da fórmula: ponha "meta": {mt.group(3)} e a '
                             f'polaridade ("{"menor_melhor" if mt.group(2).startswith("<") else "maior_melhor"}") em '
                             f'[{mt.group(1)}]; o Deidara cria a medida da meta, a cor e o status')
    if 'hoje' in ach:
        melhorias.append('no Deidara, as contas de tempo param na Data de Corte (o último dia com dado), não em TODAY()')
    if 'dado_pessoal' in ach:
        melhorias.append('troque o filtro por CPF ou e-mail por um código ou um grupo (LGPD: o DAX vai junto com o modelo)')
    if 'boa_pratica' in ach and not mudancas:
        melhorias += [a['correcao'] for a in estudo['achados'] if a['codigo'] == 'boa_pratica']
    melhorias += _portfolio(nome, leg, estudo, fmt)
    return {'argila': argila, 'dax_sugerido': novo if mudancas else None, 'mudancas_dax': mudancas,
            'muda_o_numero': muda, 'melhorias': list(dict.fromkeys(melhorias))}


def _portfolio(nome, leg, estudo, fmt):
    """O que o Deidara tem e o indicador ainda não usa."""
    out = []
    t = estudo['padrao']['tipo']
    usos = [v for pg in leg.get('paginas') or [] for v in pg['visuais']
            if any(c['tipo'] == 'medida' and c['nome'] == nome for c in v['campos'])]
    if t == 'divisao' and fmt == 'percentual':
        out.append(f'"tolerancia" (faixa amarela de "perto da meta"), "dono" e "periodicidade" para a ficha de [{nome}]')
        out.append(f'gráfico de controle de [{nome}] ("é sinal ou ruído?"): {{"tipo": "controle", "medida": "{nome}"}}')
        out.append(f'um contra-indicador ao lado de [{nome}], para ninguém melhorar o número piorando outra coisa')
    if t.startswith('variacao') or t in ('ano_anterior',):
        out.append('o que explica a variação: cascata da galeria (`deidara.py galeria cascata`, ex.: '
                   '"deneb-vega-templates/flow/waterfall" ou as funções PowerofBI.IBCS)')
    if any(v['tipo'] in ('tabela', 'matriz') for v in usos) and t in ('divisao', 'agregacao'):
        out.append(f'minigráfico de [{nome}] na tabela: "funcoes_dax": ["DaxLib.SVG"] e uma medida '
                   f'DaxLib.SVG.Viz.Line(<coluna do mês>, [{nome}])')
    if any(v['tipo'] == 'cartao' for v in usos) and t == 'divisao':
        out.append(f'no cartão de [{nome}], a barra contra a meta ("svg_barra_meta") ou o bullet da galeria')
    from tecnicas.sasori import padroes_para
    pad = next((x for x in padroes_para(nome) if x.get('cadeia') and any(
        chave(w) in chave(nome) for w in x['termos'] if len(w) > 4)), None)
    if pad:
        out.append(f'padrão "{pad["id"]}" do Deidara para [{nome}] (`deidara.py padroes {pad["id"]}`): '
                   + (pad.get('armadilhas') or [''])[0])
    return out


def propor_modelo(leg, exame):
    """As melhorias do modelo inteiro (calendário, ligações, data automática)."""
    out = []
    codigos = {a['codigo'] for a in exame['modelo']}
    if codigos & {'sem_calendario', 'data_automatica'} or any(
            a['codigo'] in ('tempo_fora_do_calendario', 'data_automatica_usada') for x in exame['medidas'].values()
            for a in x['achados']):
        out.append('calendário do Deidara: contínuo, marcado, acompanha o ano, para no último dado e tem feriados '
                   '("calendario": {"inicio": <ano>, "feriados": "BR", "datas": [...]})')
    if 'bidirecional' in codigos:
        out.append('ligações num sentido só (o Deidara gera assim); onde precisar, CROSSFILTER na medida')
    if 'coluna_fazendo_medida' in codigos:
        out.append('as colunas calculadas que somam viram medidas (ou contas por linha na view)')
    return out
