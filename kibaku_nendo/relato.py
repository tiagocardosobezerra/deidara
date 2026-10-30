"""
Como o Deidara fala com quem usa: o relatório da validação e a situação do
projeto. Sempre na mesma ordem: um resumo de uma linha, o que corrigir (a
causa primeiro, com as consequências agrupadas embaixo dela), o que decidir
(avisos agrupados por tema) e o próximo passo.
"""

import textwrap

LARGURA = 108

TEMAS = (
    ('Definições', ('definição pendente',)),
    ('Memory Card', ('OFICIAL', 'Memory Card')),
    ('Ligações', ('ligação', 'DECLARADA', 'tipos diferentes nas pontas', 'FK ', 'chave da mãe', 'receita de prova',
                  'prova ')),
    ('Filtros e cortes', ('segmentador', 'não filtra', 'filtra só parte', 'soma todos os anos')),
    ('Privacidade', ('[Privacidade]',)),
    ('Fontes', ('servidor/banco', 'SEU_SERVIDOR')),
    ('Design', ('[Design]', '[SVG]')),
    ('Modelagem', ('valor ATUAL', 'estoque', 'sem tipo', 'calendário')),
)


def _quebrar(texto, recuo):
    return textwrap.fill(texto, LARGURA, initial_indent='', subsequent_indent=' ' * recuo)


def tema_do_aviso(aviso):
    for tema, chaves in TEMAS:
        if any(c in aviso for c in chaves):
            return tema
    return 'Outros'


def _amigavel(tabela):
    import re as _re
    nome = _re.sub(r'^[df](?=[A-Z])', '', tabela)
    return _re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', nome)


def para_gestor(aviso):
    """O aviso em linguagem de negócio, para o gestor; None = assunto só do analista."""
    import re as _re
    r = _re.search(r'o segmentador (\w+)\[(.+?)\] não filtra (a medida inteira|parte da medida.*?) de "(.+?)"', aviso)
    if r:
        if r.group(3) == 'a medida inteira':
            return f'Ao filtrar por {r.group(2)}, "{r.group(4)}" não muda (é o mesmo valor para qualquer escolha). Está certo?'
        return (f'Ao filtrar por {r.group(2)}, só parte da conta de "{r.group(4)}" muda: o número pode ficar distorcido. '
                'Está certo?')
    r = _re.search(r'(\w+)\[(.+?)\] não filtra a medida "(.+?)"', aviso)
    if r:
        return f'Num visual por {r.group(2)}, "{r.group(3)}" repete o mesmo valor em toda linha.'
    r = _re.search(r'(\w+)\[(.+?)\] filtra só parte de "(.+?)"', aviso)
    if r:
        return f'Num visual por {r.group(2)}, só parte da conta de "{r.group(3)}" muda por linha.'
    r = _re.search(r'(\w+) chega em (.+?) através de (\w+)', aviso)
    if r:
        return (f'O corte por {_amigavel(r.group(1))} mostra o cadastro de hoje, não o da data do evento '
                f'(o {_amigavel(r.group(1))} atual da pessoa, não o que ela tinha na época). Serve assim?')
    r = _re.search(r'(\w+) -> (\w+): ligação DECLARADA por (.+?), sem prova', aviso)
    if r:
        return (f'{_amigavel(r.group(1))} e {_amigavel(r.group(2))} vêm de fontes diferentes; a ligação foi confirmada '
                f'por {r.group(3)} e será conferida na primeira atualização.')
    r = _re.search(r'medida (.+?): difere do indicador OFICIAL', aviso)
    if r:
        return f'"{r.group(1)}" usa uma fórmula diferente da oficial do time.'
    r = _re.search(r'medida (.+?): definição pendente', aviso)
    if r:
        return f'"{r.group(1)}" ainda não tem definição escrita.'
    return None


def resumo(modelo):
    n = [(len(modelo['tabelas']), 'tabela', 'tabelas'), (len(modelo['relacionamentos']), 'relação', 'relações'),
         (len([x for x in modelo['medidas'] if x.get('tipo') not in ('cor', 'meta')]), 'medida', 'medidas'),
         (len(modelo['paginas']), 'página', 'páginas'),
         (sum(len(p['visuais']) for p in modelo['paginas']), 'visual', 'visuais')]
    return f'{modelo["projeto"] or "(sem nome)"} · ' + ' · '.join(f'{v} {um if v == 1 else muitos}' for v, um, muitos in n)


def validacao(modelo, problemas, caminho):
    linhas = [resumo(modelo), '']
    if problemas.erros:
        linhas.append(f'✗ {len(problemas.erros)} erro(s) para corrigir (a causa primeiro):')
        for i, e in enumerate(problemas.erros, 1):
            linhas.append('  ' + _quebrar(f'{i}. {e}', 5))
            consequencias = problemas.consequencias.get(e, [])
            if consequencias:
                linhas.append('     ' + _quebrar(f'↳ mais {len(consequencias)} ponto(s) dependem disto e voltam sozinhos '
                                                 'quando for corrigido', 7))
        linhas.append('')
    if problemas.avisos:
        linhas.append(f'! {len(problemas.avisos)} aviso(s) para decidir com o usuário:')
        grupos = {}
        for a in problemas.avisos:
            grupos.setdefault(tema_do_aviso(a), []).append(a)
        for tema, _ in TEMAS + (('Outros', ()),):
            for a in grupos.get(tema, []):
                linhas.append('  ' + _quebrar(f'[{tema}] ' + a.replace(f': [{tema}] ', ': '), 4))
        linhas.append('')
    if problemas.erros:
        linhas.append(f'Próximo passo: corrija os erros e rode de novo `deidara.py validar {caminho}`.')
    elif problemas.avisos:
        linhas.append(f'Próximo passo: leve os avisos ao usuário e gere o protótipo: `deidara.py prototipar {caminho}`.')
    else:
        linhas.append(f'✓ Tudo certo. Próximo passo: `deidara.py prototipar {caminho}`.')
    return '\n'.join(linhas)

def nota_de_ajuda(m, v):
    """O que a nota da ajuda diz sobre o visual: o título e o que cada medida significa."""
    from kibaku_nendo.especificacao import medida, medidas_do_visual as _medidas_do_visual
    linhas = [v.get('titulo') or (v['categoria']['nome'] if v.get('categoria') else v['tipo'])]
    if v.get('categoria') and v['tipo'] in ('segmentador', 'botoes', 'abas', 'alternar'):
        linhas.append(f'Escolha aqui para filtrar a página por {v["categoria"]["nome"]}.' if v['tipo'] in
                      ('segmentador', 'botoes') else 'Troque o indicador que os visuais mostram.')
    for x in _medidas_do_visual(v)[:2]:
        d = (medida(m, x['nome']) or {}).get('descricao')
        if d:
            linhas.append(f'{x["nome"]}: {d}')
    return linhas
