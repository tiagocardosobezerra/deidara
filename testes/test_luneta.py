"""
Luneta: receitas, fontes, descoberta, prova e escala.

    python3 -m unittest discover -s testes
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apoio import *  # noqa: E402,F401,F403


class TestReceitas(unittest.TestCase):
    def _colar(self, texto):
        d = tempfile.mkdtemp(prefix='ddr')
        arq = os.path.join(d, 'r.txt')
        with open(arq, 'w', encoding='utf-8') as f:
            f.write(texto)
        return arq

    def test_receitas_tem_as_funcoes_documentadas(self):
        dax = receitas.receita_dax()
        for f in ('INFO.VIEW.TABLES()', 'INFO.VIEW.COLUMNS()', 'INFO.VIEW.RELATIONSHIPS()', 'INFO.PARTITIONS()',
                  'INFO.EXPRESSIONS()', '[QueryDefinition]', '[FromCardinality]'):
            self.assertIn(f, dax)
        self.assertIn('Table.Schema(c{1})', receitas.receita_m(['Metas']))
        self.assertIn("STRING_SPLIT(@tabelas", receitas.receita_sql('dbo', ['A', 'B']))

    def test_catalogar_resultado_da_receita_dax(self):
        cat, avisos = receitas.catalogar(self._colar(COLADO_DAX), 'vendas')
        self.assertEqual(cat['tipo'], 'powerbi')
        self.assertEqual(sorted(cat['tabelas']), ['Lojas', 'Vendas'])            # a calculada ficou de fora
        cols = {c['coluna']: c['familia'] for c in cat['tabelas']['Vendas']['colunas']}
        self.assertEqual(cols, {'Loja': 'inteiro', 'Valor': 'decimal', 'Data': 'datahora'})
        self.assertIn('\n    Fonte = SharePoint.Tables(Site)', cat['tabelas']['Vendas']['expressao_m'])
        self.assertEqual(cat['fks'][0]['tabela_filha'], 'Vendas')
        self.assertIn('Site', cat['expressoes'])
        self.assertTrue(any('Margem' in a for a in avisos) and any('Calc' in a for a in avisos))

    def test_resultado_irreconhecivel(self):
        with self.assertRaises(ValueError):
            receitas.catalogar(self._colar('a\tb\n1\t2\n'), 'x')


class TestFontes(unittest.TestCase):
    def test_relacao_entre_fontes_sem_declarar_e_erro(self):
        a = _base()
        a['relacionamentos'][-1].pop('declarada')
        _, p = _resolver(a)
        self.assertTrue(any('fontes diferentes' in e for e in p.erros), p.erros)

    def test_declarada_pede_quem_e_campos_que_existem(self):
        a = _base()
        a['relacionamentos'][-1]['declarada'] = {'campos': [['Cod Empresa', 'CODEMPRESA']]}
        _, p = _resolver(a)
        self.assertTrue(any('"por"' in e for e in p.erros), p.erros)
        a['relacionamentos'][-1]['declarada']['por'] = 'Ana'
        _, p = _resolver(a)
        self.assertTrue(any('"Cod Empresa" não existe' in e and 'Cód. Empresa' in e for e in p.erros), p.erros)

    def test_power_query_reaproveita_a_consulta_do_usuario(self):
        from tecnicas.c3 import tmdl
        m, _ = _resolver(_base())
        fmeta = next(t for t in m['tabelas'] if t['nome'] == 'fMeta')
        texto = tmdl.tabela(m, fmeta)
        self.assertIn('Excel.Workbook(File.Contents(CaminhoMetas), null, true)', texto)
        self.assertIn('Table.SelectColumns(Origem, {"Meta Turnover", "Cód. Empresa"})', texto)
        self.assertIn('expression CaminhoMetas', tmdl.expressoes(m))
        self.assertIn('expression erp_Servidor', tmdl.expressoes(m))

    def test_filtro_sql_em_fonte_power_query_e_erro(self):
        a = _base()
        next(t for t in a['tabelas'] if t['nome'] == 'fMeta')['filtro'] = 'x = 1'
        _, p = _resolver(a)
        self.assertTrue(any('só vale para fonte sqlserver' in e for e in p.erros), p.erros)

    def test_chave_composta_em_power_query(self):
        from tecnicas.c3 import tmdl
        cat, _ = receitas.catalogar(TestReceitas()._colar(COLADO_DAX), 'vendas')
        fonte = catalogo.Fonte('vendas', cat, '')
        a = {'projeto': 'V', 'fontes': {'vendas': {}}, 'tabelas': [
            {'nome': 'fVendas', 'tipo': 'fato', 'origem': 'Vendas', 'colunas': ['Valor', 'Data']},
            {'nome': 'dLojas', 'tipo': 'dimensao', 'origem': 'Lojas', 'colunas': ['Nome']}],
            'relacionamentos': [{'de': 'fVendas', 'para': 'dLojas'}],
            'medidas': [{'nome': 'Total', 'agregacao': 'soma', 'coluna': 'fVendas[Valor]'}],
            'paginas': [{'nome': 'P', 'visuais': [{'tipo': 'barras', 'categoria': 'dLojas[Nome]', 'valores': ['Total']}]}]}
        m, p = resolver(a, {'vendas': fonte})
        self.assertEqual(p.erros, [])
        self.assertEqual(m['relacionamentos'][0]['prova'], 'modelo existente')
        self.assertIn('SharePoint.Tables(Site)', tmdl.tabela(m, m['tabelas'][0]))


class TestDescoberta(unittest.TestCase):
    def test_tokens_e_nucleo(self):
        from tecnicas.luneta import descoberta as d
        self.assertEqual(d.nucleo('CODEMPRESA'), {'empresa'})
        self.assertEqual(d.nucleo('Cód. Empresa'), {'empresa'})
        self.assertEqual(d.nucleo('cod_empresa_fk'), {'empresa'})
        self.assertEqual(d.nucleo('MATRICULA'), {'matricula'})
        self.assertTrue(d.tem_marca_de_chave('MATRICULA'))
        self.assertFalse(d.tem_marca_de_chave('Empresa'))

    def test_buscar_por_pedido_em_todas_as_fontes(self):
        from tecnicas.luneta import descoberta as d
        self.assertEqual(d.buscar(CATALOGOS, 'salário dos colaboradores')[0]['tabela'], 'F_FUNCIONARIO')
        nomes = [r['tabela'] for r in d.buscar(CATALOGOS, 'meta de turnover por empresa')[:3]]
        self.assertIn('Metas', nomes)

    def _sem_ligacao_da_planilha(self):
        a = _base()
        a['relacionamentos'] = [r for r in a['relacionamentos'] if r['de'] != 'fMeta']
        m, _ = _resolver(a)
        from tecnicas.luneta import descoberta as d
        tabelas = [(t['fonte'], t['origem'], t['nome']) for t in m['tabelas'] if t.get('origem')]
        return d.relacionar(CATALOGOS, tabelas, {(r['de'], r['para']) for r in m['relacionamentos']})

    def test_descobre_a_ligacao_da_planilha_com_o_erp(self):
        sug = self._sem_ligacao_da_planilha()
        s = sug[0]
        self.assertEqual((s['de'], s['campo_filho'], s['para'], s['campo_mae']),
                         ('fMeta', 'Cód. Empresa', 'dEmpresa', 'CODEMPRESA'))
        self.assertEqual(s['confianca'], 'alta')
        self.assertFalse(s['redundante'])
        self.assertTrue(all(x['redundante'] for x in sug[1:]))

    def test_coluna_de_nome_nao_vira_chave_forte(self):
        sug = self._sem_ligacao_da_planilha()
        nome = [s for s in sug if s['campo_filho'] == 'Empresa' or s['campo_mae'] == 'Empresa']
        self.assertTrue(all(s['confianca'] != 'alta' for s in nome))

    def test_tabelas_ja_ligadas_nao_recebem_sugestao(self):
        from tecnicas.luneta import descoberta as d
        m, _ = _resolver(_base())
        tabelas = [(t['fonte'], t['origem'], t['nome']) for t in m['tabelas'] if t.get('origem')]
        self.assertEqual(d.relacionar(CATALOGOS, tabelas, {(r['de'], r['para']) for r in m['relacionamentos']}), [])

    def test_trecho_argila_pede_quem_confirmou(self):
        from tecnicas.luneta import descoberta as d
        trecho = d.trecho_argila(self._sem_ligacao_da_planilha()[0])
        self.assertEqual(trecho['declarada']['campos'], [['Cód. Empresa', 'CODEMPRESA']])
        self.assertEqual(trecho['declarada']['por'], '<quem confirmou>')


class TestProva(unittest.TestCase):
    def test_receita_sql_na_mesma_fonte_e_m_entre_fontes(self):
        from tecnicas.luneta import prova
        sql_ = prova.receita_sql(('F_DESLIGAMENTO', 'CODMOTIVO', 'fDesligamento[CODMOTIVO]'),
                                 ('F_MOTIVO_DESLIGAMENTO', 'CODMOTIVO', 'dMotivo[CODMOTIVO]'), 'dbo', 'dbo')
        for trecho in ('LEFT JOIN mae AS m ON m.k = f.k', 'AS mae_unica', 'pct_linhas_com_par', 'COUNT_BIG'):
            self.assertIn(trecho, sql_)
        self.assertNotIn('SELECT *', sql_)
        m = prova.receita_m({'tipo': 'powerquery', 'origem': 'Metas', 'coluna': 'Cód. Empresa', 'rotulo': 'fMeta[x]'},
                            {'tipo': 'sqlserver', 'origem': 'N_EMPRESA', 'coluna': 'CODEMPRESA', 'rotulo': 'dEmpresa[y]',
                             'servidor': 'S', 'banco': 'B', 'esquema': 'dbo'})
        self.assertIn('Table.Column(#"Metas", "Cód. Empresa")', m)
        self.assertIn('Sql.Database("S", "B"){[Schema="dbo", Item="N_EMPRESA"]}[Data]', m)

    def _provar(self, linhas):
        from tecnicas.luneta import prova
        d = tempfile.mkdtemp(prefix='ddp')
        arq = os.path.join(d, 'r.txt')
        with open(arq, 'w', encoding='utf-8') as f:
            f.write('de\tpara\tpct_nulos_filha\tpct_linhas_com_par\tpct_codigos_com_par\tmae_unica\n' + linhas)
        return [prova.avaliar(x)[0] for x in prova.ler(receitas.ler_colado(arq)[1])]

    def test_vereditos(self):
        self.assertEqual(self._provar('a\tb\t0,0\t100,0\t100,0\tsim\n'), ['provada'])
        self.assertEqual(self._provar('a\tb\t2\t95,5\t90\tsim\n'), ['provada com ressalva'])
        self.assertEqual(self._provar('a\tb\t0\t40\t35\tsim\n'), ['fraca'])
        self.assertEqual(self._provar('a\tb\t0\t100\t100\tnao\n'), ['reprovada'])

    def _com_prova(self, **valores):
        a = _base()
        r = next(r for r in a['relacionamentos'] if r['de'] == 'fMeta')
        r['declarada']['prova'] = {'pct_nulos_filha': 0.0, 'pct_linhas_com_par': 100.0, 'pct_codigos_com_par': 100.0,
                                   'mae_unica': True, 'em': '27/10/2026', **valores}
        return _resolver(a)

    def test_prova_boa_tira_o_aviso_e_vai_para_a_documentacao(self):
        m, p = self._com_prova()
        self.assertFalse(any('fMeta -> dEmpresa' in x for x in p.avisos), p.avisos)
        r = next(r for r in m['relacionamentos'] if r['de'] == 'fMeta')
        self.assertIn('provada em 27/10/2026: 100,0% com par, chave única', r['prova'])

    def test_provar_grava_na_ligacao(self):
        d = tempfile.mkdtemp(prefix='ddp')
        arq, res = os.path.join(d, 'argila.json'), os.path.join(d, 'r.txt')
        shutil.copy(os.path.join(EXEMPLO, 'argila.json'), arq)
        with open(res, 'w', encoding='utf-8') as f:
            f.write('de\tpara\tpct_nulos_filha\tpct_linhas_com_par\tpct_codigos_com_par\tmae_unica\n'
                    'fMeta[Cód. Empresa]\tdEmpresa[CODEMPRESA]\t0\t100\t100\tsim\n')
        codigo, out = _calado(deidara.main, ['provar', '--de', res, '--argila', arq])
        self.assertEqual(codigo, 0, out)
        r = next(r for r in deidara.ler_json(arq)['relacionamentos'] if r['de'] == 'fMeta')
        self.assertEqual(r['declarada']['prova']['pct_linhas_com_par'], 100.0)
        shutil.rmtree(d, ignore_errors=True)

    def test_prova_com_chave_repetida_e_erro(self):
        _, p = self._com_prova(mae_unica=False)
        self.assertTrue(any('reprovou' in e for e in p.erros), p.erros)


class TestEscala(unittest.TestCase):
    def test_relacionar_com_indice_e_rapido(self):
        import time
        from tecnicas.luneta import descoberta
        f = _catalogo_grande()
        tabs = [('erp', t['nome'], t['nome']) for t in list(f.tabelas.values())[:40]]
        inicio = time.time()
        descoberta.relacionar({'erp': f}, tabs)
        self.assertLess(time.time() - inicio, 15)

    def test_relacionar_sem_foco_em_catalogo_grande_pede_assunto(self):
        f = _catalogo_grande(120, 3)
        d = tempfile.mkdtemp(prefix='ddg')
        arq = os.path.join(d, 'erp.json')
        with open(arq, 'w', encoding='utf-8') as fh:
            json.dump({'formato': 'deidara-catalogo/1', 'fonte': 'erp', 'tipo': 'sqlserver',
                       'tabelas': {t['nome']: {'pk': t['pk'], 'colunas': list(t['colunas'].values())}
                                   for t in f.tabelas.values()}, 'fks': []}, fh)
        codigo, out = _calado(deidara.main, ['relacionar', '--catalogos', arq])
        self.assertEqual(codigo, 1)
        self.assertIn('--pedido', out)
        shutil.rmtree(d, ignore_errors=True)
