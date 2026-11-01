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

    te_no_kuchi   novo, esbocar (com o C2, que escolhe os visuais, e o Tobi, a frase)
    luneta        receita, catalogar, buscar, relacionar, provar, confirmar
    comum         validar, situacao
    c1 + bunshin  prototipar (números fictícios)
    katsu         aprovar, diff (o "sim" que detona)
    c3            gerar, conferir-desktop
    memory_card   memory-card
    sasori        funcoes, padroes
    arte          modelos, visuais
    akatsuki      galeria (modelos Deneb, funções DAX e calendários de terceiros, MIT)
    c0            estudar, propor, importar (engenharia reversa de um painel que já existe)
    onoki         onoki (o acerto da busca)
    c4            a estatística que o C2 escolhe (referencias/estatistica.md)

Cada técnica registra os próprios comandos (`tecnicas/<técnica>/comandos.py`, função `registrar`).

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
    python3 deidara.py conferir-desktop argila.json [--porta N] [--atualizar]   (Power BI Desktop aberto, Windows)
    python3 deidara.py diff      argila.json [--contra OUTRO.json]
    python3 deidara.py funcoes   buscar "acumulado" | ver SAMEPERIODLASTYEAR [--linguagem dax|m]
    python3 deidara.py padroes   [turnover | taxa | estoque | ...]
    python3 deidara.py visuais   [meta | ranking | causa | status | ...]
    python3 deidara.py c0        estudar|propor|importar ALVO [--medida NOME] [-o ARQ|PASTA] [--manter-antigas]
    python3 deidara.py galeria   [cascata | minigráfico | ibcs | ...] [--tipo deneb|funcoes_dax|calendario|svg] [--ver ID]
    python3 deidara.py status

O argila.json lista as fontes em "fontes" ({"erp": {"catalogo": "catalogos/erp.json"}}),
com caminhos relativos a ele. Formato completo: referencias/argila.md.
================================================================================
"""

import argparse
import importlib
import os
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

from kibaku_nendo import VERSAO  # noqa: E402
from kibaku_nendo.util import ErroDeUso  # noqa: E402


# os módulos de comando, na ordem em que aparecem na ajuda: a do fluxo (cada um tem `registrar(sub)`)
COMANDOS = [
    'tecnicas.te_no_kuchi.comandos',   # novo, esbocar
    'tecnicas.luneta.comandos',        # receita, catalogar, buscar, relacionar, provar, confirmar
    'tecnicas.comum',                  # validar, situacao
    'tecnicas.c1.comandos',            # prototipar
    'tecnicas.katsu.comandos',         # aprovar, diff
    'tecnicas.c3.comandos',            # gerar, conferir-desktop
    'tecnicas.memory_card.comandos',   # memory-card
    'tecnicas.sasori.comandos',        # funcoes, padroes
    'tecnicas.arte.comandos',          # modelos, visuais
    'tecnicas.akatsuki.comandos',      # galeria
    'tecnicas.c0.comandos',            # c0
    'tecnicas.onoki.comandos',         # onoki
]

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
  galeria [assunto]           modelos Deneb, funções DAX, calendários e SVG da comunidade (MIT)
  c0 estudar|propor|importar  engenharia reversa: estuda, avalia e refaz o indicador que já existe
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
    for nome in COMANDOS:                          # cada técnica registra os próprios comandos, na ordem do fluxo
        importlib.import_module(nome).registrar(sub)
    sub.add_parser('status', help='versão do Deidara').set_defaults(func=cmd_status)
    a = ap.parse_args(argv)
    if getattr(a, 'conferir', None):               # o que o argparse não confere sozinho (ex.: --por ou --remover)
        a.conferir(a, sub.choices[a.cmd])
    return a.func(a) or 0

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
