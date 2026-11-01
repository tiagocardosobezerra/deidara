"""
================================================================================
 GALERIA — o que a comunidade abriu e o Deidara trouxe (terceiros/)
================================================================================
Modelos Deneb (Vega e Vega-Lite), funções DAX do daxlib, calendários e feriados do Bravo e SVG, todos com
licença MIT, cada um com a LICENSE e a origem em terceiros/<fonte>/. O catálogo (terceiros/catalogo.json) diz o
que cada item pede; aqui ficam a busca, a montagem do modelo Deneb com os campos do painel e as funções DAX
que entram no modelo.
"""

import json
import os
import re

from kibaku_nendo.util import chave, sem_acento

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CACHE = {}
# no pacote do claude.ai (máximo de 200 arquivos), os dados de terceiros/ vão juntos neste arquivo: {caminho: texto}
PACOTE = os.path.join('terceiros', 'pacote.json')


def _pacote():
    if 'pacote' not in _CACHE:
        arq = os.path.join(RAIZ, PACOTE)
        _CACHE['pacote'] = {}
        if os.path.exists(arq):
            with open(arq, encoding='utf-8') as f:
                _CACHE['pacote'] = json.load(f)
    return _CACHE['pacote']


def _existe(rel):
    return os.path.exists(os.path.join(RAIZ, rel)) or rel.replace(os.sep, '/') in _pacote()


def _texto(rel):
    """O arquivo de terceiros/ (solto, no repositório; ou dentro do pacote.json, no pacote da skill)."""
    arq = os.path.join(RAIZ, rel)
    if os.path.exists(arq):
        with open(arq, encoding='utf-8-sig') as f:
            return f.read()
    return _pacote()[rel.replace(os.sep, '/')]


def json_de(rel):
    """Um JSON de terceiros/ (solto ou dentro do pacote.json), lido uma vez só."""
    if rel not in _CACHE:
        _CACHE[rel] = json.loads(_texto(rel))
    return _CACHE[rel]


def catalogo():
    if 'cat' not in _CACHE:
        arq = os.path.join(RAIZ, 'terceiros', 'catalogo.json')
        if not os.path.exists(arq):
            _CACHE['cat'] = []
        else:
            with open(arq, encoding='utf-8') as f:     # só o que está instalado (o pacote leva menos que o repositório)
                _CACHE['cat'] = [x for x in json.load(f)['itens'] if _existe(x['caminho'])]
    return _CACHE['cat']


def item(ident):
    return next((x for x in catalogo() if chave(x['id']) == chave(ident or '')), None)


def _palavras(t):
    return set(re.findall(r'[a-z0-9]+', sem_acento(t or '').lower()))


def buscar(termo='', tipo=None):
    """Os itens que batem com o termo (em português ou inglês), os prontos para usar primeiro."""
    quer = _palavras(termo)
    out = []
    for x in catalogo():
        if tipo and x['tipo'] != tipo:
            continue
        alvo = _palavras(' '.join([x['id'], x['nome'], x.get('descricao', ''), x.get('etiquetas', ''),
                                   ' '.join(f['nome'] for f in x.get('funcoes', []))]))
        pontos = len(quer & alvo)
        if not quer or pontos:
            out.append((-pontos, not x.get('pronto_para_usar', True), '_drafts' in x['id'], x['id'], x))
    return [x for *_, x in sorted(out, key=lambda t: t[:4])]


# ======================================================================= Deneb
def spec_deneb(ident, nomes_por_campo):
    """(spec em texto, provider, config em texto) do modelo, com cada marcador "__i__" trocado pelo nome do campo
    do painel. `nomes_por_campo`: {nome do campo no modelo (ex.: "Period"): nome no painel (ex.: "Mês/Ano")}."""
    x = item(ident)
    spec = json.loads(_texto(x['caminho']))
    um = spec.get('usermeta') or {}
    troca = {c['key']: nomes_por_campo[c['name']] for c in um.get('dataset') or [] if c['name'] in nomes_por_campo}
    config = spec.pop('config', {}) or {}
    info = um.get('information') or {}
    info.pop('previewImageBase64PNG', None)           # a prévia fica no catálogo; o visual não precisa dela

    def trocar(v):
        if isinstance(v, str):
            for k, n in troca.items():
                v = v.replace(k, n)
            return v
        if isinstance(v, list):
            return [trocar(i) for i in v]
        if isinstance(v, dict):
            return {kk: trocar(vv) for kk, vv in v.items()}
        return v
    spec = trocar(spec)
    spec.setdefault('data', [{'name': 'dataset'}]) if x['provider'] == 'vega' else None
    return (json.dumps(spec, ensure_ascii=False), 'vegaLite' if x['provider'] == 'vegaLite' else 'vega',
            json.dumps(config, ensure_ascii=False))


def previa_deneb(ident):
    """A imagem de prévia que o autor gravou no modelo (data URI PNG), para o protótipo."""
    x = item(ident)
    if not x or not x.get('previa'):
        return None
    return ((json.loads(_texto(x['caminho'])).get('usermeta') or {}).get('information') or {}).get('previewImageBase64PNG')


# ==================================================================== feriados
# nomes em português para os feriados nacionais do Brasil (o Bravo traz em inglês)
NOMES_BR = {"New Year's Day": 'Confraternização Universal', "Tiradentes' Day": 'Tiradentes', 'Good Friday': 'Sexta-feira Santa',
            'Labour Day': 'Dia do Trabalho', 'Independence Day': 'Independência', 'Lady of Aparecida': 'Nossa Senhora Aparecida',
            "All Soul's Day'": 'Finados', "Republic Day'": 'Proclamação da República', 'Christmas Day': 'Natal'}
# o que a lei mudou depois do modelo do Bravo (Lei 14.759/2023: Dia Nacional de Zumbi e da Consciência Negra)
EXTRAS_BR = [{'MonthNumber': 11, 'DayNumber': 20, 'WeekDayNumber': 0, 'OffsetWeek': 0, 'OffsetDays': 0,
              'HolidayName': 'Consciência Negra (Lei 14.759/2023)'}]


def feriados(pais):
    """As regras de feriado nacional de um país (código ISO de 2 letras), do modelo do Bravo (SQLBI, MIT)."""
    rel = 'terceiros/bravo-calendario/HolidaysDefinition.json'
    if not _existe(rel):
        return []
    regras = [dict(h) for h in json.loads(_texto(rel))['Holidays'] if h.get('IsoCountry') == (pais or '').upper()]
    if (pais or '').upper() == 'BR':
        for h in regras:
            h['HolidayName'] = NOMES_BR.get(h['HolidayName'], h['HolidayName'])
        regras += [dict(x) for x in EXTRAS_BR]
    return regras


# ================================================================= funções DAX
def funcoes_tmdl(pacotes):
    """O texto TMDL das funções dos pacotes (na ordem) e {nome da função: pacote}."""
    textos, nomes = [], {}
    for p in pacotes:
        x = item(p)
        texto = _texto(x['caminho']).replace('\r\n', '\n').strip('\n')
        textos.append(f'/// ---- {x["id"]} {x.get("versao") or ""} ({x["autor"]}), daxlib.org, licença MIT ----\n' + texto)
        for fn in x.get('funcoes', []):
            nomes[fn['nome']] = x['id']
    return '\n\n'.join(textos) + '\n', nomes
