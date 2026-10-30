"""
C3: o projeto Power BI gerado, com as técnicas de visual e a demonstração.

    python3 -m unittest discover -s testes
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apoio import *  # noqa: E402,F401,F403


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
