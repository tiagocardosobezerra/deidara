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


from tecnicas.luneta import prova

from kibaku_nendo.util import (FORMATOS, SQL_POR_FAMILIA, chave, sql_tipo)
from kibaku_nendo.medidas import resolver_medidas
from kibaku_nendo.paginas import (conferir_design, resolver_grupo_calculo, resolver_layout, resolver_paginas,
                                  resolver_tours)
# a API pública do motor continua saindo daqui (quem já importa de kibaku_nendo.especificacao)
from kibaku_nendo.desenhos import (COR_BOA, COR_ESTRELA, COR_MARCA, COR_RUIM, COR_TRILHO, ESTRELA, FORMATO_DAX,
                                   PREFIXO_SVG, conferir_svg, html_kpis_dax, literais_dax, svg_barra_meta,
                                   svg_bolha, svg_dispersao, svg_espinha, svg_estrelas, svg_iniciais,
                                   svg_pilula, svg_posicao, svg_progresso, svg_radar, svg_seta, svg_variacao,
                                   texto_dax, texto_svg)  # noqa: F401
from kibaku_nendo.modelo import (AGREGACOES, AGREGACOES_NUMERICAS, CALENDARIO_OCULTAS, CALENDARIO_SEM_ANO,
                                 COLUNAS_CALENDARIO, COR_APAGADA, DIAGNOSTICOS, EXTRAS,
                                 LIMITE_VISUAIS_POR_PAGINA, Problemas, RANKINGS, SEGMENTADORES, SVG_GERADAS,
                                 TEMPO, TIPOS_TABELA, TIPOS_VISUAL, VISUAIS_DE_TERCEIROS, alcanca, alcance,
                                 campo_do_modelo, chave_coluna, chave_tabela, chega, coluna_do_modelo,
                                 coluna_por_origem, conferir_funcoes, depende_de, distorcoes,
                                 familia_declarada, grafo_de_filtro, le_calendario, medida, medidas_do_visual,
                                 nova_coluna, pista_coluna, pista_medida, referencias_dax, resolver_coluna,
                                 sintaxe_dax, tabela_do_modelo, tabelas_da_medida)  # noqa: F401


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
                           '#D64550'], 'fundo': '#FFFFFF', 'texto': '#252423',
                 **{k: v for k, v in (argila.get('tema') if isinstance(argila.get('tema'), dict) else {}).items()
                    if k != 'paleta'}},
        'tabelas': [], 'relacionamentos': [], 'medidas': [], 'paginas': [], 'seguranca': [], 'pendencias': [],
    }
    if not m['projeto']:
        p.erro('projeto', 'informe o nome do projeto')
    resolver_layout(argila, m, p)
    _tabelas(argila, catalogos, m, p)
    _calendario(argila, m, p)
    _relacionamentos(argila, catalogos, m, p)
    resolver_medidas(argila, m, p)
    resolver_grupo_calculo(argila, m, p)
    _seguranca(argila, m, p)
    resolver_paginas(argila, m, p)
    _privacidade(m, p)
    conferir_design(argila, m, p)
    resolver_tours(m, p)
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
    from kibaku_nendo.privacidade import pessoal as _pessoal
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
            conferir_funcoes(r['filtro'], p, f'{onde} regra {j + 1}')
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
            familia = familia_declarada(oc)
            if c.get('tipo'):
                familia = c['tipo']
            elif not familia or oc.get('tipo_indefinido'):
                familia = 'texto'
                p.aviso(ondec, f'{origem["nome"]}.{oc["coluna"]} veio sem tipo da fonte {fonte.nome}: tratada como '
                               'texto; defina o tipo na consulta de origem ou informe "tipo" aqui')
            col = nova_coluna(c.get('nome') or oc['coluna'], oc['coluna'], familia,
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
        c = nova_coluna(n, None, fam, formato=fmt)
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
                   depende=depende_de(f'{d.get("tabela")}[{d.get("coluna")}]'))
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
    c = nova_coluna(oc.get('coluna', origem), oc.get('coluna', origem), familia_declarada(oc) or 'texto',
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
    c = nova_coluna(nome, None, 'texto', descricao='Chave composta gerada pelo Deidara: ' + ' + '.join(campos),
                oculta=True, expressao_sql=expr)
    c['chave_campos'] = list(campos)
    t['colunas'].append(c)
    return nome


def _parte_da_chave(catalogos, t, campo):
    """Um campo da chave composta como texto estável: data em ISO (independe do
    idioma da sessão), sem espaço à direita (char) e NULL marcado (senão NULL e
    '' viram a mesma chave)."""
    familia = familia_declarada(catalogos[t['fonte']].coluna(t['origem'], campo) or {})
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


