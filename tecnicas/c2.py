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
                 'no tempo', 'sinal', 'ruido', 'estavel', 'normal'),
    'fora': ('fora da curva', 'fora do padrao', 'outlier', 'destoa', 'destoam', 'quem esta fora', 'atipico'),
    'sazonal': ('sazonal', 'sazonalidade', 'todo ano', 'mes do ano', 'epoca do ano', 'sempre nessa epoca'),
    'previsao': ('previsao', 'projecao', 'vai fechar', 'fechar o ano', 'como vai terminar'),
    'anomalia': ('anomalia', 'anomalias', 'mes estranho', 'fora do comum', 'pico estranho'),
    'faixa': ('mediana', 'faixa', 'tipico', 'distribuicao', 'quartil', 'quartis'),
}
ADITIVAS_DE_VALOR = ('media',)
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


def _c4(argila, quer, principal, medidas, vis, cortes, cal, escolhas):
    """As técnicas do C4 Karura (estatística) que a pergunta pede. O fora da curva pinta as barras que já existem; o
    resto vai para a página "Sinal ou ruído", para não lotar a visão geral."""
    if cortes and ('fora' in quer or 'ranking' in quer):
        barras = next(v for v in vis if v['tipo'] == 'barras' and v.get('categoria') == cortes[0])
        nome = _nova(argila, {'nome': f'Fora da curva em {principal}', 'tipo': 'fora_da_curva', 'medida': principal,
                              'categoria': cortes[0],
                              'descricao': f'Quantos desvios cada item está do padrão de {principal} (C4 Karura).'})
        barras['cor'] = f'Cor {nome}'
        escolhas.append('barras pintadas pelo fora da curva ("quem está fora do padrão?")')
    if not cal:
        return
    sinal = []
    if quer & {'evolucao', 'meta', 'causa'}:
        controle = _nova(argila, {'nome': f'Controle de {principal}', 'tipo': 'controle', 'medida': principal,
                                  'descricao': f'Centro do gráfico de controle de {principal} (C4 Karura).'})
        sinal.append({'tipo': 'controle', 'medida': controle})
        if 'meta' in quer and medidas.get(chave(principal), {}).get('meta') is not None:
            sinal.append({'tipo': 'cartao', 'medida': f'{controle} · meta x faixa'})
        escolhas.append('gráfico de controle ("isso é sinal ou ruído?")')
    if 'sazonal' in quer:
        sinal.append({'tipo': 'linha', 'categoria': f'{cal}[Nome do Mês]', 'legenda': f'{cal}[Ano]',
                      'valores': [principal], 'titulo': f'{principal}: esse mês é sempre assim?'})
        escolhas.append('uma linha por ano ("esse mês é sempre assim?")')
    if quer & {'previsao', 'anomalia'}:
        o_que = 'previsao' if 'previsao' in quer else 'anomalias'
        sinal.append({'tipo': 'linha', 'categoria': f'{cal}[Mês/Ano]', 'valores': [principal], o_que: True,
                      'titulo': f'{principal}: ' + ('como vai fechar?' if o_que == 'previsao' else 'teve mês estranho?')})
        escolhas.append('linha para a ' + ('previsão' if o_que == 'previsao' else 'detecção de anomalia')
                        + ' do Power BI (ligar no painel Análise)')
    media_de_valor = next((x for x in argila['medidas'] if x.get('agregacao') in ADITIVAS_DE_VALOR and x.get('coluna')
                           and chave(x['nome']) in {chave(n) for v in vis for n in [v.get('medida')] + v.get('valores', [])
                                                    if n}), None)
    if 'faixa' in quer and media_de_valor and cortes:
        col, nome = media_de_valor['coluna'], media_de_valor['nome']
        partes = [_nova(argila, {'nome': f'{nome} · {rot}', 'agregacao': ag, 'coluna': col,
                                 'formato': media_de_valor.get('formato', 'decimal'),
                                 'descricao': f'{desc} de {nome.lower()} (a faixa típica, sem o puxão dos extremos).'})
                  for ag, rot, desc in (('quartil_1', 'quartil de baixo', 'O valor abaixo do qual fica um quarto'),
                                        ('mediana', 'mediana', 'O valor do meio'),
                                        ('quartil_3', 'quartil de cima', 'O valor abaixo do qual ficam três quartos'))]
        sinal.append({'tipo': 'tabela', 'campos': [cortes[0]] + partes + [nome],
                      'titulo': f'{nome}: qual é o normal?'})
        escolhas.append('faixa típica com mediana e quartis ("qual é o normal aqui?")')
    if sinal:
        argila['paginas'].append({'nome': 'Sinal ou ruído', 'descricao': f'O que é variação normal em {principal} e o '
                                  'que merece atenção.', 'visuais': [{'tipo': 'segmentador', 'campo': f'{cal}[Ano]'}]
                                  + sinal})


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

    _c4(argila, quer, principal, medidas, vis, cortes, (cal.get('tabela') or 'dCalendario') if cal else None, escolhas)
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
