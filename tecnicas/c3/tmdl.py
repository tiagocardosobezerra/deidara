"""
O modelo semântico do Power BI em TMDL (pasta `<Projeto>.SemanticModel`).

TMDL é o formato texto do modelo tabular que o Power BI Desktop abre num
projeto .pbip: um arquivo por tabela, indentado por tabulação.

Cada tabela lê da sua fonte:
- sqlserver: a view gerada (`sql.py`), por dois parâmetros da fonte
  (<fonte>_Servidor e <fonte>_Banco), trocados em "Editar parâmetros";
- powerbi / powerquery: a PRÓPRIA consulta Power Query que o usuário já usa
  (Excel, SharePoint, API...), vinda do catálogo; o Deidara só acrescenta a
  seleção e o nome das colunas, os tipos e as chaves compostas. Parâmetros e
  consultas auxiliares que ela usa vêm junto (expressions.tmdl).
"""

import os

from tecnicas.c3.sql import nome_view  # noqa: F401  (documenta a ligação tabela -> view)
from kibaku_nendo.util import FORMATOS, M_POR_FAMILIA, gravar_json, gravar_texto, guid, ident, m_texto, tmdl_nome

COMPATIBILIDADE = 1567


def _desc(texto, nivel):
    if not texto:
        return ''
    tab = '\t' * nivel
    return ''.join(f'{tab}/// {linha.strip()}\n' for linha in str(texto).splitlines() if linha.strip())


def _expressao(texto, nivel):
    """Expressão de várias linhas: um nível a mais que a propriedade."""
    tab = '\t' * nivel
    return '\n'.join(tab + linha for linha in texto.splitlines())


def parametros(fonte):
    p = ident(fonte['nome'], 'f')
    return f'{p}_Servidor', f'{p}_Banco'


def _m_campo(nome):
    return '[#' + m_texto(nome) + ']'


def _m_lista(itens):
    return '{' + ', '.join(itens) + '}'


def _m_sobre_consulta(t):
    """A consulta do usuário + seleção, nomes, tipos e chaves compostas."""
    origem = '\n'.join('        ' + l for l in t['expressao_m'].strip().splitlines())
    passos, ant = [f'    Origem =\n{origem}'], 'Origem'
    for c in [c for c in t['colunas'] if c.get('chave_campos')]:
        partes = ', '.join(f'if {_m_campo(f)} = null then "∅" else Text.Trim(Text.From({_m_campo(f)}))'
                           for f in c['chave_campos'])
        nome = 'Chave' + str(len(passos))
        passos.append(f'    {nome} = Table.AddColumn({ant}, {m_texto(c["nome"])}, each Text.Combine({{{partes}}}, "|"), '
                      'type text)')
        ant = nome
    sel = [m_texto(c['nome'] if c.get('chave_campos') else c['origem']) for c in t['colunas']]
    passos.append(f'    Colunas = Table.SelectColumns({ant}, {_m_lista(sel)})')
    ren = [_m_lista([m_texto(c['origem']), m_texto(c['nome'])]) for c in t['colunas']
           if not c.get('chave_campos') and c['origem'] != c['nome']]
    ant = 'Colunas'
    if ren:
        passos.append(f'    Nomes = Table.RenameColumns(Colunas, {_m_lista(ren)})')
        ant = 'Nomes'
    tipos = [_m_lista([m_texto(c['nome']), M_POR_FAMILIA.get(c['familia'], 'type text')]) for c in t['colunas']]
    passos.append(f'    Tipos = Table.TransformColumnTypes({ant}, {_m_lista(tipos)})')
    return 'let\n' + ',\n'.join(passos) + '\nin\n    Tipos'


def _particao(m, t):
    if t.get('calendario'):
        return _particao_calendario(m, t)
    if t.get('calculada'):                          # tabela auxiliar do Deidara, em DAX (opções, chave, cópia solta)
        return f'\tpartition {tmdl_nome(t["nome"])} = calculated\n\t\tmode: import\n\t\tsource = {t["calculada"]}\n'
    fonte = m['fontes'][t['fonte']]
    if (m.get('_demo') or {}).get(t['nome']):        # demonstração: linhas fictícias no próprio projeto (demo.py)
        m_expr = m['_demo'][t['nome']]
    elif fonte['tipo'] == 'sqlserver':
        serv, banco = parametros(fonte)
        m_expr = (f'let\n    Fonte = Sql.Database({serv}, {banco}),\n'
                  f'    Dados = Fonte{{[Schema={m_texto(fonte["esquema_views"])}, Item={m_texto("vw_" + t["nome"])}]}}[Data]\n'
                  f'in\n    Dados')
    else:
        m_expr = _m_sobre_consulta(t)
    return (f'\tpartition {tmdl_nome(t["nome"])} = m\n\t\tmode: import\n\t\tsource =\n{_expressao(m_expr, 4)}\n')


def _particao_calendario(m, t):
    fim = ('Date.EndOfYear(Date.From(DateTime.LocalNow()))' if t.get('fim_dinamico')   # acompanha o ano corrente
           else f'#date({t["fim"]}, 12, 31)')
    mf = t.get('mes_fiscal', 1)
    fiscal = ('' if mf == 1 else
              f',\n    AnoFiscal = Table.AddColumn(AnoTriNum, "Ano Fiscal", each [Ano] + (if [Mês] >= {mf} then 1 else 0), '
              'Int64.Type),\n    MesFiscal = Table.AddColumn(AnoFiscal, "Mês Fiscal", each Number.Mod([Mês] - '
              f'{mf} + 12, 12) + 1, Int64.Type)')
    m_expr = f'''let
    Inicio = #date({t["inicio"]}, 1, 1),
    Fim = {fim},
    Datas = List.Dates(Inicio, Duration.Days(Fim - Inicio) + 1, #duration(1, 0, 0, 0)),
    Base = Table.FromList(Datas, Splitter.SplitByNothing(), {{"Data"}}),
    Tipada = Table.TransformColumnTypes(Base, {{{{"Data", type date}}}}),
    Ano = Table.AddColumn(Tipada, "Ano", each Date.Year([Data]), Int64.Type),
    Mes = Table.AddColumn(Ano, "Mês", each Date.Month([Data]), Int64.Type),
    NomeMes = Table.AddColumn(Mes, "Nome do Mês", each {{"jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"}}{{[Mês] - 1}}, type text),
    Tri = Table.AddColumn(NomeMes, "Trimestre", each "T" & Text.From(Date.QuarterOfYear([Data])), type text),
    AnoMes = Table.AddColumn(Tri, "Ano-Mês", each Text.From([Ano]) & "-" & Text.PadStart(Text.From([Mês]), 2, "0"), type text),
    MesAno = Table.AddColumn(AnoMes, "Mês/Ano", each [Nome do Mês] & "/" & Text.From([Ano]), type text),
    AnoTri = Table.AddColumn(MesAno, "Ano-Trimestre", each Text.From([Ano]) & "-" & [Trimestre], type text),
    AnoMesNum = Table.AddColumn(AnoTri, "Ano-Mês Num", each [Ano] * 100 + [Mês], Int64.Type),
    AnoTriNum = Table.AddColumn(AnoMesNum, "Ano-Trimestre Num", each [Ano] * 10 + Date.QuarterOfYear([Data]), Int64.Type){fiscal}'''
    ultimo = 'AnoTriNum' if mf == 1 else 'MesFiscal'
    if t.get('feriados'):
        m_expr += ',\n' + _passos_feriados(t['feriados'], ultimo)
        ultimo = 'DiaUtil'
    m_expr += f'\nin\n    {ultimo}'
    return f'\tpartition {tmdl_nome(t["nome"])} = m\n\t\tmode: import\n\t\tsource =\n{_expressao(m_expr, 4)}\n'


# Páscoa (algoritmo de Meeus/Jones/Butcher) e as regras do modelo de feriados do Bravo (SQLBI, MIT): data fixa,
# Páscoa + dias (M = 99) ou o n-ésimo dia da semana do mês (S = dia da semana, 0 = domingo; O = semana, negativa
# conta do fim do mês).
_FERIADOS_M = '''    Pascoa = (a as number) as date =>
        let
            g = Number.Mod(a, 19),
            c = Number.IntegerDivide(a, 100),
            h = Number.Mod(c - Number.IntegerDivide(c, 4) - Number.IntegerDivide(8 * c + 13, 25) + 19 * g + 15, 30),
            i = h - Number.IntegerDivide(h, 28) * (1 - Number.IntegerDivide(h, 28) * Number.IntegerDivide(29, h + 1) * Number.IntegerDivide(21 - g, 11)),
            j = Number.Mod(a + Number.IntegerDivide(a, 4) + i + 2 - c + Number.IntegerDivide(c, 4), 7),
            l = i - j,
            mes = 3 + Number.IntegerDivide(l + 40, 44),
            dia = l + 28 - 31 * Number.IntegerDivide(mes, 4)
        in
            #date(a, mes, dia),
    DataDaRegra = (a as number, r as record) as date =>
        if r[M] = 99 then Date.AddDays(Pascoa(a), r[D])
        else if r[S] = 0 then Date.AddDays(#date(a, r[M], r[D]), r[X])
        else if r[O] > 0 then
            let p = #date(a, r[M], 1) in
                Date.AddDays(p, Number.Mod(r[S] - Date.DayOfWeek(p, Day.Sunday) + 7, 7) + 7 * (r[O] - 1) + r[X])
        else
            let u = Date.EndOfMonth(#date(a, r[M], 1)) in
                Date.AddDays(u, - Number.Mod(Date.DayOfWeek(u, Day.Sunday) - r[S] + 7, 7) + 7 * (r[O] + 1) + r[X]),
    Anos = {Date.Year(Inicio)..Date.Year(Fim)},
    ListaFeriados = List.Combine(List.Transform(Anos, (a) => List.Transform(Regras, (r) => [Data = DataDaRegra(a, r), Nome = r[N]]))),
    TabelaFeriados = Table.Group(Table.TransformColumnTypes(Table.FromRecords(ListaFeriados), {{"Data", type date}}), {"Data"}, {{"Nome", each Text.Combine(List.Distinct([Nome]), " / "), type text}}),
    ComFeriado = Table.NestedJoin(ULTIMO, {"Data"}, TabelaFeriados, {"Data"}, "F", JoinKind.LeftOuter),
    Feriado = Table.AddColumn(ComFeriado, "Feriado", each if Table.IsEmpty([F]) then null else [F]{0}[Nome], type text),
    DiaUtil = Table.AddColumn(Table.RemoveColumns(Feriado, {"F"}), "Dia Útil", each Date.DayOfWeek([Data], Day.Monday) < 5 and [Feriado] = null, type logical)'''


def _passos_feriados(regras, ultimo):
    lista = ', '.join(f'[M = {r["MonthNumber"]}, D = {r["DayNumber"]}, S = {r.get("WeekDayNumber", 0)}, '
                      f'O = {r.get("OffsetWeek", 0)}, X = {r.get("OffsetDays", 0)}, N = {m_texto(r["HolidayName"])}]'
                      for r in regras)
    return f'    Regras = {{{lista}}},\n' + _FERIADOS_M.replace('ULTIMO', ultimo)


ORDENAR_POR = {'Nome do Mês': 'Mês', 'Mês/Ano': 'Ano-Mês Num', 'Ano-Trimestre': 'Ano-Trimestre Num'}


def _grupo_calculo(t):
    """Tabela de grupo de cálculo: um item por conta de tempo, o nome e a ordem como colunas."""
    g = t['grupo_calculo']
    nome, ordem = t['colunas'][0]['nome'], t['colunas'][1]['nome']
    linhas = [_desc(t['descricao'], 0) + f'table {tmdl_nome(t["nome"])}', f'\tlineageTag: {guid("tabela", t["nome"])}', '',
              '\tcalculationGroup', f'\t\tprecedence: {g["precedencia"]}', '']
    for it in g['itens']:
        dax = it['dax']
        cab = (f'\t\tcalculationItem {tmdl_nome(it["rotulo"])} =\n{_expressao(dax, 4)}' if '\n' in dax
               else f'\t\tcalculationItem {tmdl_nome(it["rotulo"])} = {dax}')
        props = [f'\t\t\tordinal: {it["ordem"]}']
        if it['formato']:
            props += ['', f'\t\t\tformatStringDefinition = {it["formato"]}']
        linhas.append(cab + '\n' + '\n'.join(props) + '\n')
    linhas.append(f'\tcolumn {tmdl_nome(nome)}\n\t\tdataType: string\n\t\tlineageTag: {guid("coluna", t["nome"], nome)}\n'
                  f'\t\tsummarizeBy: none\n\t\tsourceColumn: Name\n\t\tsortByColumn: {tmdl_nome(ordem)}\n\n'
                  '\t\tannotation SummarizationSetBy = Automatic\n')
    linhas.append(f'\tcolumn {tmdl_nome(ordem)}\n\t\tdataType: int64\n\t\tformatString: 0\n\t\tisHidden\n'
                  f'\t\tlineageTag: {guid("coluna", t["nome"], ordem)}\n\t\tsummarizeBy: sum\n\t\tsourceColumn: Ordinal\n\n'
                  '\t\tannotation SummarizationSetBy = Automatic\n')
    linhas.append(f'\tpartition {tmdl_nome(t["nome"])} = calculationGroup\n\t\tmode: import\n')
    return '\n'.join(linhas)


def tabela(m, t):
    if t.get('grupo_calculo'):
        return _grupo_calculo(t)
    linhas = [_desc(t['descricao'], 0) + f'table {tmdl_nome(t["nome"])}',
              f'\tlineageTag: {guid("tabela", t["nome"])}', '']
    if t.get('calendario'):
        linhas.insert(2, '\tdataCategory: Time')
    for md in [x for x in m['medidas'] if x['tabela'] == t['nome']]:
        dax = md['dax']
        if '\n' in dax:
            cab = f'\tmeasure {tmdl_nome(md["nome"])} =\n{_expressao(dax, 3)}'
        else:
            cab = f'\tmeasure {tmdl_nome(md["nome"])} = {dax}'
        props = [f'\t\tformatString: {FORMATOS[md["formato"]]}'] if md['formato'] else []
        if md.get('formato_dinamico'):               # o formato muda com a opção escolhida (vai no fim)
            props = []
        if md.get('oculta'):
            props.append('\t\tisHidden')
        if md.get('imagem'):
            props.append('\t\tdataCategory: ImageUrl')
        if md['pasta']:
            props.append(f'\t\tdisplayFolder: {md["pasta"]}')
        props.append(f'\t\tlineageTag: {guid("medida", md["nome"])}')
        if md['formato'] == 'moeda' and not md.get('formato_dinamico'):
            props.append('')
            props.append('\t\tannotation PBI_FormatHint = {"currencyCulture":"pt-BR"}')
        if md.get('formato_dinamico'):
            props += ['', f'\t\tformatStringDefinition = {md["formato_dinamico"]}']
        linhas.append(_desc(md['descricao'], 1) + cab + '\n' + '\n'.join(props) + '\n')
    for c in t['colunas']:
        props = [f'\t\tdataType: {c["tipo_tmdl"]}']
        if c['formato']:
            props.append(f'\t\tformatString: {FORMATOS[c["formato"]]}')
        elif c['tipo_tmdl'] == 'int64':
            props.append('\t\tformatString: 0')
        if c['oculta']:
            props.append('\t\tisHidden')
        if t.get('calendario') and c['nome'] == 'Data':
            props.append('\t\tisKey')
        props.append(f'\t\tlineageTag: {guid("coluna", t["nome"], c["nome"])}')
        props.append('\t\tsummarizeBy: none')
        props.append(f'\t\tsourceColumn: [{c["nome"]}]' if t.get('calculada') else f'\t\tsourceColumn: {c["nome"]}')
        if c['nome'] in ORDENAR_POR and t.get('calendario'):
            props.append(f'\t\tsortByColumn: {tmdl_nome(ORDENAR_POR[c["nome"]])}')
        if c.get('ordenar_por'):
            props.append(f'\t\tsortByColumn: {tmdl_nome(c["ordenar_por"])}')
        props.append('')
        props.append('\t\tannotation SummarizationSetBy = User')
        if c['familia'] == 'data':
            props.append('')
            props.append('\t\tannotation UnderlyingDateTimeDataType = Date')
        linhas.append(_desc(c['descricao'], 1) + f'\tcolumn {tmdl_nome(c["nome"])}\n' + '\n'.join(props) + '\n')
    linhas.append(_particao(m, t))
    return '\n'.join(linhas)


def relacionamentos(m):
    out = []
    for r in m['relacionamentos']:
        linhas = [f'relationship {guid("rel", r["de"], r["de_coluna"], r["para"], r["para_coluna"])}']
        if not r['ativo']:
            linhas.append('\tisActive: false')
        linhas.append(f'\tfromColumn: {tmdl_nome(r["de"])}.{tmdl_nome(r["de_coluna"])}')
        linhas.append(f'\ttoColumn: {tmdl_nome(r["para"])}.{tmdl_nome(r["para_coluna"])}')
        out.append('\n'.join(linhas) + '\n')
    return '\n'.join(out)


def _parametro(nome, valor):
    return (f'expression {tmdl_nome(nome)} = {m_texto(valor)} meta [IsParameterQuery=true, Type="Text", '
            f'IsParameterQueryRequired=true]\n\tlineageTag: {guid("param", nome)}\n\n'
            f'\tannotation PBI_ResultType = Text\n')


def expressoes_compartilhadas(m):
    """{nome: expressão M} das consultas auxiliares e parâmetros das fontes Power Query."""
    out = {}
    for f in m['fontes'].values():
        if f['tipo'] == 'sqlserver' or not any(t.get('fonte') == f['nome'] for t in m['tabelas']):
            continue
        out.update(f.get('expressoes') or {})
    return out


def expressoes(m):
    blocos = []
    for f in m['fontes'].values():
        if f['tipo'] == 'sqlserver' and any(t.get('fonte') == f['nome'] for t in m['tabelas']):
            serv, banco = parametros(f)
            blocos += [_parametro(serv, f['servidor']), _parametro(banco, f['banco'])]
    for nome, expr in sorted(expressoes_compartilhadas(m).items()):
        expr = expr.strip()
        if '\n' in expr:
            corpo = f'expression {tmdl_nome(nome)} =\n{_expressao(expr, 2)}'
        else:
            corpo = f'expression {tmdl_nome(nome)} = {expr}'
        blocos.append(f'{corpo}\n\tlineageTag: {guid("expr", nome)}\n')
    return '\n'.join(blocos)


def _ordem(m):
    nomes = []
    for f in m['fontes'].values():
        if f['tipo'] == 'sqlserver' and any(t.get('fonte') == f['nome'] for t in m['tabelas']):
            nomes += list(parametros(f))
    return nomes + sorted(expressoes_compartilhadas(m)) + [t['nome'] for t in m['tabelas']]


def modelo(m):
    refs = '\n'.join(f'ref table {tmdl_nome(t["nome"])}' for t in m['tabelas'])
    return (f'model Model\n\tculture: pt-BR\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n'
            f'\tdiscourageImplicitMeasures\n'
            f'\tsourceQueryCulture: pt-BR\n\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n'
            f'annotation PBI_QueryOrder = [{",".join(chr(34) + n + chr(34) for n in _ordem(m))}]\n\n'
            f'annotation __PBI_TimeIntelligenceEnabled = 0\n\n{refs}\n')


def funcoes(m):
    """O functions.tmdl: as funções dos pacotes do daxlib como vieram, com a palavra-chave em minúsculas e o
    recuo em tabulação (o TMDL do projeto usa tabulação)."""
    import re
    out = []
    for linha in m['funcoes_dax']['tmdl'].split('\n'):
        linha = re.sub(r'^FUNCTION\b', 'function', linha)
        espacos = len(linha) - len(linha.lstrip(' '))
        out.append('\t' * (espacos // 4) + ' ' * (espacos % 4) + linha.lstrip(' ') if espacos else linha)
    return '\n'.join(out)


def gravar(m, pasta_projeto, nome):
    raiz = os.path.join(pasta_projeto, f'{nome}.SemanticModel')
    defi = os.path.join(raiz, 'definition')
    os.makedirs(os.path.join(defi, 'tables'), exist_ok=True)
    gravar_json(os.path.join(raiz, 'definition.pbism'), {
        '$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json',
        'version': '4.0', 'settings': {}})
    nivel = 1601 if any(md.get('formato_dinamico') for md in m['medidas']) else COMPATIBILIDADE   # formato dinâmico
    if m.get('funcoes_dax'):                       # funções DAX definidas pelo usuário (daxlib)
        nivel = max(nivel, 1702)
        gravar_texto(os.path.join(defi, 'functions.tmdl'), funcoes(m))
    gravar_texto(os.path.join(defi, 'database.tmdl'), f'database\n\tcompatibilityLevel: {nivel}\n')
    gravar_texto(os.path.join(defi, 'model.tmdl'), modelo(m))
    exprs = expressoes(m)
    if exprs:
        gravar_texto(os.path.join(defi, 'expressions.tmdl'), exprs)
    if m['relacionamentos']:
        gravar_texto(os.path.join(defi, 'relationships.tmdl'), relacionamentos(m))
    for t in m['tabelas']:
        gravar_texto(os.path.join(defi, 'tables', f'{_arquivo(t["nome"])}.tmdl'), tabela(m, t))
    if m.get('seguranca'):
        os.makedirs(os.path.join(defi, 'roles'), exist_ok=True)
        for papel in m['seguranca']:
            gravar_texto(os.path.join(defi, 'roles', f'{_arquivo(papel["papel"])}.tmdl'), role(papel))
    return raiz


def role(papel):
    linhas = [_desc(papel['descricao'], 0) + f'role {tmdl_nome(papel["papel"])}', '\tmodelPermission: read', '']
    for r in papel['regras']:
        linhas.append(f'\ttablePermission {tmdl_nome(r["tabela"])} = {" ".join(r["filtro"].split())}')
        linhas.append('')
    linhas.append(f'\tannotation PBI_Id = {guid("role", papel["papel"]).replace("-", "")}')
    return '\n'.join(linhas) + '\n'


def _arquivo(nome):
    return ''.join(c if c not in '<>:"/\\|?*' else '_' for c in nome)
