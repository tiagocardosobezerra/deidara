#!/usr/bin/env python3
"""
================================================================================
 DEIDARA — do schema ao painel: protótipo primeiro, Power BI depois
================================================================================
"Arte é uma explosão!" O Deidara molda a argila (a especificação do painel),
mostra a escultura (o protótipo) e, só depois do "sim" do usuário, detona
(gera o projeto Power BI completo).

Fluxo:
    coletar     estrutura das tabelas pelo Vegapunk (stella.py detalhar --json)
    validar     confere o argila.json contra a estrutura (nunca adivinha nome)
    prototipar  protótipo navegável em HTML, com números fictícios
    aprovar     grava o "sim" do usuário (hash do argila.json + do schema)
    gerar       .pbip (TMDL + PBIR) + views SQL + conferência + documentação

Uso:
    python3 deidara.py coletar   --vegapunk DIR TABELA [TABELA ...] -o schema.json [--db BANCO]
    python3 deidara.py validar   argila.json [--json]
    python3 deidara.py prototipar argila.json [-o prototipo.html]
    python3 deidara.py aprovar   argila.json --por NOME [--observacao TEXTO]
    python3 deidara.py gerar     argila.json [-o PASTA]
    python3 deidara.py diff      argila.json [--contra OUTRO.json]
    python3 deidara.py status

O argila.json aponta para o(s) schema.json em "schema" (caminho relativo a
ele). Formato completo: referencias/argila.md.
================================================================================
"""

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

from argila import VERSAO, docs, governanca, pbir, prototipo, sql, tmdl  # noqa: E402
from argila.especificacao import resolver  # noqa: E402
from argila.schema import Schema  # noqa: E402
from argila.util import gravar_json, gravar_texto, ident, ler_json, sha256_arquivo  # noqa: E402


# pasta do projeto + nome + o arquivo mais fundo do .pbip (visual.json de uma página)
LONGEST_RELATIVO = len('/.Report/definition/pages/0123456789abcdef0123/visuals/0123456789abcdef0123/visual.json')


def _lembrete(texto):
    print(f'LEMBRETE: {texto}', file=sys.stderr)


# ------------------------------------------------------------------- carga
def _carregar(caminho_argila):
    argila = ler_json(caminho_argila)
    base = os.path.dirname(os.path.abspath(caminho_argila))
    esquemas = argila.get('schema') or []
    if isinstance(esquemas, str):
        esquemas = [esquemas]
    if not esquemas:
        raise SystemExit('argila.json sem "schema": aponte para a saída do `deidara.py coletar` '
                         '(ou do `stella.py detalhar --json`).')
    caminhos = [os.path.join(base, e) for e in esquemas]
    for c in caminhos:
        if not os.path.exists(c):
            raise SystemExit(f'schema não encontrado: {c}')
    schema = Schema.carregar(caminhos)
    modelo, problemas = resolver(argila, schema)
    return argila, schema, modelo, problemas, caminhos


def _relatorio(problemas):
    for e in problemas.erros:
        print(f'  ERRO   {e}')
    for a in problemas.avisos:
        print(f'  AVISO  {a}')


def _hashes(caminho_argila, caminhos_schema):
    return {'argila_sha256': sha256_arquivo(caminho_argila),
            'schema_sha256': {os.path.basename(c): sha256_arquivo(c) for c in caminhos_schema}}


def _arquivo_aprovacao(caminho_argila):
    raiz, _ = os.path.splitext(caminho_argila)
    return raiz + '.aprovacao.json'


# ---------------------------------------------------------------- comandos
def cmd_coletar(a):
    stella = os.path.join(a.vegapunk, 'stella.py')
    if not os.path.exists(stella):
        raise SystemExit(f'stella.py não encontrado em {a.vegapunk}: aponte --vegapunk para a pasta do Vegapunk')
    cmd = [sys.executable, stella] + (['--db', a.db] if a.db else []) + \
          ['detalhar', '--dominio', 'schema', *a.tabelas, '--json']
    r = subprocess.run(cmd, cwd=a.vegapunk, capture_output=True, text=True, encoding='utf-8')
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        raise SystemExit(f'o detalhar do Vegapunk falhou (código {r.returncode})')
    dados = json.loads(r.stdout)
    faltam = [t for t in a.tabelas if t.upper() not in {k.upper() for k in dados.get('tabelas', {})}]
    if faltam:
        raise SystemExit(f'o Vegapunk não conhece: {", ".join(faltam)}. Rode o `buscar` dele antes; não invente.')
    gravar_json(a.saida, dados)
    print(f'{len(dados["tabelas"])} tabela(s) em {a.saida}')
    for av in dados.get('aviso') or []:
        print(f'  AVISO  {av}')
    _lembrete('confirme no Vegapunk as tabelas que entrarem no painel: '
              'stella.py confirmar --dominio schema "<pedido>" TABELA')


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
    if aprov.get('argila_sha256') != atual['argila_sha256'] or aprov.get('schema_sha256') != atual['schema_sha256']:
        print('O argila.json ou o schema mudou depois da aprovação: gere o protótipo de novo e peça novo aceite.')
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
    os.makedirs(os.path.join(pasta, 'sql'))
    gravar_texto(os.path.join(pasta, 'sql', '01_views.sql'), sql.views(modelo), bom=True)
    gravar_texto(os.path.join(pasta, 'sql', '02_conferencia.sql'), sql.conferencia(modelo), bom=True)
    gravar_texto(os.path.join(pasta, 'sql', '03_qualidade.sql'), sql.qualidade(modelo), bom=True)
    os.makedirs(os.path.join(pasta, 'docs'))
    gravar_texto(os.path.join(pasta, 'docs', 'dicionario_indicadores.md'),
                 docs.dicionario(modelo, aprov.get('historico') or []))
    gravar_texto(os.path.join(pasta, 'docs', 'medidas.dax'), docs.medidas_dax(modelo))
    gravar_texto(os.path.join(pasta, 'LEIA-ME.md'), docs.leia_me(modelo, nome, aprov, problemas.avisos))
    gravar_texto(os.path.join(pasta, 'prototipo.html'), prototipo.gerar_html(modelo, problemas, VERSAO))
    print(f'Katsu! Projeto gerado em {pasta}')
    print(f'  {nome}.pbip  ·  sql/01_views.sql  ·  sql/02_conferencia.sql  ·  LEIA-ME.md')
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
    vp = os.environ.get('VEGAPUNK_DIR')
    print(f'VEGAPUNK_DIR: {vp or "(não definido; use --vegapunk no coletar)"}')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog='deidara', description='Do schema ao painel Power BI.')
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('coletar', help='estrutura das tabelas pelo Vegapunk')
    c.add_argument('--vegapunk', default=os.environ.get('VEGAPUNK_DIR'), required=not os.environ.get('VEGAPUNK_DIR'))
    c.add_argument('--db')
    c.add_argument('tabelas', nargs='+')
    c.add_argument('-o', '--saida', default='schema.json')
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
    df = sub.add_parser('diff', help='o que mudou desde a aprovação')
    df.add_argument('argila')
    df.add_argument('--contra')
    sub.add_parser('status')
    a = ap.parse_args(argv)
    return {'coletar': cmd_coletar, 'validar': cmd_validar, 'prototipar': cmd_prototipar, 'aprovar': cmd_aprovar,
            'gerar': cmd_gerar, 'diff': cmd_diff, 'status': cmd_status}[a.cmd](a) or 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
