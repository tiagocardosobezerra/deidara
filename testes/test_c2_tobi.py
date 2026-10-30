"""
C2 e Tobi: o esboço escolhe os visuais pela pergunta do painel, e a frase de leitura conta o que o número fez.

    python3 -m unittest discover -s testes
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apoio import *  # noqa: E402,F401,F403


def _esboco(pedido, briefing=None):
    from tecnicas import te_no_kuchi
    argila, notas = te_no_kuchi.esbocar(CATALOGOS, pedido, briefing=briefing)
    argila['fontes'] = {'erp': {'catalogo': 'catalogos/erp.json'}, 'metas': {'catalogo': 'catalogos/metas.json'}}
    for r in argila['relacionamentos']:
        if 'declarada' in r:
            r['declarada']['por'] = 'Time de Indicadores'
    return argila, notas


def _tipos(argila, pagina=0):
    return [v['tipo'] for v in argila['paginas'][pagina]['visuais']]


class TestC2(unittest.TestCase):
    def test_le_a_pergunta(self):
        from tecnicas import c2
        self.assertEqual(c2.intencoes('Por que o turnover subiu?'), {'causa'})
        self.assertEqual(c2.intencoes('quem está pior', 'estamos na meta?'), {'ranking', 'meta'})
        self.assertEqual(c2.intencoes('evolução mês a mês'), {'evolucao'})
        self.assertEqual(c2.intencoes('turnover por cargo'), set())

    def test_por_que_mudou_ganha_a_pagina_da_causa(self):
        from kibaku_nendo.especificacao import distorcoes
        argila, notas = _esboco('por que o turnover subiu, por motivo e cargo')
        causa = next(p for p in argila['paginas'] if p['nome'] == 'Por que mudou')
        tipos = [v['tipo'] for v in causa['visuais']]
        self.assertTrue({'decomposicao', 'barras', 'cartao', 'segmentador'} <= set(tipos), tipos)
        impacto = next(v for v in causa['visuais'] if v['tipo'] == 'barras')['valores'][0]
        self.assertTrue(impacto.startswith('Impacto em'))
        m, p = _resolver(argila)
        self.assertEqual(p.erros, [])
        self.assertEqual(distorcoes(p.avisos), [])
        self.assertTrue(any('C2 escolheu' in n for n in notas), notas)

    def test_meta_e_ranking_viram_tabela(self):
        argila, _ = _esboco('turnover por cargo: quem está pior e se estamos na meta',
                            {'indicadores': [{'nome': 'Turnover', 'definicao': 'x', 'polaridade': 'menor_melhor',
                                              'meta': 0.05}]})
        tabela = next(v for v in argila['paginas'][0]['visuais'] if v['tipo'] == 'tabela')
        tipos = {next((m['tipo'] for m in argila['medidas'] if m['nome'] == c), 'coluna') for c in tabela['campos']}
        self.assertTrue({'svg_posicao', 'svg_barra_meta', 'svg_pilula'} <= tipos, tabela)
        _, p = _resolver(argila)
        self.assertEqual(p.erros, [])

    def test_evolucao_vira_linha_e_sempre_tem_a_frase(self):
        argila, _ = _esboco('evolução do turnover por cargo')
        self.assertIn('linha', _tipos(argila))
        frase = [v for v in argila['paginas'][0]['visuais'] if v['tipo'] == 'cartao'
                 and v['medida'].startswith('Leitura de')]
        self.assertEqual(len(frase), 1)

    def test_projeto_gerado_com_as_escolhas_passa_no_schema(self):
        argila, _ = _esboco('por que o turnover subiu e quem está pior, por cargo')
        argila.update({'descricao': 'x', 'publico': 'y'})
        for md in argila['medidas']:
            if str(md.get('descricao', '')).startswith('A DEFINIR'):
                md['descricao'] = 'x'
        d = tempfile.mkdtemp(prefix='ddc2')
        shutil.copytree(os.path.join(EXEMPLO, 'catalogos'), os.path.join(d, 'catalogos'))
        arq = os.path.join(d, 'argila.json')
        with open(arq, 'w', encoding='utf-8') as f:
            json.dump(argila, f, ensure_ascii=False)
        self.assertEqual(_calado(_aprovar_com_prototipo, ['aprovar', arq, '--por', 'T'])[0], 0)
        saida = os.path.join(d, 'o')
        self.assertEqual(_calado(deidara.main, ['gerar', arq, '-o', saida, '--demo'])[0], 0)
        self.assertEqual(validar_pbip.conferir(saida), [])
        with open(os.path.join(d, 'argila.prototipo.html'), encoding='utf-8') as f:
            html_ = f.read()
        self.assertIn('contra o ano anterior', html_)                     # a frase do Tobi, com números fictícios
        shutil.rmtree(d, ignore_errors=True)


class TestTobi(unittest.TestCase):
    def _fmt(self, v, f):
        return f'{v:.1%}' if f == 'percentual' else f'{v:.0f}'

    def test_medida_aditiva_diz_quanto_cada_um_explica(self):
        from tecnicas import tobi
        texto = tobi.frase('Desligamentos', 768, 730, [('Cargo A', 400, 380), ('Cargo D', 368, 350)], 'inteiro',
                           False, True, self._fmt)
        self.assertTrue(texto.startswith('Desligamentos: subiu 38 contra o ano anterior (730 → 768), piorou'), texto)
        self.assertIn('Cargo A explica 53% da alta', texto)

    def test_taxa_diz_so_onde_variou_mais(self):
        from tecnicas import tobi
        texto = tobi.frase('Turnover', 0.047, 0.051, [('Cargo A', 0.05, 0.05), ('Cargo D', 0.04, 0.06)], 'percentual',
                           False, False, self._fmt)
        self.assertIn('caiu 0,4 p.p.', texto)
        self.assertIn('melhorou', texto)
        self.assertIn('maior variação em Cargo D', texto)

    def test_dax_passa_na_checagem_e_conhece_as_funcoes(self):
        from kibaku_nendo.especificacao import sintaxe_dax
        from tecnicas import sasori, tobi
        dax = tobi.dax('Turnover', '[Turnover]', '[Turnover AA]', 'dCargo[Cargo]', 'percentual', False, False)
        self.assertEqual(sintaxe_dax(dax), [])
        self.assertEqual(sasori.desconhecidas(dax), [])
