"""
Testes do caminho do briefing ao protótipo: esboço guiado pelos padrões, briefing do gestor, origem da receita SQL
e protótipo com ligação a confirmar.

    python3 -m unittest discover -s testes
"""

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ['DEIDARA_MEMORY_CARD_DIR'] = '-'

import deidara  # noqa: E402
from tecnicas.luneta import catalogo  # noqa: E402
from tecnicas import te_no_kuchi as esboco  # noqa: E402
from tecnicas.luneta import receitas  # noqa: E402
from kibaku_nendo.especificacao import resolver  # noqa: E402

EXEMPLO = os.path.join(RAIZ, 'exemplos', 'aurora')
CATALOGOS = {n: catalogo.carregar(os.path.join(EXEMPLO, 'catalogos', f'{n}.json'), n) for n in ('erp', 'metas')}
PEDIDO = 'turnover por cargo e empresa contra a meta'
BRIEFING = {'decisao': 'Onde agir para reduzir o turnover.', 'publico': 'Gestores de RH', 'cortes': ['cargo', 'empresa'],
            'indicadores': [{'nome': 'Turnover', 'definicao': 'Desligamentos do mês sobre o headcount médio do mês.',
                             'polaridade': 'menor_melhor', 'meta': 'planilha de metas'}]}


def _calado(fn, *args):
    with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()):
        codigo = fn(*args)
    return codigo, out.getvalue()


def _md(argila, nome):
    return next(x for x in argila['medidas'] if x['nome'] == nome)


class TestEsbocoComPadrao(unittest.TestCase):
    def test_turnover_traz_a_cadeia_e_o_fato_de_evento(self):
        argila, notas = esboco.esbocar(CATALOGOS, PEDIDO, 'T')
        tabelas = {t['nome']: t for t in argila['tabelas']}
        self.assertEqual(tabelas['fDesligamento']['origem'], 'F_DESLIGAMENTO')       # o fato que a busca deixava de fora
        self.assertEqual(tabelas['dColaborador']['tipo'], 'dimensao')                 # cadastro de pessoas não é fato
        self.assertIn('Data de Admissão', [c['nome'] for c in tabelas['dColaborador']['colunas']])
        self.assertEqual(_md(argila, 'Headcount')['tipo'], 'estoque_na_data')         # estoque, não contagem
        self.assertEqual(_md(argila, 'Turnover')['meta'], 'Meta de turnover')
        self.assertFalse(_md(argila, 'Meta de turnover')['descricao'].startswith('A DEFINIR'))
        self.assertFalse([m for m in argila['medidas'] if m['nome'].startswith('Qtd ')])
        cartoes = [v['medida'] for v in argila['paginas'][0]['visuais'] if v['tipo'] == 'cartao']
        self.assertEqual(cartoes[0], 'Turnover')
        barras = [v['categoria'] for v in argila['paginas'][0]['visuais'] if v['tipo'] == 'barras']
        self.assertEqual(barras, ['dCargo[Cargo]', 'dEmpresa[Razão social]'])
        self.assertTrue(any('padrão "turnover"' in n for n in notas), notas)
        _, p = resolver(argila, CATALOGOS)
        self.assertEqual(len(p.erros), 1, p.erros)                                     # só a ligação a confirmar
        self.assertIn('ainda não confirmada', p.erros[0])

    def test_sem_padrao_continua_como_antes(self):
        argila, notas = esboco.esbocar(CATALOGOS, 'remuneração por cargo', 'R')
        self.assertFalse(any('padrão' in n for n in notas))
        self.assertTrue(argila['medidas'])

    def test_escolha_a_mao_restringe_o_padrao(self):
        argila, notas = esboco.esbocar(CATALOGOS, 'turnover', 'T', tabelas=[('erp', 'F_CARGO'), ('erp', 'N_EMPRESA')])
        self.assertTrue(any('não achei' in n for n in notas), notas)
        self.assertNotIn('fDesligamento', {t['nome'] for t in argila['tabelas']})


class TestBriefing(unittest.TestCase):
    def test_briefing_preenche_definicao_publico_e_pedido(self):
        argila, notas = esboco.esbocar(CATALOGOS, None, 'T', briefing=BRIEFING)
        self.assertEqual(argila['publico'], 'Gestores de RH')
        self.assertEqual(argila['descricao'], 'Onde agir para reduzir o turnover.')
        self.assertEqual(_md(argila, 'Turnover')['descricao'], BRIEFING['indicadores'][0]['definicao'])
        self.assertEqual(_md(argila, 'Turnover')['meta'], 'Meta de turnover')
        m, p = resolver(argila, CATALOGOS)
        self.assertFalse([x for x in p.avisos if 'definição pendente' in x], p.avisos)

    def test_indicador_sem_medida_vira_nota_e_meta_numerica_entra(self):
        b = {'indicadores': [{'nome': 'Turnover', 'meta': 0.03}, {'nome': 'Absenteísmo'}]}
        argila, notas = esboco.esbocar(CATALOGOS, 'turnover', 'T', briefing=b)
        self.assertEqual(_md(argila, 'Turnover')['meta'], 0.03)                       # a palavra do gestor manda
        self.assertTrue(any('ficou de lado' in n for n in notas), notas)
        self.assertTrue(any('Absenteísmo' in n for n in notas), notas)

    def test_sem_pedido_nem_briefing_explica(self):
        with self.assertRaises(ValueError):
            esboco.esbocar(CATALOGOS, None, 'T', briefing={})


class TestReceitaComOrigem(unittest.TestCase):
    def test_receita_sql_devolve_servidor_e_banco(self):
        texto = receitas.receita_sql('dbo', [])
        self.assertIn('@@SERVERNAME', texto)
        self.assertIn('DB_NAME()', texto)
        cab = ['secao', 'tabela', 'coluna', 'tipo', 'descricao']
        linhas = [dict(zip(cab, x)) for x in (('origem', '(banco)', 'SRV01', 'AURORA', 'rh'),
                                              ('tabela', 'T1', '', '', ''),
                                              ('coluna', 'T1', 'C1', 'int', ''))]
        cat, _ = receitas.catalogo_de_sql(linhas, 'erp')
        self.assertEqual(cat['origem'], {'servidor': 'SRV01', 'banco': 'AURORA', 'esquema': 'rh'})
        self.assertEqual(list(cat['tabelas']), ['T1'])
        d = tempfile.mkdtemp(prefix='ddo')
        arq = os.path.join(d, 'erp.json')
        with open(arq, 'w', encoding='utf-8') as f:
            json.dump(cat, f)
        self.assertEqual(catalogo.carregar(arq).origem['banco'], 'AURORA')
        shutil.rmtree(d, ignore_errors=True)


class TestFluxoNaPasta(unittest.TestCase):
    def _pasta(self):
        d = tempfile.mkdtemp(prefix='ddf')
        pasta = os.path.join(d, 'painel')
        self.assertEqual(_calado(deidara.main, ['novo', pasta, '--projeto', 'Turnover RH'])[0], 0)
        with open(os.path.join(pasta, 'painel.json'), encoding='utf-8') as f:
            painel = json.load(f)
        self.assertIn('indicadores', painel['briefing'])                               # o esqueleto do briefing
        painel['briefing'] = BRIEFING
        with open(os.path.join(pasta, 'painel.json'), 'w', encoding='utf-8') as f:
            json.dump(painel, f, ensure_ascii=False)
        for n in ('erp', 'metas'):
            shutil.copy(os.path.join(EXEMPLO, 'catalogos', f'{n}.json'), os.path.join(pasta, 'catalogos', f'{n}.json'))
        return d, pasta

    def test_prototipo_sai_com_ligacao_pendente_e_aceite_espera(self):
        d, pasta = self._pasta()
        argila = os.path.join(pasta, 'argila.json')
        codigo, saida = _calado(deidara.main, ['esbocar', pasta])                     # sem --pedido: vem do briefing
        self.assertEqual(codigo, 0, saida)
        self.assertNotIn('sem briefing', saida)
        codigo, saida = _calado(deidara.main, ['prototipar', argila])
        self.assertEqual(codigo, 0, saida)
        self.assertIn('A CONFIRMAR', saida)
        with open(os.path.join(pasta, 'argila.prototipo.html'), encoding='utf-8') as f:
            self.assertIn('ligação A CONFIRMAR', f.read())
        self.assertEqual(_calado(deidara.main, ['aprovar', argila, '--por', 'G'])[0], 1)
        _, saida = _calado(deidara.main, ['situacao', argila])
        self.assertIn('fMetas->dEmpresa', saida)
        self.assertIn('confirmar', saida.split('Próximo passo:')[1])
        _calado(deidara.main, ['confirmar', argila, '--ligacao', 'fMetas->dEmpresa', '--por', 'Ana'])
        self.assertEqual(_calado(deidara.main, ['prototipar', argila])[0], 0)
        self.assertEqual(_calado(deidara.main, ['aprovar', argila, '--por', 'G'])[0], 0)
        shutil.rmtree(d, ignore_errors=True)

    def test_roteiro_e_guia_falam_a_mesma_lingua(self):
        d, pasta = self._pasta()
        with open(os.path.join(pasta, 'ROTEIRO.md'), encoding='utf-8') as f:
            roteiro = f.read()
        self.assertIn('## 1. Briefing', roteiro)
        self.assertIn('onze modelos', deidara.GUIA)
        self.assertIn('1. briefing', deidara.GUIA)
        shutil.rmtree(d, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
