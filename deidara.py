#!/usr/bin/env python3
"""
================================================================================
 DEIDARA — do schema ao painel: protótipo primeiro, Power BI depois
================================================================================
"Arte é uma explosão!" O Deidara molda a argila (a especificação do painel),
mostra a escultura (o protótipo) e, só depois do "sim" do usuário, detona
(gera o projeto Power BI completo).

Nome de referência: o Deidara da Akatsuki, o artista da argila explosiva. Este
arquivo é ele: recebe o comando e chama a técnica certa, como a Stella faz com
os satélites do Vegapunk. O motor é a argila (`kibaku_nendo/`) e cada etapa é
uma técnica dele (`tecnicas/`):

    luneta        receita, catalogar, buscar, relacionar, provar
    te_no_kuchi   novo, esbocar (com o C2, que escolhe os visuais, e o Tobi, a frase)
    c1 + bunshin  prototipar (números fictícios)
    katsu         aprovar, diff
    c3            gerar
    sasori        funcoes, padroes
    onoki         onoki (o acerto da busca)
    arte          modelos, visuais

Fluxo:
    receita     a consulta (SQL, DAX ou Power Query) que a pessoa roda onde os
                dados estão; devolve só estrutura, nunca linhas de dado
    catalogar   transforma o resultado colado num catálogo da fonte
    buscar      acha as tabelas de um pedido em todos os catálogos
    relacionar  sugere as ligações que faltam, com a evidência de cada uma
    provar      lê o resultado da receita de prova (percentuais, nunca linhas)
    memory-card a seção deidara/ do cartão de memória do time (repositório memory-card):
                iniciar, catalogo, buscar, enviar, marcar, conferir
    validar     confere o argila.json contra os catálogos (nunca adivinha nome)
    prototipar  protótipo navegável em HTML, com números fictícios
    aprovar     grava o "sim" do usuário (hash do argila.json + do schema)
    gerar       .pbip (TMDL + PBIR) + views SQL + conferência + documentação

Uso:
    python3 deidara.py receita   sql [--esquema dbo] [--tabelas T1,T2] | dax | m [--consultas C1,C2] [-o ARQ]
    python3 deidara.py catalogar --de RESULTADO.txt --fonte NOME [--m PASTA_DOS_.m] [-o catalogo.json]
    python3 deidara.py buscar    "<pedido>" (--argila argila.json | --catalogos A.json B.json)
    python3 deidara.py relacionar (--argila argila.json | --catalogos A.json B.json [--tabelas T1,T2])
    python3 deidara.py receita   prova --argila argila.json --de "Tabela[COLUNA]" --para "Tabela[COLUNA]"
    python3 deidara.py provar    --de RESULTADO.txt [--argila argila.json]
    python3 deidara.py confirmar argila.json --ligacao DE->PARA --por NOME [--motivo M] | --remover
    python3 deidara.py memory-card iniciar --repo DONO/memory-card [--pasta DIR] [--publico]
    python3 deidara.py memory-card buscar TERMO [TERMO ...]
    python3 deidara.py memory-card enviar argila.json --categoria C --secao S [--artigo A] [--texto ARQ.md]
                                          [--motivo M] [--relacionado REF] [--status S] [--confirmar]
    python3 deidara.py memory-card marcar REF --status rascunho|em-uso|oficial [--motivo M]
    python3 deidara.py memory-card conferir [REF ...] --catalogos A.json B.json [--registrar]
    python3 deidara.py validar   argila.json [--json]
    python3 deidara.py prototipar argila.json [-o prototipo.html]
    python3 deidara.py aprovar   argila.json --por NOME [--observacao TEXTO]
    python3 deidara.py gerar     argila.json [-o PASTA]
    python3 deidara.py diff      argila.json [--contra OUTRO.json]
    python3 deidara.py funcoes   buscar "acumulado" | ver SAMEPERIODLASTYEAR [--linguagem dax|m]
    python3 deidara.py padroes   [turnover | taxa | estoque | ...]
    python3 deidara.py visuais   [meta | ranking | causa | status | ...]
    python3 deidara.py status

O argila.json lista as fontes em "fontes" ({"erp": {"catalogo": "catalogos/erp.json"}}),
com caminhos relativos a ele. Formato completo: referencias/argila.md.
================================================================================
"""

import argparse
import os
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

from kibaku_nendo import VERSAO  # noqa: E402
from kibaku_nendo.util import ErroDeUso  # noqa: E402
from kibaku_nendo.comandos import (cmd_aprovar, cmd_diff, cmd_gerar, cmd_prototipar, cmd_situacao, cmd_validar)  # noqa: E402
from tecnicas.consultas import cmd_onoki, cmd_funcoes, cmd_memory_card, cmd_modelos, cmd_padroes, cmd_visuais  # noqa: E402
from tecnicas.luneta.comandos import (cmd_buscar, cmd_catalogar, cmd_confirmar, cmd_provar, cmd_receita,
                                      cmd_relacionar)  # noqa: E402
from tecnicas.te_no_kuchi_comandos import cmd_esbocar, cmd_novo  # noqa: E402


GUIA = """Deidara — do dado ao painel Power BI: protótipo primeiro, projeto completo depois do "sim".

Por onde começar
  python deidara.py novo PASTA                     cria a pasta do painel, com o roteiro
  python deidara.py situacao PASTA/argila.json     onde estou e qual é o próximo passo

O fluxo
  1. briefing (painel.json)   as respostas do gestor: decisão, público, indicadores (definição, meta), cortes
  2. receita + catalogar      a pessoa roda a receita onde os dados estão; o resultado vira o catálogo
  3. esbocar                  o primeiro argila.json: padrões do indicador + briefing + catálogos
  4. validar                  nomes, funções e filtros, até zerar os erros
  5. prototipar               o protótipo HTML para o gestor (números fictícios; ligação a confirmar vira pendência)
  6. confirmar + aprovar      a ligação conferida com o dono do dado; o "sim" do gestor, registrado
  7. gerar                    o projeto Power BI (.pbip), views SQL, conferência e LEIA-ME
  8. memory-card enviar       salva no cartão do time

Apoio
  buscar / relacionar         quais tabelas e quais ligações (com evidência)
  padroes [assunto]           como criar cada indicador e onde
  visuais [assunto]           técnicas de visual: meta na tabela, ranking, causa, status...
  modelos                     os onze modelos de layout ("modelo" no argila.json)
  funcoes buscar|ver          dicionário de funções DAX e Power Query
  diff                        o que mudou desde a aprovação
  onoki --casos C.json        o acerto da busca nos pedidos do time (e o que mudou de ordem)

Ajuda de um comando: python deidara.py COMANDO --help
"""


def cmd_status(a):
    print(f'Deidara {VERSAO} · Python {sys.version.split()[0]} · pasta {RAIZ}')
    return 0


class _Parser(argparse.ArgumentParser):
    """argparse falando português."""
    TROCAS = (('usage:', 'uso:'), ('positional arguments', 'argumentos'), ('options:', 'opções:'),
              ('optional arguments:', 'opções:'), ('show this help message and exit', 'mostra esta ajuda'))

    def format_help(self):
        texto = super().format_help()
        for a, b in self.TROCAS:
            texto = texto.replace(a, b)
        return texto

    def format_usage(self):
        return super().format_usage().replace('usage:', 'uso:')

    def error(self, message):
        import difflib
        if 'invalid choice' in message:
            escolhido = message.split("'")[1] if "'" in message else ''
            opcoes = [x.strip(" '") for x in message.split('choose from')[-1].strip(' ()').split(',')]
            parecido = difflib.get_close_matches(escolhido, opcoes, n=1)
            if parecido:
                message += f'. Você quis dizer: {parecido[0]}?'
        message = (message.replace('the following arguments are required', 'faltam os argumentos')
                   .replace('invalid choice', 'opção inválida').replace('choose from', 'escolha entre')
                   .replace('unrecognized arguments', 'argumentos desconhecidos'))
        self.print_usage(sys.stderr)
        self.exit(2, f'{self.prog}: {message}\nVeja: python deidara.py (sem argumentos) para o roteiro.\n')


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(GUIA)
        return 0
    ap = _Parser(prog='deidara', description='Do dado ao painel Power BI.')
    sub = ap.add_subparsers(dest='cmd', required=True, parser_class=_Parser, metavar='COMANDO')
    r = sub.add_parser('receita', help='a consulta que a pessoa roda onde os dados estão (só estrutura)')
    r.add_argument('tipo', choices=['sql', 'dax', 'm', 'funcoes-dax', 'funcoes-m', 'prova'])
    r.add_argument('--argila')
    r.add_argument('--catalogos', nargs='+')
    r.add_argument('--de', help='prova: Tabela[COLUNA] da filha (lado muitos)')
    r.add_argument('--para', help='prova: Tabela[COLUNA] da mãe (lado um)')
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
    v = sub.add_parser('validar', help='confere o argila.json (nomes, ligações, funções, filtros)')
    v.add_argument('argila')
    v.add_argument('--json', action='store_true')
    p = sub.add_parser('prototipar', help='protótipo HTML para o gestor validar')
    p.add_argument('argila')
    p.add_argument('-o', '--saida')
    ap_ = sub.add_parser('aprovar', help='registra o "sim" do gestor')
    ap_.add_argument('argila')
    ap_.add_argument('--por', required=True)
    ap_.add_argument('--observacao')
    ap_.add_argument('--resumo', help='o resumo copiado da aba "Para aprovar" (confere versão e decisão)')
    ap_.add_argument('--sem-prototipo', action='store_true', help='o gestor aprovou sem protótipo, de propósito')
    ap_.add_argument('--aceito-distorcao', metavar='MOTIVO',
                     help='o gestor mantém um corte que filtra só parte da conta, sabendo disso (fica registrado)')
    g = sub.add_parser('gerar', help='gera o projeto Power BI, SQL e documentação')
    g.add_argument('argila')
    g.add_argument('-o', '--saida')
    g.add_argument('--demo', action='store_true',
                   help='projeto de demonstração: linhas fictícias embutidas, abre e calcula sem banco nenhum')
    on = sub.add_parser('onoki', help='Ōnoki mede a busca contra os pedidos de verdade do time (e pega regressão)')
    on.add_argument('--casos', required=True, help='JSON com os casos: [{"pedido", "esperadas"}] e o retrato gravado')
    on.add_argument('--argila')
    on.add_argument('--catalogos', nargs='+')
    on.add_argument('--top', type=int, default=3)
    on.add_argument('--gravar-retrato', action='store_true', help='grava a ordem atual como a referência')
    bu = sub.add_parser('buscar', help='tabelas de um pedido, em todos os catálogos')
    bu.add_argument('pedido')
    bu.add_argument('--argila')
    bu.add_argument('--catalogos', nargs='+')
    bu.add_argument('--limite', type=int, default=10)
    rl = sub.add_parser('relacionar', help='sugere ligações com evidência')
    rl.add_argument('--argila')
    rl.add_argument('--catalogos', nargs='+')
    rl.add_argument('--tabelas', help='com --catalogos: só estas tabelas (separadas por vírgula)')
    rl.add_argument('--json', action='store_true', help='mostra o trecho do argila.json de cada sugestão')
    rl.add_argument('--pedido', help='com --catalogos: o assunto (a busca escolhe as tabelas)')
    rl.add_argument('--todas', action='store_true', help='mostra todas as sugestões (padrão: as 25 melhores)')
    pv = sub.add_parser('provar', help='lê o resultado da receita de prova e grava na ligação')
    pv.add_argument('--de', required=True)
    pv.add_argument('--argila', help='grava a prova na ligação declarada correspondente')
    cf = sub.add_parser('confirmar', help='confirma (ou remove) uma ligação sugerida "A CONFIRMAR"')
    cf.add_argument('argila')
    cf.add_argument('--ligacao', required=True, help='de->para, ex.: fMetas->dEmpresa')
    cf.add_argument('--por', help='quem confirmou com o dono do dado')
    cf.add_argument('--motivo')
    cf.add_argument('--remover', action='store_true', help='o dono do dado não confirmou: tira a ligação')
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
    fu = sub.add_parser('funcoes', help='dicionário de funções DAX e M')
    fu.add_argument('acao', choices=['buscar', 'ver'])
    fu.add_argument('termo')
    fu.add_argument('--linguagem', choices=['dax', 'm'])
    pa = sub.add_parser('padroes', help='padrões de indicador e onde criar cada coisa')
    pa.add_argument('termo', nargs='?')
    sub.add_parser('modelos', help='os modelos de layout (faixa de KPIs, coluna de KPIs, história longa...)')
    vs = sub.add_parser('visuais', help='técnicas de visual (meta, ranking, causa, status...) e como fazer')
    vs.add_argument('termo', nargs='?')
    df = sub.add_parser('diff', help='o que mudou desde a aprovação')
    df.add_argument('argila')
    df.add_argument('--contra')
    nv = sub.add_parser('novo', help='cria a pasta de um painel novo, com receitas e roteiro')
    nv.add_argument('pasta')
    nv.add_argument('--projeto')
    es = sub.add_parser('esbocar', help='primeiro argila.json a partir dos catálogos e do pedido')
    es.add_argument('alvo', help='a pasta do painel (com catalogos/) ou um catálogo')
    es.add_argument('--catalogos', nargs='+', help='mais catálogos (quando o alvo é um catálogo)')
    es.add_argument('--pedido', help='o que o painel precisa mostrar, em português (sem ele, sai do briefing do painel.json)')
    es.add_argument('--projeto')
    es.add_argument('--tabelas', help='escolha à mão: fonte:TABELA,fonte:TABELA')
    es.add_argument('-o', '--saida')
    es.add_argument('--forcar', action='store_true')
    si = sub.add_parser('situacao', help='onde o projeto está e qual é o próximo passo')
    si.add_argument('argila')
    sub.add_parser('status', help='versão do Deidara')
    a = ap.parse_args(argv)
    if a.cmd == 'confirmar' and not a.remover and not a.por:
        ap.error('confirmar pede --por "<quem confirmou>" (ou --remover)')
    if a.cmd == 'memory-card':
        a.termos = a.refs = a.alvo
        a.argila = a.alvo[0] if a.alvo else None
        a.ref = a.alvo[0] if a.alvo else None
        if a.acao == 'enviar' and (not a.argila or not a.categoria or not a.secao):
            ap.error('memory-card enviar pede argila.json, --categoria e --secao')
        if a.acao == 'marcar' and (not a.ref or not a.status):
            ap.error('memory-card marcar pede REF e --status')
    return {'receita': cmd_receita, 'catalogar': cmd_catalogar, 'validar': cmd_validar, 'prototipar': cmd_prototipar, 'aprovar': cmd_aprovar,
            'gerar': cmd_gerar, 'diff': cmd_diff, 'funcoes': cmd_funcoes, 'padroes': cmd_padroes, 'visuais': cmd_visuais, 'modelos': cmd_modelos,
            'buscar': cmd_buscar, 'relacionar': cmd_relacionar, 'provar': cmd_provar,
            'memory-card': cmd_memory_card, 'confirmar': cmd_confirmar, 'situacao': cmd_situacao, 'novo': cmd_novo, 'esbocar': cmd_esbocar, 'status': cmd_status, 'onoki': cmd_onoki}[a.cmd](a) or 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    try:
        sys.exit(main())
    except ErroDeUso as e:
        print(f'✗ {e}')
        sys.exit(1)
    except FileNotFoundError as e:
        print(f'✗ arquivo ou pasta não encontrado: {e.filename}')
        sys.exit(1)
