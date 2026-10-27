"""
Testes do Deidara sobre o exemplo fictício (schema "Aurora" do Vegapunk).

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
sys.path.insert(0, os.path.join(RAIZ, 'ferramentas'))

import deidara  # noqa: E402
import validar_pbip  # noqa: E402
from argila.especificacao import referencias_dax, resolver  # noqa: E402
from argila.schema import Schema  # noqa: E402

EXEMPLO = os.path.join(RAIZ, 'exemplos', 'aurora')


def _base():
    with open(os.path.join(EXEMPLO, 'argila.json'), encoding='utf-8') as f:
        return json.load(f)


def _md(argila, nome):
    return next(x for x in argila['medidas'] if x['nome'] == nome)


SCHEMA = Schema.carregar([os.path.join(EXEMPLO, 'schema.json')])


def _resolver(argila):
    return resolver(argila, SCHEMA)


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


def _col(nome, tipo, pk=None, escala=0, tamanho=4, precisao=10):
    return {'coluna': nome, 'descricao': nome.lower(), 'tipo': tipo, 'tamanho': tamanho, 'precisao': precisao,
            'escala': escala, 'nulo': 0 if pk else 1, 'ordem': 1, 'pk_ordem': pk}


def _schema_sintetico():
    """Pedidos x clientes, com a FK em tipos diferentes (varchar -> int) e colunas de borda."""
    fk = {'constraint': 'FK_PED_CLI', 'origem': 'constraint', 'tabela_filha': 'PEDIDO', 'tabela_mae': 'CLIENTE',
          'colunas': [{'campo_filho': 'CODCLI', 'campo_mae': 'COD'}], 'composta': False,
          'on': 'PEDIDO.CODCLI = CLIENTE.COD', 'join': '', 'confirmado_pelo_dicionario': None, 'cobre_chave_da_mae': True}
    fk2 = {'constraint': 'FK_PED_LOJA', 'origem': 'constraint', 'tabela_filha': 'PEDIDO', 'tabela_mae': 'LOJA',
           'colunas': [{'campo_filho': 'EMP', 'campo_mae': 'EMP'}, {'campo_filho': 'LOJA', 'campo_mae': 'LOJA'}],
           'composta': True, 'on': '', 'join': '', 'confirmado_pelo_dicionario': None, 'cobre_chave_da_mae': True}
    dados = {'tabelas': {
        'PEDIDO': {'metadados': {'pk': ['ID']}, 'colunas': [
            _col('ID', 'int', 1), _col('CODCLI', 'varchar', tamanho=10, precisao=0),
            _col('TAXA', 'decimal', escala=6, tamanho=9, precisao=18), _col('DATA', 'datetime'),
            _col('HORA', 'time'), _col('EMP', 'int'), _col('LOJA', 'smallint')], 'fks': [fk, fk2]},
        'CLIENTE': {'metadados': {'pk': ['COD']}, 'colunas': [_col('COD', 'int', 1), _col('NOME', 'varchar', tamanho=60)],
                    'fks': [fk]},
        'LOJA': {'metadados': {'pk': ['EMP', 'LOJA']}, 'colunas': [_col('EMP', 'int', 1), _col('LOJA', 'smallint', 2),
                                                                   _col('NOMELOJA', 'varchar', tamanho=60)], 'fks': [fk2]},
    }}
    d = tempfile.mkdtemp(prefix='dds')
    with open(os.path.join(d, 'schema.json'), 'w', encoding='utf-8') as f:
        json.dump(dados, f)
    return Schema.carregar([os.path.join(d, 'schema.json')])


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
        self.assertIn('CAST(t.[CODCLI] AS int) AS [CODCLI]', views(self.m))

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
        v = views(self.m)
        self.assertIn("ISNULL(RTRIM(CONVERT(nvarchar(100), t.[EMP])), N'∅')", v)
        self.assertIn("N'|'", v)

    def test_conferencia_sem_overflow_e_qualidade_com_nomes(self):
        from argila.sql import conferencia, qualidade
        self.assertIn('COUNT_BIG(*)', conferencia(self.m))
        for linha in qualidade(self.m).split('UNION ALL'):
            if 'SELECT' in linha:
                self.assertIn('AS ocorrencias', linha)

    def test_tmdl_de_data_e_moeda(self):
        from argila import tmdl
        texto = tmdl.tabela(self.m, next(t for t in self.m['tabelas'] if t['nome'] == 'fPedido'))
        self.assertIn('annotation SummarizationSetBy = User', texto)
        self.assertIn('discourageImplicitMeasures', tmdl.modelo(self.m))


class TestMetas(unittest.TestCase):
    def setUp(self):
        self.m, self.p = _resolver(_base())

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
        shutil.copy(os.path.join(EXEMPLO, 'schema.json'), self.dir)
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
        for arq in ['Quadro_e_Turnover.pbip', 'sql/01_views.sql', 'sql/02_conferencia.sql', 'LEIA-ME.md',
                    'docs/dicionario_indicadores.md', 'Quadro_e_Turnover.SemanticModel/definition/model.tmdl']:
            self.assertTrue(os.path.exists(os.path.join(saida, arq)), arq)
        _, tabelas, colunas, medidas, erros = validar_pbip.validar_tmdl(saida)
        self.assertEqual(erros, [])
        self.assertEqual(len(tabelas), 6)
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
        a['versao'] = '1.1'
        a['paginas'][0]['visuais'].append({'tipo': 'cartao', 'medida': 'HC Médio'})
        with open(self.argila, 'w', encoding='utf-8') as f:
            json.dump(a, f, ensure_ascii=False)
        _calado(deidara.main, ['aprovar', self.argila, '--por', 'Bia', '--observacao', 'pedido do RH'])
        with open(os.path.join(self.dir, 'argila.aprovacao.json'), encoding='utf-8') as f:
            hist = json.load(f)['historico']
        self.assertEqual([h['aprovado_por'] for h in hist], ['Ana', 'Bia'])
        self.assertIn('versão: 1.0 → 1.1', hist[1]['mudancas'])
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
