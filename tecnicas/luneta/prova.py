"""
Receita de prova: confirma (ou derruba) uma ligação candidata medindo-a na
fonte. Devolve só números AGREGADOS, nunca uma linha de dado:

- pct_nulos_filha     % das linhas da filha com o código em branco;
- pct_linhas_com_par  % das linhas da filha (com código) que acham par na mãe;
- pct_codigos_com_par % dos códigos distintos da filha que existem na mãe;
- mae_unica           sim/não: o código é único na mãe (senão o Power BI recusa a relação 1:*).

É a única receita que lê conteúdo (para contar), e por isso só devolve
percentuais arredondados e sim/não. Mesmo SQL Server nas duas pontas: SQL no
SSMS. Fontes diferentes (planilha x ERP): Power Query, que lê o SQL Server
direto e a planilha pela consulta que já existe no arquivo.
"""

import datetime

from kibaku_nendo.util import m_texto, sql_nome

LIMITES = {'provada': 99.0, 'ressalva': 90.0}


def _sql_chave(alias, coluna):
    return f"NULLIF(RTRIM(CONVERT(nvarchar(100), {alias}.{sql_nome(coluna)})), N'')"


def receita_sql(de, para, esquema_de, esquema_para):
    """`de`/`para`: (origem, coluna, rótulo)."""
    (td, cd, rd), (tp, cp, rp) = de, para
    return f"""/*
  Deidara — receita de PROVA da ligação {rd} -> {rp}
  Devolve só percentuais e sim/não (nenhuma linha de dado).
  Rode no SSMS com o banco certo, copie a grade com cabeçalho para um .txt e:
  python3 deidara.py provar --de resultado.txt
*/
SET NOCOUNT ON;
WITH filha AS (
    SELECT {_sql_chave('t', cd)} AS k FROM {sql_nome(esquema_de)}.{sql_nome(td)} AS t
),
mae AS (
    SELECT DISTINCT {_sql_chave('t', cp)} AS k FROM {sql_nome(esquema_para)}.{sql_nome(tp)} AS t
)
SELECT
    N'{rd.replace("'", "''")}' AS de,
    N'{rp.replace("'", "''")}' AS para,
    a.pct_nulos_filha, a.pct_linhas_com_par, c.pct_codigos_com_par, u.mae_unica
FROM (
    SELECT
        CAST(100.0 * SUM(CASE WHEN f.k IS NULL THEN 1 ELSE 0 END) / NULLIF(COUNT_BIG(*), 0) AS decimal(5,1)) AS pct_nulos_filha,
        CAST(100.0 * SUM(CASE WHEN f.k IS NOT NULL AND m.k IS NOT NULL THEN 1 ELSE 0 END)
             / NULLIF(SUM(CASE WHEN f.k IS NOT NULL THEN 1 ELSE 0 END), 0) AS decimal(5,1)) AS pct_linhas_com_par
    FROM filha AS f
    LEFT JOIN mae AS m ON m.k = f.k
) AS a
CROSS JOIN (
    SELECT CAST(100.0 * SUM(CASE WHEN m.k IS NOT NULL THEN 1 ELSE 0 END) / NULLIF(COUNT_BIG(*), 0) AS decimal(5,1))
           AS pct_codigos_com_par
    FROM (SELECT DISTINCT k FROM filha WHERE k IS NOT NULL) AS d
    LEFT JOIN mae AS m ON m.k = d.k
) AS c
CROSS JOIN (
    SELECT CASE WHEN EXISTS (
        SELECT 1 FROM {sql_nome(esquema_para)}.{sql_nome(tp)} AS t
        WHERE t.{sql_nome(cp)} IS NOT NULL
        GROUP BY t.{sql_nome(cp)} HAVING COUNT_BIG(*) > 1
    ) THEN N'nao' ELSE N'sim' END AS mae_unica
) AS u;
"""


def _m_lista(ponta):
    """Expressão M que devolve a coluna da ponta como lista. `ponta`: dict com
    tipo da fonte, origem, coluna e, para SQL Server, servidor/banco/esquema."""
    col = m_texto(ponta['coluna'])
    if ponta['tipo'] == 'sqlserver':
        tabela = (f'Sql.Database({m_texto(ponta["servidor"])}, {m_texto(ponta["banco"])})'
                  f'{{[Schema={m_texto(ponta["esquema"])}, Item={m_texto(ponta["origem"])}]}}[Data]')
    else:
        tabela = '#' + m_texto(ponta['origem'])
    return f'Table.Column({tabela}, {col})'


def receita_m(de, para):
    """`de`/`para`: dict(tipo, origem, coluna, rotulo, servidor, banco, esquema)."""
    consultas = [p['origem'] for p in (de, para) if p['tipo'] != 'sqlserver']
    onde = (f'no arquivo (Power BI ou Excel) que já tem a(s) consulta(s): {", ".join(consultas)}' if consultas
            else 'em qualquer Power BI ou Excel')
    return f"""// Deidara — receita de PROVA da ligação {de['rotulo']} -> {para['rotulo']}
// Devolve só percentuais e sim/não (nenhuma linha de dado).
// Rode numa consulta nula {onde}; o SQL Server é lido direto.
// Copie a tabela inteira para um .txt e: python3 deidara.py provar --de resultado.txt
let
    Norm = (v) => if v = null then null else let t = Text.Trim(Text.From(v)) in if t = "" then null else t,
    Filha = List.Buffer(List.Transform({_m_lista(de)}, Norm)),
    Mae = List.Buffer(List.Transform({_m_lista(para)}, Norm)),
    MaeSemNulo = List.RemoveNulls(Mae),
    MaeDistinta = List.Buffer(List.Distinct(MaeSemNulo)),
    FilhaComCodigo = List.RemoveNulls(Filha),
    Pct = (a, b) => if b = 0 then null else Number.Round(100 * a / b, 1),
    ComPar = List.Count(List.Select(FilhaComCodigo, each List.Contains(MaeDistinta, _))),
    CodigosFilha = List.Distinct(FilhaComCodigo),
    CodigosComPar = List.Count(List.Select(CodigosFilha, each List.Contains(MaeDistinta, _))),
    Resultado = #table(
        {{"de", "para", "pct_nulos_filha", "pct_linhas_com_par", "pct_codigos_com_par", "mae_unica"}},
        {{{{{m_texto(de['rotulo'])}, {m_texto(para['rotulo'])},
          Pct(List.Count(Filha) - List.Count(FilhaComCodigo), List.Count(Filha)),
          Pct(ComPar, List.Count(FilhaComCodigo)),
          Pct(CodigosComPar, List.Count(CodigosFilha)),
          if List.Count(MaeSemNulo) = List.Count(MaeDistinta) then "sim" else "nao"}}}})
in
    Resultado
"""


def _num(v):
    try:
        return float(str(v).strip().replace('%', '').replace(',', '.'))
    except ValueError:
        return None


def ler(linhas):
    """Linhas coladas do resultado -> [prova]. Cada prova: de, para, percentuais, mae_unica."""
    out = []
    for l in linhas:
        if not l.get('de'):
            continue
        out.append({'de': l['de'], 'para': l.get('para', ''),
                    'pct_nulos_filha': _num(l.get('pct_nulos_filha')),
                    'pct_linhas_com_par': _num(l.get('pct_linhas_com_par')),
                    'pct_codigos_com_par': _num(l.get('pct_codigos_com_par')),
                    'mae_unica': str(l.get('mae_unica', '')).strip().lower() in ('sim', 'true', 'verdadeiro', '1', 's'),
                    'em': datetime.datetime.now().strftime('%d/%m/%Y')})
    return out


def avaliar(p):
    """(veredito, explicação) de uma prova."""
    if not p['mae_unica']:
        return 'reprovada', 'o código se repete no lado "um": o Power BI recusa a relação (trate a duplicidade na origem)'
    pct = p['pct_linhas_com_par']
    if pct is None:
        return 'inconclusiva', 'a filha não tem nenhum código preenchido'
    if pct >= LIMITES['provada']:
        return 'provada', f'{_br(pct)}% das linhas acham par e o código é único na mãe'
    if pct >= LIMITES['ressalva']:
        return 'provada com ressalva', (f'{_br(100 - pct)}% das linhas NÃO acham par: elas somem dos cortes por '
                                        'essa dimensão (aparecem como "(Em branco)")')
    return 'fraca', f'só {_br(pct)}% das linhas acham par: provavelmente não é esta a ligação, ou os códigos diferem'


def _br(x):
    return f'{x:.1f}'.replace('.', ',')


def texto(p):
    v, _ = avaliar(p)
    return (f'{v} em {p["em"]}: {_br(p["pct_linhas_com_par"] or 0)}% com par, '
            f'chave {"única" if p["mae_unica"] else "REPETIDA"} na mãe')
