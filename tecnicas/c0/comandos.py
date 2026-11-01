"""
C0 · comandos: `deidara.py c0 estudar | propor | importar`.
"""

import json
import os

from kibaku_nendo.util import chave, gravar_texto
from tecnicas.c0 import exame, leitura, proposta, relato
from tecnicas.c0 import importar


def _ler(alvo):
    try:
        return leitura.ler(alvo)
    except (ValueError, OSError) as e:
        print(f'C0: {e}')
        return None


def _filtro(leg, medidas):
    if not medidas:
        return None, []
    nomes = {chave(n): n for n in leg['medidas']}
    faltam = [m for m in medidas if chave(m) not in nomes]
    return [nomes[chave(m)] for m in medidas if chave(m) in nomes], faltam


def cmd_c0(a):
    leg = _ler(a.alvo)
    if leg is None:
        return 1
    so, faltam = _filtro(leg, a.medida)
    if faltam:
        import difflib
        for f in faltam:
            sug = difflib.get_close_matches(f, list(leg['medidas']), n=3, cutoff=0.5)
            print(f'C0: medida "{f}" não está no que foi lido' + (f'; parecidas: {", ".join(sug)}' if sug else ''))
        return 1
    if not leg['medidas'] and a.acao != 'importar':
        print('C0: nenhuma medida no que foi lido (no .pbix, rode a receita DAX nova: `deidara.py receita dax`).')
        return 1
    estudo = exame.examinar(leg, so)
    if a.acao == 'importar':
        import re
        if not re.fullmatch(r'[\w\-]+', a.fonte or ''):
            print(f'C0: --fonte "{a.fonte}" deve ter só letras, números, _ e - (vira o nome do arquivo do catálogo)')
            return 1
        if not a.saida:
            print('C0 importar pede -o PASTA (a pasta do novo painel)')
            return 1
        if os.path.exists(a.saida) and os.listdir(a.saida) and not a.forcar:
            print(f'{a.saida} já existe e não está vazia: escolha outra pasta (ou --forcar)')
            return 1
        argila, avisos = importar.importar(leg, a.saida, a.fonte, a.projeto, a.manter_antigas, estudo)
        print(relato.resumo(leg, estudo))
        print(f'Painel refeito em {a.saida}: {len(argila["tabelas"])} tabela(s), {len(argila["medidas"])} medida(s), '
              f'{len(argila["paginas"])} página(s); o estudo completo está em c0_relatorio.md')
        for x in avisos:
            print(f'  ! {x}')
        print(f'Próximo passo: `deidara.py validar {os.path.join(a.saida, "argila.json")}` e leve as mudanças de número '
              'ao dono de cada indicador antes do protótipo (estão no c0_relatorio.md).')
        return 0
    propostas = None
    if a.acao == 'propor':
        propostas = {n: proposta.propor(n, leg, x, estudo['medidas']) for n, x in estudo['medidas'].items()}
    if a.json:
        dados = {'resumo': relato.resumo(leg, estudo), 'nota': estudo['nota'], 'modelo': estudo['modelo'],
                 'medidas': {n: {k: v for k, v in x.items() if k != 'arvore'} for n, x in estudo['medidas'].items()}}
        if propostas:
            for n, p in propostas.items():
                dados['medidas'][n]['proposta'] = p
        print(relato.mascarar(json.dumps(dados, ensure_ascii=False, indent=1)))
        return 0
    print(relato.terminal(leg, estudo, detalhe=bool(so) or a.acao == 'propor', propostas=propostas), end='')
    for x in leg.get('avisos') or []:
        print(f'! {x}')
    if a.acao == 'propor' and not so:
        for x in proposta.propor_modelo(leg, estudo):
            print(f'+ modelo: {x}')
    if a.saida:
        gravar_texto(a.saida, relato.markdown(leg, estudo, propostas=a.acao == 'propor'))
        print(f'Relatório: {a.saida}')
    if a.acao == 'estudar':
        print(f'Próximo passo: `deidara.py c0 propor "{a.alvo}"` (como cada medida fica no Deidara e o que muda) ou '
              f'`deidara.py c0 importar "{a.alvo}" -o <pasta do painel> --manter-antigas` (refaz o painel).')
    print('LEMBRETE: a nota diz se a fórmula está bem construída, não se o indicador é o certo para a decisão; leve '
          'o que "muda o número" ao dono do indicador antes de trocar.')
    return 0


def registrar(sub):
    c0 = sub.add_parser('c0', help='engenharia reversa: estuda, avalia e refaz um indicador ou painel que já existe')
    c0.add_argument('acao', choices=['estudar', 'propor', 'importar'])
    c0.add_argument('alvo', help='pasta do .pbip, resultado da receita DAX, arquivo .dax ou o próprio DAX entre aspas')
    c0.add_argument('--medida', action='append', help='só esta medida (repita para várias)')
    c0.add_argument('-o', '--saida', help='estudar/propor: grava o relatório em Markdown; importar: a pasta do painel')
    c0.add_argument('--json', action='store_true', help='o estudo em JSON (para outra ferramenta ler)')
    c0.add_argument('--fonte', default='legado', help='importar: nome da fonte do modelo antigo')
    c0.add_argument('--projeto', help='importar: nome do projeto')
    c0.add_argument('--manter-antigas', action='store_true', dest='manter_antigas',
                    help='importar: guarda as fórmulas antigas como "<nome> (antes)" para a homologação comparar')
    c0.add_argument('--forcar', action='store_true')
    c0.set_defaults(func=cmd_c0)
