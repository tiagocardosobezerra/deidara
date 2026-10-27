#!/usr/bin/env python3
"""
================================================================================
 DEIDARA — do schema ao painel: protótipo primeiro, Power BI depois
================================================================================
"Arte é uma explosão!" O Deidara molda a argila (a especificação do painel),
mostra a escultura (o protótipo) e, só depois do "sim" do usuário, detona
(gera o projeto Power BI completo).

Fluxo:
    receita     a consulta (SQL, DAX ou Power Query) que a pessoa roda onde os
                dados estão; devolve só estrutura, nunca linhas de dado
    catalogar   transforma o resultado colado num catálogo da fonte
    validar     confere o argila.json contra os catálogos (nunca adivinha nome)
    prototipar  protótipo navegável em HTML, com números fictícios
    aprovar     grava o "sim" do usuário (hash do argila.json + do schema)
    gerar       .pbip (TMDL + PBIR) + views SQL + conferência + documentação

Uso:
    python3 deidara.py receita   sql [--esquema dbo] [--tabelas T1,T2] | dax | m [--consultas C1,C2] [-o ARQ]
    python3 deidara.py catalogar --de RESULTADO.txt --fonte NOME [--m PASTA_DOS_.m] [-o catalogo.json]
    python3 deidara.py validar   argila.json [--json]
    python3 deidara.py prototipar argila.json [-o prototipo.html]
    python3 deidara.py aprovar   argila.json --por NOME [--observacao TEXTO]
    python3 deidara.py gerar     argila.json [-o PASTA]
    python3 deidara.py diff      argila.json [--contra OUTRO.json]
    python3 deidara.py funcoes   buscar "acumulado" | ver SAMEPERIODLASTYEAR [--linguagem dax|m]
    python3 deidara.py padroes   [turnover | taxa | estoque | ...]
    python3 deidara.py status

O argila.json lista as fontes em "fontes" ({"erp": {"catalogo": "catalogos/erp.json"}}),
com caminhos relativos a ele. Formato completo: referencias/argila.md.
================================================================================
"""

import argparse
import datetime
import json
import os
import shutil
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

from argila import VERSAO, catalogo, dicionario, docs, governanca, pbir, prototipo, receitas, sql, tmdl  # noqa: E402
from argila.especificacao import resolver  # noqa: E402
from argila.util import gravar_json, gravar_texto, ident, ler_json, sha256_arquivo  # noqa: E402


# pasta do projeto + nome + o arquivo mais fundo do .pbip (visual.json de uma página)
LONGEST_RELATIVO = len('/.Report/definition/pages/0123456789abcdef0123/visuals/0123456789abcdef0123/visual.json')


def _lembrete(texto):
    print(f'LEMBRETE: {texto}', file=sys.stderr)


# ------------------------------------------------------------------- carga
def _carregar(caminho_argila):
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
    modelo, problemas = resolver(argila, catalogos)
    return argila, catalogos, modelo, problemas, caminhos


def _relatorio(problemas):
    for e in problemas.erros:
        print(f'  ERRO   {e}')
    for a in problemas.avisos:
        print(f'  AVISO  {a}')


def _hashes(caminho_argila, caminhos_schema):
    return {'argila_sha256': sha256_arquivo(caminho_argila),
            'catalogos_sha256': {os.path.basename(c): sha256_arquivo(c) for c in caminhos_schema}}


def _arquivo_aprovacao(caminho_argila):
    raiz, _ = os.path.splitext(caminho_argila)
    return raiz + '.aprovacao.json'


# ---------------------------------------------------------------- comandos
def cmd_receita(a):
    if a.tipo == 'sql':
        texto = receitas.receita_sql(a.esquema, [t.strip() for t in (a.tabelas or '').split(',') if t.strip()])
    elif a.tipo == 'dax':
        texto = receitas.receita_dax()
    elif a.tipo == 'funcoes-dax':
        texto = receitas.receita_funcoes_dax()
    elif a.tipo == 'funcoes-m':
        texto = receitas.receita_funcoes_m()
    else:
        texto = receitas.receita_m([c.strip() for c in (a.consultas or '').split(',') if c.strip()])
    if a.saida:
        gravar_texto(a.saida, texto, bom=a.tipo == 'sql')
        print(f'Receita {a.tipo} em {a.saida}')
    else:
        print(texto)
    _lembrete('a pessoa roda a receita onde os dados estão, copia a grade com o cabeçalho para um .txt e você roda '
              '`deidara.py catalogar --de ARQUIVO.txt --fonte NOME`. Nada de dado sai: só estrutura.')
    return 0


def cmd_catalogar(a):
    if a.funcoes:
        try:
            d = receitas.dicionario_local(a.de, a.funcoes)
        except ValueError as e:
            print(str(e))
            return 1
        pasta = os.path.join(dicionario.PASTA, 'local')
        os.makedirs(pasta, exist_ok=True)
        gravar_json(os.path.join(pasta, f'{a.funcoes}.json'), d)
        novas = [n for n in d['funcoes'] if n not in dicionario.funcoes(a.funcoes)]
        print(f'Dicionário local {a.funcoes}: {len(d["funcoes"])} função(ões), {len(novas)} que o Deidara não conhecia'
              + (f' (ex.: {", ".join(novas[:5])})' if novas else ''))
        return 0
    if not a.fonte:
        print('informe --fonte (ou --funcoes dax|m para o dicionário de funções)')
        return 1
    try:
        cat, avisos = receitas.catalogar(a.de, a.fonte, a.m)
    except ValueError as e:
        print(str(e))
        return 1
    saida = a.saida or os.path.join(os.path.dirname(os.path.abspath(a.de)), f'{a.fonte}.catalogo.json')
    gravar_json(saida, cat)
    ncol = sum(len(t['colunas']) for t in cat['tabelas'].values())
    print(f'Fonte {a.fonte} ({cat["tipo"]}, receita {cat["receita"]}): {len(cat["tabelas"])} tabela(s), {ncol} coluna(s), '
          f'{len(cat["fks"])} ligação(ões), {len(cat["expressoes"])} expressão(ões) auxiliar(es)')
    for x in avisos:
        print(f'  AVISO  {x}')
    print(f'Catálogo: {saida}')
    _lembrete(f'aponte no argila.json: "fontes": {{"{a.fonte}": {{"catalogo": "<caminho relativo de {os.path.basename(saida)}>"}}}}')
    return 0


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
        if p.get('dax'):
            print(f'  DAX: {p["dax"]}')
        if p.get('onde'):
            print(f'  Onde: {p["onde"]}')
        if p.get('alternativa'):
            print(f'  Alternativa: {p["alternativa"]}')
        for x in p.get('armadilhas') or []:
            print(f'  Atenção: {x}')
    return 0


def cmd_validar(a):
    _, _, modelo, problemas, _ = _carregar(a.argila)
    if a.json:
        print(json.dumps({'ok': not problemas.erros, 'erros': problemas.erros, 'avisos': problemas.avisos,
                          'resumo': _resumo(modelo)}, ensure_ascii=False, indent=2))
    else:
        print(f'{modelo["projeto"] or "(sem nome)"}: ' + ', '.join(f'{v} {k}' for k, v in _resumo(modelo).items()))
        _relatorio(problemas)
        print('OK: pode prototipar.' if not problemas.erros else f'{len(problemas.erros)} erro(s): corrija antes de seguir.')
    return 1 if problemas.erros else 0


def _resumo(m):
    return {'tabelas': len(m['tabelas']), 'relacionamentos': len(m['relacionamentos']),
            'medidas': len(m['medidas']), 'paginas': len(m['paginas']),
            'visuais': sum(len(p['visuais']) for p in m['paginas'])}


def cmd_prototipar(a):
    _, _, modelo, problemas, _ = _carregar(a.argila)
    _relatorio(problemas)
    if problemas.erros:
        print('Protótipo não gerado: corrija os erros acima.')
        return 1
    saida = a.saida or os.path.splitext(a.argila)[0] + '.prototipo.html'
    gravar_texto(saida, prototipo.gerar_html(modelo, problemas, VERSAO))
    print(f'Protótipo: {saida}')
    _lembrete('mostre o protótipo ao usuário e peça o aceite explícito; só com o "sim" rode '
              '`deidara.py aprovar argila.json --por NOME`.')
    return 0


def cmd_aprovar(a):
    _, _, modelo, problemas, caminhos = _carregar(a.argila)
    if problemas.erros:
        _relatorio(problemas)
        print('Não dá para aprovar com erro de validação.')
        return 1
    arq = _arquivo_aprovacao(a.argila)
    anterior = ler_json(arq) if os.path.exists(arq) else None
    retrato = governanca.retrato(modelo)
    mudancas = governanca.diferencas(anterior['retrato'], retrato) if anterior and anterior.get('retrato') else []
    historico = (anterior or {}).get('historico', [])
    reg = {'projeto': modelo['projeto'], 'versao': modelo['versao'], 'aprovado_por': a.por,
           'em': datetime.datetime.now().strftime('%d/%m/%Y %H:%M'), 'observacao': a.observacao or '',
           'avisos_aceitos': problemas.avisos, 'deidara': VERSAO, **_hashes(a.argila, caminhos)}
    if anterior and (mudancas or not historico):
        historico = historico + [{'versao': reg['versao'], 'em': reg['em'], 'aprovado_por': a.por,
                                  'observacao': reg['observacao'], 'mudancas': mudancas}]
    elif not anterior:
        historico = [{'versao': reg['versao'], 'em': reg['em'], 'aprovado_por': a.por,
                      'observacao': reg['observacao'], 'mudancas': ['primeira versão aprovada']}]
    reg['historico'], reg['retrato'] = historico, retrato
    gravar_json(arq, reg)
    print(f'Aprovado por {a.por} em {reg["em"]} ({len(problemas.avisos)} aviso(s) aceito(s)).')
    for x in mudancas:
        print(f'  MUDOU  {x}')
    print(f'Registro: {_arquivo_aprovacao(a.argila)}')
    return 0


def cmd_gerar(a):
    _, _, modelo, problemas, caminhos = _carregar(a.argila)
    if problemas.erros:
        _relatorio(problemas)
        return 1
    arq = _arquivo_aprovacao(a.argila)
    if not os.path.exists(arq):
        print('Sem aprovação: gere o protótipo, mostre ao usuário e rode `aprovar` só com o "sim" dele.')
        return 1
    aprov = ler_json(arq)
    atual = _hashes(a.argila, caminhos)
    if aprov.get('argila_sha256') != atual['argila_sha256'] or \
            aprov.get('catalogos_sha256') != atual['catalogos_sha256']:
        print('O argila.json ou um catálogo mudou depois da aprovação: gere o protótipo de novo e peça novo aceite.')
        for x in governanca.diferencas(aprov.get('retrato') or {}, governanca.retrato(modelo)):
            print(f'  MUDOU  {x}')
        return 1
    if aprov.get('deidara') != VERSAO:
        print(f'A aprovação foi feita com o Deidara {aprov.get("deidara")} e este é o {VERSAO}: a saída pode mudar. '
              'Gere o protótipo de novo e peça novo aceite.')
        return 1
    nome = ident(modelo['projeto'], 'Painel')
    pasta = a.saida or os.path.join(os.path.dirname(os.path.abspath(a.argila)), 'saida', nome)
    maior = len(os.path.abspath(pasta)) + len(nome) + LONGEST_RELATIVO
    if os.name == 'nt' and maior > 259:
        print(f'Caminho longo demais para o Windows ({maior} caracteres no arquivo mais fundo; o limite é 260). '
              f'Use uma pasta curta: deidara.py gerar {a.argila} -o C:/paineis/{nome}')
        return 1
    if os.path.exists(pasta):
        shutil.rmtree(pasta)
    os.makedirs(pasta)
    gravar_json(os.path.join(pasta, f'{nome}.pbip'), {
        '$schema': 'https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json',
        'version': '1.0', 'artifacts': [{'report': {'path': f'{nome}.Report'}}],
        'settings': {'enableAutoRecovery': True}})
    gravar_texto(os.path.join(pasta, '.gitignore'), '**/.pbi/localSettings.json\n**/.pbi/cache.abf\n')
    tmdl.gravar(modelo, pasta, nome)
    pbir.gravar(modelo, pasta, nome)
    for f in sql.fontes_sql(modelo):
        dsql = os.path.join(pasta, 'sql', f['nome'])
        os.makedirs(dsql)
        gravar_texto(os.path.join(dsql, '01_views.sql'), sql.views(modelo, f), bom=True)
        gravar_texto(os.path.join(dsql, '02_conferencia.sql'), sql.conferencia(modelo, f), bom=True)
        gravar_texto(os.path.join(dsql, '03_qualidade.sql'), sql.qualidade(modelo, f), bom=True)
    os.makedirs(os.path.join(pasta, 'docs'))
    gravar_texto(os.path.join(pasta, 'docs', 'dicionario_indicadores.md'),
                 docs.dicionario(modelo, aprov.get('historico') or []))
    gravar_texto(os.path.join(pasta, 'docs', 'medidas.dax'), docs.medidas_dax(modelo))
    gravar_texto(os.path.join(pasta, 'LEIA-ME.md'), docs.leia_me(modelo, nome, aprov, problemas.avisos))
    gravar_texto(os.path.join(pasta, 'prototipo.html'), prototipo.gerar_html(modelo, problemas, VERSAO))
    print(f'Katsu! Projeto gerado em {pasta}')
    print(f'  {nome}.pbip  ·  LEIA-ME.md' + ''.join(f'  ·  sql/{f["nome"]}/' for f in sql.fontes_sql(modelo)))
    _lembrete('o .pbix sai do Power BI Desktop: abra o .pbip e use Arquivo > Salvar como (passo 5 do LEIA-ME).')
    return 0


def cmd_diff(a):
    """O que mudou no argila.json desde a última aprovação (ou entre dois argila.json)."""
    _, _, modelo, problemas, _ = _carregar(a.argila)
    if a.contra:
        _, _, outro, _, _ = _carregar(a.contra)
        antes, rotulo = governanca.retrato(outro), a.contra
    else:
        arq = _arquivo_aprovacao(a.argila)
        if not os.path.exists(arq):
            print('Sem aprovação para comparar: use --contra OUTRO_ARGILA.json')
            return 1
        aprov = ler_json(arq)
        antes, rotulo = aprov.get('retrato') or {}, f'aprovação de {aprov.get("em")} ({aprov.get("aprovado_por")})'
    mud = governanca.diferencas(antes, governanca.retrato(modelo))
    print(f'Comparando com: {rotulo}')
    for x in mud:
        print(f'  {x}')
    print('Nada mudou para quem consome o painel.' if not mud else f'{len(mud)} mudança(s).')
    return 0


def cmd_status(a):
    print(f'Deidara {VERSAO} · Python {sys.version.split()[0]} · pasta {RAIZ}')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog='deidara', description='Do schema ao painel Power BI.')
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('receita', help='consulta que devolve a estrutura de uma fonte')
    r.add_argument('tipo', choices=['sql', 'dax', 'm', 'funcoes-dax', 'funcoes-m'])
    r.add_argument('--esquema', default='dbo')
    r.add_argument('--tabelas', help='sql: tabelas separadas por vírgula (vazio = todas do esquema)')
    r.add_argument('--consultas', help='m: consultas Power Query separadas por vírgula')
    r.add_argument('-o', '--saida')
    c = sub.add_parser('catalogar', help='resultado colado de uma receita -> catálogo da fonte')
    c.add_argument('--de', required=True)
    c.add_argument('--fonte')
    c.add_argument('--funcoes', choices=['dax', 'm'], help='o resultado é da receita de funções (dicionário local)')
    c.add_argument('--m', help='pasta com os .m (texto do Editor Avançado) das consultas, para a receita m')
    c.add_argument('-o', '--saida')
    v = sub.add_parser('validar')
    v.add_argument('argila')
    v.add_argument('--json', action='store_true')
    p = sub.add_parser('prototipar')
    p.add_argument('argila')
    p.add_argument('-o', '--saida')
    ap_ = sub.add_parser('aprovar')
    ap_.add_argument('argila')
    ap_.add_argument('--por', required=True)
    ap_.add_argument('--observacao')
    g = sub.add_parser('gerar')
    g.add_argument('argila')
    g.add_argument('-o', '--saida')
    fu = sub.add_parser('funcoes', help='dicionário de funções DAX e M')
    fu.add_argument('acao', choices=['buscar', 'ver'])
    fu.add_argument('termo')
    fu.add_argument('--linguagem', choices=['dax', 'm'])
    pa = sub.add_parser('padroes', help='padrões de indicador e onde criar cada coisa')
    pa.add_argument('termo', nargs='?')
    df = sub.add_parser('diff', help='o que mudou desde a aprovação')
    df.add_argument('argila')
    df.add_argument('--contra')
    sub.add_parser('status')
    a = ap.parse_args(argv)
    return {'receita': cmd_receita, 'catalogar': cmd_catalogar, 'validar': cmd_validar, 'prototipar': cmd_prototipar, 'aprovar': cmd_aprovar,
            'gerar': cmd_gerar, 'diff': cmd_diff, 'funcoes': cmd_funcoes, 'padroes': cmd_padroes, 'status': cmd_status}[a.cmd](a) or 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
