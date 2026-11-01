"""
Os comandos do Katsu: o aceite e o que mudou desde ele.
"""

import datetime
import os
import sys
from kibaku_nendo import VERSAO
from tecnicas import katsu as governanca
from kibaku_nendo.especificacao import distorcoes
from kibaku_nendo.util import gravar_json, ler_json, sha256_arquivo
from tecnicas.comum import (arquivo_da_aprovacao, carregar_argila, conferir_resumo,
                                         hashes_da_aprovacao, mais_novo, mostrar_relatorio)


def cmd_aprovar(a):
    _, _, modelo, problemas, caminhos = carregar_argila(a.argila)
    if problemas.erros:
        mostrar_relatorio(problemas, modelo, a.argila)
        print('Não dá para aprovar com erro de validação.')
        return 1
    if modelo['pendencias']:
        print('Não dá para aprovar com indicador sem definição (o gestor estaria aprovando um número sem significado):')
        for x in modelo['pendencias']:
            print(f'  · {x}')
        return 1
    prot = os.path.splitext(a.argila)[0] + '.prototipo.html'
    if not mais_novo(prot, a.argila, *caminhos):
        if not a.sem_prototipo:
            print('Não dá para aprovar: o protótipo não existe ou é anterior a esta versão do argila.json, e o gestor '
                  f'estaria aprovando algo que não viu. Gere (`deidara.py prototipar {a.argila}`), mostre e aprove de '
                  'novo. (Só se o gestor aprovou sem protótipo, de propósito: --sem-prototipo.)')
            return 1
        print('Atenção: aprovado SEM protótipo em dia (--sem-prototipo); isso fica registrado.', file=sys.stderr)
    graves = distorcoes(problemas.avisos)
    if graves and not a.aceito_distorcao:
        print(f'Não dá para aprovar: {len(graves)} número(s) sairiam distorcidos (o corte filtra só parte da conta):')
        for x in graves:
            print(f'  · {x}')
        print('Corrija o argila.json (tire o corte ou troque a medida) ou, se o gestor decidiu manter sabendo disso, '
              'aprove com --aceito-distorcao "motivo" (fica registrado).')
        return 1
    arq = arquivo_da_aprovacao(a.argila)
    anterior = ler_json(arq) if os.path.exists(arq) else None
    retrato = governanca.retrato(modelo)
    mudancas = governanca.diferencas(anterior['retrato'], retrato) if anterior and anterior.get('retrato') else []
    historico = (anterior or {}).get('historico', [])
    if a.resumo:
        conferido = conferir_resumo(a.resumo, modelo)
        if conferido:
            print(conferido)
            return 1
    reg = {'projeto': modelo['projeto'], 'versao': modelo['versao'], 'aprovado_por': a.por,
           'prototipo_sha256': sha256_arquivo(prot) if os.path.exists(prot) else None,
           'sem_prototipo': bool(a.sem_prototipo and not mais_novo(prot, a.argila, *caminhos)),
           'em': datetime.datetime.now().strftime('%d/%m/%Y %H:%M'), 'observacao': a.observacao or '',
           'avisos_aceitos': problemas.avisos, 'deidara': VERSAO, **hashes_da_aprovacao(a.argila, caminhos)}
    if graves:
        reg['distorcao_aceita'] = {'motivo': a.aceito_distorcao, 'avisos': graves}
    if anterior and (mudancas or not historico):
        historico = historico + [{'versao': reg['versao'], 'em': reg['em'], 'aprovado_por': a.por,
                                  'observacao': reg['observacao'], 'mudancas': mudancas}]
    elif not anterior:
        historico = [{'versao': reg['versao'], 'em': reg['em'], 'aprovado_por': a.por,
                      'observacao': reg['observacao'], 'mudancas': ['primeira versão aprovada']}]
    reg['historico'], reg['retrato'] = historico, retrato
    gravar_json(arq, reg)
    print(f'Katsu! Aprovado por {a.por} em {reg["em"]} ({len(problemas.avisos)} aviso(s) aceito(s)). '
          'A geração (`gerar`) está liberada.')
    for x in mudancas:
        print(f'  MUDOU  {x}')
    print(f'Registro: {arquivo_da_aprovacao(a.argila)}')
    return 0


def cmd_diff(a):
    """O que mudou no argila.json desde a última aprovação (ou entre dois argila.json)."""
    _, _, modelo, problemas, _ = carregar_argila(a.argila)
    if a.contra:
        _, _, outro, _, _ = carregar_argila(a.contra)
        antes, rotulo = governanca.retrato(outro), a.contra
    else:
        arq = arquivo_da_aprovacao(a.argila)
        if not os.path.exists(arq):
            print('Sem aprovação para comparar: use --contra OUTRO_ARGILA.json')
            return 1
        aprov = ler_json(arq)
        antes, rotulo = aprov.get('retrato') or {}, f'aprovação de {aprov.get("em")} ({aprov.get("aprovado_por")})'
    mud = governanca.diferencas(antes, governanca.retrato(modelo))
    print(f'Comparando com: {rotulo}')
    for x in mud:
        print(f'  {x}')
    print('Nada mudou para quem consome o painel.' if not mud else f'{len(mud)} mudança(s).')
    return 0


def registrar(sub):
    ap_ = sub.add_parser('aprovar', help='registra o "sim" do gestor')
    ap_.add_argument('argila')
    ap_.add_argument('--por', required=True)
    ap_.add_argument('--observacao')
    ap_.add_argument('--resumo', help='o resumo copiado da aba "Para aprovar" (confere versão e decisão)')
    ap_.add_argument('--sem-prototipo', action='store_true', help='o gestor aprovou sem protótipo, de propósito')
    ap_.add_argument('--aceito-distorcao', metavar='MOTIVO',
                     help='o gestor mantém um corte que filtra só parte da conta, sabendo disso (fica registrado)')
    ap_.set_defaults(func=cmd_aprovar)
    df = sub.add_parser('diff', help='o que mudou desde a aprovação')
    df.add_argument('argila')
    df.add_argument('--contra')
    df.set_defaults(func=cmd_diff)
