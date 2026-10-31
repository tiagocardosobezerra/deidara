"""
C0: a engenharia reversa. Lê o que existe (DAX colado, .pbip, receita), desmonta, avalia com nota, propõe a
versão Deidara e refaz o painel. O exemplo legado tem os erros clássicos; o projeto que o próprio Deidara gera
é o controle (precisa tirar nota máxima).

    python3 -m unittest discover -s testes
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apoio import *  # noqa: E402,F401,F403
from tecnicas.c0 import exame, leitura, proposta  # noqa: E402

LEGADO = os.path.join(RAIZ, 'exemplos', 'legado')


def _codigos(estudo, nome):
    return {a['codigo'] for a in estudo['medidas'][nome]['achados']}


class TestLeitura(unittest.TestCase):
    def test_pbip_inteiro(self):
        leg = leitura.ler(LEGADO)
        self.assertEqual(set(leg['tabelas']), {'Funcionarios', 'Desligamentos', 'Empresas', 'Metas', 'Calendario'})
        self.assertTrue(leg['data_automatica'])
        self.assertEqual(len(leg['medidas']), 13)
        self.assertIn('FILTER(', leg['medidas']['Desligamentos Mês Atual']['dax'])          # várias linhas
        self.assertEqual(leg['medidas']['Turnover %']['formato'], '0.0%')
        self.assertEqual(leg['tabelas']['Funcionarios']['colunas']['Desligamentos do Funcionario']['calculada'],
                         'CALCULATE(COUNTROWS(Desligamentos))')
        self.assertTrue(any(r['cruzado'] == 'bothDirections' for r in leg['relacoes']))
        self.assertEqual([v['tipo'] for v in leg['paginas'][0]['visuais']],
                         ['segmentador', 'cartao', 'cartao', 'barras', 'linha', 'tabela'])

    def test_dax_colado_em_varios_formatos(self):
        d = leitura.de_dax('Turnover = DIVIDE([A], [B])\n\n[Taxa %] =\n[A] / [B]')
        self.assertEqual({k: v['dax'] for k, v in d['medidas'].items()}, {'Turnover': 'DIVIDE([A], [B])', 'Taxa %': '[A] / [B]'})
        d = leitura.de_dax("DEFINE\n    MEASURE 'f'[X] = SUM(f[v])\n    MEASURE f[Y] = [X] * 2\nEVALUATE ROW(\"a\", [Y])")
        self.assertEqual({k: (v['tabela'], v['dax']) for k, v in d['medidas'].items()},
                         {'X': ('f', 'SUM(f[v])'), 'Y': ('f', '[X] * 2')})
        self.assertEqual(list(leitura.de_dax('CALCULATE([V], f[a] = 1)')['medidas']), ['Medida'])
        d = leitura.de_dax('Resultado =\nVAR _x = [A]\nRETURN\n    _x')
        self.assertEqual(list(d['medidas']), ['Resultado'])

    def test_receita_traz_medidas(self):
        from tecnicas.luneta import receitas
        texto = receitas.receita_dax()
        self.assertIn('INFO.VIEW.MEASURES()', texto)
        leg = leitura.de_receita([
            {'secao': 'tabela', 'tabela': 'f'}, {'secao': 'coluna', 'tabela': 'f', 'coluna': 'v', 'tipo': 'Int64'},
            {'secao': 'medida', 'tabela': 'f', 'coluna': 'Total', 'expressao': 'SUM(f[v])', 'extra': '#,0|Vendas',
             'descricao': 'Total vendido.'}])
        self.assertEqual(leg['medidas']['Total']['dax'], 'SUM(f[v])')
        self.assertEqual((leg['medidas']['Total']['formato'], leg['medidas']['Total']['pasta']), ('#,0', 'Vendas'))

    def test_casos_limite(self):
        # revisão 4 (QA): sem fórmula não é medida; "Nome := expressão" vale; formato com aspas fica inteiro
        self.assertEqual(leitura.de_dax('')['medidas'], {})
        self.assertEqual(leitura.de_dax('X = ')['medidas'], {})
        self.assertEqual(leitura.de_dax('// só comentário')['medidas'], {})
        self.assertEqual(leitura.de_dax('Total := SUM(f[v])')['medidas']['Total']['dax'], 'SUM(f[v])')
        import tempfile
        base = tempfile.mkdtemp(prefix='ddc0q')
        try:
            defi = os.path.join(base, 'X.SemanticModel', 'definition', 'tables')
            os.makedirs(defi)
            os.makedirs(os.path.join(base, 'X.Report'))
            with open(os.path.join(base, 'X.Report', 'report.json'), 'w') as f:
                f.write('{}')
            with open(os.path.join(defi, 'F.tmdl'), 'w', encoding='utf-8-sig', newline='\r\n') as f:
                f.write("table 'Fato X'\n\tmeasure 'Receita (R$)' = ```\n\t\t\tSUM('Fato X'[V])\n\t\t\t```\n"
                        '\t\tformatString: "R$"#,0\n\tcolumn V\n\t\tdataType: decimal\n'
                        "\tpartition 'Fato X' = entity\n\t\tmode: directLake\n")
            leg = leitura.ler(base)
            self.assertEqual(leg['medidas']['Receita (R$)']['dax'], "SUM('Fato X'[V])")
            self.assertEqual(leg['medidas']['Receita (R$)']['formato'], '"R$"#,0')
            self.assertTrue(any('formato antigo' in x for x in leg['avisos']))
            self.assertTrue(any('Direct Lake' in x for x in leg['avisos']))
        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_pbix_binario_nao_vira_dax(self):
        # revisão 6 (novato): o .pbix direto dava nota 10; agora explica as duas saídas
        import tempfile
        arq = os.path.join(tempfile.mkdtemp(prefix='ddc0b'), 'painel.pbix')
        with open(arq, 'wb') as f:
            f.write(b'PKbinario')
        with self.assertRaises(ValueError) as erro:
            leitura.ler(arq)
        self.assertIn('Salvar como', str(erro.exception))

    def test_alvo_que_nao_existe(self):
        with self.assertRaises(ValueError):
            leitura.ler('pasta/que/nao/existe')


class TestExame(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.leg = leitura.ler(LEGADO)
        cls.e = exame.examinar(cls.leg)

    def test_pega_cada_erro_plantado(self):
        esperado = {'Turnover %': {'taxa_sobre_cadastro', 'boa_pratica'}, 'Headcount': {'estoque_contagem'},
                    'Turnover Médio': {'media_de_taxas'}, 'Meta Turnover': {'meta_media'},
                    'Status Turnover': {'meta_no_codigo'}, 'Desligamentos AA': {'ano_anterior_parcial'},
                    'Var AA %': {'boa_pratica'}, 'Folha Total': {'soma_cadastro'},
                    'Desligamentos Mês Atual': {'hoje', 'boa_pratica'}, 'Desligamentos Diretor': {'dado_pessoal'},
                    'Valor Rescisões': {'ref_inexistente'}, 'Qtd Desligamentos': {'sem_descricao'}}
        for nome, cods in esperado.items():
            self.assertTrue(cods <= _codigos(self.e, nome), (nome, _codigos(self.e, nome)))
        self.assertEqual({a['codigo'] for a in self.e['modelo']},
                         {'sem_calendario', 'data_automatica', 'bidirecional', 'coluna_fazendo_medida'})

    def test_metodo_corte_parcial_e_coluna_de_taxa(self):
        # revisão 3 (metodologista): o segmentador de ano filtra os desligamentos e não o cadastro do denominador
        self.assertIn('corte_parcial', _codigos(self.e, 'Turnover %'))
        e = exame.examinar(leitura.de_dax('[Soma Pct] =\nSUM(f[Margem %])\n\n[Média Taxa] =\nAVERAGE(f[Taxa Conversão])'))
        self.assertEqual(e['medidas']['Soma Pct']['achados'][0]['gravidade'], 'critico')
        self.assertIn('agrega_taxa', _codigos(e, 'Média Taxa'))

    def test_nota_reprova_numero_errado(self):
        self.assertLessEqual(self.e['medidas']['Turnover %']['nota'], 4.0)
        self.assertLessEqual(self.e['medidas']['Headcount']['nota'], 7.0)
        self.assertLess(self.e['nota'], 5)
        self.assertEqual(self.e['medidas']['Turnover Acumulado']['achados'], [])
        self.assertIn(('Turnover %', 'Taxa dividida pela contagem do cadastro (Funcionarios)'),
                      self.e['medidas']['Turnover Acumulado']['herdados'])

    def test_o_que_o_deidara_gera_tira_dez(self):
        import tempfile
        pasta = tempfile.mkdtemp(prefix='ddc0')
        try:
            arq = os.path.join(pasta, 'argila.json')
            shutil.copytree(EXEMPLO, os.path.join(pasta, 'aurora'))
            arq = os.path.join(pasta, 'aurora', 'argila.json')
            _calado(_aprovar_com_prototipo, ['aprovar', arq, '--por', 'T'])
            _calado(deidara.main, ['gerar', arq, '-o', os.path.join(pasta, 'out')])
            e = exame.examinar(leitura.ler(os.path.join(pasta, 'out')))
            self.assertEqual(e['nota'], 10.0, {n: [a['codigo'] for a in x['achados']] for n, x in e['medidas'].items()
                                                if x['achados']})
        finally:
            shutil.rmtree(pasta, ignore_errors=True)

    def test_com_todos_os_recursos_tambem_tira_dez(self):
        # revisão D2 (arquiteto): grupo de cálculo, controle, daxlib, Deneb, feriados, ano fiscal, SVG, Pareto, frase
        import tempfile
        pasta = tempfile.mkdtemp(prefix='ddc0t')
        try:
            shutil.copytree(EXEMPLO, os.path.join(pasta, 'aurora'))
            arq = os.path.join(pasta, 'aurora', 'argila_completo.json')
            _calado(deidara.main, ['prototipar', arq])
            _calado(deidara.main, ['aprovar', arq, '--por', 'T', '--aceito-distorcao', 'teste'])
            codigo, out = _calado(deidara.main, ['gerar', arq, '-o', os.path.join(pasta, 'out')])
            self.assertEqual(codigo, 0, out)
            self.assertEqual(validar_pbip.conferir(os.path.join(pasta, 'out')), [])
            e = exame.examinar(leitura.ler(os.path.join(pasta, 'out')))
            self.assertEqual(e['nota'], 10.0, {n: [a['codigo'] for a in x['achados']] for n, x in e['medidas'].items()
                                                if x['achados']})
        finally:
            shutil.rmtree(pasta, ignore_errors=True)

    def test_reconhece_os_padroes(self):
        tipos = {n: x['padrao']['tipo'] for n, x in self.e['medidas'].items()}
        self.assertEqual(tipos['Turnover %'], 'divisao')
        self.assertEqual(tipos['Desligamentos AA'], 'ano_anterior')
        self.assertEqual(tipos['Turnover Acumulado'], 'acumulado_ano')
        self.assertEqual(tipos['Qtd Desligamentos'], 'agregacao')


class TestProposta(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.leg = leitura.ler(LEGADO)
        cls.e = exame.examinar(cls.leg)

    def _p(self, nome):
        return proposta.propor(nome, self.leg, self.e['medidas'][nome], self.e['medidas'])

    def test_turnover_ganha_o_estoque_medio_e_avisa_que_muda(self):
        p = self._p('Turnover %')
        self.assertEqual(p['argila'][0]['denominador'], 'Headcount Médio')
        self.assertEqual(p['argila'][1], {'nome': 'Headcount Médio', 'tipo': 'media_mensal', 'base': 'Headcount',
                                          'descricao': 'Média de Headcount no fim de cada mês do período.'})
        self.assertTrue(p['muda_o_numero'])
        self.assertEqual(p['dax_sugerido'], 'DIVIDE([Qtd Desligamentos], [Headcount])')

    def test_headcount_vira_estoque(self):
        m = self._p('Headcount')['argila'][0]
        self.assertEqual((m['tipo'], m['entradas'], m['saidas']),
                         ('estoque_na_data', 'Funcionarios[DataAdmissao]', 'Desligamentos[DataDesligamento]'))

    def test_meta_ponderada_pelo_denominador_novo(self):
        m = self._p('Meta Turnover')['argila'][0]
        self.assertEqual((m['tipo'], m['peso'], m['por']), ('media_ponderada', 'Headcount Médio', 'Empresas[CodEmpresa]'))

    def test_iferror_vira_divide(self):
        self.assertEqual(self._p('Var AA %')['dax_sugerido'],
                         'DIVIDE([Qtd Desligamentos] - [Desligamentos AA], [Desligamentos AA], 0)')

    def test_media_de_taxas_vira_a_taxa(self):
        self.assertEqual(self._p('Turnover Médio')['argila'][0]['dax'], '[Turnover %]')


class TestImportar(unittest.TestCase):
    def test_refaz_o_painel_e_compara_antes_e_depois(self):
        import tempfile
        pasta = tempfile.mkdtemp(prefix='ddc0i')
        try:
            saida = os.path.join(pasta, 'p')
            codigo, out = _calado(deidara.main, ['c0', 'importar', LEGADO, '-o', saida, '--manter-antigas'])
            self.assertEqual(codigo, 0, out)
            a = _json(os.path.join(saida, 'argila.json'))
            nomes = {m['nome'] for m in a['medidas']}
            self.assertIn('Headcount Médio', nomes)
            self.assertIn('Turnover % (antes)', nomes)
            self.assertNotIn('Valor Rescisões', nomes)                       # não calculava no modelo antigo
            self.assertNotIn('Calendario', {t['nome'] for t in a['tabelas']})
            self.assertEqual(a['calendario']['datas'], [{'tabela': 'Desligamentos', 'coluna': 'DataDesligamento'}])
            t = next(m for m in a['medidas'] if m['nome'] == 'Turnover %')
            self.assertEqual((t['meta'], t['polaridade']), ('Meta Turnover', 'menor_melhor'))
            antes = next(m for m in a['medidas'] if m['nome'] == 'Desligamentos AA (antes)')
            self.assertIn('[Qtd Desligamentos (antes)]', antes['dax'])
            self.assertIn('dCalendario[Data]', antes['dax'])
            self.assertTrue(os.path.exists(os.path.join(saida, 'c0_relatorio.md')))
            codigo, out = _calado(deidara.main, ['validar', os.path.join(saida, 'argila.json')])
            self.assertNotIn('erro(s)', out)
            m, _ = resolver(a, {'legado': catalogo.carregar(os.path.join(saida, 'catalogos', 'legado.json'), 'legado')})
            from tecnicas.c3 import docs
            self.assertIn('"Turnover % (antes)", [Turnover % (antes)]', docs.consulta_dax(m))
        finally:
            shutil.rmtree(pasta, ignore_errors=True)


class TestComando(unittest.TestCase):
    def test_estudar_propor_e_json(self):
        codigo, out = _calado(deidara.main, ['c0', 'estudar', LEGADO])
        self.assertEqual(codigo, 0)
        self.assertIn('reprovado', out)
        codigo, out = _calado(deidara.main, ['c0', 'propor', LEGADO, '--medida', 'turnover %'])
        self.assertIn('Muda o número', out)
        self.assertIn('"tipo": "divisao"', out)
        codigo, out = _calado(deidara.main, ['c0', 'estudar', LEGADO, '--json'])
        self.assertIn('"nota":', out)
        codigo, out = _calado(deidara.main, ['c0', 'estudar', LEGADO, '--medida', 'Turnoverr'])
        self.assertEqual(codigo, 1)
        self.assertIn('parecidas', out)

    def test_relatorio_nao_mostra_dado_pessoal(self):
        # revisão 5 (LGPD): o CPF escrito na fórmula do legado não sai no relatório, no JSON nem no terminal
        import tempfile
        arq = os.path.join(tempfile.mkdtemp(prefix='ddc0l'), 'r.md')
        for args in (['c0', 'propor', LEGADO, '-o', arq], ['c0', 'estudar', LEGADO, '--json'], ['c0', 'propor', LEGADO]):
            _, out = _calado(deidara.main, args)
            self.assertNotIn('123.456.789-09', out)
        with open(arq, encoding='utf-8') as f:
            texto = f.read()
        self.assertNotIn('123.456.789-09', texto)
        self.assertIn('***.***.***-**', texto)
        codigo, out = _calado(deidara.main, ['c0', 'importar', LEGADO, '-o', os.path.dirname(arq) + '/p', '--fonte', '../x'])
        self.assertEqual(codigo, 1)

    def test_modelo_grande_sem_explodir(self):
        # revisão 7 (desempenho): medida sobre medida montava a árvore inteira de novo (exponencial)
        import time
        linhas = ['[M0] =\nSUM(f[v])']
        for i in range(1, 500):
            linhas.append(f'[M{i}] =\nDIVIDE([M{i - 1}], [M{max(0, i - 2)}]) + [M{i // 2}]')
        leg = leitura.de_dax('\n\n'.join(linhas))
        inicio = time.perf_counter()
        e = exame.examinar(leg)
        self.assertLess(time.perf_counter() - inicio, 10)
        self.assertEqual(len(e['medidas']), 500)
        from tecnicas.c0.anatomia import dependencias
        self.assertEqual(len(dependencias('M499', leg)), 499)

    def test_dax_direto_na_linha_de_comando(self):
        codigo, out = _calado(deidara.main, ['c0', 'estudar', 'IFERROR([A] / [B], 0)'])
        self.assertEqual(codigo, 0)
        self.assertIn('IFERROR', out)


class TestSemFalsoAlarme(unittest.TestCase):
    """DAX realista: o exame acusa o que deve e não acusa o que está certo (revisão 1, especialista em DAX)."""
    CASOS = {
        # nome: (dax, códigos que DEVEM aparecer, códigos que NÃO podem aparecer)
        'Margem %': ('DIVIDE(SUM(f[Receita]) - SUM(f[Custo]), SUM(f[Receita]))', set(), {'boa_pratica'}),
        'Preço Médio': ('DIVIDE([Receita], [Qtd])', set(), set()),
        'Por Cem': ('[Receita] / 100', set(), {'boa_pratica'}),
        'Guarda zero': ('IF([Qtd] > 0, [Receita] / [Qtd])', {'boa_pratica'}, {'meta_no_codigo'}),
        'Comentado': ('// usa TODAY() só no comentário\nSUM(f[Receita])', set(), {'hoje'}),
        'Texto hoje': ('"Atualizado: " & FORMAT(MAX(f[Data]), "dd/mm/yyyy")', set(), {'hoje'}),
        'AA certo': ('VAR _u = MAX(f[Data])\nRETURN CALCULATE([Receita], SAMEPERIODLASTYEAR(d[Data]), d[Data] <= EDATE(_u, -12))',
                     set(), {'ano_anterior_parcial'}),
        'AA ingênuo': ('CALCULATE([Receita], DATEADD(d[Data], -1, YEAR))', {'ano_anterior_parcial'}, set()),
        'Média pond': ('AVERAGEX(f, f[Preço] * f[Qtd])', set(), {'media_de_taxas'}),
        'HC médio': ('AVERAGEX(VALUES(d[Mês]), [Clientes])', set(), {'media_de_taxas'}),
        'Soma taxas': ('SUMX(VALUES(p[Produto]), [Margem %])', {'soma_de_taxas'}, set()),
        'Média taxas': ('AVERAGEX(VALUES(p[Produto]), [Margem %])', {'media_de_taxas'}, set()),
        'Meta no IF': ('IF([Margem %] >= 0.3, "OK", "Abaixo")', {'meta_no_codigo'}, set()),
        'Participação': ('DIVIDE([Receita], CALCULATE([Receita], ALL(p)))', {'participacao_all'}, set()),
        'Participação sel': ('DIVIDE([Receita], CALCULATE([Receita], ALLSELECTED(p)))', set(), {'participacao_all'}),
        'Agora': ('CALCULATE([Receita], d[Data] <= TODAY())', {'hoje'}, set()),
        'Receita': ('SUM(f[Receita])', set(), set()),
        'Qtd': ('SUM(f[Qtd])', set(), set()),
        'Custo': ('SUM(f[Custo])', set(), set()),
        'Clientes': ('DISTINCTCOUNT(f[Cliente])', set(), set()),
        'Selecionado': ('SELECTEDVALUE(p[Produto], "Todos")', set(), set()),
        'Rank': ('RANKX(ALL(p[Produto]), [Receita])', set(), set()),
        'Var %': ('VAR a = [Receita] VAR b = [AA ingênuo] RETURN DIVIDE(a - b, b)', set(), {'boa_pratica'}),
        'Filtro coluna': ("CALCULATE([Receita], KEEPFILTERS(p[Categoria] = \"A\"))", set(), {'boa_pratica'}),
        'Filtro tabela': ('CALCULATE([Receita], FILTER(p, p[Categoria] = "A"))', {'boa_pratica'}, set()),
        'Iterador ok': ('SUMX(VALUES(p[Produto]), [Receita])', set(), {'soma_de_taxas'}),
        'Novo nome': ('MAXX(ADDCOLUMNS(VALUES(p[Produto]), "@r", [Receita]), [@r])', set(), {'ref_inexistente'}),
        'Email': ('CALCULATE([Receita], c[Email] = "ana@empresa.com")', {'dado_pessoal'}, set()),
    }

    def test_cada_caso(self):
        texto = '\n\n'.join(f"[{n}] =\n{d}" for n, (d, _, _) in self.CASOS.items())
        leg = leitura.de_dax(texto)
        self.assertEqual(set(leg['medidas']), set(self.CASOS))
        e = exame.examinar(leg)
        for n, (_, quer, nao) in self.CASOS.items():
            cods = {a['codigo'] for a in e['medidas'][n]['achados']}
            self.assertTrue(quer <= cods, (n, 'faltou', quer - cods))
            self.assertFalse(cods & nao, (n, 'alarme falso', cods & nao))


if __name__ == '__main__':
    unittest.main()
