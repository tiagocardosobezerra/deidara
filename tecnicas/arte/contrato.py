"""
O contrato de cada tipo de visual: o que o protótipo (C1) e o projeto Power BI (C3) leem do mesmo lugar.

O protótipo aprovado é o que o Power BI entrega. Quando cada lado decidia sozinho, divergia: a tabela de Pareto
saía em ordem no Power BI e fora de ordem no protótipo. Aqui ficam:

- `PAPEIS`: em que balde (bucket) do visual nativo vai cada campo do argila.json;
- `ordem(v, m)`: por qual campo o visual vem ordenado e em que sentido, a mesma regra nos dois lados.

O tipo do argila.json e o visual nativo de cada um ficam no motor (`TIPOS_VISUAL`), que os valida.
"""

from kibaku_nendo.especificacao import TIPOS_VISUAL, medida

# Papéis (buckets) de dados de cada visual nativo.
PAPEIS = {
    'card': {'valores': 'Values'},
    'gauge': {'valores': 'Y', 'meta': 'TargetValue'},
    'slicer': {'categoria': 'Values'},
    'tableEx': {'campos': 'Values'},
    'pivotTable': {'linhas': 'Rows', 'colunas': 'Columns', 'valores': 'Values'},
    'clusteredBarChart': {'categoria': 'Category', 'legenda': 'Series', 'valores': 'Y'},
    'clusteredColumnChart': {'categoria': 'Category', 'legenda': 'Series', 'valores': 'Y'},
    'lineChart': {'categoria': 'Category', 'legenda': 'Series', 'valores': 'Y'},
    'donutChart': {'categoria': 'Category', 'valores': 'Y'},
    'advancedSlicerVisual': {'categoria': 'Values'},
    'cardVisual': {'valores': 'Data'},
    'decompositionTreeVisual': {'valores': 'Analyze', 'linhas': 'ExplainBy'},
    'areaChart': {'categoria': 'Category', 'legenda': 'Series', 'valores': 'Y'},
    'azureMap': {'categoria': 'Category', 'legenda': 'Series', 'valores': 'Size'},
    'scatterChart': {'categoria': 'Category'},          # X, Y e Size saem de "valores", na ordem
    'columnChart': {'categoria': 'Category', 'legenda': 'Series', 'valores': 'Y'},
    'htmlContent443BE3AD55E043BF878BED274D3A6865': {'valores': 'content'},
    'deneb7E15AEF80B9E4D4F8E12924291ECE89A': {'categoria': 'dataset', 'valores': 'dataset'},
}

CRESCENTE, DECRESCENTE = 'Ascending', 'Descending'


def ordem(v, m=None):
    """(campo, sentido) com que o visual vem ordenado, ou None (a ordem da própria categoria: o tempo, o eixo)."""
    nativo = TIPOS_VISUAL[v['tipo']]
    if nativo in ('clusteredBarChart', 'donutChart') and v.get('valores'):
        # barras e rosca: o maior primeiro; nas setas, pelo valor atual (o último da lista)
        return (v['valores'][-1] if v['tipo'] == 'setas' else v['valores'][0]), DECRESCENTE
    if nativo == 'tableEx' and m:
        for c in v.get('campos') or []:      # Pareto e posição só fazem sentido do maior para o menor
            if c and c['tipo'] == 'medida' and (medida(m, c['nome']) or {}).get('tipo') in ('pareto', 'posicao'):
                return c, CRESCENTE
    return None


def grade_dos_botoes(v, largura, alta=True):
    """(colunas, linhas) dos botões de opções conhecidas (grupo de cálculo): numa faixa baixa, todos numa linha; numa
    caixa alta, tantas colunas quantas cabem com a letra de 10 pt inteira ("Acumulado no ano"), e as linhas que
    precisar. O layout reserva a altura e o PBIR monta a grade com a mesma conta. None: opções desconhecidas."""
    if not v.get('opcoes'):
        return None
    n = len(v['opcoes'])
    if not alta:
        return n, 1
    por_coluna = 0.75 * 10 * max(len(o) for o in v['opcoes']) + 24
    colunas = max(1, min(n, int(largura // por_coluna)))
    return colunas, -(-n // colunas)


def altura_dos_botoes(v, largura, padrao):
    """A altura que os botões pedem numa coluna de filtros (34 px por linha mais o respiro)."""
    grade = grade_dos_botoes(v, largura)
    return max(padrao, 34 * grade[1] + 30) if grade else padrao

