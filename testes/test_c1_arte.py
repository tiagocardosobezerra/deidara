"""
C1, Bunshin e Arte: protótipo, números fictícios, design e modelos de layout.

    python3 -m unittest discover -s testes
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apoio import *  # noqa: E402,F401,F403


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
