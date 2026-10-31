"""
Fora de RH: um ERP de varejo do catálogo ao esboço (revisão D1). Duas cadeias de padrão sobre a mesma coluna
(ticket médio e margem), meta mensal de valor na planilha e nomes de coluna colados (VALORLIQUIDO).

    python3 -m unittest discover -s testes
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apoio import *  # noqa: E402,F401,F403
from apoio import _linha as L  # noqa: E402


def _catalogo():
    linhas = [
        L('coluna', 'VENDAS', 'NUMPEDIDO', 'int', 4, 10, 0, 0, 1), L('coluna', 'VENDAS', 'ITEM', 'int', 4, 10, 0, 0, 2),
        L('coluna', 'VENDAS', 'DATAVENDA', 'date', 3, 10, 0, 0), L('coluna', 'VENDAS', 'CODPRODUTO', 'int', 4, 10, 0, 0),
        L('coluna', 'VENDAS', 'CODLOJA', 'int', 4, 10, 0, 0), L('coluna', 'VENDAS', 'VALORLIQUIDO', 'decimal', 9, 18, 2, 0),
        L('coluna', 'VENDAS', 'CUSTO', 'decimal', 9, 18, 2, 0),
        L('coluna', 'PRODUTOS', 'CODPRODUTO', 'int', 4, 10, 0, 0, 1), L('coluna', 'PRODUTOS', 'CATEGORIA', 'varchar', 40, 0, 0, 1),
        L('coluna', 'LOJAS', 'CODLOJA', 'int', 4, 10, 0, 0, 1), L('coluna', 'LOJAS', 'NOMELOJA', 'varchar', 60, 0, 0, 1),
        L('coluna', 'METAS_LOJA', 'CODLOJA', 'int', 4, 10, 0, 0, 1), L('coluna', 'METAS_LOJA', 'MES', 'date', 3, 10, 0, 0, 2),
        L('coluna', 'METAS_LOJA', 'META_VALOR', 'decimal', 9, 18, 2, 0),
        L('fk', 'VENDAS', 'CODPRODUTO', mae='PRODUTOS', cmae='CODPRODUTO', fk='FK_V_P', ordem=1),
        L('fk', 'VENDAS', 'CODLOJA', mae='LOJAS', cmae='CODLOJA', fk='FK_V_L', ordem=1),
        L('fk', 'METAS_LOJA', 'CODLOJA', mae='LOJAS', cmae='CODLOJA', fk='FK_M_L', ordem=1)]
    cat, _ = receitas.catalogo_de_sql(linhas, 'erp')
    return {'erp': catalogo.Fonte('erp', cat, '')}


class TestVarejo(unittest.TestCase):
    def test_esboco_de_varejo_sem_erro(self):
        from tecnicas import te_no_kuchi
        cats = _catalogo()
        briefing = {'decisao': 'onde a margem caiu e quais lojas estão abaixo da meta', 'publico': 'Diretoria',
                    'indicadores': [{'nome': 'Receita', 'definicao': 'Valor líquido vendido.', 'polaridade': 'maior_melhor',
                                     'meta': 'a da planilha'}]}
        a, notas = te_no_kuchi.esbocar(cats, 'receita, margem e ticket médio por loja e categoria contra a meta mensal',
                                       briefing=briefing)
        nomes = [m['nome'] for m in a['medidas']]
        for x in ('Receita', 'Pedidos', 'Ticket Médio', 'Custo', 'Margem %', 'Meta de Receita'):
            self.assertIn(x, nomes)
        self.assertNotIn('Receita Líquida', nomes)                     # a mesma soma da mesma coluna, uma vez só
        self.assertNotIn('Qtd MetasLoja', nomes)                       # tabela de metas não ganha contagem de linhas
        margem = next(m for m in a['medidas'] if m['nome'] == 'Margem %')
        self.assertEqual(margem['dax'], 'DIVIDE([Receita] - [Custo], [Receita])')
        meta = next(m for m in a['medidas'] if m['nome'] == 'Meta de Receita')
        self.assertEqual((meta['agregacao'], meta['formato']), ('soma', 'moeda'))   # meta de valor soma os meses
        self.assertEqual(next(m for m in a['medidas'] if m['nome'] == 'Receita')['meta'], 'Meta de Receita')
        a['fontes'] = {'erp': {'catalogo': 'x'}}
        _, p = resolver(a, cats)
        self.assertEqual(p.erros, [])

    def test_meta_ficticia_anda_junto_do_realizado(self):
        # revisão D3 (diretor): com meta e realizado sorteados à parte, toda loja aparecia fora da meta
        from tecnicas import te_no_kuchi
        from tecnicas.bunshin.simulacao import Simulador, categorias
        cats = _catalogo()
        briefing = {'indicadores': [{'nome': 'Receita', 'definicao': 'x', 'polaridade': 'maior_melhor', 'meta': 'a da planilha'}]}
        a, _ = te_no_kuchi.esbocar(cats, 'receita por loja contra a meta mensal', briefing=briefing)
        a['fontes'] = {'erp': {'catalogo': 'x'}}
        m, _ = resolver(a, cats)
        s = Simulador(m)
        self.assertLess(abs(s.valor('Meta de Receita') / s.valor('Receita') - 1), 0.12)
        loja = {'tabela': 'dLojas', 'nome': 'Loja', 'tipo': 'coluna'}
        if any(t['nome'] == 'dLojas' for t in m['tabelas']):
            status = [s.status('Receita', [(loja, r)]) for r in categorias(m, loja)]
            self.assertTrue(any(status) and not all(status), status)   # umas dentro, outras fora

    def test_coluna_colada_casa_com_o_papel(self):
        from tecnicas.te_no_kuchi import _coluna_do_papel
        t = _catalogo()['erp'].tabela('VENDAS')
        self.assertEqual(_coluna_do_papel(t, 'Receita Líquida')['coluna'], 'VALORLIQUIDO')
        self.assertEqual(_coluna_do_papel(t, 'Nº Pedido')['coluna'], 'NUMPEDIDO')


if __name__ == '__main__':
    unittest.main()
