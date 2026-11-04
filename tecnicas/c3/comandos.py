"""
Os comandos do C3: o projeto Power BI e a conferência no Desktop aberto.
"""

import datetime
import os
import shutil
from kibaku_nendo import VERSAO
from tecnicas.c3 import docs
from tecnicas import katsu as governanca
from tecnicas.c3 import pbir
from tecnicas.c1 import prototipo
from tecnicas.c3 import sql
from tecnicas.c3 import tmdl
from kibaku_nendo.util import gravar_json, gravar_texto, ident, ler_json
from tecnicas.comum import (LONGEST_RELATIVO, arquivo_da_aprovacao, carregar_argila, hashes_da_aprovacao, lembrar_salvar_no_cartao,
                            lembrete, mostrar_relatorio)
from tecnicas.bunshin import demo
from tecnicas.c3 import desktop


def cmd_gerar(a):
    _, _, modelo, problemas, caminhos = carregar_argila(a.argila)
    if problemas.erros:
        mostrar_relatorio(problemas)
        return 1
    arq = arquivo_da_aprovacao(a.argila)
    if not os.path.exists(arq):
        print('Sem aprovação: gere o protótipo, mostre ao usuário e rode `aprovar` só com o "sim" dele.')
        return 1
    aprov = ler_json(arq)
    atual = hashes_da_aprovacao(a.argila, caminhos)
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
    if a.demo:
        modelo['_demo'] = demo.expressoes(modelo)
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
    gravar_texto(os.path.join(pasta, 'docs', 'conferencia.dax'), docs.consulta_dax(modelo))
    leia = docs.leia_me(modelo, nome, aprov, problemas.avisos)
    if a.demo:
        leia = ('> **DEMONSTRAÇÃO.** Este projeto traz linhas fictícias embutidas (geradas pelo Deidara, sem fonte de '
                'dados): abra o .pbip, clique em **Atualizar** e todos os números são calculados pelo Power BI. Serve '
                'para testar e mostrar o painel; para o painel real, gere de novo sem `--demo`.\n\n') + leia
    gravar_texto(os.path.join(pasta, 'LEIA-ME.md'), leia)
    gravar_texto(os.path.join(pasta, 'HOMOLOGACAO.md'), docs.homologacao(modelo, nome, aprov))
    gravar_texto(os.path.join(pasta, 'prototipo.html'), prototipo.gerar_html(modelo, problemas, VERSAO))
    aprov['ultima_geracao'] = {'em': datetime.datetime.now().strftime('%d/%m/%Y %H:%M'), 'pasta': os.path.abspath(pasta),
                               'deidara': VERSAO}
    gravar_json(arq, aprov)
    print(f'C3! Projeto {"de DEMONSTRAÇÃO (linhas fictícias embutidas) " if a.demo else ""}gerado em {pasta}')
    if a.demo:
        print('  Abra o .pbip e clique em Atualizar: as tabelas vêm do próprio projeto, sem banco nenhum.')
    print(f'  {nome}.pbip  ·  LEIA-ME.md  ·  HOMOLOGACAO.md' + ''.join(f'  ·  sql/{f["nome"]}/' for f in sql.fontes_sql(modelo)))
    print('Agora:')
    if a.demo:                               # sem banco: nada de DBA, só abrir, mostrar e, depois, gerar o real
        print(f'  1. [Analista] abrir {nome}.pbip no Power BI Desktop e clicar em Atualizar (nenhuma credencial)')
        print('  2. [Analista + gestor] conferir o painel com os números fictícios: layout, cortes e navegação')
        print('  3. [Analista] para o painel real, gerar de novo sem --demo (aí entram as views SQL e a homologação)')
        lembrar_salvar_no_cartao(a.argila)
        return 0
    passo = 1
    for f in sql.fontes_sql(modelo):
        print(f'  {passo}. [DBA] rodar sql/{f["nome"]}/01_views.sql no banco {f["banco"]}')
        passo += 1
    print(f'  {passo}. [Analista] abrir {nome}.pbip no Power BI Desktop, conferir parâmetros e credenciais, Atualizar')
    print(f'  {passo + 1}. [Analista + dono do indicador] preencher HOMOLOGACAO.md (qualidade, totais, cortes)')
    print(f'  {passo + 2}. [Analista] Salvar como .pbix e publicar; depois `memory-card enviar ... --status em-uso`')
    lembrete('o .pbix sai do Power BI Desktop: abra o .pbip e use Arquivo > Salvar como (passo "Gerar o .pbix" do '
              'LEIA-ME), depois de preencher o HOMOLOGACAO.md.')
    lembrar_salvar_no_cartao(a.argila)
    return 0


def cmd_conferir_desktop(a):
    """O DAX conferido pelo motor do Power BI Desktop aberto no projeto (tecnicas/c3/desktop.py)."""
    _, _, modelo, problemas, _ = carregar_argila(a.argila)
    if problemas.erros:
        mostrar_relatorio(problemas)
        return 1
    medidas = [x['nome'] for x in modelo['medidas']]
    cal = modelo['calendario']['tabela'] if modelo.get('calendario') else None
    porta = a.porta
    if a.abrir:
        print(f'Abrindo {a.abrir} no Power BI Desktop...')
        porta = desktop.abrir(a.abrir)
        if not porta:
            print('✗ o Power BI Desktop não abriu o projeto no tempo (5 min): abra à mão e rode sem --abrir')
            return 1
    r = desktop.conferir(medidas, cal, porta=porta, atualizar=a.atualizar or bool(a.abrir),
                         pasta_tmp=os.path.dirname(os.path.abspath(a.argila)))
    if a.fechar and porta:
        desktop.fechar(porta)
    if r.get('erro'):
        print(f'✗ {r["erro"]}')
        for i in r.get('instancias') or []:
            print(f'  porta {i["porta"]}: {i.get("arquivo") or i["titulo"] or "(sem título)"}')
        return 1
    print(f'Power BI Desktop: {r["instancia"].get("arquivo") or r["instancia"]["titulo"]} (porta {r["instancia"]["porta"]}), '
          f'{r["calculadas"]} medida(s) calculadas no total' + (' e mês a mês' if cal else ''))
    for onde, erro in r['problemas']:
        print(f'  ✗ {onde}: {erro}')
    for nome, ms in sorted(r.get('lentas') or [], key=lambda x: -x[1]):
        print(f'  ! medida {nome}: {ms / 1000:.1f} s para calcular (o visual com ela abre lento)')
    if r['vazias'] and len(r['vazias']) == r['calculadas']:
        print('  ! todas as medidas em branco: o modelo está sem dados (clique em Atualizar ou use --atualizar)')
    if not r['problemas']:
        print('✓ nenhuma medida, item de grupo de cálculo ou partição com erro no motor do Power BI')
    return 1 if r['problemas'] else 0


def registrar(sub):
    g = sub.add_parser('gerar', help='gera o projeto Power BI, SQL e documentação')
    g.add_argument('argila')
    g.add_argument('-o', '--saida')
    g.add_argument('--demo', action='store_true',
                   help='projeto de demonstração: linhas fictícias embutidas, abre e calcula sem banco nenhum')
    g.set_defaults(func=cmd_gerar)
    cd = sub.add_parser('conferir-desktop', help='confere o DAX no Power BI Desktop aberto no projeto (só Windows)')
    cd.add_argument('argila')
    cd.add_argument('--porta', help='a porta do motor, com mais de um Power BI Desktop aberto')
    cd.add_argument('--atualizar', action='store_true', help='atualiza os dados antes (o --demo não pede credencial)')
    cd.add_argument('--abrir', metavar='PBIP', help='abre este .pbip no Desktop, espera o motor e atualiza antes')
    cd.add_argument('--fechar', action='store_true', help='fecha o Desktop no fim, sem salvar (o projeto se gera de novo)')
    cd.set_defaults(func=cmd_conferir_desktop)
