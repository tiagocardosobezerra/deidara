"""
Testes do Deidara sobre o exemplo fictício "Aurora" (ERP em SQL Server + planilha de metas).

    python3 -m unittest discover -s testes
"""

import copy
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
os.environ['DEIDARA_MEMORY_CARD_DIR'] = '-'      # o cartão de quem roda os testes não interfere
sys.path.insert(0, os.path.join(RAIZ, 'ferramentas'))

import deidara  # noqa: E402
import validar_pbip  # noqa: E402
from argila.especificacao import referencias_dax, resolver  # noqa: E402
from argila import catalogo, receitas  # noqa: E402

EXEMPLO = os.path.join(RAIZ, 'exemplos', 'aurora')


def _base():
    with open(os.path.join(EXEMPLO, 'argila.json'), encoding='utf-8') as f:
        return json.load(f)


def _md(argila, nome):
    return next(x for x in argila['medidas'] if x['nome'] == nome)


CATALOGOS = {n: catalogo.carregar(os.path.join(EXEMPLO, 'catalogos', f'{n}.json'), n) for n in ('erp', 'metas')}


def _resolver(argila):
    return resolver(argila, CATALOGOS)


def _calado(fn, *args):
    with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()):
        codigo = fn(*args)
    return codigo, out.getvalue()


class TestValidacao(unittest.TestCase):
    def test_exemplo_valida_sem_erro(self):
        m, p = _resolver(_base())
        self.assertEqual(p.erros, [])
        self.assertEqual(len(m['paginas']), 2)

    def test_tabela_inventada_e_erro(self):
        a = _base()
        a['tabelas'][1]['origem'] = 'F_CARGOS'
        _, p = _resolver(a)
        self.assertTrue(any('F_CARGOS' in e and 'F_CARGO' in e for e in p.erros), p.erros)

    def test_coluna_inventada_e_erro_com_sugestao(self):
        a = _base()
        a['tabelas'][1]['colunas'][1]['coluna'] = 'DESCRICAO_CARGO'
        _, p = _resolver(a)
        self.assertTrue(any('DESCRICAO_CARGO' in e and 'DESCRICAOCARGO' in e for e in p.erros), p.erros)

    def test_fk_invertida_e_erro(self):
        a = _base()
        a['relacionamentos'][0] = {'de': 'dCargo', 'para': 'dColaborador'}
        _, p = _resolver(a)
        self.assertTrue(any('inverta' in e for e in p.erros), p.erros)

    def test_ligacao_sem_fk_e_erro(self):
        a = _base()
        a['relacionamentos'].append({'de': 'dCargo', 'para': 'dEmpresa'})
        _, p = _resolver(a)
        self.assertTrue(any('não invente' in e for e in p.erros), p.erros)

    def test_soma_de_texto_e_erro(self):
        a = _base()
        _md(a, 'Remuneração Total')['coluna'] = 'dColaborador[Colaborador]'
        _, p = _resolver(a)
        self.assertTrue(any('numérica' in e for e in p.erros), p.erros)

    def test_dependencia_circular(self):
        a = _base()
        a['medidas'] += [{'nome': 'A', 'dax': '[B] + 1'}, {'nome': 'B', 'dax': '[A] + 1'}]
        _, p = _resolver(a)
        self.assertTrue(any('circular' in e for e in p.erros), p.erros)

    def test_dax_livre_com_coluna_inexistente(self):
        a = _base()
        a['medidas'].append({'nome': 'X', 'dax': 'SUM(dColaborador[Salario])'})
        _, p = _resolver(a)
        self.assertTrue(any('Salario' in e for e in p.erros), p.erros)

    def test_visual_com_medida_inexistente(self):
        a = _base()
        a['paginas'][0]['visuais'].append({'tipo': 'cartao', 'medida': 'Absenteísmo'})
        _, p = _resolver(a)
        self.assertTrue(any('Absenteísmo' in e for e in p.erros), p.erros)

    def test_coluna_que_nao_filtra_a_medida_gera_aviso(self):
        a = _base()
        a['paginas'][0]['visuais'].append({'tipo': 'barras', 'categoria': 'dMotivo[Motivo]', 'valores': ['Cadastros']})
        _, p = _resolver(a)
        self.assertTrue(any('não filtra a medida "Cadastros"' in x for x in p.avisos), p.avisos)

    def test_coluna_que_filtra_so_as_saidas_do_estoque(self):
        a = _base()
        a['paginas'][0]['visuais'].append({'tipo': 'barras', 'categoria': 'dMotivo[Motivo]', 'valores': ['Headcount']})
        _, p = _resolver(a)
        self.assertTrue(any('filtra só parte de "Headcount" (não chega em dColaborador)' in x for x in p.avisos), p.avisos)

    def test_segmentador_que_filtra_so_parte_da_medida(self):
        a = _base()
        a['medidas'].append({'nome': 'Taxa Simples', 'tipo': 'divisao', 'numerador': 'Desligamentos',
                             'denominador': 'Cadastros', 'formato': 'percentual'})
        a['paginas'][1]['visuais'].append({'tipo': 'cartao', 'medida': 'Taxa Simples'})
        _, p = _resolver(a)
        self.assertTrue(any('dCalendario[Ano] não filtra parte da medida (dColaborador) de "Taxa Simples"' in x
                            for x in p.avisos), p.avisos)

    def test_turnover_sobre_hc_medio_e_filtrado_pelo_calendario(self):
        _, p = _resolver(_base())
        self.assertFalse(any('"Turnover"' in x and 'segmentador' in x for x in p.avisos), p.avisos)

    def test_estoque_na_data(self):
        m, _ = _resolver(_base())
        from argila.especificacao import medida
        hc = medida(m, 'Headcount')
        self.assertIn('dColaborador[Data de Admissão] <= _fim', hc['dax'])
        self.assertIn('fDesligamento[Data do Desligamento] <= _fim', hc['dax'])
        self.assertEqual(hc['formato'], 'inteiro')
        self.assertIn("AVERAGEX(VALUES(dCalendario[Ano-Mês]), [Headcount])", medida(m, 'HC Médio')['dax'])

    def test_medida_de_tempo_nao_mostra_futuro(self):
        m, _ = _resolver(_base())
        md = next(x for x in m['medidas'] if x['nome'] == 'Desligamentos Acum. Ano')
        self.assertTrue(md['dax'].startswith('IF(\n    MIN(dCalendario[Data]) > TODAY(),'), md['dax'])
        self.assertEqual(md['formato'], 'inteiro')

    def test_trimestre_sem_ano_gera_aviso(self):
        a = _base()
        a['paginas'][0]['visuais'].append({'tipo': 'colunas', 'categoria': 'dCalendario[Trimestre]',
                                           'valores': ['Desligamentos']})
        _, p = _resolver(a)
        self.assertTrue(any('soma todos os anos' in x for x in p.avisos), p.avisos)

    def test_snowflake_avisa_atributo_atual(self):
        _, p = _resolver(_base())
        self.assertTrue(any('valor ATUAL' in x for x in p.avisos))

    def test_ligacao_automatica_entra_oculta_com_tipo(self):
        m, _ = _resolver(_base())
        col = next(c for t in m['tabelas'] if t['nome'] == 'dColaborador' for c in t['colunas'] if c['nome'] == 'CODCARGO')
        self.assertTrue(col['oculta'])
        self.assertEqual(col['tipo_tmdl'], 'int64')

    def test_referencias_dax_ignoram_strings(self):
        refs = referencias_dax('CALCULATE([A], \'d Cargo\'[Cargo] = "x[y]")')
        self.assertEqual(refs, [(None, 'A'), ('d Cargo', 'Cargo')])


def _linha(secao, tabela, coluna='', tipo='', tamanho='', precisao='', escala='', nulo='', pk='', mae='', cmae='',
           fk='', ordem=''):
    return {'secao': secao, 'tabela': tabela, 'coluna': coluna, 'tipo': tipo, 'tamanho': str(tamanho),
            'precisao': str(precisao), 'escala': str(escala), 'nulo': str(nulo), 'pk_ordem': str(pk),
            'descricao': coluna.lower(), 'tabela_mae': mae, 'campo_mae': cmae, 'fk': fk, 'fk_ordem': str(ordem)}


def _schema_sintetico():
    """Pedidos x clientes, como se viessem da receita SQL: FK em tipos diferentes (varchar -> int),
    FK composta e colunas de borda."""
    L = _linha
    linhas = [
        L('coluna', 'PEDIDO', 'ID', 'int', 4, 10, 0, 0, 1), L('coluna', 'PEDIDO', 'CODCLI', 'varchar', 10, 0, 0, 1),
        L('coluna', 'PEDIDO', 'TAXA', 'decimal', 9, 18, 6, 1), L('coluna', 'PEDIDO', 'DATA', 'datetime', 8, 23, 3, 1),
        L('coluna', 'PEDIDO', 'HORA', 'time', 5, 16, 7, 1), L('coluna', 'PEDIDO', 'EMP', 'int', 4, 10, 0, 1),
        L('coluna', 'PEDIDO', 'LOJA', 'smallint', 2, 5, 0, 1),
        L('coluna', 'CLIENTE', 'COD', 'int', 4, 10, 0, 0, 1), L('coluna', 'CLIENTE', 'NOME', 'varchar', 60, 0, 0, 1),
        L('coluna', 'LOJA', 'EMP', 'int', 4, 10, 0, 0, 1), L('coluna', 'LOJA', 'LOJA', 'smallint', 2, 5, 0, 0, 2),
        L('coluna', 'LOJA', 'NOMELOJA', 'varchar', 60, 0, 0, 1),
        L('fk', 'PEDIDO', 'CODCLI', mae='CLIENTE', cmae='COD', fk='FK_PED_CLI', ordem=1),
        L('fk', 'PEDIDO', 'EMP', mae='LOJA', cmae='EMP', fk='FK_PED_LOJA', ordem=1),
        L('fk', 'PEDIDO', 'LOJA', mae='LOJA', cmae='LOJA', fk='FK_PED_LOJA', ordem=2),
    ]
    cat, _ = receitas.catalogo_de_sql(linhas, 'loja')
    return {'loja': catalogo.Fonte('loja', cat, '')}


ARGILA_PEDIDOS = {
    'projeto': 'Pedidos', 'tabelas': [
        {'nome': 'fPedido', 'tipo': 'fato', 'origem': 'PEDIDO', 'colunas': ['ID', 'TAXA', 'DATA', 'HORA']},
        {'nome': 'dCliente', 'tipo': 'dimensao', 'origem': 'CLIENTE', 'colunas': ['COD', 'NOME']},
        {'nome': 'dLoja', 'tipo': 'dimensao', 'origem': 'LOJA', 'colunas': ['NOMELOJA']}],
    'relacionamentos': [{'de': 'fPedido', 'para': 'dCliente'}, {'de': 'fPedido', 'para': 'dLoja'}],
    'medidas': [{'nome': 'Pedidos', 'agregacao': 'contagem_linhas', 'tabela': 'fPedido'},
                {'nome': 'Clientes', 'agregacao': 'contagem_distinta', 'coluna': 'dCliente[COD]'}],
    'paginas': [{'nome': 'P', 'visuais': [{'tipo': 'cartao', 'medida': 'Pedidos'}]}]}


class TestTipos(unittest.TestCase):
    def setUp(self):
        self.m, self.p = resolver(copy.deepcopy(ARGILA_PEDIDOS), _schema_sintetico())

    def _col(self, t, c):
        return next(x for tt in self.m['tabelas'] if tt['nome'] == t for x in tt['colunas'] if x['nome'] == c)

    def test_sem_erro(self):
        self.assertEqual(self.p.erros, [])

    def test_tipos_diferentes_na_relacao_viram_cast_na_view(self):
        c = self._col('fPedido', 'CODCLI')
        self.assertEqual((c['cast_sql'], c['tipo_tmdl']), ('int', 'int64'))
        self.assertTrue(any('convertida para int' in a for a in self.p.avisos))
        from argila.sql import views
        self.assertIn('CAST(t.[CODCLI] AS int) AS [CODCLI]', views(self.m, self.m['fontes']['loja']))

    def test_decimal_com_mais_de_4_casas_vira_double(self):
        self.assertEqual(self._col('fPedido', 'TAXA')['tipo_tmdl'], 'double')

    def test_time_vira_datetime_com_formato_de_hora(self):
        c = self._col('fPedido', 'HORA')
        self.assertEqual((c['tipo_tmdl'], c['formato']), ('dateTime', 'hora'))

    def test_chave_composta(self):
        r = next(r for r in self.m['relacionamentos'] if r['para'] == 'dLoja')
        self.assertTrue(r['composta'])
        self.assertEqual(r['de_coluna'], 'Chave dLoja')

    def test_formato_padrao_de_contagem_e_distinct_sem_blank(self):
        md = next(x for x in self.m['medidas'] if x['nome'] == 'Clientes')
        self.assertEqual(md['formato'], 'inteiro')
        self.assertTrue(md['dax'].startswith('DISTINCTCOUNTNOBLANK('))

    def test_chave_composta_estavel_no_sql(self):
        from argila.sql import views
        v = views(self.m, self.m['fontes']['loja'])
        self.assertIn("ISNULL(RTRIM(CONVERT(nvarchar(100), t.[EMP])), N'∅')", v)
        self.assertIn("N'|'", v)

    def test_conferencia_sem_overflow_e_qualidade_com_nomes(self):
        from argila.sql import conferencia, qualidade
        f = self.m['fontes']['loja']
        self.assertIn('COUNT_BIG(*)', conferencia(self.m, f))
        for linha in qualidade(self.m, f).split('UNION ALL'):
            if 'SELECT' in linha:
                self.assertIn('AS ocorrencias', linha)

    def test_tmdl_de_data_e_moeda(self):
        from argila import tmdl
        texto = tmdl.tabela(self.m, next(t for t in self.m['tabelas'] if t['nome'] == 'fPedido'))
        self.assertIn('annotation SummarizationSetBy = User', texto)
        self.assertIn('discourageImplicitMeasures', tmdl.modelo(self.m))


class TestMetas(unittest.TestCase):
    def setUp(self):
        a = _base()
        _md(a, 'Turnover')['meta'] = 0.05                     # meta numérica (o exemplo usa a da planilha)
        self.m, self.p = _resolver(a)

    def test_meta_numerica_vira_medidas(self):
        from argila.especificacao import medida
        meta, cor = medida(self.m, 'Meta Turnover'), medida(self.m, 'Cor Turnover')
        self.assertEqual((meta['dax'], meta['formato']), ('0.05', 'percentual'))
        self.assertTrue(cor['oculta'])
        self.assertIn('_valor <= _meta', cor['dax'])          # turnover: menor é melhor

    def test_visuais_usam_a_cor(self):
        from argila import pbir
        from argila.layout import posicionar
        pg = self.m['paginas'][1]
        jsons = [json.dumps(pbir.visual(self.m, v, pos, 'x', 0), ensure_ascii=False) for v, pos in posicionar(pg['visuais'])]
        self.assertTrue(any('"labels"' in j and 'Cor Turnover' in j and 'Meta: 5,0%' in j for j in jsons))
        self.assertTrue(any('"fontColor"' in j and '"metadata": "fDesligamento.Turnover"' in j for j in jsons))

    def test_meta_invalida(self):
        a = _base()
        _md(a, 'Turnover')['meta'] = 'Meta Inexistente'
        _, p = _resolver(a)
        self.assertTrue(any('meta "Meta Inexistente"' in e for e in p.erros), p.erros)


class TestGovernanca(unittest.TestCase):
    def test_rls_gera_papel(self):
        from argila import tmdl
        a = copy.deepcopy(ARGILA_PEDIDOS)
        a['seguranca'] = [{'papel': 'Por cliente', 'regras': [
            {'tabela': 'dCliente', 'filtro': 'dCliente[NOME] = USERPRINCIPALNAME()'}]}]
        m, p = resolver(a, _schema_sintetico())
        self.assertEqual(p.erros, [])
        texto = tmdl.role(m['seguranca'][0])
        self.assertIn("role 'Por cliente'", texto)
        self.assertIn('	tablePermission dCliente = dCliente[NOME] = USERPRINCIPALNAME()', texto)

    def test_rls_com_coluna_inexistente(self):
        a = copy.deepcopy(ARGILA_PEDIDOS)
        a['seguranca'] = [{'papel': 'X', 'regras': [{'tabela': 'dCliente', 'filtro': 'dCliente[EMAIL] = USERPRINCIPALNAME()'}]}]
        _, p = resolver(a, _schema_sintetico())
        self.assertTrue(any('EMAIL' in e for e in p.erros), p.erros)

    def test_id_do_visual_nao_depende_da_ordem(self):
        import tempfile as tf
        from argila import pbir

        def ids(argila):
            m, _ = _resolver(argila)
            d = tf.mkdtemp(prefix='ddv')
            pbir.gravar(m, d, 'X')
            pg = os.path.join(d, 'X.Report', 'definition', 'pages')
            out = {r.split(os.sep)[-1] for r, _, fs in os.walk(pg) if 'visual.json' in fs}
            shutil.rmtree(d, ignore_errors=True)
            return out

        a = _base()
        b = _base()
        b['paginas'][0]['visuais'] = list(reversed(b['paginas'][0]['visuais']))
        self.assertEqual(ids(a), ids(b))


COLADO_DAX = "\n".join("\t".join(l) for l in [
    ["[secao]", "[tabela]", "[coluna]", "[tipo]", "[descricao]", "[extra]", "[expressao]"],
    ["tabela", "Vendas", "", "", "Vendas do SharePoint", "", ""],
    ["tabela", "Calc", "", "", "", "calculada", ""],
    ["coluna", "Vendas", "Loja", "Int64", "", "", ""],
    ["coluna", "Vendas", "Valor", "Decimal", "Valor da venda", "", ""],
    ["coluna", "Vendas", "Data", "DateTime", "", "", ""],
    ["coluna", "Vendas", "Margem", "Double", "", "calculada", ""],
    ["coluna", "Lojas", "Loja", "Int64", "", "", ""],
    ["coluna", "Lojas", "Nome", "String", "", "", ""],
    ["relacao", "Vendas", "Loja", "Many>One", "Lojas[Loja]", "ativa", ""],
    ["particao", "Vendas", "", "4", "", "", "let⏎    Fonte = SharePoint.Tables(Site)⏎in⏎    Fonte"],
    ["particao", "Lojas", "", "4", "", "", "let⏎    Fonte = Excel.Workbook(File.Contents(Arq))⏎in⏎    Fonte"],
    ["expressao", "Site", "", "0", "", "", "\"https://x.sharepoint.com/sites/rh\" meta [IsParameterQuery=true]"],
])


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
        from argila import tmdl
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
        from argila import tmdl
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


class TestDicionario(unittest.TestCase):
    def test_funcao_inventada_e_erro_com_sugestao(self):
        a = _base()
        a['medidas'].append({'nome': 'X', 'dax': 'CALCULATE([Desligamentos], SAMEPERIODLASTYAER(dCalendario[Data]))'})
        _, p = _resolver(a)
        self.assertTrue(any('SAMEPERIODLASTYAER' in e and 'SAMEPERIODLASTYEAR' in e for e in p.erros), p.erros)

    def test_dax_gerado_e_padroes_so_usam_funcoes_do_dicionario(self):
        from argila import dicionario
        m, _ = _resolver(_base())
        for md in m['medidas']:
            self.assertEqual(dicionario.desconhecidas(md['dax']), [], md['nome'])
        for pd in dicionario.padroes()['padroes']:
            for dax in (pd.get('dax'), (pd.get('argila') or {}).get('dax')):
                if dax:
                    self.assertEqual(dicionario.desconhecidas(dax), [], pd['id'])

    def test_nomes_de_coluna_e_texto_nao_viram_funcao(self):
        from argila import dicionario
        self.assertEqual(dicionario.funcoes_usadas("SUM('T x'[A(b)]) + LEN(\"ABC(\") // FOO(1)"), ['SUM', 'LEN'])

    def test_toda_funcao_tem_link_oficial_e_as_principais_tem_descricao(self):
        from argila import dicionario
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


class TestDescoberta(unittest.TestCase):
    def test_tokens_e_nucleo(self):
        from argila import descoberta as d
        self.assertEqual(d.nucleo('CODEMPRESA'), {'empresa'})
        self.assertEqual(d.nucleo('Cód. Empresa'), {'empresa'})
        self.assertEqual(d.nucleo('cod_empresa_fk'), {'empresa'})
        self.assertEqual(d.nucleo('MATRICULA'), {'matricula'})
        self.assertTrue(d.tem_marca_de_chave('MATRICULA'))
        self.assertFalse(d.tem_marca_de_chave('Empresa'))

    def test_buscar_por_pedido_em_todas_as_fontes(self):
        from argila import descoberta as d
        self.assertEqual(d.buscar(CATALOGOS, 'salário dos colaboradores')[0]['tabela'], 'F_FUNCIONARIO')
        nomes = [r['tabela'] for r in d.buscar(CATALOGOS, 'meta de turnover por empresa')[:3]]
        self.assertIn('Metas', nomes)

    def _sem_ligacao_da_planilha(self):
        a = _base()
        a['relacionamentos'] = [r for r in a['relacionamentos'] if r['de'] != 'fMeta']
        m, _ = _resolver(a)
        from argila import descoberta as d
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
        from argila import descoberta as d
        m, _ = _resolver(_base())
        tabelas = [(t['fonte'], t['origem'], t['nome']) for t in m['tabelas'] if t.get('origem')]
        self.assertEqual(d.relacionar(CATALOGOS, tabelas, {(r['de'], r['para']) for r in m['relacionamentos']}), [])

    def test_trecho_argila_pede_quem_confirmou(self):
        from argila import descoberta as d
        trecho = d.trecho_argila(self._sem_ligacao_da_planilha()[0])
        self.assertEqual(trecho['declarada']['campos'], [['Cód. Empresa', 'CODEMPRESA']])
        self.assertEqual(trecho['declarada']['por'], '<quem confirmou>')


class TestProva(unittest.TestCase):
    def test_receita_sql_na_mesma_fonte_e_m_entre_fontes(self):
        from argila import prova
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
        from argila import prova
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

    def test_prova_com_chave_repetida_e_erro(self):
        _, p = self._com_prova(mae_unica=False)
        self.assertTrue(any('reprovou' in e for e in p.erros), p.erros)


class TestMemoryCard(unittest.TestCase):
    """Cartão do time local (sem GitHub); o Deidara usa a seção deidara/ com a estrutura padrão."""

    def setUp(self):
        from argila import memory_card
        self.mc = memory_card
        self.dir = tempfile.mkdtemp(prefix='ddm')
        self.cartao = os.path.join(self.dir, 'cartao')
        self._config = memory_card.CONFIG
        memory_card.CONFIG = os.path.join(self.dir, 'cfg', 'memory_card.json')
        memory_card.iniciar(None, self.cartao)
        os.environ['DEIDARA_MEMORY_CARD_DIR'] = self.cartao
        self.ex = os.path.join(self.dir, 'ex')
        shutil.copytree(os.path.join(EXEMPLO, 'catalogos'), os.path.join(self.ex, 'catalogos'))
        self.argila = os.path.join(self.ex, 'argila.json')
        self._gravar(_base())

    def tearDown(self):
        self.mc.CONFIG = self._config
        os.environ['DEIDARA_MEMORY_CARD_DIR'] = '-'
        shutil.rmtree(self.dir, ignore_errors=True)

    def _gravar(self, argila):
        with open(self.argila, 'w', encoding='utf-8') as f:
            json.dump(argila, f, ensure_ascii=False)

    def _enviar(self, *extra):
        return _calado(deidara.main, ['memory-card', 'enviar', self.argila, '--categoria', 'Recursos Humanos',
                                      '--secao', 'Turnover', '--por', 'Teste', *extra])

    def _aprovado_e_enviado(self):
        _calado(deidara.main, ['aprovar', self.argila, '--por', 'Ana'])
        return self._enviar('--confirmar')

    def test_estrutura_padrao_na_secao_deidara(self):
        for x in ('README.md', 'CATALOGO.md', 'saves'):
            self.assertTrue(os.path.exists(os.path.join(self.cartao, 'deidara', x)), x)
        self.assertTrue(os.path.exists(os.path.join(self.cartao, 'README.md')))      # cartão novo: raiz criada
        self.assertFalse(os.path.exists(os.path.join(self.cartao, 'saves')))
        self.assertEqual((self.mc.NOME_PADRAO, self.mc.SECAO), ('memory-card', 'deidara'))

    def test_convive_com_outra_solucao_no_mesmo_cartao(self):
        import subprocess
        outro = os.path.join(self.dir, 'cartao_do_time')
        os.makedirs(os.path.join(outro, 'saves', 'rh', 'funcionarios', 'relatorio'))
        raiz = {'README.md': '# Memory Card\n(de outra solução)\n', 'CATALOGO.md': '# Catálogo da outra solução\n',
                os.path.join('saves', 'rh', 'funcionarios', 'relatorio', 'ficha.json'): '{"categoria": "RH"}'}
        for nome, texto in raiz.items():
            with open(os.path.join(outro, nome), 'w', encoding='utf-8') as f:
                f.write(texto)
        for args in (['init', '-q'], ['add', '-A'], ['-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', 'outra']):
            subprocess.run(['git', '-C', outro, *args], capture_output=True)
        with open(os.path.join(outro, 'pendente.txt'), 'w', encoding='utf-8') as f:
            f.write('trabalho em andamento de outra solução')
        self.mc.iniciar(None, outro)
        os.environ['DEIDARA_MEMORY_CARD_DIR'] = outro
        os.environ['GIT_AUTHOR_NAME'] = os.environ['GIT_COMMITTER_NAME'] = 't'
        os.environ['GIT_AUTHOR_EMAIL'] = os.environ['GIT_COMMITTER_EMAIL'] = 't@t'
        try:
            codigo, _ = self._aprovado_e_enviado()
        finally:
            for k in ('GIT_AUTHOR_NAME', 'GIT_COMMITTER_NAME', 'GIT_AUTHOR_EMAIL', 'GIT_COMMITTER_EMAIL'):
                os.environ.pop(k, None)
        self.assertEqual(codigo, 0)
        for nome, texto in raiz.items():
            with open(os.path.join(outro, nome), encoding='utf-8') as f:
                self.assertEqual(f.read(), texto, nome)
        tocados = subprocess.run(['git', '-C', outro, 'log', '--name-only', '--format=', '-n', '2'],
                                 capture_output=True, text=True).stdout.split()
        self.assertTrue(tocados and all(x.startswith('deidara/') for x in tocados), tocados)
        status = subprocess.run(['git', '-C', outro, 'status', '--porcelain'], capture_output=True, text=True).stdout
        self.assertIn('pendente.txt', status)                                     # continua só de quem estava fazendo

    def test_enviar_pede_aprovacao_e_previa_nao_grava(self):
        codigo, out = self._enviar()
        self.assertEqual(codigo, 1)
        self.assertIn('sem aprovação', out)
        _calado(deidara.main, ['aprovar', self.argila, '--por', 'Ana'])
        codigo, out = self._enviar()
        self.assertEqual(codigo, 0)
        self.assertIn('saves/recursos-humanos/turnover/quadro-e-turnover', out)
        self.assertEqual(self.mc.saves(self.cartao), [])

    def test_confirmar_grava_painel_indicadores_e_nunca_os_catalogos(self):
        codigo, _ = self._aprovado_e_enviado()
        self.assertEqual(codigo, 0)
        ref = 'recursos-humanos/turnover/quadro-e-turnover'
        save = os.path.join(self.cartao, 'deidara', 'saves', *ref.split('/'))
        for x in ('README.md', 'ficha.json', 'argila.json', 'dicionario_indicadores.md', 'prototipo.html'):
            self.assertTrue(os.path.exists(os.path.join(save, x)), x)
        with open(os.path.join(save, 'README.md'), encoding='utf-8') as f:
            readme = f.read()
        self.assertIn('<!-- corpo -->', readme)
        self.assertIn('<!-- /corpo -->', readme)
        todos = [os.path.join(r, x) for r, _, fs in os.walk(self.cartao) for x in fs if '.git' not in r]
        self.assertFalse(any('catalogo' in os.path.basename(x).lower() and x.endswith('.json') for x in todos))
        self.assertFalse(any(os.path.basename(x) in ('erp.json', 'metas.json') for x in todos))
        fichas = dict(self.mc.saves(self.cartao))
        self.assertIn('indicadores/turnover/turnover', fichas[ref]['relacionados'])
        self.assertIn(ref, fichas['indicadores/turnover/turnover']['relacionados'])

    def test_mudanca_pede_motivo_e_versiona(self):
        self._aprovado_e_enviado()
        a = _base()
        _md(a, 'Turnover')['denominador'] = 'Headcount'
        self._gravar(a)
        _calado(deidara.main, ['aprovar', self.argila, '--por', 'Ana'])
        codigo, out = self._enviar('--confirmar')
        self.assertEqual(codigo, 1)
        self.assertIn('--motivo', out)
        codigo, _ = self._enviar('--confirmar', '--motivo', 'turnover sobre headcount de fim de período')
        self.assertEqual(codigo, 0)
        ind = dict(self.mc.saves(self.cartao))['indicadores/turnover/turnover']
        self.assertEqual(ind['versao'], 2)
        self.assertEqual(ind['historico'][-1]['motivo'], 'turnover sobre headcount de fim de período')
        self.assertIn('HC Médio', ind['historico'][-1]['dax_anterior'])

    def test_oficial_pede_motivo_avisa_no_validar_e_bloqueia_mudanca(self):
        self._aprovado_e_enviado()
        with self.assertRaises(ValueError):
            self.mc.marcar(self.cartao, 'indicadores/turnover/turnover', 'oficial', 'Teste')
        self.mc.marcar(self.cartao, 'indicadores/turnover/turnover', 'oficial', 'Teste', 'comitê de RH')
        a = _base()
        _md(a, 'Turnover')['denominador'] = 'Headcount'
        self._gravar(a)
        _, out = _calado(deidara.main, ['validar', self.argila])
        self.assertIn('difere do indicador OFICIAL', out)
        _calado(deidara.main, ['aprovar', self.argila, '--por', 'Ana'])
        codigo, out = self._enviar('--confirmar', '--motivo', 'x')
        self.assertEqual(codigo, 1)
        self.assertIn('é OFICIAL', out)
        with self.assertRaises(ValueError):
            self.mc.marcar(self.cartao, 'recursos-humanos/turnover/quadro-e-turnover', 'oficial', 'Teste', 'x')

    def test_buscar(self):
        self._aprovado_e_enviado()
        refs = [r for r, _ in self.mc.buscar(self.cartao, ['headcount'])]
        self.assertIn('indicadores/quadro/headcount', refs)
        self.assertEqual(self.mc.buscar(self.cartao, ['inexistente']), [])

    def test_conferir_acha_coluna_que_sumiu_da_fonte(self):
        self._aprovado_e_enviado()
        cats = dict(CATALOGOS)
        self.assertEqual(self.mc.conferir(self.cartao, cats, resolver)['recursos-humanos/turnover/quadro-e-turnover'][0], 'ok')
        arq = os.path.join(self.ex, 'catalogos', 'erp.json')
        with open(arq, encoding='utf-8') as f:
            c = json.load(f)
        c['tabelas']['F_CARGO']['colunas'] = [x for x in c['tabelas']['F_CARGO']['colunas'] if x['coluna'] != 'DESCRICAOCARGO']
        cats['erp'] = catalogo.Fonte('erp', c, arq)
        sit, det = self.mc.conferir(self.cartao, cats, resolver)['recursos-humanos/turnover/quadro-e-turnover']
        self.assertEqual(sit, 'quebrado')
        self.assertTrue(any('DESCRICAOCARGO' in d for d in det))


class TestSimulacao(unittest.TestCase):
    def setUp(self):
        from argila.simulacao import Simulador, categorias
        self.m, _ = _resolver(_base())
        self.sim, self.cat = Simulador(self.m), categorias
        self.cargo = {'tipo': 'coluna', 'tabela': 'dCargo', 'nome': 'Cargo', 'familia': 'texto'}
        self.motivo = {'tipo': 'coluna', 'tabela': 'dMotivo', 'nome': 'Motivo', 'familia': 'texto'}

    def test_fatias_somam_o_total(self):
        rot = self.cat(self.m, self.cargo)
        soma = sum(self.sim.serie('Remuneração Total', self.cargo, rot))
        self.assertAlmostEqual(soma, self.sim.valor('Remuneração Total'), places=4)

    def test_divisao_e_coerente(self):
        f = [(self.cargo, 'Cargo B')]
        self.assertAlmostEqual(self.sim.valor('Remuneração Média', f),
                               self.sim.valor('Remuneração Total', f) / self.sim.valor('Cadastros', f))

    def test_coluna_que_nao_filtra_repete_o_valor(self):
        rot = self.cat(self.m, self.motivo)
        self.assertEqual(len(set(self.sim.serie('Cadastros', self.motivo, rot))), 1)


class TestFluxo(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='dd')
        shutil.copytree(os.path.join(EXEMPLO, 'catalogos'), os.path.join(self.dir, 'catalogos'))
        self.argila = os.path.join(self.dir, 'argila.json')
        with open(self.argila, 'w', encoding='utf-8') as f:
            json.dump(_base(), f, ensure_ascii=False)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_gerar_sem_aprovacao_recusa(self):
        codigo, out = _calado(deidara.main, ['gerar', self.argila, '-o', os.path.join(self.dir, 'o')])
        self.assertEqual(codigo, 1)
        self.assertIn('Sem aprovação', out)

    def test_mudanca_depois_da_aprovacao_recusa(self):
        _calado(deidara.main, ['aprovar', self.argila, '--por', 'Teste'])
        a = _base()
        a['descricao'] = 'mudou'
        with open(self.argila, 'w', encoding='utf-8') as f:
            json.dump(a, f, ensure_ascii=False)
        codigo, out = _calado(deidara.main, ['gerar', self.argila, '-o', os.path.join(self.dir, 'o')])
        self.assertEqual(codigo, 1)
        self.assertIn('mudou depois da aprovação', out)

    def test_fluxo_completo_gera_projeto_coerente(self):
        self.assertEqual(_calado(deidara.main, ['prototipar', self.argila])[0], 0)
        self.assertTrue(os.path.exists(os.path.join(self.dir, 'argila.prototipo.html')))
        self.assertEqual(_calado(deidara.main, ['aprovar', self.argila, '--por', 'Teste'])[0], 0)
        saida = os.path.join(self.dir, 'o')
        self.assertEqual(_calado(deidara.main, ['gerar', self.argila, '-o', saida])[0], 0)
        for arq in ['Quadro_e_Turnover.pbip', 'sql/erp/01_views.sql', 'sql/erp/03_qualidade.sql', 'LEIA-ME.md',
                    'docs/dicionario_indicadores.md', 'Quadro_e_Turnover.SemanticModel/definition/model.tmdl']:
            self.assertTrue(os.path.exists(os.path.join(saida, arq)), arq)
        _, tabelas, colunas, medidas, erros = validar_pbip.validar_tmdl(saida)
        self.assertEqual(erros, [])
        self.assertEqual(len(tabelas), 7)                      # 5 do ERP + metas + calendário
        self.assertEqual(validar_pbip.validar_visuais(saida, tabelas, colunas, medidas), [])

    def test_diff_mostra_mudanca_de_formula(self):
        _calado(deidara.main, ['aprovar', self.argila, '--por', 'Teste'])
        a = _base()
        _md(a, 'Turnover')['denominador'] = 'Headcount'
        with open(self.argila, 'w', encoding='utf-8') as f:
            json.dump(a, f, ensure_ascii=False)
        _, out = _calado(deidara.main, ['diff', self.argila])
        self.assertIn('indicador Turnover: FÓRMULA mudou', out)
        codigo, out = _calado(deidara.main, ['gerar', self.argila, '-o', os.path.join(self.dir, 'o')])
        self.assertEqual(codigo, 1)
        self.assertIn('FÓRMULA mudou', out)

    def test_reaprovacao_grava_historico(self):
        _calado(deidara.main, ['aprovar', self.argila, '--por', 'Ana'])
        a = _base()
        a['versao'] = '1.2'
        a['paginas'][0]['visuais'].append({'tipo': 'cartao', 'medida': 'HC Médio'})
        with open(self.argila, 'w', encoding='utf-8') as f:
            json.dump(a, f, ensure_ascii=False)
        _calado(deidara.main, ['aprovar', self.argila, '--por', 'Bia', '--observacao', 'pedido do RH'])
        with open(os.path.join(self.dir, 'argila.aprovacao.json'), encoding='utf-8') as f:
            hist = json.load(f)['historico']
        self.assertEqual([h['aprovado_por'] for h in hist], ['Ana', 'Bia'])
        self.assertIn('versão: 1.1 → 1.2', hist[1]['mudancas'])
        saida = os.path.join(self.dir, 'o')
        _calado(deidara.main, ['gerar', self.argila, '-o', saida])
        with open(os.path.join(saida, 'docs', 'dicionario_indicadores.md'), encoding='utf-8') as f:
            self.assertIn('pedido do RH', f.read())

    def test_versao_do_deidara_diferente_pede_novo_aceite(self):
        _calado(deidara.main, ['aprovar', self.argila, '--por', 'Teste'])
        arq = os.path.join(self.dir, 'argila.aprovacao.json')
        with open(arq, encoding='utf-8') as f:
            reg = json.load(f)
        reg['deidara'] = '0.0.1'
        with open(arq, 'w', encoding='utf-8') as f:
            json.dump(reg, f)
        codigo, out = _calado(deidara.main, ['gerar', self.argila, '-o', os.path.join(self.dir, 'o')])
        self.assertEqual(codigo, 1)
        self.assertIn('Deidara 0.0.1', out)

    def test_geracao_deterministica(self):
        _calado(deidara.main, ['aprovar', self.argila, '--por', 'Teste'])
        a, b = os.path.join(self.dir, 'a'), os.path.join(self.dir, 'b')
        _calado(deidara.main, ['gerar', self.argila, '-o', a])
        _calado(deidara.main, ['gerar', self.argila, '-o', b])
        for raiz, _, arqs in os.walk(a):
            for arq in arqs:
                if arq == 'LEIA-ME.md':
                    continue
                p = os.path.join(raiz, arq)
                with open(p, 'rb') as f1, open(p.replace(a, b, 1), 'rb') as f2:
                    self.assertEqual(f1.read(), f2.read(), p)


if __name__ == '__main__':
    unittest.main()
