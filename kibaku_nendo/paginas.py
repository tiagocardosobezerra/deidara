"""
As páginas e os visuais: o modelo de layout, o tema e o contraste, cada visual contra o modelo, os
cortes que filtram (ou não) cada medida, o grupo de cálculo e o tour.
"""

import re
from kibaku_nendo.modelo import (CALENDARIO_SEM_ANO, DIAGNOSTICOS, LIMITE_VISUAIS_POR_PAGINA, RANKINGS,
                                 SEGMENTADORES, SVG_GERADAS, TIPOS_VISUAL, VISUAIS_DE_TERCEIROS, alcanca,
                                 campo_do_modelo, nova_coluna, conferir_funcoes, depende_de, grafo_de_filtro,
                                 medidas_do_visual, pista_medida, tabelas_da_medida, chega, medida,
                                 pista_coluna, tabela_do_modelo)
from kibaku_nendo.util import chave, dax_coluna, numero_br


def resolver_layout(argila, m, p):
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


def conferir_design(argila, m, p):
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


def resolver_paginas(argila, m, p):
    if not argila.get('paginas'):
        p.erro('paginas', 'nenhuma página no painel')
    filtra = grafo_de_filtro(m)
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
            c = campo_do_modelo(m, pg['detalhe'])
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


def resolver_grupo_calculo(argila, m, p):
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
        conferir_funcoes(dax, p, onde)
        lista.append({'chave': x, 'rotulo': rotulo, 'dax': dax, 'ordem': k,
                      'formato': ('IF(ISNUMBER(SELECTEDMEASURE()), "0.0%", SELECTEDMEASUREFORMATSTRING())'
                                  if pct else None)})
    t = {'nome': nome, 'tipo': 'dimensao', 'origem': None, 'fonte': None, 'filtro': None, 'pk': [], 'auxiliar': True,
         'descricao': cfg.get('descricao') or 'Grupo de cálculo: a conta de tempo que vale para todas as medidas.',
         'colunas': [], 'grupo_calculo': {'itens': lista, 'precedencia': cfg.get('precedencia', 1)}}
    col = nova_coluna(nome, None, 'texto')
    col['ordenar_por'] = 'Ordem'
    t['colunas'] = [col, nova_coluna('Ordem', None, 'inteiro', oculta=True)]
    m['tabelas'].append(t)
    p.aviso(onde, f'[Modelagem] o grupo de cálculo "{nome}" muda TODAS as medidas do visual pelo item escolhido; '
                  'ponha o segmentador dele na página (de botões, de seleção única) e deixe as medidas de tempo '
                  'prontas para quando só uma medida precisa da conta')


def resolver_tours(m, p):
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
        conferir_funcoes(dax, p, onde)
        p.aviso(onde, '[Design] o tour usa o HTML Content (versão certificada), visual do AppSource: o administrador '
                      'do Power BI precisa liberar, e quem abre baixa o visual na primeira vez')
        if len(lay['posicoes']) > len(lista):
            p.aviso(onde, f'[Design] o tour mostra os {len(lista)} primeiros visuais da página; o resto fica sem passo')


def _conferir_pagina(m, pagina, p, onde, filtra):
    auxiliares = {t['nome'] for t in m['tabelas'] if t.get('auxiliar')}
    segs = [v['categoria'] for v in pagina['visuais'] if v['tipo'] in SEGMENTADORES and v['categoria']
            and v['categoria']['tabela'] not in auxiliares]
    medidas = {md['nome'] for v in pagina['visuais'] for md in medidas_do_visual(v)}
    metas = {x['meta_medida'] for x in m['medidas'] if x.get('meta_medida')}
    paradas = {}                                   # meta que não muda com o segmentador: um aviso só por meta
    for s in segs:
        for nome in sorted(medidas):
            alvo = tabelas_da_medida(m, nome)
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
                           and alcanca(grafo_de_filtro(m), de['nome'], t['nome']))
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
        c = campo_do_modelo(m, ref)
        if not c:
            p.erro(onde, f'{rotulo} "{ref}" não é {"coluna (Tabela[Coluna])" if quer == "coluna" else "medida"} do modelo'
                   + (pista_coluna(m, ref) if '[' in (ref or '') else pista_medida(ref, {chave(x['nome']): x for x in m['medidas']
                                                                                            if x['tipo'] != 'cor'})),
                   depende=depende_de(ref) + tuple(('medida', chave(ref)) for _ in [0] if ref))
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
            r['meta'] = campo_do_modelo(m, alvo['meta_medida'])
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
        r['categoria'] = campo_do_modelo(m, f'{cfg["tabela"]}[{cfg["coluna"]}]')
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
        for md in medidas_do_visual(r):
            alvo = tabelas_da_medida(m, md['nome'])
            faltam = sorted(a for a in alvo if not chega(m, filtra, f['tabela'], a, md['nome']))
            if faltam and len(faltam) == len(alvo):
                p.aviso(onde, f'{f["tabela"]}[{f["nome"]}] não filtra a medida "{md["nome"]}" (nenhum relacionamento '
                              f'leva de {f["tabela"]} até {", ".join(faltam)}): o valor vai repetir em toda linha')
            elif faltam:
                p.aviso(onde, f'{f["tabela"]}[{f["nome"]}] filtra só parte de "{md["nome"]}" (não chega em '
                              f'{", ".join(faltam)}): confira se a conta continua fazendo sentido em cada linha')
    return r
