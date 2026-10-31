"""
A galeria (terceiros/): o conteúdo aberto da comunidade dentro do Deidara, com licença, e o uso dele no
argila.json (funções DAX do daxlib, modelos Deneb, feriados do Bravo).

    python3 -m unittest discover -s testes
"""

import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apoio import *  # noqa: E402,F401,F403
from tecnicas import galeria  # noqa: E402

TERCEIROS = os.path.join(RAIZ, 'terceiros')


class TestConteudo(unittest.TestCase):
    @unittest.skipIf(os.path.exists(os.path.join(TERCEIROS, 'pacote.json')), 'o pacote instalado leva só parte das fontes')
    def test_toda_fonte_tem_licenca_mit_e_origem(self):
        fontes = [d for d in os.listdir(TERCEIROS) if os.path.isdir(os.path.join(TERCEIROS, d))]
        self.assertGreaterEqual(len(fontes), 8)
        for f in fontes:
            with open(os.path.join(TERCEIROS, f, 'LICENSE'), encoding='utf-8', errors='replace') as arq:
                self.assertIn('MIT License', arq.read(), f)
            self.assertTrue(os.path.exists(os.path.join(TERCEIROS, f, 'ORIGEM.md')), f)

    def test_so_texto_nenhum_binario(self):
        binarios = [x for x in glob.glob(os.path.join(TERCEIROS, '**', '*'), recursive=True)
                    if x.lower().endswith(('.pbix', '.png', '.jpg', '.gif', '.mp4', '.xlsx', '.zip', '.wmv'))]
        self.assertEqual(binarios, [])

    def test_catalogo_cobre_o_que_faltava(self):
        ids = {x['id'] for x in galeria.catalogo()}
        for esperado in ('DaxLib.SVG', 'PowerofBI.IBCS', 'EdwardCharles.WaterfallSVG', 'DataZoe.SVG',
                         'deneb-vega-templates/flow/waterfall', 'deneb-vega-templates/magnitude/bullet-graph',
                         'deneb-vega-templates/ranking/bump', 'deneb-vega-templates/distribution/boxplot',
                         'deneb-vega-templates/part-to-whole/treemap', 'bravo-calendario/HolidaysDefinition'):
            self.assertIn(esperado, ids)
        self.assertGreaterEqual(sum(len(x.get('funcoes', [])) for x in galeria.catalogo()), 500)

    def test_busca_em_portugues(self):
        for termo, esperado in (('cascata', 'EdwardCharles.WaterfallSVG'), ('minigráfico', 'DaxLib.SVG'),
                                ('ibcs', 'PowerofBI.IBCS'), ('ranking no tempo', 'deneb-vega-templates/ranking/bump'),
                                ('feriado', 'bravo-calendario/HolidaysDefinition')):
            self.assertIn(esperado, [x['id'] for x in galeria.buscar(termo)][:8], termo)


class TestFuncoesDax(unittest.TestCase):
    def _argila(self):
        a = _base()
        a['funcoes_dax'] = ['DaxLib.SVG']
        a['medidas'].append({'nome': 'Tendência do Turnover', 'dax': 'DaxLib.SVG.Viz.Line(dCalendario[Ano-Mês], [Turnover])',
                             'tabela': 'fDesligamento', 'descricao': 'Minigráfico do turnover.'})
        return a

    def test_funcao_do_pacote_vale_e_medida_vira_imagem(self):
        m, p = _resolver(self._argila())
        self.assertEqual(p.erros, [])
        md = next(x for x in m['medidas'] if x['nome'] == 'Tendência do Turnover')
        self.assertTrue(md.get('imagem'))
        self.assertTrue(any('nível de compatibilidade 1702' in x for x in p.avisos))

    def test_sem_o_pacote_a_funcao_e_desconhecida(self):
        a = self._argila()
        a.pop('funcoes_dax')
        self.assertTrue(any('DaxLib.SVG.Viz.Line' in e for e in _resolver(a)[1].erros))

    def test_pacote_inexistente(self):
        a = self._argila()
        a['funcoes_dax'] = ['DaxLib.SVGX']
        self.assertTrue(any('parecidos: DaxLib.SVG' in e for e in _resolver(a)[1].erros))

    def test_tmdl_das_funcoes(self):
        from tecnicas.c3 import tmdl
        m, _ = _resolver(self._argila())
        texto = tmdl.funcoes(m)
        self.assertIn("function 'DaxLib.SVG.Viz.Line' =", texto)
        self.assertIn('licença MIT', texto)
        self.assertFalse(any(l.startswith(' ') for l in texto.split('\n')), 'recuo com espaço')


class TestDeneb(unittest.TestCase):
    def _argila(self, campos=None):
        a = _base()
        a['medidas'].append({'nome': 'Desligamentos Ano Anterior', 'tipo': 'ano_anterior', 'base': 'Desligamentos',
                             'descricao': 'x'})
        a['paginas'][1]['visuais'].append({'tipo': 'vegalite', 'modelo': 'deneb-vega-templates/ranking/slope',
                                           'campos': campos if campos is not None else {
                                               'Category': 'dMotivo[Motivo]', 'Value 1': 'Desligamentos Ano Anterior',
                                               'Value 2': 'Desligamentos'}})
        return a

    def test_modelo_com_os_campos_do_painel(self):
        import json
        m, p = _resolver(self._argila())
        self.assertEqual(p.erros, [])
        v = next(x for x in m['paginas'][1]['visuais'] if x.get('modelo'))
        self.assertEqual(v['provider'], 'vega')
        self.assertEqual([c['nome'] for c in v['campos_deneb']], ['Motivo', 'Desligamentos Ano Anterior', 'Desligamentos'])
        self.assertNotIn('__0__', v['spec'])
        self.assertIn('Desligamentos Ano Anterior', v['spec'])
        self.assertNotIn('previewImageBase64PNG', v['spec'])
        from tecnicas.c3 import pbir
        from tecnicas.arte.layout import posicionar
        pos = dict((id(x), y) for x, y in posicionar(m['paginas'][1]['visuais']))
        vis = json.dumps(pbir.visual(m, v, pos[id(v)], 'x', 0), ensure_ascii=False)
        self.assertIn('"dataset"', vis)
        self.assertIn("'vega'", vis)

    def test_falta_campo(self):
        _, p = _resolver(self._argila({'Category': 'dMotivo[Motivo]'}))
        self.assertTrue(any('pede os campos Value 1, Value 2' in e for e in p.erros))

    def test_modelo_inexistente(self):
        a = self._argila()
        a['paginas'][1]['visuais'][-1]['modelo'] = 'deneb-vega-templates/ranking/slopee'
        self.assertTrue(any('não está na galeria' in e for e in _resolver(a)[1].erros))

    def test_prototipo_mostra_a_previa_do_autor(self):
        from tecnicas.c1 import prototipo
        m, p = _resolver(self._argila())
        html = prototipo.gerar_html(m, p, '0')
        self.assertIn('data:image/png;base64', html)
        self.assertIn('Andrzej Leszkiewicz', html)


class TestFeriados(unittest.TestCase):
    def test_feriados_do_brasil_e_dia_util(self):
        from tecnicas.c3 import tmdl
        a = _base()
        a['calendario']['feriados'] = 'BR'
        a['calendario']['feriados_extras'] = [{'mes': 1, 'dia': 25, 'nome': 'Aniversário da cidade'}]
        m, p = _resolver(a)
        self.assertEqual(p.erros, [])
        cal = next(t for t in m['tabelas'] if t['nome'] == 'dCalendario')
        self.assertEqual([c['nome'] for c in cal['colunas']][-2:], ['Feriado', 'Dia Útil'])
        texto = tmdl.tabela(m, cal)
        for x in ('N = "Tiradentes"', 'N = "Consciência Negra (Lei 14.759/2023)"', 'N = "Aniversário da cidade"',
                  '[M = 99, D = -2', 'Pascoa = (a as number) as date =>', '"Dia Útil"'):
            self.assertIn(x, texto)
        self.assertTrue(any('estaduais, municipais e pontos facultativos' in x for x in p.avisos))

    def test_pais_sem_regra(self):
        a = _base()
        a['calendario']['feriados'] = 'XX'
        self.assertTrue(any('sem feriados para "XX"' in e for e in _resolver(a)[1].erros))


if __name__ == '__main__':
    unittest.main()
