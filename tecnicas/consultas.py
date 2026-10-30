"""
Os comandos de consulta: funções e padrões (Sasori), técnicas de visual e modelos de layout (Arte) e o Memory Card.
"""

import json
import os
import shutil

from kibaku_nendo import VERSAO
from tecnicas.luneta import catalogo
from tecnicas import sasori as dicionario
from tecnicas.c3 import docs
from tecnicas import memory_card
from tecnicas.c1 import prototipo
from kibaku_nendo.especificacao import resolver
from kibaku_nendo.util import gravar_texto
from kibaku_nendo.comandos_apoio import aprovacao_valida, carregar_argila, cartao_ativo, lembrete, quem_usa, mostrar_relatorio


def cmd_funcoes(a):
    if a.acao == 'ver':
        achou = dicionario.ver(a.termo, a.linguagem)
        if not achou:
            print(f'{a.termo} não está no dicionário. Tente: deidara.py funcoes buscar "<o que você quer fazer>"')
            return 1
        ling, nome, e = achou
        print(f'{nome} ({ling.upper()} · {", ".join(e.get("categorias") or [])})')
        for s in e.get('sintaxe') or []:
            print(f'  {s}')
        if e.get('descricao'):
            print(f'  {e["descricao"]}')
        if e.get('uso'):
            print(f'  Em indicadores: {e["uso"]}')
        if e.get('url'):
            print(f'  Documentação oficial: {e["url"]}')
        return 0
    achados = dicionario.buscar(a.termo, a.linguagem)
    for nome, e in achados:
        print(f'  {nome:<28} {", ".join(e.get("categorias") or [])[:28]:<28} {e.get("descricao", "")}')
    if not achados:
        print('Nada encontrado. Busque pelo nome em inglês (ex.: "YTD", "DIVIDE") ou pela categoria.')
    return 0


def cmd_padroes(a):
    dados = dicionario.padroes()
    if not a.termo:
        print('Onde criar cada coisa:')
        for o in dados['onde_criar']:
            print(f'  {o["meio"]}: {o["quando"]}')
    for p in dicionario.padroes_para(a.termo or ''):
        print(f'\n{p["nome"]}  [{p["id"]}]')
        if p.get('argila'):
            print(f'  argila.json: {json.dumps(p["argila"], ensure_ascii=False)}')
        for i, x in enumerate(p.get('cadeia') or [], 1):
            print(f'  {i}. {json.dumps(x, ensure_ascii=False)}')
        if p.get('dax'):
            print(f'  DAX: {p["dax"]}')
        if p.get('onde'):
            print(f'  Onde: {p["onde"]}')
        if p.get('alternativa'):
            print(f'  Alternativa: {p["alternativa"]}')
        for x in p.get('armadilhas') or []:
            print(f'  Atenção: {x}')
    return 0


def cmd_visuais(a):
    achados = dicionario.visuais_para(a.termo or '')
    if not achados:
        print(f'Nenhuma técnica para "{a.termo}". Sem assunto, `deidara.py visuais` lista todas.')
        return 1
    for v in achados:
        selo = 'o Deidara gera' if v['deidara'].get('gera') else ('nativo' if v['nativo'] else 'visual personalizado')
        print(f'\n{v["nome"]}  [{v["id"]}] · {selo}')
        print(f'  Quando: {v["quando"]}')
        if v['deidara'].get('argila'):
            print(f'  argila.json (medida): {json.dumps(v["deidara"]["argila"], ensure_ascii=False)}')
        if v['deidara'].get('visual'):
            print(f'  argila.json (visual): {json.dumps(v["deidara"]["visual"], ensure_ascii=False)}')
        if v['deidara'].get('raiz'):
            print(f'  argila.json (raiz): {json.dumps(v["deidara"]["raiz"], ensure_ascii=False)}')
        if v['deidara'].get('pagina'):
            print(f'  argila.json (página): {json.dumps(v["deidara"]["pagina"], ensure_ascii=False)}')
        print(f'  No Power BI: {v["power_bi"]}')
        for x in v.get('cuidados') or []:
            print(f'  Atenção: {x}')
    print('\nGuia de design: referencias/design.md · medidas SVG: referencias/svg.md')
    return 0


def cmd_modelos(a):
    from tecnicas.arte.modelos import MODELOS
    print('Modelos de layout ("modelo" no argila.json; ver referencias/modelos.md):')
    for k, v in MODELOS.items():
        print(f'  {k:<20} {v}')
    return 0


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
