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
    python3 ferramentas/validar_pbip.py PASTA_DO_PROJETO [--mais-recente]

--mais-recente: confere também cada JSON contra a versão MAIS NOVA do mesmo
schema publicada pela Microsoft (pede internet). O Deidara grava versões que
o Power BI Desktop de 2024 em diante abre; esta checagem avisa se o formato
mudou de um jeito que quebraria a migração para as versões novas.
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


API = 'https://api.github.com/repos/microsoft/json-schemas/contents/'


def _versao(v):
    return tuple(int(x) for x in v.split('.'))


def mais_recente(url):
    """O endereço da versão mais nova do mesmo schema (a pasta da versão trocada pela maior publicada)."""
    m = re.match(re.escape(PREFIXO) + r'(.+)/(\d+\.\d+\.\d+)/schema\.json$', url or '')
    if not m:
        return url
    os.makedirs(CACHE, exist_ok=True)
    arq = os.path.join(CACHE, 'versoes-' + hashlib.sha1(m.group(1).encode()).hexdigest() + '.json')
    if not os.path.exists(arq):
        with urllib.request.urlopen(API + m.group(1), timeout=30) as r:
            nomes = [x['name'] for x in json.load(r) if re.match(r'^\d+\.\d+\.\d+$', x['name'])]
        with open(arq, 'w', encoding='utf-8') as f:
            json.dump(nomes, f)
    with open(arq, encoding='utf-8') as f:
        nomes = json.load(f)
    return f'{PREFIXO}{m.group(1)}/{max(nomes, key=_versao)}/schema.json' if nomes else url


def validar_json(pasta, recente=False):
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
            if recente:
                url = mais_recente(url)
                doc = {**doc, '$schema': url}
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


def _campos(x):
    """(Measure|Column, tabela, nome) de cada campo citado no visual (lido como JSON: nome com aspas também)."""
    if isinstance(x, dict):
        for tipo in ('Measure', 'Column'):
            v = x.get(tipo)
            if isinstance(v, dict) and isinstance(v.get('Property'), str):
                ent = ((v.get('Expression') or {}).get('SourceRef') or {}).get('Entity')
                if isinstance(ent, str):
                    yield tipo, ent, v['Property']
        for v in x.values():
            yield from _campos(v)
    elif isinstance(x, list):
        for v in x:
            yield from _campos(v)


def validar_visuais(pasta, tabelas, colunas, medidas):
    """Todo campo usado num visual existe no modelo."""
    erros = []
    for raiz, _, fs in os.walk(pasta):
        for a in fs:
            if a != 'visual.json':
                continue
            with open(os.path.join(raiz, a), encoding='utf-8-sig') as f:
                doc = json.load(f)
            for tipo, ent, prop in _campos(doc):
                ok = prop in medidas if tipo == 'Measure' else (ent, prop) in colunas
                if not ok or ent not in tabelas:
                    erros.append(f'{os.path.basename(raiz)}: {tipo} {ent}.{prop} não existe no modelo')
            erros += [f'{os.path.basename(raiz)}: {x}' for x in _seletores_de_estado(doc)]
    return erros


# o segmentador de botões só reconhece o estado com o prefixo; "selected" e "hover" (formato antigo) passam no
# schema e o Desktop ignora calado (o texto do botão escolhido ficava branco no branco)
ESTADOS_SEM_PREFIXO = {'selected': 'selection:selected', 'hover': 'interaction:hover', 'press': 'interaction:press',
                       'rest': 'interaction:rest'}


def _seletores_de_estado(doc):
    v = doc.get('visual') or {}
    if v.get('visualType') != 'advancedSlicerVisual':
        return []
    out = []
    for obj, entradas in (v.get('objects') or {}).items():
        for e in entradas:
            sid = (e.get('selector') or {}).get('id')
            if sid in ESTADOS_SEM_PREFIXO:
                out.append(f'{obj}: seletor "{sid}" que o Desktop ignora; use "{ESTADOS_SEM_PREFIXO[sid]}"')
    return out


def conferir(pasta):
    """Todos os erros do projeto (schema da Microsoft, TMDL e campos dos visuais). Sem `jsonschema`, falha alto."""
    n, erros = validar_json(pasta)
    nt, tabelas, colunas, medidas, et = validar_tmdl(pasta)
    erros += et + validar_visuais(pasta, tabelas, colunas, medidas)
    if not n:
        erros.append('nenhum JSON do projeto foi conferido contra o schema')
    return erros


def main():
    args = [a for a in sys.argv[1:] if a != '--mais-recente']
    recente = '--mais-recente' in sys.argv[1:]
    if len(args) != 1:
        print(__doc__)
        return 2
    pasta = args[0]
    if not os.path.isdir(pasta):
        print(f'ERRO  {pasta}: pasta não encontrada (passe a pasta do projeto, a que tem o .pbip)')
        return 1
    try:
        n, erros = validar_json(pasta)
        if recente:
            nr, er = validar_json(pasta, recente=True)
            print(f'Contra a versão mais nova de cada schema: {nr} JSON, {len(er)} diferença(s) '
                  '(aviso: o projeto abre com a versão gravada; o Desktop converte ao salvar)')
            for e in er:
                print(f'  AVISO {e}')
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
