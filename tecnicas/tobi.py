"""
================================================================================
 TOBI — o parceiro que não para de falar
================================================================================
Nome de referência: Tobi, o parceiro do Deidara na Akatsuki, fala o tempo todo
e comenta tudo o que acontece. Aqui ele escreve a frase de leitura do painel:
uma medida DAX que conta, em português, o que o número fez e quem puxou.

    "Turnover: caiu 0,4 p.p. contra o ano anterior (5,1% → 4,7%), melhorou;
     maior variação em Cargo D."
    "Desligamentos: subiu 38 contra o ano anterior (730 → 768), piorou;
     Cargo D explica 61% da alta."

A parte "explica X%" só sai em medida aditiva (soma, contagem): em taxa, a
variação de um item não soma na do total, então a frase diz só onde a variação
foi maior. O mesmo texto é montado em Python para o protótipo (`frase`), com os
números fictícios.
"""

ADITIVAS = ('SUM(', 'COUNT(', 'COUNTROWS(')


def aditiva(md):
    """A medida soma por linha (o total é a soma das partes)?"""
    return md.get('tipo') == 'agregacao' and (md.get('dax') or '').startswith(ADITIVAS) and md.get('formato') != 'percentual'


def _formato_dax(formato):
    return {'inteiro': '#,0', 'percentual': '0.0%', 'moeda': '"R$" #,0', 'decimal': '#,0.00'}.get(formato, '#,0.00')


def dax(nome, b, comp, col, formato, maior, soma, tendencia=None):
    """A medida de texto. `b` e `comp` são referências DAX ([Atual], [Ano Anterior]); `col`, a coluna dos itens;
    `tendencia`, as VARs do C4 que terminam em `_tendencia` (o trecho sobre os últimos 12 meses)."""
    fmt = _formato_dax(formato)
    variacao = ('FORMAT(ABS(_delta) * 100, "0.0") & " p.p."' if formato == 'percentual'
                else f'FORMAT(ABS(_delta), "{fmt}")')
    bom = '_delta >= 0' if maior else '_delta <= 0'
    quem = ('IF(_delta <> 0 && NOT ISBLANK(_item), "; " & _item & " explica " & FORMAT(DIVIDE(_parte, _delta), "0%") '
            '& " da " & IF(_delta > 0, "alta", "queda"), "")' if soma else
            'IF(NOT ISBLANK(_item), "; maior variação em " & _item, "")')
    texto_nome = nome.replace('"', '""')
    return f"""-- Frase de leitura (Tobi): o que "{nome}" fez contra o período anterior e quem puxou
VAR _agora = {b}
VAR _antes = {comp}
VAR _delta = _agora - _antes
VAR _itens = FILTER(ALLSELECTED({col}), NOT ISBLANK({b}) || NOT ISBLANK({comp}))
VAR _top = TOPN(1, _itens, IF(_delta >= 0, {b} - {comp}, {comp} - {b}), DESC)
VAR _item = MAXX(_top, {col})
VAR _parte = MAXX(_top, {b} - {comp})
{(tendencia + chr(10)) if tendencia else ""}RETURN
    IF(
        ISBLANK(_agora) || ISBLANK(_antes),
        BLANK(),
        "{texto_nome}: " & IF(_delta >= 0, "subiu ", "caiu ") & {variacao}
            & " contra o ano anterior (" & FORMAT(_antes, "{fmt}") & " → " & FORMAT(_agora, "{fmt}") & "), "
            & IF({bom}, "melhorou", "piorou")
            & {quem} & "."{" & _tendencia" if tendencia else ""}
    )"""


def frase(nome, agora, antes, itens, formato, maior, soma, formatar, serie=None):
    """O mesmo texto, em Python, para o protótipo. `itens`: [(rótulo, agora, antes)]; `formatar(v, formato)`."""
    if agora is None or antes is None:
        return ''
    delta = agora - antes
    variacao = (f'{abs(delta) * 100:.1f}'.replace('.', ',') + ' p.p.' if formato == 'percentual'
                else formatar(abs(delta), formato))
    bom = delta >= 0 if maior else delta <= 0
    texto = (f"{nome}: {'subiu' if delta >= 0 else 'caiu'} {variacao} contra o ano anterior "
             f"({formatar(antes, formato)} → {formatar(agora, formato)}), {'melhorou' if bom else 'piorou'}")
    if itens:
        r, a, b = max(itens, key=lambda x: (x[1] - x[2]) if delta >= 0 else (x[2] - x[1]))
        if soma and delta:
            texto += f'; {r} explica {round((a - b) / delta * 100)}% da {"alta" if delta > 0 else "queda"}'
        elif not soma:
            texto += f'; maior variação em {r}'
    texto += '.'
    if serie and len(serie) >= 6:                  # a tendência dos últimos 12 meses (C4 Karura)
        from tecnicas import c4
        ultimos = serie[-12:]
        inclinacao, r2 = c4.tendencia(ultimos)
        if r2 is not None and r2 >= c4.R2_MINIMO:
            passo = (f'{abs(inclinacao) * 100:.2f}'.replace('.', ',') + ' p.p.' if formato == 'percentual'
                     else formatar(abs(inclinacao), formato))
            texto += (f' Nos últimos {len(ultimos)} meses, a tendência é de {"alta" if inclinacao > 0 else "queda"}'
                      f' ({passo} por mês).')
        else:
            texto += f' Nos últimos {len(ultimos)} meses, sem tendência clara.'
    return texto
