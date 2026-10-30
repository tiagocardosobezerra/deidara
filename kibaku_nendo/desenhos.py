"""
Medidas que desenham: o DAX que monta cada imagem SVG (barra contra a meta, pílula, seta, selo, radar, bolha,
variação IBCS, estrelas, progresso, iniciais, dispersão, espinha de peixe) e o HTML dos blocos de indicador, mais a
conferência das regras de SVG em DAX (referencias/svg.md). Só texto: quem decide qual medida gerar é a
especificação.
"""

import re

from kibaku_nendo.util import dax_medida

COR_BOA, COR_RUIM = '#107C10', '#D13438'
COR_TRILHO, COR_MARCA = '#EDEBE9', '#252423'
PREFIXO_SVG = 'data:image/svg+xml;charset=utf-8,'
FORMATO_DAX = {'inteiro': '#,0', 'percentual': '0.0%', 'moeda': '"R$" #,0.00', 'decimal': '#,0.00', 'data': 'dd/mm/yyyy'}
def _texto_dax(s):
    return '"' + str(s).replace('"', '""') + '"'

def _svg_iniciais(col, fundo, texto):
    return f"""-- Configuração: círculo com as duas primeiras letras do item, para o segmentador de botões
VAR _nome = SELECTEDVALUE({col})
VAR _espaco = SEARCH(" ", _nome, 1, 0)
VAR _iniciais = UPPER(IF(_espaco > 0, LEFT(_nome, 1) & MID(_nome, _espaco + 1, 1), LEFT(_nome, 2)))
-- Desenho (o # vira %23)
VAR _svg =
    "<svg xmlns='http://www.w3.org/2000/svg' width='40' height='40' viewBox='0 0 40 40' display='block'>"
        & "<circle cx='20' cy='20' r='19' fill='{fundo}'/>"
        & "<text x='20' y='26' text-anchor='middle' font-family='Segoe UI' font-size='16' font-weight='600' "
        & "fill='{texto}'>" & _iniciais & "</text>"
        & "</svg>"
RETURN
    IF(HASONEVALUE({col}), "{PREFIXO_SVG}" & _svg, BLANK())"""


def _svg_dispersao(col, x, y, imagem, acento, nx, ny):
    """Um SVG só com todos os pontos (para o cartão novo): cada eixo vai do menor ao maior valor, com folga."""
    ponto = (f'"<image href=\'" & {imagem} & "\' x=\'" & FORMAT(_px - 14, "0.0", "en-US") & "\' y=\'" '
             f'& FORMAT(_py - 14, "0.0", "en-US") & "\' width=\'28\' height=\'28\'/>"' if imagem else
             f'"<circle cx=\'" & FORMAT(_px, "0.0", "en-US") & "\' cy=\'" & FORMAT(_py, "0.0", "en-US") '
             f'& "\' r=\'13\' fill=\'%23{acento[1:]}\' fill-opacity=\'0.85\'/>"'
             f' & "<text x=\'" & FORMAT(_px, "0.0", "en-US") & "\' y=\'" & FORMAT(_py + 4, "0.0", "en-US") '
             f'& "\' text-anchor=\'middle\' font-family=\'Segoe UI\' font-size=\'10\' font-weight=\'600\' fill=\'%23FFFFFF\'>" '
             f'& UPPER(LEFT({col}, 1) & MID({col}, SEARCH(" ", {col}, 1, 0) + 1, 1)) & "</text>"')
    return f"""-- Configuração: área de 400 x 300, com 40 de margem para os eixos
VAR _minX = MINX(ALLSELECTED({col}), {x})
VAR _minY = MINX(ALLSELECTED({col}), {y})
VAR _folgaX = (MAXX(ALLSELECTED({col}), {x}) - _minX) * 0.1 + 1
VAR _folgaY = (MAXX(ALLSELECTED({col}), {y}) - _minY) * 0.1 + 1
VAR _baseX = _minX - _folgaX
VAR _baseY = _minY - _folgaY
VAR _faixaX = MAXX(ALLSELECTED({col}), {x}) + _folgaX - _baseX
VAR _faixaY = MAXX(ALLSELECTED({col}), {y}) + _folgaY - _baseY
VAR _pontos =
    CONCATENATEX(
        ALLSELECTED({col}),
        VAR _px = 40 + 350 * DIVIDE({x} - _baseX, _faixaX)
        VAR _py = 270 - 250 * DIVIDE({y} - _baseY, _faixaY)
        RETURN
            IF(NOT ISBLANK({x}) && NOT ISBLANK({y}), {ponto})
    )
-- Desenho (o # vira %23)
VAR _svg =
    "<svg xmlns='http://www.w3.org/2000/svg' width='100%25' height='100%25' viewBox='0 0 400 300' display='block'>"
        & "<line x1='40' y1='270' x2='395' y2='270' stroke='%23C8C6C4'/>"
        & "<line x1='40' y1='10' x2='40' y2='270' stroke='%23C8C6C4'/>"
        & "<text x='395' y='290' text-anchor='end' font-family='Segoe UI' font-size='11' fill='%23605E5C'>{nx} →</text>"
        & "<text x='44' y='20' font-family='Segoe UI' font-size='11' fill='%23605E5C'>↑ {ny}</text>"
        & _pontos
        & "</svg>"
RETURN
    "{PREFIXO_SVG}" & _svg"""


def _texto_svg(s):
    """Texto fixo dentro do SVG: sem "#", "%", "&" nem "<" soltos."""
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('%', '%25').replace('#', '%23')
            .replace('"', "'"))


def _svg_espinha(b, cortes, n, maior, nome, acento):
    """Diagrama de espinha de peixe (Ishikawa): a cabeça é o indicador, cada espinha é um corte, e em cada espinha
    os N itens piores que a média do corte, do pior para o menos ruim."""
    k = len(cortes)
    lados = (k + 1) // 2                           # espinhas por lado: as ímpares em cima, as pares embaixo
    passo = 500 / lados
    sentido, op = ('ASC', '<') if maior else ('DESC', '>')
    linhas, desenho = [], []
    for i, (col, rotulo) in enumerate(cortes):
        cima = i % 2 == 0
        xa = 10 + passo * (i // 2 + 1)             # onde a espinha encosta na linha central
        xp = xa - 60                               # a ponta da espinha
        yp, yt, y0 = (40, 30, 52) if cima else (280, 300, 190)
        nome_item = f'SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(LEFT({col}, 20), "%", "%25"), "#", "%23"), "&", "&amp;"), "<", "&lt;")'
        linhas.append(
            f'VAR _media{i + 1} = AVERAGEX(ALLSELECTED({col}), {b})\n'
            f'VAR _itens{i + 1} =\n'
            f'    CONCATENATEX(\n'
            f'        TOPN({n}, FILTER(ALLSELECTED({col}), NOT ISBLANK({b}) && {b} {op} _media{i + 1}), {b}, {sentido}),\n'
            f'        "<tspan x=\'{xp - 6:.0f}\' dy=\'15\'>" & {nome_item} & "</tspan>",\n'
            f'        " ",\n        {b}, {sentido}\n    )')
        desenho.append(f"""        & "<line x1='{xa:.0f}' y1='160' x2='{xp:.0f}' y2='{yp}' stroke='%23A19F9D' stroke-width='2'/>"
        & "<text x='{xp:.0f}' y='{yt}' font-family='Segoe UI' font-size='12' font-weight='700' fill='%23252423'>{_texto_svg(rotulo)}</text>"
        & "<text y='{y0 - 15}' text-anchor='end' font-family='Segoe UI' font-size='11' fill='%23A4262C'>" & _itens{i + 1} & "</text>\"""")
    vars_ = '\n'.join(linhas)
    corpo = '\n'.join(desenho)
    return f"""-- Configuração: espinha de peixe em 640 x 320; em cada corte, os {n} piores que a média do corte
{vars_}
-- Cores (o # vira %23)
VAR _cor = "%23{acento[1:]}" -- destaque do tema
-- Desenho
VAR _svg =
    "<svg xmlns='http://www.w3.org/2000/svg' width='100%25' height='100%25' viewBox='0 0 640 320' overflow='visible' display='block'>"
        & "<line x1='20' y1='160' x2='520' y2='160' stroke='%23605E5C' stroke-width='4'/>"
        & "<rect x='522' y='130' width='114' height='60' rx='8' fill='" & _cor & "'/>"
        & "<text x='579' y='165' text-anchor='middle' font-family='Segoe UI' font-size='12' font-weight='700' fill='%23FFFFFF'>{_texto_svg(nome[:18])}</text>"
{corpo}
        & "</svg>"
RETURN
    "{PREFIXO_SVG}" & _svg"""


def _html_kpis(itens, acento):
    blocos = []
    for x in itens:
        fmt = FORMATO_DAX.get(x['formato'], '#,0.00')
        cor = (f'IF({dax_medida(x["nome"])} {">=" if x["polaridade"] == "maior_melhor" else "<="} '
               f'{dax_medida(x["meta_medida"])}, "{COR_BOA}", "{COR_RUIM}")' if x.get('meta_medida') else f'"{COR_MARCA}"')
        blocos.append(f'"<div class=\'kpi\'><div class=\'rotulo\'>{x["nome"]}</div>'
                      f'<div class=\'valor\' style=\'color:" & {cor} & "\'>" & FORMAT({dax_medida(x["nome"])}, {_texto_dax(fmt)}) '
                      f'& "</div></div>"')
    corpo = '\n        & '.join(blocos)
    return f"""-- HTML para o visual HTML Content: um bloco por indicador, a cor do valor segue a meta
VAR _estilo =
    "<style>.faixa{{display:flex;gap:12px;font-family:Segoe UI}}.kpi{{flex:1;border-top:4px solid {acento};"
        & "padding:8px 12px;background:#FFFFFF}}.rotulo{{font-size:12px;color:#605E5C}}.valor{{font-size:26px;"
        & "font-weight:600}}</style>"
RETURN
    _estilo & "<div class='faixa'>"
        & {corpo}
        & "</div>"
"""


def _svg_barra_meta(b, meta, col, op):
    return f"""-- Configuração: a imagem tem 100 x 20 e preenche a célula
VAR _valor = {b}
VAR _meta = {meta}
-- Cálculo: o mesmo eixo para todas as linhas visíveis (maior valor ou meta, com folga)
VAR _maximo =
    MAXX(ALLSELECTED({col}), MAX({b}, {meta})) * 1.1
VAR _largura = IF(_maximo > 0, MAX(0, DIVIDE(_valor, _maximo) * 100), 0)
VAR _posMeta = IF(_maximo > 0, MAX(0, DIVIDE(_meta, _maximo) * 100), 0)
VAR _ordem = FORMAT(ROUND(MAX(0, DIVIDE(_valor, _maximo)) * 1000000000, 0), "000000000000")
-- Cores (o # vira %23)
VAR _corBarra = IF(_valor {op} _meta, "%23{COR_BOA[1:]}", "%23{COR_RUIM[1:]}") -- verde bateu / vermelho não bateu
VAR _corTrilho = "%23{COR_TRILHO[1:]}" -- cinza claro
VAR _corMeta = "%23{COR_MARCA[1:]}" -- quase preto
-- Desenho
VAR _svg =
    "<svg xmlns='http://www.w3.org/2000/svg' width='100%25' height='100%25' viewBox='-2 -2 104 24' "
        & "overflow='visible' preserveAspectRatio='none' display='block'>"
        & "<desc>" & _ordem & "</desc>"
        & "<rect x='0' y='0' width='100' height='20' rx='3' fill='" & _corTrilho & "'/>"
        & "<rect x='0' y='3' width='" & FORMAT(_largura, "0.00", "en-US") & "' height='14' rx='3' fill='" & _corBarra & "'/>"
        & "<line x1='" & FORMAT(_posMeta, "0.00", "en-US") & "' y1='-2' x2='" & FORMAT(_posMeta, "0.00", "en-US")
        & "' y2='22' stroke='" & _corMeta & "' stroke-width='2' stroke-dasharray='3 2'/>"
        & "</svg>"
RETURN
    IF(HASONEVALUE({col}) && NOT ISBLANK(_valor), "{PREFIXO_SVG}" & _svg, BLANK())"""


def _svg_pilula(b, meta, col, op):
    return f"""-- Configuração: a largura acompanha o texto
VAR _valor = {b}
VAR _meta = {meta}
VAR _bateu = _valor {op} _meta
VAR _texto = IF(_bateu, "Na meta", "Fora da meta")
VAR _largura = LEN(_texto) * 7 + 20
-- Cores (o # vira %23)
VAR _corFundo = IF(_bateu, "%23DFF6DD", "%23FDE7E9") -- verde claro / vermelho claro
VAR _corTexto = IF(_bateu, "%23107C10", "%23A4262C") -- verde / vermelho escuro
-- Desenho
VAR _svg =
    "<svg xmlns='http://www.w3.org/2000/svg' width='" & _largura & "' height='22' viewBox='-1 -1 "
        & (_largura + 2) & " 24' overflow='visible' display='block'>"
        & "<desc>" & IF(_bateu, "1", "0") & "</desc>"
        & "<rect x='0' y='0' width='" & _largura & "' height='22' rx='11' fill='" & _corFundo & "'/>"
        & "<text x='" & FORMAT(_largura / 2, "0.0", "en-US") & "' y='15' text-anchor='middle' "
        & "font-family='Segoe UI' font-size='12' font-weight='600' fill='" & _corTexto & "'>" & _texto & "</text>"
        & "</svg>"
RETURN
    IF(HASONEVALUE({col}) && NOT ISBLANK(_valor) && NOT ISBLANK(_meta), "{PREFIXO_SVG}" & _svg, BLANK())"""


def _svg_seta(b, antes, col, op):
    return f"""-- Configuração: a imagem tem 100 x 20; a seta vai do valor anterior (ponto cinza) ao atual
VAR _atual = {b}
VAR _antes = {antes}
-- Cálculo: o mesmo eixo para todas as linhas visíveis
VAR _maximo =
    MAXX(ALLSELECTED({col}), MAX({b}, {antes})) * 1.1
VAR _x1 = IF(_maximo > 0, MAX(0, DIVIDE(_antes, _maximo) * 100), 0)
VAR _x2 = IF(_maximo > 0, MAX(0, DIVIDE(_atual, _maximo) * 100), 0)
VAR _ponta = IF(_x2 >= _x1, -4, 4)
VAR _ordem = FORMAT(ROUND(MAX(0, DIVIDE(_atual, _maximo)) * 1000000000, 0), "000000000000")
-- Cores (o # vira %23): a cor segue a polaridade do indicador
VAR _cor = IF(_atual {op} _antes, "%23{COR_BOA[1:]}", "%23{COR_RUIM[1:]}") -- verde melhorou / vermelho piorou
VAR _corTrilho = "%23{COR_TRILHO[1:]}" -- cinza claro
VAR _corAntes = "%23A19F9D" -- cinza médio
-- Desenho
VAR _svg =
    "<svg xmlns='http://www.w3.org/2000/svg' width='100%25' height='100%25' viewBox='-6 -2 112 24' "
        & "overflow='visible' preserveAspectRatio='none' display='block'>"
        & "<desc>" & _ordem & "</desc>"
        & "<line x1='0' y1='10' x2='100' y2='10' stroke='" & _corTrilho & "' stroke-width='2'/>"
        & "<circle cx='" & FORMAT(_x1, "0.00", "en-US") & "' cy='10' r='3' fill='" & _corAntes & "'/>"
        & "<line x1='" & FORMAT(_x1, "0.00", "en-US") & "' y1='10' x2='" & FORMAT(_x2, "0.00", "en-US")
        & "' y2='10' stroke='" & _cor & "' stroke-width='3'/>"
        & "<path d='M" & FORMAT(_x2 + _ponta, "0.00", "en-US") & " 5 L" & FORMAT(_x2, "0.00", "en-US") & " 10 L"
        & FORMAT(_x2 + _ponta, "0.00", "en-US") & " 15' fill='none' stroke='" & _cor & "' stroke-width='3'/>"
        & "</svg>"
RETURN
    IF(HASONEVALUE({col}) && NOT ISBLANK(_atual), "{PREFIXO_SVG}" & _svg, BLANK())"""


def _svg_radar(eixos, col, acento):
    """Um polígono por linha: cada eixo é uma medida, dividida pelo maior valor dela entre as linhas visíveis."""
    import math
    n = len(eixos)
    ang = [(-math.pi / 2 + 2 * math.pi * k / n) for k in range(n)]
    grade = ' '.join(f'{50 + 40 * math.cos(a):.1f},{50 + 40 * math.sin(a):.1f}' for a in ang)
    meio = ' '.join(f'{50 + 20 * math.cos(a):.1f},{50 + 20 * math.sin(a):.1f}' for a in ang)
    raios = ''.join(f"<line x1='50' y1='50' x2='{50 + 40 * math.cos(a):.1f}' y2='{50 + 40 * math.sin(a):.1f}' "
                    "stroke='%23E4E7EC'/>" for a in ang)
    linhas = []
    for k, (e, a) in enumerate(zip(eixos, ang), 1):
        linhas.append(f'VAR _v{k} = MIN(1, MAX(0, DIVIDE({e}, MAXX(ALLSELECTED({col}), {e}))))')
    pts = ' & " " & '.join(f'FORMAT(50 + 40 * _v{k} * {math.cos(a):.4f}, "0.0", "en-US") & "," & '
                           f'FORMAT(50 + 40 * _v{k} * {math.sin(a):.4f}, "0.0", "en-US")' for k, a in enumerate(ang, 1))
    return (f"""-- Configuração: radar de {n} eixos em 100 x 100; cada eixo vai de 0 ao maior valor entre as linhas
{chr(10).join(linhas)}
VAR _pontos = {pts}
-- Cores (o # vira %23)
VAR _cor = "%23{acento[1:]}" -- destaque do tema
-- Desenho
VAR _svg =
    "<svg xmlns='http://www.w3.org/2000/svg' width='100%25' height='100%25' viewBox='-2 -2 104 104' overflow='visible' display='block'>"
        & "<polygon points='{grade}' fill='none' stroke='%23D0D5DD'/>"
        & "<polygon points='{meio}' fill='none' stroke='%23E4E7EC'/>"
        & "{raios}"
        & "<polygon points='" & _pontos & "' fill='" & _cor & "' fill-opacity='0.35' stroke='" & _cor & "' stroke-width='2'/>"
        & "</svg>"
RETURN
    IF(HASONEVALUE({col}), "{PREFIXO_SVG}" & _svg, BLANK())""")


def _svg_bolha(b, linha, coluna, acento):
    return f"""-- Configuração: um círculo por célula da matriz; o raio segue a raiz do valor (a área fica proporcional)
VAR _valor = {b}
VAR _maximo = MAXX(CROSSJOIN(ALLSELECTED({linha}), ALLSELECTED({coluna})), {b})
VAR _raio = IF(_maximo > 0, SQRT(MAX(0, DIVIDE(_valor, _maximo))) * 10, 0)
VAR _ordem = FORMAT(ROUND(MAX(0, DIVIDE(_valor, _maximo)) * 1000000000, 0), "000000000000")
-- Cores (o # vira %23)
VAR _cor = "%23{acento[1:]}" -- destaque do tema
-- Desenho
VAR _svg =
    "<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='-1 -1 24 24' overflow='visible' display='block'>"
        & "<desc>" & _ordem & "</desc>"
        & "<circle cx='11' cy='11' r='" & FORMAT(_raio, "0.00", "en-US") & "' fill='" & _cor & "' fill-opacity='0.7'/>"
        & "</svg>"
RETURN
    IF(HASONEVALUE({linha}) && HASONEVALUE({coluna}) && NOT ISBLANK(_valor), "{PREFIXO_SVG}" & _svg, BLANK())"""


def _svg_variacao(b, plano, col, op):
    return f"""-- Configuração: barra do desvio (real menos comparação) a partir do centro, no estilo IBCS
VAR _desvio = {b} - {plano}
VAR _maximo = MAXX(ALLSELECTED({col}), ABS({b} - {plano})) * 1.1
VAR _largura = IF(_maximo > 0, DIVIDE(ABS(_desvio), _maximo) * 50, 0)
VAR _x = IF(_desvio >= 0, 50, 50 - _largura)
VAR _ordem = FORMAT(ROUND((DIVIDE(_desvio, _maximo) + 1) * 500000000, 0), "000000000000")
-- Cores (o # vira %23): a cor segue a polaridade do indicador
VAR _cor = IF({b} {op} {plano}, "%23{COR_BOA[1:]}", "%23{COR_RUIM[1:]}") -- verde melhor / vermelho pior
VAR _corEixo = "%23{COR_MARCA[1:]}" -- quase preto
-- Desenho
VAR _svg =
    "<svg xmlns='http://www.w3.org/2000/svg' width='100%25' height='100%25' viewBox='-2 -2 104 24' "
        & "overflow='visible' preserveAspectRatio='none' display='block'>"
        & "<desc>" & _ordem & "</desc>"
        & "<rect x='" & FORMAT(_x, "0.00", "en-US") & "' y='3' width='" & FORMAT(_largura, "0.00", "en-US")
        & "' height='14' fill='" & _cor & "'/>"
        & "<line x1='50' y1='-2' x2='50' y2='22' stroke='" & _corEixo & "' stroke-width='1.5'/>"
        & "</svg>"
RETURN
    IF(HASONEVALUE({col}) && NOT ISBLANK({b}), "{PREFIXO_SVG}" & _svg, BLANK())"""


ESTRELA = '10,1 12.6,7.2 19.5,7.6 14.2,12 16,18.8 10,15 4,18.8 5.8,12 0.5,7.6 7.4,7.2'
COR_ESTRELA = '#F2C811'


def _svg_estrelas(b, col, maior, maximo):
    """Cinco estrelas em 110 x 20: cinzas embaixo e as amarelas cortadas na largura da nota (meia estrela aparece)."""
    if maximo:
        nota = f'DIVIDE(_valor, {repr(float(maximo)).rstrip("0").rstrip(".")}) * 5'
        regra = f'a nota é o valor sobre {maximo} (vale cinco estrelas)'
    elif maior:
        nota = f'DIVIDE(_valor, MAXX(ALLSELECTED({col}), {b})) * 5'
        regra = 'o maior valor entre as linhas visíveis vale cinco estrelas'
    else:
        nota = f'DIVIDE(MINX(FILTER(ALLSELECTED({col}), NOT ISBLANK({b})), {b}), _valor) * 5'
        regra = 'o menor valor entre as linhas visíveis (o melhor) vale cinco estrelas'
    estrelas = ''.join(f"<polygon points='{ESTRELA}' transform='translate({22 * k} 0)'/>" for k in range(5))
    return f"""-- Configuração: cinco estrelas em 110 x 20; {regra}
VAR _valor = {b}
VAR _nota = MIN(5, MAX(0, {nota}))
VAR _largura = _nota * 22
VAR _ordem = FORMAT(ROUND(_nota * 1000000, 0), "000000000000")
-- Cores (o # vira %23)
VAR _cor = "%23{COR_ESTRELA[1:]}" -- amarelo das estrelas
VAR _apagada = "%23E1DFDD" -- cinza claro
-- Desenho
VAR _svg =
    "<svg xmlns='http://www.w3.org/2000/svg' width='110' height='20' viewBox='-2 -2 114 24' overflow='visible' display='block'>"
        & "<desc>" & _ordem & "</desc>"
        & "<defs><clipPath id='nota'><rect x='0' y='0' width='" & FORMAT(_largura, "0.00", "en-US") & "' height='20'/></clipPath></defs>"
        & "<g fill='" & _apagada & "'>{estrelas}</g>"
        & "<g fill='" & _cor & "' clip-path='url(%23nota)'>{estrelas}</g>"
        & "</svg>"
RETURN
    IF(HASONEVALUE({col}) && NOT ISBLANK(_valor), "{PREFIXO_SVG}" & _svg, BLANK())"""


def _svg_progresso(b, meta, col, op):
    """Cartão pequeno com o percentual da meta e a barra de progresso; feito para marcador de mapa."""
    return f"""-- Configuração: cartão de 120 x 34 com o percentual da meta e a barra (cheia ao bater a meta)
VAR _valor = {b}
VAR _meta = {meta}
VAR _percentual = DIVIDE(_valor, _meta)
VAR _largura = MIN(1, MAX(0, _percentual)) * 108
VAR _ordem = FORMAT(ROUND(MIN(10, MAX(0, _percentual)) * 100000000, 0), "000000000000")
-- Cores (o # vira %23): a cor segue a polaridade do indicador
VAR _cor = IF(_valor {op} _meta, "%23{COR_BOA[1:]}", "%23{COR_RUIM[1:]}") -- verde bateu / vermelho não bateu
-- Desenho (o % do texto vira %25)
VAR _svg =
    "<svg xmlns='http://www.w3.org/2000/svg' width='120' height='34' viewBox='-1 -1 122 36' overflow='visible' display='block'>"
        & "<desc>" & _ordem & "</desc>"
        & "<rect x='0' y='0' width='120' height='34' rx='6' fill='%23FFFFFF' stroke='%23C8C6C4'/>"
        & "<text x='6' y='15' font-family='Segoe UI' font-size='12' font-weight='700' fill='%23{COR_MARCA[1:]}'>"
        & FORMAT(_percentual * 100, "0", "en-US") & "%25 da meta</text>"
        & "<rect x='6' y='22' width='108' height='6' rx='3' fill='%23{COR_TRILHO[1:]}'/>"
        & "<rect x='6' y='22' width='" & FORMAT(_largura, "0.00", "en-US") & "' height='6' rx='3' fill='" & _cor & "'/>"
        & "</svg>"
RETURN
    IF(HASONEVALUE({col}) && NOT ISBLANK(_valor) && NOT ISBLANK(_meta), "{PREFIXO_SVG}" & _svg, BLANK())"""


def _svg_posicao(b, col, sentido, acento):
    return f"""-- Configuração: um selo redondo com a posição; os três primeiros na cor de destaque
VAR _posicao = RANKX(ALLSELECTED({col}), {b}, , {sentido}, Dense)
-- Cores (o # vira %23)
VAR _cor = IF(_posicao <= 3, "%23{acento[1:]}", "%23A19F9D") -- destaque do tema / cinza médio
-- Desenho
VAR _svg =
    "<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='-1 -1 26 26' overflow='visible' display='block'>"
        & "<desc>" & FORMAT(_posicao, "000000") & "</desc>"
        & "<circle cx='12' cy='12' r='11' fill='" & _cor & "'/>"
        & "<text x='12' y='16.5' text-anchor='middle' font-family='Segoe UI' font-size='12' font-weight='700' "
        & "fill='%23FFFFFF'>" & _posicao & "</text>"
        & "</svg>"
RETURN
    IF(HASONEVALUE({col}) && NOT ISBLANK({b}), "{PREFIXO_SVG}" & _svg, BLANK())"""


def _literais(dax):
    return re.findall(r'"((?:[^"]|"")*)"', re.sub(r'--[^\n]*', '', dax))


def conferir_svg(dax, p, onde, por_linha=True):
    """As regras de medida SVG em DAX (referencias/svg.md): erro quando a imagem quebra, aviso quando falha em
    algum lugar (total, borda, exportação)."""
    texto = ''.join(_literais(dax))
    if not re.search(r'data:image/svg\+xml(;[^,]*)?,', texto):
        p.erro(onde, '[SVG] o texto precisa começar com "data:image/svg+xml;charset=utf-8," (a vírgula final é '
                     'obrigatória)')
    if re.search(r"(fill|stroke|stop-color|color|background)\s*[=:]\s*['\"]?#[0-9A-Fa-f]{3,8}", texto):
        p.erro(onde, '[SVG] cor com "#" dentro da imagem: troque por "%23" (ex.: fill=\'%23107C10\'); sem isso a '
                     'imagem não aparece')
    marcacao = ''.join(x for x in _literais(dax) if '<' in x or '=' in x)
    if re.search(r'%(?![0-9A-Fa-f]{2})', marcacao):
        p.erro(onde, '[SVG] "%" solto dentro da imagem: escreva "%25" (ex.: width=\'100%25\')')
    if 'viewbox' not in texto.lower():
        p.aviso(onde, '[SVG] sem viewBox: a imagem pode sair cortada ou fora de escala; use viewBox com folga e '
                      'overflow=\'visible\'')
    if por_linha and not re.search(r'HASONEVALUE|ISINSCOPE', dax, re.I):
        p.aviso(onde, '[SVG] sem HASONEVALUE (ou ISINSCOPE) no RETURN: na linha de total a imagem sai quebrada')
    if 'foreignobject' in texto.lower():
        p.aviso(onde, '[SVG] foreignObject (HTML dentro do SVG) não funciona em todo lugar (celular, exportação): '
                      'prefira formas SVG')
    if '""' in dax:
        p.aviso(onde, '[SVG] aspas duplas escapadas no SVG: use aspas simples nos atributos (attr=\'" & _var & "\')')
