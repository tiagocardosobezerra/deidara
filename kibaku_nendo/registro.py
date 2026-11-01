"""
O que o motor pede às técnicas, sem importá-las.

O motor (`kibaku_nendo/`) resolve e confere a especificação; as técnicas (`tecnicas/`) dependem dele, nunca o
contrário. Algumas contas do motor precisam do que uma técnica sabe: o dicionário de funções (Sasori), a
estatística (C4 Karura), a frase de leitura (Tobi), a geometria do layout (Arte), o tour (C1), a galeria de
terceiros, a prova e os tokens da busca (Luneta). O motor pede pelo papel (`usar('estatistica')`); quem diz qual
módulo faz cada papel é o pacote das técnicas, ao ser importado (`tecnicas/__init__.py` chama `registrar`).

Papel pedido e ninguém registrado é erro de instalação, dito com o nome do papel.
"""

import importlib

PACOTE_DAS_TECNICAS = 'tecnicas'
_registro = {}


def registrar(papel, modulo):
    """`modulo`: o módulo ou o caminho dele ("tecnicas.c4"), importado só na primeira vez que o papel é pedido."""
    _registro[papel] = modulo


def usar(papel):
    if papel not in _registro:
        importlib.import_module(PACOTE_DAS_TECNICAS)     # o pacote se registra ao ser importado
    alvo = _registro.get(papel)
    if alvo is None:
        raise LookupError(f'nenhuma técnica registrada para "{papel}" (pacote {PACOTE_DAS_TECNICAS} incompleto?)')
    if isinstance(alvo, str):
        alvo = _registro[papel] = importlib.import_module(alvo)
    return alvo
