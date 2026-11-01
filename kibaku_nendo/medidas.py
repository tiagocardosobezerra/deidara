"""
As medidas do argila.json: agregação, divisão, tempo, estoque, metas com a cor, as medidas que
desenham (SVG) e as técnicas que pedem tabela auxiliar.
"""

from kibaku_nendo.desenhos import (COR_ATENCAO, COR_BOA, COR_RUIM, FORMATO_DAX, PREFIXO_SVG, html_kpis_dax, svg_barra_meta,
                                   svg_bolha, svg_dispersao, svg_espinha, svg_estrelas, svg_iniciais,
                                   svg_pilula, svg_posicao, svg_progresso, svg_radar, svg_seta, svg_variacao,
                                   texto_dax, conferir_svg)
from kibaku_nendo.modelo import (AGREGACOES, AGREGACOES_NUMERICAS, COR_APAGADA, EXTRAS, RANKINGS, SVG_GERADAS,
                                 TEMPO, alcanca, nova_coluna, conferir_funcoes, depende_de, grafo_de_filtro,
                                 pista_medida, resolver_coluna, chave_coluna, coluna_do_modelo, medida,
                                 pista_coluna, referencias_dax, sintaxe_dax, tabela_do_modelo, boas_praticas_dax,
                                 tabelas_da_medida)
from kibaku_nendo.util import FORMATOS, NUMERICAS, chave, dax_coluna, dax_medida, dax_tabela


def resolver_medidas(argila, m, p):
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
             'meta_medida': None, 'cor_medida': None, 'base_meta': md.get('base_meta'),
             'dono': md.get('dono'), 'periodicidade': md.get('periodicidade'), 'tolerancia': md.get('tolerancia')}
        try:
            if 'agregacao' in md:
                _medida_agregacao(m, md, r, p, onde)
            elif md.get('tipo') == 'divisao':
                r['tipo'] = 'divisao'
                for k in ('numerador', 'denominador'):
                    if chave(md.get(k, '')) not in nomes:
                        p.erro(onde, f'{k} "{md.get(k)}" não é uma medida do modelo' + pista_medida(md.get(k), nomes))
                num = dax_medida(md.get('numerador', ''))
                if md.get('formato') == 'percentual':
                    # taxa: mês sem nenhum desligamento é 0%, não um buraco na linha (sem base, continua em branco)
                    num += ' + 0'
                r['dax'] = f'DIVIDE({num}, {dax_medida(md.get("denominador", ""))})'
                r['depende'] = [md.get('numerador'), md.get('denominador')]
            elif md.get('tipo') in TEMPO:
                _medida_tempo(m, md, r, p, onde, nomes)
            elif md.get('tipo') == 'estoque_na_data':
                _medida_estoque(m, md, r, p, onde)
            elif md.get('tipo') == 'media_ponderada':
                _medida_ponderada(m, md, r, p, onde, nomes)
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
                elif m.get('funcoes_dax'):            # chama uma função de imagem do daxlib (SVG, IBCS, cascata)
                    from tecnicas.sasori import funcoes_usadas
                    usadas = {n.upper() for n in funcoes_usadas(r['dax'])}
                    if usadas & {n.upper() for n in m['funcoes_dax']['imagem']}:
                        r['imagem'], r['formato'] = True, None
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
    _no_estoque(m, p)
    _cadastro_inteiro(m, p)
    _taxa_sobre_cadastro(m, p)
    _herdar_polaridade(m, brutas)
    _metas(m, p)
    _svgs(m, p)
    _extras(m, p)
    _c4(m, p)
    _ciclos(m, p)
    for md in m['medidas']:
        if md.get('tipo') not in ('cor', 'meta', 'corte') and (not (md.get('descricao') or '').strip()
                                                      or md['descricao'].strip().upper().startswith('A DEFINIR')):
            m['pendencias'].append(f'medida {md["nome"]}: definição de negócio pendente')
            p.aviso(f'medida {md["nome"]}', 'definição pendente: escreva o que o número significa (numerador, '
                                            'filtro, período) antes de mostrar ao gestor; o aprovar recusa sem ela')


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
            p.erro(onde, f'"medida" ("{cfg.get("medida")}") não é uma medida do modelo' + pista_medida(cfg.get('medida'), todas))
            continue
        tc, cc = resolver_coluna(m, cfg.get('categoria'))
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
            tl, cl = resolver_coluna(m, cfg.get('coluna_matriz'))
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
        if tipo in ('svg_seta', 'svg_variacao', 'impacto', 'leitura'):
            comp = medida(m, cfg.get('comparar') or '')
            if not comp:
                p.erro(onde, f'"comparar" ("{cfg.get("comparar")}") precisa ser a medida do valor anterior '
                             '(ex.: a de ano anterior)' + pista_medida(cfg.get('comparar'), todas))
                continue
            cfg['comparar'] = comp['nome']
            md['depende'].append(comp['nome'])
        if base.get('meta_medida'):
            cfg['meta'] = base['meta_medida']
        op = '>=' if maior else '<='
        if tipo == 'svg_barra_meta':
            md['depende'].append(base['meta_medida'])
            md['dax'] = svg_barra_meta(b, dax_medida(base['meta_medida']), col, op)
        elif tipo == 'svg_pilula':
            md['depende'].append(base['meta_medida'])
            md['dax'] = svg_pilula(b, dax_medida(base['meta_medida']), col, op)
        elif tipo == 'svg_seta':
            md['dax'] = svg_seta(b, dax_medida(cfg['comparar']), col, op)
        elif tipo == 'svg_posicao':
            md['dax'] = svg_posicao(b, col, sentido, (m['tema']['cores'] or ['#118DFF'])[0])
        elif tipo == 'svg_radar':
            md['dax'] = svg_radar([dax_medida(x) for x in cfg['medidas']], col, (m['tema']['cores'] or ['#118DFF'])[0])
        elif tipo == 'svg_bolha':
            md['dax'] = svg_bolha(b, col, dax_coluna(*cfg['coluna_matriz']), (m['tema']['cores'] or ['#118DFF'])[0])
        elif tipo == 'svg_variacao':
            md['dax'] = svg_variacao(b, dax_medida(cfg['comparar']), col, '>=' if maior else '<=')
        elif tipo == 'svg_estrelas':
            md['dax'] = svg_estrelas(b, col, maior, maximo)
        elif tipo == 'svg_progresso':
            md['depende'].append(base['meta_medida'])
            md['dax'] = svg_progresso(b, dax_medida(base['meta_medida']), col, op)
        elif tipo == 'leitura':                        # a frase do Tobi: o que o número fez e quem puxou
            from tecnicas import tobi
            cfg['aditiva'] = tobi.aditiva(base)
            md['formato'] = None
            cal = (m.get('calendario') or {}).get('tabela')
            if cal:                                    # com calendário, a frase diz também a tendência (C4 Karura)
                from tecnicas import c4
                tendencia = c4.dax_tendencia(b, dax_tabela(cal), base['formato'])
            md['dax'] = tobi.dax(base['nome'], b, dax_medida(cfg['comparar']), col, base['formato'], maior, cfg['aditiva'],
                                 tendencia if cal else None)
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
        conferir_funcoes(md['dax'], p, onde)
        if md.get('imagem'):
            conferir_svg(md['dax'], p, onde)
    m['medidas'].extend(novas)


def _tabela_auxiliar(m, p, onde, nome, dax, colunas, descricao):
    """Tabela calculada em DAX que o Deidara cria para uma técnica (opções das abas, chave de alternar, cópia
    solta da coluna do destaque). Não tem fonte nem relacionamento: só as medidas leem a escolha."""
    if tabela_do_modelo(m, nome):
        p.erro(onde, f'já existe uma tabela chamada "{nome}"')
        return None
    t = {'nome': nome, 'tipo': 'dimensao', 'origem': None, 'fonte': None, 'descricao': descricao, 'filtro': None,
         'colunas': [], 'pk': [], 'auxiliar': True, 'calculada': dax}
    for c in colunas:
        col = nova_coluna(c['nome'], None, c.get('familia', 'texto'), oculta=c.get('oculta', False))
        col['ordenar_por'] = c.get('ordenar_por')
        t['colunas'].append(col)
    m['tabelas'].append(t)
    conferir_funcoes(dax, p, onde)
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
            linhas = ', '.join(f'{{ {texto_dax(r)}, {k} }}' for k, (r, _) in enumerate(alvos, 1))
            if not _tabela_auxiliar(m, p, onde, tab, f'DATATABLE("Opção", STRING, "Ordem", INTEGER, {{ {linhas} }})',
                                    [{'nome': 'Opção', 'ordenar_por': 'Ordem'}, {'nome': 'Ordem', 'familia': 'inteiro',
                                                                                  'oculta': True}],
                                    f'Opções de "{nome}" (uma por botão).'):
                continue
            col = dax_coluna(tab, 'Opção')
            ramos = ', '.join(f'{texto_dax(r)}, {dax_medida(a["nome"])}' for r, a in alvos)
            md['dax'] = (f'VAR _escolha = SELECTEDVALUE({col}, {texto_dax(alvos[0][0])})\n'
                         f'RETURN\n    SWITCH(_escolha, {ramos})')
            formatos = {a['formato'] for _, a in alvos}
            md['formato'] = alvos[0][1]['formato']
            if len(formatos) > 1:                     # cada opção com o próprio formato (formato dinâmico)
                md['formato_dinamico'] = (f'SWITCH(SELECTEDVALUE({col}, {texto_dax(alvos[0][0])}), '
                                          + ', '.join(f'{texto_dax(r)}, {texto_dax(FORMATO_DAX.get(a["formato"], "#,0.00"))}'
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
            if not _tabela_auxiliar(m, p, onde, tab, f'DATATABLE("Estado", STRING, {{ {{ {texto_dax(rotulo)} }} }})',
                                    [{'nome': 'Estado'}], f'Chave de "{nome}": ligada quando o botão está selecionado.'):
                continue
            col = dax_coluna(tab, 'Estado')
            md['dax'] = f'IF(ISFILTERED({col}), {dax_medida(lig["nome"])}, {dax_medida(des["nome"])})'
            md['formato'] = des['formato']
            if lig['formato'] != des['formato']:
                md['formato_dinamico'] = (f'IF(ISFILTERED({col}), {texto_dax(FORMATO_DAX.get(lig["formato"], "#,0.00"))}, '
                                          f'{texto_dax(FORMATO_DAX.get(des["formato"], "#,0.00"))})')
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
            tc, cc = resolver_coluna(m, cfg.get('categoria'))
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
            tc, cc = resolver_coluna(m, cfg.get('categoria'))
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
            tc, cc = resolver_coluna(m, cfg.get('categoria'))
            if not cc:
                p.erro(onde, '"categoria" precisa ser a coluna dos botões' + pista_coluna(m, cfg.get('categoria')))
                continue
            col = dax_coluna(tc['nome'], cc['nome'])
            for sufixo, fundo, texto in (('', '%23EDEBE9', '%23605E5C'), (' (ligado)', '%23' + acento[1:], '%23FFFFFF')):
                dax = svg_iniciais(col, fundo, texto)
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
            tc, cc = resolver_coluna(m, cfg.get('categoria'))
            mx, my = medida(m, cfg.get('x') or ''), medida(m, cfg.get('y') or '')
            if not cc or not mx or not my:
                p.erro(onde, '"svg_dispersao" pede "categoria" (os pontos), "x" e "y" (medidas do modelo)')
                continue
            img = cfg.get('imagem')
            img_md = medida(m, img) if img and '[' not in img else None
            ti, ci = resolver_coluna(m, img) if img and '[' in img else (None, None)
            if img and not (img_md or ci):
                p.erro(onde, '"imagem" precisa ser a coluna (ou a medida) com a imagem de cada ponto, em data:image/...')
                continue
            fonte_img = (dax_medida(img_md['nome']) if img_md else f'MAX({dax_coluna(ti["nome"], ci["nome"])})') if img else None
            md['dax'] = svg_dispersao(dax_coluna(tc['nome'], cc['nome']), dax_medida(mx['nome']), dax_medida(my['nome']),
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
            md['dax'] = html_kpis_dax(itens, acento)
            md['depende'] = [x['nome'] for x in itens] + [x['meta_medida'] for x in itens if x.get('meta_medida')]
            cfg['medidas'] = [x['nome'] for x in itens]
        elif tipo == 'svg_espinha':
            base = medida(m, cfg.get('medida') or '')
            cortes = [resolver_coluna(m, x) for x in (cfg.get('cortes') or [])]
            n = cfg.get('n', 3)
            if not base or not 2 <= len(cortes) <= 6 or not all(c for _, c in cortes):
                p.erro(onde, '"svg_espinha" pede "medida" e "cortes": de 2 a 6 colunas do modelo (uma espinha por coluna)')
                continue
            if not isinstance(n, int) or not 1 <= n <= 5:
                p.erro(onde, '"n" deve ser um número inteiro de 1 a 5 (quantos itens em cada espinha)')
                continue
            md['dax'] = svg_espinha(dax_medida(base['nome']), [(dax_coluna(t['nome'], c['nome']), c['nome']) for t, c in cortes],
                                     n, base['polaridade'] == 'maior_melhor', base['nome'], acento)
            md['depende'] = [base['nome']]
            md['polaridade'] = base['polaridade']
            cfg.update({'base': base['nome'], 'cortes': [[t['nome'], c['nome']] for t, c in cortes], 'n': n})
        conferir_funcoes(md['dax'], p, onde)
        if md.get('imagem'):                               # a dispersão e a espinha são o gráfico inteiro
            conferir_svg(md['dax'], p, onde, por_linha=tipo not in ('svg_dispersao', 'svg_espinha'))
    m['medidas'].extend(novas)


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
            alvo = medida(m, nome_meta)
            if md['tipo'] == 'divisao' and (alvo.get('dax') or '').startswith('AVERAGE('):
                p.aviso(onde, f'a meta "{nome_meta}" é a média simples das linhas: no total, "{md["nome"]}" pesa cada '
                              'item pelo tamanho dele e a meta não (a empresa de 10 pessoas vale o mesmo que a de '
                              f'5.000). Use {{"tipo": "media_ponderada", "coluna": "...", "peso": '
                              f'"{(md.get("depende") or ["", ""])[1]}", "por": "<coluna dos itens da meta>"}}')
        else:
            p.erro(onde, f'meta "{meta}" deve ser um número ou o nome de uma medida do modelo')
            continue
        nome_meta = _meta_do_periodo(m, md, nome_meta, p, onde)
        op = '>=' if md['polaridade'] == 'maior_melhor' else '<='
        cor = f'Cor {md["nome"]}'
        tol = md.get('tolerancia')
        if tol is not None and (isinstance(tol, bool) or not isinstance(tol, (int, float)) or not 0 < tol < 1):
            p.erro(onde, '"tolerancia" é a fração da meta que ainda conta como "perto" (ex.: 0.1 = até 10% do lado '
                         'ruim fica amarelo)')
            tol = None
        if tol:                                       # três faixas: bateu, perto (amarelo) e longe
            sinal = '-' if md['polaridade'] == 'maior_melhor' else '+'
            regra = (f'IF(_valor {op} _meta, "{COR_BOA}", IF(_valor {op} _meta {sinal} ABS(_meta) * {tol}, '
                     f'"{COR_ATENCAO}", "{COR_RUIM}"))')
        else:
            regra = f'IF(_valor {op} _meta, "{COR_BOA}", "{COR_RUIM}")'
        m['medidas'].append({
            'nome': cor, 'tipo': 'cor', 'formato': None, 'pasta': 'Metas', 'tabela': md['tabela'],
            'descricao': f'Cor do status de {md["nome"]} contra a meta ({md["polaridade"].replace("_", " ")}'
                         + (f'; até {tol:.0%} da meta do lado ruim fica amarelo' if tol else '') + ').',
            'dax': (f'VAR _valor = {dax_medida(md["nome"])}\nVAR _meta = {dax_medida(nome_meta)}\n'
                    f'RETURN\n    IF(\n        ISBLANK(_valor) || ISBLANK(_meta),\n        BLANK(),\n'
                    f'        {regra}\n    )'),
            'depende': [md['nome'], nome_meta], 'meta': None, 'polaridade': md['polaridade'], 'oculta': True,
            'meta_medida': None, 'cor_medida': None, 'conferencia_sql': None})
        md['meta_medida'], md['cor_medida'] = nome_meta, cor
        if not (md.get('dono') or '').strip():
            p.aviso(onde, f'quem responde por "{md["nome"]}"? Indicador com meta pede "dono" (a área ou a pessoa que '
                          'explica o número e decide a ação); vai para a ficha do dicionário')
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


AGREGACAO_X = {'soma': 'SUMX', 'media': 'AVERAGEX', 'minimo': 'MINX', 'maximo': 'MAXX', 'contagem': 'COUNTX'}


def _no_estoque(m, p):
    """`"no_estoque": "Headcount"` numa agregação do cadastro: soma (média...) só de quem está dentro no último dia do
    período, com as mesmas pontas do estoque. Sem isso, a remuneração do cadastro soma ativos e desligados."""
    for r in m['medidas']:
        cfg = r.get('no_estoque')
        if not cfg:
            continue
        onde = f'medida {r["nome"]}'
        est = medida(m, cfg['estoque'])
        if not est or not est.get('estoque'):
            p.erro(onde, f'"no_estoque" ("{cfg["estoque"]}") precisa ser uma medida estoque_na_data do modelo')
            continue
        if cfg['agregacao'] not in AGREGACAO_X:
            p.erro(onde, f'"no_estoque" vale para {", ".join(AGREGACAO_X)}')
            continue
        (t, c), (te, ce) = cfg['coluna'], est['estoque']['entradas']
        if t != te:
            p.erro(onde, f'"no_estoque": a coluna precisa ser de {te} (a tabela das entradas de {est["nome"]})')
            continue
        cal = dax_coluna(m['calendario']['tabela'], 'Data')
        corte = ref_corte(m)
        cond = [f'{dax_coluna(te, ce)} <= _fim']
        if est['estoque'].get('fim'):
            tf, cf = est['estoque']['fim']
            cond.append(f'(ISBLANK({dax_coluna(tf, cf)}) || {dax_coluna(tf, cf)} > _fim)')
        lidas = [t]
        if est['estoque'].get('saidas'):
            ts, cs = est['estoque']['saidas']
            if not any(x['de'] == ts and x['para'] == t and x['ativo'] for x in m['relacionamentos']):
                p.erro(onde, f'"no_estoque" pede a ligação ativa {ts} -> {t} (para saber quem já saiu)')
                continue
            cond.append(f'ISEMPTY(FILTER(RELATEDTABLE({dax_tabela(ts)}), {dax_coluna(ts, cs)} <= _fim))')
            lidas.append(ts)
        juntas = '\n            && '.join(cond)
        r['dax'] = (f'VAR _fim = MIN(MAX({cal}), {corte})\n'
                    f'VAR _dentro =\n    FILTER(\n        {dax_tabela(t)},\n        {juntas}\n    )\n'
                    f'RETURN\n    IF(MIN({cal}) > {corte}, BLANK(), '
                    f'{AGREGACAO_X[cfg["agregacao"]]}(_dentro, {dax_coluna(t, c)}))')
        r.pop('conferencia', None)
        r['depende'], r['le_calendario'], r['tabelas_lidas'] = [est['nome']], True, lidas


def _cadastro_inteiro(m, p):
    """Soma ou média de valor da tabela de cadastro de um estoque (ex.: remuneração em dColaborador) junta ativos
    e desligados: quase nunca é o que o gestor pensa ao ler o número."""
    cadastros = {}
    for r in m['medidas']:
        if r.get('estoque'):
            cadastros.setdefault(r['estoque']['entradas'][0], r['nome'])
    for r in m['medidas']:
        if r.get('tipo') != 'agregacao' or r.get('no_estoque') or not r.get('dax'):
            continue
        func = r['dax'].split('(')[0]
        tabs = {tn for tn, _ in referencias_dax(r['dax']) if tn}
        alvo = next((tn for tn in tabs if tn in cadastros), None)
        if alvo and func in ('SUM', 'AVERAGE'):
            p.aviso(f'medida {r["nome"]}', f'[Modelagem] "{r["nome"]}" {"soma" if func == "SUM" else "faz a média de"} '
                                           f'{alvo} inteira, ativos e desligados (o estoque "{cadastros[alvo]}" conta só '
                                           f'quem está dentro). Para só os ativos no fim do período, acrescente '
                                           f'"no_estoque": "{cadastros[alvo]}"')


def _taxa_sobre_cadastro(m, p):
    """Regra 4 do Deidara: estoque não é contagem de cadastro. Taxa de evento (desligamentos, cancelamentos) dividida
    pela contagem de uma dimensão conta ativos e desligados de todos os tempos e não muda com o período."""
    fatos = {t['nome'] for t in m['tabelas'] if t['tipo'] == 'fato'}
    for r in m['medidas']:
        if r.get('tipo') != 'divisao' or len(r.get('depende') or []) < 2:
            continue
        num, den = (medida(m, x) for x in r['depende'][:2])
        if not num or not den or den.get('tipo') != 'agregacao' or not (den.get('dax') or '').startswith('COUNTROWS('):
            continue
        dim = den.get('tabela')
        if dim in fatos or not (set(tabelas_da_medida(m, num['nome'])) & fatos):
            continue
        p.aviso(f'medida {r["nome"]}', f'[Modelagem] "{r["nome"]}" divide por "{den["nome"]}", a contagem do cadastro '
                                       f'{dim} inteiro (ativos e desligados, de todos os tempos): estoque não é '
                                       'contagem de cadastro. Use um estoque_na_data (quem está dentro no fim do mês) '
                                       'e o media_mensal dele no denominador (`deidara.py padroes turnover`)')


def _herdar_polaridade(m, brutas):
    """Conta de tempo sem polaridade própria segue a da base (desligamentos acumulados: menor é melhor)."""
    explicitas = {chave(x.get('nome') or '') for x in brutas if 'polaridade' in x}
    for _ in range(3):                             # cadeias curtas: acumulado de uma variação etc.
        for r in m['medidas']:
            if r.get('tipo') in TEMPO and chave(r['nome']) not in explicitas and r.get('depende'):
                base = medida(m, r['depende'][0])
                if base:
                    r['polaridade'] = base['polaridade']


def _medida_ponderada(m, md, r, p, onde, nomes):
    """Média de uma coluna (ex.: a meta de cada empresa) ponderada por uma medida (ex.: o HC médio de cada uma),
    item a item de `por`. É a meta do total que conversa com uma taxa: o turnover do grupo pesa cada empresa pelo
    tamanho dela, e a meta do grupo precisa pesar igual (a média simples dá o mesmo peso à empresa de 10 pessoas e à
    de 5.000)."""
    r['tipo'] = 'media_ponderada'
    t, c = resolver_coluna(m, md.get('coluna'))
    if not c or c['familia'] not in NUMERICAS:
        p.erro(onde, f'"coluna" ("{md.get("coluna")}") precisa ser uma coluna numérica do modelo (Tabela[Coluna])'
                     + (pista_coluna(m, md.get('coluna'), NUMERICAS) if md.get('coluna') else ''))
        return
    tp, cp = resolver_coluna(m, md.get('por'))
    if not cp:
        p.erro(onde, f'"por" ("{md.get("por")}") precisa ser a coluna dos itens que pesam (ex.: dEmpresa[Cód. Empresa])'
                     + (pista_coluna(m, md.get('por')) if md.get('por') else ''))
        return
    peso = md.get('peso', '')
    if chave(peso) not in nomes:
        p.erro(onde, f'"peso" "{peso}" não é uma medida do modelo' + pista_medida(peso, nomes))
        return
    if not alcanca(grafo_de_filtro(m, m.get('ligacoes_pendentes') or ()), tp['nome'], t['nome']):
        p.erro(onde, f'{tp["nome"]}[{cp["nome"]}] não filtra {t["nome"]}: cada item precisa achar a sua linha em '
                     f'{t["nome"]} (confira o relacionamento)')
        return
    r['tabela'] = md.get('tabela') or t['nome']
    r['depende'], r['tabela_da_meta'] = [peso], t['nome']
    r['dax'] = (f'VAR _itens =\n    ADDCOLUMNS(\n        VALUES({dax_coluna(tp["nome"], cp["nome"])}),\n'
                f'        "@valor", CALCULATE(AVERAGE({dax_coluna(t["nome"], c["nome"])})),\n'
                f'        "@peso", {dax_medida(peso)}\n    )\n'
                'RETURN\n    DIVIDE(\n        SUMX(_itens, [@valor] * [@peso]),\n'
                '        SUMX(FILTER(_itens, NOT ISBLANK([@valor])), [@peso])\n    )')


def _meta_do_periodo(m, md, nome_meta, p, onde):
    """Taxa de fluxo (desligamentos ÷ HC, faltas ÷ dias) cresce com o tamanho do período: o turnover de um mês é
    perto de 1/12 do anual. `"base_meta": "ano"` (ou "mes") diz a que período a meta se refere; o Deidara cria
    `<meta> no Período`, a meta proporcional aos meses do filtro (até o último dado), e compara com ela."""
    base = md.get('base_meta')
    den = medida(m, (md.get('depende') or [None, None])[1] or '') if md['tipo'] == 'divisao' else None
    fluxo = den is not None and den.get('tipo') in ('estoque_na_data', 'media_mensal')
    if base is None:
        if fluxo and m.get('calendario'):
            p.aviso(onde, f'a meta de "{md["nome"]}" é anual ou mensal? Uma taxa sobre estoque cresce com o período (a '
                          'de um mês é perto de 1/12 da anual): sem dizer, a cor compara o mês contra a meta do ano. '
                          'Use "base_meta": "ano" ou "mes" (ou "periodo", se ela vale para qualquer período)')
        return nome_meta
    if base not in ('ano', 'mes', 'periodo'):
        p.erro(onde, '"base_meta" é "ano", "mes" ou "periodo"')
        return nome_meta
    if base == 'periodo':
        return nome_meta
    if not m.get('calendario'):
        p.erro(onde, f'"base_meta": "{base}" pede "calendario" no argila.json')
        return nome_meta
    cal = m['calendario']['tabela']
    k = dax_coluna(cal, 'Ano-Mês Num')
    corte = ref_corte(m)
    nome = f'{nome_meta} no Período'
    if medida(m, nome):
        return nome
    fator = '_meses / 12' if base == 'ano' else '_meses'
    m['medidas'].append({
        'nome': nome, 'tipo': 'meta_periodo', 'formato': md['formato'], 'pasta': 'Metas', 'tabela': md['tabela'],
        'descricao': (f'{nome_meta} proporcional aos meses do filtro (meta {"anual" if base == "ano" else "mensal"}; '
                      'conta os meses até o último dado).'),
        'dax': (f'VAR _ate = YEAR({corte}) * 100 + MONTH({corte})\n'
                f'VAR _meses = COUNTROWS(FILTER(VALUES({k}), {k} <= _ate))\n'
                f'RETURN\n    {dax_medida(nome_meta)} * {fator}'),
        'depende': [nome_meta], 'meta': None, 'polaridade': md['polaridade'], 'oculta': False, 'meta_medida': None,
        'cor_medida': None, 'conferencia_sql': None, 'base': nome_meta, 'base_meta': base})
    return nome


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
    t, c = resolver_coluna(m, md.get('coluna'), md.get('tabela'))
    if not c:
        dep = depende_de(md.get('coluna')) or ((chave_coluna(md.get('tabela') or '', md.get('coluna') or ''),))
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
    if md.get('no_estoque'):                       # só de quem está dentro na data: montada depois do estoque
        r['no_estoque'] = {'estoque': md['no_estoque'], 'agregacao': ag, 'coluna': (t['nome'], c['nome'])}
        return
    if ag in ('quartil_1', 'quartil_3'):           # a faixa típica: o quartil de baixo e o de cima
        r['dax'] = f'PERCENTILE.INC({dax_coluna(t["nome"], c["nome"])}, {0.25 if ag == "quartil_1" else 0.75})'
    if ag in ('mediana', 'quartil_1', 'quartil_3'):
        return                                     # sem conferência simples em SQL (é percentil por janela)
    sql = {'soma': 'SUM(CAST({} AS decimal(38,6)))', 'media': 'AVG(CAST({} AS decimal(38,6)))', 'minimo': 'MIN({})',
           'maximo': 'MAX({})', 'contagem': 'COUNT_BIG({})', 'contagem_distinta': 'COUNT_BIG(DISTINCT {})'}[ag]
    if ag in ('minimo', 'maximo') and c['familia'] not in NUMERICAS:
        return                      # data/texto: a conferência numérica não se aplica
    r['conferencia'] = {'tabela': t['nome'], 'sql': sql.format(f'[{c["nome"]}]')}


def _medida_tempo(m, md, r, p, onde, nomes):
    r['tipo'] = md['tipo']
    base = md.get('base', '')
    if chave(base) not in nomes:
        p.erro(onde, f'base "{base}" não é uma medida do modelo' + pista_medida(base, nomes))
    if not m.get('calendario'):
        p.erro(onde, 'medida de tempo pede "calendario" no argila.json')
        return
    data = dax_coluna(m['calendario']['tabela'], 'Data')
    b = dax_medida(base)
    r['depende'] = [base]
    fim_ano = m['calendario'].get('fim_ano')                  # ano fiscal: o 3º argumento do TOTALYTD
    corte = ref_corte(m)
    # comparação justa: o período anterior para no mesmo dia em que o dado atual para (jan-out deste ano contra
    # jan-out do ano passado, e não contra o ano inteiro), o padrão "previous year up to a certain date" do SQLBI.
    # A data vem numa variável: filtro True/False com medida dentro o Power BI recusa ("função PLACEHOLDER")
    ate = f'KEEPFILTERS({data} <= _corte)'
    expr = {
        'acumulado_ano': f'TOTALYTD({b}, {data}' + (f', "{fim_ano}")' if fim_ano else ')'),
        'ano_anterior': f'CALCULATE({b}, CALCULATETABLE(SAMEPERIODLASTYEAR({data}), {ate}))',
        'variacao_ano_anterior': (f'VAR _atual = {b}\nVAR _anterior =\n    CALCULATE({b}, CALCULATETABLE('
                                  f'SAMEPERIODLASTYEAR({data}), {ate}))\nRETURN DIVIDE(_atual - _anterior, _anterior)'),
        'variacao_mes_anterior': (f'VAR _atual = {b}\nVAR _anterior =\n    CALCULATE({b}, CALCULATETABLE('
                                  f'DATEADD({data}, -1, MONTH), {ate}))\nRETURN DIVIDE(_atual - _anterior, _anterior)'),
        # média dos valores de fim de mês no período (ex.: HC médio para o turnover)
        'media_mensal': f'AVERAGEX(VALUES({dax_coluna(m["calendario"]["tabela"], "Ano-Mês")}), {b})',
        'movel_12m': f'CALCULATE({b}, DATESINPERIOD({data}, MAX({data}), -12, MONTH))',
    }[md['tipo']]
    # período depois do último dado: sem isso o acumulado repete nos meses que ainda não têm dado e a
    # variação dá -100% (atual em branco contra um ano anterior com valor)
    corpo = '\n'.join('    ' + l for l in expr.split('\n'))
    r['dax'] = f'VAR _corte = {corte}\nRETURN\n    IF(\n        MIN({data}) > _corte,\n        BLANK(),\n' + \
        '\n'.join('    ' + l for l in corpo.split('\n')) + '\n    )'


NOME_CORTE = 'Data de Corte'


def ref_corte(m):
    """A data até onde há dado: as contas de tempo param nela. Por padrão, a última data com registro nas datas do
    calendário (e nas de entrada e saída dos estoques), nunca depois de hoje; `"corte": "hoje"` no calendário usa
    a data de hoje (fonte atualizada todo dia, sem atraso)."""
    if m['calendario'].get('corte') == 'hoje':
        return 'TODAY()'
    m['_usa_corte'] = True
    return dax_medida(NOME_CORTE)


def _colunas_do_corte(m):
    colunas = [(d['tabela'], d['coluna']) for d in m['calendario']['datas'] if d['ativo']]
    for md in m['medidas']:
        for ponta in ('entradas', 'saidas', 'fim'):
            x = (md.get('estoque') or {}).get(ponta)
            if x and tuple(x) not in colunas:
                colunas.append(tuple(x))
    return colunas


def _ultima_data(colunas):
    maiores = [f'CALCULATE(MAX({dax_coluna(t, c)}), REMOVEFILTERS())' for t, c in colunas]
    return ('BLANK()' if not maiores else maiores[0] if len(maiores) == 1
            else 'MAXX({ ' + ', '.join(maiores) + ' }, [Value])')


def corte_sem_medida(m):
    """A data de corte escrita por extenso, sem citar a medida: é a que vai dentro do grupo de cálculo. Medida citada
    num item de cálculo recebe o próprio item de novo (recursão lateral), e o Power BI recusa ou erra a conta."""
    if m['calendario'].get('corte') == 'hoje':
        return 'TODAY()'
    ultima = _ultima_data(_colunas_do_corte(m))
    return f'MIN(TODAY(), COALESCE({ultima}, TODAY()))'


def garantir_corte(m, p):
    """Cria a medida oculta `Data de Corte` quando alguma conta de tempo a usa."""
    if not m.pop('_usa_corte', False):
        return
    colunas = _colunas_do_corte(m)
    if any(chave(x['nome']) == chave(NOME_CORTE) for x in m['medidas']):
        p.erro(f'medida {NOME_CORTE}', f'"{NOME_CORTE}" é o nome da medida que o Deidara cria para as contas de '
                                       'tempo: renomeie a sua')
        return
    ultima = _ultima_data(colunas)
    m['medidas'].append({
        'nome': NOME_CORTE, 'tipo': 'corte', 'formato': 'data', 'pasta': 'Apoio', 'tabela': m['calendario']['tabela'],
        'descricao': 'Último dia com dado (nunca depois de hoje): as contas de tempo param nele e o ano anterior '
                     'é comparado até o mesmo dia.',
        'dax': f'VAR _ultima = {ultima}\nRETURN\n    IF(ISBLANK(_ultima) || _ultima > TODAY(), TODAY(), _ultima)',
        'depende': [], 'meta': None, 'polaridade': 'maior_melhor', 'oculta': True, 'meta_medida': None,
        'cor_medida': None, 'conferencia_sql': None, 'tabelas_lidas': sorted({t for t, _ in colunas}),
        'le_calendario': False})


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
    te, ce = resolver_coluna(m, md.get('entradas'))
    datas = ('data', 'datahora')
    if md.get('saidas'):                                   # as duas pontas no mesmo relatório, não uma por vez
        ts0, cs0 = resolver_coluna(m, md['saidas'])
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
        tf, cf = resolver_coluna(m, md['fim'])
        if not cf or tf['nome'] != te['nome'] or cf['familia'] not in ('data', 'datahora'):
            p.erro(onde, '"fim" precisa ser uma coluna de data da mesma tabela das entradas')
            return
        fim_ref = (f',\n        OR(ISBLANK({dax_coluna(tf["nome"], cf["nome"])}), '
                   f'{dax_coluna(tf["nome"], cf["nome"])} > _fim)')
    corte = ref_corte(m)                    # admissão marcada para o futuro não entra no estoque de hoje
    dax = (f'VAR _fim = MIN(MAX({dax_coluna(cal, "Data")}), {corte})\nVAR _entradas =\n    CALCULATE(\n'
           f'        COUNTROWS({dax_tabela(te["nome"])}),\n        {dax_coluna(te["nome"], ce["nome"])} <= _fim{fim_ref},\n'
           f'        REMOVEFILTERS({dax_tabela(cal)})\n    )\n')
    if md.get('saidas'):
        ts, cs = resolver_coluna(m, md['saidas'])
        if not cs or cs['familia'] not in ('data', 'datahora'):
            return                                          # já relatado acima
        if not alcanca(grafo_de_filtro(m), te['nome'], ts['nome']):
            p.aviso(onde, f'{te["nome"]} não filtra {ts["nome"]}: um corte por {te["nome"]} vai tirar as saídas de '
                          'todo mundo; confira o relacionamento')
        lidas.append(ts['nome'])
        dax += (f'VAR _saidas =\n    CALCULATE(\n        COUNTROWS({dax_tabela(ts["nome"])}),\n'
                f'        {dax_coluna(ts["nome"], cs["nome"])} <= _fim,\n        REMOVEFILTERS({dax_tabela(cal)})\n    )\n'
                'RETURN\n    IF(MIN(' + dax_coluna(cal, 'Data') + f') > {corte}, BLANK(), _entradas - _saidas)')
    else:
        dax += 'RETURN\n    IF(MIN(' + dax_coluna(cal, 'Data') + f') > {corte}, BLANK(), _entradas)'
    r['estoque'] = {'entradas': (te['nome'], ce['nome']),
                    'fim': (tf['nome'], cf['nome']) if md.get('fim') else None,
                    'saidas': (ts['nome'], cs['nome']) if md.get('saidas') else None}
    r['dax'], r['tabela'] = dax, md.get('tabela') or te['nome']
    r['tabelas_lidas'], r['le_calendario'], r['depende'] = lidas, True, []


def _conferir_refs(m, r, nomes, p, onde):
    for problema in sintaxe_dax(r['dax']):
        p.erro(onde, f'DAX mal escrito: {problema}')
    if r.get('pasta') != 'C0 · antes':        # a fórmula antiga fica como era, só para a homologação comparar
        for regra, conselho in boas_praticas_dax(r['dax']):
            p.aviso(onde, f'[Power BI] boa prática ({regra}): {conselho}')
    import re as _re
    for lit in _re.findall(r'"((?:[^"]|"")*)"', r['dax']):
        if _re.search(r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b', lit) or _re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', lit):
            p.aviso(onde, '[Privacidade] CPF ou e-mail escrito no DAX: vai junto para quem abre o modelo; filtre por '
                          'código ou grupo (LGPD: só o necessário)')
            break
    conferir_funcoes(r['dax'], p, onde)
    deps = []
    for tn, n in referencias_dax(r['dax']):
        if tn:
            t = tabela_do_modelo(m, tn)
            if not t:
                p.erro(onde, f'tabela "{tn}" do DAX não está no modelo')
            elif not coluna_do_modelo(t, n) and chave(n) not in nomes:
                p.erro(onde, f'coluna "{tn}[{n}]" do DAX não está no modelo', depende=depende_de(f'{tn}[{n}]'))
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


def _c4(m, p):
    """C4 Karura (tecnicas/c4.py): o gráfico de controle (centro, limites, sinal e a meta x faixa) e o fora da
    curva. O tipo do gráfico sai da medida: taxa em percentual vira gráfico p, outra divisão vira gráfico u, e o
    resto, XmR."""
    from tecnicas import c4
    novas = []
    for md in m['medidas']:
        if md.get('tipo') not in ('controle', 'fora_da_curva'):
            continue
        cfg, onde, nome = md['extra'], f'medida {md["nome"]}', md['nome']
        base = medida(m, cfg.get('medida') or '')
        if not base:
            p.erro(onde, f'"medida" ("{cfg.get("medida")}") não é uma medida do modelo')
            continue
        b = dax_medida(base['nome'])
        num, den = (base.get('depende') or [None, None])[:2] if base.get('tipo') == 'divisao' else (None, None)
        proporcao = base.get('tipo') == 'divisao' and base.get('formato') == 'percentual'
        md['polaridade'] = base['polaridade']
        if md['tipo'] == 'controle':
            cal = (m.get('calendario') or {}).get('tabela')
            if not cal:
                p.erro(onde, 'o gráfico de controle pede "calendario" no argila.json (um ponto por mês)')
                continue
            tipo = cfg.get('grafico') or ('p' if proporcao else 'u' if base.get('tipo') == 'divisao' else 'xmr')
            if tipo not in ('xmr', 'p', 'u') or (tipo != 'xmr' and not num):
                p.erro(onde, '"grafico" deve ser xmr, p ou u (p e u pedem uma medida de divisão)')
                continue
            dn, dd = (dax_medida(num), dax_medida(den)) if tipo != 'xmr' else (None, None)
            dep = [base['nome']] + ([num, den] if tipo != 'xmr' else [])
            ref = _referencia(cfg.get('referencia'), p, onde)
            if ref is False:
                continue
            md.update({'dax': c4.dax_controle('centro', b, dax_tabela(cal), tipo, dn, dd, ref), 'formato': base['formato'],
                       'depende': list(dep)})
            textos = {'superior': 'Limite superior do gráfico de controle de ',
                      'inferior': 'Limite inferior do gráfico de controle de ',
                      'sinal': 'Sinal do gráfico de controle (1 fora do limite, 2 oito do mesmo lado da média, '
                               '3 seis na mesma direção) de '}
            partes = {'superior': f'{nome} · limite superior', 'inferior': f'{nome} · limite inferior',
                      'sinal': f'{nome} · sinal'}
            for parte, nome_parte in partes.items():
                novas.append(_derivada(md, nome_parte, c4.dax_controle(parte, b, dax_tabela(cal), tipo, dn, dd, ref),
                                       'inteiro' if parte == 'sinal' else base['formato'], dep,
                                       textos[parte] + base['nome'] + '.', oculta=parte == 'sinal'))
            if base.get('meta_medida'):
                partes['meta'] = f'{nome} · meta x faixa'
                # a faixa é de UM mês: a meta proporcional ao período vira a meta de um mês (a anual ÷ 12)
                mp = medida(m, base['meta_medida'])
                meta_mes = (f'{dax_medida(mp["base"])}' + (' / 12' if mp.get('base_meta') == 'ano' else '')
                            if mp and mp.get('tipo') == 'meta_periodo' else dax_medida(base['meta_medida']))
                novas.append(_derivada(md, partes['meta'], c4.dax_meta_x_faixa(
                    b, meta_mes, dax_tabela(cal), tipo, base['polaridade'] == 'maior_melhor',
                    base['formato'], dn, dd, ref), None, dep + [base['meta_medida']],
                    f'Se a meta de {base["nome"]} cabe na faixa normal do processo.'))
            cfg.update({'base': base['nome'], 'grafico': tipo, 'partes': partes, 'numerador': num,
                        'denominador': den, 'calendario': cal, 'periodo_referencia': ref})
            p.aviso(onde, f'[Design] o gráfico de controle precisa de uns {c4.PONTOS_MINIMOS} meses para os limites '
                          'valerem (NIST 6.3.2): com menos, leia os limites como provisórios')
        else:
            tc, cc = resolver_coluna(m, cfg.get('categoria'))
            if not cc:
                p.erro(onde, '"categoria" precisa ser a coluna dos itens (Tabela[Coluna])'
                       + pista_coluna(m, cfg.get('categoria')))
                continue
            col = dax_coluna(tc['nome'], cc['nome'])
            funil = bool(proporcao and num)
            md.update({'dax': c4.dax_fora_da_curva(b, col, funil, dax_medida(num) if funil else None,
                                                   dax_medida(den) if funil else None),
                       'formato': 'decimal', 'depende': [base['nome']] + ([num, den] if funil else [])})
            limiar = c4.LIMIAR_FUNIL if funil else c4.LIMIAR_Z_MODIFICADO
            cor = f'Cor {nome}'
            acento = (m['tema']['cores'] or ['#118DFF'])[0]
            ref = dax_medida(nome)
            novas.append(_derivada(md, cor, f'IF(ISBLANK({ref}), BLANK(), IF(ABS({ref}) > {limiar}, "{COR_RUIM}", '
                                            f'"{acento}"))', None, [nome],
                                   f'Vermelho para o item fora da curva em {base["nome"]}.', tipo='cor', oculta=True))
            md['cor_medida'] = cor
            cfg.update({'base': base['nome'], 'tabela': tc['nome'], 'coluna': cc['nome'], 'funil': funil,
                        'limiar': limiar, 'numerador': num, 'denominador': den})
        conferir_funcoes(md['dax'], p, onde)
        for x in sintaxe_dax(md['dax']):
            p.erro(onde, f'DAX gerado mal escrito ({x}): avise o time do Deidara')
    m['medidas'].extend(novas)


def _referencia(cfg, p, onde):
    """`"referencia": {"de": "2023-01", "ate": "2023-12"}` -> (202301, 202312); None sem referência; False se
    inválida (já relatado)."""
    if not cfg:
        return None
    try:
        de, ate = (int(str(cfg[k]).replace('-', '')) for k in ('de', 'ate'))
        if not (190001 <= de <= ate <= 299912 and 1 <= de % 100 <= 12 and 1 <= ate % 100 <= 12):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        p.erro(onde, '"referencia" é {"de": "AAAA-MM", "ate": "AAAA-MM"} (o período de onde saem os limites)')
        return False
    if (ate // 100 * 12 + ate % 100) - (de // 100 * 12 + de % 100) + 1 < 20:
        p.aviso(onde, '[Design] o período de referência tem menos de 20 meses: os limites ainda são provisórios '
                      '(NIST 6.3.2)')
    return de, ate


def _derivada(md, nome, dax, formato, depende, descricao, tipo='c4', oculta=False):
    return {'nome': nome, 'tipo': tipo, 'formato': formato, 'pasta': md.get('pasta') or 'Estatística',
            'tabela': md['tabela'], 'dax': dax, 'depende': list(depende), 'descricao': descricao, 'meta': None,
            'polaridade': md.get('polaridade', 'maior_melhor'), 'oculta': oculta, 'meta_medida': None,
            'cor_medida': None, 'conferencia_sql': None, 'extra': {'de': md['nome']}}
