"""
Os comandos da Luneta: receita, catalogar, buscar, relacionar, provar e confirmar (a fonte vista de
longe, sem conexão).
"""

import json
import os

from tecnicas.luneta import descoberta
from tecnicas import sasori as dicionario
from tecnicas.luneta import prova
from tecnicas.luneta import receitas
from kibaku_nendo.util import gravar_json, gravar_texto, ler_json
from kibaku_nendo.comandos_apoio import carregar_catalogos, lembrete, ponta_da_ligacao


def cmd_receita(a):
    if a.tipo == 'prova':
        cats, modelo = carregar_catalogos(a)
        de, para = ponta_da_ligacao(cats, modelo, a.de), ponta_da_ligacao(cats, modelo, a.para)
        if de['fonte'] == para['fonte'] and de['tipo'] == 'sqlserver':
            texto = prova.receita_sql((de['origem'], de['coluna'], de['rotulo']), (para['origem'], para['coluna'], para['rotulo']),
                                      de['esquema'], para['esquema'])
        else:
            texto = prova.receita_m(de, para)
        if a.saida:
            gravar_texto(a.saida, texto, bom=texto.startswith('/*'))
            print(f'Receita de prova em {a.saida}')
        else:
            print(texto)
        lembrete('esta receita conta (percentuais e sim/não, nenhuma linha). Com o resultado colado: '
                  f'`deidara.py provar --de resultado.txt --argila {a.argila or "argila.json"}` (grava a prova na ligação).')
        return 0
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
    lembrete('a pessoa roda a receita onde os dados estão, copia a grade com o cabeçalho para um .txt e você roda '
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
    pasta_de = os.path.dirname(os.path.abspath(a.de))
    pasta_cat = os.path.join(os.path.dirname(pasta_de), 'catalogos')
    if not a.saida and os.path.basename(pasta_de) == 'colado' and os.path.isdir(pasta_cat):
        saida = os.path.join(pasta_cat, f'{a.fonte}.json')          # pasta criada pelo `novo`
    else:
        saida = a.saida or os.path.join(pasta_de, f'{a.fonte}.catalogo.json')
    gravar_json(saida, cat)
    ncol = sum(len(t['colunas']) for t in cat['tabelas'].values())
    print(f'Fonte {a.fonte} ({cat["tipo"]}, receita {cat["receita"]}): {len(cat["tabelas"])} tabela(s), {ncol} coluna(s), '
          f'{len(cat["fks"])} ligação(ões), {len(cat["expressoes"])} expressão(ões) auxiliar(es)')
    for x in avisos:
        print(f'  AVISO  {x}')
    print(f'Catálogo: {saida}')
    if os.path.basename(os.path.dirname(os.path.abspath(saida))) == 'catalogos':
        print(f'Próximo passo: `deidara.py esbocar {os.path.dirname(os.path.dirname(os.path.abspath(saida)))} --pedido "..."` '
              '(ou, se o argila.json já existe, aponte este catálogo em "fontes")')
    else:
        lembrete(f'aponte no argila.json: "fontes": {{"{a.fonte}": {{"catalogo": "<caminho relativo de '
                  f'{os.path.basename(saida)}>"}}}}')
    return 0


def cmd_buscar(a):
    cats, _ = carregar_catalogos(a)
    achados = descoberta.buscar(cats, a.pedido, a.limite)
    if not achados:
        print('Nada encontrado. Tente palavras do negócio mais gerais, ou acrescente sinônimos em dicionario/sinonimos.json.')
        return 0
    for i, r in enumerate(achados, 1):
        print(f'{i:>2}. {r["fonte"]} · {r["tabela"]}  (pontos {str(r["pontos"]).replace(".", ",")})'
              + (f' — {r["descricao"]}' if r['descricao'] else ''))
        if r['colunas']:
            print(f'      colunas: {", ".join(r["colunas"][:8])}')
    lembrete('confirme com o usuário as tabelas antes de montar o argila.json; depois rode `relacionar`.')
    return 0


def cmd_relacionar(a):
    cats, modelo = carregar_catalogos(a)
    if modelo:
        tabelas = [(t['fonte'], t['origem'], t['nome']) for t in modelo['tabelas'] if t.get('origem')]
        ja = {(r['de'], r['para']) for r in modelo['relacionamentos']}
    else:
        filtro = {x.strip().upper() for x in (a.tabelas or '').split(',') if x.strip()}
        if a.pedido and not filtro:
            filtro = {r['tabela'].upper() for r in descoberta.buscar(cats, a.pedido, 15)}
            print(f'Tabelas do pedido (pela busca): {", ".join(sorted(filtro))}')
        tabelas = [(n, t['nome'], t['nome']) for n, f in cats.items() for t in f.tabelas.values()
                   if not filtro or t['nome'].upper() in filtro]
        ja = set()
        if len(tabelas) > 40:
            print(f'{len(tabelas)} tabelas é demais para sugerir ligações de uma vez (o resultado seria ilegível). '
                  'Diga o assunto com --pedido "<o que o painel mostra>" ou escolha com --tabelas T1,T2,...')
            return 1
    sugestoes = descoberta.relacionar(cats, tabelas, ja)
    escondidas = []
    if not a.todas and len(sugestoes) > 25:
        sugestoes, escondidas = sugestoes[:25], sugestoes[25:]
    if not sugestoes:
        print('Nenhuma ligação candidata. Se as tabelas se ligam, os nomes das colunas não deixam isso claro: '
              'pergunte ao dono do dado e acrescente sinônimos em dicionario/sinonimos.json.')
    for i, s in enumerate(sugestoes, 1):
        selo = 'PROVADA NO CATÁLOGO' if s['provada_no_catalogo'] else f'confiança {s["confianca"]}'
        if s.get('redundante'):
            selo += '; redundante se aceitar as de cima'
        print(f'{i:>2}. {s["de"]}[{s["campo_filho"]}] -> {s["para"]}[{s["campo_mae"]}]  ({selo}, {s["pontos"]} pts)')
        for mo in s['motivos']:
            print(f'      · {mo}')
        if not s['provada_no_catalogo'] and a.json:
            print('      ' + json.dumps(descoberta.trecho_argila(s), ensure_ascii=False))
    if escondidas:
        conf = sorted({s['confianca'] for s in escondidas})
        print(f'    … mais {len(escondidas)} sugestão(ões) ({", ".join(conf)}): use --todas para ver')
    ligadas = {n for s in sugestoes + escondidas for n in (s['de'], s['para'])} | {n for par in ja for n in par}
    soltas = [n for _, _, n in tabelas if n not in ligadas]
    if soltas:
        print(f'Sem nenhuma ligação nem candidata: {", ".join(soltas)}')
    lembrete('nenhuma sugestão vira ligação sozinha: confirme os campos com o dono do dado, declare com "por" e, '
              'se puder, prove: `deidara.py receita prova --de "T[C]" --para "T[C]"`.')
    return 0


def cmd_provar(a):
    cab, linhas = receitas.ler_colado(a.de)
    provas = prova.ler(linhas)
    if not provas:
        print(f'{a.de}: não é resultado da receita de prova (cabeçalho: {", ".join(cab[:6])})')
        return 1
    argila = ler_json(a.argila) if a.argila else None
    for pv in provas:
        veredito, explicacao = prova.avaliar(pv)
        print(f'{pv["de"]} -> {pv["para"]}: {veredito.upper()} — {explicacao}')
        bloco = {k: v for k, v in pv.items() if k not in ('de', 'para')}
        if argila is None:
            print('  rode com --argila argila.json para gravar a prova na ligação (o bloco nunca se escreve à mão)')
            continue
        de, para = pv['de'].split('[')[0], pv['para'].split('[')[0]
        alvo = next((r for r in argila.get('relacionamentos', []) if r.get('declarada')
                     and r.get('de', '').upper() == de.upper() and r.get('para', '').upper() == para.upper()), None)
        if not alvo:
            print(f'  nenhuma ligação declarada {de} -> {para} no argila.json: declare (ou confirme) antes de provar')
            continue
        alvo['declarada']['prova'] = bloco
        gravar_json(a.argila, argila)
        print(f'  prova gravada na ligação {de} -> {para} do {a.argila}')
    return 0


def cmd_confirmar(a):
    """Confirma uma ligação sugerida ("A CONFIRMAR") com o nome de quem confirmou com o dono do dado."""
    argila = ler_json(a.argila)
    de, _, para = a.ligacao.replace(' ', '').partition('->')
    pend = [r for r in argila.get('relacionamentos', []) if r.get('declarada')]
    alvo = next((r for r in pend if r['de'].upper() == de.upper() and r['para'].upper() == para.upper()), None)
    if not alvo:
        opcoes = ', '.join(f'{r["de"]}->{r["para"]}' for r in pend) or 'nenhuma'
        print(f'Ligação {a.ligacao} não encontrada entre as declaradas ({opcoes}).')
        return 1
    if a.remover:
        argila['relacionamentos'].remove(alvo)
        gravar_json(a.argila, argila)
        print(f'Ligação {de}->{para} removida (o dono do dado não confirmou).')
        return 0
    alvo['declarada']['por'] = a.por
    if a.motivo:
        alvo['declarada']['motivo'] = a.motivo
    gravar_json(a.argila, argila)
    print(f'Ligação {de}->{para} confirmada por {a.por}. Para provar com números: '
          f'`deidara.py receita prova --argila {a.argila} --de "{de}[{alvo["declarada"]["campos"][0][0]}]" '
          f'--para "{para}[{alvo["declarada"]["campos"][0][1]}]"`')
    return 0
