"""
O comando do Ōnoki: o acerto da busca.
"""

from kibaku_nendo.util import gravar_json, ler_json
from tecnicas.comum import (carregar_catalogos)
from tecnicas import onoki


def cmd_onoki(a):
    """Ōnoki avalia a busca da Luneta contra os casos do time (e confere o retrato gravado)."""
    cats, _ = carregar_catalogos(a)
    dados = ler_json(a.casos)
    casos = dados.get('casos') or []
    if not casos:
        print(f'{a.casos} sem "casos": [{{"pedido": "...", "esperadas": ["TABELA"]}}]')
        return 1
    resultado = onoki.avaliar(cats, casos, a.top)
    print(onoki.texto(resultado))
    atual = onoki.retrato(cats, casos)
    if a.gravar_retrato:
        dados['retrato'] = atual
        gravar_json(a.casos, dados)
        print(f'Retrato gravado em {a.casos}: a próxima avaliação mostra o que mudar na ordem.')
        return 0
    mudou = onoki.diferencas(dados.get('retrato') or {}, atual) if dados.get('retrato') else []
    for x in mudou:
        print(f'  MUDOU  {x}')
    if mudou:
        print('A ordem mudou desde o retrato. Se foi de propósito (sinônimo novo, ajuste de peso), grave de novo com '
              '--gravar-retrato.')
    return 1 if mudou else 0


def registrar(sub):
    on = sub.add_parser('onoki', help='Ōnoki mede a busca contra os pedidos de verdade do time (e pega regressão)')
    on.add_argument('--casos', required=True, help='JSON com os casos: [{"pedido", "esperadas"}] e o retrato gravado')
    on.add_argument('--argila')
    on.add_argument('--catalogos', nargs='+')
    on.add_argument('--top', type=int, default=3)
    on.add_argument('--gravar-retrato', action='store_true', help='grava a ordem atual como a referência')
    on.set_defaults(func=cmd_onoki)
