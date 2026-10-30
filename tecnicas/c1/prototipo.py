"""
Esculpir: o protótipo navegável do painel, num único .html sem dependência
externa (abre offline, em qualquer navegador, e pode ser enviado por e-mail
para validação).

Os números são FICTÍCIOS, determinísticos e coerentes entre si (ver
simulacao.py): o protótipo valida layout, indicadores e navegação, nunca
valor. Nenhuma linha do banco é lida — regra "só estrutura, nunca dados" do
Deidara.
"""

import html
import json
import math

from kibaku_nendo.especificacao import COR_BOA, COR_RUIM, medida
from tecnicas.arte.modelos import montar, paginas_do_relatorio
from tecnicas.bunshin.simulacao import Simulador, categorias
from kibaku_nendo.util import numero_br


def formatar(v, formato, compacto=False):
    if v is None:                                    # medida que fica em branco nesta linha (ex.: fora dos melhores/piores)
        return ''
    if formato == 'percentual':
        return numero_br(v * 100, 1) + '%'
    pref = 'R$ ' if formato == 'moeda' else ''
    if compacto and abs(v) >= 1e4:
        for lim, suf in ((1e9, ' bi'), (1e6, ' mi'), (1e3, ' mil')):
            if abs(v) >= lim:
                return pref + numero_br(v / lim, 1) + suf
    casas = 0 if formato == 'inteiro' else 2
    return pref + numero_br(v, casas)


# ------------------------------------------------------------------- visuais
def _e(s):
    return html.escape(str(s), quote=True)


def _titulo(v, w):
    return f'<text x="12" y="22" class="t">{_e(_corta(v["titulo"], int(w / 7.5)))}</text>'


def _curto(r, n):
    """Rótulo de mês que não cabe ("jan/2025"): fica só o mês, sem reticências no meio da palavra."""
    r = str(r)
    return r.split('/')[0] if len(r) > n and '/' in r else r


def _corta(s, n):
    s = str(s)
    return s if len(s) <= n else s[:max(1, n - 1)] + '…'


def svg_visual(sim, v, pos, cores):
    w, h = pos['w'], pos['h']
    corpo = {'cartao': _cartao, 'medidor': _medidor, 'segmentador': _segmentador, 'tabela': _tabela,
             'matriz': _matriz, 'rosca': _rosca, 'linha': _linha, 'barras': _barras, 'colunas': _colunas,
             'botoes': _botoes, 'cartoes': _cartoes, 'decomposicao': _decomposicao, 'dispersao': _dispersao,
             'area': _area, 'mapa': _mapa, 'abas': _abas, 'alternar': _alternar, 'skyline': _skyline,
             'setas': _setas, 'imagem': _imagem, 'aviso': _aviso, 'html': _html, 'vegalite': _vegalite}[v['tipo']]
    return (f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{_e(v["titulo"])}">'
            f'{corpo(sim, v, w, h, cores)}</svg>')


def _cor_status(sim, nome, filtros=()):
    st = sim.status(nome, filtros)
    return '' if st is None else f' style="fill:{COR_BOA if st else COR_RUIM}"'


def _simbolo(sim, nome, filtros=()):
    st = sim.status(nome, filtros)
    return '' if st is None else (' ✓' if st else ' ✗')


def titulo_do_cartao(m, v, sim=None):
    """O mesmo texto vai para o título do cartão no Power BI (meta numérica: fixo; meta medida: o valor dela)."""
    if not v.get('meta'):
        return None
    md = medida(m, v['meta']['nome'])
    if md and md['tipo'] == 'meta':
        return f'Meta: {formatar(float(md["dax"]), md["formato"], True)}'
    if md and sim is not None:
        return f'Meta: {formatar(sim.valor(md["nome"]), md["formato"], True)}'
    return f'Meta: {v["meta"]["nome"]}'


def _cartao(sim, v, w, h, cores):
    md = v['valores'][0]
    mdl = medida(sim.m, md['nome'])
    if mdl and mdl['tipo'] == 'lista_top':          # texto: um item por linha, como a medida concatena
        base = medida(sim.m, mdl['ranking']['base'])
        itens = sim.lista(mdl)
        out = [f'<text x="12" y="20" class="sub">{_e(_corta(v["titulo"], int(w / 6.5)))}</text>']
        passo = max(16, min(26, (h - 34) / max(1, len(itens))))
        for i, (r, val) in enumerate(itens):
            y = 30 + passo * (i + 0.75)
            out.append(f'<text x="12" y="{y:.0f}" class="cel" style="font-weight:600">{i + 1}. {_e(_corta(r, int((w - 110) / 7)))}</text>'
                       f'<text x="{w - 12}" y="{y:.0f}" class="cel" text-anchor="end">{_e(formatar(val, base["formato"], True))}</text>')
        return ''.join(out)
    val = sim.valor(md['nome'])
    meta = titulo_do_cartao(sim.m, v, sim)
    topo = f'<text x="12" y="20" class="sub">{_e(meta)}</text>' if meta else ''
    st = sim.status(md['nome'])
    selo = '' if st is None or w < 300 else (f'<text x="{w - 36}" y="20" class="sub" text-anchor="end"{_cor_status(sim, md["nome"])}>'
                                             f'{"✓ na meta" if st else "✗ fora da meta"}</text>')   # estreito: a cor já diz
    txt = formatar(val, md['formato'], True)
    tam = max(16, min(54, (h - 44) * 0.62, (w - 24) / (0.58 * max(1, len(txt)))))  # cabe na altura e na largura
    cor = _cor_status(sim, md['nome'])
    estilo = f' style="font-size:{tam:.0f}px;{cor[8:-1]}"' if cor else f' style="font-size:{tam:.0f}px"'
    return (topo + selo + f'<text x="{w / 2}" y="{h / 2 + tam * 0.3:.0f}" class="kpi" text-anchor="middle"{estilo}>'
            f'{_e(formatar(val, md["formato"], True))}</text>'
            f'<text x="{w / 2}" y="{h / 2 + tam * 0.3 + 22:.0f}" class="sub" text-anchor="middle">{_e(_corta(v["titulo"], int(w / 6.5)))}</text>')


def _medidor(sim, v, w, h, cores):
    md = medida(sim.m, v['valores'][0]['nome'])
    val = sim.valor(md['nome'])
    if v['meta']:
        meta = sim.valor(v['meta']['nome'])
    elif isinstance(md.get('meta'), (int, float)):
        meta = md['meta']
    else:
        meta = val * 1.25
    frac = max(0.0, min(1.0, val / (meta * 1.4 or 1)))
    cx, cy, r = w / 2, h - 22, max(10, min(w / 2 - 20, h - 50))
    ang = math.pi * (1 - frac)
    x, y = cx + r * math.cos(ang), cy - r * math.sin(ang)
    am = math.pi * (1 - 1 / 1.4)
    return (_titulo(v, w) +
            f'<path d="M{cx - r},{cy} A{r},{r} 0 0 1 {cx + r},{cy}" class="trilho" stroke-width="16"/>'
            f'<path d="M{cx - r},{cy} A{r},{r} 0 0 1 {x:.1f},{y:.1f}" fill="none" stroke="{cores[0]}" stroke-width="16"/>'
            f'<line x1="{cx + (r - 12) * math.cos(am):.1f}" y1="{cy - (r - 12) * math.sin(am):.1f}" '
            f'x2="{cx + (r + 12) * math.cos(am):.1f}" y2="{cy - (r + 12) * math.sin(am):.1f}" stroke="#252423" stroke-width="2"/>'
            f'<text x="{cx}" y="{cy - 6}" class="kpi2" text-anchor="middle">{_e(formatar(val, md["formato"], True))}</text>'
            f'<text x="{cx}" y="{cy + 14}" class="sub" text-anchor="middle">meta {_e(formatar(meta, md["formato"], True))}</text>')


def _pilula(sim, md, filtros, x, y, w):
    st = sim.status(md['svg']['base'], filtros)
    if st is None:
        return ''
    texto = 'Na meta' if st else 'Fora da meta'
    lw = len(texto) * 7 + 20
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{lw}" height="16" rx="8" fill="{"#DFF6DD" if st else "#FDE7E9"}"/>'
            f'<text x="{x + lw / 2:.1f}" y="{y + 12:.1f}" text-anchor="middle" class="sub" '
            f'style="fill:{"#107C10" if st else "#A4262C"};font-weight:600">{texto}</text>')


def _seta(sim, md, filtros, x, y, w):
    cfg = md['svg']
    _, vals = sim.classificacao({**cfg}, filtros)
    rotulos = [r for r, _ in vals] or [None]
    filtro_linha = [(c, r) for c, r in filtros if (c['tabela'], c['nome']) == (cfg['tabela'], cfg['coluna'])]
    outros = [(c, r) for c, r in filtros if (c, r) not in filtro_linha]
    col = filtro_linha[0][0] if filtro_linha else None
    mx = max([max(sim.valor(cfg['base'], outros + [(col, r)]), sim.valor(cfg['comparar'], outros + [(col, r)]))
              for r in rotulos if col] + [1e-9]) * 1.1
    atual, antes = sim.valor(cfg['base'], filtros), sim.valor(cfg['comparar'], filtros)
    x1, x2 = x + w * antes / mx, x + w * atual / mx
    melhor = atual >= antes if md['polaridade'] == 'maior_melhor' else atual <= antes
    cor = '#107C10' if melhor else '#D13438'
    p = -4 if x2 >= x1 else 4
    return (f'<line x1="{x:.1f}" x2="{x + w:.1f}" y1="{y + 8:.1f}" y2="{y + 8:.1f}" stroke="#EDEBE9" stroke-width="2"/>'
            f'<circle cx="{x1:.1f}" cy="{y + 8:.1f}" r="3" fill="#A19F9D"/>'
            f'<line x1="{x1:.1f}" x2="{x2:.1f}" y1="{y + 8:.1f}" y2="{y + 8:.1f}" stroke="{cor}" stroke-width="3"/>'
            f'<path d="M{x2 + p:.1f} {y + 3:.1f} L{x2:.1f} {y + 8:.1f} L{x2 + p:.1f} {y + 13:.1f}" fill="none" stroke="{cor}" stroke-width="3"/>')


def _selo(sim, md, filtros, x, y, w):
    cfg = {**md['svg']}
    rotulo, vals = sim.classificacao(cfg, filtros)
    nomes = [r for r, _ in vals]
    if rotulo not in nomes:
        return ''
    pos = nomes.index(rotulo) + 1
    cor = sim.m['tema']['cores'][0] if pos <= 3 else '#A19F9D'
    return (f'<circle cx="{x + 9:.1f}" cy="{y + 8:.1f}" r="9" fill="{cor}"/>'
            f'<text x="{x + 9:.1f}" y="{y + 12:.1f}" text-anchor="middle" class="sub" style="fill:#FFFFFF;font-weight:700">{pos}</text>')


def _linha_e_resto(cfg, filtros):
    linha = [(c, r) for c, r in filtros if (c['tabela'], c['nome']) == (cfg['tabela'], cfg['coluna'])]
    return (linha[0][0] if linha else None), [(c, r) for c, r in filtros if (c, r) not in linha]


def _variacao(sim, md, filtros, x, y, w):
    """Desvio contra a comparação, a partir do centro (IBCS): verde melhor, vermelho pior."""
    cfg = md['svg']
    col, outros = _linha_e_resto(cfg, filtros)
    if not col:
        return ''
    desvio = lambda f: sim.valor(cfg['base'], f) - sim.valor(cfg['comparar'], f)
    mx = max([abs(desvio(outros + [(col, r)])) for r in categorias(sim.m, col)] + [1e-9]) * 1.1
    d = desvio(filtros)
    bw = abs(d) / mx * w / 2
    melhor = d >= 0 if md['polaridade'] == 'maior_melhor' else d <= 0
    meio = x + w / 2
    return (f'<rect x="{meio if d >= 0 else meio - bw:.1f}" y="{y + 1:.1f}" width="{bw:.1f}" height="14" '
            f'fill="{"#107C10" if melhor else "#D13438"}"/>'
            f'<line x1="{meio:.1f}" x2="{meio:.1f}" y1="{y - 3:.1f}" y2="{y + 19:.1f}" stroke="#252423" stroke-width="1.5"/>')


def _radar(sim, md, filtros, x, y, w, h):
    """Um polígono por linha: cada eixo é uma medida, dividida pelo maior valor dela entre as linhas."""
    cfg = md['svg']
    col, outros = _linha_e_resto(cfg, filtros)
    if not col:
        return ''
    eixos = cfg['medidas']
    lado = min(w, h)
    cx, cy, raio = x + lado / 2, y + lado / 2, lado / 2 - 4
    ang = [-math.pi / 2 + 2 * math.pi * k / len(eixos) for k in range(len(eixos))]
    pts = []
    for e, a in zip(eixos, ang):
        mx = max([sim.valor(e, outros + [(col, r)]) for r in categorias(sim.m, col)] + [1e-9])
        f = max(0, min(1, sim.valor(e, filtros) / mx))
        pts.append(f'{cx + raio * f * math.cos(a):.1f},{cy + raio * f * math.sin(a):.1f}')
    grade = ' '.join(f'{cx + raio * math.cos(a):.1f},{cy + raio * math.sin(a):.1f}' for a in ang)
    meio = ' '.join(f'{cx + raio / 2 * math.cos(a):.1f},{cy + raio / 2 * math.sin(a):.1f}' for a in ang)
    cor = sim.m['tema']['cores'][0]
    return (f'<polygon points="{grade}" fill="none" stroke="#D0D5DD"/><polygon points="{meio}" fill="none" stroke="#E4E7EC"/>'
            + ''.join(f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{cx + raio * math.cos(a):.1f}" y2="{cy + raio * math.sin(a):.1f}" '
                      'stroke="#E4E7EC"/>' for a in ang)
            + f'<polygon points="{" ".join(pts)}" fill="{cor}" fill-opacity=".35" stroke="{cor}" stroke-width="2"/>')


def _barra_meta(sim, escala, filtros, x, y, w):
    """A mesma barra que a medida SVG desenha no Power BI: trilho, valor (verde/vermelho) e meta tracejada."""
    w = max(20, w)
    if not escala:                                   # SVG em DAX livre: o desenho é do analista
        return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="14" rx="3" class="caixa"/>'
                f'<text x="{x + w / 2:.1f}" y="{y + 11:.1f}" class="sub" text-anchor="middle">{"SVG · só no Power BI" if w >= 110 else "SVG"}</text>')
    md, maximo = escala
    v, meta = sim.valor(md['svg']['base'], filtros), sim.valor(md['svg']['meta'], filtros)
    bw = max(0, v / maximo * w) if maximo else 0
    mx = max(0, meta / maximo * w) if maximo else 0
    ok = v >= meta if md['polaridade'] == 'maior_melhor' else v <= meta
    cor = '#107C10' if ok else '#D13438'
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="14" rx="3" fill="#EDEBE9"/>'
            f'<rect x="{x:.1f}" y="{y + 2:.1f}" width="{bw:.1f}" height="10" rx="3" fill="{cor}"/>'
            f'<line x1="{x + mx:.1f}" x2="{x + mx:.1f}" y1="{y - 2:.1f}" y2="{y + 16:.1f}" stroke="#252423" '
            f'stroke-width="2" stroke-dasharray="3 2"/>')


def _nota_estrelas(sim, md, filtros):
    """A mesma nota de 0 a 5 que a medida svg_estrelas calcula."""
    cfg = md['svg']
    v = sim.valor(cfg['base'], filtros)
    if cfg.get('maximo'):
        return max(0, min(5, v / cfg['maximo'] * 5))
    col, outros = _linha_e_resto(cfg, filtros)
    vals = [sim.valor(cfg['base'], outros + [(col, r)]) for r in categorias(sim.m, col)] if col else [v]
    if md['polaridade'] == 'maior_melhor':
        return max(0, min(5, v / (max(vals) or 1) * 5))
    return max(0, min(5, (min(vals) / v * 5) if v else 0))


def _estrelas(sim, md, filtros, x, y, w):
    nota = _nota_estrelas(sim, md, filtros)
    out = []
    for k in range(5):
        cheia = max(0, min(1, nota - k))
        out.append(f'<text x="{x + 15 * k:.1f}" y="{y + 13:.1f}" style="font-size:15px;fill:#E1DFDD">★</text>')
        if cheia:                                    # meia estrela: a amarela cortada na largura da nota
            corte = '' if cheia >= 1 else f';clip-path:inset(0 {100 - cheia * 100:.0f}% 0 0)'
            out.append(f'<text x="{x + 15 * k:.1f}" y="{y + 13:.1f}" style="font-size:15px;fill:#F2C811{corte}">★</text>')
    return ''.join(out)


def _progresso(sim, md, filtros, x, y, w):
    cfg = md['svg']
    v, meta = sim.valor(cfg['base'], filtros), sim.valor(cfg['meta'], filtros)
    pct = v / meta if meta else 0
    ok = v >= meta if md['polaridade'] == 'maior_melhor' else v <= meta
    bw = max(0, min(1, pct)) * (w - 50)
    return (f'<text x="{x:.1f}" y="{y + 12:.1f}" class="sub" style="font-weight:700">{numero_br(pct * 100, 0)}%</text>'
            f'<rect x="{x + 44:.1f}" y="{y + 5:.1f}" width="{w - 50:.1f}" height="6" rx="3" fill="#EDEBE9"/>'
            f'<rect x="{x + 44:.1f}" y="{y + 5:.1f}" width="{bw:.1f}" height="6" rx="3" fill="{"#107C10" if ok else "#D13438"}"/>')


def _botoes(sim, v, w, h, cores):
    """Segmentador de botões: as opções lado a lado, a primeira marcada (com ícone ou imagem, se pedidos)."""
    com_imagem = bool(v.get('imagem'))
    rot = ([] if com_imagem else ['Tudo']) + categorias(sim.m, v['categoria'])[:5 if not com_imagem else 6]
    gap = 6
    bw = (w - 24 - gap * (len(rot) - 1)) / len(rot)
    bh = max(18, h - 34)
    out = [f'<text x="12" y="18" class="sub">{_e(_corta(v["titulo"], int(w / 6.5)))} · filtro ilustrativo</text>']
    for i, r in enumerate(rot):
        x = 12 + i * (bw + gap)
        ativo = i == 0
        if com_imagem:                               # o círculo com as iniciais, aceso no escolhido
            raio = max(8, min(bh / 2 - 12, bw / 2 - 6, 20))
            ini = _iniciais(r)
            out.append(f'<rect x="{x:.1f}" y="26" width="{bw:.1f}" height="{bh:.1f}" rx="8" fill="#FFFFFF" '
                       f'stroke="{cores[0] if ativo else "#E1DFDD"}"/>'
                       f'<circle cx="{x + bw / 2:.1f}" cy="{26 + raio + 4:.1f}" r="{raio:.1f}" fill="{cores[0] if ativo else "#EDEBE9"}"/>'
                       f'<text x="{x + bw / 2:.1f}" y="{26 + raio + 9:.1f}" class="cel" text-anchor="middle" '
                       f'style="fill:{"#FFFFFF" if ativo else "#605E5C"};font-weight:600">{_e(ini)}</text>'
                       + (f'<text x="{x + bw / 2:.1f}" y="{26 + bh - 6:.1f}" class="eixo" text-anchor="middle">'
                          f'{_e(_corta(r, max(3, int(bw / 6.5))))}</text>' if bh >= 2 * raio + 24 else '')
                       + f'<title>{_e(r)}</title>')
            continue
        marca = '✓ ' if v.get('icone') and ativo else ''
        out.append(f'<rect x="{x:.1f}" y="26" width="{bw:.1f}" height="{bh:.1f}" rx="8" fill="{cores[0] if ativo else "#FFFFFF"}" '
                   f'stroke="{cores[0]}"/><text x="{x + bw / 2:.1f}" y="{26 + bh / 2 + 5:.1f}" class="cel" text-anchor="middle" '
                   f'style="fill:{"#FFFFFF" if ativo else cores[0]}">{_e(marca + _corta(r, max(3, int(bw / 7.5))))}</text>')
    return ''.join(out)


def _iniciais(nome):
    partes = str(nome).split()
    return (partes[0][:1] + partes[-1][:1] if len(partes) > 1 else str(nome)[:2]).upper()


def _abas(sim, v, w, h, cores):
    """Abas de indicador: o rótulo e o valor de cada opção, a primeira escolhida com a barra de destaque."""
    alvo = medida(sim.m, v['controla'])
    rot, mds = alvo['extra']['rotulos'], alvo['extra']['medidas']
    bw = (w - 24) / len(rot)
    out = []
    for i, (r, nome) in enumerate(zip(rot, mds)):
        x = 12 + i * bw
        md = medida(sim.m, nome)
        if i == 0:
            out.append(f'<rect x="{x:.1f}" y="6" width="{bw - 4:.1f}" height="{h - 12:.1f}" fill="{cores[0]}" fill-opacity=".1"/>'
                       f'<rect x="{x:.1f}" y="6" width="{bw - 4:.1f}" height="5" fill="{cores[0]}"/>')
        out.append(f'<text x="{x + 12:.1f}" y="{min(34, h / 2):.1f}" class="sub">{_e(_corta(r, int(bw / 7)))}</text>'
                   f'<text x="{x + 12:.1f}" y="{min(h - 14, h / 2 + 22):.1f}" class="kpi2">{_e(formatar(sim.valor(nome), md["formato"], True))}</text>')
    return ''.join(out)


def _alternar(sim, v, w, h, cores):
    """A chave liga/desliga (desenhada desligada) com o rótulo."""
    y = max(4, h / 2 - 14)
    return (f'<rect x="12" y="{y:.1f}" width="52" height="28" rx="14" fill="#C8C6C4"/>'
            f'<circle cx="26" cy="{y + 14:.1f}" r="10" fill="#FFFFFF"/>'
            f'<text x="74" y="{y + 19:.1f}" class="cel">{_e(_corta(v["titulo"] or "", int((w - 80) / 7)))}</text>')


def _skyline(sim, v, w, h, cores):
    """Colunas empilhadas com um respiro branco entre os blocos."""
    rot = categorias(sim.m, v['categoria'])
    leg = categorias(sim.m, v['legenda'])[:6]
    md = v['valores'][0]
    vals = [[sim.valor(md['nome'], [(v['categoria'], r), (v['legenda'], l)]) for l in leg] for r in rot]
    mx = max([sum(x) for x in vals] + [1e-9]) * 1.08
    top, base = 52, h - 30
    gw = (w - 24) / len(rot)
    out = [_titulo(v, w), _legenda([(l, [0], None) for l in leg], cores, w, 42)]
    for i, r in enumerate(rot):
        y = base
        for k, val in enumerate(vals[i]):
            bh = (base - top) * val / mx
            out.append(f'<rect x="{12 + i * gw + 1:.1f}" y="{y - bh:.1f}" width="{gw - 2:.1f}" height="{max(0, bh - 2):.1f}" '
                       f'fill="{cores[k % len(cores)]}"/>')
            y -= bh
        if len(rot) <= 14 or i % 2 == 0:
            out.append(f'<text x="{12 + i * gw + gw / 2:.1f}" y="{base + 16}" class="eixo" text-anchor="middle">'
                       f'{_e(_corta(r, max(3, int(gw / 6))))}</text>')
    return ''.join(out)


def _setas(sim, v, w, h, cores):
    """Do valor anterior (ponto cinza) ao atual (ponto colorido), por categoria, com a variação ao lado."""
    rot = categorias(sim.m, v['categoria'])
    ant, atual = v['valores']
    pares = [(r, sim.valor(ant['nome'], [(v['categoria'], r)]), sim.valor(atual['nome'], [(v['categoria'], r)])) for r in rot]
    pares.sort(key=lambda x: -x[2])
    mx = max([max(a, b) for _, a, b in pares] + [1e-9]) * 1.1
    top, esq = 40, min(150, w * 0.3)
    gh = (h - top - 10) / max(1, len(pares))
    largura = w - esq - 70
    out = [_titulo(v, w)]
    for i, (r, a, b) in enumerate(pares):
        y = top + i * gh + gh / 2
        xa, xb = esq + largura * a / mx, esq + largura * b / mx
        var = (b - a) / a if a else 0
        out.append(f'<text x="{esq - 8}" y="{y + 4:.1f}" class="eixo" text-anchor="end">{_e(_corta(r, int(esq / 6.5)))}</text>'
                   f'<line x1="{xa:.1f}" x2="{xb:.1f}" y1="{y:.1f}" y2="{y:.1f}" stroke="{cores[0]}" stroke-width="3"/>'
                   f'<circle cx="{xa:.1f}" cy="{y:.1f}" r="5" fill="#A19F9D"/><circle cx="{xb:.1f}" cy="{y:.1f}" r="5" fill="{cores[0]}"/>'
                   f'<text x="{max(xa, xb) + 10:.1f}" y="{y + 4:.1f}" class="eixo">{"+" if var >= 0 else ""}{numero_br(var * 100, 1)}%</text>')
    return ''.join(out)


def _imagem(sim, v, w, h, cores):
    """Medida SVG no cartão inteiro: a dispersão com os pontos (iniciais) ou o radar."""
    md = medida(sim.m, v['valores'][0]['nome'])
    out = [_titulo(v, w)]
    if md['tipo'] == 'svg_dispersao':
        cfg = md['extra']
        col = {'tabela': cfg['tabela'], 'nome': cfg['coluna'], 'tipo': 'coluna'}
        rot = categorias(sim.m, col)
        xs = [sim.valor(cfg['x'], [(col, r)]) for r in rot]
        ys = [sim.valor(cfg['y'], [(col, r)]) for r in rot]
        def escala(vals):
            folga = (max(vals) - min(vals)) * 0.1 + 1
            return min(vals) - folga, max(vals) - min(vals) + 2 * folga
        (bx, fx), (by, fy) = escala(xs), escala(ys)
        x0, y0, x1, y1 = 50, h - 30, w - 20, 40
        out.append(f'<line x1="{x0}" y1="{y0}" x2="{x1}" y2="{y0}" class="grade"/><line x1="{x0}" y1="{y1}" x2="{x0}" y2="{y0}" class="grade"/>'
                   f'<text x="{x1}" y="{y0 + 18}" class="eixo" text-anchor="end">{_e(cfg["x"])} →</text>'
                   f'<text x="{x0 + 4}" y="{y1 + 4}" class="eixo">↑ {_e(cfg["y"])}</text>')
        for r, a, b in zip(rot, xs, ys):
            px, py = x0 + (x1 - x0) * (a - bx) / fx, y0 - (y0 - y1) * (b - by) / fy
            out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="14" fill="{cores[0]}" fill-opacity=".85"><title>{_e(r)}</title></circle>'
                       f'<text x="{px:.1f}" y="{py + 4:.1f}" text-anchor="middle" class="eixo" style="fill:#FFFFFF;font-weight:600">'
                       f'{_e(_iniciais(r))}</text>')
        return ''.join(out)
    if md['tipo'] == 'svg_espinha':
        return ''.join(out) + _espinha(sim, md, w, h, cores)
    return ''.join(out) + (f'<rect x="12" y="34" width="{w - 24}" height="{h - 46}" rx="8" class="caixa"/>'
                           f'<text x="{w / 2}" y="{h / 2}" class="sub" text-anchor="middle">imagem SVG · só no Power BI</text>')


def _espinha(sim, md, w, h, cores):
    """Espinha de peixe: o mesmo desenho da medida DAX (640 x 320), com os piores que a média de cada corte."""
    cfg = md['extra']
    base = medida(sim.m, cfg['base'])
    maior = base['polaridade'] == 'maior_melhor'
    k = len(cfg['cortes'])
    passo = 500 / ((k + 1) // 2)
    esc = min((w - 24) / 640, (h - 40) / 320)
    out = [f'<g transform="translate({(w - 640 * esc) / 2:.1f} 34) scale({esc:.3f})">'
           f'<line x1="20" y1="160" x2="520" y2="160" stroke="#605E5C" stroke-width="4"/>'
           f'<rect x="522" y="130" width="114" height="60" rx="8" fill="{cores[0]}"/>'
           f'<text x="579" y="165" text-anchor="middle" class="eixo" style="font-size:16px;fill:#FFFFFF;font-weight:700">'
           f'{_e(_corta(base["nome"], 18))}</text>']
    for i, (tab, col) in enumerate(cfg['cortes']):
        campo = {'tabela': tab, 'nome': col, 'tipo': 'coluna'}
        vals = [(r, sim.valor(base['nome'], [(campo, r)])) for r in categorias(sim.m, campo)]
        media = sum(x for _, x in vals) / max(1, len(vals))
        piores = sorted([x for x in vals if (x[1] < media if maior else x[1] > media)], key=lambda x: x[1] if maior else -x[1])
        cima = i % 2 == 0
        xa = 10 + passo * (i // 2 + 1)
        xp = xa - 60
        yp, yt, y0 = (40, 30, 52) if cima else (280, 300, 190)
        out.append(f'<line x1="{xa:.0f}" y1="160" x2="{xp:.0f}" y2="{yp}" stroke="#A19F9D" stroke-width="2"/>'
                   f'<text x="{xp:.0f}" y="{yt}" class="eixo" style="font-size:18px;font-weight:700">{_e(col)}</text>')
        for j, (r, _) in enumerate(piores[:cfg['n']]):
            out.append(f'<text x="{xp - 6:.0f}" y="{y0 + 15 * j}" class="eixo" text-anchor="end" style="font-size:15px;fill:#A4262C">'
                       f'{_e(_corta(r, 20))}</text>')
    return ''.join(out) + '</g>'


def _aviso(sim, v, w, h, cores):
    """A faixa de aviso: só aparece quando há algo fora da meta."""
    texto = sim.valor(v['valores'][0]['nome'])
    if not texto:
        return f'<text x="12" y="{h / 2 + 5:.0f}" class="sub">(sem aviso: tudo dentro da meta)</text>'
    return (f'<rect x="0" y="0" width="{w}" height="{h}" rx="8" fill="#FDE7E9"/>'
            f'<text x="14" y="{h / 2 + 5:.0f}" class="cel" style="fill:#A4262C;font-weight:600">{_e(_corta(texto, int((w - 24) / 7)))}</text>')


def _html(sim, v, w, h, cores):
    """HTML Content: os blocos de indicador que a medida HTML monta."""
    md = medida(sim.m, v['valores'][0]['nome'])
    nomes = (md.get('extra') or {}).get('medidas') or []
    if not nomes:
        return _titulo(v, w) + f'<text x="12" y="{h / 2}" class="sub">HTML · só no Power BI (visual HTML Content)</text>'
    bw = (w - 24 - 12 * (len(nomes) - 1)) / len(nomes)
    out = []
    for i, n in enumerate(nomes):
        x = 12 + i * (bw + 12)
        base = medida(sim.m, n)
        out.append(f'<rect x="{x:.1f}" y="8" width="{bw:.1f}" height="{h - 16:.1f}" fill="#FFFFFF"/>'
                   f'<rect x="{x:.1f}" y="8" width="{bw:.1f}" height="4" fill="{cores[0]}"/>'
                   f'<text x="{x + 12:.1f}" y="32" class="sub">{_e(_corta(n, int(bw / 7)))}</text>'
                   f'<text x="{x + 12:.1f}" y="{min(h - 16, 64)}" class="kpi2"{_cor_status(sim, n)}>'
                   f'{_e(formatar(sim.valor(n), base["formato"], True))}</text>')
    return ''.join(out)


def _vegalite(sim, v, w, h, cores):
    """Deneb (Vega-Lite): o pirulito da especificação padrão."""
    rot = categorias(sim.m, v['categoria'])
    md = v['valores'][0]
    vals = sorted(((r, sim.valor(md['nome'], [(v['categoria'], r)])) for r in rot), key=lambda x: -x[1])
    mx = max([x for _, x in vals] + [1e-9]) * 1.15
    top, esq = 40, min(150, w * 0.3)
    gh = (h - top - 10) / max(1, len(vals))
    out = [_titulo(v, w)]
    for i, (r, val) in enumerate(vals):
        y = top + i * gh + gh / 2
        x = esq + (w - esq - 70) * val / mx
        out.append(f'<text x="{esq - 8}" y="{y + 4:.1f}" class="eixo" text-anchor="end">{_e(_corta(r, int(esq / 6.5)))}</text>'
                   f'<line x1="{esq}" x2="{x:.1f}" y1="{y:.1f}" y2="{y:.1f}" stroke="#C8C6C4" stroke-width="2"/>'
                   f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{cores[0]}"/>'
                   f'<text x="{x + 12:.1f}" y="{y + 4:.1f}" class="eixo">{_e(formatar(val, md["formato"], True))}</text>')
    return ''.join(out)


def _cartoes(sim, v, w, h, cores):
    """Cartão novo com vários indicadores lado a lado."""
    mds = [x for x in v['valores'] if x]
    n = max(1, len(mds))
    if h > w * 1.2:                                  # coluna estreita: os indicadores um embaixo do outro
        ch = (h - 24) / n
        tam = max(18, min(44, ch * 0.35, w / 5))
        out = []
        for i, md in enumerate(mds):
            y0 = 12 + i * ch
            if i:
                out.append(f'<line x1="16" x2="{w - 16}" y1="{y0:.1f}" y2="{y0:.1f}" class="grade"/>')
            cor = _cor_status(sim, md['nome'])
            estilo = f' style="font-size:{tam:.0f}px;{cor[8:-1]}"' if cor else f' style="font-size:{tam:.0f}px"'
            out.append(f'<text x="{w / 2:.1f}" y="{y0 + ch / 2 + tam * 0.3:.0f}" class="kpi" text-anchor="middle"{estilo}>'
                       f'{_e(formatar(sim.valor(md["nome"]), md["formato"], True))}</text>'
                       f'<text x="{w / 2:.1f}" y="{y0 + ch / 2 + tam * 0.3 + 22:.0f}" class="sub" text-anchor="middle">'
                       f'{_e(_corta(md["nome"], int(w / 7)))}</text>')
        return ''.join(out)
    cw = (w - 24) / n
    tam = max(18, min(44, (h - 50) * 0.5, cw / 5))
    out = []
    for i, md in enumerate(mds):
        x = 12 + i * cw
        if i:
            out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="16" y2="{h - 16}" class="grade"/>')
        cor = _cor_status(sim, md['nome'])
        txt = formatar(sim.valor(md['nome']), md['formato'], True) + _simbolo(sim, md['nome'])
        t2 = min(tam, (cw - 16) / (0.58 * max(1, len(txt))))
        estilo = f' style="font-size:{t2:.0f}px;{cor[8:-1]}"' if cor else f' style="font-size:{t2:.0f}px"'
        out.append(f'<text x="{x + cw / 2:.1f}" y="{h / 2 + tam * 0.3:.0f}" class="kpi" text-anchor="middle"{estilo}>'
                   f'{_e(formatar(sim.valor(md["nome"]), md["formato"], True))}{_e(_simbolo(sim, md["nome"]))}</text>'
                   f'<text x="{x + cw / 2:.1f}" y="{h / 2 + tam * 0.3 + 22:.0f}" class="sub" text-anchor="middle">'
                   f'{_e(_corta(md["nome"], int(cw / 7)))}</text>')
    return ''.join(out)


def _decomposicao(sim, v, w, h, cores):
    """Árvore de decomposição: o total à esquerda e o primeiro corte aberto em ramos, do maior para o menor."""
    md, corte = v['valores'][0], v['linhas'][0]
    rot = categorias(sim.m, corte)[:6]
    vals = sorted(((r, sim.valor(md['nome'], [(corte, r)])) for r in rot), key=lambda x: -x[1])
    out = [_titulo(v, w), f'<text x="12" y="42" class="sub">abrir por: {_e(" › ".join(c["nome"] for c in v["linhas"]))}</text>']
    bw, bh = min(240, w * 0.3), 64
    bx, by = 12, (h + 30) / 2 - bh / 2
    total = formatar(sim.valor(md['nome']), md['formato'], True)
    t2 = max(14, min(30, (bw - 20) / (0.6 * max(1, len(total)))))
    out.append(f'<rect x="{bx}" y="{by:.1f}" width="{bw:.1f}" height="{bh}" rx="10" fill="{cores[0]}"/>'
               f'<text x="{bx + 12}" y="{by + 24:.1f}" class="sub" style="fill:#FFFFFF">{_e(_corta(md["nome"], int(bw / 7.5)))}</text>'
               f'<text x="{bx + 12}" y="{by + 52:.1f}" class="kpi2" style="fill:#FFFFFF;font-size:{t2:.0f}px">{_e(total)}</text>')
    x0 = bx + bw + 48
    larg = max(40, w - x0 - 90)
    gh = (h - 64) / max(1, len(vals))
    mx = max([x[1] for x in vals] + [1e-9])
    for i, (r, val) in enumerate(vals):
        y = 56 + i * gh + gh / 2
        out.append(f'<path d="M{bx + bw} {by + bh / 2:.1f} C{x0 - 24} {by + bh / 2:.1f} {x0 - 24} {y:.1f} {x0} {y:.1f}" '
                   f'fill="none" class="trilho"/>'
                   f'<text x="{x0}" y="{y - 6:.1f}" class="eixo">{_e(_corta(r, int(larg / 7)))}</text>'
                   f'<rect x="{x0}" y="{y:.1f}" width="{larg * val / mx:.1f}" height="{min(12, gh * 0.3):.1f}" rx="3" fill="{cores[1 % len(cores)]}"/>'
                   f'<text x="{x0 + larg * val / mx + 6:.1f}" y="{y + 10:.1f}" class="eixo">{_e(formatar(val, md["formato"], True))}</text>')
    return ''.join(out)


def _dispersao(sim, v, w, h, cores):
    """Dispersão: cada categoria é um ponto (x, y) e, se houver, o tamanho é a terceira medida."""
    cat = v['categoria']
    mx_, my_ = v['valores'][0], v['valores'][1]
    tam = v['valores'][2] if len(v['valores']) > 2 else None
    rot = categorias(sim.m, cat)
    pts = [(r, sim.valor(mx_['nome'], [(cat, r)]), sim.valor(my_['nome'], [(cat, r)]),
            sim.valor(tam['nome'], [(cat, r)]) if tam else 1) for r in rot]
    esq, top, base, dir_ = 60, 40, h - 34, w - 20
    xs, ys, ss = [p[1] for p in pts], [p[2] for p in pts], [p[3] for p in pts]
    x0, x1 = min(xs), max(xs) or 1
    y0, y1 = min(ys), max(ys) or 1
    smax = max(ss) or 1
    out = [_titulo(v, w)]
    for g in range(4):
        y = top + (base - top) * g / 3
        out.append(f'<line x1="{esq}" x2="{dir_}" y1="{y:.1f}" y2="{y:.1f}" class="grade"/>')
    for r, x, y, s in pts:
        px = esq + (dir_ - esq) * ((x - x0) / ((x1 - x0) or 1)) * 0.9 + (dir_ - esq) * 0.05
        py = base - (base - top) * ((y - y0) / ((y1 - y0) or 1)) * 0.85 - (base - top) * 0.07
        raio = 5 + 14 * (s / smax) if tam else 7
        rot_ = _e(_corta(r, 12))
        lado = (f'x="{px - raio - 3:.1f}" text-anchor="end"' if px + raio + 8 * len(rot_) > dir_
                else f'x="{px + raio + 3:.1f}"')
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{raio:.1f}" fill="{cores[0]}" fill-opacity=".55" stroke="{cores[0]}">'
                   f'<title>{_e(r)}</title></circle><text {lado} y="{py + 4:.1f}" class="eixo">{rot_}</text>')
    jitter = (medida(sim.m, mx_['nome']) or {}).get('tipo') == 'jitter'      # o X só espalha os pontos: sem eixo
    out.append(('' if jitter else
                f'<text x="{(esq + dir_) / 2:.1f}" y="{h - 8}" class="eixo" text-anchor="middle">{_e(mx_["nome"])} →</text>')
               + f'<text x="14" y="{(top + base) / 2:.1f}" class="eixo" transform="rotate(-90 14 {(top + base) / 2:.1f})" '
               f'text-anchor="middle">{_e(my_["nome"])} →</text>')
    return ''.join(out)


def _area(sim, v, w, h, cores):
    """Área: a linha com o espaço até o eixo preenchido."""
    rot, ss = _series(sim, v)
    top, base, esq = (52 if len(ss) > 1 else 36), h - 30, 34
    meta = _meta_fixa(sim, v)
    mx = _escala(ss, meta)
    gw = (w - 2 * esq) / max(1, len(rot) - 1)
    out = [_titulo(v, w), _legenda(ss, cores, w, 42)]
    if meta is not None:
        ym = base - (base - top) * meta / mx
        out.append(_linha_meta(esq, ym, w - esq, ym, formatar(meta, ss[0][2], True), w - esq, ym - 4))
    for k, (nome, s, fmt) in enumerate(ss):
        pts = [f'{esq + i * gw:.1f},{base - (base - top) * s[i] / mx:.1f}' for i in range(len(rot))]
        out.append(f'<polygon points="{esq},{base} {" ".join(pts)} {esq + (len(rot) - 1) * gw:.1f},{base}" '
                   f'fill="{cores[k % len(cores)]}" fill-opacity=".25"/>'
                   f'<polyline points="{" ".join(pts)}" fill="none" stroke="{cores[k % len(cores)]}" stroke-width="2.5"/>')
    passo = max(1, -(-len(rot) // max(1, int((w - 2 * esq) / 64))))
    for i in range(0, len(rot), passo):
        out.append(f'<text x="{esq + i * gw:.1f}" y="{base + 16}" class="eixo" text-anchor="middle">{_e(rot[i])}</text>')
    return ''.join(out)


def _mapa(sim, v, w, h, cores):
    """Mapa ilustrativo: uma bolha por local, do tamanho do valor (o Power BI desenha o mapa de verdade)."""
    cat = v['categoria']
    rot = categorias(sim.m, cat)
    out = [_titulo(v, w), f'<rect x="12" y="34" width="{w - 24}" height="{h - 46}" rx="10" class="caixa" style="fill:#EEF3F8;stroke:#D0DAE6"/>',
           f'<text x="{w - 20}" y="{h - 20}" class="sub" text-anchor="end">mapa ilustrativo</text>']
    import random as _r
    g = _r.Random(cat['nome'])
    if v.get('marcador'):                            # cada local vira a imagem da medida (estrelas, progresso...)
        img = medida(sim.m, v['marcador'])
        desenho = {'svg_estrelas': _estrelas, 'svg_progresso': _progresso, 'svg_pilula': _pilula, 'svg_seta': _seta,
                   'svg_posicao': _selo, 'svg_variacao': _variacao}.get(img['tipo'])
        for r in rot:
            cx, cy = g.uniform(40, w - 150), g.uniform(64, h - 40)
            out.append(f'<rect x="{cx - 4:.1f}" y="{cy - 4:.1f}" width="104" height="24" rx="6" fill="#FFFFFF" stroke="#C8C6C4"/>'
                       + (desenho(sim, img, [(cat, r)], cx, cy, 96) if desenho else
                          f'<text x="{cx:.1f}" y="{cy + 12:.1f}" class="sub">SVG</text>')
                       + f'<text x="{cx + 50:.1f}" y="{cy - 8:.1f}" class="eixo" text-anchor="middle">{_e(_corta(r, 14))}</text>')
        return ''.join(out)
    md = v['valores'][0]
    vals = [sim.valor(md['nome'], [(cat, r)]) for r in rot]
    mx = max(vals + [1e-9])
    leg = categorias(sim.m, v['legenda'])[:5] if v.get('legenda') else []
    for r, val in zip(rot, vals):
        cx, cy = g.uniform(40, w - 60), g.uniform(60, h - 40)
        raio = 6 + 22 * (val / mx)
        if v.get('camada') == 'colunas':             # coluna 3D: a altura é o valor
            alto = 8 + 60 * (val / mx)
            out.append(f'<rect x="{cx - 4:.1f}" y="{cy - alto:.1f}" width="8" height="{alto:.1f}" fill="{cores[0]}"/>'
                       f'<path d="M{cx - 4:.1f},{cy - alto:.1f} l4,-3 l4,3 Z" fill="{cores[0]}" fill-opacity=".6"/>')
            out.append(f'<text x="{cx:.1f}" y="{cy + 14:.1f}" class="eixo" text-anchor="middle">{_e(_corta(r, 14))}</text>')
            continue
        if leg:                                      # cada local vira uma pizza com a composição da legenda
            partes = [sim.valor(md['nome'], [(cat, r), (v['legenda'], l)]) for l in leg]
            tot, a = sum(partes) or 1, -math.pi / 2
            for k, pv in enumerate(partes):
                b = a + 2 * math.pi * pv / tot
                grande = 1 if b - a > math.pi else 0
                out.append(f'<path d="M{cx:.1f},{cy:.1f} L{cx + raio * math.cos(a):.1f},{cy + raio * math.sin(a):.1f} '
                           f'A{raio:.1f},{raio:.1f} 0 {grande} 1 {cx + raio * math.cos(b):.1f},{cy + raio * math.sin(b):.1f} Z" '
                           f'fill="{cores[k % len(cores)]}" stroke="#FFFFFF" stroke-width="1"/>')
                a = b
        else:
            out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{raio:.1f}" fill="{cores[0]}" fill-opacity=".55" stroke="{cores[0]}"/>')
        out.append(f'<text x="{cx:.1f}" y="{cy - raio - 4:.1f}" class="eixo" text-anchor="middle">{_e(_corta(r, 14))}</text>')
    if leg:
        out.append(_legenda([(l, [0], None) for l in leg], cores, w, 46))
    return ''.join(out)


def _segmentador(sim, v, w, h, cores):
    return (f'<text x="12" y="20" class="sub">{_e(_corta(v["titulo"], int(w / 6.5)))} · filtro ilustrativo</text>'
            f'<rect x="12" y="28" width="{w - 24}" height="22" rx="3" class="caixa"/>'
            f'<text x="20" y="43" class="cel">Tudo</text><text x="{w - 26}" y="43" class="cel">▾</text>')


def _tabela(sim, v, w, h, cores):
    cols = v['campos']
    chaves = [c for c in cols if c['tipo'] == 'coluna']
    linhas = [[(chaves[0], r)] for r in categorias(sim.m, chaves[0])] if chaves else [[]]
    medidas_t = [c for c in cols if c['tipo'] == 'medida']
    if chaves and medidas_t:                       # linha em que toda medida fica em branco some, como no Power BI
        linhas = [l for l in linhas if any(sim.valor(c['nome'], l) is not None for c in medidas_t)] or linhas
    radar = next((c for c in medidas_t if (medida(sim.m, c['nome']) or {}).get('tipo') == 'svg_radar'), None)
    rh = 64 if radar else 22                         # o radar pede uma linha alta (a imagem tem 64 x 64)
    n = max(1, min(len(linhas), int((h - 84) // rh)))
    if len(linhas) > n:
        n = max(1, n - 1)                            # espaço para a linha "Outros"
    cw = (w - 24) / len(cols)
    out = [_titulo(v, w)]

    def x_de(k, c):
        return 12 + k * cw + (cw - 6 if c['tipo'] == 'medida' else 0)

    for k, c in enumerate(cols):
        anc = 'end' if c['tipo'] == 'medida' else 'start'
        out.append(f'<text x="{x_de(k, c):.1f}" y="48" class="cab" text-anchor="{anc}">{_e(_corta(c["nome"], int(cw / 7)))}</text>')
    out.append(f'<line x1="12" x2="{w - 12}" y1="54" y2="54" class="grade"/>')
    escala = {}                                      # barra x meta: o mesmo eixo para todas as linhas
    for c in cols:
        md = medida(sim.m, c['nome']) if c['tipo'] == 'medida' else None
        if md and md['tipo'] == 'svg_barra_meta' and md['svg'].get('meta'):
            vals = [max(sim.valor(md['svg']['base'], l), sim.valor(md['svg']['meta'], l)) for l in linhas]
            escala[c['nome']] = (md, (max(vals) if vals else 0) * 1.1)
    for i in range(n):
        topo = 57 + i * rh
        y = topo + rh / 2 + 4
        if i % 2:
            out.append(f'<rect x="12" y="{topo}" width="{w - 24}" height="{rh}" class="zebra"/>')
        for k, c in enumerate(cols):
            cor = ''
            md_img = medida(sim.m, c['nome']) if c['tipo'] == 'medida' else None
            if md_img and md_img.get('imagem'):
                desenho = {'svg_pilula': _pilula, 'svg_seta': _seta, 'svg_posicao': _selo,
                           'svg_variacao': _variacao, 'svg_estrelas': _estrelas,
                           'svg_progresso': _progresso}.get(md_img['tipo'])
                if md_img['tipo'] == 'svg_radar':
                    out.append(_radar(sim, md_img, linhas[i], 12 + k * cw + 4, topo + 2, cw - 10, rh - 4))
                elif desenho:
                    out.append(desenho(sim, md_img, linhas[i], 12 + k * cw + 4, y - 12, cw - 10))
                else:
                    out.append(_barra_meta(sim, escala.get(c['nome']), linhas[i], 12 + k * cw + 4, y - 12, cw - 10))
                continue
            if c['tipo'] == 'medida':
                txt = formatar(sim.valor(c['nome'], linhas[i]), c['formato']) + _simbolo(sim, c['nome'], linhas[i])
                cor = _cor_status(sim, c['nome'], linhas[i])
            elif linhas[i] and linhas[i][0][0] is c:
                txt = linhas[i][0][1]
            else:
                rot = categorias(sim.m, c)
                txt = rot[i % len(rot)]
            anc = 'end' if c['tipo'] == 'medida' else 'start'
            out.append(f'<text x="{x_de(k, c):.1f}" y="{y}" class="cel" text-anchor="{anc}"{cor}>{_e(_corta(txt, int(cw / 6.5)))}</text>')
    if len(linhas) > n and n > 1:                    # as linhas que não couberam viram "Outros", e o total fecha
        y = 57 + n * rh + 15
        restantes = linhas[n:]
        for k, c in enumerate(cols):
            if c['tipo'] == 'medida':
                md = medida(sim.m, c['nome'])
                if md.get('imagem'):
                    continue
                if sim.aditiva(md):
                    resto = sum(sim.valor(c['nome'], l) for l in restantes)
                    txt = formatar(resto, c['formato'])
                else:
                    txt = '…'
                out.append(f'<text x="{x_de(k, c):.1f}" y="{y}" class="cel" text-anchor="end">{_e(txt)}</text>')
            elif k == 0:
                out.append(f'<text x="12" y="{y}" class="cel">Outros ({len(restantes)})</text>')
        n += 1
    y = 57 + n * rh + 15
    out.append(f'<line x1="12" x2="{w - 12}" y1="{y - 14}" y2="{y - 14}" class="grade"/>')
    for k, c in enumerate(cols):
        if c['tipo'] == 'medida' and (medida(sim.m, c['nome']) or {}).get('imagem'):
            continue                                 # no total a imagem fica vazia (HASONEVALUE)
        if c['tipo'] == 'medida':
            out.append(f'<text x="{x_de(k, c):.1f}" y="{y + 2}" class="cab" text-anchor="end">'
                       f'{_e(formatar(sim.valor(c["nome"]), c["formato"]))}</text>')
        elif k == 0:
            out.append(f'<text x="12" y="{y + 2}" class="cab">Total</text>')
    return ''.join(out)


def _matriz(sim, v, w, h, cores):
    linha_c = v['linhas'][0]
    linhas = categorias(sim.m, linha_c)
    col_c = v['colunas'][0] if v['colunas'] else None
    colunas = categorias(sim.m, col_c)[:6] if col_c else []
    md = v['valores'][0]
    heads = colunas or [x['nome'] for x in v['valores']]
    n = max(1, min(len(linhas), int((h - 84) // 22)))
    cw = (w - 24) / (len(heads) + 3.5)
    out = [_titulo(v, w), f'<text x="12" y="48" class="cab">{_e(_corta(linha_c["nome"], int(2.2 * cw / 7)))}</text>']
    bolha = (medida(sim.m, md['nome']) or {}).get('tipo') == 'svg_bolha' and colunas
    for k, hd in enumerate(heads + (['Total'] if colunas and not bolha else [])):
        out.append(f'<text x="{12 + (k + 3.5) * cw - 6:.1f}" y="48" class="cab" text-anchor="end">{_e(_corta(hd, int(cw / 7)))}</text>')
    out.append(f'<line x1="12" x2="{w - 12}" y1="54" y2="54" class="grade"/>')
    bolha = (medida(sim.m, md['nome']) or {}).get('tipo') == 'svg_bolha' and colunas
    if bolha:                                        # o raio segue a raiz do valor: a área fica proporcional
        base = medida(sim.m, md['nome'])['svg']['base']
        maior = max([sim.valor(base, [(linha_c, l), (col_c, c)]) for l in linhas for c in colunas] + [1e-9])
    for i in range(n):
        y = 72 + i * 22
        out.append(f'<text x="12" y="{y}" class="cel">{_e(_corta(linhas[i], int(2.2 * cw / 7)))}</text>')
        for k, hd in enumerate(heads):
            if bolha:
                val = sim.valor(base, [(linha_c, linhas[i]), (col_c, hd)])
                out.append(f'<circle cx="{12 + (k + 3.5) * cw - cw / 2:.1f}" cy="{y - 4}" r="{math.sqrt(max(0, val / maior)) * 10:.1f}" '
                           f'fill="{cores[0]}" fill-opacity=".7"><title>{_e(hd)}: {_e(formatar(val, medida(sim.m, base)["formato"]))}</title></circle>')
                continue
            if colunas:
                filtros, nome = [(linha_c, linhas[i]), (col_c, hd)], md['nome']
                fmt = md['formato']
            else:
                filtros, nome = [(linha_c, linhas[i])], hd
                fmt = v['valores'][k]['formato']
            val = sim.valor(nome, filtros)
            out.append(f'<text x="{12 + (k + 3.5) * cw - 6:.1f}" y="{y}" class="cel" text-anchor="end"'
                       f'{_cor_status(sim, nome, filtros)}>{_e(formatar(val, fmt, True) + _simbolo(sim, nome, filtros))}</text>')
        if colunas and not bolha:
            tot = sim.valor(md['nome'], [(linha_c, linhas[i])])
            out.append(f'<text x="{12 + (len(heads) + 3.5) * cw - 6:.1f}" y="{y}" class="cab" text-anchor="end">'
                       f'{_e(formatar(tot, md["formato"], True))}</text>')
    return ''.join(out)


def _series(sim, v):
    rot = categorias(sim.m, v['categoria'])
    if v['legenda']:
        leg = categorias(sim.m, v['legenda'])[:4]
        md = v['valores'][0]
        return rot, [(l, sim.serie(md['nome'], v['categoria'], rot, [(v['legenda'], l)]), md['formato']) for l in leg]
    return rot, [(x['nome'], sim.serie(x['nome'], v['categoria'], rot), x['formato']) for x in v['valores']]


def _legenda(series, cores, w, y):
    if len(series) < 2:
        return ''
    out, x = [], 12
    for i, (nome, _, _) in enumerate(series):
        out.append(f'<circle cx="{x + 5}" cy="{y - 4}" r="5" fill="{cores[i % len(cores)]}"/>'
                   f'<text x="{x + 14}" y="{y}" class="sub">{_e(_corta(nome, 26))}</text>')
        x += 24 + min(len(nome), 26) * 6.5
    return ''.join(out)


def _escala(series, meta=None):
    return max([max(s) for _, s, _ in series] + [meta or 0, 1e-9]) * 1.12


def _meta_fixa(sim, v):
    """O valor da linha de meta do gráfico (só meta fixa, como no Power BI) ou None."""
    md = v.get('meta') and medida(sim.m, v['meta']['nome'])
    return float(md['dax']) if md and md['tipo'] == 'meta' else None


def _linha_meta(x1, y1, x2, y2, rotulo, tx, ty, anc='end'):
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#252423" stroke-width="1.5" stroke-dasharray="6 4"/>'
            f'<text x="{tx:.1f}" y="{ty:.1f}" class="eixo" text-anchor="{anc}" style="font-weight:600">Meta {_e(rotulo)}</text>')


def _colunas(sim, v, w, h, cores):
    rot, ss = _series(sim, v)
    top, base, esq = (48 if len(ss) > 1 else 34), h - 30, 12
    meta = _meta_fixa(sim, v)
    mx = _escala(ss, meta)
    gw = (w - 2 * esq) / len(rot)
    bw = gw * 0.7 / len(ss)
    out = [_titulo(v, w), _legenda(ss, cores, w, 42)]
    out.append(f'<line x1="{esq}" x2="{w - esq}" y1="{base}" y2="{base}" class="grade"/>')
    for i, r in enumerate(rot):
        for k, (_, s, fmt) in enumerate(ss):
            bh = max(0, (base - top - 14) * s[i] / mx)
            x = esq + i * gw + gw * 0.15 + k * bw
            cor = cores[k % len(cores)] if not v.get('cor') or i == 0 else '#C8C6C4'   # destaque: só o escolhido aceso
            out.append(f'<rect x="{x:.1f}" y="{base - bh:.1f}" width="{max(1, bw - 1):.1f}" height="{bh:.1f}" fill="{cor}">'
                       f'<title>{_e(r)}: {_e(formatar(s[i], fmt))}</title></rect>')
        out.append(f'<text x="{esq + i * gw + gw / 2:.1f}" y="{base + 16}" class="eixo" text-anchor="middle">{_e(_corta(_curto(r, int((gw - 4) / 8)), max(3, int((gw - 4) / 8))))}</text>')
    if len(ss) == 1 and gw > max(44, 6.5 * max(len(formatar(x, ss[0][2], True)) for x in ss[0][1])):   # rótulo só se couber
        s, fmt = ss[0][1], ss[0][2]
        for i in range(len(rot)):
            bh = max(0, (base - top - 14) * s[i] / mx)
            out.append(f'<text x="{esq + i * gw + gw / 2:.1f}" y="{base - bh - 4:.1f}" class="eixo" text-anchor="middle">'
                       f'{_e(formatar(s[i], fmt, True))}</text>')
    if meta is not None:
        ym = base - (base - top - 14) * meta / mx
        out.append(_linha_meta(esq, ym, w - esq, ym, formatar(meta, ss[0][2], True), w - esq, ym - 4))
    return ''.join(out)


def _barras(sim, v, w, h, cores):
    rot, ss = _series(sim, v)
    ordem = sorted(range(len(rot)), key=lambda i: -ss[0][1][i])    # maior primeiro, como no Power BI
    rot = [rot[i] for i in ordem]
    ss = [(n, [s[i] for i in ordem], f) for n, s, f in ss]
    top, esq = (52 if len(ss) > 1 else 36), min(150, w * 0.32)
    meta = _meta_fixa(sim, v)
    mx = _escala(ss, meta)
    lo = min([0] + [x or 0 for _, s, _ in ss for x in s]) * 1.12  # impacto: barras para os dois lados do zero
    largura = w - esq - 70
    x0 = esq + largura * -lo / (mx - lo)
    impacto = len(ss) == 1 and (medida(sim.m, v['valores'][0]['nome']) or {}).get('tipo') == 'impacto'
    maior = impacto and (medida(sim.m, v['valores'][0]['nome']) or {}).get('polaridade') != 'menor_melhor'
    gh = (h - top - 10) / len(rot)
    bh = gh * 0.7 / len(ss)
    out = [_titulo(v, w), _legenda(ss, cores, w, 42)]
    if lo < 0:
        out.append(f'<line x1="{x0:.1f}" x2="{x0:.1f}" y1="{top - 4}" y2="{h - 8}" class="grade"/>')
    for i, r in enumerate(rot):
        out.append(f'<text x="{esq - 8}" y="{top + i * gh + gh / 2 + 4:.1f}" class="eixo" text-anchor="end">{_e(_corta(r, int(esq / 6.5)))}</text>')
        for k, (_, s, fmt) in enumerate(ss):
            val = s[i] or 0
            bw = abs(largura * val / (mx - lo))
            y = top + i * gh + gh * 0.15 + k * bh
            cor = cores[k % len(cores)] if not v.get('cor') or i == 0 else '#C8C6C4'   # destaque: só o escolhido aceso
            if impacto:                              # verde quando ajudou o indicador, vermelho quando atrapalhou
                cor = COR_BOA if (val >= 0) == maior else COR_RUIM
            xb = x0 if val >= 0 else x0 - bw
            out.append(f'<rect x="{xb:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{max(1, bh - 1):.1f}" fill="{cor}">'
                       f'<title>{_e(r)}: {_e(formatar(s[i], fmt))}</title></rect>')
            if len(ss) == 1:
                out.append(f'<text x="{x0 + bw + 6:.1f}" y="{y + bh / 2 + 4:.1f}" class="eixo">{_e(formatar(s[i], fmt, True))}</text>'
                           if val >= 0 else
                           f'<text x="{xb - 6:.1f}" y="{y + bh / 2 + 4:.1f}" class="eixo" text-anchor="end">'
                           f'{_e(formatar(s[i], fmt, True))}</text>')
    if meta is not None:
        xm = x0 + largura * meta / (mx - lo)
        out.append(_linha_meta(xm, top - 4, xm, h - 8, formatar(meta, ss[0][2], True), xm - 4, h - 12))
    return ''.join(out)


def _linha(sim, v, w, h, cores):
    rot, ss = _series(sim, v)
    top, base, esq = (52 if len(ss) > 1 else 36), h - 30, 34
    meta = _meta_fixa(sim, v)
    mx = _escala(ss, meta)
    gw = (w - 2 * esq) / max(1, len(rot) - 1)
    out = [_titulo(v, w), _legenda(ss, cores, w, 42)]
    if meta is not None:
        ym = base - (base - top) * meta / mx
        out.append(_linha_meta(esq, ym, w - esq, ym, formatar(meta, ss[0][2], True), w - esq, ym - 4))
    for g in range(4):
        y = top + (base - top) * g / 3
        out.append(f'<line x1="{esq}" x2="{w - esq}" y1="{y:.1f}" y2="{y:.1f}" class="grade"/>')
    for k, (nome, s, fmt) in enumerate(ss):
        pts = ' '.join(f'{esq + i * gw:.1f},{base - (base - top) * s[i] / mx:.1f}' for i in range(len(rot)))
        out.append(f'<polyline points="{pts}" fill="none" stroke="{cores[k % len(cores)]}" stroke-width="2.5"/>')
        for i in range(len(rot)):
            out.append(f'<circle cx="{esq + i * gw:.1f}" cy="{base - (base - top) * s[i] / mx:.1f}" r="3" '
                       f'fill="{cores[k % len(cores)]}"><title>{_e(rot[i])}: {_e(formatar(s[i], fmt))}</title></circle>')
    passo = max(1, -(-len(rot) // max(1, int((w - 2 * esq) / 64))))
    for i in range(0, len(rot), passo):
        out.append(f'<text x="{esq + i * gw:.1f}" y="{base + 16}" class="eixo" text-anchor="middle">{_e(rot[i])}</text>')
    return ''.join(out)


def _rosca(sim, v, w, h, cores):
    rot, ss = _series(sim, v)
    s, fmt = ss[0][1], ss[0][2]
    tot = sum(s) or 1
    cx, cy = min(w * 0.32, (h - 30) / 2 + 20), (h + 30) / 2
    r = max(10, min(cx - 16, (h - 50) / 2))
    out, a = [_titulo(v, w)], -math.pi / 2
    for i, val in enumerate(s):
        b = a + 2 * math.pi * val / tot
        grande = 1 if b - a > math.pi else 0
        out.append(f'<path d="M{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f} A{r},{r} 0 {grande} 1 '
                   f'{cx + r * math.cos(b):.1f},{cy + r * math.sin(b):.1f}" fill="none" stroke="{cores[i % len(cores)]}" '
                   f'stroke-width="{r * 0.42:.1f}"><title>{_e(rot[i])}: {_e(formatar(val, fmt))}</title></path>')
        a = b
    passo = 20 if len(rot) * 20 < h - 40 else (h - 40) / len(rot)
    for i, rr in enumerate(rot):
        y = cy - len(rot) * passo / 2 + i * passo + 4
        out.append(f'<circle cx="{cx + r + 30}" cy="{y - 4}" r="5" fill="{cores[i % len(cores)]}"/>'
                   f'<text x="{cx + r + 40}" y="{y}" class="eixo">{_e(_corta(rr, 18))} · {numero_br(100 * s[i] / tot, 0)}%</text>')
    return ''.join(out)


# ------------------------------------------------------------- modelo (SVG)
def _niveis(m):
    """Fato no nível 0; cada dimensão no menor número de saltos até um fato."""
    viz = {}
    for r in m['relacionamentos']:
        viz.setdefault(r['de'], set()).add(r['para'])
        viz.setdefault(r['para'], set()).add(r['de'])
    nivel = {t['nome']: 0 for t in m['tabelas'] if t['tipo'] == 'fato'}
    if not nivel and m['tabelas']:
        nivel[m['tabelas'][0]['nome']] = 0
    fila = list(nivel)
    while fila:
        x = fila.pop(0)
        for y in sorted(viz.get(x, ())):
            if y not in nivel:
                nivel[y] = nivel[x] + 1
                fila.append(y)
    fim = max(nivel.values(), default=0)
    for t in m['tabelas']:
        nivel.setdefault(t['nome'], fim + 1)     # sem relacionamento: coluna à parte
    return nivel


def svg_modelo(m):
    nivel = _niveis(m)
    colunas = {}
    for t in m['tabelas']:
        colunas.setdefault(nivel[t['nome']], []).append(t)
    bw, W = 220, 1180
    ncol = max(colunas) + 1 if colunas else 1
    gap = (W - ncol * bw) / (ncol + 1)

    def caixa_h(t):
        return 52 + 18 * min(10, len([c for c in t['colunas'] if not c['oculta']]))

    pos, H = {}, 0
    for k in range(ncol):
        y = 30
        for t in colunas.get(k, []):
            pos[t['nome']] = (gap + k * (bw + gap), y, caixa_h(t))
            y += caixa_h(t) + 28
        H = max(H, y)
    out = [f'<svg viewBox="0 0 {W} {H}" class="modelo" role="img" aria-label="Diagrama do modelo de dados">']
    for r in m['relacionamentos']:
        if r['de'] not in pos or r['para'] not in pos:
            continue
        (x1, y1, h1), (x2, y2, h2) = pos[r['de']], pos[r['para']]
        if x1 == x2:
            a, b = (x1 + bw, y1 + 30), (x2 + bw, y2 + 30)
            meio = x1 + bw + 40
        else:
            a = (x1 + bw if x2 > x1 else x1, y1 + min(h1 / 2, 40))
            b = (x2 if x2 > x1 else x2 + bw, y2 + min(h2 / 2, 40))
            meio = (a[0] + b[0]) / 2
        d = f'M{a[0]},{a[1]} C{meio},{a[1]} {meio},{b[1]} {b[0]},{b[1]}'
        para_dir = b[0] > a[0] or x1 == x2
        decl = ' declarada' if str(r['prova']).startswith('declarada') else ''
        out.append(f'<path d="{d}" class="rel{"" if r["ativo"] else " inativa"}{decl}">'
                   f'<title>{_e(r["de"])}[{_e(r["de_coluna"])}] muitos → um {_e(r["para"])}[{_e(r["para_coluna"])}] · prova: {_e(r["prova"])}</title></path>'
                   f'<text x="{a[0] + (6 if para_dir else -6)}" y="{a[1] - 5}" class="card" text-anchor="{"start" if para_dir else "end"}">*</text>'
                   f'<text x="{b[0] + (6 if x1 == x2 else (-6 if para_dir else 6))}" y="{b[1] - 5}" class="card" '
                   f'text-anchor="{"start" if x1 == x2 else ("end" if para_dir else "start")}">1</text>')
    for t in m['tabelas']:
        x, y, h = pos[t['nome']]
        cls = 'fato' if t['tipo'] == 'fato' else 'dim'
        out.append(f'<g><rect x="{x}" y="{y}" width="{bw}" height="{h}" rx="6" class="cx {cls}"/>'
                   f'<text x="{x + 10}" y="{y + 20}" class="t">{_e(_corta(t["nome"], 26))}</text>'
                   f'<text x="{x + 10}" y="{y + 36}" class="sub">{_e(_corta((t.get("fonte") + " · " + t["origem"]) if t["origem"] else "gerada no Power Query", 32))}</text>'
                   f'<line x1="{x}" x2="{x + bw}" y1="{y + 44}" y2="{y + 44}" class="grade"/>')
        visiveis = [c for c in t['colunas'] if not c['oculta']]
        for k, c in enumerate(visiveis[:10]):
            out.append(f'<text x="{x + 12}" y="{y + 62 + k * 18}" class="cel">{_e(_corta(c["nome"], 30))}</text>')
        if len(visiveis) > 10:
            out.append(f'<text x="{x + bw - 10}" y="{y + h - 6}" class="sub" text-anchor="end">+{len(visiveis) - 10}</text>')
        out.append('</g>')
    out.append('</svg>')
    return ''.join(out)


# --------------------------------------------------------------------- HTML
CSS = """
:root{--fundo:#F3F2F1;--pagina:#FFFFFF;--texto:#252423;--suave:#605E5C;--borda:#E1DFDD;--destaque:#118DFF;
--aviso:#8A6100;--avisofundo:#FFF4CE;--erro:#A4262C}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--fundo:#1B1A19;--texto:#F3F2F1;--suave:#C8C6C4;--borda:#3B3A39}}
*{box-sizing:border-box}body{margin:0;font-family:"Segoe UI",system-ui,sans-serif;background:var(--fundo);color:var(--texto)}
header{display:flex;flex-wrap:wrap;gap:8px 20px;align-items:baseline;padding:16px 20px 8px}
header h1{font-size:20px;margin:0}header .meta{color:var(--suave);font-size:13px}
.faixa{margin:0 20px 10px;padding:8px 12px;border-radius:6px;background:var(--avisofundo);color:var(--aviso);font-size:13px}
nav{display:flex;gap:4px;padding:0 20px;flex-wrap:wrap;border-bottom:1px solid var(--borda)}
nav button{font:inherit;font-size:14px;border:0;background:none;color:var(--suave);padding:10px 14px;cursor:pointer;border-bottom:3px solid transparent}
nav button[aria-selected=true]{color:var(--texto);border-bottom-color:var(--destaque);font-weight:600}
main{padding:16px 20px 40px}section{display:none}section.ativa{display:block}
.palco{width:100%;overflow:hidden}.pagina{position:relative;transform-origin:0 0;background:var(--pagina);box-shadow:0 1px 4px rgba(0,0,0,.15)}
.pagina h2{position:absolute;left:16px;top:8px;margin:0;font-size:20px;color:#252423}
.vis{position:absolute;background:#fff;border:1px solid #EDEBE9;border-radius:4px}
.vis.segmentador,.vis.botoes{border-color:transparent;background:transparent}
.fundo{position:absolute;left:0;top:0;line-height:0}.fundo svg{display:block}
.desenhada .vis{background:transparent;border:0}
.desenhada .t{font-size:19px}.desenhada .sub{font-size:14px}.desenhada .kpi{font-size:54px}.desenhada .kpi2{font-size:30px}
.desenhada .eixo{font-size:13px}.desenhada .cab,.desenhada .cel{font-size:15px}.desenhada .info{width:26px;height:26px;font-size:14px;line-height:24px}.desenhada .vis.segmentador .caixa{fill:#fff}
.ir{position:absolute;background:transparent;border:0;padding:0;cursor:pointer;border-radius:12px;z-index:3}
.ir:hover{background:rgba(127,127,127,.12)}.ir:focus-visible{outline:3px solid var(--destaque)}
.ajuda{position:absolute;width:44px;height:44px;border-radius:50%;border:2px solid var(--destaque);background:#fff;
color:var(--destaque);font:700 20px Segoe UI,sans-serif;cursor:pointer;z-index:6}
.notas{position:absolute;inset:0;z-index:5;background:rgba(255,255,255,.35)}
.abre-tour,.fecha-tour{position:absolute;width:164px;height:44px;border-radius:22px;border:2px solid var(--destaque);
background:#fff;color:var(--destaque);font:700 14px Segoe UI,sans-serif;cursor:pointer;z-index:6}
.tour-proto{position:absolute;left:0;top:0;z-index:7}.fecha-tour{top:16px;z-index:1000}
.nota-ajuda{position:absolute;box-sizing:border-box;padding:10px 12px;background:rgba(255,255,255,.96);
border:2px solid var(--destaque);border-radius:8px;font:13px Segoe UI,sans-serif;color:#252423;overflow:auto}
.nota-ajuda b{display:block;margin-bottom:4px}.nota-ajuda p{margin:0 0 4px}
.escura .vis text{fill:#E6EAF2}.escura .vis .sub,.escura .vis .eixo{fill:#9AA4B8}.escura .grade,.escura .trilho{stroke:#2A3346}
.escura .zebra{fill:#1F2738}.escura .vis .caixa,.escura.desenhada .vis.segmentador .caixa{fill:#1A2130;stroke:#3A4560}
.escura .info{background:#1A2130;color:#C8D0E0;border-color:#3A4560}
.vis svg{display:block;font-family:"Segoe UI",system-ui,sans-serif}
.t{font-size:14px;font-weight:600;fill:#252423}.sub{font-size:12px;fill:#605E5C}.kpi{font-size:34px;font-weight:600;fill:#252423}
.kpi2{font-size:22px;font-weight:600;fill:#252423}.eixo{font-size:11px;fill:#605E5C}.cab{font-size:12px;font-weight:600;fill:#252423}
.cel{font-size:12px;fill:#252423}.grade{stroke:#E1DFDD}.zebra{fill:#F8F8F8}.trilho{fill:none;stroke:#E1DFDD}
.caixa{fill:#fff;stroke:#8A8886}.nota{color:var(--suave);font-size:13px;margin:8px 0 0}
.modelo{width:100%;height:auto;background:var(--pagina);border-radius:6px}.cx{stroke-width:1.5}
.cx.fato{fill:#EAF3FF;stroke:#118DFF}.cx.dim{fill:#fff;stroke:#8A8886}.rel{stroke:#605E5C;stroke-width:1.5}
.rel{fill:none}.rel.inativa{stroke-dasharray:6 4}.rel.declarada{stroke:#C55A11;stroke-dasharray:3 3;stroke-width:2}.card{font-size:13px;font-weight:600;fill:#605E5C}
table .sub{color:#605E5C}
table{border-collapse:collapse;width:100%;font-size:13px;background:var(--pagina);color:#252423}th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--borda);vertical-align:top}
th{position:sticky;top:0;background:#F3F2F1}code,pre{font-family:Consolas,monospace;font-size:12px}pre{margin:0;white-space:pre-wrap}
.tabela-rolagem{overflow-x:auto}ul.lista{padding-left:20px;line-height:1.6}.ok{color:#107C10}.erro{color:var(--erro)}
@media (max-width:700px){header,main{padding-left:16px;padding-right:16px}nav{padding:0 8px}
.palco{height:auto!important;overflow:visible}.pagina{transform:none!important;width:auto!important;height:auto!important;
background:transparent;box-shadow:none}.pagina h2{position:static;margin:0 0 10px;color:var(--texto)}
.vis{position:relative!important;left:auto!important;top:auto!important;width:auto!important;height:auto!important;margin:0 0 10px}
.vis svg{width:100%;height:auto}.fundo,.ir{display:none}
.desenhada .vis:not(.segmentador):not(.botoes){background:#fff;border:1px solid #EDEBE9;border-radius:6px}
.escura.desenhada .vis:not(.segmentador):not(.botoes){background:#141A26;border-color:#2A3346}}
.decisao{display:flex;flex-direction:column;gap:6px;margin:6px 0 12px}.decisao label{display:flex;gap:8px;align-items:center}
#aprovador{font:inherit;padding:6px 8px;border:1px solid var(--borda);border-radius:6px;margin-left:6px}
.info{position:absolute;top:4px;right:4px;width:22px;height:22px;border-radius:50%;border:1px solid #C8C6C4;background:#fff;
color:#605E5C;font:600 12px/20px "Segoe UI",sans-serif;cursor:pointer;padding:0;z-index:2}
.info:hover,.info:focus{border-color:var(--destaque);color:var(--destaque);outline:none}
#painel{position:fixed;right:16px;bottom:16px;max-width:420px;width:calc(100% - 32px);max-height:60vh;overflow:auto;background:var(--pagina);
color:#252423;border:1px solid var(--borda);border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,.18);padding:14px 16px;display:none;z-index:10}
#painel.aberto{display:block}#painel h3{margin:0 24px 8px 0;font-size:15px}#painel dl{margin:0}#painel dt{font-weight:600;margin-top:10px}
#painel dd{margin:2px 0 0}#painel .fechar{position:absolute;top:8px;right:10px;border:0;background:none;font-size:18px;cursor:pointer;color:#605E5C}
.aprovar{max-width:980px}.aprovar .ind{background:var(--pagina);color:#252423;border:1px solid var(--borda);border-radius:8px;padding:12px 14px;margin:10px 0}
.aprovar label{display:flex;gap:10px;align-items:flex-start;cursor:pointer}.aprovar input[type=checkbox]{width:18px;height:18px;margin-top:2px}
.aprovar .det{color:#605E5C;font-size:13px;margin:4px 0 0 28px}.aprovar textarea{width:100%;min-height:64px;font:inherit;padding:8px;
border:1px solid var(--borda);border-radius:6px}.aprovar h3{margin:22px 0 6px}.botao{font:inherit;font-weight:600;border:0;border-radius:6px;
background:var(--destaque);color:#fff;padding:10px 16px;cursor:pointer}.botao:focus{outline:2px solid #252423}
.progresso{font-size:14px;margin:6px 0 12px}.copiado{color:#107C10;margin-left:10px}
@media print{nav,.faixa .so-tela,.info,#painel,.botao{display:none!important}section{display:block!important;break-after:page}
.palco{height:auto!important;overflow:visible}.pagina{transform:none!important;box-shadow:none;zoom:.62}body{background:#fff}}
"""

JS = """
const botoes=[...document.querySelectorAll('nav button')];
function abrir(id){const sec=document.getElementById(id);const aba=(sec&&sec.dataset.aba)||id;
botoes.forEach(b=>b.setAttribute('aria-selected',b.dataset.alvo===aba));
document.querySelectorAll('section').forEach(s=>s.classList.toggle('ativa',s.id===id));escalar();
try{history.replaceState(null,'','#'+id)}catch(e){}}
botoes.forEach(b=>b.addEventListener('click',()=>abrir(b.dataset.alvo)));
document.querySelectorAll('.ir').forEach(b=>b.addEventListener('click',()=>{abrir(b.dataset.ir);scrollTo(0,0);}));
document.querySelectorAll('.ajuda').forEach(b=>b.addEventListener('click',()=>{const n=b.nextElementSibling;n.hidden=!n.hidden;}));
document.querySelectorAll('.abre-tour').forEach(b=>b.addEventListener('click',()=>{const t=b.nextElementSibling;t.hidden=false;
t.querySelectorAll('details').forEach(d=>d.open=d.classList.contains('tg-raiz'));}));
document.querySelectorAll('.fecha-tour').forEach(b=>b.addEventListener('click',()=>{b.parentElement.hidden=true;}));
function escalar(){if(innerWidth<=700){document.querySelectorAll('.pagina').forEach(pg=>pg.style.transform='');return;}
document.querySelectorAll('section.ativa .palco').forEach(p=>{const pg=p.firstElementChild;
const k=Math.min(1,p.clientWidth/pg.offsetWidth);pg.style.transform='scale('+k+')';p.style.height=(pg.offsetHeight*k)+'px';});}
addEventListener('resize',escalar);
const h=location.hash.slice(1);abrir(h&&document.getElementById(h)&&document.getElementById(h).dataset.aba?h:botoes[0].dataset.alvo);
const painel=document.getElementById('painel');
function esc(s){return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
document.querySelectorAll('.info').forEach(b=>b.addEventListener('click',ev=>{ev.stopPropagation();
const d=JSON.parse(b.dataset.info);let x='<button class="fechar" aria-label="Fechar">×</button><h3>'+esc(d.titulo)+'</h3><dl>';
d.itens.forEach(i=>{x+='<dt>'+esc(i.nome)+'</dt><dd>'+esc(i.definicao||'Sem definição ainda.')+(i.meta?'<br><small>'+esc(i.meta)+'</small>':'')+'</dd>';});
if(!d.itens.length)x+='<dd>Filtro da página (ilustrativo no protótipo): escolha um valor e os números da página respondem a ele.'+(d.excecoes&&d.excecoes.length?' <b>Não mudam com este filtro:</b> '+esc(d.excecoes.join(', '))+'.':'')+'</dd>';
painel.innerHTML=x+'</dl>';painel.classList.add('aberto');painel.querySelector('.fechar').focus();
painel.querySelector('.fechar').addEventListener('click',()=>{painel.classList.remove('aberto');b.focus();});}));
document.addEventListener('keydown',e=>{if(e.key==='Escape')painel.classList.remove('aberto');});
const CHAVE='deidara:'+document.body.dataset.chave;
function ler(){try{return JSON.parse(localStorage.getItem(CHAVE)||'{}')}catch(e){return {}}}
function gravar(v){try{localStorage.setItem(CHAVE,JSON.stringify(v))}catch(e){}}
const estado=ler();
document.querySelectorAll('[data-guardar]').forEach(el=>{const k=el.dataset.guardar;
if(k in estado){if(el.type==='checkbox')el.checked=estado[k];else el.value=estado[k];}
el.addEventListener('input',()=>{estado[k]=el.type==='checkbox'?el.checked:el.value;gravar(estado);progresso();});});
function progresso(){const cs=[...document.querySelectorAll('.aprovar input[type=checkbox]')];const ok=cs.filter(c=>c.checked).length;
const p=document.getElementById('progresso');if(p)p.textContent=ok+' de '+cs.length+' indicador(es) confirmado(s)';}
progresso();
const copiar=document.getElementById('copiar');
if(copiar)copiar.addEventListener('click',()=>{const NL=String.fromCharCode(10);const b=document.body.dataset;
const dec=document.querySelector('input[name=decisao]:checked');const nome=(document.getElementById('aprovador').value||'').trim();
let t='Aceite do protótipo: '+b.projeto+' (versão '+b.versao+')'+NL+'Código: '+b.codigo+NL;
t+='Decisão: '+(dec?dec.value:'(não marcada)')+NL+'Aprovador: '+(nome||'(não informado)')+NL;
t+='Data: '+new Date().toLocaleDateString('pt-BR')+NL+NL+'Indicadores:'+NL;
document.querySelectorAll('.aprovar .ind').forEach(d=>{const c=d.querySelector('input');t+=(c.checked?'  [x] ':'  [ ] ')+d.dataset.nome+NL;});
document.querySelectorAll('.aprovar textarea').forEach(a=>{if(a.value.trim())t+=NL+a.dataset.rotulo+':'+NL+'  '+a.value.trim().split(NL).join(NL+'  ')+NL;});
const fim=()=>{document.getElementById('copiado').textContent='Resumo copiado: cole no e-mail ou no chat para o analista.';};
if(!dec||!nome){document.getElementById('copiado').textContent='Marque a decisão e escreva seu nome antes de copiar.';return;}
if(navigator.clipboard)navigator.clipboard.writeText(t).then(fim,()=>{prompt('Copie o resumo:',t)});else prompt('Copie o resumo:',t);});
document.querySelector('nav').addEventListener('keydown',e=>{const i=botoes.indexOf(document.activeElement);if(i<0)return;
let j=null;if(e.key==='ArrowRight')j=(i+1)%botoes.length;if(e.key==='ArrowLeft')j=(i-1+botoes.length)%botoes.length;
if(j!==null){e.preventDefault();botoes[j].focus();abrir(botoes[j].dataset.alvo);}});
"""


def _texto_meta(m, md):
    if not md.get('meta_medida'):
        return ''
    alvo = medida(m, md['meta_medida'])
    valor = formatar(float(alvo['dax']), alvo['formato'], True) if alvo and alvo['tipo'] == 'meta' else md['meta_medida']
    sentido = 'quanto maior, melhor' if md['polaridade'] == 'maior_melhor' else 'quanto menor, melhor'
    return f'Meta: {valor} ({sentido})'


def codigo_do_prototipo(m):
    """Identifica o que o gestor viu: muda quando muda qualquer coisa que aparece no painel."""
    import hashlib
    from tecnicas.katsu import retrato
    return hashlib.sha1(json.dumps(retrato(m), sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()[:8]


def _excecoes_do_filtro(m, v, pagina):
    from kibaku_nendo.especificacao import grafo_de_filtro as grafo_de_filtro, tabelas_da_medida as tabelas_da_medida, chega
    if v['tipo'] not in ('segmentador', 'botoes', 'abas', 'alternar') or not v.get('categoria'):
        return []
    g = grafo_de_filtro(m)
    nomes = {x['nome'] for o in pagina['visuais'] for x in o['valores'] + o['campos'] if x and x['tipo'] == 'medida'}
    return sorted(n for n in nomes
                  if not all(chega(m, g, v['categoria']['tabela'], a, n) for a in tabelas_da_medida(m, n)))


def _botao_info(m, v, pagina=None):
    nomes = [x['nome'] for x in v['valores'] + v['campos'] + ([v['meta']] if v.get('meta') else []) if x and x['tipo'] == 'medida']
    itens = []
    for n in dict.fromkeys(nomes):
        md = medida(m, n)
        if md and md['tipo'] != 'cor':
            itens.append({'nome': md['nome'], 'definicao': md['descricao'], 'meta': _texto_meta(m, md)})
    excecoes = _excecoes_do_filtro(m, v, pagina) if pagina else []
    dados = json.dumps({'titulo': v['titulo'], 'itens': itens, 'excecoes': excecoes}, ensure_ascii=False)
    return f'<button type="button" class="info" aria-label="O que é: {_e(v["titulo"])}" data-info="{_e(dados)}">i</button>'


def _secao_aprovar(m, problemas):
    onde = {}
    for pg in m['paginas']:
        for v in pg['visuais']:
            for x in v['valores'] + v['campos'] + ([v['meta']] if v.get('meta') else []):
                if x and x['tipo'] == 'medida':
                    onde.setdefault(x['nome'], []).append(pg['nome'])
    inds = []
    for md in m['medidas']:
        if md['tipo'] in ('cor', 'meta') or md['nome'] not in onde:
            continue
        paginas = ', '.join(dict.fromkeys(onde[md['nome']]))
        meta = _texto_meta(m, md)
        inds.append(f'<div class="ind" data-nome="{_e(md["nome"])}"><label><input type="checkbox" data-guardar="ok:{_e(md["nome"])}">'
                    f'<span><b>{_e(md["nome"])}</b> — {_e(md["descricao"] or "sem definição")}</span></label>'
                    f'<div class="det">Aparece em: {_e(paginas)}{" · " + _e(meta) if meta else ""}</div></div>')
    from kibaku_nendo.relato import para_gestor
    traduzidos = [t for t in dict.fromkeys(para_gestor(a) for a in problemas.avisos) if t]
    pontos = ''.join(f'<li>{_e(t)}</li>' for t in traduzidos) or '<li class="ok">Nenhum.</li>'
    comentarios = ''.join(f'<h3>Comentários sobre a página {_e(pg["nome"])}</h3><textarea data-guardar="c:{_e(pg["nome"])}" '
                          f'data-rotulo="Página {_e(pg["nome"])}" placeholder="O que mudar, tirar ou acrescentar?"></textarea>'
                          for pg in m['paginas'])
    return (f'<section id="aprovar" class="aprovar"><p>Antes de dizer "sim", confirme se cada número significa o que você '
            f'espera. Os valores do protótipo são fictícios: aqui se aprova <b>o que</b> é medido e <b>como</b> aparece.</p>'
            f'<div class="progresso" id="progresso"></div>{"".join(inds)}'
            f'<h3>Pontos de atenção (converse com o analista)</h3><ul class="lista">{pontos}</ul>{comentarios}'
            f'<h3>A sua decisão</h3><div class="decisao"><label><input type="radio" name="decisao" value="Aprovo" '
            f'data-guardar="d:aprovo"> Aprovo este protótipo</label><label><input type="radio" name="decisao" '
            f'value="Peço ajustes" data-guardar="d:ajustes"> Peço ajustes (veja os comentários)</label></div>'
            f'<p><label>Seu nome <input type="text" id="aprovador" data-guardar="nome" autocomplete="name"></label></p>'
            f'<p><button type="button" class="botao" id="copiar">Copiar resumo do aceite</button><span class="copiado" '
            f'id="copiado" role="status"></span></p><p class="nota">As marcações ficam só neste navegador: mande o resumo '
            f'copiado ao analista (e-mail ou chat). O aceite vale quando ele registra o seu "sim" no Deidara.</p></section>')


def _rotular_secao(s):
    """<section role=tabpanel ... aria-labelledby="aba-XYZ"> com id="XYZ" de volta."""
    import re as _re
    return _re.sub(r'<section role="tabpanel" tabindex="0" aria-labelledby="aba-([^"]+)"',
                   r'<section role="tabpanel" tabindex="0" id="\1" aria-labelledby="aba-\1"', s, count=1)


def gerar_html(m, problemas, versao):
    cores = m['tema']['cores']
    sim = Simulador(m)
    abas, secoes = [], []
    rel = paginas_do_relatorio(m)
    ids = [f'p{k + 1}' for k in range(len(rel))]
    aba_do_grupo = {}
    for i, pg in enumerate(rel):
        sid = ids[i]
        if not pg['oculta'] or pg.get('dica') or pg.get('detalhe'):   # dica e detalhe também se aprovam
            abas.append((sid, f'Dica · {pg["nome"]}' if pg.get('dica') else
                         f'Detalhe · {pg["nome"]}' if pg.get('detalhe') else pg['nome']))
            aba_do_grupo[pg['grupo']] = sid
        lay = montar(m, rel, i)
        vis = []
        for v, p in lay['posicoes']:
            vv = dict(v, titulo='') if id(v) in lay['sem_titulo'] else v
            vis.append(f'<div class="vis {v["tipo"]}" style="left:{p["x"]}px;top:{p["y"]}px;width:{p["w"]}px;height:{p["h"]}px">'
                       f'{_botao_info(m, v, pg)}{svg_visual(sim, vv, p, cores)}</div>')
        ir = ''.join(f'<button type="button" class="ir" data-ir="{ids[n["alvo"]]}" title="{_e(n["rotulo"])}" '
                     f'aria-label="{_e(n["rotulo"])}" style="left:{n["x"]}px;top:{n["y"]}px;width:{n["w"]}px;height:{n["h"]}px">'
                     f'</button>' for n in lay['nav'])
        if pg.get('ajuda'):
            from kibaku_nendo.relato import nota_de_ajuda
            notas = ''.join(f'<div class="nota-ajuda" style="left:{p["x"]}px;top:{p["y"]}px;width:{p["w"]}px;height:{p["h"]}px">'
                            + ''.join(f'<{"b" if k == 0 else "p"}>{_e(t)}</{"b" if k == 0 else "p"}>'
                                      for k, t in enumerate(nota_de_ajuda(m, v))) + '</div>' for v, p in lay['posicoes'])
            ir += (f'<button type="button" class="ajuda" aria-label="Como ler esta página" title="Como ler esta página" '
                   f'style="left:{lay["w"] - 64}px;top:{lay["h"] - 104}px">?</button><div class="notas" hidden>{notas}</div>')
        tour = next((medida(m, x['tour']) for x in m['paginas'] if x['nome'] == pg['nome'] and isinstance(x.get('tour'), str)),
                    None) if not pg['oculta'] else None
        if tour:                                     # o mesmo HTML do Power BI, por cima da página
            x_tour = lay['w'] - (248 if pg.get('ajuda') else 184)
            ir += (f'<button type="button" class="abre-tour" style="left:{x_tour}px;top:{lay["h"] - 104}px">▶ Tour guiado</button>'
                   f'<div class="tour-proto" hidden>{tour["extra"]["html"]}'
                   f'<button type="button" class="fecha-tour" style="left:{lay["w"] - 184}px">Voltar</button></div>')
        classes = 'pagina' + (' desenhada' if lay['fundo'] else '') + (' escura' if lay['escuro'] else '')
        fundo = f'<div class="fundo" aria-hidden="true">{lay["fundo"]}</div>' if lay['fundo'] else f'<h2>{_e(pg["nome"])}</h2>'
        desc = f'<p class="nota">{_e(pg["descricao"])}</p>' if pg['descricao'] and not lay['fundo'] else ''
        if pg.get('detalhe'):
            c = pg['detalhe']
            desc += (f'<p class="nota">Página de detalhamento: no Power BI, clique com o botão direito num ponto de '
                     f'{_e(c["tabela"])}[{_e(c["nome"])}] em outra página e escolha Detalhar; ela abre filtrada pelo item.</p>')
        if pg.get('dica'):
            de = [v.get('titulo') or v['tipo'] for x in m['paginas'] for v in x['visuais'] if v.get('dica') == pg['nome']]
            desc += (f'<p class="nota">Página de dica (320 x 240): aparece ao passar o mouse em '
                     f'{_e(", ".join(de) or "nenhum visual ainda")}.</p>')
        secoes.append(f'<section id="{sid}" data-aba="{aba_do_grupo.get(pg["grupo"], sid)}"><div class="palco">'
                      f'<div class="{classes}" style="width:{lay["w"]}px;height:{lay["h"]}px">'
                      f'{fundo}{"".join(vis)}{ir}</div></div>{desc}</section>')
    abas.append(('aprovar', 'Para aprovar'))
    secoes.append(_secao_aprovar(m, problemas))
    abas.append(('modelo', 'Modelo de dados'))
    rels = ''.join(f'<tr><td>{_e(r["de"])}[{_e(r["de_coluna"])}]</td><td>{_e(r["para"])}[{_e(r["para_coluna"])}]</td>'
                   f'<td>{"ativa" if r["ativo"] else "inativa"}</td><td>{_e(r["prova"])}'
                   + (f'<br><span class="sub">campos: {_e(", ".join(f"{a}={b}" for a, b in r["campos"]))}</span>' if r['composta'] else '')
                   + '</td></tr>' for r in m['relacionamentos'])
    secoes.append(f'<section id="modelo">{svg_modelo(m)}<h3>Relacionamentos (muitos → um)</h3><div class="tabela-rolagem"><table>'
                  f'<tr><th>De (muitos)</th><th>Para (um)</th><th>Estado</th><th>Prova da ligação</th></tr>{rels}</table></div></section>')
    abas.append(('indicadores', 'Indicadores'))
    linhas = ''.join(f'<tr><td><b>{_e(x["nome"])}</b><br><span class="sub">{_e(x["pasta"])}</span></td><td>{_e(x["descricao"])}</td>'
                     f'<td>{_e(x["formato"] or "")}</td><td><pre>{_e(x["dax"] or "")}</pre></td></tr>' for x in m['medidas']
                     if x['tipo'] != 'cor')
    secoes.append(f'<section id="indicadores"><div class="tabela-rolagem"><table><tr><th>Indicador</th><th>Definição</th>'
                  f'<th>Formato</th><th>DAX</th></tr>{linhas}</table></div></section>')
    abas.append(('pendencias', f'Pendências do analista ({len(problemas.avisos)})'))
    av = ''.join(f'<li>{_e(a)}</li>' for a in problemas.avisos) or '<li class="ok">Nenhuma pendência.</li>'
    secoes.append(f'<section id="pendencias"><p>Detalhe técnico dos pontos de atenção (para o analista):</p>'
                  f'<ul class="lista">{av}</ul></section>')
    secoes = [s.replace('<section id="', '<section role="tabpanel" tabindex="0" aria-labelledby="aba-', 1)
              .replace('aria-labelledby="aba-', 'aria-labelledby="aba-', 1) for s in secoes]
    secoes = [_rotular_secao(s) for s in secoes]
    nav = ''.join(f'<button type="button" role="tab" id="aba-{sid}" aria-controls="{sid}" data-alvo="{sid}">{_e(n)}</button>'
                  for sid, n in abas)
    meta = ' · '.join(x for x in [m['publico'] and f'Público: {m["publico"]}',
                                  m['responsavel'] and f'Responsável: {m["responsavel"]}',
                                  m.get('versao') and f'painel v{m["versao"]}', f'Deidara {versao}'] if x)
    chave_local = f'{m["projeto"]}|{m.get("versao") or versao}'
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(m['projeto'])} · protótipo</title><style>{CSS}</style></head>
<body data-chave="{_e(chave_local)}" data-projeto="{_e(m['projeto'])}" data-versao="{_e(m.get('versao') or '—')}" data-codigo="{codigo_do_prototipo(m)}">
<header><h1>{_e(m['projeto'])}</h1><span class="meta">{_e(meta)}</span></header>
<div class="faixa">Protótipo gerado pelo Deidara. Os números são fictícios: valide layout, indicadores e navegação, não valores.
<span class="so-tela">Clique em ⓘ para ver o que cada número significa; a aba <b>Para aprovar</b> reúne o que confirmar.</span></div>
<nav role="tablist">{nav}</nav><main>{''.join(secoes)}</main>
<aside id="painel" role="dialog" aria-live="polite"></aside>
<script>{JS}</script></body></html>
"""
