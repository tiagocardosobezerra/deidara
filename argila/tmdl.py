"""
O modelo semântico do Power BI em TMDL (pasta `<Projeto>.SemanticModel`).

TMDL é o formato texto do modelo tabular que o Power BI Desktop abre num
projeto .pbip: um arquivo por tabela, indentado por tabulação. Cada tabela
lê a view correspondente (`sql.py`) por dois parâmetros, Servidor e Banco,
que o usuário troca em "Transformar dados > Editar parâmetros".
"""

import os

from .sql import nome_view  # noqa: F401  (documenta a ligação tabela -> view)
from .util import FORMATOS, gravar_json, gravar_texto, guid, m_texto, tmdl_nome

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


def _particao(m, t):
    if t.get('calendario'):
        return _particao_calendario(m, t)
    m_expr = (f'let\n    Fonte = Sql.Database(Servidor, Banco),\n'
              f'    Dados = Fonte{{[Schema={m_texto(m["fonte"]["esquema_views"])}, Item={m_texto("vw_" + t["nome"])}]}}[Data]\n'
              f'in\n    Dados')
    return (f'\tpartition {tmdl_nome(t["nome"])} = m\n\t\tmode: import\n\t\tsource =\n{_expressao(m_expr, 4)}\n')


def _particao_calendario(m, t):
    m_expr = f'''let
    Inicio = #date({t["inicio"]}, 1, 1),
    Fim = #date({t["fim"]}, 12, 31),
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
    AnoTriNum = Table.AddColumn(AnoMesNum, "Ano-Trimestre Num", each [Ano] * 10 + Date.QuarterOfYear([Data]), Int64.Type)
in
    AnoTriNum'''
    return f'\tpartition {tmdl_nome(t["nome"])} = m\n\t\tmode: import\n\t\tsource =\n{_expressao(m_expr, 4)}\n'


ORDENAR_POR = {'Nome do Mês': 'Mês', 'Mês/Ano': 'Ano-Mês Num', 'Ano-Trimestre': 'Ano-Trimestre Num'}


def tabela(m, t):
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
        if md.get('oculta'):
            props.append('\t\tisHidden')
        if md['pasta']:
            props.append(f'\t\tdisplayFolder: {md["pasta"]}')
        props.append(f'\t\tlineageTag: {guid("medida", md["nome"])}')
        if md['formato'] == 'moeda':
            props.append('')
            props.append('\t\tannotation PBI_FormatHint = {"currencyCulture":"pt-BR"}')
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
        props.append(f'\t\tsourceColumn: {c["nome"]}')
        if c['nome'] in ORDENAR_POR and t.get('calendario'):
            props.append(f'\t\tsortByColumn: {tmdl_nome(ORDENAR_POR[c["nome"]])}')
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


def expressoes(m):
    f = m['fonte']
    return (f'expression Servidor = {m_texto(f["servidor"])} meta [IsParameterQuery=true, Type="Text", '
            f'IsParameterQueryRequired=true]\n\tlineageTag: {guid("param", "Servidor")}\n\n'
            f'\tannotation PBI_ResultType = Text\n\n'
            f'expression Banco = {m_texto(f["banco"])} meta [IsParameterQuery=true, Type="Text", '
            f'IsParameterQueryRequired=true]\n\tlineageTag: {guid("param", "Banco")}\n\n'
            f'\tannotation PBI_ResultType = Text\n')


def modelo(m):
    refs = '\n'.join(f'ref table {tmdl_nome(t["nome"])}' for t in m['tabelas'])
    return (f'model Model\n\tculture: pt-BR\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n'
            f'\tdiscourageImplicitMeasures\n'
            f'\tsourceQueryCulture: pt-BR\n\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n'
            f'annotation PBI_QueryOrder = ["Servidor","Banco",{",".join(chr(34) + t["nome"] + chr(34) for t in m["tabelas"])}]\n\n'
            f'annotation __PBI_TimeIntelligenceEnabled = 0\n\n{refs}\n')


def gravar(m, pasta_projeto, nome):
    raiz = os.path.join(pasta_projeto, f'{nome}.SemanticModel')
    defi = os.path.join(raiz, 'definition')
    os.makedirs(os.path.join(defi, 'tables'), exist_ok=True)
    gravar_json(os.path.join(raiz, 'definition.pbism'), {
        '$schema': 'https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json',
        'version': '4.0', 'settings': {}})
    gravar_texto(os.path.join(defi, 'database.tmdl'), f'database\n\tcompatibilityLevel: {COMPATIBILIDADE}\n')
    gravar_texto(os.path.join(defi, 'model.tmdl'), modelo(m))
    gravar_texto(os.path.join(defi, 'expressions.tmdl'), expressoes(m))
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
