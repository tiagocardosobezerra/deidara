#!/usr/bin/env python3
"""
Traz para terceiros/ o conteúdo aberto (licença MIT) que o Deidara usa: funções DAX (daxlib), modelos Deneb
(Vega e Vega-Lite), calendários e feriados (Bravo) e SVG. Só arquivo de texto (modelo, função, documentação,
licença): .pbix, imagem e vídeo ficam de fora.

Uso (pede git e internet; rode na pasta da skill):
    python3 ferramentas/atualizar_terceiros.py [--de PASTA_COM_OS_CLONES]

Cada fonte vai para terceiros/<id>/ com a LICENSE original e um ORIGEM.md (repositório, commit, data). Repositório
sem licença ou com licença que não deixa copiar para um projeto MIT (GPL) não entra: ver LICENCAS-DE-TERCEIROS.md.
"""

import datetime
import os
import re
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(RAIZ, 'terceiros')
TEXTO = ('.json', '.md', '.txt', '.tmdl', '.daxlib', '.svg', '.vl', '.vg')

FONTES = [
    {'id': 'daxlib', 'repo': 'daxlib/daxlib', 'licenca': 'MIT', 'versao_mais_nova': 'packages',
     'sobre': 'Funções DAX (UDF) da comunidade: SVG, IBCS, cascata, minigráfico, estatística, calendário.'},
    {'id': 'deneb-vega-templates', 'repo': 'avatorl/Deneb-Vega-Templates', 'licenca': 'MIT',
     'sobre': 'Modelos Deneb em Vega, pelo vocabulário visual do Financial Times (Andrzej Leszkiewicz).'},
    {'id': 'dataviz-vega', 'repo': 'avatorl/DataViz-Vega', 'licenca': 'MIT',
     'sobre': 'Visualizações em Vega do mesmo autor (Andrzej Leszkiewicz).'},
    {'id': 'deneb-showcase', 'repo': 'PBI-David/Deneb-Showcase', 'licenca': 'MIT',
     'sobre': 'Exemplos avançados de Deneb (David Bacci): mapa de calor de calendário, waffle, gantt, sankey...'},
    {'id': 'deneb-vega-showcase', 'repo': 'Flynnxx1/Deneb-Vega-Showcase', 'licenca': 'MIT',
     'sobre': 'Exemplos de Vega e Deneb (Flynnxx1).'},
    {'id': 'powerbi-deneb', 'repo': 'CSalcedoDataBI/PowerBI-Deneb', 'licenca': 'MIT',
     'sobre': 'Modelos Deneb em Vega-Lite com .pbip de exemplo (Cristobal Salcedo).'},
    {'id': 'bravo-calendario', 'repo': 'sql-bi/Bravo', 'licenca': 'MIT', 'subpasta': 'src/Assets/ManageDates/Templates',
     'sobre': 'Modelos de calendário, inteligência de tempo e feriados de vários países, Brasil incluído (SQLBI).'},
    {'id': 'powerbi-svg', 'repo': 'jurgenfolz/PowerBI-SVG', 'licenca': 'MIT',
     'sobre': 'SVG para Power BI: fronteiras de países e bandeiras (Jurgen Folz).'},
    {'id': 'deneb-metadados', 'repo': 'deneb-viz/deneb', 'licenca': 'MIT', 'subpasta': 'packages/template-usermeta',
     'sobre': 'O formato dos metadados de um modelo Deneb (do código do próprio visual).'},
]


def _git(*args, cwd=None):
    return subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def _versao(v):
    return tuple(int(x) if x.isdigit() else -1 for x in re.split(r'[.\-]', v))


def _escolher(origem, fonte):
    """Os arquivos de texto da fonte (no daxlib, só a versão mais nova de cada pacote)."""
    base = os.path.join(origem, fonte.get('subpasta', ''))
    for raiz, pastas, arquivos in os.walk(base):
        pastas[:] = [p for p in pastas if p != '.git']
        if fonte.get('versao_mais_nova') and os.path.basename(os.path.dirname(raiz)) in 'abcdefghijklmnopqrstuvwxyz' \
                and pastas and all(re.match(r'^\d', p) for p in pastas):
            pastas[:] = [max(pastas, key=_versao)]        # packages/<letra>/<pacote>/<versão>: só a última
        for a in arquivos:
            if a.lower().endswith(TEXTO) or a.upper().startswith('LICENSE'):
                yield os.path.join(raiz, a), os.path.relpath(os.path.join(raiz, a), base)


def copiar(fonte, origem):
    alvo = os.path.join(DESTINO, fonte['id'])
    shutil.rmtree(alvo, ignore_errors=True)
    n = 0
    for de, rel in _escolher(origem, fonte):
        para = os.path.join(alvo, rel)
        os.makedirs(os.path.dirname(para), exist_ok=True)
        shutil.copyfile(de, para)
        n += 1
    lic = next((os.path.join(origem, x) for x in os.listdir(origem) if x.upper().startswith('LICENSE')), None)
    if lic:
        shutil.copyfile(lic, os.path.join(alvo, 'LICENSE'))
    commit = _git('rev-parse', 'HEAD', cwd=origem) if os.path.isdir(os.path.join(origem, '.git')) else '?'
    with open(os.path.join(alvo, 'ORIGEM.md'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(f'# {fonte["id"]}\n\n{fonte["sobre"]}\n\n'
                f'- Repositório: https://github.com/{fonte["repo"]}'
                + (f' (pasta `{fonte["subpasta"]}`)' if fonte.get('subpasta') else '') + '\n'
                f'- Licença: {fonte["licenca"]} (texto em `LICENSE`, mantido como veio)\n'
                f'- Commit: `{commit}`\n- Copiado em: {datetime.date.today():%d/%m/%Y}\n'
                '- Só arquivos de texto; .pbix, imagens e vídeos ficaram no repositório original.\n')
    return n


def main():
    args = sys.argv[1:]
    clones = args[args.index('--de') + 1] if '--de' in args else None
    tmp = None if clones else tempfile.mkdtemp(prefix='deidara-terceiros-')
    try:
        for fonte in FONTES:
            nome = fonte['repo'].replace('/', '_')
            origem = os.path.join(clones or tmp, nome)
            if not os.path.isdir(origem):
                _git('clone', '-q', '--depth', '1', f'https://github.com/{fonte["repo"]}.git', origem)
            print(f'{fonte["id"]:<22} {copiar(fonte, origem):>5} arquivo(s)  ({fonte["repo"]}, {fonte["licenca"]})')
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
    print('Agora: python3 ferramentas/catalogar_terceiros.py (refaz o terceiros/catalogo.json)')
    return 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
