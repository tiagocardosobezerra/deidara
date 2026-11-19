#!/usr/bin/env python3
"""
Gera os SVGs animados do README (pt-BR e inglês) em assets/readme/.

    python ferramentas/gerar_svgs_readme.py
    python ferramentas/gerar_svgs_readme.py --capturas-de PASTA_PNG   # refaz as capturas antes

O GitHub mostra o SVG dentro de <img>: nada de script nem de recurso externo.
Por isso tudo vai embutido (fontes em subconjunto WOFF, capturas em WebP) e a
animação é só CSS, num laço único por arquivo. Cada classe animada lê
--d (atraso) e --ps (play-state), para congelar um quadro ao revisar, e com
prefers-reduced-motion a animação para no quadro de descanso, que já é
completo (é também o estado sem animação).

Fontes de entrada (no repositório):
  assets/readme/fontes/*.woff     Inter, Poppins e JetBrains Mono (OFL, só latim)
  assets/readme/capturas/*.webp   uma captura por modelo de layout (960 px)
  tecnicas/arte/modelos.py        nomes e descrições dos modelos (pt-BR)

--capturas-de: pasta com as capturas do protótipo em PNG 1440 x 900 (uma por
modelo, <modelo>.png). O gerador recorta a página, reduz para 960 px e grava
o WebP em assets/readme/capturas/.

Depende só de fontTools e Pillow.
"""

import argparse
import ast
import base64
import io
import math
import os
import sys
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont
from PIL import Image

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, 'assets', 'readme')
FONTES = os.path.join(SAIDA, 'fontes')
CAPTURAS = os.path.join(SAIDA, 'capturas')

C = dict(bg='#0B1220', p1='#111A2E', p2='#1E293B', p3='#1E2A44', l1='#334155', l2='#475569',
         t0='#F1F5F9', t1='#E2E8F0', t2='#CBD5E1', t3='#94A3B8', t4='#64748B',
         amb='#F59E0B', amb2='#FCD34D', lar='#FB923C', red='#F87171', ok='#34D399', blue='#60A5FA')

FAM = {  # classe -> (arquivo, família css, peso)
    'I4': ('inter-400.woff', 'DI4', 400), 'I6': ('inter-600.woff', 'DI6', 600), 'I8': ('inter-800.woff', 'DI8', 800),
    'P6': ('poppins-600.woff', 'DP6', 600), 'P8': ('poppins-800.woff', 'DP8', 800),
    'M4': ('jetbrainsmono-400.woff', 'DM4', 400), 'M7': ('jetbrainsmono-700.woff', 'DM7', 700)}
_TT = {}


def tt(fam):
    if fam not in _TT:
        _TT[fam] = TTFont(os.path.join(FONTES, FAM[fam][0]))
    return _TT[fam]


def width(txt, fam, size, ls=0.0):
    f = tt(fam)
    cmap, hm, upm = f.getBestCmap(), f['hmtx'], f['head'].unitsPerEm
    w = sum(hm[cmap.get(ord(ch)) or cmap[ord('?')]][0] for ch in txt)
    return w * size / upm + ls * len(txt)


def wrap(txt, fam, size, maxw):
    out, cur = [], ''
    for word in txt.split(' '):
        t = (cur + ' ' + word).strip()
        if width(t, fam, size) <= maxw or not cur:
            cur = t
        else:
            out.append(cur)
            cur = word
    if cur:
        out.append(cur)
    return out


def modelos_pt():
    """Lê o dicionário MODELOS de tecnicas/arte/modelos.py sem importar o pacote."""
    src = open(os.path.join(RAIZ, 'tecnicas', 'arte', 'modelos.py'), encoding='utf-8').read()
    for no in ast.parse(src).body:
        if isinstance(no, ast.Assign) and getattr(no.targets[0], 'id', '') == 'MODELOS':
            d = ast.literal_eval(no.value)
            return [(k, v) for k, v in d.items() if k != 'padrao']
    raise SystemExit('MODELOS não encontrado em tecnicas/arte/modelos.py')


MODELOS_EN = {
    'faixa-de-kpis': 'Icon rail, title with filters in the corner, KPI row, charts beside the table',
    'coluna-de-kpis': 'Filter bar, KPI column on the left, chart grid and tabs at the bottom',
    'secoes-com-rolagem': 'Sidebar with KPIs and filters; summary and scrolling sections',
    'trilho-escuro': 'Dark page rail, a single KPI strip, two panels and a wide table',
    'kpis-clicaveis': 'Side menu and clickable KPIs: the chosen KPI changes the chart and the table',
    'historia-longa': 'One long dark page, read like a story, section by section',
    'executivo': 'A row of up to five KPIs and one full-width main chart, the rest below',
    'mapa-central': 'The map (or the main chart) in the center, KPIs on the left, sparklines on the right, tables below',
    'causa-raiz': 'Filter column, KPI row and the decomposition tree up front, with the detail below',
    'tabela-lateral': 'KPI strip, charts on the left and a tall table on the right',
    'equipes': 'Side panel with KPIs, filters and pages; sparklines on top and one large main chart',
}


# ---------------------------------------------------------------- capturas
def refazer_capturas(pasta):
    os.makedirs(CAPTURAS, exist_ok=True)
    for nome, _ in modelos_pt():
        im = Image.open(os.path.join(pasta, nome + '.png')).convert('RGB')
        g = im.convert('L')
        w, h = g.size
        px = g.load()
        # a página branca começa na primeira linha com mais da metade dos pixels claros
        topo = next(y for y in range(h) if sum(px[x, y] > 235 for x in range(0, w, 4)) > w / 8)
        corte = im.crop((20, topo + 1, w - 20, min(h, topo + 1 + 700)))
        corte = corte.resize((960, round(960 * corte.height / corte.width)), Image.LANCZOS)
        corte.save(os.path.join(CAPTURAS, nome + '.webp'), 'WEBP', quality=74, method=6)
        print('captura', nome, corte.size)


def captura_b64(nome, largura=None, q=74):
    im = Image.open(os.path.join(CAPTURAS, nome + '.webp')).convert('RGB')
    if largura and largura < im.width:
        im = im.resize((largura, round(largura * im.height / im.width)), Image.LANCZOS)
    b = io.BytesIO()
    im.save(b, 'WEBP', quality=q, method=6)
    return base64.b64encode(b.getvalue()).decode(), im.size


# ---------------------------------------------------------------- SVG
class SVG:
    def __init__(self, w, h, T, label, linha_do_tempo):
        self.w, self.h, self.T, self.label, self.ldt = w, h, T, label, linha_do_tempo
        self.body, self.defs, self.css = [], [], []
        self.used = {k: set() for k in FAM}
        self.n = 0

    def id(self, p):
        self.n += 1
        return f'{p}{self.n}'

    def add(self, s):
        self.body.append(s)

    def text(self, x, y, txt, fam='I4', size=16, fill=None, anchor='start', ls=0, extra=''):
        self.used[fam].update(txt)
        a = f' text-anchor="{anchor}"' if anchor != 'start' else ''
        lsp = f' letter-spacing="{ls}"' if ls else ''
        return (f'<text x="{x:.1f}" y="{y:.1f}" class="{fam}" font-size="{size}" fill="{fill or C["t1"]}"{a}{lsp}{extra}>'
                f'{escape(txt)}</text>')

    def comment(self, txt):
        self.css.append(f'/* {txt} */')

    # -- animação: keyframes em segundos dentro do laço T
    def kf(self, frames, ease='cubic-bezier(.2,.8,.2,1)', origin=None):
        name = self.id('k')
        pts = ''.join(f'{max(0, min(100, t / self.T * 100)):.3f}%{{{css}}}' for t, css in frames)
        self.css.append(f'@keyframes {name}{{{pts}}}')
        cls = self.id('a')
        extra = f'transform-box:fill-box;transform-origin:{origin};' if origin else ''
        self.css.append(f'.{cls}{{animation:{name} {self.T}s {ease} infinite both;'
                        f'animation-delay:var(--d,0s);animation-play-state:var(--ps,running);{extra}}}')
        return cls

    def janela(self, segs, fi=.45, fo=.35, dy=14, sc=None, out_dy=-8, ease='cubic-bezier(.2,.8,.2,1)', origin='center', base_visivel=None):
        """Visível nos intervalos segs [(entra, sai)]; entra=0 / sai=T = visível na emenda do laço.
        Devolve (classe, atributo base). O atributo base é o quadro de descanso (sem animação)."""
        T = self.T
        tr = lambda y, s=None: f'transform:translate(0px,{y}px)' + (f' scale({s})' if s else (' scale(1)' if sc else ''))
        vis = 'opacity:1;' + tr(0, 1 if sc else None)
        hin = 'opacity:0;' + tr(dy, sc)
        hout = 'opacity:0;' + tr(out_dy, 1 if sc else None)
        v0 = any(a <= 0 for a, _ in segs)
        fr = [(0, vis if v0 else hin)]
        for a, b in segs:
            if a > 0:
                fr += [(a, hin), (a + fi, vis)]
            if b < T:
                fr += [(b, vis), (b + fo, hout), (b + fo + .01, hin)]
        vT = any(b >= T for _, b in segs)
        fr.append((T, vis if vT else hin))
        cls = self.kf(fr, ease, origin if sc else None)
        vis_base = v0 if base_visivel is None else base_visivel
        return cls, ('' if vis_base else ' opacity="0"')

    def render(self, nome):
        faces = []
        for fam, chars in self.used.items():
            if not chars:
                continue
            o = subset.Options()
            o.flavor = 'woff'
            o.layout_features = ['kern']
            o.name_IDs = []
            o.notdef_outline = True
            o.hinting = False
            f = TTFont(os.path.join(FONTES, FAM[fam][0]))
            s = subset.Subsetter(o)
            s.populate(text=''.join(sorted(chars)) + ' ')
            s.subset(f)
            b = io.BytesIO()
            f.flavor = 'woff'
            f.save(b)
            faces.append(f"@font-face{{font-family:'{FAM[fam][1]}';src:url(data:font/woff;base64,"
                         f"{base64.b64encode(b.getvalue()).decode()}) format('woff')}}")
        cls = ''.join(f".{k}{{font-family:'{v[1]}',sans-serif;font-variant-ligatures:none;font-feature-settings:'liga' 0,'calt' 0;" + ('white-space:pre;' if k[0] == 'M' else '') + "}"
                      for k, v in FAM.items())
        css = ('\n'.join(faces) + '\n' + f'/* Linha do tempo: {self.ldt} */\n' + cls + '\n' + '\n'.join(self.css)
               + '\n@media (prefers-reduced-motion:reduce){*{animation:none!important}}')
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" '
               f'role="img" aria-label="{escape(self.label)}"><title>{escape(self.label)}</title>'
               f'<style><![CDATA[\n{css}\n]]></style><defs>{"".join(self.defs)}</defs>'
               + fundo(self) + ''.join(self.body) + '</svg>')
        p = os.path.join(SAIDA, nome + '.svg')
        open(p, 'w', encoding='utf-8', newline='\n').write(svg)
        kb = len(svg.encode('utf-8')) / 1024
        print(f'{nome}.svg  {kb:.0f} KB')
        if kb >= 900:
            raise SystemExit(f'{nome}.svg passou de 900 KB')


def fundo(s):
    s.defs.append(f'<pattern id="grade" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="{C["p3"]}" stroke-width="1"/></pattern>'
                  f'<radialGradient id="brilho" cx=".78" cy=".42" r=".6"><stop offset="0" stop-color="{C["amb"]}" stop-opacity=".13"/><stop offset="1" stop-color="{C["amb"]}" stop-opacity="0"/></radialGradient>'
                  f'<clipPath id="moldura"><rect width="{s.w}" height="{s.h}" rx="16"/></clipPath>')
    return (f'<rect width="{s.w}" height="{s.h}" rx="16" fill="{C["bg"]}"/>'
            f'<g clip-path="url(#moldura)"><rect width="{s.w}" height="{s.h}" fill="url(#grade)" opacity=".45"/>'
            f'<rect width="{s.w}" height="{s.h}" fill="url(#brilho)"/></g>'
            f'<rect x=".5" y=".5" width="{s.w-1}" height="{s.h-1}" rx="15.5" fill="none" stroke="{C["p3"]}"/>')


def card(x, y, w, h, fill=None, stroke=None, rx=14, extra=''):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill or C["p1"]}" stroke="{stroke or C["p3"]}"{extra}/>'


def estrela(cx, cy, r1, r2, pontas=8, rot=-90):
    pts = []
    for i in range(pontas * 2):
        r = r1 if i % 2 == 0 else r2
        a = math.radians(rot + i * 180 / pontas)
        pts.append(f'{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}')
    return ' '.join(pts)


def marca(s, x, y, tam=30):
    """Estrela de oito pontas + DEIDARA, como no banner."""
    s.defs.append(f'<linearGradient id="gx" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{C["amb2"]}"/><stop offset=".55" stop-color="{C["amb"]}"/><stop offset="1" stop-color="{C["lar"]}"/></linearGradient>')
    r = tam * .62
    return (f'<polygon points="{estrela(x + r, y - tam * .36, r, r * .46)}" fill="url(#gx)"/>'
            f'<circle cx="{x + r:.1f}" cy="{y - tam * .36:.1f}" r="{r * .22:.1f}" fill="{C["bg"]}"/>'
            + s.text(x + 2 * r + 12, y, 'Deidara', 'P8', tam, C['t0'], ls=.2))


def janela_nav(s, x, y, w, h, titulo, barra=34):
    return (card(x, y, w, h, '#0E1628', C['l1'], 12)
            + f'<path d="M{x+1} {y+barra}h{w-2}" stroke="{C["l1"]}"/>'
            + ''.join(f'<circle cx="{x + 18 + i * 15}" cy="{y + barra / 2}" r="4.5" fill="{c}"/>' for i, c in enumerate([C['red'], C['amb'], C['ok']]))
            + s.text(x + 72, y + barra / 2 + 4.5, titulo, 'M4', 12.5, C['t3']))


# ================================================================= 1. hero
TX = {
    'pt': dict(
        label='Deidara: primeiro a escultura, depois a explosão. Do pedido em português ao projeto Power BI completo, com protótipo aprovado pelo gestor.',
        selo='Skill do Claude Code · Power BI', t1='Primeiro a escultura.', t2a='Depois, ', t2b='a explosão.',
        sub='Descreva o painel em português. O gestor aprova o protótipo e, depois do “sim”, sai o projeto Power BI completo.',
        fichas=[('0', 'linhas de dado'), ('289', 'testes'), ('11', 'modelos de layout')],
        voce='você', pedido='Quero os desligamentos por motivo e cargo, com a meta de turnover por empresa.',
        aprovado='Aprovado', ficticio='números fictícios',
        passos=['pedido', 'protótipo', '“sim”', 'projeto'],
        arq_sub={'TMDL': 'modelo semântico', 'PBIR': 'relatório', 'views SQL': 'sql/erp/', 'HOMOLOGACAO.md': 'roteiro do teste'},
    ),
    'en': dict(
        label='Deidara: first the sculpture, then the explosion. From a plain-words request to the full Power BI project, with a prototype the manager approves.',
        selo='Claude Code skill · Power BI', t1='First the sculpture.', t2a='Then, ', t2b='the explosion.',
        sub='Describe the dashboard in plain words. The manager approves the prototype and, after the “yes”, the full Power BI project comes out.',
        fichas=[('0', 'data rows'), ('289', 'tests'), ('11', 'layout templates')],
        voce='you', pedido='I want terminations by reason and role, with the turnover target by company.',
        aprovado='Approved', ficticio='fictional numbers',
        passos=['request', 'prototype', '“yes”', 'project'],
        arq_sub={'TMDL': 'semantic model', 'PBIR': 'report', 'views SQL': 'sql/erp/', 'HOMOLOGACAO.md': 'test script'},
    ),
}


def hero(lang):
    X = TX[lang]
    W, H, T = 1280, 640, 15.0
    s = SVG(W, H, T, X['label'],
            '15 s. Descanso 0–2,6 (protótipo aprovado + arquivos) · Cena 1 pedido 3,0–5,9 · Cena 2 protótipo 6,0–9,0 '
            '(selo 7,4) · Cena 3 Katsu! 9,0–10,6 · Cena 4 arquivos 10,4–12,0 · descanso até 15 (emenda no começo)')
    # ---------------- coluna da esquerda (fixa: é o quadro de descanso)
    L = 64
    s.add(marca(s, L, 92, 30))
    pw = width(X['selo'], 'I6', 13.5) + 28
    px0 = L + 2 * 30 * .62 + 12 + width('Deidara', 'P8', 30, .2) + 16
    s.add(card(px0, 70, pw, 28, C['p1'], C['l1'], 14) + s.text(px0 + 14, 89, X['selo'], 'I6', 13.5, C['t2']))
    # título: tamanho que cabe na coluna
    colw = 560
    tam = 54
    while max(width(X['t1'], 'P8', tam), width(X['t2a'] + X['t2b'], 'P8', tam)) > colw:
        tam -= 1
    y1 = 214
    s.add(s.text(L, y1, X['t1'], 'P8', tam, C['t0']))
    s.add(s.text(L, y1 + tam * 1.18, X['t2a'], 'P8', tam, C['t0'])
          + s.text(L + width(X['t2a'], 'P8', tam), y1 + tam * 1.18, X['t2b'], 'P8', tam, 'url(#gx)'))
    ys = y1 + tam * 1.18 + 58
    for i, ln in enumerate(wrap(X['sub'], 'I4', 19.5, 520)):
        s.add(s.text(L, ys + i * 31, ln, 'I4', 19.5, C['t2']))
    # fichas
    fy, fw, fg = 492, 176, 16
    for i, (num, lab) in enumerate(X['fichas']):
        fx = L + i * (fw + fg)
        s.add(card(fx, fy, fw, 76, C['p1'], C['l1'], 12)
              + s.text(fx + 18, fy + 42, num, 'P8', 30, C['amb'])
              + s.text(fx + 18, fy + 63, lab, 'I6', 13.5, C['t3']))

    # ---------------- palco da direita
    SX, SY, SW = 676, 52, 556
    cxm = SX + SW / 2
    # trilho de passos embaixo do palco
    passos_t = [(3.0, 6.0), (6.0, 7.4), (7.4, 9.0), (9.0, T)]
    py = 612
    sw_ = SW / 4
    for i, nome in enumerate(X['passos']):
        x0 = SX + i * sw_
        s.add(f'<rect x="{x0 + 4:.1f}" y="{py - 22}" width="{sw_ - 8:.1f}" height="3" rx="1.5" fill="{C["l1"]}"/>'
              + s.text(x0 + 4, py, f'{i + 1} · {nome}', 'I6', 13, C['t4']))
        segs = [passos_t[i]] + ([(0, 2.6)] if i == 3 else [])
        cl, b = s.janela(segs, fi=.3, fo=.3, dy=0, out_dy=0)
        s.add(f'<g class="{cl}"{b}><rect x="{x0 + 4:.1f}" y="{py - 22}" width="{sw_ - 8:.1f}" height="3" rx="1.5" fill="{C["amb"]}"/>'
              + s.text(x0 + 4, py, f'{i + 1} · {nome}', 'I6', 13, C['amb2']) + '</g>')

    # cena 1: o pedido e o argila.json
    s.comment('Cena 1 · pedido (3,0–5,9 s): o balão do pedido e o argila.json que o esbocar escreve')
    bub_w = SW
    linhas = wrap(X['pedido'], 'I6', 17.5, bub_w - 48)
    bub_h = 50 + len(linhas) * 26
    cl, b = s.janela([(3.0, 5.6)], dy=12)
    bub = (card(SX, SY + 8, bub_w, bub_h, '#1B2540', C['l1'], 16)
           + s.text(SX + 24, SY + 36, X['voce'].upper(), 'I8', 11.5, C['t3'], ls=1.4)
           + ''.join(s.text(SX + 24, SY + 64 + i * 26, ln, 'I6', 17.5, C['t0']) for i, ln in enumerate(linhas)))
    s.add(f'<g class="{cl}"{b}>{bub}</g>')
    jy = SY + 8 + bub_h + 22
    jh = 560 - jy
    cl, b = s.janela([(3.5, 5.6)], dy=16)
    s.add(f'<g class="{cl}"{b}>' + card(SX, jy, SW, jh, '#0E1628', C['l1'], 14)
          + f'<path d="M{SX+1} {jy+38}h{SW-2}" stroke="{C["p3"]}"/><circle cx="{SX+20}" cy="{jy+19}" r="4.5" fill="{C["amb"]}"/>'
          + s.text(SX + 34, jy + 23.5, 'argila.json', 'M7', 13.5, C['t2']) + '</g>')
    K, S_, P_, B_ = C['amb2'], C['t1'], C['t4'], C['blue']
    jl = [[('{', P_)],
          [('  "projeto": ', K), ('"Quadro e Turnover"', S_), (',', P_)],
          [('  "modelo": ', K), ('"faixa-de-kpis"', S_), (',', P_)],
          [('  "tabelas": ', K), ('[', P_), ('"fDesligamento"', B_), (', ', P_), ('"dMotivo"', B_), (',', P_)],
          [('              ', P_), ('"dCargo"', B_), (', ', P_), ('"fMeta"', B_), (', ', P_), ('"dEmpresa"', B_), ('],', P_)],
          [('  "medidas": ', K), ('[', P_), ('"Desligamentos"', S_), (', ', P_), ('"Turnover"', S_), (',', P_)],
          [('              ', P_), ('"Meta de Turnover"', S_), ('],', P_)],
          [('  "relacionamentos": ', K), ('[{', P_), ('"de"', K), (': ', P_), ('"fMeta"', B_), (', ', P_), ('"para"', K), (': ', P_), ('"dEmpresa"', B_), ('}]', P_)],
          [('}', P_)]]
    lh = min(26, (jh - 58) / len(jl))
    for i, partes in enumerate(jl):
        x = SX + 22
        frag = ''
        for txt, cor in partes:
            frag += s.text(x, 0, txt, 'M4', 13.5, cor)
            x += width(txt, 'M4', 13.5)
        cl, b = s.janela([(3.8 + i * .12, 5.6)], fi=.25, dy=0, out_dy=0)
        s.add(f'<g transform="translate(0 {jy + 64 + i * lh:.1f})"><g class="{cl}"{b}>{frag}</g></g>')

    # cena 2: o protótipo (a mesma janela do descanso)
    s.comment('Cena 2 · protótipo (6,0–9,0 s): a janela do protótipo sobe; o selo Aprovado cai em 7,4 s')
    img, (iw, ih) = captura_b64('faixa-de-kpis', 640, 78)
    jw = SW
    jih = round(jw * ih / iw)
    wy = SY + 4
    s.defs.append(f'<clipPath id="cp"><rect x="{SX}" y="{wy + 34}" width="{jw}" height="{jih}" rx="0"/></clipPath>')
    cl, b = s.janela([(0, 2.6), (6.0, T)], dy=16)
    tag_w = width(X['ficticio'], 'I6', 11.5) + 20
    s.add(f'<g class="{cl}"{b}>' + janela_nav(s, SX, wy, jw, jih + 34 + 1, 'argila.prototipo.html')
          + card(SX + jw - tag_w - 12, wy + 8, tag_w, 19, '#1A1408', 'rgba(245,158,11,.55)', 9.5)
          + s.text(SX + jw - tag_w / 2 - 12, wy + 21.5, X['ficticio'], 'I6', 11.5, C['amb2'], 'middle')
          + f'<image x="{SX}" y="{wy + 34}" width="{jw}" height="{jih}" href="data:image/webp;base64,{img}" clip-path="url(#cp)" preserveAspectRatio="xMidYMid slice"/>'
          + '</g>')
    win_bottom = wy + 34 + jih
    # selo "Aprovado ✓"
    st_txt = X['aprovado'] + ' ✓'
    stw = width(st_txt, 'I8', 19, 1) + 36
    stx, sty = SX + jw - stw - 26, win_bottom - 70
    cl, b = s.janela([(0, 2.6), (7.4, T)], fi=.3, dy=0, sc=1.7, ease='cubic-bezier(.3,1.4,.5,1)')
    s.add(f'<g transform="rotate(-6 {stx + stw / 2:.0f} {sty + 22})"><g class="{cl}"{b}>'
          f'<rect x="{stx:.1f}" y="{sty}" width="{stw:.1f}" height="44" rx="10" fill="#0B2A22" stroke="{C["ok"]}" stroke-width="2.5"/>'
          f'<rect x="{stx + 5:.1f}" y="{sty + 5}" width="{stw - 10:.1f}" height="34" rx="7" fill="none" stroke="{C["ok"]}" stroke-opacity=".45"/>'
          + s.text(stx + stw / 2, sty + 29, st_txt, 'I8', 19, '#A7F3D0', 'middle', ls=1) + '</g></g>')

    # cena 3: Katsu!
    s.comment('Cena 3 · Katsu! (9,0–10,6 s): a estrela nasce, incha e solta 18 partículas âmbar e laranja')
    kx, ky = cxm, win_bottom + (560 - win_bottom) / 2 + 6
    fr = [(0, 'opacity:0;transform:scale(.2)'), (9.0, 'opacity:0;transform:scale(.2)'), (9.35, 'opacity:1;transform:scale(1)'),
          (9.75, 'opacity:1;transform:scale(1.18)'), (9.95, 'opacity:1;transform:scale(1.25)'), (10.35, 'opacity:0;transform:scale(1.6)'), (T, 'opacity:0;transform:scale(.2)')]
    ck = s.kf(fr, 'cubic-bezier(.2,.8,.2,1)', 'center')
    s.add(f'<g class="{ck}" opacity="0"><polygon points="{estrela(kx, ky, 82, 46)}" fill="url(#gx)"/>'
          f'<circle cx="{kx:.1f}" cy="{ky:.1f}" r="47" fill="#1A1006"/>'
          + s.text(kx, ky + 8, 'Katsu!', 'P8', 23, C['amb2'], 'middle') + '</g>')
    # brilho que dobra
    gb = s.kf([(0, 'opacity:0'), (9.8, 'opacity:0'), (10.0, 'opacity:.9'), (10.6, 'opacity:0'), (T, 'opacity:0')], 'ease-out')
    s.defs.append(f'<radialGradient id="flash"><stop offset="0" stop-color="{C["lar"]}" stop-opacity=".5"/><stop offset="1" stop-color="{C["lar"]}" stop-opacity="0"/></radialGradient>')
    s.add(f'<circle class="{gb}" opacity="0" cx="{kx:.0f}" cy="{ky:.0f}" r="190" fill="url(#flash)"/>')
    for i in range(18):
        a = math.radians(i * 20 + (7 if i % 2 else 0))
        dist = 120 + (i % 3) * 22
        dx, dy = math.cos(a) * dist, math.sin(a) * dist * .62
        cor = C['amb'] if i % 2 else C['lar']
        t0 = 9.92 + (i % 3) * .03
        cp_ = s.kf([(0, 'opacity:0;transform:translate(0px,0px) scale(.6)'), (t0, 'opacity:0;transform:translate(0px,0px) scale(.6)'),
                    (t0 + .05, 'opacity:1;transform:translate(0px,0px) scale(1)'),
                    (t0 + .75, f'opacity:0;transform:translate({dx:.0f}px,{dy:.0f}px) scale(.4)'), (T, 'opacity:0;transform:translate(0px,0px) scale(.6)')],
                   'cubic-bezier(.2,.8,.2,1)', 'center')
        r = 4.5 if i % 3 else 6
        forma = (f'<rect x="{kx - r:.1f}" y="{ky - r:.1f}" width="{2 * r}" height="{2 * r}" rx="1.5" fill="{cor}" transform="rotate(45 {kx:.1f} {ky:.1f})"/>'
                 if i % 2 else f'<circle cx="{kx:.1f}" cy="{ky:.1f}" r="{r}" fill="{cor}"/>')
        s.add(f'<g class="{cp_}" opacity="0">{forma}</g>')

    # cena 4: os arquivos
    s.comment('Cena 4 · arquivos (10,4–12,0 s): saem da explosão Painel.pbip, TMDL, PBIR, views SQL e HOMOLOGACAO.md')
    arqs = [('Painel.pbip', None), ('TMDL', X['arq_sub']['TMDL']), ('PBIR', X['arq_sub']['PBIR']),
            ('views SQL', X['arq_sub']['views SQL']), ('HOMOLOGACAO.md', X['arq_sub']['HOMOLOGACAO.md'])]
    chip = []
    for nome, sub in arqs:
        w_ = 30 + width(nome, 'M7', 14) + (10 + width(sub, 'I4', 12.5) if sub else 0) + 16
        chip.append((nome, sub, w_))
    linhas_chip = [chip[:3], chip[3:]]
    ch_h, gap = 40, 10
    total_h = 2 * ch_h + gap
    y0 = win_bottom + (560 - win_bottom - total_h) / 2 + 4
    k = 0
    for r_, fila in enumerate(linhas_chip):
        tw = sum(c[2] for c in fila) + gap * (len(fila) - 1)
        x = cxm - tw / 2
        for nome, sub, w_ in fila:
            yy = y0 + r_ * (ch_h + gap)
            ox, oy = kx - (x + w_ / 2), ky - (yy + ch_h / 2)
            t0 = 10.35 + k * .13
            hin = f'opacity:0;transform:translate({ox:.0f}px,{oy:.0f}px) scale(.3)'
            vis = 'opacity:1;transform:translate(0px,0px) scale(1)'
            cc = s.kf([(0, vis), (2.6, vis), (2.95, 'opacity:0;transform:translate(0px,-6px) scale(1)'), (2.96, hin), (t0, hin), (t0 + .55, vis), (T, vis)],
                      'cubic-bezier(.2,.8,.2,1)', 'center')
            icon = (f'<path d="M{x + 13:.1f} {yy + 11}h8l5 5v13h-13z" fill="none" stroke="{C["amb"]}" stroke-width="1.6" stroke-linejoin="round"/>')
            body = (card(x, yy, w_, ch_h, '#101C30', 'rgba(52,211,153,.55)', 9) + icon
                    + s.text(x + 34, yy + 25.5, nome, 'M7', 14, C['t0']))
            if sub:
                body += s.text(x + 34 + width(nome, 'M7', 14) + 10, yy + 25.5, sub, 'I4', 12.5, C['t3'])
            s.add(f'<g class="{cc}">{body}</g>')
            x += w_ + gap
            k += 1
    s.render('hero' if lang == 'pt' else 'hero.en')


# ================================================================= 2. modelos
def modelos(lang):
    pt = modelos_pt()
    n = len(pt)
    P = 2.6
    W, H, T = 1280, 800, round(P * n, 2)
    tit = 'Onze modelos de layout, do protótipo ao .pbip' if lang == 'pt' else 'Eleven layout templates, from prototype to .pbip'
    sub = ('Basta uma linha no argila.json ("modelo"): o protótipo e o .pbip saem com a mesma montagem.' if lang == 'pt'
           else 'One line in argila.json ("modelo"): the prototype and the .pbip come out with the same layout.')
    label = (f'Os {n} modelos de layout do Deidara, um por vez, em capturas reais do protótipo' if lang == 'pt'
             else f'Deidara\'s {n} layout templates, one at a time, in real prototype screenshots')
    s = SVG(W, H, T, label, f'{T:g} s. {n} modelos, {P:g} s cada, na ordem de tecnicas/arte/modelos.py; o primeiro volta na emenda do laço')
    s.add(marca(s, 64, 78, 24))
    s.add(s.text(64, 128, tit, 'P8', 34, C['t0']))
    s.add(s.text(64, 160, sub, 'I4', 17, C['t3']))
    # janela
    jw, iw_ = 960, 960
    jx = (W - jw) / 2
    jy = 192
    _, (cw, chh) = captura_b64(pt[0][0], 960)
    ih = round(iw_ * chh / cw)
    s.add(janela_nav(s, jx, jy, jw, ih + 36, 'argila.prototipo.html', 36))
    s.defs.append(f'<clipPath id="cj"><rect x="{jx + 1}" y="{jy + 36}" width="{jw - 2}" height="{ih - 1}" rx="0"/></clipPath>')
    ny = jy + 36 + ih + 46
    max_l = max(len(wrap(d if lang == 'pt' else MODELOS_EN[m], 'I4', 18, jw - 40)) for m, d in pt)
    s.h = H = int(ny + 32 + 26 * (max_l - 1) + 48 + 30)
    for k, (nome, desc_pt) in enumerate(pt):
        desc = desc_pt if lang == 'pt' else MODELOS_EN[nome]
        a, b_ = k * P, (k + 1) * P
        segs = [(0, P - .35)] if k == 0 else [(a - .35, b_ - .35)]
        if k == 0:
            segs.append((T - .35, T))
        s.comment(f'Modelo {k + 1} · {nome} ({max(0, a - .35):.2f}–{b_ - .35:.2f} s)')
        img, _ = captura_b64(nome, 960)
        # a imagem que entra fica por cima e cobre a que sai, que só some depois (nada de dupla exposição);
        # na emenda, a última some por cima da primeira, já opaca embaixo
        if k == 0:
            isegs, ifi, ifo = [(0, P), (T - .35, T)], .01, .01
        elif k < n - 1:
            isegs, ifi, ifo = [(a - .35, b_)], .35, .01
        else:
            isegs, ifi, ifo = [(a - .35, T - .35)], .35, .35
        cl, bs = s.janela(isegs, fi=ifi, fo=ifo, dy=0, out_dy=0, ease='ease-in-out')
        s.add(f'<g class="{cl}"{bs}><image x="{jx + 1}" y="{jy + 36}" width="{jw - 2}" height="{ih}" href="data:image/webp;base64,{img}" '
              f'preserveAspectRatio="xMidYMin slice" clip-path="url(#cj)"/></g>')
        tsegs = [(0, P - .35), (T - .15, T)] if k == 0 else [(a - .15, b_ - .35)]
        cl2, bs2 = s.janela(tsegs, fi=.15, fo=.2, dy=6, out_dy=-4)
        num = f'{k + 1:02d} / {n}'
        dl = wrap(desc, 'I4', 18, jw - 40)
        s.add(f'<g class="{cl2}"{bs2}>' + s.text(jx, ny, nome, 'M7', 24, C['amb'])
              + s.text(jx + jw, ny, num, 'M4', 16, C['t4'], 'end')
              + ''.join(s.text(jx, ny + 32 + i * 26, ln, 'I4', 18, C['t2']) for i, ln in enumerate(dl)) + '</g>')
        # barra de tempo do modelo
        if k == 0:
            gr = [(0, 'transform:scaleX(0)'), (P - .35, 'transform:scaleX(1)'), (P - .34, 'transform:scaleX(0)'), (T - .35, 'transform:scaleX(0)'), (T, 'transform:scaleX(0)')]
        else:
            gr = [(0, 'transform:scaleX(0)'), (a - .35, 'transform:scaleX(0)'), (b_ - .35, 'transform:scaleX(1)'), (b_ - .34, 'transform:scaleX(0)'), (T, 'transform:scaleX(0)')]
        cg = s.kf(gr, 'linear', 'left center')
        bar = f'<rect class="{cg}" x="{jx + 1}" y="{jy + 36 + ih - 3}" width="{jw - 2}" height="3" fill="{C["amb"]}" opacity=".9"/>'
        s.add(f'<g class="{cl}"{bs}>{bar}</g>')
    # fileira de pontos: um por modelo; o ativo cresce e fica âmbar
    pd = 16
    largo = 44
    tot = (n - 1) * pd + largo + (n - 1) * 10
    x0 = W / 2 - tot / 2
    dots_y = H - 30
    for k, (nome, _) in enumerate(pt):
        a, b_ = k * P, (k + 1) * P
        segs = [(0, P - .35)] if k == 0 else [(a - .35, b_ - .35)]
        if k == 0:
            segs.append((T - .35, T))
        # posição quando ativo: cada ponto antes dele tem pd; o ativo tem largo
        xa = x0 + k * (pd + 10)
        s.add(f'<rect x="{xa:.1f}" y="{dots_y - 6}" width="{pd}" height="12" rx="6" fill="{C["l1"]}"/>')
        tsegs = [(0, P - .35), (T - .15, T)] if k == 0 else [(a - .15, b_ - .35)]
        cl, bs = s.janela(tsegs, fi=.15, fo=.2, dy=0, out_dy=0, ease='ease-in-out')
        s.add(f'<rect class="{cl}"{bs} x="{xa:.1f}" y="{dots_y - 6}" width="{pd}" height="12" rx="6" fill="{C["amb"]}"/>')
    s.render('modelos' if lang == 'pt' else 'modelos.en')


# ================================================================= 3. resultados
RES = {
    'pt': dict(tit='Medido, não prometido',
               sub='Contado no próprio repositório. Os schemas foram conferidos no projeto gerado da vitrine.',
               label='Resultados medidos do Deidara: 289 testes, 143 de 143 arquivos JSON conferidos contra os schemas da Microsoft, dicionários, catálogos, galeria e zero linhas de dado',
               c1=('TESTES', '289', 'testes automatizados passando'),
               c2=('SCHEMAS DA MICROSOFT', '143 de 143', 'arquivos JSON do projeto gerado conferidos contra os schemas oficiais (na vitrine)'),
               c3=('MODELOS DE LAYOUT', '11', 'do protótipo ao .pbip, com a mesma montagem'),
               c4=('LINHAS DE DADO', '0', 'nas receitas: elas devolvem só a estrutura das fontes'),
               g1=('DICIONÁRIO DE FUNÇÕES', [('Power Query (M)', 667, None), ('DAX', 467, None)]),
               g2=('CATÁLOGOS DO DEIDARA', [('técnicas de visual', 53, (44, 'com visual nativo')), ('padrões de indicador', 30, None)]),
               g3=('GALERIA DE TERCEIROS (MIT)', [('modelos Deneb', 158, None), ('pacotes do daxlib', 66, None)]),
               nota='Testes: testes/ · funções: dicionario/dax.json e m.json · padrões e técnicas: dicionario/ · galeria: terceiros/catalogo.json · schemas: ferramentas/validar_pbip.py'),
    'en': dict(tit='Measured, not promised',
               sub='Counted in the repository itself. The schemas were checked on the generated showcase project.',
               label='Deidara measured results: 289 tests, 143 of 143 JSON files checked against Microsoft schemas, dictionaries, catalogs, gallery and zero data rows',
               c1=('TESTS', '289', 'automated tests passing'),
               c2=('MICROSOFT SCHEMAS', '143 of 143', 'JSON files of the generated project checked against the official schemas (showcase)'),
               c3=('LAYOUT TEMPLATES', '11', 'from prototype to .pbip, with the same layout'),
               c4=('DATA ROWS', '0', 'in the recipes: they return only the structure of the sources'),
               g1=('FUNCTION DICTIONARY', [('Power Query (M)', 667, None), ('DAX', 467, None)]),
               g2=('DEIDARA CATALOGS', [('visual techniques', 53, (44, 'with a native visual')), ('KPI patterns', 30, None)]),
               g3=('THIRD-PARTY GALLERY (MIT)', [('Deneb templates', 158, None), ('daxlib packages', 66, None)]),
               nota='Tests: testes/ · functions: dicionario/dax.json and m.json · patterns and techniques: dicionario/ · gallery: terceiros/catalogo.json · schemas: ferramentas/validar_pbip.py'),
}


def resultados(lang):
    X = RES[lang]
    W, H, T = 1280, 760, 12.0
    s = SVG(W, H, T, X['label'], '12 s. Cartões 0,2–1,1 · grade de testes 0,6–2,4 · anel dos schemas 1,0–2,6 · modelos 1,2–2,6 · '
                                 'barras 2,6–4,6 · tudo parado até 11,5 · some 11,5–12 (o quadro de descanso é o final)')
    s.add(marca(s, 64, 78, 24))
    s.add(s.text(64, 130, X['tit'], 'P8', 36, C['t0']))
    s.add(s.text(64, 162, X['sub'], 'I4', 17, C['t3']))
    out = T - .5

    def mostra(t, dy=14):
        return s.janela([(t, out)], fi=.5, fo=.45, dy=dy, base_visivel=True)

    gx = 20
    cy, ch, cw = 196, 336, (W - 128 - 3 * gx) / 4
    xs = [64 + i * (cw + gx) for i in range(4)]

    def cab(x, ttl, big, desc, big_size=46, big_col=C['amb'], desc_y=None):
        r = card(x, cy, cw, ch) + s.text(x + 24, cy + 38, ttl, 'I8', 11.5, C['t3'], ls=1.4)
        r += s.text(x + 24, cy + 92, big, 'P8', big_size, big_col)
        dl = wrap(desc, 'I4', 14.5, cw - 48)
        dy0 = desc_y or cy + ch - 24 - (len(dl) - 1) * 21
        r += ''.join(s.text(x + 24, dy0 + i * 21, ln, 'I4', 14.5, C['t2']) for i, ln in enumerate(dl))
        return r, len(dl)

    # 1. testes: grade 17 x 17 = 289
    s.comment('Cartão 1 · 289 testes: grade de 17 x 17 que acende linha a linha')
    x = xs[0]
    cl, b = mostra(.2)
    r, nl = cab(x, *X['c1'])
    cell, g = 7, 2.5
    gx0, gy0 = x + 24, cy + 114
    base = ''.join(f'<rect x="{gx0 + c * (cell + g)}" y="{gy0 + rr * (cell + g)}" width="{cell}" height="{cell}" rx="1.5" fill="{C["p3"]}"/>'
                   for rr in range(17) for c in range(17))
    lit = ''
    for rr in range(17):
        t0 = .6 + rr * .1
        ca = s.kf([(0, 'opacity:0'), (t0, 'opacity:0'), (t0 + .2, 'opacity:1'), (out, 'opacity:1'), (T, 'opacity:1')], 'linear')
        lit += f'<g class="{ca}">' + ''.join(f'<rect x="{gx0 + c * (cell + g)}" y="{gy0 + rr * (cell + g)}" width="{cell}" height="{cell}" rx="1.5" fill="{C["ok"]}"/>' for c in range(17)) + '</g>'
    gw = 17 * cell + 16 * g
    chk = (f'<circle cx="{gx0 + gw + 34}" cy="{gy0 + gw / 2}" r="17" fill="rgba(52,211,153,.14)" stroke="{C["ok"]}" stroke-width="2"/>'
           f'<path d="M{gx0 + gw + 26} {gy0 + gw / 2}l6 6 11-12" fill="none" stroke="{C["ok"]}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>')
    s.add(f'<g class="{cl}"{b}>{r}{base}{lit}{chk}</g>')
    # o texto do cartão 1 fica embaixo da grade: confere que não encosta
    # 2. schemas: anel 100%
    s.comment('Cartão 2 · 143 de 143: o anel fecha')
    x = xs[1]
    cl, b = mostra(.35)
    r, nl = cab(x, X['c2'][0], X['c2'][1], X['c2'][2], 40)
    rcx, rcy, rr_ = x + cw / 2, cy + 176, 48
    circ = 2 * math.pi * rr_
    cr = s.kf([(0, f'stroke-dashoffset:{circ:.1f}'), (1.0, f'stroke-dashoffset:{circ:.1f}'), (2.6, 'stroke-dashoffset:0'), (T, 'stroke-dashoffset:0')],
              'cubic-bezier(.4,0,.2,1)')
    ring = (f'<circle cx="{rcx}" cy="{rcy}" r="{rr_}" fill="none" stroke="{C["p3"]}" stroke-width="10"/>'
            f'<circle class="{cr}" cx="{rcx}" cy="{rcy}" r="{rr_}" fill="none" stroke="{C["ok"]}" stroke-width="10" stroke-linecap="round" '
            f'stroke-dasharray="{circ:.1f}" stroke-dashoffset="0" transform="rotate(-90 {rcx} {rcy})"/>'
            + s.text(rcx, rcy + 8, '100%', 'P8', 22, C['t0'], 'middle'))
    s.add(f'<g class="{cl}"{b}>{r}{ring}</g>')
    # 3. modelos: 11 miniaturas acendem
    s.comment('Cartão 3 · 11 modelos: onze miniaturas acendem em sequência')
    x = xs[2]
    cl, b = mostra(.5)
    r, nl = cab(x, *X['c3'])
    mw, mh, mg = 50, 32, 8
    minis = ''
    for i in range(11):
        mx = x + 24 + (i % 4) * (mw + mg)
        my = cy + 122 + (i // 4) * (mh + mg)
        t0 = 1.2 + i * .12
        ca = s.kf([(0, 'opacity:0'), (t0, 'opacity:0'), (t0 + .25, 'opacity:1'), (T, 'opacity:1')], 'linear')
        minis += (f'<rect x="{mx}" y="{my}" width="{mw}" height="{mh}" rx="4" fill="{C["p2"]}" stroke="{C["l1"]}"/>'
                  f'<g class="{ca}"><rect x="{mx}" y="{my}" width="{mw}" height="{mh}" rx="4" fill="#1A1408" stroke="{C["amb"]}"/>'
                  f'<rect x="{mx + 5}" y="{my + 5}" width="{mw - 10}" height="5" rx="1.5" fill="{C["amb"]}"/>'
                  f'<rect x="{mx + 5}" y="{my + 14}" width="{(mw - 13) / 2:.1f}" height="13" rx="1.5" fill="{C["lar"]}" opacity=".7"/>'
                  f'<rect x="{mx + 8 + (mw - 13) / 2:.1f}" y="{my + 14}" width="{(mw - 13) / 2:.1f}" height="13" rx="1.5" fill="{C["amb2"]}" opacity=".45"/></g>')
    s.add(f'<g class="{cl}"{b}>{r}{minis}</g>')
    # 4. zero linhas de dado
    s.comment('Cartão 4 · 0 linhas de dado: as linhas de uma tabela são riscadas; a estrutura (cabeçalho) fica')
    x = xs[3]
    cl, b = mostra(.65)
    r, nl = cab(x, *X['c4'], big_col=C['ok'])
    tx_, ty_ = x + 24, cy + 124
    tw_ = cw - 48
    tab = (f'<rect x="{tx_}" y="{ty_}" width="{tw_}" height="24" rx="4" fill="rgba(96,165,250,.16)" stroke="{C["blue"]}"/>'
           + s.text(tx_ + 10, ty_ + 16.5, 'F_DESLIGAMENTO', 'M7', 12, '#BFDBFE'))
    for i in range(3):
        yy = ty_ + 32 + i * 22
        tab += f'<rect x="{tx_}" y="{yy}" width="{tw_}" height="16" rx="3" fill="{C["p2"]}"/>'
        st = s.kf([(0, 'transform:scaleX(0)'), (1.6 + i * .2, 'transform:scaleX(0)'), (2.0 + i * .2, 'transform:scaleX(1)'), (T, 'transform:scaleX(1)')],
                  'cubic-bezier(.4,0,.2,1)', 'left center')
        tab += f'<rect class="{st}" x="{tx_ - 4}" y="{yy + 7}" width="{tw_ + 8}" height="2.5" rx="1" fill="{C["red"]}"/>'
    s.add(f'<g class="{cl}"{b}>{r}{tab}</g>')

    # barras
    by, bh_, bw = cy + ch + gx, 214, (W - 128 - 2 * gx) / 3
    for gi, key in enumerate(['g1', 'g2', 'g3']):
        ttl, itens = X[key]
        x = 64 + gi * (bw + gx)
        s.comment(f'Barras {gi + 1} · {ttl}')
        cl, b = mostra(2.4 + gi * .2)
        mx_ = max(v for _, v, _ in itens)
        body = card(x, by, bw, bh_) + s.text(x + 24, by + 38, ttl, 'I8', 11.5, C['t3'], ls=1.4)
        for j, (lab, v, parte) in enumerate(itens):
            yy = by + 78 + j * 74
            body += s.text(x + 24, yy, lab, 'I6', 15, C['t1']) + s.text(x + bw - 24, yy, f'{v}', 'P8', 22, C['amb'], 'end')
            full = bw - 48
            body += f'<rect x="{x + 24}" y="{yy + 12}" width="{full:.1f}" height="12" rx="6" fill="{C["bg"]}" stroke="{C["p3"]}"/>'
            t0 = 2.8 + gi * .2 + j * .25
            gr = s.kf([(0, 'transform:scaleX(0)'), (t0, 'transform:scaleX(0)'), (t0 + 1.2, 'transform:scaleX(1)'), (T, 'transform:scaleX(1)')],
                      'cubic-bezier(.15,.7,.3,1)', 'left center')
            bwv = full * v / mx_
            if parte:
                pv, pl = parte
                pw_ = full * pv / mx_
                body += (f'<g class="{gr}"><rect x="{x + 24}" y="{yy + 12}" width="{bwv:.1f}" height="12" rx="6" fill="{C["l2"]}"/>'
                         f'<rect x="{x + 24}" y="{yy + 12}" width="{pw_:.1f}" height="12" rx="6" fill="{C["ok"]}"/></g>')
                body += (f'<rect x="{x + 24}" y="{yy + 33}" width="10" height="10" rx="2" fill="{C["ok"]}"/>'
                         + s.text(x + 40, yy + 42, f'{pv} {pl}', 'I4', 13, C['t3']))
            else:
                body += f'<rect class="{gr}" x="{x + 24}" y="{yy + 12}" width="{bwv:.1f}" height="12" rx="6" fill="{C["amb"] if j == 0 else C["lar"]}"/>'
        s.add(f'<g class="{cl}"{b}>{body}</g>')
    ny = by + bh_ + 34
    nl_ = wrap(X['nota'], 'I4', 13.5, W - 128)
    for i, ln in enumerate(nl_):
        s.add(s.text(64, ny + i * 20, ln, 'I4', 13.5, C['t3']))
    s.h = int(ny + 20 * (len(nl_) - 1) + 34)
    s.render('resultados' if lang == 'pt' else 'resultados.en')


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    ap.add_argument('--capturas-de', help='pasta com <modelo>.png 1440 x 900 do protótipo')
    a = ap.parse_args()
    if a.capturas_de:
        refazer_capturas(a.capturas_de)
    falta = [m for m, _ in modelos_pt() if not os.path.exists(os.path.join(CAPTURAS, m + '.webp'))]
    if falta:
        sys.exit('faltam capturas: ' + ', '.join(falta) + ' (use --capturas-de)')
    if set(MODELOS_EN) != {m for m, _ in modelos_pt()}:
        sys.exit('MODELOS_EN não bate com tecnicas/arte/modelos.py: traduza o modelo novo')
    for lang in ('pt', 'en'):
        hero(lang)
        modelos(lang)
        resultados(lang)


if __name__ == '__main__':
    main()
