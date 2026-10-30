"""
Os comandos do fluxo sobre a argila: validar, prototipar (C1), aprovar (Katsu), gerar (C3), diff e
situacao.
"""

import datetime
import json
import os
import re
import shutil
import sys

from kibaku_nendo import VERSAO
from tecnicas.c3 import docs
from tecnicas import katsu as governanca
from tecnicas import memory_card
from tecnicas.c3 import pbir
from tecnicas.c1 import prototipo
from kibaku_nendo import relato
from tecnicas.c3 import sql
from tecnicas.c3 import tmdl
from kibaku_nendo.especificacao import distorcoes
from kibaku_nendo.util import gravar_json, gravar_texto, ident, ler_json, sha256_arquivo
from kibaku_nendo.comandos_apoio import (LIGACAO_PENDENTE, LONGEST_RELATIVO, aprovacao_valida,
                                         arquivo_da_aprovacao, carregar_argila, conferir_resumo,
                                         hashes_da_aprovacao, lembrete, mais_novo, mostrar_relatorio,
                                         resumo_do_modelo)


def cmd_validar(a):
    _, _, modelo, problemas, _ = carregar_argila(a.argila)
    if a.json:
        print(json.dumps({'ok': not problemas.erros, 'erros': problemas.erros, 'avisos': problemas.avisos,
                          'resumo': resumo_do_modelo(modelo)}, ensure_ascii=False, indent=2))
    else:
        print(relato.validacao(modelo, problemas, a.argila))
    return 1 if problemas.erros else 0


def cmd_prototipar(a):
    _, _, modelo, problemas, _ = carregar_argila(a.argila)
    pendentes = [e for e in problemas.erros if LIGACAO_PENDENTE in e]
    if pendentes and len(pendentes) == len(problemas.erros):
        # números fictícios: o gestor já pode reagir; a ligação vira pendência e o `aprovar` continua recusando
        problemas.erros = []
        for e in pendentes:
            problemas.aviso('[Ligações] ' + e.split(':')[0], 'ligação A CONFIRMAR: o protótipo mostra o painel SEM ela '
                            '(os números desta tabela não abrem pelos cortes dela); confirme com o dono do dado antes do '
                            'aceite')
        print(f'{len(pendentes)} ligação(ões) A CONFIRMAR: o protótipo sai com elas nas pendências; o `aprovar` só passa '
              'depois do `confirmar`.')
    if problemas.erros:
        mostrar_relatorio(problemas, modelo, a.argila)
        print('Protótipo não gerado: corrija os erros acima.')
        return 1
    saida = a.saida or os.path.splitext(a.argila)[0] + '.prototipo.html'
    gravar_texto(saida, prototipo.gerar_html(modelo, problemas, VERSAO))
    print(f'Protótipo: {saida}')
    lembrete('mostre o protótipo ao usuário e peça o aceite explícito; só com o "sim" rode '
              '`deidara.py aprovar argila.json --por NOME`.')
    return 0


def cmd_aprovar(a):
    _, _, modelo, problemas, caminhos = carregar_argila(a.argila)
    if problemas.erros:
        mostrar_relatorio(problemas, modelo, a.argila)
        print('Não dá para aprovar com erro de validação.')
        return 1
    if modelo['pendencias']:
        print('Não dá para aprovar com indicador sem definição (o gestor estaria aprovando um número sem significado):')
        for x in modelo['pendencias']:
            print(f'  · {x}')
        return 1
    prot = os.path.splitext(a.argila)[0] + '.prototipo.html'
    if not mais_novo(prot, a.argila, *caminhos):
        if not a.sem_prototipo:
            print('Não dá para aprovar: o protótipo não existe ou é anterior a esta versão do argila.json, e o gestor '
                  f'estaria aprovando algo que não viu. Gere (`deidara.py prototipar {a.argila}`), mostre e aprove de '
                  'novo. (Só se o gestor aprovou sem protótipo, de propósito: --sem-prototipo.)')
            return 1
        print('Atenção: aprovado SEM protótipo em dia (--sem-prototipo); isso fica registrado.', file=sys.stderr)
    graves = distorcoes(problemas.avisos)
    if graves and not a.aceito_distorcao:
        print(f'Não dá para aprovar: {len(graves)} número(s) sairiam distorcidos (o corte filtra só parte da conta):')
        for x in graves:
            print(f'  · {x}')
        print('Corrija o argila.json (tire o corte ou troque a medida) ou, se o gestor decidiu manter sabendo disso, '
              'aprove com --aceito-distorcao "motivo" (fica registrado).')
        return 1
    arq = arquivo_da_aprovacao(a.argila)
    anterior = ler_json(arq) if os.path.exists(arq) else None
    retrato = governanca.retrato(modelo)
    mudancas = governanca.diferencas(anterior['retrato'], retrato) if anterior and anterior.get('retrato') else []
    historico = (anterior or {}).get('historico', [])
    if a.resumo:
        conferido = conferir_resumo(a.resumo, modelo)
        if conferido:
            print(conferido)
            return 1
    reg = {'projeto': modelo['projeto'], 'versao': modelo['versao'], 'aprovado_por': a.por,
           'prototipo_sha256': sha256_arquivo(prot) if os.path.exists(prot) else None,
           'sem_prototipo': bool(a.sem_prototipo and not mais_novo(prot, a.argila, *caminhos)),
           'em': datetime.datetime.now().strftime('%d/%m/%Y %H:%M'), 'observacao': a.observacao or '',
           'avisos_aceitos': problemas.avisos, 'deidara': VERSAO, **hashes_da_aprovacao(a.argila, caminhos)}
    if graves:
        reg['distorcao_aceita'] = {'motivo': a.aceito_distorcao, 'avisos': graves}
    if anterior and (mudancas or not historico):
        historico = historico + [{'versao': reg['versao'], 'em': reg['em'], 'aprovado_por': a.por,
                                  'observacao': reg['observacao'], 'mudancas': mudancas}]
    elif not anterior:
        historico = [{'versao': reg['versao'], 'em': reg['em'], 'aprovado_por': a.por,
                      'observacao': reg['observacao'], 'mudancas': ['primeira versão aprovada']}]
    reg['historico'], reg['retrato'] = historico, retrato
    gravar_json(arq, reg)
    print(f'Katsu! Aprovado por {a.por} em {reg["em"]} ({len(problemas.avisos)} aviso(s) aceito(s)). '
          'A geração (`gerar`) está liberada.')
    for x in mudancas:
        print(f'  MUDOU  {x}')
    print(f'Registro: {arquivo_da_aprovacao(a.argila)}')
    return 0


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
        from tecnicas.bunshin import demo
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
    print(f'Katsu! Projeto {"de DEMONSTRAÇÃO (linhas fictícias embutidas) " if a.demo else ""}gerado em {pasta}')
    if a.demo:
        print('  Abra o .pbip e clique em Atualizar: as tabelas vêm do próprio projeto, sem banco nenhum.')
    print(f'  {nome}.pbip  ·  LEIA-ME.md  ·  HOMOLOGACAO.md' + ''.join(f'  ·  sql/{f["nome"]}/' for f in sql.fontes_sql(modelo)))
    print('Agora:')
    if a.demo:                               # sem banco: nada de DBA, só abrir, mostrar e, depois, gerar o real
        print(f'  1. [Analista] abrir {nome}.pbip no Power BI Desktop e clicar em Atualizar (nenhuma credencial)')
        print('  2. [Analista + gestor] conferir o painel com os números fictícios: layout, cortes e navegação')
        print('  3. [Analista] para o painel real, gerar de novo sem --demo (aí entram as views SQL e a homologação)')
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
    return 0


def cmd_diff(a):
    """O que mudou no argila.json desde a última aprovação (ou entre dois argila.json)."""
    _, _, modelo, problemas, _ = carregar_argila(a.argila)
    if a.contra:
        _, _, outro, _, _ = carregar_argila(a.contra)
        antes, rotulo = governanca.retrato(outro), a.contra
    else:
        arq = arquivo_da_aprovacao(a.argila)
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
