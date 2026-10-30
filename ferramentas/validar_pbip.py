#!/usr/bin/env python3
"""
Confere os JSON de um projeto .pbip contra os JSON Schemas públicos da
Microsoft (o endereço que cada arquivo traz em "$schema"), e faz uma checagem
estrutural do TMDL (indentação, nomes citados, referências cruzadas).

É a melhor prova possível sem o Power BI Desktop. Precisa do pacote
`jsonschema` (ferramentas/requisitos-dev.txt). Os schemas que o Deidara gera
vêm junto em ferramentas/schemas/ (licença MIT da Microsoft); um schema novo
é baixado uma vez e fica em ~/.cache/deidara/schemas.

Uso:
    python3 ferramentas/validar_pbip.py PASTA_DO_PROJETO
"""

import hashlib
import json
import os
import re
import sys
import urllib.request

CACHE = os.path.join(os.path.expanduser('~'), '.cache', 'deidara', 'schemas')
GUARDADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schemas')
GITHUB = 'https://raw.githubusercontent.com/microsoft/json-schemas/main/'
PREFIXO = 'https://developer.microsoft.com/json-schemas/'


def baixar(url):
    nome = hashlib.sha1(url.encode()).hexdigest() + '.json'
    guardado = os.path.join(GUARDADOS, nome)
    if os.path.exists(guardado):                  # sem internet: o schema veio com o Deidara
        with open(guardado, encoding='utf-8-sig') as f:
            return json.load(f)
    os.makedirs(CACHE, exist_ok=True)
    arq = os.path.join(CACHE, nome)
    if not os.path.exists(arq):
        real = url.replace(PREFIXO, GITHUB) if url.startswith(PREFIXO) else url
        with urllib.request.urlopen(real, timeout=30) as r:
            dados = r.read()
        with open(arq, 'wb') as f:
            f.write(dados)
    with open(arq, encoding='utf-8-sig') as f:
        return json.load(f)


def validar_json(pasta):
    from jsonschema import Draft7Validator
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT7

    def recuperar(uri):
        return Resource.from_contents(baixar(uri), default_specification=DRAFT7)

    registro = Registry(retrieve=recuperar)
    erros, n = [], 0
    for raiz, _, arquivos in os.walk(pasta):
        for a in arquivos:
            if not a.endswith(('.json', '.pbir', '.pbism', '.pbip')):
                continue
            caminho = os.path.join(raiz, a)
            with open(caminho, encoding='utf-8-sig') as f:
                doc = json.load(f)
            url = doc.get('$schema') if isinstance(doc, dict) else None
            if not url:
                continue
            n += 1
            esquema = baixar(url)
            v = Draft7Validator({**esquema, '$id': url}, registry=registro)
            for e in sorted(v.iter_errors(doc), key=lambda e: list(e.path)):
                erros.append(f'{os.path.relpath(caminho, pasta)}: {"/".join(map(str, e.path)) or "(raiz)"}: {e.message[:300]}')
    return n, erros


def validar_tmdl(pasta):
    """Checagem estrutural: tabulação, nomes e referências entre arquivos."""
    erros, tabelas, colunas, medidas = [], {}, set(), set()
    defs = [os.path.join(r, a) for r, _, fs in os.walk(pasta) for a in fs if a.endswith('.tmdl')]
    nome = r"('(?:[^']|'')+'|[A-Za-z_][A-Za-z0-9_]*)"
    for arq in defs:
        with open(arq, encoding='utf-8') as f:
            linhas = f.read().split('\n')
        atual = None
        for i, l in enumerate(linhas, 1):
            if l.startswith(' '):
                erros.append(f'{os.path.basename(arq)}:{i}: indentação com espaço (TMDL usa tabulação)')
            mt = re.match(r'^table ' + nome + r'\s*$', l)
            if mt:
                atual = mt.group(1).strip("'").replace("''", "'")
                tabelas[atual] = arq
            mc = re.match(r'^\tcolumn ' + nome, l)
            if mc and atual:
                colunas.add((atual, mc.group(1).strip("'").replace("''", "'")))
            mm = re.match(r'^\tmeasure ' + nome, l)
            if mm and atual:
                medidas.add(mm.group(1).strip("'").replace("''", "'"))
    for arq in defs:
        with open(arq, encoding='utf-8') as f:
            texto = f.read()
        for lado, t, c in re.findall(r'\t(fromColumn|toColumn): ' + nome + r'\.' + nome, texto):
            t, c = t.strip("'").replace("''", "'"), c.strip("'").replace("''", "'")
            if (t, c) not in colunas:
                erros.append(f'{os.path.basename(arq)}: {lado} {t}.{c} não existe')
        for t in re.findall(r'^ref table ' + nome, texto, re.M):
            if t.strip("'").replace("''", "'") not in tabelas:
                erros.append(f'{os.path.basename(arq)}: ref table {t} sem arquivo')
    return len(defs), tabelas, colunas, medidas, erros


def validar_visuais(pasta, tabelas, colunas, medidas):
    """Todo campo usado num visual existe no modelo."""
    erros = []
    for raiz, _, fs in os.walk(pasta):
        for a in fs:
            if a != 'visual.json':
                continue
            with open(os.path.join(raiz, a), encoding='utf-8') as f:
                texto = f.read()
            for tipo, ent, prop in re.findall(r'"(Measure|Column)": \{\s*"Expression": \{\s*"SourceRef": \{\s*"Entity": "([^"]+)"'
                                              r'\s*\}\s*\},\s*"Property": "([^"]+)"', texto):
                ok = prop in medidas if tipo == 'Measure' else (ent, prop) in colunas
                if not ok or ent not in tabelas:
                    erros.append(f'{os.path.basename(raiz)}: {tipo} {ent}.{prop} não existe no modelo')
    return erros


def conferir(pasta):
    """Todos os erros do projeto (schema da Microsoft, TMDL e campos dos visuais). Sem `jsonschema`, falha alto."""
    n, erros = validar_json(pasta)
    nt, tabelas, colunas, medidas, et = validar_tmdl(pasta)
    erros += et + validar_visuais(pasta, tabelas, colunas, medidas)
    if not n:
        erros.append('nenhum JSON do projeto foi conferido contra o schema')
    return erros


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    pasta = sys.argv[1]
    try:
        n, erros = validar_json(pasta)
    except ImportError:
        print('Falta o pacote jsonschema: pip install jsonschema (a checagem de TMDL roda mesmo assim).')
        n, erros = 0, []
    nt, tabelas, colunas, medidas, et = validar_tmdl(pasta)
    ev = validar_visuais(pasta, tabelas, colunas, medidas)
    print(f'JSON conferidos contra o schema da Microsoft: {n}' + ('' if n else ' (instale `jsonschema` para conferir)'))
    print(f'TMDL: {nt} arquivo(s), {len(tabelas)} tabela(s), {len(colunas)} coluna(s), {len(medidas)} medida(s)')
    todos = erros + et + ev
    for e in todos:
        print(f'  ERRO  {e}')
    print(('OK' if n else 'OK parcial (só TMDL e campos; os JSON não foram conferidos)') if not todos else f'{len(todos)} erro(s)')
    return 1 if todos else 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
