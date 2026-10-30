"""
Sasori: o dicionário de funções.

    python3 -m unittest discover -s testes
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apoio import *  # noqa: E402,F401,F403


class TestDicionario(unittest.TestCase):
    def test_funcao_inventada_e_erro_com_sugestao(self):
        a = _base()
        a['medidas'].append({'nome': 'X', 'dax': 'CALCULATE([Desligamentos], SAMEPERIODLASTYAER(dCalendario[Data]))'})
        _, p = _resolver(a)
        self.assertTrue(any('SAMEPERIODLASTYAER' in e and 'SAMEPERIODLASTYEAR' in e for e in p.erros), p.erros)

    def test_dax_gerado_e_padroes_so_usam_funcoes_do_dicionario(self):
        from tecnicas import sasori as dicionario
        m, _ = _resolver(_base())
        for md in m['medidas']:
            self.assertEqual(dicionario.desconhecidas(md['dax']), [], md['nome'])
        for pd in dicionario.padroes()['padroes']:
            for dax in (pd.get('dax'), (pd.get('argila') or {}).get('dax')):
                if dax:
                    self.assertEqual(dicionario.desconhecidas(dax), [], pd['id'])

    def test_nomes_de_coluna_e_texto_nao_viram_funcao(self):
        from tecnicas import sasori as dicionario
        self.assertEqual(dicionario.funcoes_usadas("SUM('T x'[A(b)]) + LEN(\"ABC(\") // FOO(1)"), ['SUM', 'LEN'])

    def test_toda_funcao_tem_link_oficial_e_as_principais_tem_descricao(self):
        from tecnicas import sasori as dicionario
        dax = dicionario.funcoes('dax')
        for n in ('CALCULATE', 'DIVIDE', 'TOTALYTD', 'DATESINPERIOD', 'USERELATIONSHIP'):
            self.assertTrue(dax[n]['url'].startswith('https://learn.microsoft.com/pt-br/dax/'), n)
            self.assertTrue(dax[n].get('descricao'), n)
        self.assertIn('Excel.Workbook', dicionario.funcoes('m'))

    def test_dicionario_local_da_receita(self):
        d = tempfile.mkdtemp(prefix='ddf')
        arq = os.path.join(d, 'f.txt')
        with open(arq, 'w', encoding='utf-8') as f:
            f.write('FUNCTION_NAME\tDESCRIPTION\nSUM\tx\nNOVAFUNCAO\ty\n')
        loc = receitas.dicionario_local(arq, 'dax')
        self.assertEqual(sorted(loc['funcoes']), ['NOVAFUNCAO', 'SUM'])
