"""
Os comandos do Memory Card.
"""

import json
import os
import shutil
from kibaku_nendo import VERSAO
from tecnicas.luneta import catalogo
from tecnicas.c3 import docs
from tecnicas import memory_card
from tecnicas.c1 import prototipo
from kibaku_nendo.especificacao import resolver
from kibaku_nendo.util import gravar_texto
from tecnicas.comum import (aprovacao_valida, carregar_argila, cartao_ativo, lembrete, quem_usa,
                                         mostrar_relatorio)


def cmd_memory_card(a):
    if a.acao == 'desligar':
        print(memory_card.desligar())
        return 0
    if a.acao == 'iniciar':
        try:
            for m in memory_card.iniciar(a.repo, a.pasta, a.publico):
                print(m)
        except ValueError as e:
            print(str(e))
            return 1
        return 0
    pasta = cartao_ativo()
    if a.acao == 'catalogo':
        itens = memory_card.saves(pasta)
        if a.json:
            print(json.dumps([{'ref': r, **{k: f.get(k) for k in ('tipo', 'titulo', 'versao', 'status', 'descricao')}}
                              for r, f in itens], ensure_ascii=False, indent=2))
        for r, f in itens:
            print(f'  [{f["tipo"]}] {r}  v{f["versao"]} · {f["status"]} — {f.get("descricao") or ""}'[:160])
        if not itens:
            print('O cartão está vazio.')
        return 0
    if a.acao == 'buscar':
        achados = memory_card.buscar(pasta, a.termos or [], a.limite)
        for r, f in achados:
            selo = 'OFICIAL' if f.get('status') == 'oficial' else f['status']
            print(f'  [{f["tipo"]}] {f["titulo"]} ({selo}, v{f["versao"]}) — {r}')
            if f.get('descricao'):
                print(f'      {f["descricao"]}')
            if f['tipo'] == 'indicador':
                print(f'      DAX: {" ".join(f.get("dax", "").split())[:150]}')
        if not achados:
            print('Nada no cartão com esses termos: pode criar do zero.')
        lembrete('se algo serviu, ofereça reaproveitar (a definição de um indicador OFICIAL não se reescreve).')
        return 0
    if a.acao == 'marcar':
        try:
            print(memory_card.marcar(pasta, a.ref, a.status, quem_usa(a), a.motivo))
        except ValueError as e:
            print(str(e))
            return 1
        return 0
    if a.acao == 'conferir':
        if not a.catalogos:
            print('informe --catalogos com os catálogos atuais das fontes (eles não ficam no cartão)')
            return 1
        cats = {}
        for c in a.catalogos:
            f = catalogo.carregar(c)
            cats[f.nome] = f
        res = memory_card.conferir(pasta, cats, resolver, a.refs or (), a.registrar, quem_usa(a))
        commit = res.pop('__commit__', None)
        for ref, (sit, det) in res.items():
            print(f'  {sit.upper():<12} {ref}')
            for d in det[:8]:
                print(f'      · {d}')
        if commit:
            print(commit[1][0])
        return 1 if any(s == 'quebrado' for s, _ in res.values()) else 0
    # enviar
    argila, cats, modelo, problemas, caminhos = carregar_argila(a.argila)
    if problemas.erros:
        mostrar_relatorio(problemas)
        return 1
    aprov, recusa = aprovacao_valida(a.argila, caminhos, modelo)
    if recusa:
        print(f'Só painel aprovado entra no cartão: {recusa}.')
        return 1
    texto = None
    if a.texto:
        with open(a.texto, encoding='utf-8') as f:
            texto = f.read()
    plano = memory_card.planejar(pasta, argila, modelo, aprov, a.categoria, a.secao, a.artigo, a.motivo, texto,
                                 a.relacionado, a.status)
    print(f'Destino: {memory_card.SECAO}/saves/{plano["ref"]}  (v{plano["versao"]}, {"novo" if plano["novo"] else "versão nova" if plano["mudancas"] else "sem mudança no painel"}, status {plano["status"]})')
    for m in plano['mudancas']:
        print(f'  MUDOU  {m}')
    for i in plano['indicadores']:
        extra = f' — {"; ".join(i["mudancas"])}' if i['mudancas'] else ''
        print(f'  indicador {i["nome"]}: {i["estado"]} (v{i["versao"]}) {i["ref"]}{extra}')
    for b in plano['bloqueios'] + plano['erros']:
        print(f'  ERRO  {b}')
    if plano['bloqueios'] or plano['erros']:
        return 1
    if plano['novo']:
        print('\nArtigo (corpo):\n' + '\n'.join('  ' + l for l in (plano['texto'] or '').strip().splitlines()[:40]))
    if not a.confirmar:
        lembrete('isto é só a prévia: mostre ao usuário e, só com o "sim", repita com --confirmar.')
        return 0
    import tempfile
    tmp = tempfile.mkdtemp(prefix='ddmc')
    dic = os.path.join(tmp, 'dicionario_indicadores.md')
    gravar_texto(dic, docs.dicionario(modelo, aprov.get('historico') or []))
    prot = os.path.join(tmp, 'prototipo.html')
    gravar_texto(prot, prototipo.gerar_html(modelo, problemas, VERSAO))
    try:
        resultado = memory_card.gravar(pasta, plano, quem_usa(a), a.argila,
                                       {'dicionario_indicadores.md': dic, 'prototipo.html': prot})
    except ValueError as e:
        print(str(e))
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f'Salvo em {memory_card.SECAO}/saves/{plano["ref"]}: {resultado}')
    return 0


def registrar(sub):
    mc = sub.add_parser('memory-card', help='o cartão de memória do time (painéis e indicadores)')
    mc.add_argument('acao', choices=['iniciar', 'catalogo', 'buscar', 'enviar', 'marcar', 'conferir', 'desligar'])
    mc.add_argument('alvo', nargs='*', help='buscar: termos; enviar: argila.json; marcar: REF; conferir: REFs')
    mc.add_argument('--repo')
    mc.add_argument('--pasta')
    mc.add_argument('--publico', action='store_true')
    mc.add_argument('--json', action='store_true')
    mc.add_argument('--limite', type=int, default=10)
    mc.add_argument('--categoria')
    mc.add_argument('--secao')
    mc.add_argument('--artigo')
    mc.add_argument('--texto')
    mc.add_argument('--motivo')
    mc.add_argument('--relacionado', action='append', default=[])
    mc.add_argument('--status')
    mc.add_argument('--por')
    mc.add_argument('--confirmar', action='store_true')
    mc.add_argument('--catalogos', nargs='+')
    mc.add_argument('--registrar', action='store_true')
    mc.set_defaults(func=cmd_memory_card, conferir=_conferir)


def _conferir(a, parser):
    a.termos = a.refs = a.alvo
    a.argila = a.alvo[0] if a.alvo else None
    a.ref = a.alvo[0] if a.alvo else None
    if a.acao == 'enviar' and (not a.argila or not a.categoria or not a.secao):
        parser.error('memory-card enviar pede argila.json, --categoria e --secao')
    if a.acao == 'marcar' and (not a.ref or not a.status):
        parser.error('memory-card marcar pede REF e --status')
