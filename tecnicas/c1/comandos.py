"""
Os comandos do C1: o protótipo.
"""

import os
from kibaku_nendo import VERSAO
from tecnicas.c1 import prototipo
from kibaku_nendo.util import gravar_texto
from tecnicas.comum import (LIGACAO_PENDENTE, carregar_argila, lembrete, mostrar_relatorio)


def cmd_prototipar(a):
    _, _, modelo, problemas, _ = carregar_argila(a.argila)
    pendentes = [e for e in problemas.erros if LIGACAO_PENDENTE in e]
    if pendentes and len(pendentes) == len(problemas.erros):
        # números fictícios: o gestor já pode reagir; a ligação vira pendência e o `aprovar` continua recusando
        problemas.erros = []
        for e in pendentes:
            problemas.aviso('[Ligações] ' + e.split(':')[0], 'ligação A CONFIRMAR: o protótipo mostra o painel SEM ela '
                            '(os números desta tabela não abrem pelos cortes dela); confirme com o dono do dado antes do '
                            'aceite')
        print(f'{len(pendentes)} ligação(ões) A CONFIRMAR: o protótipo sai com elas nas pendências; o `aprovar` só passa '
              'depois do `confirmar`.')
    if problemas.erros:
        mostrar_relatorio(problemas, modelo, a.argila)
        print('Protótipo não gerado: corrija os erros acima.')
        return 1
    saida = a.saida or os.path.splitext(a.argila)[0] + '.prototipo.html'
    gravar_texto(saida, prototipo.gerar_html(modelo, problemas, VERSAO))
    print(f'Protótipo: {saida}')
    lembrete('mostre o protótipo ao usuário e peça o aceite explícito; só com o "sim" rode '
              '`deidara.py aprovar argila.json --por NOME`.')
    return 0


def registrar(sub):
    p = sub.add_parser('prototipar', help='protótipo HTML para o gestor validar')
    p.add_argument('argila')
    p.add_argument('-o', '--saida')
    p.set_defaults(func=cmd_prototipar)
