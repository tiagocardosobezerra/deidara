"""
A guarda de legibilidade: o que o Deidara corrige por cima do estilo de origem, sempre, em todo modelo.

O estilo de cada modelo de layout vem do dashboard de onde ele saiu (terceiros/power-bi-design-files/estilos.json)
e fica como o autor fez. Algumas escolhas de lá não servem para um painel gerado, e só apareceram com o projeto
aberto no Power BI Desktop (31/10/2026). Elas ficam corrigidas aqui, depois de o estilo entrar, e não no arquivo
de terceiros:

- a linha no tempo sem o eixo dos meses: o leitor não sabe de que mês é cada ponto;
- o nome do item cortado ou escondido no eixo das barras ("Departam..."): eixo visível, margem de 45%;
- o seletor de estado antigo no segmentador de botões ("selected", "hover"), que passa no schema e o Desktop
  ignora calado (o texto do botão escolhido ficava branco no branco);
- o texto do botão 100% transparente (o dashboard do kpis-clicaveis usava imagem no botão): os botões de
  período e as abas saíam vazios.
"""

import copy

ESTADOS = {'selected': 'selection:selected', 'hover': 'interaction:hover', 'press': 'interaction:press',
           'rest': 'interaction:rest'}


def _lit(valor):
    if isinstance(valor, bool):
        return {'expr': {'Literal': {'Value': 'true' if valor else 'false'}}}
    if isinstance(valor, int):
        return {'expr': {'Literal': {'Value': f'{valor}D'}}}
    return {'expr': {'Literal': {'Value': valor}}}


def _propriedades(objetos, nome):
    """As propriedades gerais (sem seletor) do objeto, criando o que faltar."""
    entradas = objetos.setdefault(nome, [])
    geral = next((e for e in entradas if not e.get('selector')), None)
    if geral is None:
        geral = {'properties': {}}
        entradas.insert(0, geral)
    return geral.setdefault('properties', {})


def _estados(objetos):
    """Seletor de estado no formato que o Desktop reconhece; duas entradas do mesmo estado viram uma."""
    for nome, entradas in objetos.items():
        juntas = []
        for e in entradas:
            e = copy.deepcopy(e)
            sid = (e.get('selector') or {}).get('id')
            if sid in ESTADOS:
                e['selector']['id'] = ESTADOS[sid]
            par = next((x for x in juntas if 'selector' in e and x.get('selector') == e['selector']), None)
            if par:
                par.setdefault('properties', {}).update(e.get('properties', {}))
            else:
                juntas.append(e)
        objetos[nome] = juntas


def aplicar(tipo, vis):
    """Corrige `vis` (o "visual" do visual.json) depois do estilo de origem."""
    objetos = vis.setdefault('objects', {})
    if tipo == 'lineChart':
        eixo = _propriedades(objetos, 'categoryAxis')
        eixo['show'] = _lit(True)
        eixo['fontSize'] = _lit(10)
    elif tipo == 'clusteredBarChart':
        eixo = _propriedades(objetos, 'categoryAxis')
        eixo['show'] = _lit(True)                     # barra sem o nome do item não se lê (tabela-lateral escondia)
        eixo['maxMarginFactor'] = {'expr': {'Literal': {'Value': '45L'}}}
        eixo['fontSize'] = _lit(11)
    elif tipo == 'advancedSlicerVisual':
        _estados(objetos)
        for e in objetos.get('value', []):          # texto do botão sempre visível
            e.get('properties', {}).pop('transparency', None)
    if not objetos:
        vis.pop('objects')
    return vis
