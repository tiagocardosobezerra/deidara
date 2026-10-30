"""
C4 Karura: a estatística do Deidara, conferida contra os exemplos resolvidos do NIST/SEMATECH e-Handbook.

    python3 -m unittest discover -s testes
"""

import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apoio import *  # noqa: E402,F401,F403

# NIST 6.3.2.2: vazão dos 10 primeiros lotes (o exemplo do gráfico de valores individuais)
NIST_XMR = [49.6, 47.6, 49.9, 51.3, 47.8, 51.2, 52.6, 52.4, 53.6, 52.1]
# NIST 6.3.3.2: fração defeituosa em 30 wafers de 50 chips (o exemplo do gráfico p)
NIST_P = [0.24, 0.30, 0.16, 0.20, 0.08, 0.14, 0.32, 0.18, 0.28, 0.20, 0.10, 0.12, 0.34, 0.24, 0.44, 0.16, 0.20, 0.10,
          0.26, 0.22, 0.40, 0.36, 0.48, 0.30, 0.18, 0.24, 0.14, 0.26, 0.18, 0.12]


class TestContasDoC4(unittest.TestCase):
    def test_xmr_bate_com_o_nist(self):
        from tecnicas import c4
        g = c4.xmr(NIST_XMR)
        self.assertAlmostEqual(g['centro'], 50.81, places=2)
        self.assertAlmostEqual(g['mr'], 1.8778, places=4)
        self.assertAlmostEqual(g['superior'], 55.8041, places=4)
        self.assertAlmostEqual(g['inferior'], 45.8159, places=4)

    def test_grafico_p_pela_formula_do_nist(self):
        from tecnicas import c4
        g = c4.grafico_p([round(x * 50) for x in NIST_P], [50] * 30)
        p = sum(NIST_P) / 30
        self.assertAlmostEqual(g['centro'], p, places=6)
        self.assertAlmostEqual(g['superior'][0], p + 3 * (p * (1 - p) / 50) ** 0.5, places=6)
        self.assertAlmostEqual(g['inferior'][0], max(0, p - 3 * (p * (1 - p) / 50) ** 0.5), places=6)
        self.assertAlmostEqual(g['superior'][0], 0.4102, places=4)
        self.assertAlmostEqual(g['inferior'][0], 0.0524, places=4)
        foras = [k + 1 for k, s in enumerate(c4.sinais(NIST_P, g['centro'], g['superior'], g['inferior'])) if s == 1]
        self.assertEqual(foras, [15, 23])                       # as amostras 15 (0,44) e 23 (0,48) passam do limite

    def test_grupo_menor_tem_limite_mais_largo(self):
        from tecnicas import c4
        g = c4.grafico_p([5, 50], [100, 1000])
        self.assertGreater(g['superior'][0], g['superior'][1])

    def test_tres_regras_de_sinal(self):
        from tecnicas import c4
        self.assertEqual(c4.sinais([10, 10, 30], 10, 20, 0)[2], 1)                       # fora do limite
        oito = [11, 12, 11, 12, 11, 12, 11, 12]
        self.assertEqual(c4.sinais(oito, 10, 20, 0)[7], 2)                                # 8 do mesmo lado
        self.assertIsNone(c4.sinais(oito[:7], 10, 20, 0)[6])
        seis = [10, 11, 12, 13, 14, 15]
        self.assertEqual(c4.sinais([9, 11] + seis[:-1] + [15], 12, 30, 0)[-1], 3)        # 6 subindo

    def test_z_modificado_do_nist(self):
        from tecnicas import c4
        valores = [10, 11, 10.5, 9.8, 10.2, 30]
        z = c4.z_modificado(valores)
        med = statistics.median(valores)
        mad = statistics.median(abs(x - med) for x in valores)
        self.assertAlmostEqual(z[-1], 0.6745 * (30 - med) / mad)
        self.assertGreater(z[-1], c4.LIMIAR_Z_MODIFICADO)
        self.assertTrue(all(abs(x) < c4.LIMIAR_Z_MODIFICADO for x in z[:-1]))

    def test_tendencia_bate_com_a_regressao_do_python(self):
        from tecnicas import c4
        y = [5.0, 4.9, 4.9, 4.7, 4.8, 4.6, 4.5, 4.6, 4.4, 4.3, 4.3, 4.1]
        inclinacao, r2 = c4.tendencia(y)
        ref = statistics.linear_regression(list(range(1, 13)), y)
        self.assertAlmostEqual(inclinacao, ref.slope)
        self.assertAlmostEqual(r2, statistics.correlation(list(range(1, 13)), y) ** 2)

    def test_meta_x_faixa_segue_a_polaridade(self):
        from tecnicas import c4
        self.assertEqual(c4.meta_x_faixa(0.05, 0.07, 0.02, False), 'dentro')
        self.assertEqual(c4.meta_x_faixa(0.01, 0.07, 0.02, False), 'inalcancavel')   # menor melhor, abaixo da faixa
        self.assertEqual(c4.meta_x_faixa(0.09, 0.07, 0.02, False), 'folgada')
        self.assertEqual(c4.meta_x_faixa(0.09, 0.07, 0.02, True), 'inalcancavel')

    def test_todo_dax_do_c4_passa(self):
        from kibaku_nendo.especificacao import sintaxe_dax
        from tecnicas import c4, sasori
        daxs = [c4.dax_controle(parte, '[T]', 'dCalendario', tipo, '[D]', '[H]')
                for parte in ('centro', 'superior', 'inferior', 'sinal') for tipo in ('xmr', 'p', 'u')]
        daxs += [c4.dax_meta_x_faixa('[T]', '[M]', 'dCalendario', 'p', False, 'percentual', '[D]', '[H]'),
                 c4.dax_fora_da_curva('[S]', 'dCargo[Cargo]'),
                 c4.dax_fora_da_curva('[T]', 'dCargo[Cargo]', True, '[D]', '[H]'),
                 c4.dax_tendencia('[T]', 'dCalendario', 'percentual') + '\nRETURN _tendencia']
        for d in daxs:
            self.assertEqual(sintaxe_dax(d), [], d[:80])
            self.assertEqual(sasori.desconhecidas(d), [], d[:80])


class TestC4NoMotor(unittest.TestCase):
    def _argila(self):
        a = _base()
        a['medidas'] += [
            {'nome': 'Controle do Turnover', 'tipo': 'controle', 'medida': 'Turnover', 'descricao': 'x'},
            {'nome': 'Controle dos Desligamentos', 'tipo': 'controle', 'medida': 'Desligamentos', 'descricao': 'x'},
            {'nome': 'Fora da curva', 'tipo': 'fora_da_curva', 'medida': 'Remuneração Média',
             'categoria': 'dCargo[Cargo]', 'descricao': 'x'},
            {'nome': 'Fora no turnover', 'tipo': 'fora_da_curva', 'medida': 'Turnover', 'categoria': 'dCargo[Cargo]',
             'descricao': 'x'},
        ]
        a['paginas'][1]['visuais'] = [
            {'tipo': 'segmentador', 'campo': 'dCalendario[Ano]'},
            {'tipo': 'controle', 'medida': 'Controle do Turnover'},
            {'tipo': 'controle', 'medida': 'Controle dos Desligamentos'},
            {'tipo': 'cartao', 'medida': 'Controle do Turnover · meta x faixa'},
            {'tipo': 'barras', 'categoria': 'dCargo[Cargo]', 'valores': ['Remuneração Média'], 'cor': 'Cor Fora da curva'},
            {'tipo': 'tabela', 'campos': ['dCargo[Cargo]', 'Turnover', 'Fora no turnover']},
            {'tipo': 'linha', 'categoria': 'dCalendario[Nome do Mês]', 'legenda': 'dCalendario[Ano]', 'valores': ['Turnover']},
            {'tipo': 'linha', 'categoria': 'dCalendario[Mês/Ano]', 'valores': ['Turnover'], 'previsao': True},
        ]
        return a

    def test_escolhe_o_grafico_pela_medida(self):
        from kibaku_nendo.especificacao import medida
        m, p = _resolver(self._argila())
        self.assertEqual(p.erros, [])
        self.assertEqual(medida(m, 'Controle do Turnover')['extra']['grafico'], 'p')          # taxa: gráfico p
        self.assertEqual(medida(m, 'Controle dos Desligamentos')['extra']['grafico'], 'xmr')  # contagem: XmR
        self.assertTrue(medida(m, 'Fora no turnover')['extra']['funil'])                       # taxa: o funil
        self.assertFalse(medida(m, 'Fora da curva')['extra']['funil'])                         # valor: z modificado
        for nome in ('Controle do Turnover · limite superior', 'Controle do Turnover · sinal',
                     'Controle do Turnover · meta x faixa', 'Cor Fora da curva'):
            self.assertTrue(medida(m, nome), nome)
        self.assertTrue(any('Previsão no painel Análise' in x for x in p.avisos), p.avisos)
        self.assertFalse([x for x in p.avisos if 'soma todos os anos' in x], p.avisos)       # sazonal por ano
        self.assertFalse([x for x in p.avisos if 'filtra só parte' in x], p.avisos)

    def test_faixa_tipica(self):
        from kibaku_nendo.especificacao import medida
        a = _base()
        a['medidas'] += [{'nome': 'Remuneração mediana', 'agregacao': 'mediana', 'coluna': 'dColaborador[Remuneração]',
                          'descricao': 'x'},
                         {'nome': 'Remuneração Q1', 'agregacao': 'quartil_1', 'coluna': 'dColaborador[Remuneração]',
                          'descricao': 'x'}]
        m, p = _resolver(a)
        self.assertEqual(p.erros, [])
        self.assertTrue(medida(m, 'Remuneração mediana')['dax'].startswith('MEDIAN('))
        self.assertIn(', 0.25)', medida(m, 'Remuneração Q1')['dax'])

    def test_pbip_e_prototipo(self):
        d = tempfile.mkdtemp(prefix='ddc4')
        shutil.copytree(os.path.join(EXEMPLO, 'catalogos'), os.path.join(d, 'catalogos'))
        arq = os.path.join(d, 'argila.json')
        with open(arq, 'w', encoding='utf-8') as f:
            json.dump(self._argila(), f, ensure_ascii=False)
        self.assertEqual(_calado(_aprovar_com_prototipo, ['aprovar', arq, '--por', 'T'])[0], 0)
        saida = os.path.join(d, 'o')
        self.assertEqual(_calado(deidara.main, ['gerar', arq, '-o', saida, '--demo'])[0], 0)
        self.assertEqual(validar_pbip.conferir(saida), [])
        with open(os.path.join(d, 'argila.prototipo.html'), encoding='utf-8') as f:
            html_ = f.read()
        self.assertIn('limites da variação normal', html_)
        self.assertIn('faixa normal', html_)
        shutil.rmtree(d, ignore_errors=True)


class TestC2EscolheOC4(unittest.TestCase):
    def test_perguntas_viram_a_pagina_sinal_ou_ruido(self):
        from tecnicas import te_no_kuchi
        argila, notas = te_no_kuchi.esbocar(
            CATALOGOS, 'turnover por cargo: é sinal ou ruído, quem está fora da curva, é sazonal e como vai fechar o ano')
        sinal = next(p for p in argila['paginas'] if p['nome'] == 'Sinal ou ruído')
        tipos = [v['tipo'] for v in sinal['visuais']]
        self.assertIn('controle', tipos)
        self.assertTrue(any(v.get('previsao') for v in sinal['visuais']))
        self.assertTrue(any(v.get('legenda') == 'dCalendario[Ano]' for v in sinal['visuais']))
        self.assertTrue(any(v.get('cor', '').startswith('Cor Fora da curva') for p in argila['paginas']
                            for v in p['visuais']))
        argila['fontes'] = {'erp': {'catalogo': 'catalogos/erp.json'}, 'metas': {'catalogo': 'catalogos/metas.json'}}
        for r in argila['relacionamentos']:
            if 'declarada' in r:
                r['declarada']['por'] = 'T'
        _, p = _resolver(argila)
        self.assertEqual(p.erros, [])
