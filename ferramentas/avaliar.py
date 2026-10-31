#!/usr/bin/env python3
"""
O placar do motor do Deidara num exemplo: o esboço monta o que o pedido pede, e o validar pega cada erro de
indicador que muda o número sem ninguém ver (as "armadilhas"). Complementa o Ōnoki (que mede só a busca de
tabelas): aqui é o caminho inteiro, do pedido ao aviso.

Uso:
    python3 ferramentas/avaliar.py exemplos/aurora/avaliacao.json

O arquivo de casos fica ao lado do argila.json e dos catálogos do exemplo. Cada armadilha muda o argila.json
("set", "pop", "add", "replace" num caminho como "medidas.Turnover.base_meta", em que o nome escolhe o item da
lista) e diz o trecho do erro ou do aviso que precisa aparecer. Sai com código 1 se algum caso falhar.
"""

import copy
import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from kibaku_nendo.especificacao import resolver  # noqa: E402
from tecnicas.luneta import catalogo  # noqa: E402


def _filho(atual, parte):
    if isinstance(atual, list):
        return next(x for x in atual if isinstance(x, dict) and parte in (x.get('nome'), x.get('id')))
    return atual[parte]


def mudar(argila, ops):
    """Aplica as mudanças de uma armadilha numa cópia do argila.json."""
    a = copy.deepcopy(argila)
    for op, caminho, *valor in ops:
        partes = caminho.split('.')
        alvo = a
        for parte in partes[:-1]:
            alvo = _filho(alvo, parte)
        ultima = partes[-1]
        if op == 'set':
            alvo[ultima] = valor[0]
        elif op == 'pop':
            alvo.pop(ultima, None)
        elif op == 'add':
            _filho(alvo, ultima).append(valor[0]) if isinstance(alvo, list) else alvo[ultima].append(valor[0])
        elif op == 'replace':
            lista = alvo if isinstance(alvo, list) else None
            if lista is None:
                raise ValueError('replace precisa de um item de lista: "medidas.<nome>"')
            i = next(k for k, x in enumerate(lista) if x.get('nome') == ultima)
            lista[i] = valor[0]
        else:
            raise ValueError(f'operação desconhecida: {op}')
    return a


def _replace_pai(argila, ops):
    """"replace" com caminho "medidas.X": troca o item X da lista "medidas"."""
    out = []
    for op, caminho, *valor in ops:
        if op == 'replace':
            pai, nome = caminho.rsplit('.', 1)
            out.append(('replace_item', pai, nome, valor[0]))
        else:
            out.append((op, caminho, *valor))
    a = copy.deepcopy(argila)
    simples = [x for x in out if x[0] != 'replace_item']
    a = mudar(a, simples)
    for _, pai, nome, valor in [x for x in out if x[0] == 'replace_item']:
        lista = a
        for parte in pai.split('.'):
            lista = _filho(lista, parte)
        i = next(k for k, x in enumerate(lista) if x.get('nome') == nome)
        lista[i] = valor
    return a


def avaliar(arquivo):
    pasta = os.path.dirname(os.path.abspath(arquivo))
    with open(arquivo, encoding='utf-8') as f:
        casos = json.load(f)
    with open(os.path.join(pasta, 'argila.json'), encoding='utf-8') as f:
        base = json.load(f)
    cats = {n: catalogo.carregar(os.path.join(pasta, cfg['catalogo']), n) for n, cfg in base['fontes'].items()}
    linhas, ok, total = [], 0, 0

    from tecnicas import te_no_kuchi
    for c in casos.get('esbocos') or []:
        total += 1
        argila, notas = te_no_kuchi.esbocar(cats, c['pedido'], briefing=c.get('briefing'))
        argila['fontes'] = base['fontes']
        for r in argila['relacionamentos']:
            if 'declarada' in r:
                r['declarada']['por'] = 'avaliação'
        _, p = resolver(argila, cats)
        nomes = {m['nome'] for m in argila['medidas']}
        paginas = {pg['nome'] for pg in argila['paginas']}
        tipos = {v['tipo'] for pg in argila['paginas'] for v in pg['visuais']}
        faltas = ([f'medida {x}' for x in c.get('medidas', []) if x not in nomes]
                  + [f'página {x}' for x in c.get('paginas', []) if x not in paginas]
                  + [f'visual {x}' for x in c.get('visuais', []) if x not in tipos]
                  + [f'erro: {e}' for e in p.erros if not c.get('aceita_erro') or c['aceita_erro'] not in e]
                  + [f'nota indevida "{x}"' for x in c.get('sem_nota', []) if any(x in n for n in notas)]
                  + [f'aviso indevido "{x}"' for x in c.get('sem_aviso', []) if any(x in a for a in p.avisos)]
                  + [f'{n} não é {t}' for n, t in (c.get('tipos') or {}).items()
                     if next((m.get('tipo') for m in argila['medidas'] if m['nome'] == n), None) != t])
        ok += not faltas
        linhas.append(('✓' if not faltas else '✗') + f' esboço · {c["nome"]}' + (f' — falta {"; ".join(faltas)}' if faltas else ''))

    for c in casos.get('armadilhas') or []:
        total += 1
        try:
            argila = _replace_pai(base, c.get('mudar') or [])
            _, p = resolver(argila, cats)
            lista, alvo = (p.erros, c['erro']) if 'erro' in c else (p.avisos, c['aviso'])
            pegou = any(alvo in x for x in lista)
            motivo = '' if pegou else f' — esperava {"erro" if "erro" in c else "aviso"} com "{alvo}"'
        except Exception as e:                       # caso mal escrito também é falha, com o motivo
            pegou, motivo = False, f' — o caso não rodou: {type(e).__name__}: {e}'
        ok += pegou
        linhas.append(('✓' if pegou else '✗') + f' armadilha · {c["nome"]}{motivo}')
    return ok, total, linhas


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    ok, total, linhas = avaliar(sys.argv[1])
    for x in linhas:
        print(x)
    print(f'\nPlacar: {ok} de {total} ({ok / total:.0%})' if total else 'Nenhum caso.')
    return 0 if ok == total else 1


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
