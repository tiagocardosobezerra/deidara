"""
O motor: validação, tipos, metas, sintaxe DAX, número distorcido e mensagens.

    python3 -m unittest discover -s testes
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apoio import *  # noqa: E402,F401,F403
import test_c3  # noqa: E402


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
        for argila in (_base(), test_c3.TestTecnicasCompletas()._argila(), test_c3.TestCausaRaiz()._argila()):
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
