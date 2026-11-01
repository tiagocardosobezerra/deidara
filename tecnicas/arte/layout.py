"""
Posição de cada visual na página (1280 x 720, o padrão 16:9 do Power BI).

O protótipo e o relatório do Power BI usam esta MESMA função: o que foi
aprovado no protótipo é o que sai no .pbip.

Ordem fixa por faixas: segmentadores no topo, cartões e medidores logo
abaixo, gráficos numa grade de duas colunas e tabelas/matrizes em largura
inteira no fim.
"""

LARGURA, ALTURA = 1280, 720
MARGEM, ESPACO = 16, 12
TITULO = 48              # faixa do título da página


def posicionar(visuais):
    """Devolve [(visual, {'x','y','w','h'})] na ordem de leitura."""
    from tecnicas.arte.modelos import GRAF, KPI, SEG, peso_do_filtro
    seg = [v for v in visuais if v['tipo'] in SEG]
    kpi = [v for v in visuais if v['tipo'] in KPI]
    graf = [v for v in visuais if v['tipo'] in GRAF]
    tab = [v for v in visuais if v['tipo'] in ('tabela', 'matriz')]
    util = LARGURA - 2 * MARGEM
    y = TITULO
    out = []

    def faixa(itens, altura, por_linha, peso=lambda v: 1):
        nonlocal y
        for i in range(0, len(itens), por_linha):
            linha = itens[i:i + por_linha]
            if len(linha) == 1 and len(itens) > 1 and linha[0]['tipo'] == 'imagem':
                linha_w = [(util - ESPACO) / 2]         # a imagem SVG sozinha na linha não estica: cortaria o desenho
            else:
                livre = util - ESPACO * (len(linha) - 1)
                total = sum(peso(v) for v in linha)
                linha_w = [livre * peso(v) / total for v in linha]
            # a imagem SVG (dispersão, espinha) é 4:3 e o Power BI ajusta pela largura: a linha cresce com ela
            alto = max([altura] + [w * 0.75 for v, w in zip(linha, linha_w) if v['tipo'] == 'imagem'])
            x = float(MARGEM)
            for v, w in zip(linha, linha_w):
                out.append((v, {'x': x, 'y': y, 'w': w, 'h': alto}))
                x += w + ESPACO
            y += alto + ESPACO

    # os botões ganham a largura das opções (peso_do_filtro), como na faixa dos modelos
    filtros = [v for v in seg if v['tipo'] != 'aviso']
    # botões dos itens de uma coluna (quantos, só o Power BI sabe) vão em até três linhas: a faixa cresce
    faixa(filtros, 84 if any(v['tipo'] == 'botoes' and not v.get('opcoes') for v in filtros) else 56, 6, peso_do_filtro)
    faixa([v for v in kpi if v['tipo'] == 'cartao'] + [v for v in kpi if v['tipo'] == 'medidor'], 104, 6)
    faixa([v for v in kpi if v['tipo'] == 'cartoes'], 120, 1)
    faixa([v for v in seg if v['tipo'] == 'aviso'], 56, 1)
    faixa([v for v in kpi if v['tipo'] == 'abas'], 80, 1)
    resto = ALTURA - MARGEM - y
    linhas_graf = (len(graf) + 1) // 2
    blocos = linhas_graf + len(tab)
    if blocos:
        h = max(200, (resto - ESPACO * (blocos - 1)) / blocos)
        faixa(graf, h, 2)
        faixa(tab, h, 1)
    return [(v, {k: round(n, 2) for k, n in pos.items()}) for v, pos in out]


def altura_da_pagina(posicoes):
    """A página cresce (rolagem vertical) quando os visuais não cabem em 720."""
    fim = max([p['y'] + p['h'] for _, p in posicoes] or [ALTURA])
    return max(ALTURA, int(round(fim + MARGEM)))
