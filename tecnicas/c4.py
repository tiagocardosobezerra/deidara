"""
================================================================================
 C4 KARURA — as bombas que ninguém vê
================================================================================
Nome de referência: o C4 Karura é a obra-prima do Deidara: bombas tão pequenas
que ninguém as vê, que entram no alvo e agem por dentro. Aqui é a estatística
que acha, dentro do número, o que o olho não vê: se a variação é sinal ou
ruído, quem está fora da curva, se a meta cabe no processo e para onde a série
anda.

Toda conta sai como DAX e roda no Power BI, sobre o dado real; o Deidara nunca
vê dado. A mesma conta existe em Python (as funções sem `dax_`), para o
protótipo desenhar com os números fictícios e para os testes conferirem contra
os exemplos resolvidos do NIST/SEMATECH e-Handbook of Statistical Methods
(conteúdo público; ver LICENCAS-DE-TERCEIROS.md):

- gráfico de controle de valores individuais (XmR), NIST 6.3.2.2:
  centro ± 3·MR̄/1,128;
- gráfico p (proporção, como o turnover), NIST 6.3.3.2: p̄ ± 3·√(p̄(1−p̄)/n);
- gráfico u (contagem por exposição), NIST 6.3.3.1: ū ± 3·√(ū/n);
- três regras de sinal das WECO, NIST 6.3.2: ponto fora do limite, 8 seguidos
  do mesmo lado do centro, 6 seguidos subindo ou descendo (com todas as regras
  o alarme falso sobe de 1 a cada 371 pontos para 1 a cada 92);
- fora da curva: z-score modificado 0,6745·(x − mediana)/MAD > 3,5, NIST
  1.3.5.17 (o z-score comum engana em grupo pequeno); em taxa, o gráfico p por
  unidade (o "funil": a empresa pequena tem limite mais largo);
- tendência: reta de mínimos quadrados (LINESTX) nos últimos 12 meses, só
  afirmada com r² de 0,5 para cima.
"""

import math
import statistics

D2 = 1.128                       # d2 para n = 2 (NIST 6.3.2.2): 3 / 1,128 = 2,66
LIMIAR_Z_MODIFICADO = 3.5        # NIST 1.3.5.17 (Iglewicz e Hoaglin)
LIMIAR_FUNIL = 3.0               # 3 sigmas, como os limites do gráfico p
R2_MINIMO = 0.5
PONTOS_MINIMOS = 20              # NIST 6.3.2: com menos, os limites ainda não são confiáveis
SINAIS = {1: 'ponto fora do limite', 2: '8 seguidos do mesmo lado da média', 3: '6 seguidos na mesma direção'}


# ===================================================================== Python
def xmr(valores):
    """{'centro', 'mr', 'sigma', 'superior', 'inferior'} do gráfico de valores individuais."""
    centro = sum(valores) / len(valores)
    amplitudes = [abs(b - a) for a, b in zip(valores, valores[1:])]
    mr = sum(amplitudes) / len(amplitudes) if amplitudes else 0.0
    sigma = mr / D2
    return {'centro': centro, 'mr': mr, 'sigma': sigma, 'superior': centro + 3 * sigma, 'inferior': centro - 3 * sigma}


def grafico_p(numeradores, denominadores):
    """Centro p̄ e limites de cada ponto (o n de cada ponto abre ou fecha o limite)."""
    p = sum(numeradores) / sum(denominadores)
    lim = [3 * math.sqrt(max(0.0, p * (1 - p)) / n) if n else 0.0 for n in denominadores]
    return {'centro': p, 'superior': [p + x for x in lim], 'inferior': [max(0.0, p - x) for x in lim]}


def grafico_u(numeradores, exposicoes):
    u = sum(numeradores) / sum(exposicoes)
    lim = [3 * math.sqrt(u / n) if n else 0.0 for n in exposicoes]
    return {'centro': u, 'superior': [u + x for x in lim], 'inferior': [max(0.0, u - x) for x in lim]}


def sinais(valores, centro, superior, inferior):
    """O sinal de cada ponto: 1 fora do limite, 2 oito do mesmo lado, 3 seis na mesma direção, None nenhum.
    `superior` e `inferior` podem ser um número (XmR) ou uma lista (p, u)."""
    sup = superior if isinstance(superior, list) else [superior] * len(valores)
    inf = inferior if isinstance(inferior, list) else [inferior] * len(valores)
    out = []
    for k, v in enumerate(valores):
        ult8 = valores[max(0, k - 7):k + 1]
        ult6 = valores[max(0, k - 5):k + 1]
        if v > sup[k] or v < inf[k]:
            out.append(1)
        elif len(ult8) == 8 and (min(ult8) > centro or max(ult8) < centro):
            out.append(2)
        elif len(ult6) == 6 and (all(b > a for a, b in zip(ult6, ult6[1:])) or all(b < a for a, b in zip(ult6, ult6[1:]))):
            out.append(3)
        else:
            out.append(None)
    return out


def z_modificado(valores):
    """0,6745·(x − mediana)/MAD de cada valor (NIST 1.3.5.17); None quando o MAD é zero."""
    med = statistics.median(valores)
    mad = statistics.median(abs(x - med) for x in valores)
    return [0.6745 * (x - med) / mad if mad else None for x in valores]


def z_funil(numeradores, denominadores):
    """Quantos desvios a taxa de cada unidade está do p̄, pelo tamanho dela (o gráfico p por unidade)."""
    p = sum(numeradores) / sum(denominadores)
    out = []
    for a, n in zip(numeradores, denominadores):
        dp = math.sqrt(max(0.0, p * (1 - p)) / n) if n else 0
        out.append((a / n - p) / dp if dp else None)
    return out


def tendencia(valores):
    """(inclinação por ponto, r²) da reta de mínimos quadrados sobre a série em ordem."""
    n = len(valores)
    if n < 3:
        return None, None
    xs = list(range(1, n + 1))
    mx, my = sum(xs) / n, sum(valores) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, valores))
    syy = sum((y - my) ** 2 for y in valores)
    inclinacao = sxy / sxx
    r2 = (sxy * sxy) / (sxx * syy) if syy else 0.0
    return inclinacao, r2


def meta_x_faixa(meta, superior, inferior, maior_melhor):
    """'dentro', 'inalcancavel' (fora, do lado bom) ou 'folgada' (fora, do lado ruim: o processo já bate)."""
    if inferior <= meta <= superior:
        return 'dentro'
    acima = meta > superior
    return 'inalcancavel' if acima == maior_melhor else 'folgada'


# ======================================================================== DAX
def _pontos(cal, b, num=None, den=None):
    extra = (f', "@num", {num}, "@den", {den}' if num else '')
    return (f'CALCULATETABLE(ADDCOLUMNS(VALUES({cal}[Ano-Mês Num]), "@v", {b}{extra}), ALLSELECTED({cal}))')


def _anterior(cal):
    """A coluna "@ant": o valor do ponto anterior na série (para a amplitude móvel e a direção)."""
    k = f'{cal}[Ano-Mês Num]'
    return (f'ADDCOLUMNS(_pontos, "@ant", VAR _k = {k} RETURN '
            f'MAXX(FILTER(_pontos, {k} = MAXX(FILTER(_pontos, {k} < _k), {k})), [@v]))')


def _limites(tipo, num, den, n_pontual=True):
    """VARs _centro e _sigma de cada tipo de gráfico (na série _pontos e _serie)."""
    if tipo == 'xmr':
        return ('VAR _centro = AVERAGEX(_pontos, [@v])\n'
                'VAR _mr = AVERAGEX(FILTER(_serie, NOT ISBLANK([@ant])), ABS([@v] - [@ant]))\n'
                f'VAR _sigma = DIVIDE(_mr, {D2})')
    n = den if n_pontual else 'AVERAGEX(_pontos, [@den])'
    centro = 'DIVIDE(SUMX(_pontos, [@num]), SUMX(_pontos, [@den]))'
    disp = ('SQRT(MAX(0, DIVIDE(_centro * (1 - _centro), _n)))' if tipo == 'p' else
            'SQRT(MAX(0, DIVIDE(_centro, _n)))')   # taxa acima de 100% num mês não derruba a medida
    return f'VAR _centro = {centro}\nVAR _n = {n}\nVAR _sigma = {disp}'


def dax_controle(parte, b, cal, tipo, num=None, den=None):
    """`parte`: centro, superior, inferior ou sinal. `tipo`: xmr, p ou u (p e u pedem numerador e denominador)."""
    cab = (f'-- C4 Karura · gráfico de controle ({ {"xmr": "XmR", "p": "p", "u": "u"}[tipo] }), {parte}: NIST 6.3\n'
           f'VAR _pontos = {_pontos(cal, b, num, den)}\n'
           f'VAR _serie = {_anterior(cal)}\n'
           + _limites(tipo, num, den) + '\n')
    piso = 'MAX(0, _centro - 3 * _sigma)' if tipo in ('p', 'u') else '_centro - 3 * _sigma'
    if parte == 'centro':
        return cab + 'RETURN\n    _centro'
    if parte == 'superior':
        return cab + 'RETURN\n    _centro + 3 * _sigma'
    if parte == 'inferior':
        return cab + f'RETURN\n    {piso}'
    k = f'{cal}[Ano-Mês Num]'
    return cab + f"""VAR _k = MAX({k})
VAR _v = {b}
VAR _ate = FILTER(_serie, {k} <= _k)
VAR _ult8 = TOPN(8, _ate, {k}, DESC)
VAR _ult5 = TOPN(5, _ate, {k}, DESC)
VAR _lado = COUNTROWS(_ult8) = 8 && (MINX(_ult8, [@v]) > _centro || MAXX(_ult8, [@v]) < _centro)
VAR _sobe = COUNTROWS(FILTER(_ult5, NOT ISBLANK([@ant]) && [@v] > [@ant])) = 5
VAR _desce = COUNTROWS(FILTER(_ult5, NOT ISBLANK([@ant]) && [@v] < [@ant])) = 5
RETURN
    IF(
        HASONEVALUE({k}) && NOT ISBLANK(_v),
        SWITCH(TRUE(), _v > _centro + 3 * _sigma || _v < {piso}, 1, _lado, 2, _sobe || _desce, 3, BLANK())
    )"""


def dax_meta_x_faixa(b, meta, cal, tipo, maior, formato, num=None, den=None):
    """Texto: a meta cabe na faixa normal do processo?"""
    fmt = {'inteiro': '#,0', 'percentual': '0.0%', 'moeda': '"R$" #,0', 'decimal': '#,0.00'}.get(formato, '#,0.00')
    inalcancavel = '_meta > _sup' if maior else '_meta < _inf'
    return (f'-- C4 Karura · meta x faixa normal: a meta cabe no processo como ele está?\n'
            f'VAR _pontos = {_pontos(cal, b, num, den)}\n'
            f'VAR _serie = {_anterior(cal)}\n'
            + _limites(tipo, num, den, n_pontual=False) + '\n'
            + f"""VAR _sup = _centro + 3 * _sigma
VAR _inf = {'MAX(0, _centro - 3 * _sigma)' if tipo in ('p', 'u') else '_centro - 3 * _sigma'}
VAR _meta = {meta}
VAR _faixa = FORMAT(_inf, "{fmt}") & " a " & FORMAT(_sup, "{fmt}")
RETURN
    IF(
        ISBLANK(_meta) || COUNTROWS(_pontos) < 2,
        BLANK(),
        SWITCH(
            TRUE(),
            _meta >= _inf && _meta <= _sup,
                "A meta (" & FORMAT(_meta, "{fmt}") & ") está dentro da faixa normal (" & _faixa
                    & "): alguns meses vão bater e outros não, por acaso.",
            {inalcancavel},
                "A meta (" & FORMAT(_meta, "{fmt}") & ") está fora da faixa normal (" & _faixa
                    & "): sem mudar o processo, ela não será atingida de forma estável.",
            "A meta (" & FORMAT(_meta, "{fmt}") & ") é folgada: a faixa normal (" & _faixa
                & ") já fica toda do lado bom."
        )
    )""")


def dax_fora_da_curva(b, col, proporcao=False, num=None, den=None):
    """O quanto cada item está fora do padrão: z-score modificado (valor) ou desvios do funil (taxa)."""
    if proporcao:
        return (f'-- C4 Karura · fora da curva (funil do gráfico p, NIST 6.3.3.2)\n'
                f'VAR _itens = ADDCOLUMNS(ALLSELECTED({col}), "@num", {num}, "@den", {den})\n'
                f'VAR _p = DIVIDE(SUMX(_itens, [@num]), SUMX(_itens, [@den]))\n'
                f'VAR _n = {den}\n'
                f'VAR _dp = SQRT(MAX(0, DIVIDE(_p * (1 - _p), _n)))\n'
                f'RETURN\n    IF(HASONEVALUE({col}) && NOT ISBLANK({b}), DIVIDE(DIVIDE({num}, _n) - _p, _dp))')
    return (f'-- C4 Karura · fora da curva (z-score modificado, NIST 1.3.5.17)\n'
            f'VAR _itens = ADDCOLUMNS(ALLSELECTED({col}), "@v", {b})\n'
            f'VAR _mediana = MEDIANX(FILTER(_itens, NOT ISBLANK([@v])), [@v])\n'
            f'VAR _mad = MEDIANX(FILTER(_itens, NOT ISBLANK([@v])), ABS([@v] - _mediana))\n'
            f'RETURN\n    IF(HASONEVALUE({col}) && NOT ISBLANK({b}), DIVIDE(0.6745 * ({b} - _mediana), _mad))')


def dax_tendencia(b, cal, formato):
    """O trecho da frase do Tobi sobre a tendência dos últimos 12 meses (LINESTX), só com r² ≥ 0,5."""
    k = f'{cal}[Ano-Mês Num]'
    passo = ('FORMAT(ABS(_inclinacao) * 100, "0.00") & " p.p."' if formato == 'percentual' else
             'FORMAT(ABS(_inclinacao), "' + {'inteiro': '#,0.0', 'moeda': '"R$" #,0'}.get(formato, '#,0.00') + '")')
    return f"""VAR _ultimos = TOPN(12, {_pontos(cal, b)}, {k}, DESC)
VAR _ordem = ADDCOLUMNS(_ultimos, "@i", RANKX(_ultimos, {k}, , ASC))
VAR _reta = LINESTX(_ordem, [@v], [@i])
VAR _inclinacao = MAXX(_reta, [Slope1])
VAR _r2 = MAXX(_reta, [CoefficientOfDetermination])
VAR _tendencia =
    IF(
        COUNTROWS(_ultimos) < 6,
        "",
        IF(
            _r2 >= {R2_MINIMO},
            " Nos últimos " & COUNTROWS(_ultimos) & " meses, a tendência é de " & IF(_inclinacao > 0, "alta", "queda")
                & " (" & {passo} & " por mês).",
            " Nos últimos " & COUNTROWS(_ultimos) & " meses, sem tendência clara."
        )
    )"""
