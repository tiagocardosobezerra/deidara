#!/usr/bin/env python3
"""
A bateria de ponta a ponta: todo comando do Deidara, rodado como quem usa roda (python deidara.py ...), numa
pasta e numa "casa" temporárias (o ~/.deidara de quem roda não é tocado). Cada passo confere o código de saída
e um trecho da resposta; no fim, o placar.

    python3 ferramentas/ponta_a_ponta.py [--desktop] [--manter PASTA]

Cobre: novo, receitas (sql, dax, m, funções, prova), catalogar (fonte e funções), buscar, relacionar, provar,
confirmar, esbocar, validar (texto e --json), situacao, prototipar, aprovar (com --resumo), diff, gerar (real e
--demo), validar_pbip, memory-card (iniciar, enviar, catalogo, buscar, marcar, conferir, desligar), funcoes,
padroes, modelos, visuais, galeria (e --ver), c0 (estudar, propor, importar), onoki, avaliar, status, a vitrine
nos doze modelos, a referência, o pacote da skill e a skill instalada numa pasta só de leitura. Com --desktop
(Windows com Power BI Desktop), o conferir-desktop abre e confere a vitrine.
"""

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AURORA = os.path.join(RAIZ, 'exemplos', 'aurora')
LEGADO = os.path.join(RAIZ, 'exemplos', 'legado')
VITRINE = os.path.join(RAIZ, 'exemplos', 'vitrine')


class Bateria:
    def __init__(self, pasta, raiz=RAIZ):
        self.pasta, self.raiz = pasta, raiz
        self.casa = os.path.join(pasta, 'casa')
        os.makedirs(self.casa, exist_ok=True)
        self.env = dict(os.environ, HOME=self.casa, USERPROFILE=self.casa, PYTHONIOENCODING='utf-8',
                        DEIDARA_LOCAL=os.path.join(self.casa, '.deidara'),
                        GIT_AUTHOR_NAME='Bateria', GIT_AUTHOR_EMAIL='bateria@exemplo.invalid',
                        GIT_COMMITTER_NAME='Bateria', GIT_COMMITTER_EMAIL='bateria@exemplo.invalid')
        for k in ('DEIDARA_MEMORY_CARD_DIR', 'DEIDARA_MEMORY_CARD_REPO', 'DEIDARA_TREINO'):
            self.env.pop(k, None)
        self.resultados = []

    def rodar(self, nome, args, codigo=0, contem=(), entrada=None, script='deidara.py'):
        cmd = [sys.executable, os.path.join(self.raiz, script)] + [str(a) for a in args]
        r = subprocess.run(cmd, capture_output=True, env=self.env, cwd=self.pasta, input=entrada, timeout=900)
        saida = (r.stdout + r.stderr).decode('utf-8', 'replace')
        faltam = [t for t in contem if t not in saida]
        ok = (codigo is None or r.returncode == codigo) and not faltam
        self.resultados.append((ok, nome, '' if ok else f'código {r.returncode} (esperado {codigo})'
                                + (f'; faltou "{faltam[0]}"' if faltam else '') + f'\n      {saida.strip()[-400:]}'))
        print(f'{"✓" if ok else "✗"} {nome}', flush=True)
        return saida

    def checar(self, nome, condicao, detalhe=''):
        self.resultados.append((bool(condicao), nome, detalhe))
        print(f'{"✓" if condicao else "✗"} {nome}', flush=True)


def fluxo_do_zero(b):
    """O caminho do usuário: pasta nova, receitas, colar, catalogar, esboçar, validar, protótipo, aceite, gerar."""
    p = os.path.join(b.pasta, 'painel')
    b.rodar('novo', ['novo', p, '--projeto', 'Turnover Bateria'], contem=['Pasta do painel criada'])
    for tipo in ('sql', 'dax', 'm', 'funcoes-dax', 'funcoes-m'):
        b.rodar(f'receita {tipo}', ['receita', tipo, '-o', os.path.join(p, 'receitas', f'r_{tipo}.txt')])
    shutil.copy(os.path.join(AURORA, 'colado', 'erp_receita_sql.txt'), os.path.join(p, 'colado', 'erp.txt'))
    shutil.copy(os.path.join(AURORA, 'colado', 'metas_receita_m.txt'), os.path.join(p, 'colado', 'metas.txt'))
    shutil.copytree(os.path.join(AURORA, 'colado', 'm'), os.path.join(p, 'colado', 'm'), dirs_exist_ok=True)
    b.rodar('catalogar sql', ['catalogar', '--de', os.path.join(p, 'colado', 'erp.txt'), '--fonte', 'erp',
                              '-o', os.path.join(p, 'catalogos', 'erp.json')], contem=['Catálogo'])
    b.rodar('catalogar m', ['catalogar', '--de', os.path.join(p, 'colado', 'metas.txt'), '--fonte', 'metas',
                            '--m', os.path.join(p, 'colado', 'm'), '-o', os.path.join(p, 'catalogos', 'metas.json')],
            contem=['Catálogo'])
    funcoes = os.path.join(p, 'colado', 'funcoes.txt')
    with open(funcoes, 'w', encoding='utf-8') as f:
        f.write('FUNCTION_NAME\tDESCRIPTION\nSUMX\tsoma linha a linha\nFUNCAOLOCALDEIDARA\tfunção da versão local\n')
    b.rodar('catalogar funções (dicionário local)', ['catalogar', '--de', funcoes, '--funcoes', 'dax'])
    cats = [os.path.join(p, 'catalogos', 'erp.json'), os.path.join(p, 'catalogos', 'metas.json')]
    b.rodar('buscar', ['buscar', 'desligamentos por motivo', '--catalogos'] + cats, contem=['F_DESLIGAMENTO'])
    b.rodar('relacionar', ['relacionar', '--catalogos'] + cats)
    b.rodar('esbocar', ['esbocar', p, '--pedido', 'desligamentos por motivo e cargo com a meta de turnover por empresa'],
            contem=['Esboço'])
    arq = os.path.join(p, 'argila.json')
    b.rodar('validar (ligação a confirmar)', ['validar', arq], codigo=1, contem=['confirmar'])
    b.rodar('confirmar sem --por', ['confirmar', arq, '--ligacao', 'fMetas->dEmpresa'], codigo=2)
    b.rodar('receita prova', ['receita', 'prova', '--argila', arq, '--de', 'fMetas[Cód. Empresa]',
                              '--para', 'dEmpresa[CODEMPRESA]', '-o', os.path.join(p, 'receitas', 'prova.sql')])
    b.rodar('confirmar', ['confirmar', arq, '--ligacao', 'fMetas->dEmpresa', '--por', 'Dona do dado'],
            contem=['confirmada'])
    prova = os.path.join(p, 'colado', 'prova.txt')
    with open(prova, 'w', encoding='utf-8') as f:
        f.write('de\tpara\tpct_nulos_filha\tpct_linhas_com_par\tpct_codigos_com_par\tmae_unica\n'
                'fMetas[Cód. Empresa]\tdEmpresa[CODEMPRESA]\t0\t100\t100\tsim\n')
    b.rodar('provar', ['provar', '--de', prova, '--argila', arq])
    with open(arq, encoding='utf-8') as f:
        a = json.load(f)
    a['descricao'], a['publico'] = 'Onde o turnover passou da meta e por quê.', 'Diretoria de RH'
    with open(arq, 'w', encoding='utf-8') as f:
        json.dump(a, f, ensure_ascii=False, indent=2)
    b.rodar('validar', ['validar', arq])
    saida = b.rodar('validar --json', ['validar', arq, '--json'])
    b.checar('validar --json é JSON', saida.strip().startswith('{') and '"ok": true' in saida)
    b.rodar('situacao (antes do protótipo)', ['situacao', arq], contem=['prototipar'])
    b.rodar('gerar sem aceite', ['gerar', arq, '-o', os.path.join(p, 'pbi')], codigo=1, contem=['Sem aprovação'])
    b.rodar('prototipar', ['prototipar', arq], contem=['Protótipo'])
    b.rodar('aprovar', ['aprovar', arq, '--por', 'Gestora', '--aceito-distorcao', 'teste da bateria'],
            contem=['Aprovado'])
    b.rodar('diff (sem mudança)', ['diff', arq])
    b.rodar('gerar', ['gerar', arq, '-o', os.path.join(p, 'pbi')], contem=['Projeto gerado'])
    b.rodar('validar_pbip (real)', [os.path.join(p, 'pbi')], script='ferramentas/validar_pbip.py', contem=['OK'])
    b.rodar('gerar --demo', ['gerar', arq, '-o', os.path.join(p, 'demo'), '--demo'], contem=['DEMONSTRAÇÃO'])
    b.rodar('validar_pbip (demo)', [os.path.join(p, 'demo')], script='ferramentas/validar_pbip.py', contem=['OK'])
    pbi = os.path.join(p, 'pbi')
    for arquivo in ('LEIA-ME.md', 'HOMOLOGACAO.md', os.path.join('docs', 'dicionario_indicadores.md'),
                    os.path.join('sql', 'erp', '01_views.sql'), os.path.join('sql', 'erp', '02_conferencia.sql'),
                    os.path.join('sql', 'erp', '03_qualidade.sql')):
        b.checar(f'entrega: {arquivo}', os.path.exists(os.path.join(pbi, arquivo)))
    a['medidas'][0]['descricao'] += ' (revisada)'
    with open(arq, 'w', encoding='utf-8') as f:
        json.dump(a, f, ensure_ascii=False, indent=2)
    b.rodar('gerar depois de mudar (recusa)', ['gerar', arq, '-o', os.path.join(p, 'pbi2')], codigo=1)
    b.rodar('diff (mudou)', ['diff', arq], contem=['mudou'])
    b.rodar('situacao (depois de mudar)', ['situacao', arq])
    return arq


def memory_card(b, arq):
    cartao = os.path.join(b.pasta, 'cartao')
    b.rodar('memory-card iniciar', ['memory-card', 'iniciar', '--pasta', cartao])
    b.rodar('memory-card enviar painel mudado (recusa)', ['memory-card', 'enviar', arq, '--categoria', 'Recursos Humanos',
                                                          '--secao', 'Turnover'], codigo=1, contem=['aprove de novo'])
    b.rodar('prototipar de novo', ['prototipar', arq])
    b.rodar('aprovar de novo', ['aprovar', arq, '--por', 'Gestora', '--aceito-distorcao', 'teste'])
    b.rodar('memory-card enviar (prévia)', ['memory-card', 'enviar', arq, '--categoria', 'Recursos Humanos',
                                            '--secao', 'Turnover', '--motivo', 'bateria'])
    b.rodar('memory-card enviar --confirmar', ['memory-card', 'enviar', arq, '--categoria', 'Recursos Humanos',
                                               '--secao', 'Turnover', '--motivo', 'bateria', '--confirmar'])
    b.rodar('memory-card catalogo', ['memory-card', 'catalogo'], contem=['Turnover'])
    b.rodar('memory-card buscar', ['memory-card', 'buscar', 'turnover'], contem=['Turnover'])
    saida = b.rodar('memory-card buscar --json', ['memory-card', 'buscar', 'turnover', '--json'])
    try:
        achados = json.loads(saida)
    except ValueError:
        achados = []
    b.checar('memory-card buscar --json é JSON', bool(achados), saida[:200])
    b.checar('cartão sem medida técnica escondida', not any('limite' in (x.get('titulo') or '') for x in achados),
             ', '.join(x.get('titulo') or '' for x in achados))
    saida = b.rodar('memory-card catalogo --json', ['memory-card', 'catalogo', '--json'])
    b.checar('memory-card catalogo --json é JSON', saida.strip().startswith('['), saida[:200])
    ref = next((x['ref'] for x in achados if x.get('tipo') == 'indicador'), None)
    if ref:
        b.rodar('memory-card marcar', ['memory-card', 'marcar', ref, '--status', 'em-uso',
                                       '--motivo', 'bateria'])
    else:
        b.checar('memory-card: referência no resultado da busca', False, saida[-300:])
    b.rodar('memory-card conferir', ['memory-card', 'conferir', '--catalogos',
                                     os.path.join(b.pasta, 'painel', 'catalogos', 'erp.json')])
    b.rodar('memory-card marcar sem --status', ['memory-card', 'marcar', 'x'], codigo=2)
    b.rodar('memory-card desligar', ['memory-card', 'desligar'])


def consultas(b):
    b.rodar('funcoes buscar', ['funcoes', 'buscar', 'acumulado'], contem=['TOTALYTD'])
    b.rodar('funcoes ver', ['funcoes', 'ver', 'SAMEPERIODLASTYEAR'], contem=['SAMEPERIODLASTYEAR'])
    b.rodar('funcoes ver (M)', ['funcoes', 'ver', 'Table.SelectRows', '--linguagem', 'm'])
    b.rodar('funcoes ver (local)', ['funcoes', 'ver', 'FUNCAOLOCALDEIDARA'], contem=['FUNCAOLOCALDEIDARA'])
    b.rodar('padroes', ['padroes'], contem=['Turnover'])
    b.rodar('padroes turnover', ['padroes', 'turnover'], contem=['HC Médio'])
    b.rodar('modelos', ['modelos'], contem=['faixa-de-kpis'])
    b.rodar('visuais', ['visuais', 'meta'])
    b.rodar('galeria', ['galeria', 'cascata'], contem=['waterfall'])
    b.rodar('galeria --ver', ['galeria', '--ver', 'deneb-vega-templates/ranking/slope'], contem=['Value 1'])
    b.rodar('galeria funções', ['galeria', 'minigrafico', '--tipo', 'funcoes_dax'], contem=['DaxLib'])
    b.rodar('status', ['status'], contem=['Deidara'])
    b.rodar('sem argumentos (roteiro)', [], contem=['Por onde começar'])
    b.rodar('comando errado', ['gerra'], codigo=2, contem=['gerar'])


def c0_e_onoki(b):
    saida = os.path.join(b.pasta, 'c0')
    b.rodar('c0 estudar', ['c0', 'estudar', LEGADO, '-o', os.path.join(b.pasta, 'c0_estudo.md')])
    b.rodar('c0 estudar --json', ['c0', 'estudar', LEGADO, '--json'])
    b.rodar('c0 estudar (DAX colado)', ['c0', 'estudar', 'Turnover = DIVIDE([Desligamentos], COUNTROWS(dColaborador))'])
    b.rodar('c0 propor', ['c0', 'propor', LEGADO, '-o', os.path.join(b.pasta, 'c0_proposta.md')])
    b.rodar('c0 importar', ['c0', 'importar', LEGADO, '-o', saida, '--manter-antigas'])
    if os.path.exists(os.path.join(saida, 'argila.json')):
        b.rodar('c0 importado: validar', ['validar', os.path.join(saida, 'argila.json')], codigo=None)
    b.rodar('onoki', ['onoki', '--casos', os.path.join(AURORA, 'onoki.json'), '--catalogos',
                      os.path.join(AURORA, 'catalogos', 'erp.json'), os.path.join(AURORA, 'catalogos', 'metas.json')])
    b.rodar('avaliar', [os.path.join(AURORA, 'avaliacao.json')], script='ferramentas/avaliar.py')


def vitrine_e_referencia(b, desktop=False):
    b.rodar('vitrine nos 12 modelos', [os.path.join(b.pasta, 'vitrines')] + (['--desktop'] if desktop else []),
            script='ferramentas/vitrine.py')
    b.rodar('referência', [], script='ferramentas/referencia.py', contem=['igual à referência'])


def instalada(b):
    """O pacote da skill, descompactado numa pasta só de leitura (como no claude.ai), fazendo o fluxo."""
    zipado = os.path.join(b.pasta, 'skill.zip')
    b.rodar('empacotar', ['-o', zipado, '--sem-conferir-git'], script='ferramentas/empacotar.py')
    if not os.path.exists(zipado):
        return
    destino = os.path.join(b.pasta, 'instalada')
    with zipfile.ZipFile(zipado) as z:
        b.checar('pacote com até 200 arquivos', len(z.namelist()) <= 200, str(len(z.namelist())))
        z.extractall(destino)
    skill = os.path.join(destino, 'deidara')
    for pasta, _, nomes in os.walk(skill):                       # só leitura: nada pode ser gravado ali
        for n in nomes:
            os.chmod(os.path.join(pasta, n), stat.S_IREAD)
    copia = Bateria(os.path.join(b.pasta, 'na_instalada'), raiz=skill)
    copia.env = b.env
    p = os.path.join(copia.pasta, 'painel')
    os.makedirs(p, exist_ok=True)
    shutil.copytree(os.path.join(VITRINE, 'catalogos'), os.path.join(p, 'catalogos'))
    shutil.copy(os.path.join(VITRINE, 'argila.json'), p)
    arq = os.path.join(p, 'argila.json')
    for nome, args, contem in (('instalada: status', ['status'], ['Deidara']),
                               ('instalada: validar', ['validar', arq], []),
                               ('instalada: buscar (treino)', ['buscar', 'desligamentos', '--argila', arq], []),
                               ('instalada: prototipar', ['prototipar', arq], ['Protótipo']),
                               ('instalada: aprovar', ['aprovar', arq, '--por', 'T', '--aceito-distorcao', 't'], []),
                               ('instalada: gerar --demo', ['gerar', arq, '-o', os.path.join(p, 'pbi'), '--demo'],
                                ['DEMONSTRAÇÃO']),
                               ('instalada: galeria', ['galeria', 'cascata'], ['waterfall'])):
        copia.rodar(nome, args, contem=contem)
    b.resultados += copia.resultados
    for pasta, _, nomes in os.walk(skill):
        for n in nomes:
            os.chmod(os.path.join(pasta, n), stat.S_IWRITE | stat.S_IREAD)


def main(argv=None):
    ap = argparse.ArgumentParser(description='a bateria de ponta a ponta do Deidara')
    ap.add_argument('--desktop', action='store_true', help='também abre a vitrine no Power BI Desktop (Windows)')
    ap.add_argument('--manter', help='roda nesta pasta e não apaga no fim')
    a = ap.parse_args(argv)
    pasta = a.manter or tempfile.mkdtemp(prefix='deidara_bateria_')
    os.makedirs(pasta, exist_ok=True)
    b = Bateria(pasta)
    arq = fluxo_do_zero(b)
    memory_card(b, arq)
    consultas(b)
    c0_e_onoki(b)
    vitrine_e_referencia(b, a.desktop)
    instalada(b)
    falhas = [r for r in b.resultados if not r[0]]
    print(f'\n{len(b.resultados) - len(falhas)} de {len(b.resultados)} passos certos')
    for _, nome, detalhe in falhas:
        print(f'  ✗ {nome}: {detalhe}')
    if not a.manter:
        shutil.rmtree(pasta, ignore_errors=True)
    return 1 if falhas else 0


if __name__ == '__main__':
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, 'reconfigure'):
            fluxo.reconfigure(encoding='utf-8')
    sys.exit(main())
