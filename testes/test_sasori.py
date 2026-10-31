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


class TestBoasPraticas(unittest.TestCase):
    def test_regras_do_bpa_no_dax_escrito_a_mao(self):
        from kibaku_nendo.modelo import boas_praticas_dax as bp
        self.assertEqual([r for r, _ in bp('[A] / [B]')], ['divisão com "/"'])
        self.assertEqual(bp('DIVIDE([A], [B])'), [])
        self.assertEqual(bp('"a/b" & fVenda[Data/Hora]'), [])                 # barra em texto e em nome não conta
        self.assertIn('IFERROR/ISERROR', [r for r, _ in bp('IFERROR([A], 0)')])
        self.assertIn('EARLIER', [r for r, _ in bp('EARLIER(f[x])')])
        self.assertIn('FILTER na tabela inteira dentro do CALCULATE',
                      [r for r, _ in bp('CALCULATE([V], FILTER(fVenda, fVenda[X] > 1))')])
        self.assertEqual(bp('CALCULATE([V], fVenda[X] > 1)'), [])
        self.assertIn('COUNTROWS(DISTINCT())', [r for r, _ in bp('COUNTROWS(DISTINCT(f[C]))')])

    def test_vira_aviso_no_validar(self):
        a = _base()
        a['medidas'].append({'nome': 'Razão', 'dax': '[Desligamentos] / [Headcount]', 'descricao': 'x'})
        _, p = _resolver(a)
        self.assertTrue(any('boa prática (divisão com "/")' in x for x in p.avisos))


class TestSchemaMaisRecente(unittest.TestCase):
    def test_troca_a_versao_pela_maior_publicada(self):
        import hashlib
        caminho = 'fabric/item/report/definition/visualContainer'
        os.makedirs(validar_pbip.CACHE, exist_ok=True)
        arq = os.path.join(validar_pbip.CACHE, 'versoes-' + hashlib.sha1(caminho.encode()).hexdigest() + '.json')
        guardado = None
        if os.path.exists(arq):
            with open(arq, encoding='utf-8') as f:
                guardado = f.read()
        try:
            with open(arq, 'w', encoding='utf-8') as f:
                json.dump(['1.0.0', '2.0.0', '2.10.0', '2.9.0'], f)
            url = validar_pbip.PREFIXO + caminho + '/2.0.0/schema.json'
            self.assertEqual(validar_pbip.mais_recente(url), validar_pbip.PREFIXO + caminho + '/2.10.0/schema.json')
            self.assertEqual(validar_pbip.mais_recente('https://outro/schema.json'), 'https://outro/schema.json')
        finally:
            if guardado is None:
                os.remove(arq)
            else:
                with open(arq, 'w', encoding='utf-8') as f:
                    f.write(guardado)


class TestPadroes(unittest.TestCase):
    def test_todo_padrao_tem_dax_valido_e_funcoes_do_dicionario(self):
        from kibaku_nendo.modelo import boas_praticas_dax, sintaxe_dax
        from tecnicas import sasori as dicionario
        dax_dic = dicionario.funcoes('dax')
        pads = dicionario.padroes()['padroes']
        self.assertGreaterEqual(len(pads), 29)
        for pd in pads:
            textos = [pd.get('dax'), (pd.get('argila') or {}).get('dax')] + [x.get('dax') for x in pd.get('cadeia') or []]
            for dax in filter(None, textos):
                self.assertEqual(sintaxe_dax(dax), [], (pd['id'], dax))
                self.assertEqual(dicionario.desconhecidas(dax), [], pd['id'])
                self.assertEqual(boas_praticas_dax(dax), [], (pd['id'], dax))
            for f in pd.get('funcoes') or []:
                self.assertIn(f, dax_dic, (pd['id'], f))
            self.assertTrue(pd.get('armadilhas'), pd['id'])

    def test_padroes_fora_do_rh(self):
        from tecnicas import sasori as dicionario
        for termo, esperado in (('otif', 'otif'), ('nps', 'nps'), ('churn', 'churn'), ('orçado', 'orcado_realizado'),
                                ('absenteísmo', 'absenteismo'), ('sla', 'sla'), ('margem', 'margem'),
                                ('ticket médio', 'ticket_medio'), ('tempo de casa', 'tempo_de_casa')):
            self.assertIn(esperado, [p['id'] for p in dicionario.padroes_para(termo)], termo)
