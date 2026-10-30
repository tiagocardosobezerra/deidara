"""
================================================================================
 ŌNOKI — o mestre que avalia o aluno
================================================================================
Nome de referência: Ōnoki, o Tsuchikage, foi o mestre do Deidara em Iwagakure
e nunca deixou passar um golpe mal dado. Aqui ele mede a Luneta:

- `avaliar`: para cada caso (um pedido e as tabelas certas), em que posição a
  busca põe a tabela certa. Dá o acerto no topo, o acerto entre as N primeiras
  e o MRR (a média de 1/posição), como o Pythagoras do Vegapunk;
- `retrato` e `diferencas`: as N primeiras tabelas de cada pedido, gravadas
  antes de uma mudança; depois dela, qualquer troca de ordem aparece, como o
  Atlas do Vegapunk. Mudou de propósito? Grave o retrato de novo.

Os casos ficam num JSON ({"casos": [{"pedido": "...", "esperadas": ["TABELA"]}],
"retrato": {...}}); o do exemplo é exemplos/aurora/onoki.json. Monte o do seu
time com os pedidos de verdade: é o jeito de saber se uma mudança na busca ou
nos sinônimos ajudou ou atrapalhou.
"""

from kibaku_nendo.util import chave
from tecnicas.luneta import descoberta


def _posicao(achadas, esperadas):
    alvo = {chave(x) for x in esperadas}
    return next((k for k, t in enumerate(achadas, 1) if chave(t) in alvo), None)


def avaliar(catalogos, casos, top=3):
    """{'casos', 'topo', 'entre_top', 'mrr', 'falhas': [(pedido, esperadas, achadas)]}."""
    linhas, falhas = [], []
    for c in casos:
        achadas = [r['tabela'] for r in descoberta.buscar(catalogos, c['pedido'], max(top, 10))]
        pos = _posicao(achadas, c['esperadas'])
        linhas.append(pos)
        if pos != 1:
            falhas.append((c['pedido'], c['esperadas'], achadas[:top], pos))
    n = max(1, len(casos))
    return {'casos': len(casos), 'topo': sum(1 for p in linhas if p == 1) / n,
            'entre_top': sum(1 for p in linhas if p and p <= top) / n,
            'mrr': sum(1 / p for p in linhas if p) / n, 'falhas': falhas, 'top': top}


def retrato(catalogos, casos, n=5):
    return {c['pedido']: [r['tabela'] for r in descoberta.buscar(catalogos, c['pedido'], n)] for c in casos}


def diferencas(antes, depois):
    """[texto] de cada pedido cujo topo mudou desde o retrato gravado."""
    out = []
    for pedido in sorted(set(antes) | set(depois)):
        a, d = antes.get(pedido), depois.get(pedido)
        if a != d:
            out.append(f'"{pedido}": {" > ".join(a or ["(sem retrato)"])}  ->  {" > ".join(d or ["(nada)"])}')
    return out


def texto(resultado):
    linhas = [f'Ōnoki avaliou {resultado["casos"]} pedido(s): tabela certa no topo em '
              f'{resultado["topo"]:.0%}, entre as {resultado["top"]} primeiras em {resultado["entre_top"]:.0%} '
              f'(MRR {resultado["mrr"]:.2f}).']
    for pedido, esperadas, achadas, pos in resultado['falhas']:
        onde = f'na posição {pos}' if pos else 'fora das primeiras'
        linhas.append(f'  ✗ "{pedido}": esperava {", ".join(esperadas)} ({onde}); veio {", ".join(achadas) or "nada"}')
    return '\n'.join(linhas)
