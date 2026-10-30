"""
================================================================================
 TREINO — o olho que o Deidara treinou
================================================================================
Nome de referência: depois de perder para o Sharingan, o Deidara treinou o olho
esquerdo até enxergar o que antes o enganava. Aqui a Luneta aprende com quem a
corrige, nesta instalação:

- quando a pessoa troca as tabelas do esboço (`esbocar --tabelas`), as palavras
  do pedido passam a puxar aquelas tabelas na busca;
- quando o dono do dado confirma uma ligação sugerida (`confirmar`), ela volta
  com confiança alta nos próximos esboços; quando ele a recusa (`--remover`),
  ela deixa de ser sugerida.

Só estrutura: palavras do pedido, nomes de tabela e de coluna, nunca dado. O
treino fica em dicionario/local/treino.json, fora do git e do pacote da skill.
DEIDARA_TREINO aponta outro arquivo; DEIDARA_TREINO=- desliga.
"""

import json
import os

from kibaku_nendo.util import chave

ARQUIVO = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                       'dicionario', 'local', 'treino.json')
BONUS_POR_VEZ, BONUS_MAXIMO = 4.0, 12.0


def _arquivo():
    return os.environ.get('DEIDARA_TREINO') or ARQUIVO


def ler():
    arq = _arquivo()
    if arq == '-' or not os.path.exists(arq):
        return {'termos': {}, 'ligacoes': {}}
    with open(arq, encoding='utf-8') as f:
        dados = json.load(f)
    dados.setdefault('termos', {})
    dados.setdefault('ligacoes', {})
    return dados


def _gravar(dados):
    arq = _arquivo()
    if arq == '-':
        return
    os.makedirs(os.path.dirname(os.path.abspath(arq)), exist_ok=True)
    with open(arq, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def aprender_tabelas(palavras, tabelas):
    """`palavras`: os termos do pedido (já sem as vazias); `tabelas`: as origens que a pessoa escolheu."""
    dados = ler()
    for p in palavras:
        alvo = dados['termos'].setdefault(p, {})
        for t in tabelas:
            alvo[chave(t)] = alvo.get(chave(t), 0) + 1
    _gravar(dados)


def bonus(palavras, origem):
    """Pontos a mais para a tabela que a pessoa já escolheu para estas palavras."""
    termos = ler()['termos']
    vezes = sum(termos.get(p, {}).get(chave(origem), 0) for p in palavras)
    return min(BONUS_MAXIMO, BONUS_POR_VEZ * vezes)


def _ligacao(origem_de, campo_de, origem_para, campo_para):
    return f'{chave(origem_de)}.{chave(campo_de)}->{chave(origem_para)}.{chave(campo_para)}'


def aprender_ligacao(origem_de, campo_de, origem_para, campo_para, confirmada):
    dados = ler()
    k = _ligacao(origem_de, campo_de, origem_para, campo_para)
    reg = dados['ligacoes'].setdefault(k, {'confirmada': 0, 'recusada': 0})
    reg['confirmada' if confirmada else 'recusada'] += 1
    _gravar(dados)


def veredito(origem_de, campo_de, origem_para, campo_para):
    """'confirmada', 'recusada' ou None (o dono do dado ainda não disse)."""
    reg = ler()['ligacoes'].get(_ligacao(origem_de, campo_de, origem_para, campo_para))
    if not reg or reg['confirmada'] == reg['recusada']:
        return None
    return 'confirmada' if reg['confirmada'] > reg['recusada'] else 'recusada'
