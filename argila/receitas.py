"""
Receitas: o Deidara manda a consulta, a pessoa roda onde os dados estão e
devolve o resultado. Nenhuma conexão, credencial ou driver no Deidara.

- sql: catálogo do SQL Server (só `sys.*`), no SSMS;
- dax: estrutura de um modelo Power BI existente (funções INFO), na
  Exibição de consulta DAX do Power BI Desktop. Serve para qualquer fonte que
  já esteja num modelo (Excel, SharePoint, API...), e traz a expressão Power
  Query de cada tabela, que o Deidara reaproveita;
- m: estrutura de consultas Power Query (`Table.Schema`), em qualquer
  conector, numa consulta nula do Power BI ou do Excel.

As três devolvem só metadados (nome, tipo, descrição, chave, ligação, a
expressão da consulta), nunca linhas de dado. O resultado é copiado da grade
("Copiar com cabeçalhos" / "Copiar tabela") e colado num arquivo .txt, que o
`catalogar` lê (`ler_colado` + `catalogo_de_*`).
"""

import csv
import datetime
import io
import os
import re

from .catalogo import FORMATO
from .util import chave, familia_da_coluna, m_texto, sem_acento

# quebras de linha e tabulações viajam codificadas, para caber numa célula da grade
QUEBRA, TABULACAO = '⏎', '⇥'


# =================================================================== receitas
def receita_sql(esquema='dbo', tabelas=()):
    lista = ','.join(tabelas)
    return f"""/*
  Deidara — receita SQL: estrutura das tabelas (SQL Server 2016 ou superior)
  Lê SOMENTE o catálogo (sys.*): nenhuma linha de dado sai daqui.
  1. Selecione o banco certo e ajuste @esquema e @tabelas (vazio = todas do esquema).
  2. Rode (F5) com o resultado em grade.
  3. Clique na grade, Ctrl+A, botão direito > "Copiar com Cabeçalhos" e cole num .txt.
  4. Devolva o .txt a quem pediu (o analista do painel). Quem tem o Deidara roda:
     python deidara.py catalogar --de colado/NOME_DA_FONTE.txt --fonte NOME_DA_FONTE
*/
SET NOCOUNT ON;
DECLARE @esquema sysname = N'{esquema.replace("'", "''")}';
DECLARE @tabelas nvarchar(max) = N'{lista.replace("'", "''")}';

WITH alvo AS (
    SELECT t.object_id, t.name
    FROM sys.tables AS t
    JOIN sys.schemas AS s ON s.schema_id = t.schema_id
    WHERE s.name = @esquema AND t.is_ms_shipped = 0
      AND (@tabelas = N'' OR t.name IN (SELECT LTRIM(RTRIM(value)) FROM STRING_SPLIT(@tabelas, N',')))
),
pk AS (
    SELECT ic.object_id, ic.column_id, ic.key_ordinal
    FROM sys.indexes AS i
    JOIN sys.index_columns AS ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
    WHERE i.is_primary_key = 1
),
descr AS (
    SELECT major_id, minor_id,
           REPLACE(REPLACE(REPLACE(CAST(value AS nvarchar(4000)), CHAR(13), N' '), CHAR(10), N' '), CHAR(9), N' ') AS texto
    FROM sys.extended_properties
    WHERE class = 1 AND name = N'MS_Description'
)
SELECT N'tabela' AS secao, a.name AS tabela, CAST(NULL AS sysname) AS coluna, CAST(NULL AS sysname) AS tipo,
       CAST(NULL AS int) AS tamanho, CAST(NULL AS int) AS precisao, CAST(NULL AS int) AS escala,
       CAST(NULL AS int) AS nulo, CAST(NULL AS int) AS pk_ordem, d.texto AS descricao,
       CAST(NULL AS sysname) AS tabela_mae, CAST(NULL AS sysname) AS campo_mae,
       CAST(NULL AS sysname) AS fk, CAST(NULL AS int) AS fk_ordem
FROM alvo AS a
LEFT JOIN descr AS d ON d.major_id = a.object_id AND d.minor_id = 0
UNION ALL
SELECT N'coluna', a.name, c.name, TYPE_NAME(c.system_type_id),
       CASE WHEN c.max_length = -1 THEN -1
            WHEN TYPE_NAME(c.system_type_id) IN (N'nchar', N'nvarchar') THEN c.max_length / 2
            ELSE c.max_length END,
       c.precision, c.scale, CAST(c.is_nullable AS int), pk.key_ordinal, d.texto,
       NULL, NULL, NULL, NULL
FROM alvo AS a
JOIN sys.columns AS c ON c.object_id = a.object_id
LEFT JOIN pk ON pk.object_id = c.object_id AND pk.column_id = c.column_id
LEFT JOIN descr AS d ON d.major_id = c.object_id AND d.minor_id = c.column_id
UNION ALL
SELECT N'fk', a.name, pc.name, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
       rt.name, rc.name, fk.name, fkc.constraint_column_id
FROM alvo AS a
JOIN sys.foreign_keys AS fk ON fk.parent_object_id = a.object_id
JOIN sys.foreign_key_columns AS fkc ON fkc.constraint_object_id = fk.object_id
JOIN sys.columns AS pc ON pc.object_id = fkc.parent_object_id AND pc.column_id = fkc.parent_column_id
JOIN sys.tables AS rt ON rt.object_id = fkc.referenced_object_id
JOIN sys.columns AS rc ON rc.object_id = fkc.referenced_object_id AND rc.column_id = fkc.referenced_column_id
UNION ALL
SELECT N'origem', N'(banco)', CAST(@@SERVERNAME AS sysname), CAST(DB_NAME() AS sysname), NULL, NULL, NULL, NULL, NULL,
       @esquema, NULL, NULL, NULL, NULL
ORDER BY secao DESC, tabela, fk, fk_ordem, coluna;
"""


def _codifica(expr):
    return (f'SUBSTITUTE(SUBSTITUTE(SUBSTITUTE({expr}, UNICHAR(13), ""), UNICHAR(10), "{QUEBRA}"), '
            f'UNICHAR(9), "{TABULACAO}")')


def receita_dax():
    def linha(secao, tabela='""', coluna='""', tipo='""', descricao='""', extra='""', expressao='""'):
        return (f'"secao", "{secao}", "tabela", {tabela}, "coluna", {coluna}, "tipo", {tipo}, '
                f'"descricao", {descricao}, "extra", {extra}, "expressao", {expressao}')
    return f"""// Deidara — receita DAX: estrutura do modelo Power BI (só metadados; nenhuma linha de dado)
// 1. No Power BI Desktop, abra o .pbix que já carrega as fontes (Excel, SharePoint, banco...).
// 2. Exibição de consulta DAX > nova consulta > cole tudo isto > Executar.
// 3. Na grade do resultado: Copiar tabela; cole num .txt.
// 4. Devolva o .txt a quem pediu (o analista do painel). Quem tem o Deidara roda:
//    python deidara.py catalogar --de colado/NOME_DA_FONTE.txt --fonte NOME_DA_FONTE
// Quebras de linha das expressões vêm como {QUEBRA}: o Deidara desfaz.
DEFINE
    VAR _ids = SELECTCOLUMNS(INFO.TABLES(), "IdTabela", [ID], "NomeTabela", [Name])
    VAR _tabelas =
        SELECTCOLUMNS(
            INFO.VIEW.TABLES(),
            {linha('tabela', '[Name]', descricao=_codifica('[Description]'),
                   extra='IF(ISBLANK([Expression]), IF([IsHidden], "oculta", ""), "calculada")')}
        )
    VAR _colunas =
        SELECTCOLUMNS(
            INFO.VIEW.COLUMNS(),
            {linha('coluna', '[Table]', '[Name]', '[DataType]', _codifica('[Description]'),
                   'IF(ISBLANK([Expression]), IF([IsHidden], "oculta", ""), "calculada")')}
        )
    VAR _relacoes =
        SELECTCOLUMNS(
            INFO.VIEW.RELATIONSHIPS(),
            {linha('relacao', '[FromTable]', '[FromColumn]', '[FromCardinality] & ">" & [ToCardinality]',
                   '[ToTable] & "[" & [ToColumn] & "]"', 'IF([IsActive], "ativa", "inativa")')}
        )
    VAR _particoes =
        SELECTCOLUMNS(
            FILTER(
                CROSSJOIN(
                    SELECTCOLUMNS(INFO.PARTITIONS(), "IdDaParticao", [TableID], "Consulta", [QueryDefinition],
                                  "TipoParticao", [Type]),
                    _ids
                ),
                [IdDaParticao] = [IdTabela]
            ),
            {linha('particao', '[NomeTabela]', tipo='FORMAT([TipoParticao], "0")', expressao=_codifica('[Consulta]'))}
        )
    VAR _expressoes =
        SELECTCOLUMNS(
            INFO.EXPRESSIONS(),
            {linha('expressao', '[Name]', tipo='FORMAT([Kind], "0")', expressao=_codifica('[Expression]'))}
        )
EVALUATE
    UNION(_tabelas, _colunas, _relacoes, _particoes, _expressoes)
"""


def receita_m(consultas=()):
    consultas = list(consultas) or ['NomeDaConsulta']
    itens = ',\n'.join(f'        {{{m_texto(c)}, #{m_texto(c)}}}' for c in consultas)
    return f"""// Deidara — receita Power Query: estrutura das consultas (só nomes e tipos; nenhuma linha de dado)
// Serve para qualquer conector: Excel, SharePoint, CSV, pasta, API, outro banco.
// 1. Em cada consulta listada, confira os tipos das colunas (selecione as colunas >
//    Transformar > Detectar tipo de dados). Coluna sem tipo vira aviso no Deidara.
// 2. Página Inicial > Nova fonte > Consulta nula > Editor Avançado > cole tudo isto.
//    Ajuste a lista abaixo: {{"Nome no Deidara", #"Nome da consulta"}}.
// 3. Na visualização do resultado: clique no canto da grade > Copiar tabela inteira; cole num .txt.
// 4. Para cada consulta, abra o Editor Avançado, copie o texto e salve como <Nome no Deidara>.m
//    na mesma pasta do .txt (é a conexão que o painel vai reaproveitar). Parâmetros que ela usar:
//    salve também, um .m por parâmetro, com o nome dele.
// 5. Devolva o .txt e os .m a quem pediu (o analista do painel). Quem tem o Deidara roda:
//    python deidara.py catalogar --de colado/NOME_DA_FONTE.txt --fonte NOME_DA_FONTE --m colado/m
let
    Consultas = {{
{itens}
    }},
    PorConsulta = List.Transform(Consultas, (c) =>
        let
            Esquema = Table.Schema(c{{1}}),
            Campos = Table.SelectColumns(Esquema, {{"Name", "TypeName", "Kind", "IsNullable", "NumericPrecision",
                                                    "NumericScale", "MaxLength", "Description"}}),
            ComTabela = Table.AddColumn(Campos, "Tabela", each c{{0}}, type text)
        in
            ComTabela),
    Resultado = Table.ReorderColumns(Table.Combine(PorConsulta),
        {{"Tabela", "Name", "TypeName", "Kind", "IsNullable", "NumericPrecision", "NumericScale", "MaxLength",
          "Description"}})
in
    Resultado
"""


def receita_funcoes_dax():
    return """// Deidara — receita: dicionário de funções DAX da SUA versão do Power BI (só nomes e descrições)
// Exibição de consulta DAX > cole > Executar > Copiar tabela > cole num .txt
// python3 deidara.py catalogar --funcoes dax --de resultado.txt
EVALUATE INFO.FUNCTIONS()
"""


def receita_funcoes_m():
    return """// Deidara — receita: dicionário de funções Power Query (M) do SEU ambiente (só nomes e descrições)
// Consulta nula > Editor Avançado > cole > Copiar tabela inteira > cole num .txt
// python3 deidara.py catalogar --funcoes m --de resultado.txt
let
    Tudo = Record.ToTable(#shared),
    Funcoes = Table.SelectRows(Tudo, each Value.Is([Value], type function)),
    ComDoc = Table.AddColumn(Funcoes, "Descricao", each
        try Value.Metadata(Value.Type([Value]))[Documentation.LongDescription] otherwise null, type text),
    Resultado = Table.SelectColumns(ComDoc, {"Name", "Descricao"})
in
    Resultado
"""


def dicionario_local(caminho, linguagem):
    """Resultado colado da receita de funções -> {nome: {descricao}} (fica em dicionario/local)."""
    cab, linhas = ler_colado(caminho)
    col_nome = next((c for c in cab if c in ('function_name', 'functionname', 'name', 'nome')), None)
    if not col_nome:
        raise ValueError(f'{caminho}: não achei a coluna com o nome da função (cabeçalho: {", ".join(cab[:8])})')
    col_desc = next((c for c in cab if c in ('description', 'descricao')), None)
    out = {}
    for l in linhas:
        n = (l.get(col_nome) or '').strip()
        if n and not n.startswith('#'):
            out[n] = {'descricao_local': (l.get(col_desc) or '')[:500] if col_desc else ''}
    return {'formato': 'deidara-dicionario/1', 'linguagem': linguagem, 'origem': 'receita de funções do usuário',
            'coletado_em': datetime.datetime.now().strftime('%d/%m/%Y %H:%M'), 'funcoes': out}


# ================================================================ resultado
def _texto(bruto):
    if bruto.startswith((b'\xff\xfe', b'\xfe\xff')):
        return bruto.decode('utf-16')
    try:
        return bruto.decode('utf-8-sig')
    except UnicodeDecodeError:
        return bruto.decode('cp1252')


def _cabecalho(h):
    """'Tabela[secao]' / '[secao]' / ' Secão ' -> 'secao'."""
    h = h.strip().strip('"')
    mt = re.fullmatch(r'.*\[([^\]]+)\]', h)
    if mt:
        h = mt.group(1)
    return re.sub(r'[^a-z0-9_]', '', sem_acento(h).lower().replace(' ', '_'))


def ler_colado(caminho):
    """Lê o resultado colado da grade (TSV, ou CSV com ; ou ,). Devolve [dict]."""
    with open(caminho, 'rb') as f:
        texto = _texto(f.read())
    linhas = [l for l in texto.splitlines() if l.strip()]
    linhas = [l for l in linhas if not re.match(r'^\(\d+ (rows?|linhas?) ', l.strip(), re.I)]
    if len(linhas) < 2:
        raise ValueError(f'{caminho}: sem linhas de resultado (cole a grade inteira, com o cabeçalho)')
    sep = '\t' if '\t' in linhas[0] else (';' if linhas[0].count(';') > linhas[0].count(',') else ',')
    leitor = csv.reader(io.StringIO('\n'.join(linhas)), delimiter=sep)
    cab = [_cabecalho(h) for h in next(leitor)]
    out = []
    for valores in leitor:
        valores += [''] * (len(cab) - len(valores))
        out.append({k: _limpo(v) for k, v in zip(cab, valores)})
    return cab, out


def _limpo(v):
    v = (v or '').strip()
    if v.upper() == 'NULL':
        return ''
    return v.replace(QUEBRA, '\n').replace(TABULACAO, '\t')


def detectar_receita(cab):
    c = set(cab)
    if {'secao', 'tabela_mae', 'fk'} <= c:
        return 'sql'
    if {'secao', 'extra', 'expressao'} <= c:
        return 'dax'
    if {'tabela', 'name', 'typename', 'kind'} <= c:
        return 'm'
    return None


def _int(v):
    try:
        return int(float(str(v).replace(',', '.')))
    except (TypeError, ValueError):
        return None


def _novo(fonte, tipo, receita):
    return {'formato': FORMATO, 'fonte': fonte, 'tipo': tipo, 'receita': receita,
            'coletado_em': datetime.datetime.now().strftime('%d/%m/%Y %H:%M'), 'tabelas': {}, 'fks': [],
            'expressoes': {}}


def _tabela(cat, nome):
    return cat['tabelas'].setdefault(nome, {'descricao': '', 'pk': [], 'expressao_m': None, 'colunas': []})


# ------------------------------------------------------------------- SQL
def catalogo_de_sql(linhas, fonte):
    cat, avisos = _novo(fonte, 'sqlserver', 'sql'), []
    pks, fks = {}, {}
    for l in linhas:
        sec, tab = l.get('secao'), l.get('tabela')
        if not tab:
            continue
        if sec == 'origem':                      # onde a receita rodou: vira o servidor e o banco do argila.json
            cat['origem'] = {k: v for k, v in (('servidor', l.get('coluna')), ('banco', l.get('tipo')),
                                                ('esquema', l.get('descricao'))) if v}
        elif sec == 'tabela':
            _tabela(cat, tab)['descricao'] = l.get('descricao', '')
        elif sec == 'coluna':
            oc = {'coluna': l['coluna'], 'tipo': l.get('tipo') or None, 'tamanho': _int(l.get('tamanho')),
                  'precisao': _int(l.get('precisao')), 'escala': _int(l.get('escala')), 'nulo': _int(l.get('nulo')),
                  'descricao': l.get('descricao', '')}
            oc['familia'] = familia_da_coluna(oc) or 'texto'
            if not familia_da_coluna(oc):
                avisos.append(f'{tab}.{l["coluna"]}: tipo {l.get("tipo")} sem equivalente; tratado como texto')
            _tabela(cat, tab)['colunas'].append(oc)
            if _int(l.get('pk_ordem')):
                pks.setdefault(tab, []).append((_int(l['pk_ordem']), l['coluna']))
        elif sec == 'fk':
            fk = fks.setdefault(l['fk'], {'nome': l['fk'], 'origem': 'constraint', 'tabela_filha': tab,
                                          'tabela_mae': l['tabela_mae'], 'colunas': []})
            fk['colunas'].append((_int(l.get('fk_ordem')) or 0, {'campo_filho': l['coluna'], 'campo_mae': l['campo_mae']}))
    for tab, campos in pks.items():
        _tabela(cat, tab)['pk'] = [c for _, c in sorted(campos)]
    for fk in fks.values():
        fk['colunas'] = [c for _, c in sorted(fk['colunas'], key=lambda x: x[0])]
        cat['fks'].append(fk)
    return cat, avisos


# ------------------------------------------------------------------- DAX
_FAMILIA_PBI = {
    'int64': 'inteiro', 'integer': 'inteiro', 'wholenumber': 'inteiro', 'numerointeiro': 'inteiro',
    'double': 'real', 'decimalnumber': 'real', 'numerodecimal': 'real', 'number': 'real',
    'decimal': 'decimal', 'fixeddecimalnumber': 'decimal', 'fixeddecimal': 'decimal', 'currency': 'decimal',
    'numerodecimalfixo': 'decimal', 'moeda': 'decimal',
    'datetime': 'datahora', 'dateandtime': 'datahora', 'dataehora': 'datahora', 'date': 'data', 'data': 'data',
    'time': 'hora', 'hora': 'hora', 'boolean': 'logico', 'truefalse': 'logico', 'verdadeirofalso': 'logico',
    'logical': 'logico', 'string': 'texto', 'text': 'texto', 'texto': 'texto',
}


def familia_powerbi(tipo):
    return _FAMILIA_PBI.get(re.sub(r'[^a-z0-9]', '', sem_acento(tipo or '').lower()))


def _cardinalidade(v):
    v = chave(v)
    if v in ('many', 'muitos', '*', '2'):
        return 'muitos'
    if v in ('one', 'um', '1'):
        return 'um'
    return v or '?'


def catalogo_de_dax(linhas, fonte):
    cat, avisos = _novo(fonte, 'powerbi', 'dax'), []
    calculadas = set()
    for l in linhas:
        if l.get('secao') == 'tabela' and l.get('extra') == 'calculada':
            calculadas.add(l['tabela'])
            avisos.append(f'tabela {l["tabela"]} é calculada (DAX) no modelo de origem: ficou de fora; '
                          'recrie como medida ou tabela do Deidara')
    for l in linhas:
        sec, tab = l.get('secao'), l.get('tabela')
        if not tab or tab in calculadas or tab.startswith(('LocalDateTable_', 'DateTableTemplate_')):
            continue
        if sec == 'tabela':
            _tabela(cat, tab)['descricao'] = l.get('descricao', '')
        elif sec == 'coluna':
            if l.get('coluna', '').startswith('RowNumber-'):
                continue
            if l.get('extra') == 'calculada':
                avisos.append(f'{tab}[{l["coluna"]}] é coluna calculada no modelo de origem: ficou de fora')
                continue
            fam = familia_powerbi(l.get('tipo'))
            if not fam:
                avisos.append(f'{tab}[{l["coluna"]}]: tipo "{l.get("tipo")}" não reconhecido; tratado como texto')
            _tabela(cat, tab)['colunas'].append({'coluna': l['coluna'], 'familia': fam or 'texto',
                                                 'tipo': l.get('tipo'), 'descricao': l.get('descricao', ''),
                                                 'tipo_indefinido': not fam})
        elif sec == 'particao':
            expr = l.get('expressao', '')
            t = _tabela(cat, tab)
            if t['expressao_m'] and expr:
                avisos.append(f'tabela {tab} tem mais de uma partição: ficou só a primeira')
            elif expr:
                t['expressao_m'] = expr
        elif sec == 'expressao' and l.get('expressao'):
            cat['expressoes'][tab] = l['expressao']
    for l in linhas:
        if l.get('secao') != 'relacao':
            continue
        de, para = l.get('tabela'), l.get('descricao', '')
        mt = re.fullmatch(r'(.*)\[(.*)\]', para)
        if not mt or de in calculadas or mt.group(1) in calculadas:
            continue
        lado = [_cardinalidade(x) for x in (l.get('tipo') or '>').split('>', 1)]
        filha, cf, mae, cm = de, l['coluna'], mt.group(1), mt.group(2)
        if lado == ['um', 'muitos']:
            filha, cf, mae, cm = mae, cm, de, l['coluna']
        elif lado == ['muitos', 'muitos']:
            avisos.append(f'relação muitos-para-muitos {de}[{l["coluna"]}] - {para}: ficou de fora')
            continue
        elif lado != ['muitos', 'um']:
            avisos.append(f'relação {de}[{l["coluna"]}] - {para} com cardinalidade "{l.get("tipo")}": tratada '
                          f'como {de} (muitos) -> {mt.group(1)} (um)')
        cat['fks'].append({'nome': f'{filha}.{cf} -> {mae}.{cm}', 'origem': 'modelo existente',
                           'tabela_filha': filha, 'tabela_mae': mae, 'ativa': l.get('extra') != 'inativa',
                           'colunas': [{'campo_filho': cf, 'campo_mae': cm}]})
    sem_expr = [n for n, t in cat['tabelas'].items() if not t['expressao_m']]
    for n in sem_expr:
        avisos.append(f'tabela {n} veio sem expressão Power Query: confira se ela é importada')
    return cat, avisos


# --------------------------------------------------------------------- M
_FAMILIA_M = {
    'int64.type': 'inteiro', 'int32.type': 'inteiro', 'int16.type': 'inteiro', 'int8.type': 'inteiro',
    'byte.type': 'inteiro', 'number.type': 'real', 'double.type': 'real', 'single.type': 'real',
    'percentage.type': 'real', 'currency.type': 'decimal', 'decimal.type': 'decimal',
    'date.type': 'data', 'datetime.type': 'datahora', 'datetimezone.type': 'datahora', 'time.type': 'hora',
    'logical.type': 'logico', 'text.type': 'texto',
}
_KIND_M = {'number': 'real', 'text': 'texto', 'date': 'data', 'datetime': 'datahora', 'datetimezone': 'datahora',
           'time': 'hora', 'logical': 'logico'}


def familia_m(typename, kind):
    t = (typename or '').strip().lower()
    t = t if t.endswith('.type') or not t else t + '.type'
    return _FAMILIA_M.get(t) or _KIND_M.get((kind or '').strip().lower())


def catalogo_de_m(linhas, fonte, pasta_m=None):
    cat, avisos = _novo(fonte, 'powerquery', 'm'), []
    for l in linhas:
        tab, col = l.get('tabela'), l.get('name')
        if not tab or not col:
            continue
        fam = familia_m(l.get('typename'), l.get('kind'))
        if not fam:
            avisos.append(f'{tab}[{col}]: sem tipo na consulta ({l.get("typename") or l.get("kind") or "any"}); '
                          'tratado como texto: detecte o tipo no Power Query ou informe "tipo" no argila.json')
        _tabela(cat, tab)['colunas'].append({
            'coluna': col, 'familia': fam or 'texto', 'tipo': l.get('typename') or l.get('kind'),
            'precisao': _int(l.get('numericprecision')), 'escala': _int(l.get('numericscale')),
            'tamanho': _int(l.get('maxlength')), 'nulo': 0 if chave(l.get('isnullable')) in ('false', 'falso') else 1,
            'formato_sugerido': 'percentual' if 'percentage' in (l.get('typename') or '').lower() else None,
            'descricao': l.get('description', ''), 'tipo_indefinido': not fam})
    if pasta_m:
        for arq in sorted(os.listdir(pasta_m)):
            if not arq.lower().endswith('.m'):
                continue
            with open(os.path.join(pasta_m, arq), encoding='utf-8-sig') as f:
                expr = f.read().strip()
            nome = arq[:-2]
            t = next((t for n, t in cat['tabelas'].items() if chave(n) == chave(nome)), None)
            if t is not None:
                t['expressao_m'] = expr
            else:
                cat['expressoes'][nome] = expr
    for n, t in cat['tabelas'].items():
        if not t['expressao_m']:
            avisos.append(f'consulta {n} sem o arquivo {n}.m: o painel não vai saber de onde ler; salve o texto do '
                          'Editor Avançado e rode o catalogar de novo com --m')
    return cat, avisos


def catalogar(caminho, fonte, pasta_m=None, receita=None):
    cab, linhas = ler_colado(caminho)
    receita = receita or detectar_receita(cab)
    if receita == 'sql':
        return catalogo_de_sql(linhas, fonte)
    if receita == 'dax':
        return catalogo_de_dax(linhas, fonte)
    if receita == 'm':
        return catalogo_de_m(linhas, fonte, pasta_m)
    raise ValueError(f'{caminho}: não reconheci o resultado (cabeçalho: {", ".join(cab[:8])}). '
                     'Cole a grade inteira de uma receita do Deidara, com o cabeçalho.')
