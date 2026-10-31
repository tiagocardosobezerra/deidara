"""
O desenho de cada visual do protótipo, em SVG, com os números fictícios do simulador (bunshin). Um desenho por
tipo de visual do argila.json; prototipo.py monta a página com eles.
"""

import html
import math

from kibaku_nendo.especificacao import COR_BOA, COR_RUIM, medida
from kibaku_nendo.desenhos import COR_ATENCAO
from tecnicas.bunshin.simulacao import categorias
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


def _eixo(r, rotulos, n):
    """Rótulo do eixo que cabe em `n` letras: sem a palavra que todos repetem ("Empresa A", "Empresa B" vira "A",
    "B"), o mês sem o ano, e só então as reticências."""
    rotulos = [str(x) for x in rotulos]
    if any(len(x) > n for x in rotulos) and len(rotulos) > 1:
        partes = [x.split(' ') for x in rotulos]
        comum = 0
        while all(len(p) > comum + 1 for p in partes) and len({p[comum] for p in partes}) == 1:
            comum += 1
        if comum:
            r = ' '.join(str(r).split(' ')[comum:])
    return _corta(_curto(r, n), max(3, n))


def svg_visual(sim, v, pos, cores):
    w, h = pos['w'], pos['h']
    corpo = {'cartao': _cartao, 'medidor': _medidor, 'segmentador': _segmentador, 'tabela': _tabela,
             'matriz': _matriz, 'rosca': _rosca, 'linha': _linha, 'barras': _barras, 'colunas': _colunas,
             'botoes': _botoes, 'cartoes': _cartoes, 'decomposicao': _decomposicao, 'dispersao': _dispersao,
             'area': _area, 'mapa': _mapa, 'abas': _abas, 'alternar': _alternar, 'skyline': _skyline,
             'setas': _setas, 'imagem': _imagem, 'aviso': _aviso, 'html': _html, 'vegalite': _vegalite, 'controle': _controle}[v['tipo']]
    return (f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{_e(v["titulo"])}">'
            f'{corpo(sim, v, w, h, cores)}</svg>')


def _cor_status(sim, nome, filtros=()):
    f = sim.faixa(nome, filtros)
    return '' if f is None else f' style="fill:{ {"boa": COR_BOA, "atencao": COR_ATENCAO, "ruim": COR_RUIM}[f] }"'


def _simbolo(sim, nome, filtros=()):
    f = sim.faixa(nome, filtros)
    return '' if f is None else {'boa': ' ✓', 'atencao': ' !', 'ruim': ' ✗'}[f]


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
    texto_da_medida = sim.valor(md['nome']) if mdl and mdl.get('formato') is None and mdl['tipo'] in ('leitura', 'c4') \
        else None
    if isinstance(texto_da_medida, str):           # medida de texto (a frase do Tobi, a meta x faixa), em linhas
        import textwrap
        texto = texto_da_medida
        for tam in (24, 21, 18, 16, 14):            # a maior letra em que a frase cabe no cartão
            linhas = textwrap.wrap(texto, max(16, int((w - 24) / (tam * 0.53))))
            if 40 + len(linhas) * tam * 1.4 <= h:
                break
        out = [f'<text x="12" y="20" class="sub">{_e(_corta(v["titulo"], int(w / 6.5)))}</text>']
        for i, l in enumerate(linhas[:max(1, int((h - 34) / (tam * 1.4)))]):
            out.append(f'<text x="12" y="{34 + tam * 1.4 * (i + 0.8):.0f}" class="cel" style="font-size:{tam}px">{_e(l)}</text>')
        return ''.join(out)
    val = sim.valor(md['nome'])
    meta = titulo_do_cartao(sim.m, v, sim)
    topo = f'<text x="12" y="20" class="sub">{_e(meta)}</text>' if meta else ''
    st = sim.status(md['nome'])
    selo = '' if st is None or w < 300 else (f'<text x="{w - 36}" y="20" class="sub" text-anchor="end"{_cor_status(sim, md["nome"])}>'
                                             f'{ {"boa": "✓ na meta", "atencao": "! perto da meta", "ruim": "✗ fora da meta"}[sim.faixa(md["nome"])] }</text>')   # estreito: a cor já diz
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
                       f'{_e(_eixo(r, rot, max(3, int(gw / 6))))}</text>')
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
    """Deneb (Vega-Lite): o pirulito da especificação padrão; modelo da galeria: a prévia que o autor gravou."""
    if v.get('modelo'):
        from tecnicas import galeria
        previa = galeria.previa_deneb(v['modelo'])
        it = galeria.item(v['modelo']) or {}
        corpo = (f'<image href="{_e(previa)}" x="12" y="34" width="{w - 24}" height="{h - 64}" '
                 'preserveAspectRatio="xMidYMid meet"/>' if previa else
                 f'<rect x="12" y="34" width="{w - 24}" height="{h - 64}" fill="#F3F2F1" rx="6"/>')
        return (_titulo(v, w) + corpo + f'<text x="12" y="{h - 12}" class="sub">Deneb · {_e(_corta(it.get("nome", ""), 40))}'
                f' ({_e(_corta(it.get("autor", ""), 30))}) · desenhado no Power BI com os dados reais</text>')
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
        out.append(f'<text x="{esq + i * gw + gw / 2:.1f}" y="{base + 16}" class="eixo" text-anchor="middle">'
                   f'{_e(_eixo(r, rot, int((gw - 4) / 8)))}</text>')
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


def _controle(sim, v, w, h, cores):
    """Gráfico de controle (C4 Karura): o indicador mês a mês, o centro tracejado, os limites em vermelho e os
    pontos com sinal em destaque (vermelho fora do limite, âmbar nas sequências)."""
    g = sim.grafico_de_controle(v['controle'])
    fmt = v['valores'][0]['formato']
    top, base, esq, dir_ = 40, h - 30, 44, w - 12
    todos = g['valores'] + g['superior'] + g['inferior'] + [g['centro']]
    lo, hi = min(todos), max(todos)
    folga = (hi - lo) * 0.1 or 1
    lo, hi = lo - folga, hi + folga
    n = len(g['rotulos'])

    def px(i):
        return esq + (dir_ - esq) * (i + 0.5) / n

    def py(y):
        return base - (base - top) * (y - lo) / (hi - lo)

    def linha(ys, estilo):
        pts = ' '.join(f'{px(i):.1f},{py(y):.1f}' for i, y in enumerate(ys))
        return f'<polyline points="{pts}" fill="none" {estilo}/>'

    out = [_titulo(v, w),
           linha(g['superior'], 'stroke="#D13438" stroke-width="1.5" stroke-dasharray="2 3"'),
           linha(g['inferior'], 'stroke="#D13438" stroke-width="1.5" stroke-dasharray="2 3"'),
           linha([g['centro']] * n, 'stroke="#8A8886" stroke-width="1.5" stroke-dasharray="6 4"'),
           linha(g['valores'], f'stroke="{cores[0]}" stroke-width="2.5"')]
    for i, (y, sinal) in enumerate(zip(g['valores'], g['sinais'])):
        cor = '#D13438' if sinal == 1 else '#C19C00' if sinal else cores[0]
        out.append(f'<circle cx="{px(i):.1f}" cy="{py(y):.1f}" r="{6 if sinal else 3.5}" fill="{cor}" stroke="#fff" '
                   f'stroke-width="1.5"><title>{_e(g["rotulos"][i])}: {_e(formatar(y, fmt))}</title></circle>')
        out.append(f'<text x="{px(i):.1f}" y="{base + 16}" class="eixo" text-anchor="middle">'
                   f'{_e(_corta(_curto(g["rotulos"][i], int((dir_ - esq) / n / 8)), max(3, int((dir_ - esq) / n / 8))))}</text>')
    out.append(f'<text x="{esq:.1f}" y="{py(max(g["superior"])) - 6:.1f}" class="eixo" style="fill:#D13438">'
               f'limites da variação normal</text>'
               f'<text x="{esq:.1f}" y="{base - 4:.1f}" class="eixo">média {_e(formatar(g["centro"], fmt, True))}'
               f'{" · " + str(sum(1 for x in g["sinais"] if x)) + " sinal(is)" if any(g["sinais"]) else " · sem sinal"}</text>')
    return ''.join(out)


def _cor_fora(sim, v):
    """{rótulo: cor} quando a cor das barras vem do fora da curva (C4 Karura); None para outra cor."""
    cor = medida(sim.m, v.get('cor') or '') if v.get('cor') else None
    dono = medida(sim.m, (cor or {}).get('extra', {}).get('de') or '') if cor else None
    if not dono or dono.get('tipo') != 'fora_da_curva':
        return None
    limiar = dono['extra']['limiar']
    out = {}
    for r in categorias(sim.m, v['categoria']):
        z = sim.valor(dono['nome'], [(v['categoria'], r)])
        out[r] = '#D13438' if z is not None and abs(z) > limiar else sim.m['tema']['cores'][0]
    return out


def _barras(sim, v, w, h, cores):
    fora = _cor_fora(sim, v)
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
            if fora:                                  # fora da curva: vermelho só para quem passou do limiar
                cor = fora.get(r, cor)
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
