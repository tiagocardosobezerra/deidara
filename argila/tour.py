"""
Tour guiado da página, para o visual HTML Content (versão certificada).

A versão certificada tira script, formulário e recurso externo, então o tour
anda só com HTML e CSS: cada passo é um <details> dentro do anterior, e o
<summary> é o botão. Fechado, ele fica no cartão do passo atual como
"Próximo"; aberto, vai para o cartão do passo seguinte como "Voltar". O
holofote é um recorte com sombra enorme em volta do visual. Inspirado no
Interactive Dashboard Tour do Power BI Design Files (Sajjad Ahmadi, MIT);
o HTML é escrito pelo Deidara. As classes começam com "tg-" para não
esbarrar no CSS de quem hospeda (o protótipo usa o mesmo HTML).
"""

import html
import math

LARGURA_CARTAO = 380
BOTAO_W, BOTAO_H = 124, 36
LIMITE_PASSOS = 8


def _e(s):
    return html.escape(str(s), quote=False).replace("'", '&#39;')


def _altura(paragrafos):
    linhas = sum(max(1, math.ceil(len(t) / 46)) for t in paragrafos[1:])
    return 92 + 21 * linhas + BOTAO_H + 16


def _cartao(pos, w, h, alto):
    """Ao lado do visual (direita, esquerda), senão embaixo ou em cima; sempre dentro da página."""
    folga = 24
    candidatos = [(pos['x'] + pos['w'] + folga, pos['y']), (pos['x'] - LARGURA_CARTAO - folga, pos['y']),
                  (pos['x'], pos['y'] + pos['h'] + folga), (pos['x'], pos['y'] - alto - folga)]
    for x, y in candidatos:
        if 0 <= x and x + LARGURA_CARTAO <= w and 0 <= y and y + alto <= h:
            return x, y
    x = min(max(16, pos['x'] + 16), w - LARGURA_CARTAO - 16)
    y = min(max(16, pos['y'] + 16), h - alto - 16)
    return x, y


def passos(posicoes, nota):
    """[(paragrafos, pos)] dos visuais da página, na ordem de leitura; `nota(v)` dá título e definições."""
    out = []
    for v, pos in posicoes:
        texto = nota(v)
        if texto:
            out.append((texto, pos))
    return out[:LIMITE_PASSOS]


def html_do_tour(lista, w, h, acento):
    """O HTML do tour (sem aspas duplas nos atributos): um passo por visual."""
    n = len(lista)
    cartoes = [(*_cartao(pos, w, h, _altura(par)), _altura(par)) for par, pos in lista]
    css = [
        f".tg-tour{{position:relative;width:{w}px;height:{h}px;overflow:hidden;"
        "font-family:'Segoe UI',Arial,sans-serif;color:#252423;text-align:left}",
        ".tg-tour *{box-sizing:border-box}",
        ".tg-tour summary{list-style:none;cursor:pointer}.tg-tour summary::marker{content:''}"
        ".tg-tour summary::-webkit-details-marker{display:none}",
        f".tg-spot{{position:absolute;border-radius:10px;box-shadow:0 0 0 4000px rgba(255,255,255,.9);"
        f"outline:3px solid {acento};outline-offset:4px;pointer-events:none;animation:tg-aparece .35s ease-out both}}",
        f".tg-cartao{{position:absolute;width:{LARGURA_CARTAO}px;padding:16px 20px;background:#FFFFFF;"
        f"border:1px solid #D0D5DD;border-top:5px solid {acento};border-radius:12px;"
        "box-shadow:0 12px 32px rgba(0,0,0,.16);animation:tg-aparece .35s ease-out both}",
        f".tg-num{{font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:{acento}}}",
        ".tg-cartao h2,.tg-cartao p,.tg-num{position:static;transform:none;background:none}",
        ".tg-cartao h2{margin:6px 0 8px;font-size:18px;line-height:1.25;color:#252423}",
        ".tg-cartao p{margin:0 0 6px;font-size:14px;line-height:1.5;color:#3B3A39}",
        ".tg-fim{position:absolute;left:20px;right:20px;bottom:16px;font-size:13px;color:#605E5C}",
        f".tg-botao{{position:absolute;width:{BOTAO_W}px;height:{BOTAO_H}px;font-size:14px;font-weight:700}}",
        ".tg-prox,.tg-volta{width:100%;height:100%;align-items:center;justify-content:center;border-radius:18px}",
        f".tg-prox{{display:flex;background:{acento};color:#FFFFFF}}"
        f".tg-volta{{display:none;background:#FFFFFF;color:{acento};border:1px solid {acento}}}",
        "details[open]>summary>.tg-prox{display:none}details[open]>summary>.tg-volta{display:flex}",
        "details:has(>details[open])>.tg-passo{visibility:hidden}",
        f".tg-raiz>summary{{position:absolute;left:{w - 372}px;top:16px;z-index:999;display:flex;align-items:center;"
        f"justify-content:center;width:172px;height:44px;border-radius:22px;background:#FFFFFF;color:{acento};"
        f"border:1px solid {acento};font-size:14px;font-weight:700}}",
        ".tg-encerrar{display:none}.tg-raiz[open]>summary>.tg-encerrar{display:inline}"
        ".tg-raiz[open]>summary>.tg-de-novo{display:none}",
        "@keyframes tg-aparece{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}",
    ]
    for k, ((par, pos), (cx, cy, alto)) in enumerate(zip(lista, cartoes)):
        z = 10 * (k + 1)
        css.append(f".tg-s{k}{{left:{pos['x']:.0f}px;top:{pos['y']:.0f}px;width:{pos['w']:.0f}px;"
                   f"height:{pos['h']:.0f}px;z-index:{z}}}"
                   f".tg-c{k}{{left:{cx:.0f}px;top:{cy:.0f}px;height:{alto}px;z-index:{z + 1}}}")
        if k:                                        # o botão que leva ao passo k: no cartão k-1, depois no cartão k
            px, py, pa = cartoes[k - 1]
            css.append(f".tg-p{k}>summary{{left:{px + LARGURA_CARTAO - 20 - BOTAO_W:.0f}px;"
                       f"top:{py + pa - 16 - BOTAO_H:.0f}px;z-index:{z - 8}}}"
                       f".tg-p{k}[open]>summary{{left:{cx + 20:.0f}px;top:{cy + alto - 16 - BOTAO_H:.0f}px;"
                       f"z-index:{z + 2}}}")

    def passo(k):
        par, _ = lista[k]
        corpo = ''.join(f'<p>{_e(t)}</p>' for t in par[1:])
        fim = ("<div class='tg-fim'>Fim do tour. Use Voltar, no canto de cima, para ir ao painel.</div>"
               if k == n - 1 else '')
        return (f"<div class='tg-passo'><div class='tg-spot tg-s{k}'></div><div class='tg-cartao tg-c{k}'>"
                f"<div class='tg-num'>Passo {k + 1} de {n}</div><h2>{_e(par[0])}</h2>{corpo}{fim}</div></div>")

    miolo = ''
    for k in range(n - 1, 0, -1):                    # de dentro para fora: o passo k mora dentro do k-1
        miolo = (f"<details class='tg-p{k}'><summary class='tg-botao'><span class='tg-prox'>Próximo →</span>"
                 f"<span class='tg-volta'>← Voltar</span></summary>{passo(k)}{miolo}</details>")
    return (f"<style>{''.join(css)}</style><div class='tg-tour'><details class='tg-raiz' open>"
            "<summary><span class='tg-encerrar'>Encerrar tour ×</span><span class='tg-de-novo'>▶ Ver o tour de novo</span>"
            f"</summary>{passo(0) if n else ''}{miolo}</details></div>")


def dax_do_tour(texto_html):
    """A medida que devolve o HTML: textos de até 3000 letras emendados, com as aspas do DAX dobradas."""
    partes = [texto_html[i:i + 3000] for i in range(0, len(texto_html), 3000)] or ['']
    return '-- Tour guiado da página para o visual HTML Content (sem script: só HTML e CSS)\n' + '\n    & '.join(
        '"' + p.replace('"', '""') + '"' for p in partes)
