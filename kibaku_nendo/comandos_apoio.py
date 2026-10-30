"""
O que os comandos do Deidara têm em comum: carregar o argila.json com os catálogos, mostrar o
relatório da validação, achar a aprovação e conferir se o protótipo está em dia.
"""

import os
import sys

from tecnicas.luneta import catalogo
from tecnicas import memory_card
from kibaku_nendo import relato
from kibaku_nendo.especificacao import resolver
from kibaku_nendo.util import ler_json, sha256_arquivo


# pasta do projeto + nome + o arquivo mais fundo do .pbip (visual.json de uma página)
LONGEST_RELATIVO = len('/.Report/definition/pages/0123456789abcdef0123/visuals/0123456789abcdef0123/visual.json')


def lembrete(texto):
    sys.stdout.flush()                       # o lembrete vem depois do que já foi dito, não antes
    print(f'LEMBRETE: {texto}', file=sys.stderr)


# ------------------------------------------------------------------- carga
def carregar_argila(caminho_argila):
    argila = ler_json(caminho_argila)
    base = os.path.dirname(os.path.abspath(caminho_argila))
    fontes = argila.get('fontes') or {}
    if not fontes:
        raise SystemExit('argila.json sem "fontes": rode uma receita (`deidara.py receita`), o `catalogar` e aponte '
                         'o catálogo, ex.: "fontes": {"erp": {"catalogo": "catalogos/erp.json"}}')
    catalogos, caminhos = {}, []
    for nome, cfg in fontes.items():
        if not (cfg or {}).get('catalogo'):
            raise SystemExit(f'fonte {nome} sem "catalogo"')
        c = os.path.join(base, cfg['catalogo'])
        if not os.path.exists(c):
            raise SystemExit(f'catálogo da fonte {nome} não encontrado: {c}')
        try:
            catalogos[nome] = catalogo.carregar(c, nome)
        except ValueError as e:
            raise SystemExit(str(e))
        caminhos.append(c)
    modelo, problemas = resolver(dict(argila, _pasta=base), catalogos)   # _pasta: base do "tema": {"arquivo": ...}
    cartao = memory_card.configuracao().get('pasta')
    if cartao:
        problemas.avisos += memory_card.avisos_do_modelo(cartao, modelo)
    return argila, catalogos, modelo, problemas, caminhos


def mostrar_relatorio(problemas, modelo=None, caminho='argila.json'):
    if modelo is not None:
        print(relato.validacao(modelo, problemas, caminho))
        return
    for e in problemas.erros:
        print(f'  ERRO   {e}')
    for a in problemas.avisos:
        print(f'  AVISO  {a}')


def hashes_da_aprovacao(caminho_argila, caminhos_schema):
    return {'argila_sha256': sha256_arquivo(caminho_argila),
            'catalogos_sha256': {os.path.basename(c): sha256_arquivo(c) for c in caminhos_schema}}


def arquivo_da_aprovacao(caminho_argila):
    raiz, _ = os.path.splitext(caminho_argila)
    return raiz + '.aprovacao.json'


# ---------------------------------------------------------------- comandos
def carregar_catalogos(a):
    """Catálogos (e o modelo, se veio o argila.json) para buscar/relacionar/provar."""
    if getattr(a, 'argila', None):
        _, cats, modelo, _, _ = carregar_argila(a.argila)
        return cats, modelo
    if not getattr(a, 'catalogos', None):
        raise SystemExit('informe --argila argila.json ou --catalogos A.json B.json')
    cats = {}
    for c in a.catalogos:
        try:
            f = catalogo.carregar(c)
        except ValueError as e:
            raise SystemExit(str(e))
        cats[f.nome] = f
    return cats, None


def ponta_da_ligacao(cats, modelo, ref):
    """'Tabela[COLUNA]' (nome no modelo ou origem no catálogo) -> dados da ponta para a receita de prova."""
    import re as _re
    mt = _re.fullmatch(r"\s*'?(.+?)'?\[(.+)\]\s*", ref or '')
    if not mt:
        raise SystemExit(f'"{ref}": use Tabela[COLUNA]')
    tab, col = mt.group(1), mt.group(2)
    cand = []
    if modelo:
        cand = [(t['fonte'], t['origem']) for t in modelo['tabelas']
                if t.get('origem') and (t['nome'].upper() == tab.upper() or t['origem'].upper() == tab.upper())]
    cand += [(n, f.tabela(tab)['nome']) for n, f in cats.items() if f.tabela(tab)]
    if not cand:
        raise SystemExit(f'tabela "{tab}" não está no modelo nem nos catálogos')
    fonte, origem = cand[0]
    oc = cats[fonte].coluna(origem, col)
    if not oc and modelo:                                   # nome da coluna no modelo -> coluna da fonte
        t = next((x for x in modelo['tabelas'] if x.get('origem') == origem and x['fonte'] == fonte), None)
        c = next((c for c in (t or {}).get('colunas', []) if c['nome'].upper() == col.upper() and c['origem']), None)
        if c:
            oc = cats[fonte].coluna(origem, c['origem'])
    if not oc:
        sug = cats[fonte].colunas_parecidas(origem, col)
        raise SystemExit(f'coluna "{col}" não existe em {origem} (fonte {fonte})' + (f'; parecidas: {", ".join(sug)}' if sug else ''))
    cfg = (modelo or {}).get('fontes', {}).get(fonte, {})
    return {'fonte': fonte, 'tipo': cats[fonte].tipo, 'origem': origem, 'coluna': oc['coluna'],
            'rotulo': f'{tab}[{oc["coluna"]}]', 'servidor': cfg.get('servidor', 'SEU_SERVIDOR'),
            'banco': cfg.get('banco', 'SEU_BANCO'), 'esquema': cfg.get('esquema_origem', 'dbo')}


def aprovacao_valida(caminho_argila, caminhos, modelo):
    """(registro de aprovação, None) ou (None, motivo da recusa)."""
    arq = arquivo_da_aprovacao(caminho_argila)
    if not os.path.exists(arq):
        return None, 'ainda não aprovado'
    aprov = ler_json(arq)
    atual = hashes_da_aprovacao(caminho_argila, caminhos)
    if aprov.get('argila_sha256') != atual['argila_sha256'] or \
            aprov.get('catalogos_sha256') != atual['catalogos_sha256']:
        return None, 'o argila.json ou um catálogo mudou depois da aprovação (aprove de novo)'
    return aprov, None


def quem_usa(a):
    if getattr(a, 'por', None):
        return a.por
    r = memory_card._rodar(['git', 'config', 'user.name'])
    return (r.stdout.strip() if r and r.returncode == 0 else '') or 'não informado'


def cartao_ativo():
    cfg = memory_card.configuracao()
    if not cfg.get('pasta') or not os.path.isdir(cfg['pasta']):
        raise SystemExit('Memory Card não configurado nesta máquina: rode `deidara.py memory-card iniciar --repo '
                         f'DONO/{memory_card.NOME_PADRAO}` (o cartão do time; o Deidara usa a seção '
                         f'{memory_card.SECAO}/; precisa do `gh` autenticado e do `git`). Numa sandbox sem '
                         'o `gh` (como o claude.ai), o cartão não funciona: diga isso ao usuário.')
    memory_card._atualizar(cfg['pasta'])
    return cfg['pasta']


def resumo_do_modelo(m):
    return {'tabelas': len(m['tabelas']), 'relacionamentos': len(m['relacionamentos']),
            'medidas': len(m['medidas']), 'paginas': len(m['paginas']),
            'visuais': sum(len(p['visuais']) for p in m['paginas'])}


LIGACAO_PENDENTE = 'ligação sugerida ainda não confirmada'


def mais_novo(arq, *outros):
    return os.path.exists(arq) and all(os.path.getmtime(arq) >= os.path.getmtime(o) for o in outros if os.path.exists(o))


def conferir_resumo(caminho, modelo):
    """O resumo copiado da aba Para aprovar: confere código do protótipo e decisão. None = ok."""
    from tecnicas.c1 import prototipo as _p
    with open(caminho, encoding='utf-8-sig') as f:
        texto = f.read()
    codigo = _p.codigo_do_prototipo(modelo)
    if f'Código: {codigo}' not in texto:
        return (f'O resumo não é deste protótipo (código esperado {codigo}): o gestor aprovou outra versão. '
                'Mande o protótipo atual e peça um resumo novo.')
    if 'Decisão: Aprovo' not in texto:
        return 'O resumo não traz "Decisão: Aprovo": o gestor pediu ajustes. Leia os comentários, ajuste e prototipe de novo.'
    return None
