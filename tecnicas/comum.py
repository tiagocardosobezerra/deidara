"""
O que os comandos do Deidara têm em comum: carregar o argila.json com os catálogos, mostrar o
relatório da validação, achar a aprovação e conferir se o protótipo está em dia.
"""

import json
import os
import re
import sys

from tecnicas.luneta import catalogo
from tecnicas import katsu as governanca
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
    r = memory_card.rodar(['git', 'config', 'user.name'])
    return (r.stdout.strip() if r and r.returncode == 0 else '') or 'não informado'


def cartao_ativo():
    cfg = memory_card.configuracao()
    if not cfg.get('pasta') or not os.path.isdir(cfg['pasta']):
        raise SystemExit('Memory Card não configurado nesta máquina: rode `deidara.py memory-card iniciar --repo '
                         f'DONO/{memory_card.NOME_PADRAO}` (o cartão do time; o Deidara usa a seção '
                         f'{memory_card.SECAO}/; precisa do `gh` autenticado e do `git`). Numa sandbox sem '
                         'o `gh` (como o claude.ai), o cartão não funciona: diga isso ao usuário.')
    memory_card.atualizar(cfg['pasta'])
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


def cmd_validar(a):
    _, _, modelo, problemas, _ = carregar_argila(a.argila)
    if a.json:
        print(json.dumps({'ok': not problemas.erros, 'erros': problemas.erros, 'avisos': problemas.avisos,
                          'resumo': resumo_do_modelo(modelo)}, ensure_ascii=False, indent=2))
    else:
        print(relato.validacao(modelo, problemas, a.argila))
    return 1 if problemas.erros else 0


def cmd_situacao(a):
    """Onde o projeto está no fluxo e qual é o próximo passo."""
    if not os.path.exists(a.argila):
        print(f'{a.argila} não existe. Para começar: `deidara.py novo PASTA` (ver `deidara.py` sem argumentos).')
        return 1
    passos = []

    def passo(ok, texto, proximo=None):
        passos.append((ok, texto, proximo))
        return ok

    try:
        argila, cats, modelo, problemas, caminhos = carregar_argila(a.argila)
    except SystemExit as e:
        print(f'✗ fontes: {e}')
        print('Próximo passo: rode a receita da fonte e o `catalogar` (ver referencias/fontes.md).')
        return 1
    passo(True, f'fontes catalogadas: {", ".join(f"{n} ({c.tipo})" for n, c in cats.items())}')
    prot = os.path.splitext(a.argila)[0] + '.prototipo.html'
    pendentes = [e for e in problemas.erros if LIGACAO_PENDENTE in e]
    if pendentes and len(pendentes) == len(problemas.erros):   # o protótipo já sai; o aceite espera a confirmação
        passo(True, f'validação: só falta confirmar {len(pendentes)} ligação(ões) sugerida(s)')
        if passo(mais_novo(prot, a.argila, *caminhos), 'protótipo em dia com o argila.json',
                 f'deidara.py prototipar {a.argila}'):
            ligacoes = ', '.join(re.sub(r'^relacionamentos\[\d+\]\s*', '', e.split(':')[0]).replace(' ', '') for e in pendentes)
            passo(False, f'ligação(ões) A CONFIRMAR: {ligacoes}',
                  f'confira os campos com o dono do dado e rode `deidara.py confirmar {a.argila} --ligacao DE->PARA '
                  '--por "<quem confirmou>"` (ou --remover); o aceite vem depois')
        return _imprimir_situacao(modelo, passos)
    if not passo(not problemas.erros, f'validação: {len(problemas.erros)} erro(s), {len(problemas.avisos)} aviso(s)',
                 f'deidara.py validar {a.argila}'):
        return _imprimir_situacao(modelo, passos)
    aprov, recusa = aprovacao_valida(a.argila, caminhos, modelo)
    if not passo(mais_novo(prot, a.argila, *caminhos) or bool(aprov and aprov.get('sem_prototipo')),
                 'protótipo em dia com o argila.json', f'deidara.py prototipar {a.argila}'):
        return _imprimir_situacao(modelo, passos)
    if not passo(aprov is not None, f'aprovação: {aprov["aprovado_por"]} em {aprov["em"]}' if aprov else
                 f'aprovação: {recusa}', f'mostre o protótipo e, com o "sim", `deidara.py aprovar {a.argila} --por NOME`'):
        return _imprimir_situacao(modelo, passos)
    ger = aprov.get('ultima_geracao')
    if not passo(bool(ger), f'projeto Power BI gerado em {ger["pasta"]} ({ger["em"]})' if ger else 'projeto Power BI gerado',
                 f'deidara.py gerar {a.argila} -o C:/paineis/<nome>'):
        return _imprimir_situacao(modelo, passos)
    cartao = memory_card.configuracao().get('pasta')
    if cartao and os.path.isdir(cartao):
        salvo = [r for r, f in memory_card.saves(cartao)
                 if f.get('tipo') == 'painel' and f.get('retrato') == governanca.retrato(modelo)]
        passo(bool(salvo), f'salvo no Memory Card: {salvo[0]}' if salvo else 'salvo no Memory Card (versão atual)',
              f'deidara.py memory-card enviar {a.argila} --categoria C --secao S')
    else:
        passo(True, 'Memory Card não configurado nesta máquina (opcional)')
    return _imprimir_situacao(modelo, passos)


def _imprimir_situacao(modelo, passos):
    print(relato.resumo(modelo))
    for ok, texto, _ in passos:
        print(f'  {"✓" if ok else "✗"} {texto}')
    pendente = next((p for p in passos if not p[0]), None)
    if pendente:
        print(f'Próximo passo: {pendente[2]}')
        return 0
    print('✓ Tudo feito. Siga o LEIA-ME da pasta gerada (views, atualizar, conferir, publicar).')
    return 0


def registrar(sub):
    v = sub.add_parser('validar', help='confere o argila.json (nomes, ligações, funções, filtros)')
    v.add_argument('argila')
    v.add_argument('--json', action='store_true')
    v.set_defaults(func=cmd_validar)
    si = sub.add_parser('situacao', help='onde o projeto está e qual é o próximo passo')
    si.add_argument('argila')
    si.set_defaults(func=cmd_situacao)
