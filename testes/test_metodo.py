"""
O método dos indicadores: calendário, data de corte, meta e as contas que dão número errado sem aviso.

    python3 -m unittest discover -s testes
"""

import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apoio import *  # noqa: E402,F401,F403
from tecnicas.c3 import sql, tmdl  # noqa: E402


def _tabela(m, nome):
    return next(t for t in m['tabelas'] if t['nome'] == nome)


class TestCalendario(unittest.TestCase):
    def test_sem_fim_acompanha_o_ano_corrente(self):
        a = _base()
        a['calendario'].pop('fim', None)
        m, p = _resolver(a)
        self.assertFalse(p.erros)
        cal = _tabela(m, 'dCalendario')
        self.assertTrue(cal['fim_dinamico'])
        self.assertEqual(cal['fim'], datetime.date.today().year)
        self.assertIn('Date.EndOfYear(Date.From(DateTime.LocalNow()))', tmdl.tabela(m, cal))
        self.assertIn('DATEFROMPARTS(YEAR(GETDATE()), 12, 31)', sql.qualidade(m, sql.fontes_sql(m)[0]))

    def test_fim_fixo_no_passado_vira_aviso(self):
        a = _base()
        a['calendario']['fim'] = datetime.date.today().year - 1
        m, p = _resolver(a)
        self.assertFalse(p.erros)
        self.assertTrue(any('o calendário termina em 31/12' in x for x in p.avisos))
        self.assertIn(f'#date({a["calendario"]["fim"]}, 12, 31)', tmdl.tabela(m, _tabela(m, 'dCalendario')))

    def test_fim_atual_e_fim_invalido(self):
        a = _base()
        a['calendario']['fim'] = 'atual'
        self.assertTrue(_tabela(_resolver(a)[0], 'dCalendario')['fim_dinamico'])
        a['calendario']['fim'] = 'logo'
        self.assertTrue(any('"fim" pode ser "atual"' in x for x in _resolver(a)[1].erros))

    def test_ano_fiscal(self):
        a = _base()
        a['calendario']['mes_inicio_fiscal'] = 4
        m, p = _resolver(a)
        self.assertFalse(p.erros)
        cal = _tabela(m, 'dCalendario')
        self.assertIn('Ano Fiscal', [c['nome'] for c in cal['colunas']])
        texto = tmdl.tabela(m, cal)
        self.assertIn('"Ano Fiscal", each [Ano] + (if [Mês] >= 4 then 1 else 0)', texto)
        self.assertIn('in\n', texto)
        acum = next(x for x in m['medidas'] if x['nome'] == 'Desligamentos Acum. Ano')
        self.assertIn('TOTALYTD([Desligamentos], dCalendario[Data], "03-31")', acum['dax'])
        a['calendario']['mes_inicio_fiscal'] = 13
        self.assertTrue(any('mes_inicio_fiscal' in x for x in _resolver(a)[1].erros))

    def test_fiscal_no_grupo_de_calculo(self):
        a = _base()
        a['calendario']['mes_inicio_fiscal'] = 7
        a['grupo_calculo'] = {'nome': 'Período', 'itens': ['atual', 'acumulado_ano']}
        m, p = _resolver(a)
        self.assertFalse(p.erros)
        grupo = next(t for t in m['tabelas'] if t.get('grupo_calculo'))
        self.assertIn('DATESYTD(dCalendario[Data], "06-30")', grupo['grupo_calculo']['itens'][1]['dax'])

    def test_esboco_nao_fixa_o_fim(self):
        from tecnicas import te_no_kuchi
        with open(te_no_kuchi.__file__, encoding='utf-8') as f:
            self.assertNotIn('2018, 2026', f.read())


class TestDataDeCorte(unittest.TestCase):
    def setUp(self):
        self.m, self.p = _resolver(_base())

    def _md(self, nome):
        return next(x for x in self.m['medidas'] if x['nome'] == nome)

    def test_corte_e_a_ultima_data_com_dado_nunca_depois_de_hoje(self):
        self.assertFalse(self.p.erros)
        corte = self._md('Data de Corte')
        self.assertTrue(corte['oculta'])
        self.assertIn('CALCULATE(MAX(fDesligamento[Data do Desligamento]), REMOVEFILTERS())', corte['dax'])
        self.assertIn('CALCULATE(MAX(dColaborador[Data de Admissão]), REMOVEFILTERS())', corte['dax'])  # estoque
        self.assertIn('_ultima > TODAY(), TODAY(), _ultima', corte['dax'])
        self.assertFalse(any('Data de Corte' in x for x in self.m['pendencias']))

    def test_ano_anterior_compara_ate_o_mesmo_dia(self):
        dax = self._md('Var. Desligamentos A/A')['dax']
        self.assertIn('VAR _corte = [Data de Corte]', dax)
        # filtro True/False com medida dentro o Power BI recusa ("função PLACEHOLDER"): a data vai numa variável
        self.assertIn('CALCULATETABLE(SAMEPERIODLASTYEAR(dCalendario[Data]), '
                      'KEEPFILTERS(dCalendario[Data] <= _corte))', dax)
        self.assertNotIn('<= [Data de Corte]', dax)
        self.assertNotIn('TODAY()', dax)

    def test_estoque_para_no_corte(self):
        self.assertIn('VAR _fim = MIN(MAX(dCalendario[Data]), [Data de Corte])', self._md('Headcount')['dax'])

    def test_corte_nao_cria_distorcao_nem_aparece_ao_gestor(self):
        self.assertFalse(any('Acum. Ano' in a and 'parte' in a for a in self.p.avisos), self.p.avisos)
        from tecnicas.c3 import docs
        self.assertNotIn('**Data de Corte**', docs.dicionario(self.m))

    def test_corte_hoje(self):
        a = _base()
        a['calendario']['corte'] = 'hoje'
        m, p = _resolver(a)
        self.assertFalse(p.erros)
        self.assertFalse(any(x['nome'] == 'Data de Corte' for x in m['medidas']))
        self.assertIn('VAR _corte = TODAY()', next(x for x in m['medidas'] if x['nome'] == 'Desligamentos Acum. Ano')['dax'])
        a['calendario']['corte'] = 'ontem'
        self.assertTrue(any('"corte"' in e for e in _resolver(a)[1].erros))

    def test_nome_reservado(self):
        a = _base()
        a['medidas'].append({'nome': 'Data de Corte', 'dax': 'TODAY()', 'descricao': 'x'})
        self.assertTrue(any('renomeie a sua' in e for e in _resolver(a)[1].erros))

    def test_grupo_de_calculo_tambem_para_no_corte(self):
        a = _base()
        a['grupo_calculo'] = {'nome': 'Período', 'itens': ['atual', 'variacao_ano_anterior', 'mes_anterior']}
        m, p = _resolver(a)
        self.assertFalse(p.erros)
        itens = next(t for t in m['tabelas'] if t.get('grupo_calculo'))['grupo_calculo']['itens']
        # sem citar medida dentro do item (recursão lateral): a data de corte vai por extenso
        self.assertIn('VAR _corte = MIN(TODAY(), COALESCE(MAXX({ CALCULATE(MAX(fDesligamento['
                      'Data do Desligamento]), REMOVEFILTERS())', itens[1]['dax'])
        self.assertIn('KEEPFILTERS(dCalendario[Data] <= _corte)', itens[1]['dax'])   # CALCULATE fora do filtro
        self.assertIn('CALCULATETABLE(DATEADD(dCalendario[Data], -1, MONTH)', itens[2]['dax'])
        from kibaku_nendo.especificacao import referencias_dax
        for it in itens:
            self.assertEqual([n for t, n in referencias_dax(it['dax']) if not t and n != 'Value'], [], it['rotulo'])



class TestMeta(unittest.TestCase):
    def _md(self, m, nome):
        return next(x for x in m['medidas'] if x['nome'] == nome)

    def test_meta_anual_vira_proporcional_aos_meses(self):
        m, p = _resolver(_base())
        self.assertFalse(p.erros)
        prop = self._md(m, 'Meta de Turnover no Período')
        self.assertIn('VAR _meses = COUNTROWS(FILTER(VALUES(dCalendario[Ano-Mês Num]), dCalendario[Ano-Mês Num] <= _ate))',
                      prop['dax'])
        self.assertIn('[Meta de Turnover] * _meses / 12', prop['dax'])
        turnover = self._md(m, 'Turnover')
        self.assertEqual(turnover['meta_medida'], 'Meta de Turnover no Período')
        self.assertIn('VAR _meta = [Meta de Turnover no Período]', self._md(m, 'Cor Turnover')['dax'])

    def test_meta_mensal_e_periodo(self):
        a = _base()
        _md(a, 'Turnover')['base_meta'] = 'mes'
        m, _ = _resolver(a)
        self.assertIn('[Meta de Turnover] * _meses', self._md(m, 'Meta de Turnover no Período')['dax'])
        _md(a, 'Turnover')['base_meta'] = 'periodo'
        m, _ = _resolver(a)
        self.assertEqual(self._md(m, 'Turnover')['meta_medida'], 'Meta de Turnover')
        _md(a, 'Turnover')['base_meta'] = 'semestre'
        self.assertTrue(any('"base_meta"' in e for e in _resolver(a)[1].erros))

    def test_taxa_sobre_estoque_sem_base_da_meta_vira_aviso(self):
        a = _base()
        _md(a, 'Turnover').pop('base_meta')
        _, p = _resolver(a)
        self.assertTrue(any('é anual ou mensal?' in x for x in p.avisos))

    def test_meta_ponderada_pelo_tamanho(self):
        m, p = _resolver(_base())
        meta = self._md(m, 'Meta de Turnover')
        self.assertIn('VALUES(dEmpresa[Cód. Empresa])', meta['dax'])
        self.assertIn('"@valor", CALCULATE(AVERAGE(fMeta[Meta Turnover]))', meta['dax'])
        self.assertIn('"@peso", [HC Médio]', meta['dax'])
        self.assertIn('SUMX(FILTER(_itens, NOT ISBLANK([@valor])), [@peso])', meta['dax'])
        self.assertFalse(any('média simples' in x for x in p.avisos))

    def test_meta_media_simples_vira_aviso(self):
        a = _base()
        a['medidas'] = [x for x in a['medidas'] if x['nome'] != 'Meta de Turnover'] + [
            {'nome': 'Meta de Turnover', 'agregacao': 'media', 'coluna': 'fMeta[Meta Turnover]',
             'formato': 'percentual', 'descricao': 'x'}]
        _, p = _resolver(a)
        self.assertTrue(any('média simples das linhas' in x and '"media_ponderada"' in x for x in p.avisos))

    def test_meta_ponderada_invalida(self):
        a = _base()
        _md(a, 'Meta de Turnover')['peso'] = 'HC'
        self.assertTrue(any('"peso" "HC"' in e for e in _resolver(a)[1].erros))
        a = _base()
        _md(a, 'Meta de Turnover')['por'] = 'dMotivo[Motivo]'
        self.assertTrue(any('não filtra fMeta' in e for e in _resolver(a)[1].erros))

    def test_meta_que_nao_muda_com_o_ano_continua_avisada(self):
        _, p = _resolver(_base())
        self.assertTrue(any('a meta "Meta de Turnover" não muda com dCalendario[Ano]' in x for x in p.avisos))



class TestCadastroEPolaridade(unittest.TestCase):
    def _md(self, m, nome):
        return next(x for x in m['medidas'] if x['nome'] == nome)

    def test_soma_do_cadastro_inteiro_vira_aviso(self):
        a = _base()
        _md(a, 'Remuneração Total').pop('no_estoque')
        _, p = _resolver(a)
        self.assertTrue(any('soma dColaborador inteira, ativos e desligados' in x and '"no_estoque": "Headcount"' in x
                            for x in p.avisos), p.avisos)

    def test_no_estoque_soma_so_quem_esta_dentro(self):
        m, p = _resolver(_base())
        self.assertFalse(p.erros)
        self.assertFalse(any('ativos e desligados' in x for x in p.avisos))
        dax = self._md(m, 'Remuneração Total')['dax']
        self.assertIn('VAR _fim = MIN(MAX(dCalendario[Data]), [Data de Corte])', dax)
        self.assertIn('dColaborador[Data de Admissão] <= _fim', dax)
        self.assertIn('ISEMPTY(FILTER(RELATEDTABLE(fDesligamento), fDesligamento[Data do Desligamento] <= _fim))', dax)
        self.assertIn('SUMX(_dentro, dColaborador[Remuneração])', dax)
        conf = sql.conferencia(m, sql.fontes_sql(m)[0])
        self.assertIn('Remuneração Total: só de quem está em "Headcount"', conf)
        self.assertIn('AND NOT EXISTS (SELECT 1 FROM [bi].[vw_fDesligamento] AS s WHERE s.[MATRICULA] = e.[Matrícula]',
                      conf)

    def test_no_estoque_invalido(self):
        a = _base()
        _md(a, 'Remuneração Total')['no_estoque'] = 'Desligamentos'
        self.assertTrue(any('estoque_na_data' in e for e in _resolver(a)[1].erros))

    def test_conta_de_tempo_herda_a_polaridade_da_base(self):
        m, _ = _resolver(_base())
        self.assertEqual(self._md(m, 'Desligamentos Acum. Ano')['polaridade'], 'menor_melhor')
        a = _base()
        _md(a, 'Desligamentos Acum. Ano')['polaridade'] = 'maior_melhor'       # a escolhida pela pessoa vale
        m, _ = _resolver(a)
        self.assertEqual(self._md(m, 'Desligamentos Acum. Ano')['polaridade'], 'maior_melhor')



class TestFicticiosCoerentes(unittest.TestCase):
    """O gestor faz a conta de cabeça: os números fictícios do protótipo precisam fechar entre si."""

    def setUp(self):
        from tecnicas.bunshin.simulacao import Simulador, categorias
        self.m, _ = _resolver(_base())
        self.s, self.categorias = Simulador(self.m), categorias
        self.cargo = {'tabela': 'dCargo', 'nome': 'Cargo', 'tipo': 'coluna'}
        self.mes = {'tabela': 'dCalendario', 'nome': 'Mês/Ano', 'tipo': 'coluna'}

    def test_taxa_fecha_com_numerador_e_denominador_mostrados(self):
        v = self.s.valor
        self.assertAlmostEqual(v('Turnover'), v('Desligamentos') / v('HC Médio'), places=9)
        f = [(self.cargo, 'Cargo A')]
        self.assertAlmostEqual(v('Turnover', f), v('Desligamentos', f) / v('HC Médio', f), places=9)

    def test_taxa_varia_entre_as_linhas(self):
        taxas = {round(self.s.valor('Turnover', [(self.cargo, r)]), 3) for r in self.categorias(self.m, self.cargo)}
        self.assertGreater(len(taxas), 4)

    def test_estoque_nao_se_divide_entre_os_meses(self):
        hc = self.s.valor('Headcount')
        for r in self.categorias(self.m, self.mes):
            self.assertLess(abs(self.s.valor('Headcount', [(self.mes, r)]) / hc - 1), 0.05)
        mensal = self.s.valor('Turnover', [(self.mes, 'jan/2025')])
        self.assertLess(mensal, self.s.valor('Turnover') / 4)          # a taxa de um mês é bem menor que a do ano

    def test_valor_por_pessoa_plausivel_e_variado(self):
        media = self.s.valor('Remuneração Média')
        self.assertTrue(2000 < media < 15000, media)
        por_cargo = {round(self.s.valor('Remuneração Média', [(self.cargo, r)])) for r in self.categorias(self.m, self.cargo)}
        self.assertGreater(len(por_cargo), 4)

    def test_meta_anual_vira_mensal_na_linha_do_mes(self):
        anual = self.s.valor('Meta de Turnover no Período')
        self.assertAlmostEqual(self.s.valor('Meta de Turnover no Período', [(self.mes, 'jan/2025')]) * 12,
                               self.s.valor('Meta de Turnover', [(self.mes, 'jan/2025')]), places=9)
        self.assertGreater(anual, 0)



class TestFichaEHomologacao(unittest.TestCase):
    def setUp(self):
        self.m, self.p = _resolver(_base())

    def _md(self, nome):
        return next(x for x in self.m['medidas'] if x['nome'] == nome)

    def test_tolerancia_vira_faixa_amarela(self):
        dax = self._md('Cor Turnover')['dax']
        self.assertIn('IF(_valor <= _meta, "#107C10", IF(_valor <= _meta + ABS(_meta) * 0.1, "#986F0B", "#D13438"))', dax)
        a = _base()
        _md(a, 'Turnover')['tolerancia'] = 2
        self.assertTrue(any('"tolerancia"' in e for e in _resolver(a)[1].erros))

    def test_indicador_com_meta_sem_dono_vira_aviso(self):
        self.assertFalse(any('quem responde' in x for x in self.p.avisos))
        a = _base()
        _md(a, 'Turnover').pop('dono')
        self.assertTrue(any('quem responde por "Turnover"' in x for x in _resolver(a)[1].avisos))

    def test_ficha_no_dicionario(self):
        from tecnicas.c3 import docs
        texto = docs.dicionario(self.m)
        self.assertIn('## Fichas dos indicadores', texto)
        self.assertIn('- **Dono:** Gerência de Gente e Gestão · **Periodicidade:** mensal', texto)
        self.assertIn('amarelo até 10% da meta do lado ruim', texto)
        self.assertIn('(meta anual, proporcional aos meses do filtro)', texto)
        self.assertIn('```dax\nTurnover =\nDIVIDE([Desligamentos] + 0, [HC Médio])\n```', texto)   # mês sem saída: 0%

    def test_consulta_dax_da_homologacao(self):
        from kibaku_nendo.especificacao import sintaxe_dax
        from tecnicas import sasori
        from tecnicas.c3 import docs
        dax = docs.consulta_dax(self.m)
        self.assertIn('EVALUATE\nROW(', dax)
        self.assertIn('"Desligamentos", [Desligamentos]', dax)
        self.assertIn('"Remuneração Total", [Remuneração Total]', dax)        # o de fim de mês, como no SQL
        self.assertEqual(sintaxe_dax(dax), [])
        self.assertEqual(sasori.desconhecidas(dax), [])

    def test_prototipo_mostra_perto_da_meta(self):
        from tecnicas.bunshin.simulacao import Simulador
        s = Simulador(self.m)
        self.assertIn(s.faixa('Turnover'), ('boa', 'atencao', 'ruim'))
        self.assertIsNone(s.faixa('Desligamentos'))


class TestPlacar(unittest.TestCase):
    def test_o_motor_pega_todas_as_armadilhas_do_exemplo(self):
        sys.path.insert(0, os.path.join(RAIZ, 'ferramentas'))
        import avaliar
        ok, total, linhas = avaliar.avaliar(os.path.join(EXEMPLO, 'avaliacao.json'))
        self.assertGreaterEqual(total, 20)
        self.assertEqual(ok, total, '\n'.join(x for x in linhas if x.startswith('✗')))


if __name__ == '__main__':
    unittest.main()
