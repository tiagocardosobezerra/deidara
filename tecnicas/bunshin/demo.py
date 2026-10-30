"""
Projeto de demonstração: linhas fictícias embutidas no próprio .pbip.

`deidara.py gerar ... --demo` troca a origem de cada tabela (a view do SQL
Server, a consulta Power Query) por uma tabela escrita no projeto
(`#table` do Power Query), com os MESMOS nomes de coluna. Medidas,
relacionamentos e páginas são os do projeto real, então o Power BI calcula
tudo de verdade, sem banco nenhum: serve para testar o painel, clicar,
filtrar e mostrar ao gestor antes de a fonte estar pronta.

As linhas são inventadas, nunca lidas de lugar nenhum, e coerentes entre si:
- cada chave estrangeira aponta para uma chave que existe na tabela-mãe;
- uma tabela que é mãe de uma fato e filha de dimensões (o cadastro de
  pessoas, de contratos) vira uma entidade com algumas centenas de linhas;
- um evento com data ligado a uma entidade com data (o desligamento de um
  colaborador) acontece uma vez por entidade e sempre depois da data dela;
- a tabela que só aponta para uma dimensão, sem data (metas por empresa),
  ganha uma linha por linha da mãe;
- nada passa da data de hoje.
"""

import datetime
import random

from kibaku_nendo.util import M_POR_FAMILIA, m_texto

LINHAS_DIMENSAO = 8
LINHAS_ENTIDADE = 600
LINHAS_FATO = 900
FRACAO_EVENTO = 0.35


def campo_do_modelo(nome):
    return '#"' + nome.replace('"', '""') + '"'


def _literal(v, familia):
    if v is None:
        return 'null'
    if familia == 'data':
        return f'#date({v.year}, {v.month}, {v.day})'
    if familia == 'datahora':
        return f'#datetime({v.year}, {v.month}, {v.day}, 0, 0, 0)'
    if familia == 'logico':
        return 'true' if v else 'false'
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        return repr(v)
    return m_texto(str(v))


def _ordem(tabelas, rels):
    """As mães antes das filhas."""
    feitas, ordem = set(), []
    pendentes = list(tabelas)
    while pendentes:
        for t in list(pendentes):
            pais = {r['para'] for r in rels if r['de'] == t['nome'] and r['para'] != t['nome']}
            if pais <= feitas or not any(p['nome'] in pais for p in pendentes):
                ordem.append(t)
                feitas.add(t['nome'])
                pendentes.remove(t)
                break
        else:                                        # ciclo: segue na ordem do argila.json
            ordem += pendentes
            break
    return ordem


def linhas(m, semente='deidara'):
    """{tabela: [ {coluna: valor} ]} para todas as tabelas menos o calendário."""
    rng = random.Random(semente)
    cal = next((t for t in m['tabelas'] if t.get('calendario')), None)
    hoje = datetime.date.today()
    fim = min(datetime.date(cal['fim'], 12, 31), hoje) if cal else hoje
    inicio = datetime.date(cal['inicio'], 1, 1) if cal else fim - datetime.timedelta(days=3 * 365)
    tabelas = [t for t in m['tabelas'] if not t.get('calendario') and not t.get('auxiliar')]
    nomes = {t['nome'] for t in tabelas}
    rels = [r for r in m['relacionamentos'] if r['de'] in nomes and r['para'] in nomes]
    dados = {}
    for t in _ordem(tabelas, rels):
        pais = [r for r in rels if r['de'] == t['nome']]
        filhos = [r for r in rels if r['para'] == t['nome']]
        datas = [c for c in t['colunas'] if c['familia'] in ('data', 'datahora')]
        chaves = {r['para_coluna'] for r in filhos}
        chaves |= {c['nome'] for c in t['colunas'] if c.get('origem') and c['origem'].upper() in
                   {x.upper() for x in t.get('pk') or []}}
        chaves -= {r['de_coluna'] for r in pais}
        mae_com_data = next((r for r in pais if any(c['familia'] in ('data', 'datahora')
                                                     for c in _tab(m, r['para'])['colunas'])), None)
        base = None                                  # linhas da mãe que cada linha desta acompanha
        if not pais:
            n = LINHAS_DIMENSAO
        elif filhos:
            n = LINHAS_ENTIDADE
        elif datas and mae_com_data:
            mae = dados[mae_com_data['para']]
            col_data_mae = next(c['nome'] for c in _tab(m, mae_com_data['para'])['colunas']
                                if c['familia'] in ('data', 'datahora'))
            candidatas = [x for x in mae if x[col_data_mae] and x[col_data_mae] <= fim - datetime.timedelta(days=60)]
            n = min(len(candidatas), max(1, int(len(mae) * FRACAO_EVENTO)))
            base = (mae_com_data, col_data_mae, rng.sample(candidatas, n))
        elif not datas and len(pais) == 1:
            n = len(dados[pais[0]['para']])
            base = (pais[0], None, list(dados[pais[0]['para']]))
        else:
            n = LINHAS_FATO
        out = []
        for k in range(n):
            linha = {}
            for r in pais:
                if base and r is base[0]:
                    mae_linha = base[2][k]
                else:
                    mae_linha = rng.choice(dados[r['para']]) if dados.get(r['para']) else {}
                linha[r['de_coluna']] = mae_linha.get(r['para_coluna'])
                if base and r is base[0]:
                    linha['_mae'] = mae_linha
            for c in t['colunas']:
                if c['nome'] in linha:
                    continue
                linha[c['nome']] = _valor(rng, t, c, k, n, chaves, inicio, fim, linha.get('_mae'),
                                          base[1] if base else None)
            linha.pop('_mae', None)
            out.append(linha)
        dados[t['nome']] = out
    return dados


def _tab(m, nome):
    return next(t for t in m['tabelas'] if t['nome'] == nome)


def _valor(rng, t, c, k, n, chaves, inicio, fim, mae, col_data_mae):
    fam = c['familia']
    if c['nome'] in chaves:
        return k + 1 if fam in ('inteiro', 'decimal', 'real') else f'{k + 1:03d}'
    if fam in ('data', 'datahora'):
        if mae is not None and col_data_mae and mae.get(col_data_mae):
            ini = mae[col_data_mae] + datetime.timedelta(days=60)
            return ini + datetime.timedelta(days=rng.randint(0, max(0, (fim - ini).days)))
        if n >= LINHAS_ENTIDADE:                   # entradas antigas: o estoque começa cheio
            ini = inicio - datetime.timedelta(days=6 * 365)
            return ini + datetime.timedelta(days=int(rng.triangular(0, (fim - ini).days, (fim - ini).days * 0.35)))
        return inicio + datetime.timedelta(days=rng.randint(0, max(0, (fim - inicio).days)))
    if fam == 'texto':
        if n > 26:
            return f'{c["nome"]} {k + 1:03d}'
        return f'{c["nome"]} {chr(65 + k)}'
    if fam == 'logico':
        return rng.random() < 0.5
    if c.get('formato') == 'percentual':
        return round(rng.uniform(0.12, 0.32), 3)
    if c.get('formato') == 'moeda' or fam == 'decimal':
        return round(rng.uniform(2500, 18000), 2)
    if fam == 'inteiro':
        return rng.randint(1, 100)
    return round(rng.uniform(1, 1000), 2)


def expressoes(m, semente='deidara'):
    """{tabela: expressão M com as linhas fictícias} (nomes de coluna = os do modelo)."""
    out = {}
    for nome, rows in linhas(m, semente).items():
        t = _tab(m, nome)
        tipo = ', '.join(f'{campo_do_modelo(c["nome"])} = {M_POR_FAMILIA.get(c["familia"], "type text").replace("type ", "")}'
                         for c in t['colunas'])
        corpo = ',\n'.join('        {' + ', '.join(_literal(r.get(c['nome']), c['familia']) for c in t['colunas']) + '}'
                           for r in rows)
        out[nome] = (f'let\n    // DEMONSTRAÇÃO: {len(rows)} linha(s) fictícia(s) geradas pelo Deidara, sem fonte de dados\n'
                     f'    Dados = #table(\n        type table [{tipo}],\n        {{\n{corpo}\n        }})\nin\n    Dados')
    return out
