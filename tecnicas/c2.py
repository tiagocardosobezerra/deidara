"""
================================================================================
 C2 — o dragão que solta a bomba certa em cada alvo
================================================================================
Nome de referência: o C2 é o dragão de argila do Deidara, que voa sobre o campo
e solta em cada alvo a bomba que serve para ele. Aqui ele lê a pergunta do
painel (o pedido e a decisão do briefing) e escolhe, no catálogo de técnicas
(dicionario/visuais.json), os visuais que respondem a ela:

    "como evoluiu?"            linha no tempo, no lugar das colunas
    "estamos na meta?"         tabela com a barra contra a meta e a pílula de status
    "quem está melhor/pior?"   tabela com o selo da posição no ranking
    "por que mudou / onde agir?"  página "Por que mudou": árvore de decomposição,
                               ranking de impacto e a frase do Tobi

Com calendário, o painel sempre ganha a frase de leitura do Tobi (o que o
indicador fez contra o ano anterior e quem puxou). As medidas novas usam os tipos
prontos do argila.json; o esboço ainda passa pela limpeza de corte que distorce.
"""

import re

from kibaku_nendo.util import chave, sem_acento

GATILHOS = {
    'causa': ('por que', 'porque', 'causa', 'explica', 'onde agir', 'reduzir', 'diminuir', 'aumentou', 'subiu',
              'caiu', 'piorou', 'melhorou', 'variacao', 'o que puxou', 'investigar'),
    'meta': ('meta', 'atingir', 'bater', 'alvo', 'objetivo', 'dentro do esperado'),
    'ranking': ('quem', 'pior', 'piores', 'melhor', 'melhores', 'ranking', 'maiores', 'menores', 'top', 'destaque'),
    'evolucao': ('evolucao', 'evoluiu', 'tendencia', 'ao longo', 'mes a mes', 'historico', 'comportamento',
                 'no tempo'),
}
LIMITE_DA_PAGINA = 12
ADITIVAS = ('contagem_linhas', 'contagem', 'soma')


def intencoes(*textos):
    """As perguntas que o painel precisa responder, lidas no pedido e na decisão do briefing."""
    texto = ' ' + re.sub(r'[^a-z0-9 ]+', ' ', sem_acento(' '.join(t or '' for t in textos)).lower()) + ' '
    return {k for k, palavras in GATILHOS.items() if any(f' {p} ' in texto for p in palavras)}


def _nova(argila, md):
    """Acrescenta a medida se o nome ainda não existe; devolve o nome."""
    if chave(md['nome']) not in {chave(x['nome']) for x in argila['medidas']}:
        argila['medidas'].append(md)
    return md['nome']


def soltar(argila, quer, notas):
    pg = argila['paginas'][0]
    vis = pg['visuais']
    principal = next((v['medida'] for v in vis if v['tipo'] == 'cartao'), None)
    if not principal:
        return
    medidas = {chave(x['nome']): x for x in argila['medidas']}
    cal = argila.get('calendario')
    cortes = [v['categoria'] for v in vis if v['tipo'] == 'barras' and principal in v.get('valores', [])]
    todos = [v['categoria'] for v in vis if v['tipo'] == 'barras']
    escolhas = []

    if 'evolucao' in quer:
        for v in vis:
            if v['tipo'] == 'colunas' and v.get('categoria', '').startswith('dCalendario['):
                v['tipo'] = 'linha'
                escolhas.append('linha no tempo ("como evoluiu?")')

    tabela = []                                     # a tabela da pergunta "quem" e "na meta?"
    if cortes and 'ranking' in quer:
        tabela.append(_nova(argila, {'nome': f'Posição em {principal}', 'tipo': 'svg_posicao', 'medida': principal,
                                     'categoria': cortes[0], 'descricao': f'Posição no ranking de {principal}.'}))
        escolhas.append('selo da posição no ranking ("quem está melhor ou pior?")')
    if cortes and 'meta' in quer and medidas.get(chave(principal), {}).get('meta') is not None:
        tabela.append(principal)
        tabela.append(_nova(argila, {'nome': f'{principal} x Meta', 'tipo': 'svg_barra_meta', 'medida': principal,
                                     'categoria': cortes[0], 'descricao': f'{principal} contra a meta, por linha.'}))
        tabela.append(_nova(argila, {'nome': f'Status de {principal}', 'tipo': 'svg_pilula', 'medida': principal,
                                     'categoria': cortes[0], 'descricao': f'Se {principal} está na meta, por linha.'}))
        escolhas.append('barra contra a meta e pílula de status ("estamos na meta?")')
    if tabela:
        if principal not in tabela:
            tabela.insert(1, principal)
        nova = {'tipo': 'tabela', 'campos': [cortes[0]] + tabela}
        k = next((i for i, v in enumerate(vis) if v['tipo'] == 'tabela'), None)
        if k is None:
            vis.append(nova)
        else:
            vis[k] = nova

    if not cal or not todos:
        if escolhas:
            notas.append('C2 escolheu pela pergunta: ' + '; '.join(escolhas))
        return
    anterior = _nova(argila, {'nome': f'{principal} Ano Anterior', 'tipo': 'ano_anterior', 'base': principal,
                              'descricao': f'{principal} no mesmo período do ano anterior.'})
    def leitura(nome, anterior_de, corte):            # a frase do Tobi sobre `nome`, com quem puxou em `corte`
        return _nova(argila, {'nome': f'Leitura de {nome}', 'tipo': 'leitura', 'medida': nome, 'comparar': anterior_de,
                              'categoria': corte,
                              'descricao': f'Frase que conta o que {nome} fez contra o ano anterior e quem puxou.'})

    if len(vis) < LIMITE_DA_PAGINA:                # na visão geral, logo depois dos cartões
        k = max((i for i, v in enumerate(vis) if v['tipo'] == 'cartao'), default=len(vis) - 1)
        vis.insert(k + 1, {'tipo': 'cartao', 'medida': leitura(principal, anterior, (cortes or todos)[0])})
        escolhas.append('a frase do Tobi (o que o indicador fez e quem puxou)')
    if 'causa' in quer:
        em_tela = {chave(n) for v in vis for n in [v.get('medida')] + v.get('valores', []) if n}
        aditiva = next((x['nome'] for x in argila['medidas'] if x.get('agregacao') in ADITIVAS
                        and chave(x['nome']) in em_tela), None) or principal
        base_ant = anterior if aditiva == principal else _nova(argila, {
            'nome': f'{aditiva} Ano Anterior', 'tipo': 'ano_anterior', 'base': aditiva,
            'descricao': f'{aditiva} no mesmo período do ano anterior.'})
        corte = todos[0]
        impacto = _nova(argila, {'nome': f'Impacto em {aditiva}', 'tipo': 'impacto', 'medida': aditiva,
                                 'comparar': base_ant, 'categoria': corte,
                                 'descricao': f'Quanto cada item mexeu em {aditiva} contra o ano anterior.'})
        causa = [{'tipo': 'segmentador', 'campo': 'dCalendario[Ano]'},
                 {'tipo': 'cartao', 'medida': leitura(aditiva, base_ant, corte)},
                 {'tipo': 'decomposicao', 'medida': aditiva, 'cortes': todos[:4]},
                 {'tipo': 'barras', 'categoria': corte, 'valores': [impacto]}]
        argila['paginas'].append({'nome': 'Por que mudou', 'descricao': f'O que puxou {aditiva} e onde agir.',
                                  'visuais': causa})
        escolhas.append('página "Por que mudou" com árvore de decomposição, ranking de impacto e a frase do Tobi '
                        '("por que mudou? onde agir?")')
    notas.append('C2 escolheu pela pergunta: ' + '; '.join(escolhas))
