"""
A camada SQL do painel: uma view por tabela do modelo, num schema próprio
(`bi` por padrão), com as colunas já com o nome amigável.

Por que views e não SELECT dentro do Power BI:
- o DBA revisa e versiona o SQL num lugar só;
- a chave composta vira uma coluna só (o Power BI só relaciona por uma);
- data e hora viram `date` onde o calendário liga;
- trocar a origem não quebra o .pbip, só a view.

Também gera a homologação: o total de cada indicador direto no banco (geral
e por ano) e as checagens de qualidade que fazem a atualização do Power BI
falhar ou mentir (chave repetida no lado um, órfãos, data fora do
calendário). Tudo lê só as views: SQL Server 2016 SP1 ou superior.
"""

from .util import sql_nome


def nome_view(m, t):
    return f'{sql_nome(m["fontes"][t["fonte"]]["esquema_views"])}.{sql_nome("vw_" + t["nome"])}'


def fontes_sql(m):
    """Fontes SQL Server que têm pelo menos uma tabela no modelo."""
    return [f for f in m['fontes'].values()
            if f['tipo'] == 'sqlserver' and any(t.get('fonte') == f['nome'] for t in m['tabelas'])]


def _da_fonte(m, fonte):
    return [t for t in m['tabelas'] if t.get('fonte') == fonte['nome']]


def _lit(s):
    return "N'" + str(s).replace("'", "''") + "'"


def _tabela(m, nome):
    return next(x for x in m['tabelas'] if x['nome'] == nome)


def _expr(c):
    if c['expressao_sql']:
        return c['expressao_sql']
    col = f't.{sql_nome(c["origem"])}'
    if c.get('cast_sql'):
        return f'CAST({col} AS {c["cast_sql"]})'
    if c['como_data']:
        return f'CAST({col} AS date)'
    return col


def _cabecalho(m, titulo, linhas):
    corpo = '\n'.join(f'  {l}' for l in linhas)
    return f'/*\n  {m["projeto"]} — {titulo}\n  Gerado pelo Deidara a partir do argila.json aprovado.\n{corpo}\n*/\nSET NOCOUNT ON;\n'


def views(m, fonte):
    esq = fonte['esquema_views']
    out = [_cabecalho(m, f'camada de views para o Power BI (fonte {fonte["nome"]}, banco {fonte["banco"]})',
                      ['Revise com o DBA antes de rodar. Só leitura: nenhuma view altera dado.',
                       'Requer SQL Server 2016 SP1 ou superior (CREATE OR ALTER).']),
           f"IF SCHEMA_ID({_lit(esq)}) IS NULL\n    EXEC(N'CREATE SCHEMA {sql_nome(esq)} AUTHORIZATION dbo');", 'GO', '']
    for t in _da_fonte(m, fonte):
        cols = ',\n'.join(f'    {_expr(c)} AS {sql_nome(c["nome"])}' for c in t['colunas'])
        where = f'\nWHERE {t["filtro"]}' if t['filtro'] else ''
        desc = f'-- {t["descricao"]}\n' if t['descricao'] else ''
        out.append(f'{desc}-- origem: {fonte["esquema_origem"]}.{t["origem"]}\n'
                   f'CREATE OR ALTER VIEW {nome_view(m, t)}\nAS\nSELECT\n{cols}\n'
                   f'FROM {sql_nome(fonte["esquema_origem"])}.{sql_nome(t["origem"])} AS t{where};\nGO\n')
    out.append('-- Permissão de leitura para a conta que o Power BI (gateway) usa:')
    out.append(f'-- GRANT SELECT ON SCHEMA::{sql_nome(esq)} TO [conta_do_gateway];')
    return '\n'.join(out) + '\n'


def _data_ativa(m, tabela):
    for d in (m.get('calendario') or {}).get('datas', []):
        if d['tabela'] == tabela and d['ativo']:
            return d['coluna']
    return None


def conferencia(m, fonte):
    """Total de cada indicador de agregação simples desta fonte: geral e por ano da data ativa."""
    out = [_cabecalho(m, 'conferência dos indicadores (homologação)', [
        'Rode depois de criar as views. Compare cada total com o cartão do Power BI',
        'sem nenhum segmentador marcado; o bloco por ano, com o segmentador de Ano.',
        'Divisão, tempo e DAX livre não entram: confira pelos componentes.'])]
    gerais, por_ano = [], []
    for md in m['medidas']:
        c = md.get('conferencia')
        if not c:
            continue
        t = _tabela(m, c['tabela'])
        if t.get('fonte') != fonte['nome']:
            continue
        gerais.append(f"SELECT {_lit(md['nome'])} AS indicador, CAST({c['sql']} AS decimal(38,6)) AS total_no_banco "
                      f'FROM {nome_view(m, t)}')
        data = _data_ativa(m, t['nome'])
        if data:
            por_ano.append(f"SELECT {_lit(md['nome'])} AS indicador, YEAR({sql_nome(data)}) AS ano, "
                           f"CAST({c['sql']} AS decimal(38,6)) AS total_no_banco FROM {nome_view(m, t)} "
                           f'GROUP BY YEAR({sql_nome(data)})')
    if not gerais:
        out.append('-- Nenhum indicador de agregação simples para conferir.')
    else:
        out.append('-- 1) Total geral\n' + '\nUNION ALL\n'.join(gerais) + ';\n')
    if por_ano:
        out.append('-- 2) Por ano (data ativa do calendário)\n' + '\nUNION ALL\n'.join(por_ano)
                   + '\nORDER BY indicador, ano;\n')
    out += _conferencia_estoque(m, fonte)
    return '\n'.join(out) + '\n'


def _conferencia_estoque(m, fonte):
    """Estoque (headcount) no último dia de cada um dos últimos 24 meses, para comparar com o visual por mês."""
    out = []
    for md in m['medidas']:
        e = md.get('estoque')
        if not e:
            continue
        te = _tabela(m, e['entradas'][0])
        ts = _tabela(m, e['saidas'][0]) if e['saidas'] else None
        if te.get('fonte') != fonte['nome'] or (ts and ts.get('fonte') != fonte['nome']):
            continue
        ent = sql_nome(e['entradas'][1])
        cond = f'e.{ent} <= f.fim_do_mes'
        if e['fim']:
            fim = sql_nome(e['fim'][1])
            cond += f' AND (e.{fim} IS NULL OR e.{fim} > f.fim_do_mes)'
        conta = f'(SELECT COUNT_BIG(*) FROM {nome_view(m, te)} AS e WHERE {cond})'
        if ts:
            conta += (f'\n     - (SELECT COUNT_BIG(*) FROM {nome_view(m, ts)} AS s '
                      f'WHERE s.{sql_nome(e["saidas"][1])} <= f.fim_do_mes)')
        out.append(f"""-- {len(out) + 3}) {md['nome']}: estoque no último dia de cada mês (compare com o visual por mês, mês a mês)
WITH n AS (SELECT TOP (24) ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS k FROM sys.all_objects),
     f AS (SELECT EOMONTH(GETDATE(), -k) AS fim_do_mes FROM n)
SELECT {_lit(md['nome'])} AS indicador, f.fim_do_mes,
       {conta} AS total_no_banco
FROM f
ORDER BY f.fim_do_mes;
""")
    return out


def qualidade(m, fonte):
    """Checagens que derrubam ou distorcem a atualização, nas tabelas desta fonte. Esperado: tudo zero."""
    out = [_cabecalho(m, 'qualidade dos dados antes da primeira atualização', [
        'Cada linha deve trazer ocorrencias = 0. Diferente de zero:',
        '  chave_repetida  -> o Power BI recusa a relação (lado "um" com duplicata);',
        '  orfaos          -> linhas da fato sem par na dimensão (somem do corte, aparecem como "(Em branco)");',
        '  fora_calendario -> datas fora do intervalo do calendário (somem dos gráficos de tempo).'])]
    partes = []
    for r in m['relacionamentos']:
        de, para = _tabela(m, r['de']), _tabela(m, r['para'])
        if de.get('fonte') != fonte['nome'] or (para['origem'] and para.get('fonte') != fonte['nome']):
            continue                          # ligação com outra fonte: confere-se no Power BI
        rotulo = f'{r["de"]}[{r["de_coluna"]}] -> {r["para"]}[{r["para_coluna"]}]'
        if para['origem']:
            k = sql_nome(r['para_coluna'])
            partes.append(f"SELECT N'chave_repetida' AS checagem, {_lit(rotulo)} AS onde, COUNT_BIG(*) AS ocorrencias "
                          f'FROM (SELECT {k} FROM {nome_view(m, para)} GROUP BY {k} HAVING COUNT_BIG(*) > 1) AS x')
        if de['origem'] and para['origem']:
            kf, km = sql_nome(r['de_coluna']), sql_nome(r['para_coluna'])
            partes.append(f"SELECT N'orfaos' AS checagem, {_lit(rotulo)} AS onde, COUNT_BIG(*) AS ocorrencias FROM {nome_view(m, de)} AS f "
                          f'WHERE f.{kf} IS NOT NULL AND NOT EXISTS (SELECT 1 FROM {nome_view(m, para)} AS d '
                          f'WHERE d.{km} = f.{kf})')
        if de['origem'] and not para['origem'] and para.get('calendario'):
            k = sql_nome(r['de_coluna'])
            partes.append(f"SELECT N'fora_calendario' AS checagem, {_lit(rotulo)} AS onde, COUNT_BIG(*) AS ocorrencias FROM {nome_view(m, de)} "
                          f"WHERE {k} < '{para['inicio']}0101' OR {k} > '{para['fim']}1231'")
    out.append('\nUNION ALL\n'.join(partes) + ';' if partes else '-- Nenhum relacionamento para checar.')
    return '\n'.join(out) + '\n'
