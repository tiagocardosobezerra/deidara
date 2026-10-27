"""
Esculpir: o protótipo navegável do painel, num único .html sem dependência
externa (abre offline, em qualquer navegador, e pode ser enviado por e-mail
para validação).

Os números são FICTÍCIOS, determinísticos e coerentes entre si (ver
simulacao.py): o protótipo valida layout, indicadores e navegação, nunca
valor. Nenhuma linha do banco é lida — regra "só estrutura, nunca dados" do
Vegapunk.
"""

import html
import math

from .especificacao import COR_BOA, COR_RUIM, medida
from .layout import LARGURA, altura_da_pagina, posicionar
from .simulacao import Simulador, categorias
from .util import numero_br


def formatar(v, formato, compacto=False):
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


def _corta(s, n):
    s = str(s)
    return s if len(s) <= n else s[:max(1, n - 1)] + '…'


def svg_visual(sim, v, pos, cores):
    w, h = pos['w'], pos['h']
    corpo = {'cartao': _cartao, 'medidor': _medidor, 'segmentador': _segmentador, 'tabela': _tabela,
             'matriz': _matriz, 'rosca': _rosca, 'linha': _linha, 'barras': _barras, 'colunas': _colunas}[v['tipo']]
    return (f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{_e(v["titulo"])}">'
            f'{corpo(sim, v, w, h, cores)}</svg>')


def _cor_status(sim, nome, filtros=()):
    st = sim.status(nome, filtros)
    return '' if st is None else f' style="fill:{COR_BOA if st else COR_RUIM}"'


def titulo_do_cartao(m, v):
    """O mesmo texto vai para o título do cartão no Power BI."""
    if not v.get('meta'):
        return None
    md = medida(m, v['meta']['nome'])
    if md and md['tipo'] == 'meta':
        return f'Meta: {formatar(float(md["dax"]), md["formato"], True)}'
    return f'Meta: {v["meta"]["nome"]}'


def _cartao(sim, v, w, h, cores):
    md = v['valores'][0]
    val = sim.valor(md['nome'])
    meta = titulo_do_cartao(sim.m, v)
    topo = f'<text x="12" y="20" class="sub">{_e(meta)}</text>' if meta else ''
    return (topo + f'<text x="{w / 2}" y="{h / 2 + 8}" class="kpi" text-anchor="middle"{_cor_status(sim, md["nome"])}>'
            f'{_e(formatar(val, md["formato"], True))}</text>'
            f'<text x="{w / 2}" y="{h / 2 + 32}" class="sub" text-anchor="middle">{_e(_corta(v["titulo"], int(w / 6.5)))}</text>')


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


def _segmentador(sim, v, w, h, cores):
    return (f'<text x="12" y="20" class="sub">{_e(_corta(v["titulo"], int(w / 6.5)))}</text>'
            f'<rect x="12" y="28" width="{w - 24}" height="22" rx="3" class="caixa"/>'
            f'<text x="20" y="43" class="cel">Tudo</text><text x="{w - 26}" y="43" class="cel">▾</text>')


def _tabela(sim, v, w, h, cores):
    cols = v['campos']
    chaves = [c for c in cols if c['tipo'] == 'coluna']
    linhas = [[(chaves[0], r)] for r in categorias(sim.m, chaves[0])] if chaves else [[]]
    n = max(1, min(len(linhas), int((h - 84) // 22)))
    cw = (w - 24) / len(cols)
    out = [_titulo(v, w)]

    def x_de(k, c):
        return 12 + k * cw + (cw - 6 if c['tipo'] == 'medida' else 0)

    for k, c in enumerate(cols):
        anc = 'end' if c['tipo'] == 'medida' else 'start'
        out.append(f'<text x="{x_de(k, c):.1f}" y="48" class="cab" text-anchor="{anc}">{_e(_corta(c["nome"], int(cw / 7)))}</text>')
    out.append(f'<line x1="12" x2="{w - 12}" y1="54" y2="54" class="grade"/>')
    for i in range(n):
        y = 72 + i * 22
        if i % 2:
            out.append(f'<rect x="12" y="{y - 15}" width="{w - 24}" height="22" class="zebra"/>')
        for k, c in enumerate(cols):
            cor = ''
            if c['tipo'] == 'medida':
                txt = formatar(sim.valor(c['nome'], linhas[i]), c['formato'])
                cor = _cor_status(sim, c['nome'], linhas[i])
            elif linhas[i] and linhas[i][0][0] is c:
                txt = linhas[i][0][1]
            else:
                rot = categorias(sim.m, c)
                txt = rot[i % len(rot)]
            anc = 'end' if c['tipo'] == 'medida' else 'start'
            out.append(f'<text x="{x_de(k, c):.1f}" y="{y}" class="cel" text-anchor="{anc}"{cor}>{_e(_corta(txt, int(cw / 6.5)))}</text>')
    y = 72 + n * 22
    out.append(f'<line x1="12" x2="{w - 12}" y1="{y - 14}" y2="{y - 14}" class="grade"/>')
    for k, c in enumerate(cols):
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
    for k, hd in enumerate(heads + (['Total'] if colunas else [])):
        out.append(f'<text x="{12 + (k + 3.5) * cw - 6:.1f}" y="48" class="cab" text-anchor="end">{_e(_corta(hd, int(cw / 7)))}</text>')
    out.append(f'<line x1="12" x2="{w - 12}" y1="54" y2="54" class="grade"/>')
    for i in range(n):
        y = 72 + i * 22
        out.append(f'<text x="12" y="{y}" class="cel">{_e(_corta(linhas[i], int(2.2 * cw / 7)))}</text>')
        for k, hd in enumerate(heads):
            if colunas:
                filtros, nome = [(linha_c, linhas[i]), (col_c, hd)], md['nome']
                fmt = md['formato']
            else:
                filtros, nome = [(linha_c, linhas[i])], hd
                fmt = v['valores'][k]['formato']
            val = sim.valor(nome, filtros)
            out.append(f'<text x="{12 + (k + 3.5) * cw - 6:.1f}" y="{y}" class="cel" text-anchor="end"'
                       f'{_cor_status(sim, nome, filtros)}>{_e(formatar(val, fmt, True))}</text>')
        if colunas:
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


def _escala(series):
    return max([max(s) for _, s, _ in series] + [1e-9]) * 1.12


def _colunas(sim, v, w, h, cores):
    rot, ss = _series(sim, v)
    top, base, esq = (48 if len(ss) > 1 else 34), h - 30, 12
    mx = _escala(ss)
    gw = (w - 2 * esq) / len(rot)
    bw = gw * 0.7 / len(ss)
    out = [_titulo(v, w), _legenda(ss, cores, w, 42)]
    out.append(f'<line x1="{esq}" x2="{w - esq}" y1="{base}" y2="{base}" class="grade"/>')
    for i, r in enumerate(rot):
        for k, (_, s, fmt) in enumerate(ss):
            bh = max(0, (base - top - 14) * s[i] / mx)
            x = esq + i * gw + gw * 0.15 + k * bw
            out.append(f'<rect x="{x:.1f}" y="{base - bh:.1f}" width="{max(1, bw - 1):.1f}" height="{bh:.1f}" fill="{cores[k % len(cores)]}">'
                       f'<title>{_e(r)}: {_e(formatar(s[i], fmt))}</title></rect>')
        out.append(f'<text x="{esq + i * gw + gw / 2:.1f}" y="{base + 16}" class="eixo" text-anchor="middle">{_e(_corta(r, max(3, int(gw / 6))))}</text>')
    if len(ss) == 1 and gw > 44:
        s, fmt = ss[0][1], ss[0][2]
        for i in range(len(rot)):
            bh = max(0, (base - top - 14) * s[i] / mx)
            out.append(f'<text x="{esq + i * gw + gw / 2:.1f}" y="{base - bh - 4:.1f}" class="eixo" text-anchor="middle">'
                       f'{_e(formatar(s[i], fmt, True))}</text>')
    return ''.join(out)


def _barras(sim, v, w, h, cores):
    rot, ss = _series(sim, v)
    ordem = sorted(range(len(rot)), key=lambda i: -ss[0][1][i])    # maior primeiro, como no Power BI
    rot = [rot[i] for i in ordem]
    ss = [(n, [s[i] for i in ordem], f) for n, s, f in ss]
    top, esq = (52 if len(ss) > 1 else 36), min(150, w * 0.32)
    mx = _escala(ss)
    gh = (h - top - 10) / len(rot)
    bh = gh * 0.7 / len(ss)
    out = [_titulo(v, w), _legenda(ss, cores, w, 42)]
    for i, r in enumerate(rot):
        out.append(f'<text x="{esq - 8}" y="{top + i * gh + gh / 2 + 4:.1f}" class="eixo" text-anchor="end">{_e(_corta(r, int(esq / 6.5)))}</text>')
        for k, (_, s, fmt) in enumerate(ss):
            bw = max(0, (w - esq - 70) * s[i] / mx)
            y = top + i * gh + gh * 0.15 + k * bh
            out.append(f'<rect x="{esq}" y="{y:.1f}" width="{bw:.1f}" height="{max(1, bh - 1):.1f}" fill="{cores[k % len(cores)]}">'
                       f'<title>{_e(r)}: {_e(formatar(s[i], fmt))}</title></rect>')
            if len(ss) == 1:
                out.append(f'<text x="{esq + bw + 6:.1f}" y="{y + bh / 2 + 4:.1f}" class="eixo">{_e(formatar(s[i], fmt, True))}</text>')
    return ''.join(out)


def _linha(sim, v, w, h, cores):
    rot, ss = _series(sim, v)
    top, base, esq = (52 if len(ss) > 1 else 36), h - 30, 34
    mx = _escala(ss)
    gw = (w - 2 * esq) / max(1, len(rot) - 1)
    out = [_titulo(v, w), _legenda(ss, cores, w, 42)]
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
        out.append(f'<path d="{d}" class="rel{"" if r["ativo"] else " inativa"}">'
                   f'<title>{_e(r["de"])}[{_e(r["de_coluna"])}] muitos → um {_e(r["para"])}[{_e(r["para_coluna"])}] · prova: {_e(r["prova"])}</title></path>'
                   f'<text x="{a[0] + (6 if para_dir else -6)}" y="{a[1] - 5}" class="card" text-anchor="{"start" if para_dir else "end"}">*</text>'
                   f'<text x="{b[0] + (6 if x1 == x2 else (-6 if para_dir else 6))}" y="{b[1] - 5}" class="card" '
                   f'text-anchor="{"start" if x1 == x2 else ("end" if para_dir else "start")}">1</text>')
    for t in m['tabelas']:
        x, y, h = pos[t['nome']]
        cls = 'fato' if t['tipo'] == 'fato' else 'dim'
        out.append(f'<g><rect x="{x}" y="{y}" width="{bw}" height="{h}" rx="6" class="cx {cls}"/>'
                   f'<text x="{x + 10}" y="{y + 20}" class="t">{_e(_corta(t["nome"], 26))}</text>'
                   f'<text x="{x + 10}" y="{y + 36}" class="sub">{_e(_corta(t["origem"] or "gerada no Power Query", 30))}</text>'
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
.vis.segmentador{border-color:transparent;background:transparent}
.vis svg{display:block;font-family:"Segoe UI",system-ui,sans-serif}
.t{font-size:14px;font-weight:600;fill:#252423}.sub{font-size:12px;fill:#605E5C}.kpi{font-size:34px;font-weight:600;fill:#252423}
.kpi2{font-size:22px;font-weight:600;fill:#252423}.eixo{font-size:11px;fill:#605E5C}.cab{font-size:12px;font-weight:600;fill:#252423}
.cel{font-size:12px;fill:#252423}.grade{stroke:#E1DFDD}.zebra{fill:#F8F8F8}.trilho{fill:none;stroke:#E1DFDD}
.caixa{fill:#fff;stroke:#8A8886}.nota{color:var(--suave);font-size:13px;margin:8px 0 0}
.modelo{width:100%;height:auto;background:var(--pagina);border-radius:6px}.cx{stroke-width:1.5}
.cx.fato{fill:#EAF3FF;stroke:#118DFF}.cx.dim{fill:#fff;stroke:#8A8886}.rel{stroke:#605E5C;stroke-width:1.5}
.rel{fill:none}.rel.inativa{stroke-dasharray:6 4}.card{font-size:13px;font-weight:600;fill:#605E5C}
table .sub{color:#605E5C}
table{border-collapse:collapse;width:100%;font-size:13px;background:var(--pagina);color:#252423}th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--borda);vertical-align:top}
th{position:sticky;top:0;background:#F3F2F1}code,pre{font-family:Consolas,monospace;font-size:12px}pre{margin:0;white-space:pre-wrap}
.tabela-rolagem{overflow-x:auto}ul.lista{padding-left:20px;line-height:1.6}.ok{color:#107C10}.erro{color:var(--erro)}
@media (max-width:700px){header,main{padding-left:16px;padding-right:16px}nav{padding:0 8px}}
"""

JS = """
const botoes=[...document.querySelectorAll('nav button')];
function abrir(id){botoes.forEach(b=>b.setAttribute('aria-selected',b.dataset.alvo===id));
document.querySelectorAll('section').forEach(s=>s.classList.toggle('ativa',s.id===id));escalar();
try{history.replaceState(null,'','#'+id)}catch(e){}}
botoes.forEach(b=>b.addEventListener('click',()=>abrir(b.dataset.alvo)));
function escalar(){document.querySelectorAll('section.ativa .palco').forEach(p=>{const pg=p.firstElementChild;
const k=Math.min(1,p.clientWidth/pg.offsetWidth);pg.style.transform='scale('+k+')';p.style.height=(pg.offsetHeight*k)+'px';});}
addEventListener('resize',escalar);
const h=location.hash.slice(1);abrir(botoes.some(b=>b.dataset.alvo===h)?h:botoes[0].dataset.alvo);
"""


def gerar_html(m, problemas, versao):
    cores = m['tema']['cores']
    sim = Simulador(m)
    abas, secoes = [], []
    for i, pg in enumerate(m['paginas']):
        sid = f'p{i + 1}'
        abas.append((sid, pg['nome']))
        posicoes = posicionar(pg['visuais'])
        alt = altura_da_pagina(posicoes)
        vis = ''.join(
            f'<div class="vis {v["tipo"]}" style="left:{p["x"]}px;top:{p["y"]}px;width:{p["w"]}px;height:{p["h"]}px">'
            f'{svg_visual(sim, v, p, cores)}</div>' for v, p in posicoes)
        desc = f'<p class="nota">{_e(pg["descricao"])}</p>' if pg['descricao'] else ''
        secoes.append(f'<section id="{sid}"><div class="palco"><div class="pagina" style="width:{LARGURA}px;height:{alt}px">'
                      f'<h2>{_e(pg["nome"])}</h2>{vis}</div></div>{desc}</section>')
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
    abas.append(('pendencias', f'Pendências ({len(problemas.avisos)})'))
    av = ''.join(f'<li>{_e(a)}</li>' for a in problemas.avisos) or '<li class="ok">Nenhuma pendência.</li>'
    secoes.append(f'<section id="pendencias"><p>Itens para decidir antes de aprovar:</p><ul class="lista">{av}</ul></section>')
    nav = ''.join(f'<button type="button" role="tab" data-alvo="{sid}">{_e(n)}</button>' for sid, n in abas)
    meta = ' · '.join(x for x in [m['publico'] and f'Público: {m["publico"]}',
                                  m['responsavel'] and f'Responsável: {m["responsavel"]}', f'versão {versao}'] if x)
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(m['projeto'])} · protótipo</title><style>{CSS}</style></head>
<body><header><h1>{_e(m['projeto'])}</h1><span class="meta">{_e(meta)}</span></header>
<div class="faixa">Protótipo gerado pelo Deidara. Os números são fictícios: valide layout, indicadores e navegação, não valores.</div>
<nav role="tablist">{nav}</nav><main>{''.join(secoes)}</main>
<script>{JS}</script></body></html>
"""
