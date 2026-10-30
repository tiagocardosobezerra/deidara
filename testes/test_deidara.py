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
import empacotar  # noqa: E402
import validar_pbip  # noqa: E402
from kibaku_nendo.especificacao import referencias_dax, resolver  # noqa: E402
from tecnicas.luneta import catalogo  # noqa: E402
from tecnicas.luneta import receitas  # noqa: E402

EXEMPLO = os.path.join(RAIZ, 'exemplos', 'aurora')


def _base():
    with open(os.path.join(EXEMPLO, 'argila.json'), encoding='utf-8') as f:
        return json.load(f)


def _md(argila, nome):
    return next(x for x in argila['medidas'] if x['nome'] == nome)


CATALOGOS = {n: catalogo.carregar(os.path.join(EXEMPLO, 'catalogos', f'{n}.json'), n) for n in ('erp', 'metas')}


def _resolver(argila):
    return resolver(argila, CATALOGOS)


def _aprovar_com_prototipo(argv):
    """O fluxo real: o gestor vê o protótipo atual e então aprova."""
    deidara.main(['prototipar', argv[1]])
    return deidara.main(argv)


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
        from kibaku_nendo.especificacao import medida
        hc = medida(m, 'Headcount')
        self.assertIn('dColaborador[Data de Admissão] <= _fim', hc['dax'])
        self.assertIn('fDesligamento[Data do Desligamento] <= _fim', hc['dax'])
        self.assertEqual(hc['formato'], 'inteiro')
        self.assertIn("AVERAGEX(VALUES(dCalendario[Ano-Mês]), [Headcount])", medida(m, 'HC Médio')['dax'])

    def test_estoque_relata_as_duas_pontas_e_aponta_o_catalogo(self):
        a = _base()
        t = next(t for t in a['tabelas'] if t['nome'] == 'dColaborador')
        t['colunas'] = [c for c in t['colunas'] if c.get('coluna') != 'DATAADMISSAO']
        _md(a, 'Headcount')['saidas'] = 'fDesligamento[Data Errada]'
        _, p = _resolver(a)
        texto = '\n'.join(p.erros)
        self.assertIn('"saidas"', texto)
        self.assertIn('"entradas"', texto)
        self.assertIn('{"coluna": "DATAADMISSAO", "nome": "Data de Admissão"}', texto)

    def test_medida_inexistente_sugere_parecida(self):
        a = _base()
        _md(a, 'Turnover')['numerador'] = 'Desligamento'
        _, p = _resolver(a)
        self.assertTrue(any('parecidas: Desligamentos' in e for e in p.erros), p.erros)

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
        from tecnicas.c3.sql import views
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
        from tecnicas.c3.sql import views
        v = views(self.m, self.m['fontes']['loja'])
        self.assertIn("ISNULL(RTRIM(CONVERT(nvarchar(100), t.[EMP])), N'∅')", v)
        self.assertIn("N'|'", v)

    def test_conferencia_sem_overflow_e_qualidade_com_nomes(self):
        from tecnicas.c3.sql import conferencia, qualidade
        f = self.m['fontes']['loja']
        self.assertIn('COUNT_BIG(*)', conferencia(self.m, f))
        for linha in qualidade(self.m, f).split('UNION ALL'):
            if 'SELECT' in linha:
                self.assertIn('AS ocorrencias', linha)

    def test_tmdl_de_data_e_moeda(self):
        from tecnicas.c3 import tmdl
        texto = tmdl.tabela(self.m, next(t for t in self.m['tabelas'] if t['nome'] == 'fPedido'))
        self.assertIn('annotation SummarizationSetBy = User', texto)
        self.assertIn('discourageImplicitMeasures', tmdl.modelo(self.m))


class TestMetas(unittest.TestCase):
    def setUp(self):
        a = _base()
        _md(a, 'Turnover')['meta'] = 0.05                     # meta numérica (o exemplo usa a da planilha)
        self.m, self.p = _resolver(a)

    def test_meta_numerica_vira_medidas(self):
        from kibaku_nendo.especificacao import medida
        meta, cor = medida(self.m, 'Meta Turnover'), medida(self.m, 'Cor Turnover')
        self.assertEqual((meta['dax'], meta['formato']), ('0.05', 'percentual'))
        self.assertTrue(cor['oculta'])
        self.assertIn('_valor <= _meta', cor['dax'])          # turnover: menor é melhor

    def test_visuais_usam_a_cor(self):
        from tecnicas.c3 import pbir
        from tecnicas.arte.layout import posicionar
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
        from tecnicas.c3 import tmdl
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
        from tecnicas.c3 import pbir

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


class TestMemoryCard(unittest.TestCase):
    """Cartão do time local (sem GitHub); o Deidara usa a seção deidara/ com a estrutura padrão."""

    def setUp(self):
        from tecnicas import memory_card
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
        _calado(_aprovar_com_prototipo, ['aprovar', self.argila, '--por', 'Ana'])
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
        self.assertIn('Só painel aprovado entra no cartão', out)
        _calado(_aprovar_com_prototipo, ['aprovar', self.argila, '--por', 'Ana'])
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
        _calado(_aprovar_com_prototipo, ['aprovar', self.argila, '--por', 'Ana'])
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
        _calado(_aprovar_com_prototipo, ['aprovar', self.argila, '--por', 'Ana'])
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


class TestDesign(unittest.TestCase):
    def _com_barra(self, **extra):
        a = _base()
        a['medidas'].append({'nome': 'Turnover x Meta', 'tipo': 'svg_barra_meta', 'medida': 'Turnover',
                             'categoria': 'dEmpresa[Empresa]', 'descricao': 'Barra contra a meta.', **extra})
        a['paginas'][1]['visuais'].append({'tipo': 'tabela', 'campos': ['dEmpresa[Empresa]', 'Turnover', 'Turnover x Meta']})
        return a

    def test_barra_meta_segue_as_regras_de_svg(self):
        from tecnicas import sasori as dicionario
        from tecnicas.c3 import tmdl
        from kibaku_nendo.especificacao import medida
        m, p = _resolver(self._com_barra())
        self.assertEqual(p.erros, [])
        self.assertFalse([x for x in p.avisos if '[SVG]' in x], p.avisos)
        md = medida(m, 'Turnover x Meta')
        for trecho in ('"data:image/svg+xml;charset=utf-8,"', "viewBox='-2 -2 104 24'", "overflow='visible'",
                       'HASONEVALUE(dEmpresa[Empresa])', 'ALLSELECTED(dEmpresa[Empresa])', '"%23107C10"',
                       'FORMAT(_largura, "0.00", "en-US")', '<desc>'):
            self.assertIn(trecho, md['dax'])
        self.assertNotIn("='#", md['dax'])
        self.assertEqual(dicionario.desconhecidas(md['dax']), [])
        self.assertTrue(md['imagem'])
        t = next(t for t in m['tabelas'] if t['nome'] == md['tabela'])
        bloco = tmdl.tabela(m, t).split("measure 'Turnover x Meta'")[1].split('measure ')[0]
        self.assertIn('dataCategory: ImageUrl', bloco)
        self.assertNotIn('formatString', bloco)

    def test_barra_meta_pede_meta_e_tabela(self):
        _, p = _resolver(self._com_barra(medida='Desligamentos'))
        self.assertTrue(any('não tem meta' in e for e in p.erros), p.erros)
        a = self._com_barra()
        a['paginas'][1]['visuais'].append({'tipo': 'cartao', 'medida': 'Turnover x Meta'})
        _, p = _resolver(a)
        self.assertTrue(any('só aparece em tabela ou matriz' in e for e in p.erros), p.erros)

    def test_svg_escrito_a_mao_e_conferido(self):
        a = _base()
        dax = '"data:image/svg+xml;utf8<svg width=\'100%\'><circle fill=\'#FF0000\' r=\'4\'/></svg>"'
        a['medidas'].append({'nome': 'Bolinha', 'descricao': 'x', 'tabela': 'fDesligamento', 'dax': dax})
        _, p = _resolver(a)
        erros = '\n'.join(p.erros)
        for trecho in ('vírgula final', '"%23"', '"%25"'):
            self.assertIn(trecho, erros)
        avisos = '\n'.join(p.avisos)
        self.assertIn('sem viewBox', avisos)
        self.assertIn('HASONEVALUE', avisos)

    def test_contraste_do_tema(self):
        a = _base()
        a['tema'] = {'fundo': '#FFFFFF', 'texto': '#BBBBBB', 'cores': ['#118DFF', '#F2F2F2']}
        _, p = _resolver(a)
        avisos = '\n'.join(p.avisos)
        self.assertIn('[Design] o texto (#BBBBBB)', avisos)
        self.assertIn('#F2F2F2', avisos.split('cores de dados')[1])
        self.assertNotIn('#118DFF', avisos.split('cores de dados')[1])
        a['tema'] = {'fundo': '#FFFFFF', 'texto': 'preto'}
        _, p = _resolver(a)
        self.assertTrue(any('cor inválida' in e for e in p.erros), p.erros)

    def test_prototipo_desenha_a_barra_e_visuais_ensina(self):
        d = tempfile.mkdtemp(prefix='ddv')
        shutil.copytree(os.path.join(EXEMPLO, 'catalogos'), os.path.join(d, 'catalogos'))
        arq = os.path.join(d, 'argila.json')
        with open(arq, 'w', encoding='utf-8') as f:
            json.dump(self._com_barra(), f, ensure_ascii=False)
        self.assertEqual(_calado(deidara.main, ['prototipar', arq])[0], 0)
        with open(os.path.join(d, 'argila.prototipo.html'), encoding='utf-8') as f:
            self.assertIn('stroke-dasharray="3 2"', f.read())
        codigo, out = _calado(deidara.main, ['visuais', 'meta'])
        self.assertEqual(codigo, 0)
        self.assertIn('svg_barra_meta', out)
        self.assertEqual(_calado(deidara.main, ['visuais', 'zzzz'])[0], 1)
        shutil.rmtree(d, ignore_errors=True)


class TestModelos(unittest.TestCase):
    MODELOS = ('faixa-de-kpis', 'coluna-de-kpis', 'secoes-com-rolagem', 'trilho-escuro', 'kpis-clicaveis',
               'historia-longa', 'executivo', 'mapa-central', 'causa-raiz', 'tabela-lateral', 'equipes')

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='ddm')
        shutil.copytree(os.path.join(EXEMPLO, 'catalogos'), os.path.join(self.dir, 'catalogos'))
        self.argila = os.path.join(self.dir, 'argila.json')

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _gerar(self, modelo):
        a = _base()
        a['modelo'] = modelo
        with open(self.argila, 'w', encoding='utf-8') as f:
            json.dump(a, f, ensure_ascii=False)
        saida = os.path.join(self.dir, modelo)
        self.assertEqual(_calado(_aprovar_com_prototipo, ['aprovar', self.argila, '--por', 'Teste'])[0], 0)
        self.assertEqual(_calado(deidara.main, ['gerar', self.argila, '-o', saida])[0], 0)
        rep = os.path.join(saida, 'Quadro_e_Turnover.Report')
        paginas = {}
        for pid in json.load(open(os.path.join(rep, 'definition', 'pages', 'pages.json'), encoding='utf-8'))['pageOrder']:
            base = os.path.join(rep, 'definition', 'pages', pid)
            vis = []
            for v in os.listdir(os.path.join(base, 'visuals')):
                vis.append(json.load(open(os.path.join(base, 'visuals', v, 'visual.json'), encoding='utf-8')))
            paginas[pid] = (json.load(open(os.path.join(base, 'page.json'), encoding='utf-8')), vis)
        with open(os.path.join(self.dir, 'argila.prototipo.html'), encoding='utf-8') as f:
            html_ = f.read()
        return saida, rep, paginas, html_

    def test_cada_modelo_gera_fundo_navegacao_e_projeto_coerente(self):
        for modelo in self.MODELOS:
            with self.subTest(modelo=modelo):
                saida, rep, paginas, html_ = self._gerar(modelo)
                report = json.load(open(os.path.join(rep, 'definition', 'report.json'), encoding='utf-8'))
                imagens = {i['name'] for i in report['resourcePackages'][0]['items'] if i['type'] == 'Image'}
                for pid, (page, vis) in paginas.items():
                    self.assertEqual(page['width'], 1920)
                    fundo = page['objects']['background'][0]['properties']['image']['image']['url']['expr'][
                        'ResourcePackageItem']['ItemName']
                    self.assertIn(fundo, imagens)
                    self.assertTrue(os.path.exists(os.path.join(rep, 'StaticResources', 'RegisteredResources', fundo)))
                    for v in vis:
                        tipo = v['visual']['visualType']
                        if tipo == 'actionButton':
                            destino = v['visual']['visualContainerObjects']['visualLink'][0]['properties'][
                                'navigationSection']['expr']['Literal']['Value'].strip("'")
                            self.assertIn(destino, paginas)
                        else:
                            self.assertEqual(v['visual']['visualContainerObjects']['background'][0]['properties'][
                                'show']['expr']['Literal']['Value'], 'false')
                            p = v['position']
                            self.assertIn(f'left:{p["x"]:g}px;top:{p["y"]:g}px', html_.replace('.0px', 'px'))
                self.assertIn('class="pagina desenhada', html_)
                _, tabelas, colunas, medidas, erros = validar_pbip.validar_tmdl(saida)
                self.assertEqual(erros, [])
                self.assertEqual(validar_pbip.conferir(saida), [])

    def test_kpis_clicaveis_e_historia(self):
        _, _, paginas, html_ = self._gerar('kpis-clicaveis')
        ocultas = [p for p, _ in paginas.values() if p.get('visibility') == 'HiddenInViewMode']
        self.assertEqual(len(paginas), 2 + len(ocultas))
        self.assertEqual(len(ocultas), 4)                  # 3 cartões na Visão Geral e 3 no Turnover: 2 + 2 variações
        self.assertIn('class="ir"', html_)
        _, _, paginas, html_ = self._gerar('historia-longa')
        self.assertEqual(len(paginas), 1)
        page, _ = next(iter(paginas.values()))
        self.assertGreater(page['height'], 1080)
        self.assertIn('pagina desenhada escura', html_)

    def test_modelo_errado_e_tema_escuro(self):
        a = _base()
        a['modelo'] = 'faixa-kpis'
        _, p = _resolver(a)
        self.assertTrue(any('quis dizer "faixa-de-kpis"' in e for e in p.erros), p.erros)
        a['modelo'] = 'historia-longa'
        m, p = _resolver(a)
        self.assertEqual(m['tema']['fundo'], '#0F1420')
        self.assertFalse([x for x in p.avisos if '[Design]' in x], p.avisos)
        a['tema'] = {'fundo': '#101010', 'texto': '#FAFAFA'}
        m, _ = _resolver(a)
        self.assertEqual(m['tema']['fundo'], '#101010')
        self.assertEqual(_calado(deidara.main, ['modelos'])[0], 0)


class TestDemo(unittest.TestCase):
    def test_linhas_coerentes(self):
        from tecnicas.bunshin import demo
        m, _ = _resolver(_base())
        d = demo.linhas(m)
        self.assertEqual(len(d['dEmpresa']), 8)
        self.assertEqual(len(d['fMeta']), len(d['dEmpresa']))            # uma meta por empresa
        colab = {x['Matrícula']: x for x in d['dColaborador']}
        self.assertGreater(len(colab), 100)
        empresas = {x['Cód. Empresa'] for x in d['dEmpresa']}
        self.assertTrue(all(x['CODEMPRESA'] in empresas for x in d['dColaborador']))
        des = d['fDesligamento']
        self.assertEqual(len({x['MATRICULA'] for x in des}), len(des))   # um desligamento por pessoa
        import datetime
        for x in des:
            adm = colab[x['MATRICULA']]['Data de Admissão']
            self.assertGreater(x['Data do Desligamento'], adm)
            self.assertLessEqual(x['Data do Desligamento'], datetime.date.today())
        self.assertEqual(demo.linhas(m), d)                               # sempre os mesmos números

    def test_gerar_demo_embute_as_linhas(self):
        d = tempfile.mkdtemp(prefix='ddd')
        shutil.copytree(os.path.join(EXEMPLO, 'catalogos'), os.path.join(d, 'catalogos'))
        arq = os.path.join(d, 'argila.json')
        a = _base()
        a['modelo'] = 'faixa-de-kpis'
        with open(arq, 'w', encoding='utf-8') as f:
            json.dump(a, f, ensure_ascii=False)
        _calado(_aprovar_com_prototipo, ['aprovar', arq, '--por', 'Teste'])
        saida = os.path.join(d, 'o')
        codigo, out = _calado(deidara.main, ['gerar', arq, '-o', saida, '--demo'])
        self.assertEqual(codigo, 0, out)
        self.assertIn('DEMONSTRAÇÃO', out)
        tab = os.path.join(saida, 'Quadro_e_Turnover.SemanticModel', 'definition', 'tables')
        with open(os.path.join(tab, 'dEmpresa.tmdl'), encoding='utf-8') as f:
            t = f.read()
        self.assertIn('#table(', t)
        self.assertNotIn('Sql.Database', t)
        with open(os.path.join(tab, 'dCalendario.tmdl'), encoding='utf-8') as f:
            self.assertIn('List.Dates', f.read())                         # o calendário continua o mesmo
        with open(os.path.join(saida, 'LEIA-ME.md'), encoding='utf-8') as f:
            self.assertTrue(f.read().startswith('> **DEMONSTRAÇÃO.**'))
        _, tabelas, colunas, medidas, erros = validar_pbip.validar_tmdl(saida)
        self.assertEqual(erros, [])
        fundos = [x for x in os.listdir(os.path.join(saida, 'Quadro_e_Turnover.Report', 'StaticResources',
                                                     'RegisteredResources')) if x.startswith('fundo_')]
        with open(os.path.join(saida, 'Quadro_e_Turnover.Report', 'StaticResources', 'RegisteredResources', fundos[0]),
                  encoding='utf-8') as f:
            self.assertIn('Demonstração · dados fictícios', f.read())
        shutil.rmtree(d, ignore_errors=True)


class TestMigracao(unittest.TestCase):
    """O que veio do Power BI Design Files: visuais nativos, medidas de ranking e SVG, estilos, paletas e modelos."""

    def _argila(self, modelo='faixa-de-kpis'):
        a = _base()
        a['modelo'] = modelo
        a['medidas'] += [
            {'nome': 'Deslig. Ano Anterior', 'tipo': 'ano_anterior', 'base': 'Desligamentos', 'descricao': 'x'},
            {'nome': 'Posição', 'tipo': 'posicao', 'medida': 'Desligamentos', 'categoria': 'dCargo[Cargo]',
             'ordem': 'maior_primeiro', 'descricao': 'x'},
            {'nome': 'Pareto', 'tipo': 'pareto', 'medida': 'Desligamentos', 'categoria': 'dCargo[Cargo]', 'descricao': 'x'},
            {'nome': 'Extremos', 'tipo': 'melhores_piores', 'medida': 'Desligamentos', 'categoria': 'dMotivo[Motivo]', 'n': 2,
             'descricao': 'x'},
            {'nome': 'Selo', 'tipo': 'svg_posicao', 'medida': 'Desligamentos', 'categoria': 'dCargo[Cargo]', 'descricao': 'x'},
            {'nome': 'Seta', 'tipo': 'svg_seta', 'medida': 'Desligamentos', 'comparar': 'Deslig. Ano Anterior',
             'categoria': 'dCargo[Cargo]', 'descricao': 'x'},
            {'nome': 'Pílula', 'tipo': 'svg_pilula', 'medida': 'Turnover', 'categoria': 'dEmpresa[Empresa]', 'descricao': 'x'},
        ]
        a['paginas'][1]['visuais'] = [
            {'tipo': 'botoes', 'campo': 'dCalendario[Ano]'},
            {'tipo': 'cartoes', 'medidas': ['Desligamentos', 'Deslig. Ano Anterior']},
            {'tipo': 'decomposicao', 'medida': 'Desligamentos', 'cortes': ['dMotivo[Motivo]', 'dCargo[Cargo]']},
            {'tipo': 'dispersao', 'categoria': 'dEmpresa[Empresa]', 'x': 'Headcount', 'y': 'Turnover', 'tamanho': 'Desligamentos'},
            {'tipo': 'area', 'categoria': 'dCalendario[Mês/Ano]', 'valores': ['Desligamentos Acum. Ano']},
            {'tipo': 'tabela', 'campos': ['Selo', 'dCargo[Cargo]', 'Desligamentos', 'Posição', 'Pareto', 'Seta']},
            {'tipo': 'tabela', 'campos': ['dMotivo[Motivo]', 'Extremos']},
            {'tipo': 'tabela', 'campos': ['dEmpresa[Empresa]', 'Turnover', 'Pílula']},
        ]
        return a

    def test_medidas_de_ranking_e_svg(self):
        from tecnicas import sasori as dicionario
        from kibaku_nendo.especificacao import medida
        m, p = _resolver(self._argila())
        self.assertEqual(p.erros, [])
        self.assertFalse([x for x in p.avisos if '[SVG]' in x or 'não filtra parte' in x], p.avisos)
        for nome, trecho in (('Posição', 'RANKX(ALLSELECTED(dCargo[Cargo])'), ('Pareto', 'SUMX(FILTER(ALLSELECTED'),
                             ('Extremos', '_posicao <= 2 || _posicao > _linhas - 2'), ('Selo', 'data:image/svg+xml'),
                             ('Seta', "stroke-width='3'"), ('Pílula', 'Fora da meta')):
            md = medida(m, nome)
            self.assertIn(trecho, md['dax'], nome)
            self.assertEqual(dicionario.desconhecidas(md['dax']), [], nome)
        self.assertEqual(medida(m, 'Posição')['formato'], 'inteiro')
        self.assertEqual(medida(m, 'Pareto')['formato'], 'percentual')
        self.assertTrue(medida(m, 'Seta')['imagem'])
        from tecnicas.bunshin.simulacao import Simulador, categorias
        sim = Simulador(m)
        cargo = {'tipo': 'coluna', 'tabela': 'dCargo', 'nome': 'Cargo', 'familia': 'texto'}
        pos = sorted(sim.valor('Posição', [(cargo, r)]) for r in categorias(m, cargo))
        self.assertEqual(pos, list(range(1, len(pos) + 1)))
        self.assertAlmostEqual(max(sim.valor('Pareto', [(cargo, r)]) for r in categorias(m, cargo)), 1.0)
        motivo = {'tipo': 'coluna', 'tabela': 'dMotivo', 'nome': 'Motivo', 'familia': 'texto'}
        vals = [sim.valor('Extremos', [(motivo, r)]) for r in categorias(m, motivo)]
        self.assertEqual(sum(v is not None for v in vals), 4)          # 2 mais + 2 menos
        a = self._argila()
        next(x for x in a['medidas'] if x['nome'] == 'Seta')['comparar'] = 'Nada'
        _, p = _resolver(a)
        self.assertTrue(any('"comparar"' in e for e in p.erros), p.erros)

    def test_visuais_novos_no_pbip_com_estilo_e_paleta(self):
        d = tempfile.mkdtemp(prefix='ddg')
        shutil.copytree(os.path.join(EXEMPLO, 'catalogos'), os.path.join(d, 'catalogos'))
        arq = os.path.join(d, 'argila.json')
        a = self._argila()
        a['tema'] = {'paleta': 'contraste-executivo'}
        with open(arq, 'w', encoding='utf-8') as f:
            json.dump(a, f, ensure_ascii=False)
        self.assertEqual(_calado(_aprovar_com_prototipo, ['aprovar', arq, '--por', 'T'])[0], 0)
        saida = os.path.join(d, 'o')
        self.assertEqual(_calado(deidara.main, ['gerar', arq, '-o', saida])[0], 0)
        papeis, estilos = {}, {}
        for raiz, _, fs in os.walk(os.path.join(saida, 'Quadro_e_Turnover.Report')):
            if 'visual.json' in fs:
                v = json.load(open(os.path.join(raiz, 'visual.json'), encoding='utf-8'))['visual']
                papeis.setdefault(v['visualType'], set()).update((v.get('query') or {}).get('queryState', {}).keys())
                estilos.setdefault(v['visualType'], set()).update((v.get('objects') or {}).keys())
        self.assertEqual(papeis['advancedSlicerVisual'], {'Values'})
        self.assertEqual(papeis['cardVisual'], {'Data'})
        self.assertEqual(papeis['decompositionTreeVisual'], {'Analyze', 'ExplainBy'})
        self.assertEqual(papeis['scatterChart'], {'Category', 'X', 'Y', 'Size'})
        self.assertIn('areaChart', papeis)
        self.assertIn('columnHeaders', estilos['tableEx'])                 # formatação do dashboard de origem
        with open(os.path.join(saida, 'Quadro_e_Turnover.Report', 'StaticResources', 'RegisteredResources',
                               'Deidara.json'), encoding='utf-8') as f:
            self.assertEqual(json.load(f)['dataColors'][0], '#1800ED')    # a paleta
        self.assertEqual(validar_pbip.conferir(saida), [])
        with open(os.path.join(d, 'argila.prototipo.html'), encoding='utf-8') as f:
            html_ = f.read()
        for trecho in ('abrir por:', 'Fora da meta', 'Headcount →'):
            self.assertIn(trecho, html_)
        shutil.rmtree(d, ignore_errors=True)

    def _tecnicas(self):
        a = _base()
        _md(a, 'Remuneração Média').update({'meta': 9000, 'polaridade': 'menor_melhor'})
        a['medidas'] += [
            {'nome': 'Deslig. Ano Anterior', 'tipo': 'ano_anterior', 'base': 'Desligamentos', 'descricao': 'x'},
            {'nome': 'Radar', 'tipo': 'svg_radar', 'medidas': ['Headcount', 'Remuneração Média', 'Desligamentos'],
             'categoria': 'dCargo[Cargo]', 'descricao': 'x'},
            {'nome': 'Bolha', 'tipo': 'svg_bolha', 'medida': 'Remuneração Total', 'categoria': 'dCargo[Cargo]',
             'colunas': 'dEmpresa[Empresa]', 'descricao': 'x'},
            {'nome': 'Desvio', 'tipo': 'svg_variacao', 'medida': 'Desligamentos', 'comparar': 'Deslig. Ano Anterior',
             'categoria': 'dCargo[Cargo]', 'descricao': 'x'},
            {'nome': 'Top 3', 'tipo': 'lista_top', 'medida': 'Remuneração Total', 'categoria': 'dCargo[Cargo]', 'n': 3,
             'descricao': 'x'},
        ]
        a['paginas'][1]['visuais'] = [
            {'tipo': 'cartao', 'medida': 'Top 3'},
            {'tipo': 'colunas', 'categoria': 'dEmpresa[Empresa]', 'valores': ['Remuneração Média'], 'meta': True},
            {'tipo': 'tabela', 'campos': ['dCargo[Cargo]', 'Radar', 'Desligamentos', 'Desvio']},
            {'tipo': 'matriz', 'linhas': ['dCargo[Cargo]'], 'colunas': ['dEmpresa[Empresa]'], 'valores': ['Bolha']},
        ]
        return a

    def test_radar_bolha_desvio_e_lista(self):
        from tecnicas import sasori as dicionario
        from kibaku_nendo.especificacao import medida
        m, p = _resolver(self._tecnicas())
        self.assertEqual(p.erros, [])
        self.assertFalse([x for x in p.avisos if '[SVG]' in x], p.avisos)
        for nome, trecho in (('Radar', 'MAXX(ALLSELECTED(dCargo[Cargo]), [Desligamentos])'),
                             ('Bolha', 'CROSSJOIN(ALLSELECTED(dCargo[Cargo]), ALLSELECTED(dEmpresa[Empresa]))'),
                             ('Desvio', 'ABS([Desligamentos] - [Deslig. Ano Anterior])'),
                             ('Top 3', 'TOPN(3, ALLSELECTED(dCargo[Cargo]), [Remuneração Total], DESC)')):
            md = medida(m, nome)
            self.assertIn(trecho, md['dax'], nome)
            self.assertEqual(dicionario.desconhecidas(md['dax']), [], nome)
        self.assertTrue(medida(m, 'Radar')['imagem'])
        self.assertIsNone(medida(m, 'Top 3')['formato'])
        from tecnicas.bunshin.simulacao import Simulador
        self.assertEqual(len(Simulador(m).lista(medida(m, 'Top 3'))), 3)
        a = self._tecnicas()
        _md(a, 'Radar')['medidas'] = ['Headcount', 'Desligamentos']
        _md(a, 'Bolha')['colunas'] = 'dEmpresa[Nada]'
        _, p = _resolver(a)
        self.assertTrue(any('de 3 a 8' in e for e in p.erros), p.erros)
        self.assertTrue(any('"colunas"' in e for e in p.erros), p.erros)

    def test_linha_de_meta_so_com_meta_fixa(self):
        from tecnicas.c3 import pbir
        m, p = _resolver(self._tecnicas())
        v = m['paginas'][1]['visuais'][1]
        ref = pbir.visual(m, v, {'x': 0, 'y': 0, 'w': 400, 'h': 300}, 'x', 0)['visual']['objects']['y1AxisReferenceLine'][0]
        self.assertEqual(ref['properties']['value']['expr']['Literal']['Value'], '9000.0D')
        a = self._tecnicas()
        a['paginas'][1]['visuais'][1] = {'tipo': 'barras', 'categoria': 'dEmpresa[Empresa]', 'valores': ['Turnover'],
                                         'meta': 'Meta de Turnover'}
        m, p = _resolver(a)
        self.assertTrue(any('meta fixa' in x for x in p.avisos), p.avisos)
        v = m['paginas'][1]['visuais'][1]
        self.assertNotIn('y1AxisReferenceLine', pbir.visual(m, v, {'x': 0, 'y': 0, 'w': 400, 'h': 300}, 'x', 0)['visual']
                         .get('objects') or {})
        a['paginas'][1]['visuais'][1]['meta'] = True
        _md(a, 'Turnover').pop('meta', None)
        _, p = _resolver(a)
        self.assertTrue(any('"meta": true' in e for e in p.erros), p.erros)

    def test_tecnicas_novas_no_pbip_e_no_prototipo(self):
        d = tempfile.mkdtemp(prefix='ddt')
        shutil.copytree(os.path.join(EXEMPLO, 'catalogos'), os.path.join(d, 'catalogos'))
        arq = os.path.join(d, 'argila.json')
        with open(arq, 'w', encoding='utf-8') as f:
            json.dump(self._tecnicas(), f, ensure_ascii=False)
        self.assertEqual(_calado(_aprovar_com_prototipo, ['aprovar', arq, '--por', 'T'])[0], 0)
        saida = os.path.join(d, 'o')
        self.assertEqual(_calado(deidara.main, ['gerar', arq, '-o', saida, '--demo'])[0], 0)
        self.assertEqual(validar_pbip.conferir(saida), [])
        grades = []
        for raiz, _, fs in os.walk(os.path.join(saida, 'Quadro_e_Turnover.Report')):
            if 'visual.json' in fs:
                v = json.load(open(os.path.join(raiz, 'visual.json'), encoding='utf-8'))['visual']
                grades += [g['properties']['imageHeight']['expr']['Literal']['Value'] for g in (v.get('objects') or {}).get('grid', [])]
        self.assertIn('64D', grades)                   # o radar pede a linha alta
        with open(os.path.join(d, 'argila.prototipo.html'), encoding='utf-8') as f:
            html_ = f.read()
        self.assertIn('stroke-dasharray="6 4"', html_)                     # a linha de meta
        self.assertIn('fill-opacity=".35"', html_)                         # o radar
        self.assertIn('1. Cargo', html_)                                   # a lista
        shutil.rmtree(d, ignore_errors=True)

    def test_mapa_com_pizza_usa_series(self):
        from tecnicas.c3 import pbir
        a = _base()
        a['paginas'][1]['visuais'] = [{'tipo': 'mapa', 'local': 'dEmpresa[Empresa]', 'valores': ['Headcount'],
                                       'legenda': 'dCargo[Cargo]'}]
        m, p = _resolver(a)
        self.assertEqual(p.erros, [])
        v = m['paginas'][1]['visuais'][0]
        q = pbir.visual(m, v, {'x': 0, 'y': 0, 'w': 400, 'h': 300}, 'x', 0)['visual']['query']['queryState']
        self.assertEqual(set(q), {'Category', 'Series', 'Size'})
        from tecnicas.c1 import prototipo
        self.assertIn('<path d="M', prototipo._mapa(prototipo.Simulador(m), v, 400, 300, ['#118DFF', '#E66C37']))

    def test_padrao_continua_sem_estilo(self):
        from tecnicas.c3 import pbir
        m, _ = _resolver(_base())
        v = next(v for pg in m['paginas'] for v in pg['visuais'] if v['tipo'] == 'tabela')
        self.assertNotIn('columnHeaders', (pbir.visual(m, v, {'x': 0, 'y': 0, 'w': 10, 'h': 10}, 'x', 0)['visual']
                                           .get('objects') or {}))


class TestTecnicasCompletas(unittest.TestCase):
    """As técnicas que pedem tabela auxiliar, imagem por medida, página de ajuda ou visual do AppSource."""

    def _argila(self):
        a = _base()
        _md(a, 'Remuneração Média').update({'meta': 9000, 'polaridade': 'menor_melhor'})
        a['medidas'] += [
            {'nome': 'Deslig. Ano Anterior', 'tipo': 'ano_anterior', 'base': 'Desligamentos', 'descricao': 'x'},
            {'nome': 'Escolhido', 'tipo': 'escolha', 'opcoes': {'Pessoas': 'Headcount', 'Custo': 'Remuneração Total'},
             'descricao': 'x'},
            {'nome': 'Chave', 'tipo': 'alternar', 'rotulo': 'Ver custo', 'desligado': 'Headcount',
             'ligado': 'Remuneração Total', 'descricao': 'x'},
            {'nome': 'Destaque', 'tipo': 'cor_destaque', 'categoria': 'dCargo[Cargo]', 'descricao': 'x'},
            {'nome': 'Aviso', 'tipo': 'aviso', 'medida': 'Remuneração Média', 'categoria': 'dCargo[Cargo]', 'descricao': 'x'},
            {'nome': 'Iniciais', 'tipo': 'svg_iniciais', 'categoria': 'dEmpresa[Empresa]', 'descricao': 'x'},
            {'nome': 'Pontos', 'tipo': 'svg_dispersao', 'categoria': 'dCargo[Cargo]', 'x': 'Headcount',
             'y': 'Remuneração Média', 'descricao': 'x'},
            {'nome': 'Faixa', 'tipo': 'html_kpis', 'medidas': ['Headcount', 'Remuneração Média'], 'descricao': 'x'},
        ]
        a['paginas'][1]['ajuda'] = True
        a['paginas'][1]['visuais'] = [
            {'tipo': 'abas', 'medida': 'Escolhido'},
            {'tipo': 'alternar', 'medida': 'Chave'},
            {'tipo': 'aviso', 'medida': 'Aviso'},
            {'tipo': 'botoes', 'campo': 'Destacar Cargo[Cargo]', 'icone': True},
            {'tipo': 'botoes', 'campo': 'dEmpresa[Empresa]', 'imagem': 'Iniciais'},
            {'tipo': 'barras', 'categoria': 'dCargo[Cargo]', 'valores': ['Remuneração Total'], 'cor': 'Destaque'},
            {'tipo': 'colunas', 'categoria': 'dEmpresa[Empresa]', 'valores': ['Escolhido']},
            {'tipo': 'setas', 'categoria': 'dEmpresa[Empresa]', 'medida': 'Desligamentos', 'comparar': 'Deslig. Ano Anterior'},
            {'tipo': 'skyline', 'categoria': 'dCalendario[Mês/Ano]', 'legenda': 'dMotivo[Motivo]', 'valores': ['Desligamentos']},
            {'tipo': 'imagem', 'medida': 'Pontos'},
            {'tipo': 'html', 'medida': 'Faixa'},
            {'tipo': 'vegalite', 'categoria': 'dCargo[Cargo]', 'valores': ['Remuneração Total']},
        ]
        return a

    def test_medidas_e_tabelas_auxiliares(self):
        from tecnicas import sasori as dicionario
        from kibaku_nendo.especificacao import medida, tabela_do_modelo
        m, p = _resolver(self._argila())
        self.assertEqual(p.erros, [])
        self.assertFalse([x for x in p.avisos if '[SVG]' in x or 'não chega em' in x or 'fica parado' in x], p.avisos)
        self.assertEqual(sum('AppSource' in x for x in p.avisos), 2)                  # html e vegalite
        for nome, trecho in (('Escolhido', "SELECTEDVALUE('Escolhido (opções)'[Opção], \"Pessoas\")"),
                             ('Chave', "ISFILTERED('Chave (chave)'[Estado])"),
                             ('Destaque', "VALUES('Destacar Cargo'[Cargo])"),
                             ('Aviso', 'fora da meta de Remuneração Média'),
                             ('Iniciais', 'SEARCH(" ", _nome, 1, 0)'),
                             ('Pontos', 'CONCATENATEX('), ('Faixa', "class='kpi'")):
            md = medida(m, nome)
            self.assertIn(trecho, md['dax'], nome)
            self.assertEqual(dicionario.desconhecidas(md['dax']), [], nome)
        self.assertIn('SWITCH(SELECTEDVALUE', medida(m, 'Escolhido')['formato_dinamico'])  # inteiro e moeda
        for t in ('Escolhido (opções)', 'Chave (chave)', 'Destacar Cargo'):
            self.assertTrue(tabela_do_modelo(m, t)['auxiliar'], t)
        self.assertTrue(medida(m, 'Iniciais (ligado)') and medida(m, 'Chave · chave ligada') and medida(m, 'Aviso · fundo'))
        from tecnicas.bunshin.simulacao import Simulador, categorias
        sim = Simulador(m)
        self.assertEqual(categorias(m, {'tabela': 'Escolhido (opções)', 'nome': 'Opção'}), ['Pessoas', 'Custo'])
        self.assertEqual(sim.valor('Escolhido'), sim.valor('Headcount'))
        a = self._argila()
        _md(a, 'Escolhido')['opcoes'] = ['Headcount']
        a['paginas'][1]['visuais'][0] = {'tipo': 'abas', 'medida': 'Headcount'}
        _, p = _resolver(a)
        self.assertTrue(any('"opcoes"' in e for e in p.erros), p.erros)

    def test_pbip_com_tudo(self):
        d = tempfile.mkdtemp(prefix='ddc')
        shutil.copytree(os.path.join(EXEMPLO, 'catalogos'), os.path.join(d, 'catalogos'))
        arq = os.path.join(d, 'argila.json')
        with open(arq, 'w', encoding='utf-8') as f:
            json.dump(self._argila(), f, ensure_ascii=False)
        self.assertEqual(_calado(_aprovar_com_prototipo, ['aprovar', arq, '--por', 'T'])[0], 0)
        saida = os.path.join(d, 'o')
        self.assertEqual(_calado(deidara.main, ['gerar', arq, '-o', saida, '--demo'])[0], 0)
        self.assertEqual(validar_pbip.conferir(saida), [])
        rep = os.path.join(saida, 'Quadro_e_Turnover.Report', 'definition')
        sem = os.path.join(saida, 'Quadro_e_Turnover.SemanticModel', 'definition')
        with open(os.path.join(sem, 'database.tmdl'), encoding='utf-8') as f:
            self.assertIn('1601', f.read())                                         # formato dinâmico
        with open(os.path.join(sem, 'tables', 'Destacar Cargo.tmdl'), encoding='utf-8') as f:
            self.assertIn('= calculated', f.read())
        with open(os.path.join(rep, 'report.json'), encoding='utf-8') as f:
            self.assertEqual(len(json.load(f)['publicCustomVisuals']), 2)
        objetos, paginas = {}, []
        for raiz, _, fs in os.walk(rep):
            if 'page.json' in fs:
                with open(os.path.join(raiz, 'page.json'), encoding='utf-8') as f:
                    paginas.append(json.load(f)['displayName'])
            if 'visual.json' in fs:
                with open(os.path.join(raiz, 'visual.json'), encoding='utf-8') as f:
                    v = json.load(f)['visual']
                objetos.setdefault(v['visualType'], set()).update((v.get('objects') or {}).keys())
        self.assertIn('Ajuda · Turnover', ' '.join(paginas))
        self.assertTrue({'accentBar', 'selectionIcon', 'image'} <= objetos['advancedSlicerVisual'])
        self.assertIn('error', objetos['clusteredBarChart'])                       # setas
        self.assertIn('layout', objetos['columnChart'])                            # skyline
        self.assertIn('vega', objetos['deneb7E15AEF80B9E4D4F8E12924291ECE89A'])
        self.assertIn('textbox', objetos)                                          # notas da ajuda
        with open(os.path.join(d, 'argila.prototipo.html'), encoding='utf-8') as f:
            html_ = f.read()
        for trecho in ('class="ajuda"', 'nota-ajuda', 'fora da meta', '✓ Tudo'):
            self.assertIn(trecho, html_)
        shutil.rmtree(d, ignore_errors=True)


class TestCausaRaiz(unittest.TestCase):
    """Os três visuais do Root Cause Analysis: espinha de peixe, jitter plot e ranking de impacto."""

    def _argila(self):
        a = _base()
        a['medidas'] += [
            {'nome': 'Deslig. Ano Anterior', 'tipo': 'ano_anterior', 'base': 'Desligamentos', 'descricao': 'x'},
            {'nome': 'Espinha', 'tipo': 'svg_espinha', 'medida': 'Desligamentos',
             'cortes': ['dEmpresa[Empresa]', 'dCargo[Cargo]', 'dMotivo[Motivo]'], 'n': 3, 'descricao': 'x'},
            {'nome': 'X Desligamentos', 'tipo': 'jitter', 'medida': 'Desligamentos', 'categoria': 'dCargo[Cargo]',
             'descricao': 'x'},
            {'nome': 'Impacto', 'tipo': 'impacto', 'medida': 'Desligamentos', 'comparar': 'Deslig. Ano Anterior',
             'categoria': 'dCargo[Cargo]', 'descricao': 'x'},
        ]
        a['paginas'][1]['visuais'] = [
            {'tipo': 'imagem', 'medida': 'Espinha'},
            {'tipo': 'dispersao', 'categoria': 'dCargo[Cargo]', 'x': 'X Desligamentos', 'y': 'Desligamentos'},
            {'tipo': 'barras', 'categoria': 'dCargo[Cargo]', 'valores': ['Impacto']},
            {'tipo': 'tabela', 'campos': ['dCargo[Cargo]', 'Impacto']},
        ]
        return a

    def test_medidas(self):
        from tecnicas import sasori as dicionario
        from kibaku_nendo.especificacao import medida
        m, p = _resolver(self._argila())
        self.assertEqual(p.erros, [])
        self.assertFalse([x for x in p.avisos if '[SVG]' in x or 'foi feita para as linhas' in x], p.avisos)
        for nome, trecho in (('Espinha', 'AVERAGEX(ALLSELECTED(dMotivo[Motivo]), [Desligamentos])'),
                             ('Espinha', '[Desligamentos] > _media1), [Desligamentos], DESC)'),    # menor_melhor: pior é maior
                             ('X Desligamentos', 'MOD(_posicao * 37, 101) / 100'),
                             ('Impacto', '_agora - _antes')):
            md = medida(m, nome)
            self.assertIn(trecho, md['dax'], nome)
            self.assertEqual(dicionario.desconhecidas(md['dax']), [], nome)
        self.assertTrue(medida(m, 'Espinha')['imagem'])
        self.assertEqual(medida(m, 'Impacto')['cor_medida'], 'Cor Impacto')
        self.assertIn('_impacto <= 0', medida(m, 'Cor Impacto')['dax'])                 # menos desligamento é bom
        from tecnicas.bunshin.simulacao import Simulador
        sim = Simulador(m)
        cargo = {'tabela': 'dCargo', 'nome': 'Cargo', 'tipo': 'coluna'}
        r = 'Cargo A'
        self.assertAlmostEqual(sim.valor('Impacto', [(cargo, r)]),
                               sim.valor('Desligamentos', [(cargo, r)]) - sim.valor('Deslig. Ano Anterior', [(cargo, r)]))
        self.assertTrue(0 <= sim.valor('X Desligamentos', [(cargo, r)]) <= 1)
        a = self._argila()
        _md(a, 'Espinha')['cortes'] = ['dCargo[Cargo]']
        _md(a, 'Impacto').pop('comparar')
        _, p = _resolver(a)
        self.assertTrue(any('de 2 a 6 colunas' in e for e in p.erros), p.erros)
        self.assertTrue(any('"comparar"' in e for e in p.erros), p.erros)
        a = self._argila()
        _md(a, 'Espinha')['n'] = 9
        _, p = _resolver(a)
        self.assertTrue(any('de 1 a 5' in e for e in p.erros), p.erros)

    def test_pbip_e_prototipo(self):
        d = tempfile.mkdtemp(prefix='ddr')
        shutil.copytree(os.path.join(EXEMPLO, 'catalogos'), os.path.join(d, 'catalogos'))
        arq = os.path.join(d, 'argila.json')
        with open(arq, 'w', encoding='utf-8') as f:
            json.dump(self._argila(), f, ensure_ascii=False)
        self.assertEqual(_calado(_aprovar_com_prototipo, ['aprovar', arq, '--por', 'T'])[0], 0)
        saida = os.path.join(d, 'o')
        self.assertEqual(_calado(deidara.main, ['gerar', arq, '-o', saida, '--demo'])[0], 0)
        self.assertEqual(validar_pbip.conferir(saida), [])
        objetos = {}
        for raiz, _, fs in os.walk(os.path.join(saida, 'Quadro_e_Turnover.Report')):
            if 'visual.json' in fs:
                with open(os.path.join(raiz, 'visual.json'), encoding='utf-8') as f:
                    v = json.load(f)['visual']
                objetos.setdefault(v['visualType'], {}).update(v.get('objects') or {})
        self.assertFalse(objetos['scatterChart']['categoryAxis'][0]['properties']['show']['expr']['Literal']['Value']
                         == 'true')                                                 # jitter: X escondido
        self.assertIn("'Cor Impacto'", json.dumps(objetos['clusteredBarChart']['dataPoint'], ensure_ascii=False)
                      .replace('"Property": "Cor Impacto"', "'Cor Impacto'"))
        with open(os.path.join(d, 'argila.prototipo.html'), encoding='utf-8') as f:
            html_ = f.read()
        self.assertIn('stroke-width="4"', html_)                                    # a linha central da espinha
        self.assertIn('#D13438', html_)                                             # impacto que atrapalhou
        shutil.rmtree(d, ignore_errors=True)


class TestSintaxeDax(unittest.TestCase):
    def test_pega_o_que_o_power_bi_recusaria(self):
        from kibaku_nendo.especificacao import sintaxe_dax
        self.assertEqual(sintaxe_dax('DIVIDE([A], [B])'), [])
        self.assertEqual(sintaxe_dax('CALCULATE([A], \'Tab (x)\'[Col] = "a;b)")'), [])     # texto e nome não contam
        self.assertEqual(sintaxe_dax('VAR _x = 1 -- comentário (\nRETURN _x'), [])
        self.assertTrue(any('fechar' in x for x in sintaxe_dax('DIVIDE([A], [B]')))
        self.assertTrue(any('";"' in x for x in sintaxe_dax('DIVIDE([A]; [B])')))
        self.assertTrue(any('aspas' in x for x in sintaxe_dax('"abc')))
        self.assertTrue(any('operador' in x for x in sintaxe_dax('[A] +')))

    def test_todo_dax_que_o_deidara_escreve_passa(self):
        from kibaku_nendo.especificacao import sintaxe_dax
        for argila in (_base(), TestTecnicasCompletas()._argila(), TestCausaRaiz()._argila()):
            m, _ = _resolver(argila)
            for md in m['medidas']:
                if md.get('dax') and md.get('tipo') not in ('html_kpis', 'html_tour'):
                    self.assertEqual(sintaxe_dax(md['dax']), [], md['nome'])

    def test_vira_erro_no_validar(self):
        a = _base()
        a['medidas'].append({'nome': 'Quebrada', 'dax': 'DIVIDE([Desligamentos]; [Headcount]', 'descricao': 'x'})
        _, p = _resolver(a)
        self.assertTrue(any('DAX mal escrito' in e for e in p.erros), p.erros)


class TestNumeroDistorcido(unittest.TestCase):
    """Corte que filtra só parte da conta: o esboço não cria, e o aceite não deixa passar em bloco."""

    def test_esboco_sai_sem_corte_que_distorce(self):
        from kibaku_nendo.especificacao import distorcoes
        from tecnicas import te_no_kuchi
        argila, notas = te_no_kuchi.esbocar(CATALOGOS, 'turnover e desligamentos por motivo e cargo, com meta de '
                                                       'turnover por empresa')
        argila['fontes'] = {'erp': {'catalogo': 'catalogos/erp.json'}, 'metas': {'catalogo': 'catalogos/metas.json'}}
        _, p = _resolver(argila)
        self.assertEqual(distorcoes(p.avisos), [])
        self.assertTrue(any('fora do esboço' in n or 'em vez de' in n for n in notas), notas)

    def test_aprovar_recusa_distorcao_sem_motivo(self):
        d = tempfile.mkdtemp(prefix='ddd')
        shutil.copytree(os.path.join(EXEMPLO, 'catalogos'), os.path.join(d, 'catalogos'))
        a = _base()
        a['paginas'][1]['visuais'].append({'tipo': 'barras', 'categoria': 'dMotivo[Motivo]', 'valores': ['Turnover']})
        arq = os.path.join(d, 'argila.json')
        with open(arq, 'w', encoding='utf-8') as f:
            json.dump(a, f, ensure_ascii=False)
        _calado(deidara.main, ['prototipar', arq])
        codigo, out = _calado(deidara.main, ['aprovar', arq, '--por', 'T'])
        self.assertEqual(codigo, 1)
        self.assertIn('distorcidos', out)
        codigo, _ = _calado(deidara.main, ['aprovar', arq, '--por', 'T', '--aceito-distorcao', 'o gestor quer ver assim'])
        self.assertEqual(codigo, 0)
        with open(os.path.join(d, 'argila.aprovacao.json'), encoding='utf-8') as f:
            self.assertEqual(json.load(f)['distorcao_aceita']['motivo'], 'o gestor quer ver assim')
        shutil.rmtree(d, ignore_errors=True)


class TestEmpacotar(unittest.TestCase):
    def test_zip_da_skill_sem_zip_dentro_nem_arquivo_local(self):
        import zipfile
        d = tempfile.mkdtemp(prefix='ddz')
        destino = os.path.join(d, 'deidara-skill.zip')
        with redirect_stdout(io.StringIO()):
            empacotar.main(['-o', destino])
        nomes = zipfile.ZipFile(destino).namelist()
        self.assertIn('deidara/SKILL.md', nomes)
        self.assertIn('deidara/deidara.py', nomes)
        self.assertFalse([n for n in nomes if n.endswith(('.zip', '.pyc', '.aprovacao.json'))
                          or '/assets/' in n or '/.git/' in n or '__pycache__' in n or '/schemas/' in n], nomes)
        shutil.rmtree(d, ignore_errors=True)

    def test_arquivo_fora_do_git_nao_entra(self):
        solto = os.path.join(RAIZ, 'cliente_real_teste.json')
        with open(solto, 'w', encoding='utf-8') as f:
            f.write('{}')
        try:
            self.assertNotIn('cliente_real_teste.json', empacotar.arquivos_da_skill())
        finally:
            os.remove(solto)


class TestExperiencia(unittest.TestCase):
    def test_sem_argumentos_mostra_o_roteiro(self):
        codigo, out = _calado(deidara.main, [])
        self.assertEqual(codigo, 0)
        self.assertIn('Por onde começar', out)

    def test_erro_em_cascata_vira_uma_causa_so(self):
        a = _base()
        a['tabelas'][1]['colunas'][1]['coluna'] = 'DESCRICAO_CARGO'
        _, p = _resolver(a)
        self.assertEqual(len(p.erros), 1, p.erros)
        self.assertEqual(len(p.consequencias[p.erros[0]]), 5)

    def test_relatorio_tem_proximo_passo(self):
        from kibaku_nendo import relato
        m, p = _resolver(_base())
        texto = relato.validacao(m, p, 'x.json')
        self.assertIn('Próximo passo', texto)
        self.assertIn('[Ligações]', texto)


class TestComeco(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='ddn')
        self.pasta = os.path.join(self.dir, 'painel')

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_novo_cria_pasta_com_receitas_e_roteiro(self):
        codigo, _ = _calado(deidara.main, ['novo', self.pasta, '--projeto', 'Turnover'])
        self.assertEqual(codigo, 0)
        for x in ('ROTEIRO.md', 'receitas/receita_sql.sql', 'receitas/receita_dax.dax', 'receitas/receita_m.pq',
                  'catalogos', 'colado/m'):
            self.assertTrue(os.path.exists(os.path.join(self.pasta, x)), x)
        self.assertEqual(_calado(deidara.main, ['novo', self.pasta])[0], 1)           # não sobrescreve

    def _esboco(self):
        _calado(deidara.main, ['novo', self.pasta])
        for f in ('erp.json', 'metas.json'):
            shutil.copy(os.path.join(EXEMPLO, 'catalogos', f), os.path.join(self.pasta, 'catalogos'))
        codigo, out = _calado(deidara.main, ['esbocar', self.pasta, '--pedido', 'desligamentos por motivo e cargo com a meta por empresa'])
        self.assertEqual(codigo, 0, out)
        arq = os.path.join(self.pasta, 'argila.json')
        with open(arq, encoding='utf-8') as f:
            return arq, json.load(f)

    def test_esboco_classifica_e_marca_o_que_e_de_gente(self):
        arq, a = self._esboco()
        tipos = {t['origem']: t['tipo'] for t in a['tabelas']}
        self.assertEqual(tipos['F_DESLIGAMENTO'], 'fato')
        self.assertEqual(tipos['F_FUNCIONARIO'], 'dimensao')
        self.assertEqual(tipos['F_MOTIVO_DESLIGAMENTO'], 'dimensao')
        decl = [r for r in a['relacionamentos'] if 'declarada' in r]
        self.assertTrue(decl and all(r['declarada']['por'] == 'A CONFIRMAR' for r in decl))
        cadeia = {'Desligamentos', 'Headcount', 'HC Médio', 'Turnover'}         # o padrão turnover traz a definição
        self.assertTrue(cadeia <= {m['nome'] for m in a['medidas']})
        self.assertTrue(all(m['descricao'].startswith('A DEFINIR') for m in a['medidas']
                            if m['nome'] not in cadeia and not m.get('meta') and m['nome'] not in
                            {x.get('meta') for x in a['medidas']}))
        self.assertTrue(a['descricao'].startswith('A DEFINIR'))                   # sem briefing, o painel fica a definir
        self.assertEqual(a['modelo'], 'faixa-de-kpis')
        meta = next(m for m in a['medidas'] if 'Meta' in m['nome'])
        self.assertEqual((meta['agregacao'], meta['formato']), ('media', 'percentual'))
        self.assertTrue(meta['nome'].startswith('Meta de '), meta['nome'])

    def test_esboco_valida_e_so_bloqueia_o_que_precisa_de_gente(self):
        arq, a = self._esboco()
        codigo, out = _calado(deidara.main, ['validar', arq])
        self.assertEqual(codigo, 1)
        self.assertIn('deidara.py confirmar', out)
        for r in a['relacionamentos']:
            if 'declarada' in r:
                lig = f'{r["de"]}->{r["para"]}'
                self.assertEqual(_calado(deidara.main, ['confirmar', arq, '--ligacao', lig, '--por', 'Ana (RH)'])[0], 0)
        self.assertEqual(_calado(deidara.main, ['confirmar', arq, '--ligacao', 'X->Y', '--por', 'Ana'])[0], 1)
        codigo, out = _calado(deidara.main, ['validar', arq])
        self.assertEqual(codigo, 0, out)
        self.assertEqual(_calado(deidara.main, ['prototipar', arq])[0], 0)
        codigo, out = _calado(_aprovar_com_prototipo, ['aprovar', arq, '--por', 'Gestor'])
        self.assertEqual(codigo, 1)
        self.assertIn('sem definição', out)

    def test_esboco_nao_sobrescreve(self):
        self._esboco()
        codigo, out = _calado(deidara.main, ['esbocar', self.pasta, '--pedido', 'x'])
        self.assertEqual(codigo, 1)
        self.assertIn('não sobrescreve', out)

    def test_situacao_aponta_o_proximo_passo(self):
        arq, _ = self._esboco()
        codigo, out = _calado(deidara.main, ['situacao', arq])
        self.assertEqual(codigo, 0)
        self.assertIn('Próximo passo: deidara.py prototipar', out)                 # ligação a confirmar não segura o protótipo


class TestPrototipoParaAprovar(unittest.TestCase):
    def setUp(self):
        from tecnicas.c1 import prototipo
        a = _base()
        _md(a, 'Turnover')['meta'] = 0.05
        self.m, self.p = _resolver(a)
        self.html = prototipo.gerar_html(self.m, self.p, '0.0')

    def test_cada_visual_tem_o_que_e(self):
        n = sum(len(pg['visuais']) for pg in self.m['paginas'])
        self.assertEqual(self.html.count('class="info"'), n)
        self.assertIn('Desligamentos do período divididos pelo headcount médio do período', self.html)

    def test_aba_para_aprovar_com_checklist_e_comentarios(self):
        self.assertIn('id="aprovar"', self.html)
        self.assertIn('Copiar resumo do aceite', self.html)
        self.assertEqual(self.html.count('data-guardar="c:'), len(self.m['paginas']))

    def test_status_nao_depende_so_da_cor(self):
        self.assertTrue('na meta' in self.html or 'fora da meta' in self.html)

    def test_versao_do_painel_no_cabecalho(self):
        self.assertIn('painel v1.1', self.html)

    def test_javascript_sem_quebra_de_linha_em_string(self):
        js = self.html.split('<script>')[1].split('</script>')[0]
        # a quebra de linha do resumo vem de String.fromCharCode(10): nenhuma string do JS pode quebrar
        self.assertIn('const NL=String.fromCharCode(10)', js)
        self.assertNotIn("b.versao+')\n", js)

    def test_resumo_traz_codigo_decisao_e_aprovador(self):
        from tecnicas.c1 import prototipo
        self.assertIn(f'data-codigo="{prototipo.codigo_do_prototipo(self.m)}"', self.html)
        self.assertIn('name="decisao" value="Aprovo"', self.html)
        self.assertIn('id="aprovador"', self.html)

    def test_pontos_de_atencao_em_linguagem_de_negocio(self):
        secao = self.html.split('id="aprovar"')[1].split('</section>')[0]
        self.assertIn('vêm de fontes diferentes', secao)
        self.assertIn('mostra o cadastro de hoje', secao)
        self.assertNotIn('relacionamentos[', secao)          # o texto técnico fica na aba do analista
        self.assertIn('Pendências do analista', self.html)

    def test_abas_acessiveis(self):
        self.assertIn('aria-controls="aprovar"', self.html)
        self.assertIn('role="tabpanel" tabindex="0" id="aprovar" aria-labelledby="aba-aprovar"', self.html)


def _catalogo_grande(n=600, colunas=15):
    """ERP sintético grande, como sairia da receita SQL."""
    import random
    r = random.Random(7)
    dom = ['empresa', 'filial', 'cargo', 'setor', 'cliente', 'produto', 'pedido', 'nota', 'titulo', 'conta']
    linhas = []
    for i in range(n):
        t = f'T{i:05d}'
        linhas.append(_linha('coluna', t, 'ID', 'int', 4, 10, 0, 0, 1))
        for j in range(colunas):
            o = r.choice(dom)
            linhas.append(_linha('coluna', t, f'COD{o.upper()}{j}', r.choice(['int', 'varchar', 'decimal']), 4, 10, 2, 1))
    cat, _ = receitas.catalogo_de_sql(linhas, 'erp')
    return catalogo.Fonte('erp', cat, '')


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


class TestSimulacao(unittest.TestCase):
    def setUp(self):
        from tecnicas.bunshin.simulacao import Simulador, categorias
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
        _calado(_aprovar_com_prototipo, ['aprovar', self.argila, '--por', 'Teste'])
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
        self.assertEqual(_calado(_aprovar_com_prototipo, ['aprovar', self.argila, '--por', 'Teste'])[0], 0)
        saida = os.path.join(self.dir, 'o')
        self.assertEqual(_calado(deidara.main, ['gerar', self.argila, '-o', saida])[0], 0)
        for arq in ['Quadro_e_Turnover.pbip', 'sql/erp/01_views.sql', 'sql/erp/03_qualidade.sql', 'LEIA-ME.md',
                    'docs/dicionario_indicadores.md', 'Quadro_e_Turnover.SemanticModel/definition/model.tmdl']:
            self.assertTrue(os.path.exists(os.path.join(saida, arq)), arq)
        _, tabelas, colunas, medidas, erros = validar_pbip.validar_tmdl(saida)
        self.assertEqual(erros, [])
        self.assertEqual(len(tabelas), 7)                      # 5 do ERP + metas + calendário
        self.assertEqual(validar_pbip.conferir(saida), [])

    def test_diff_mostra_mudanca_de_formula(self):
        _calado(_aprovar_com_prototipo, ['aprovar', self.argila, '--por', 'Teste'])
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
        _calado(_aprovar_com_prototipo, ['aprovar', self.argila, '--por', 'Ana'])
        a = _base()
        a['versao'] = '1.2'
        a['paginas'][0]['visuais'].append({'tipo': 'cartao', 'medida': 'HC Médio'})
        with open(self.argila, 'w', encoding='utf-8') as f:
            json.dump(a, f, ensure_ascii=False)
        _calado(_aprovar_com_prototipo, ['aprovar', self.argila, '--por', 'Bia', '--observacao', 'pedido do RH'])
        with open(os.path.join(self.dir, 'argila.aprovacao.json'), encoding='utf-8') as f:
            hist = json.load(f)['historico']
        self.assertEqual([h['aprovado_por'] for h in hist], ['Ana', 'Bia'])
        self.assertIn('versão: 1.1 → 1.2', hist[1]['mudancas'])
        saida = os.path.join(self.dir, 'o')
        _calado(deidara.main, ['gerar', self.argila, '-o', saida])
        with open(os.path.join(saida, 'docs', 'dicionario_indicadores.md'), encoding='utf-8') as f:
            self.assertIn('pedido do RH', f.read())

    def test_versao_do_deidara_diferente_pede_novo_aceite(self):
        _calado(_aprovar_com_prototipo, ['aprovar', self.argila, '--por', 'Teste'])
        arq = os.path.join(self.dir, 'argila.aprovacao.json')
        with open(arq, encoding='utf-8') as f:
            reg = json.load(f)
        reg['deidara'] = '0.0.1'
        with open(arq, 'w', encoding='utf-8') as f:
            json.dump(reg, f)
        codigo, out = _calado(deidara.main, ['gerar', self.argila, '-o', os.path.join(self.dir, 'o')])
        self.assertEqual(codigo, 1)
        self.assertIn('Deidara 0.0.1', out)

    def test_entrega_com_homologacao_papeis_e_proximos_passos(self):
        _calado(_aprovar_com_prototipo, ['aprovar', self.argila, '--por', 'Teste'])
        saida = os.path.join(self.dir, 'o')
        codigo, out = _calado(deidara.main, ['gerar', self.argila, '-o', saida])
        self.assertEqual(codigo, 0)
        self.assertIn('Agora:', out)
        self.assertIn('[DBA] rodar sql/erp/01_views.sql', out)
        with open(os.path.join(saida, 'HOMOLOGACAO.md'), encoding='utf-8') as f:
            hom = f.read()
        self.assertIn('| [ ] | HC Médio | apoia Turnover |', hom)
        self.assertIn('| [ ] | Turnover | Turnover › Turnover | pelos componentes: Desligamentos, HC Médio |', hom)
        self.assertIn('| [ ] | Meta de Turnover | cor/meta de Turnover | na própria fonte (metas: Metas) |', hom)
        with open(os.path.join(saida, 'LEIA-ME.md'), encoding='utf-8') as f:
            leia = f.read()
        self.assertIn('Se algo der errado', leia)
        self.assertIn('[DBA]', leia)
        _, out = _calado(deidara.main, ['situacao', self.argila])
        self.assertIn('projeto Power BI gerado em', out)

    def test_geracao_deterministica(self):
        _calado(_aprovar_com_prototipo, ['aprovar', self.argila, '--por', 'Teste'])
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
