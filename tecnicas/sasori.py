"""
================================================================================
 SASORI — o parceiro da arte eterna
================================================================================
Nome de referência: Sasori, o parceiro do Deidara na Akatsuki, defendia a arte
que dura para sempre, contra a explosão que dura um instante. Aqui é o que é
permanente e conferido: o dicionário de funções e os padrões de indicador.
Nenhuma função é inventada.

Mesma regra das tabelas e colunas: função DAX que não está no dicionário é
erro. O dicionário traz, de cada função, nome, categoria, assinatura e o link
da documentação oficial da Microsoft, e para as mais usadas em indicadores
uma descrição e um uso em pt-BR (dicionario/dax.json, dicionario/m.json).
Os padrões de indicador (dicionario/padroes.json) dizem onde criar cada
coisa (medida, cálculo visual, grupo de cálculo, Power Query, view SQL).

A pasta dicionario/local/ guarda o dicionário da versão do Power BI do
usuário, gerado pela receita de funções (INFO.FUNCTIONS no DAX, #shared no
M): o que estiver lá também vale.
"""

import difflib
import json
import os
import re

from kibaku_nendo.util import chave

PASTA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dicionario')
_cache = {}


def _ler(nome):
    with open(os.path.join(PASTA, nome), encoding='utf-8') as f:
        return json.load(f)


def funcoes(linguagem='dax'):
    """{NOME: entrada}, juntando o dicionário do Deidara e o local do usuário."""
    if linguagem in _cache:
        return _cache[linguagem]
    base = dict(_ler(f'{linguagem}.json')['funcoes'])
    local = os.path.join(PASTA, 'local', f'{linguagem}.json')
    if os.path.exists(local):
        with open(local, encoding='utf-8') as f:
            for nome, e in json.load(f).get('funcoes', {}).items():
                base.setdefault(nome, {'categorias': ['(local)'], 'url': None, **e})
    _cache[linguagem] = base
    return base


def padroes():
    return _ler('padroes.json')


def visuais():
    return _ler('visuais.json')


def estilos():
    return _ler('estilos.json')


def paletas():
    return _ler('paletas.json')


def visuais_para(termo):
    """Técnicas de visual cujo id, nome ou termos batem com alguma palavra do assunto."""
    t = chave(termo)
    out = []
    for v in visuais()['visuais']:
        alvo = chave(' '.join([v['id'], v['nome'], ' '.join(v.get('termos', []))]))
        if not t or any(w in alvo for w in t.split()):
            out.append(v)
    return out


_CHAMADA = re.compile(r"(?<![\w.\]'\[])([A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)*)\s*\(")


def funcoes_usadas(dax):
    """Nomes de função chamados num DAX (fora de strings, colunas e medidas)."""
    texto = re.sub(r'"(?:[^"]|"")*"', '""', dax)
    texto = re.sub(r"'(?:[^']|'')*'", "''", texto)
    texto = re.sub(r'\[(?:[^\]]|\]\])*\]', '[]', texto)
    texto = re.sub(r'//[^\n]*|--[^\n]*|/\*.*?\*/', '', texto, flags=re.S)
    return [n for n in _CHAMADA.findall(texto) if n.upper() not in ('VAR', 'RETURN')]


def desconhecidas(dax, linguagem='dax'):
    """[(função, [parecidas])] chamadas no DAX que não estão no dicionário."""
    todas = funcoes(linguagem)
    upper = {k.upper(): k for k in todas}
    out = []
    for n in funcoes_usadas(dax):
        if n.upper() not in upper and n not in [x for x, _ in out]:
            out.append((n, difflib.get_close_matches(n.upper(), list(upper), n=3, cutoff=0.7)))
    return out


def buscar(termo, linguagem='dax', limite=15):
    linguagem = linguagem or 'dax'
    t = chave(termo)
    out = []
    for nome, e in funcoes(linguagem).items():
        texto = chave(' '.join([nome, ' '.join(e.get('categorias') or []), e.get('descricao', ''), e.get('uso', '')]))
        if all(p in texto for p in t.split()):
            out.append((0 if t in chave(nome) else 1 if e.get('descricao') else 2, nome, e))
    return [(n, e) for _, n, e in sorted(out, key=lambda x: (x[0], x[1]))][:limite]


def ver(nome, linguagem=None):
    for ling in ([linguagem] if linguagem else ['dax', 'm']):
        for k, e in funcoes(ling).items():
            if k.upper() == nome.upper():
                return ling, k, e
    return None


def padroes_para(termo):
    t = chave(termo)
    out = []
    for p in padroes()['padroes']:
        alvo = chave(' '.join([p['id'], p['nome'], ' '.join(p.get('termos', []))]))
        if not t or any(w in alvo for w in t.split()):
            out.append(p)
    return out
