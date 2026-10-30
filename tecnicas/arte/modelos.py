"""
Modelos de layout: onde cada visual fica, o fundo desenhado da página e a
navegação entre páginas.

Os onze modelos foram tirados da estrutura de dashboards do repositório
Power BI Design Files, de Sajjad Ahmadi (licença MIT; ver
LICENCAS-DE-TERCEIROS.md e referencias/modelos.md). A técnica é a dele: um
fundo desenhado com os painéis, o título e a navegação, e os visuais nativos
transparentes por cima. O fundo aqui é gerado pelo Deidara para cada painel
(a pergunta da página, as cores do tema), nunca a imagem original.

O protótipo e o .pbip usam ESTA mesma montagem: o que foi aprovado é o que sai.
"""

import html

from tecnicas.arte.layout import LARGURA as LARGURA_PADRAO, altura_da_pagina, posicionar

MODELOS = {
    'padrao': 'O layout simples de sempre (1280 x 720), sem fundo desenhado',
    'faixa-de-kpis': 'Trilho de ícones, título com filtros no canto, linha de KPIs, gráficos ao lado da tabela',
    'coluna-de-kpis': 'Barra de filtros, coluna de KPIs à esquerda, grade de gráficos e abas no rodapé',
    'secoes-com-rolagem': 'Barra lateral com KPIs e filtros; resumo e seções com rolagem',
    'trilho-escuro': 'Trilho escuro de páginas, faixa única de KPIs, dois painéis e tabela larga',
    'kpis-clicaveis': 'Menu lateral e KPIs clicáveis: o KPI escolhido muda o gráfico e a tabela',
    'historia-longa': 'Uma página longa e escura, lida como história, seção por seção',
    'executivo': 'Linha de até cinco KPIs e um gráfico principal em largura total, o resto embaixo',
    'mapa-central': 'O mapa (ou o gráfico principal) no centro, KPIs à esquerda, minigráficos à direita, tabelas embaixo',
    'causa-raiz': 'Coluna de filtros, linha de KPIs e a árvore de decomposição em destaque, com o detalhe embaixo',
    'tabela-lateral': 'Faixa de KPIs, gráficos à esquerda e uma tabela alta à direita',
    'equipes': 'Painel lateral com KPIs, filtros e páginas; minigráficos no topo e um gráfico principal grande',
}
ESCURO = {'fundo': '#0F1420', 'texto': '#E6EAF2',
          'cores': ['#4CC9F0', '#F8961E', '#90BE6D', '#F94144', '#F9C74F', '#B5A3FF', '#43AA8B', '#FF8FAB']}
W = 1920
H = 1080
DICA_W, DICA_H = 320, 240                                  # página de dica (tooltip)
GAP = 16
SEG = ('segmentador', 'botoes', 'alternar', 'aviso')     # o aviso fica no canto de cima, como uma notificação
KPI = ('cartao', 'medidor', 'cartoes', 'abas')
GRAF = ('barras', 'colunas', 'linha', 'rosca', 'area', 'dispersao', 'decomposicao', 'mapa', 'skyline', 'setas', 'imagem',
        'html', 'vegalite')
TAB = ('tabela', 'matriz')


# ----------------------------------------------------------------- páginas do relatório
def paginas_do_relatorio(m):
    """As páginas que saem no relatório. Em geral, uma por página do argila.json; os KPIs clicáveis
    ganham uma página escondida por KPI; a história junta todas numa página só."""
    modelo = m.get('modelo') or 'padrao'
    pgs = m['paginas']
    if modelo == 'historia-longa':
        return [{'nome': m['projeto'], 'descricao': m.get('descricao') or '', 'visuais': [v for p in pgs for v in p['visuais']],
                 'oculta': False, 'grupo': 0, 'secoes': pgs, 'kpi_ativo': None,
                 'ajuda': any(p.get('ajuda') for p in pgs)}]
    out = []
    for g, pg in enumerate(pgs):
        escondida = bool(pg.get('dica') or pg.get('detalhe'))     # dica e detalhe não entram na navegação
        base = {'nome': pg['nome'], 'descricao': pg.get('descricao') or '', 'visuais': pg['visuais'],
                'oculta': escondida, 'grupo': g, 'kpi_ativo': None, 'ajuda': pg.get('ajuda', False),
                'dica': pg.get('dica', False), 'detalhe': pg.get('detalhe')}
        cards = [v for v in pg['visuais'] if v['tipo'] == 'cartao']
        if modelo != 'kpis-clicaveis' or not cards or escondida:
            out.append(base)
            continue
        for k, card in enumerate(cards):
            out.append(dict(base, nome=pg['nome'] if k == 0 else f'{pg["nome"]} · {card["valores"][0]["nome"]}',
                            oculta=k > 0, kpi_ativo=k, visuais=_com_kpi(pg['visuais'], card), ajuda=base['ajuda'] and k == 0))
    return out


def _com_kpi(visuais, card):
    """O gráfico principal e a tabela principal passam a mostrar o KPI do cartão escolhido."""
    md = card['valores'][0]
    out, graf_ok, tab_ok = [], False, False
    for v in visuais:
        if v['tipo'] in GRAF and not graf_ok:
            v = dict(v, valores=[md], legenda=None, titulo=f'{md["nome"]} por {v["categoria"]["nome"]}' if v.get('categoria') else md['nome'])
            graf_ok = True
        elif v['tipo'] == 'tabela' and not tab_ok:
            cols = [c for c in v['campos'] if c and c['tipo'] == 'coluna'][:1]
            if cols:
                v = dict(v, campos=cols + [md], titulo=f'{md["nome"]} por {cols[0]["nome"]}')
                tab_ok = True
        out.append(v)
    return out


# ----------------------------------------------------------------- fundo desenhado
class Fundo:
    def __init__(self, w, h, cor):
        self.w, self.h, self.p = w, h, [f'<rect width="{w}" height="{h}" fill="{cor}"/>']

    def ret(self, x, y, w, h, cor, rx=0, borda=None, op=1):
        b = f' stroke="{borda}" stroke-width="1.5"' if borda else ''
        o = f' fill-opacity="{op}"' if op != 1 else ''
        self.p.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" rx="{rx}" fill="{cor}"{o}{b}/>')

    def txt(self, x, y, s, tam, cor, peso=400, ancora='start'):
        self.p.append(f'<text x="{x:.0f}" y="{y:.0f}" font-family="Segoe UI, Segoe UI Semibold, Arial, sans-serif" '
                      f'font-size="{tam}" font-weight="{peso}" fill="{cor}" text-anchor="{ancora}">{html.escape(str(s))}</text>')

    def circ(self, cx, cy, r, cor, borda=None):
        b = f' stroke="{borda}" stroke-width="2"' if borda else ''
        self.p.append(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r}" fill="{cor}"{b}/>')

    def svg(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">'
                + ''.join(self.p) + '</svg>')


def _quebra(s, n):
    linhas, atual = [], ''
    for p in (s or '').split():
        if len(atual) + len(p) + 1 > n and atual:
            linhas.append(atual)
            atual = p
        else:
            atual = f'{atual} {p}'.strip()
    return linhas + ([atual] if atual else [])


def _cores(m):
    t = m['tema']
    escuro = t['fundo'].upper() in ('#0F1420',) or _luz(t['fundo']) < 0.3
    return {'acento': t['cores'][0], 'texto': t['texto'], 'mudo': '#9AA4B8' if escuro else '#5B6472',
            'painel': '#1A2130' if escuro else '#FFFFFF', 'borda': '#2A3346' if escuro else '#E4E7EC',
            'pagina': t['fundo'] if escuro else '#F3F5F8', 'escuro': escuro}


def _luz(c):
    c = c.lstrip('#')
    if len(c) == 3:
        c = ''.join(x * 2 for x in c)
    r, g, b = (int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


# ----------------------------------------------------------------- ferramentas de grade
def _em_linha(itens, x, y, w, h, gap=GAP):
    if not itens:
        return []
    lw = (w - gap * (len(itens) - 1)) / len(itens)
    return [(v, {'x': x + k * (lw + gap), 'y': y, 'w': lw, 'h': h}) for k, v in enumerate(itens)]


def _em_coluna(itens, x, y, w, h, gap=GAP):
    if not itens:
        return []
    lh = (h - gap * (len(itens) - 1)) / len(itens)
    return [(v, {'x': x, 'y': y + k * (lh + gap), 'w': w, 'h': lh}) for k, v in enumerate(itens)]


def _grade(itens, x, y, w, colunas, altura, gap=GAP):
    out = []
    for i in range(0, len(itens), colunas):
        out += _em_linha(itens[i:i + colunas], x, y, w, altura, gap)
        y += altura + gap
    return out, y


def _separar(visuais):
    return ([v for v in visuais if v['tipo'] in SEG], [v for v in visuais if v['tipo'] in KPI],
            [v for v in visuais if v['tipo'] in GRAF], [v for v in visuais if v['tipo'] in TAB])


def _filtros_no_canto(seg, direita, y, h, area):
    if not seg:
        return []
    pesos = [(3 if v.get('imagem') or v.get('icone') else 2.2) if v['tipo'] == 'botoes' else 0.9 if v['tipo'] == 'alternar'
             else 3 if v['tipo'] == 'aviso' else 1
             for v in seg]      # botões precisam de largura para as opções
    un = min(210, (area - GAP * (len(seg) - 1)) / sum(pesos))
    x = direita - un * sum(pesos) - GAP * (len(seg) - 1)
    out = []
    for v, p in zip(seg, pesos):
        out.append((v, {'x': x, 'y': y, 'w': un * p, 'h': h}))
        x += un * p + GAP
    return out


def _paineis(f, posicoes, c, pula=SEG):
    for v, p in posicoes:
        if v['tipo'] not in pula:
            f.ret(p['x'] - 6, p['y'] - 6, p['w'] + 12, p['h'] + 12, c['painel'], 14, c['borda'])


# ----------------------------------------------------------------- os modelos
def montar(m, paginas, i):
    """{'w','h','posicoes':[(v,pos)],'fundo': svg|None,'nav':[{x,y,w,h,alvo,rotulo}],'escuro','sem_titulo': set(ids)}"""
    modelo = m.get('modelo') or 'padrao'
    pg = paginas[i]
    if pg.get('dica'):                               # página de dica: 320 x 240, um visual embaixo do outro
        n = max(1, len(pg['visuais']))
        alto = (DICA_H - 8 * (n + 1)) / n
        pos = [(v, {'x': 8, 'y': 8 + k * (alto + 8), 'w': DICA_W - 16, 'h': alto}) for k, v in enumerate(pg['visuais'])]
        return {'w': DICA_W, 'h': DICA_H, 'posicoes': pos, 'fundo': None, 'nav': [], 'escuro': False, 'sem_titulo': set()}
    if modelo == 'padrao':
        pos = posicionar(pg['visuais'])
        return {'w': LARGURA_PADRAO, 'h': altura_da_pagina(pos), 'posicoes': pos, 'fundo': None, 'nav': [],
                'escuro': False, 'sem_titulo': set()}
    c = _cores(m)
    r = {'faixa-de-kpis': _faixa, 'coluna-de-kpis': _coluna, 'secoes-com-rolagem': _secoes,
         'trilho-escuro': _trilho, 'kpis-clicaveis': _clicaveis, 'historia-longa': _historia,
         'executivo': _executivo, 'mapa-central': _mapa_central, 'causa-raiz': _causa_raiz,
         'tabela-lateral': _tabela_lateral, 'equipes': _equipes}[modelo](m, paginas, i, c)
    r['escuro'] = c['escuro']
    if m.get('_demo') and r['fundo']:
        selo = (f'<rect x="{r["w"] - 300}" y="{r["h"] - 40}" width="284" height="30" rx="15" fill="#FFF4CE"/>'
                f'<text x="{r["w"] - 158}" y="{r["h"] - 20}" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" '
                f'font-size="15" font-weight="600" fill="#8A6100">Demonstração · dados fictícios</text>')
        r['fundo'] = r['fundo'].replace('</svg>', selo + '</svg>')
    r['posicoes'] = [(v, {k: round(n, 1) for k, n in p.items()}) for v, p in r['posicoes']]
    for n in r['nav']:
        for k in ('x', 'y', 'w', 'h'):
            n[k] = round(n[k], 1)
    r.setdefault('sem_titulo', set())
    return r


def _visiveis(paginas):
    return [(k, p) for k, p in enumerate(paginas) if not p['oculta']]


def _ativa(paginas, i):
    return paginas[i]['grupo']


def _cabecalho(f, pg, x, y, c, tam=34, largura=60):
    f.txt(x, y, pg['nome'], tam, c['texto'], 700)
    for k, linha in enumerate(_quebra(pg['descricao'], largura)[:2]):
        f.txt(x, y + 32 + k * 22, linha, 17, c['mudo'])


def _altura(*fins):
    return max(H, int(max(fins) + 32))


def _faixa(m, paginas, i, c):
    pg = paginas[i]
    seg, kpi, graf, tab = _separar(pg['visuais'])
    pos = _filtros_no_canto(seg, 1880, 34, 64, 1100)
    y = 140
    if kpi:
        pos += _em_linha(kpi[:6], 120, y, 1760, 196)
        pos += _em_linha(kpi[6:], 120, y + 212, 1760, 196) if kpi[6:] else []
        y += 212 * (1 + bool(kpi[6:]))
    y += 16
    fim = y
    if graf and tab:
        linhas = (len(graf) + 1) // 2
        hg = max(280, (H - 32 - y - GAP * (linhas - 1)) / linhas)
        g, fim1 = _grade(graf, 120, y, 780, 2, hg)
        hT = max(320, (H - 32 - y - GAP * (len(tab) - 1)) / len(tab))
        t = _em_coluna(tab, 920, y, 960, hT * len(tab) + GAP * (len(tab) - 1))
        pos += g + t
        fim = max(fim1 - GAP, y + hT * len(tab) + GAP * (len(tab) - 1))
    elif graf:
        cols = 2 if len(graf) <= 2 or len(graf) == 4 else 3
        linhas = (len(graf) + cols - 1) // cols
        hg = max(300, (H - 32 - y - GAP * (linhas - 1)) / linhas)
        g, fim = _grade(graf, 120, y, 1760, cols, hg)
        pos += g
        fim -= GAP
    elif tab:
        hT = max(320, (H - 32 - y - GAP * (len(tab) - 1)) / len(tab))
        pos += _em_coluna(tab, 120, y, 1760, hT * len(tab) + GAP * (len(tab) - 1))
        fim = y + hT * len(tab)
    h = _altura(fim, y)
    f = Fundo(W, h, c['pagina'])
    f.ret(0, 0, 88, h, c['painel'], 0, c['borda'])
    _cabecalho(f, pg, 120, 74, c)
    _paineis(f, pos, c)
    nav = []
    for k, (alvo, p) in enumerate(_visiveis(paginas)):
        cy = 150 + k * 84
        ativo = p['grupo'] == _ativa(paginas, i)
        f.circ(44, cy, 24, c['acento'] if ativo else c['pagina'], None if ativo else c['borda'])
        f.txt(44, cy + 7, k + 1, 20, '#FFFFFF' if ativo else c['mudo'], 700, 'middle')
        nav.append({'x': 16, 'y': cy - 28, 'w': 56, 'h': 56, 'alvo': alvo, 'rotulo': p['nome']})
    return {'w': W, 'h': h, 'posicoes': pos, 'fundo': f.svg(), 'nav': nav if len(nav) > 1 else []}


def _coluna(m, paginas, i, c):
    pg = paginas[i]
    seg, kpi, graf, tab = _separar(pg['visuais'])
    pos = _em_linha(seg[:5], 120, 22, min(5, len(seg)) * 236 - GAP, 68) if seg else []
    itens = graf + tab
    x0 = 360 if kpi else 32
    larg = 1888 - x0
    linhas = []
    if itens:
        linhas.append(itens[:2])
        resto = itens[2:]
        linhas += [resto[k:k + 3] for k in range(0, len(resto), 3)]
    rodape = 65
    disp = H - 130 - rodape - 24
    hl = max(300, (disp - GAP * (len(linhas) - 1)) / max(1, len(linhas)))
    y = 130
    for ln in linhas:
        if len(ln) == 2 and ln is linhas[0]:
            w1 = (larg - GAP) * 2 / 3
            pos += [(ln[0], {'x': x0, 'y': y, 'w': w1, 'h': hl}), (ln[1], {'x': x0 + w1 + GAP, 'y': y, 'w': larg - w1 - GAP, 'h': hl})]
        else:
            pos += _em_linha(ln, x0, y, larg, hl)
        y += hl + GAP
    h = max(H, int(y - GAP + 24 + rodape))
    if kpi:
        pos += _em_coluna(kpi[:5], 32, 130, 310, h - 130 - rodape - 24)
    f = Fundo(W, h, c['pagina'])
    f.ret(0, 0, W, 110, c['painel'], 0, c['borda'])
    f.txt(34, 62, 'Filtros', 18, c['mudo'], 600)
    f.txt(1888, 58, pg['nome'], 30, c['texto'], 700, 'end')
    if pg['descricao']:
        f.txt(1888, 88, _quebra(pg['descricao'], 70)[0], 16, c['mudo'], 400, 'end')
    _paineis(f, pos, c)
    f.ret(0, h - rodape, W, rodape, c['painel'], 0, c['borda'])
    nav = []
    vis = _visiveis(paginas)
    for k, (alvo, p) in enumerate(vis):
        x = 360 + k * 320
        ativo = p['grupo'] == _ativa(paginas, i)
        f.txt(x + 150, h - rodape + 40, p['nome'], 19, c['texto'] if ativo else c['mudo'], 700 if ativo else 400, 'middle')
        if ativo:
            f.ret(x + 30, h - rodape, 240, 5, c['acento'])
        nav.append({'x': x, 'y': h - rodape, 'w': 300, 'h': rodape, 'alvo': alvo, 'rotulo': p['nome']})
    return {'w': W, 'h': h, 'posicoes': pos, 'fundo': f.svg(), 'nav': nav if len(nav) > 1 else []}


def _secoes(m, paginas, i, c):
    pg = paginas[i]
    seg, kpi, graf, tab = _separar(pg['visuais'])
    pos = []
    y = 176
    pos += _em_coluna(kpi[:4], 24, y, 252, len(kpi[:4]) * 118 - GAP) if kpi else []
    y += len(kpi[:4]) * 118 + (24 if kpi else 0)
    pos += _em_coluna(seg, 24, y, 252, len(seg) * 80 - GAP) if seg else []
    x0, larg = 330, 1558
    y = 32
    secoes = []
    corpo = list(graf) + list(tab)
    if graf:
        pos.append((graf[0], {'x': x0, 'y': y, 'w': larg, 'h': 340}))
        y += 340 + 40
        corpo = graf[1:] + tab
    sem_titulo = set()
    for v in corpo:
        secoes.append((v['titulo'], y))
        hv = 420 if v['tipo'] in TAB else 360
        pos.append((v, {'x': x0, 'y': y + 66, 'w': larg, 'h': hv}))
        sem_titulo.add(id(v))
        y += 66 + hv + 40
    kpi_extra = kpi[4:]
    if kpi_extra:
        pos += _em_linha(kpi_extra, x0, y, larg, 160)
        y += 200
    h = max(H, int(y))
    f = Fundo(W, h, c['pagina'])
    f.ret(0, 0, 300, h, c['painel'], 0, c['borda'])
    f.txt(24, 64, pg['nome'], 28, c['texto'], 700)
    for k, linha in enumerate(_quebra(pg['descricao'], 30)[:3]):
        f.txt(24, 96 + k * 22, linha, 15, c['mudo'])
    for titulo, ys in secoes:
        f.ret(x0 - 6, ys, larg + 12, 52, c['painel'], 10, c['borda'])
        f.ret(x0 + 8, ys + 14, 6, 24, c['acento'], 3)
        f.txt(x0 + 28, ys + 34, titulo, 22, c['texto'], 700)
    _paineis(f, [(v, p) for v, p in pos if v['tipo'] not in KPI or p['x'] > 300], c)
    for v, p in pos:
        if v['tipo'] in KPI and p['x'] < 300:
            f.ret(p['x'] - 4, p['y'] - 4, p['w'] + 8, p['h'] + 8, c['pagina'], 12, c['borda'])
    nav = []
    vis = _visiveis(paginas)
    for k, (alvo, p) in enumerate(vis):
        yy = h - 60 - (len(vis) - 1 - k) * 52
        ativo = p['grupo'] == _ativa(paginas, i)
        if ativo:
            f.ret(16, yy - 34, 268, 46, c['acento'], 8)
        f.txt(32, yy - 4, p['nome'], 18, '#FFFFFF' if ativo else c['texto'], 600 if ativo else 400)
        nav.append({'x': 16, 'y': yy - 34, 'w': 268, 'h': 46, 'alvo': alvo, 'rotulo': p['nome']})
    if len(nav) > 1:
        f.txt(24, h - 60 - len(vis) * 52 - 4, 'Páginas', 14, c['mudo'], 700)
    return {'w': W, 'h': h, 'posicoes': pos, 'fundo': f.svg(), 'nav': nav if len(nav) > 1 else [],
            'sem_titulo': sem_titulo}


def _trilho(m, paginas, i, c):
    pg = paginas[i]
    seg, kpi, graf, tab = _separar(pg['visuais'])
    pos = _filtros_no_canto(seg, 1888, 22, 62, 900)
    y = 112
    faixa = None
    if kpi:
        pos += _em_linha(kpi[:6], 156, y + 14, 1716, 132, 32)
        faixa = (140, y, 1748, 160)
        y += 160 + 28
    g, y2 = _grade(graf, 140, y, 1748, 2, 340, 28)
    pos += g
    y = y2 if graf else y
    for t in tab:
        pos.append((t, {'x': 140, 'y': y, 'w': 1748, 'h': 400}))
        y += 400 + 28
    h = max(H, int(y + 4))
    f = Fundo(W, h, c['pagina'])
    f.ret(0, 0, 104, h, '#1F2A37' if not c['escuro'] else '#0A0E16')
    f.ret(28, 24, 48, 48, c['acento'], 10)
    _cabecalho(f, pg, 140, 62, c, 32, 90)
    if faixa:
        f.ret(*faixa, c['painel'], 14, c['borda'])
        cards = [p for v, p in pos if v['tipo'] in KPI]
        for p in cards[1:]:
            f.ret(p['x'] - 17, faixa[1] + 24, 1.5, faixa[3] - 48, c['borda'])
    _paineis(f, [(v, p) for v, p in pos if v['tipo'] not in KPI], c)
    nav = []
    for k, (alvo, p) in enumerate(_visiveis(paginas)):
        cy = 150 + k * 80
        ativo = p['grupo'] == _ativa(paginas, i)
        f.circ(52, cy, 24, c['acento'] if ativo else '#33415C')
        f.txt(52, cy + 7, k + 1, 20, '#FFFFFF', 700, 'middle')
        nav.append({'x': 24, 'y': cy - 28, 'w': 56, 'h': 56, 'alvo': alvo, 'rotulo': p['nome']})
    return {'w': W, 'h': h, 'posicoes': pos, 'fundo': f.svg(), 'nav': nav if len(nav) > 1 else []}


def _clicaveis(m, paginas, i, c):
    pg = paginas[i]
    seg, kpi, graf, tab = _separar(pg['visuais'])
    pos = _filtros_no_canto(seg, 1888, 22, 60, 900)
    cards = [v for v in kpi if v['tipo'] == 'cartao']
    outros_kpi = [v for v in kpi if v['tipo'] != 'cartao']
    pos += _em_linha(cards[:6], 270, 140, 1618, 136) if cards else []
    principal, tabela = (graf[:1], tab[:1])
    detalhe = graf[1:] + tab[1:] + outros_kpi + cards[6:]
    larg = 1090 if detalhe else 1618
    y = 300
    if principal:
        pos.append((principal[0], {'x': 270, 'y': y, 'w': larg, 'h': 360}))
        y += 376
    if tabela:
        pos.append((tabela[0], {'x': 270, 'y': y, 'w': larg, 'h': 372}))
        y += 388
    if detalhe:
        hd = max(240, (748 - GAP * (len(detalhe) - 1)) / len(detalhe))
        pos += _em_coluna(detalhe, 1376, 300, 512, hd * len(detalhe) + GAP * (len(detalhe) - 1))
        y = max(y, 300 + hd * len(detalhe) + GAP * len(detalhe))
    h = max(H, int(y + 16))
    f = Fundo(W, h, c['pagina'])
    _cabecalho(f, {'nome': paginas[i]['nome'].split(' · ')[0], 'descricao': pg['descricao']}, 32, 64, c, 32, 80)
    nav = []
    grupos = [(alvo, p) for alvo, p in _visiveis(paginas)]
    for k, (alvo, p) in enumerate(grupos):
        yy = 140 + k * 60
        ativo = p['grupo'] == _ativa(paginas, i)
        f.ret(24, yy, 224, 50, c['acento'] if ativo else c['painel'], 10, None if ativo else c['borda'])
        f.txt(44, yy + 32, p['nome'], 18, '#FFFFFF' if ativo else c['texto'], 600 if ativo else 400)
        nav.append({'x': 24, 'y': yy, 'w': 224, 'h': 50, 'alvo': alvo, 'rotulo': p['nome']})
    if len(nav) < 2:
        nav = []
    # os cartões são os botões: cada um leva à variação da página com aquele KPI
    variacoes = [k for k, p in enumerate(paginas) if p['grupo'] == pg['grupo']]
    ids_cards = {id(v) for v in cards[:6]}
    for k, (v, p) in enumerate([(v, p) for v, p in pos if id(v) in ids_cards]):
        ativo = k == (pg['kpi_ativo'] or 0)
        f.ret(p['x'] - 6, p['y'] - 6, p['w'] + 12, p['h'] + 12, c['painel'], 14, c['acento'] if ativo else c['borda'])
        if ativo:
            f.ret(p['x'] - 6, p['y'] + p['h'] + 1, p['w'] + 12, 5, c['acento'], 2)
        if k < len(variacoes) and not ativo:
            nav.append({'x': p['x'], 'y': p['y'], 'w': p['w'], 'h': p['h'], 'alvo': variacoes[k],
                        'rotulo': f'Ver {v["valores"][0]["nome"]}'})
    _paineis(f, [(v, p) for v, p in pos if id(v) not in ids_cards], c)
    return {'w': W, 'h': h, 'posicoes': pos, 'fundo': f.svg(), 'nav': nav}


def _historia(m, paginas, i, c):
    pg = paginas[i]
    seg = []
    vistos = set()
    for v in pg['visuais']:
        if v['tipo'] in SEG and (v['categoria']['tabela'], v['categoria']['nome']) not in vistos:
            vistos.add((v['categoria']['tabela'], v['categoria']['nome']))
            seg.append(v)
    pos = _filtros_no_canto(seg[:4], 1850, 40, 60, 900)
    y = 170
    blocos = []
    for n, sec in enumerate(pg['secoes'], 1):
        _, kpi, graf, tab = _separar(sec['visuais'])
        blocos.append((n, sec, y))
        y += 110
        if kpi:
            pos += _em_linha(kpi[:6], 70, y, 1780, 150)
            y += 182
        corpo = graf + tab
        k = 0
        while k < len(corpo):
            par = corpo[k:k + 2]
            if len(par) == 2:
                pos += _em_linha(par, 70, y, 1780, 440, 40)
            else:
                pos.append((par[0], {'x': 70, 'y': y, 'w': 1780, 'h': 440}))
            y += 440 + 40
            k += 2
        y += 20
    conclusao = y
    y += 190
    h = max(H, int(y))
    f = Fundo(W, h, c['pagina'])
    f.txt(70, 84, m['projeto'], 46, c['texto'], 700)
    if m.get('publico'):
        f.txt(70, 122, m['publico'], 18, c['mudo'])
    for n, sec, ys in blocos:
        f.ret(70, ys, 1780, 84, c['painel'], 12, c['borda'])
        f.circ(116, ys + 42, 24, c['acento'])
        f.txt(116, ys + 50, n, 22, c['pagina'], 800, 'middle')
        f.txt(160, ys + 40, sec['nome'], 28, c['texto'], 700)
        if sec.get('descricao'):
            f.txt(160, ys + 68, _quebra(sec['descricao'], 120)[0], 16, c['mudo'])
    _paineis(f, pos, c)
    f.ret(70, conclusao, 1780, 160, c['painel'], 14, c['borda'])
    f.ret(70, conclusao, 8, 160, c['acento'], 4)
    f.txt(104, conclusao + 48, 'Para decidir', 22, c['acento'], 700)
    for k, linha in enumerate(_quebra(m.get('descricao') or '', 130)[:3]):
        f.txt(104, conclusao + 86 + k * 26, linha, 19, c['texto'])
    return {'w': W, 'h': h, 'posicoes': pos, 'fundo': f.svg(), 'nav': []}


# ----------------------------------------------------------------- os cinco tirados das outras páginas
def _nav_lista(f, paginas, i, c, x, y, w, h=46, gap=8, claro=False):
    """Lista vertical das páginas (a ativa preenchida com a cor de destaque)."""
    nav = []
    for k, (alvo, p) in enumerate(_visiveis(paginas)):
        yy = y + k * (h + gap)
        ativo = p['grupo'] == _ativa(paginas, i)
        if ativo:                                    # sobre o painel de destaque, a ativa fica branca
            f.ret(x, yy, w, h, '#FFFFFF' if claro else c['acento'], 10)
        elif claro:
            f.ret(x, yy, w, h, '#FFFFFF', 10, None, 0.12)
        cor_txt = (c['acento'] if claro else '#FFFFFF') if ativo else ('#FFFFFF' if claro else c['texto'])
        f.txt(x + 16, yy + h / 2 + 6, p['nome'], 17, cor_txt, 600 if ativo else 400)
        nav.append({'x': x, 'y': yy, 'w': w, 'h': h, 'alvo': alvo, 'rotulo': p['nome']})
    return nav if len(nav) > 1 else []


def _nav_abas_topo(f, paginas, i, c, x, y, w=240, h=40):
    nav = []
    for k, (alvo, p) in enumerate(_visiveis(paginas)):
        xx = x + k * (w + 8)
        ativo = p['grupo'] == _ativa(paginas, i)
        f.ret(xx, y, w, h, c['acento'] if ativo else c['painel'], 20, None if ativo else c['borda'])
        f.txt(xx + w / 2, y + h / 2 + 6, p['nome'], 16, '#FFFFFF' if ativo else c['texto'], 600 if ativo else 400, 'middle')
        nav.append({'x': xx, 'y': y, 'w': w, 'h': h, 'alvo': alvo, 'rotulo': p['nome']})
    return nav if len(nav) > 1 else []


def _executivo(m, paginas, i, c):
    pg = paginas[i]
    seg, kpi, graf, tab = _separar(pg['visuais'])
    pos = _filtros_no_canto(seg, 1880, 30, 62, 820)
    y = 130
    if kpi:
        pos += _em_linha(kpi[:5], 40, y, 1840, 220, 24)
        y += 220 + 30
        if kpi[5:]:
            pos += _em_linha(kpi[5:], 40, y, 1840, 160, 24)
            y += 190
    heroi = next((v for v in graf if v['tipo'] in ('linha', 'area', 'colunas')), graf[0] if graf else None)
    resto = [v for v in graf if v is not heroi] + tab
    if heroi:
        hh = max(380, (H - 40 - y) if not resto else 420)
        pos.append((heroi, {'x': 40, 'y': y, 'w': 1840, 'h': hh}))
        y += hh + 30
    g, y2 = _grade(resto, 40, y, 1840, 2, 380, 30)
    pos += g
    h = max(H, int((y2 if resto else y) + 10))
    f = Fundo(W, h, c['pagina'])
    f.ret(40, 44, 8, 52, c['acento'], 4)
    _cabecalho(f, pg, 64, 76, c, 34, 80)
    _paineis(f, pos, c)
    nav = []
    abas = _visiveis(paginas)
    if len(abas) > 1 and not seg:                      # sem filtros, as abas ocupam o canto do cabeçalho
        nav = _nav_abas_topo(f, paginas, i, c, 1880 - len(abas) * 228, 40, 220, 40)
    elif len(abas) > 1:                                # com filtros, um ponto por página logo abaixo deles
        for k, (alvo, p) in enumerate(abas):
                cx = 1880 - (len(abas) - k) * 26
                ativo = p['grupo'] == _ativa(paginas, i)
                f.circ(cx, 110, 8, c['acento'] if ativo else c['borda'])
                nav.append({'x': cx - 12, 'y': 98, 'w': 24, 'h': 24, 'alvo': alvo, 'rotulo': p['nome']})
    return {'w': W, 'h': h, 'posicoes': pos, 'fundo': f.svg(), 'nav': nav}


def _mapa_central(m, paginas, i, c):
    pg = paginas[i]
    seg, kpi, graf, tab = _separar(pg['visuais'])
    pos = _filtros_no_canto(seg, 1888, 28, 56, 700)
    heroi = next((v for v in graf if v['tipo'] == 'mapa'), graf[0] if graf else None)
    laterais = [v for v in graf if v is not heroi][:3]
    ids = {id(v) for v in laterais}
    resto = [v for v in graf if v is not heroi and id(v) not in ids] + tab
    topo, alto = 120, 600
    if kpi:
        pos += _em_coluna(kpi[:4], 32, topo, 300, alto)
    x0 = 352 if kpi else 32
    x1 = 1568 if laterais else 1888
    if heroi:
        pos.append((heroi, {'x': x0, 'y': topo, 'w': x1 - x0, 'h': alto}))
    if laterais:
        pos += _em_coluna(laterais, 1588, topo, 300, alto)
    y = topo + alto + 24
    if resto:
        por = 4 if len(resto) >= 4 else len(resto)
        g, y = _grade(resto, 32, y, 1856, por, 300, 24)
        pos += g
    h = max(H, int(y + 8))
    f = Fundo(W, h, c['pagina'])
    f.txt(W / 2, 66, pg['nome'], 34, c['texto'], 700, 'middle')
    if pg['descricao']:
        f.txt(W / 2, 98, _quebra(pg['descricao'], 110)[0], 17, c['mudo'], 400, 'middle')
    _paineis(f, pos, c)
    nav = []
    for k, (alvo, p) in enumerate(_visiveis(paginas)):
        x = 32 + k * 210
        ativo = p['grupo'] == _ativa(paginas, i)
        f.txt(x, 62, p['nome'], 16, c['acento'] if ativo else c['mudo'], 700 if ativo else 400)
        if ativo:
            f.ret(x, 72, 60, 4, c['acento'], 2)
        nav.append({'x': x - 6, 'y': 36, 'w': 200, 'h': 44, 'alvo': alvo, 'rotulo': p['nome']})
    return {'w': W, 'h': h, 'posicoes': pos, 'fundo': f.svg(), 'nav': nav if len(nav) > 1 else []}


def _causa_raiz(m, paginas, i, c):
    pg = paginas[i]
    seg, kpi, graf, tab = _separar(pg['visuais'])
    pos = _em_coluna(seg, 24, 190, 252, len(seg) * 84 - GAP) if seg else []
    x0, larg = 330, 1558
    y = 32
    if kpi:
        pos += _em_linha(kpi[:5], x0, y, larg, 170, 20)
        y += 170 + 24
        if kpi[5:]:
            pos += _em_linha(kpi[5:], x0, y, larg, 140, 20)
            y += 164
    heroi = next((v for v in graf if v['tipo'] == 'decomposicao'), graf[0] if graf else None)
    resto = [v for v in graf if v is not heroi] + tab
    if heroi:
        pos.append((heroi, {'x': x0, 'y': y, 'w': larg, 'h': 480}))
        y += 480 + 24
    g, y2 = _grade(resto, x0, y, larg, 2, 360, 24)
    pos += g
    h = max(H, int((y2 if resto else y) + 8))
    f = Fundo(W, h, c['pagina'])
    f.ret(0, 0, 300, h, c['painel'], 0, c['borda'])
    f.txt(24, 64, pg['nome'], 26, c['texto'], 700)
    for k, linha in enumerate(_quebra(pg['descricao'], 30)[:3]):
        f.txt(24, 94 + k * 21, linha, 15, c['mudo'])
    if seg:
        f.txt(24, 176, 'Filtros', 14, c['mudo'], 700)
    _paineis(f, pos, c)
    vis = _visiveis(paginas)
    nav = _nav_lista(f, paginas, i, c, 16, h - 40 - len(vis) * 54, 268) if len(vis) > 1 else []
    return {'w': W, 'h': h, 'posicoes': pos, 'fundo': f.svg(), 'nav': nav}


def _tabela_lateral(m, paginas, i, c):
    pg = paginas[i]
    seg, kpi, graf, tab = _separar(pg['visuais'])
    pos = _filtros_no_canto(seg, 1880, 30, 60, 820)
    y = 118
    faixa = None
    if kpi:
        pos += _em_linha(kpi[:6], 56, y + 12, 1808, 126, 32)
        faixa = (40, y, 1840, 150)
        y += 150 + 28
    if tab and graf:
        linhas = (len(graf) + 1) // 2
        hg = max(300, (H - 40 - y - 24 * (linhas - 1)) / linhas)
        g, fim1 = _grade(graf, 40, y, 900, 2 if len(graf) > 1 else 1, hg, 24)
        hT = max(360, (H - 40 - y - 24 * (len(tab) - 1)) / len(tab))
        t = _em_coluna(tab, 964, y, 916, hT * len(tab) + 24 * (len(tab) - 1), 24)
        pos += g + t
        fim = max(fim1, y + hT * len(tab) + 24 * len(tab))
    else:
        g, fim = _grade(graf + tab, 40, y, 1840, 2, 400, 24)
        pos += g
    h = max(H, int(fim + 16))
    f = Fundo(W, h, c['pagina'])
    _cabecalho(f, pg, 40, 66, c, 32, 90)
    if faixa:
        f.ret(*faixa, c['painel'], 14, c['borda'])
        cards = [p for v, p in pos if v['tipo'] in KPI]
        for p in cards[1:]:
            f.ret(p['x'] - 17, faixa[1] + 22, 1.5, faixa[3] - 44, c['borda'])
    _paineis(f, [(v, p) for v, p in pos if v['tipo'] not in KPI], c)
    nav = []
    vis = _visiveis(paginas)
    if len(vis) > 1:
        for k, (alvo, p) in enumerate(vis):
            x = 900 + k * 200 - len(vis) * 100
            ativo = p['grupo'] == _ativa(paginas, i)
            f.txt(x + 90, 64, p['nome'], 16, c['acento'] if ativo else c['mudo'], 700 if ativo else 400, 'middle')
            if ativo:
                f.ret(x + 60, 74, 60, 4, c['acento'], 2)
            nav.append({'x': x, 'y': 38, 'w': 180, 'h': 44, 'alvo': alvo, 'rotulo': p['nome']})
    return {'w': W, 'h': h, 'posicoes': pos, 'fundo': f.svg(), 'nav': nav}


def _equipes(m, paginas, i, c):
    pg = paginas[i]
    seg, kpi, graf, tab = _separar(pg['visuais'])
    pos = []
    lx, lw = 48, 372
    y = 180
    if kpi:                                          # um por linha: valor em reais precisa da largura toda
        for v in kpi[:5]:
            pos.append((v, {'x': lx, 'y': y, 'w': lw, 'h': 112}))
            y += 126
    if seg:
        pos += _em_coluna(seg, lx, y + 8, lw, len(seg) * 76 - GAP)
        y += len(seg) * 76 + 8
    heroi = next((v for v in graf if v['tipo'] == 'dispersao'), None)
    mini = [v for v in graf if v is not heroi][:3] if heroi else graf[:3]
    if not heroi and graf[3:]:
        heroi = graf[3]
    ids = {id(v) for v in mini}
    resto = [v for v in graf if v is not heroi and id(v) not in ids] + tab
    x0, larg = 468, 1428
    yr = 24
    if mini:
        pos += _em_linha(mini, x0, yr, larg, 260, 20)
        yr += 280
    if heroi:
        pos.append((heroi, {'x': x0, 'y': yr, 'w': larg, 'h': 500}))
        yr += 520
    g, y2 = _grade(resto, x0, yr, larg, 2, 360, 20)
    pos += g
    h = max(H, int(max(y + 200, (y2 if resto else yr)) + 8))
    f = Fundo(W, h, c['pagina'])
    f.ret(24, 24, 420, h - 48, c['acento'], 18)
    f.txt(lx, 84, pg['nome'], 30, '#FFFFFF', 700)
    for k, linha in enumerate(_quebra(pg['descricao'], 34)[:2]):
        f.txt(lx, 116 + k * 22, linha, 16, '#FFFFFF')
    for v, p in pos:
        if v['tipo'] in KPI + SEG and p['x'] < 450:
            if v['tipo'] in KPI:
                f.ret(p['x'] - 4, p['y'] - 4, p['w'] + 8, p['h'] + 8, '#FFFFFF', 12)
    _paineis(f, [(v, p) for v, p in pos if p['x'] > 450], c)
    vis = _visiveis(paginas)
    nav = _nav_lista(f, paginas, i, c, 40, h - 64 - len(vis) * 54, 388, claro=True) if len(vis) > 1 else []
    return {'w': W, 'h': h, 'posicoes': pos, 'fundo': f.svg(), 'nav': nav}
