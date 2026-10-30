"""
O que veio por último do Power BI Design Files: estrelas e progresso como marcador do mapa, colunas 3D, tour
guiado em HTML Content, tema de arquivo e o agrupamento de textos.

    python3 -m unittest discover -s testes
"""

import csv
import json
import os
import shutil
import tempfile
import unittest

from test_deidara import EXEMPLO, _aprovar_com_prototipo, _base, _calado, _md, _resolver, deidara, validar_pbip


def _argila():
    a = _base()
    a['medidas'] += [
        {'nome': 'Estrelas', 'tipo': 'svg_estrelas', 'medida': 'Headcount', 'categoria': 'dEmpresa[Empresa]',
         'descricao': 'x'},
        {'nome': 'Nota', 'tipo': 'svg_estrelas', 'medida': 'Headcount', 'categoria': 'dEmpresa[Empresa]', 'maximo': 5,
         'descricao': 'x'},
        {'nome': 'Progresso', 'tipo': 'svg_progresso', 'medida': 'Turnover', 'categoria': 'dEmpresa[Empresa]',
         'descricao': 'x'},
    ]
    a['paginas'][0]['tour'] = True
    a['paginas'][1]['visuais'] = [
        {'tipo': 'mapa', 'local': 'dEmpresa[Empresa]', 'marcador': 'Progresso'},
        {'tipo': 'mapa', 'local': 'dEmpresa[Empresa]', 'valores': ['Headcount'], 'camada': 'colunas'},
        {'tipo': 'tabela', 'campos': ['dEmpresa[Empresa]', 'Headcount', 'Estrelas', 'Nota']},
    ]
    return a


class TestMarcadores(unittest.TestCase):
    def test_medidas_svg(self):
        from tecnicas import sasori as dicionario
        from kibaku_nendo.especificacao import medida
        m, p = _resolver(_argila())
        self.assertEqual(p.erros, [])
        self.assertFalse([x for x in p.avisos if '[SVG]' in x or 'marcador' in x], p.avisos)
        for nome, trecho in (('Estrelas', "MAXX(ALLSELECTED(dEmpresa[Empresa]), [Headcount])"),
                             ('Nota', 'DIVIDE(_valor, 5) * 5'), ('Estrelas', "clip-path='url(%23nota)'"),
                             ('Progresso', '"%25 da meta</text>"'), ('Progresso', '[Meta de Turnover]')):
            md = medida(m, nome)
            self.assertIn(trecho, md['dax'], nome)
            self.assertEqual(dicionario.desconhecidas(md['dax']), [], nome)
        self.assertEqual(m['paginas'][1]['visuais'][0]['marcador'], 'Progresso')
        self.assertEqual(m['paginas'][1]['visuais'][1]['camada'], 'colunas')

    def test_erros(self):
        casos = [
            (lambda a: _md(a, 'Nota').update(maximo=0), '"maximo"'),
            (lambda a: _md(a, 'Progresso').update(medida='Headcount'), 'não tem meta'),
            (lambda a: a['paginas'][1]['visuais'][0].update(marcador='Headcount'), 'medida de imagem'),
            (lambda a: a['paginas'][1]['visuais'][0].update(legenda='dCargo[Cargo]'), 'não leva "legenda"'),
            (lambda a: a['paginas'][1]['visuais'][1].update(camada='pizza'), '"camada"'),
            (lambda a: a['paginas'][1]['visuais'][1].pop('valores'), '"marcador"'),
        ]
        for mudar, trecho in casos:
            a = _argila()
            mudar(a)
            _, p = _resolver(a)
            self.assertTrue(any(trecho in e for e in p.erros), (trecho, p.erros))


class TestTour(unittest.TestCase):
    def test_medida_do_tour(self):
        from kibaku_nendo.especificacao import medida
        m, p = _resolver(_argila())
        md = medida(m, 'Tour · Visão Geral')
        self.assertEqual(md['tipo'], 'html_tour')
        texto = md['extra']['html']
        self.assertIn("<details class='tg-p1'>", texto)
        self.assertIn('Passo 1 de', texto)
        self.assertNotIn('<script', texto.lower())
        self.assertNotIn('"', texto.split('</style>', 1)[1].replace('&quot;', ''))  # atributos com aspas simples
        self.assertTrue(any('tour usa o HTML Content' in x for x in p.avisos), p.avisos)
        self.assertEqual(m['paginas'][0]['tour'], 'Tour · Visão Geral')

    def test_historia_longa_fica_sem_tour(self):
        a = _argila()
        a['modelo'] = 'historia-longa'
        m, p = _resolver(a)
        self.assertTrue(any('tour guiado fica de fora' in x for x in p.avisos), p.avisos)


class TestTemaDeArquivo(unittest.TestCase):
    def test_tema_inteiro_no_relatorio(self):
        from tecnicas.c3 import pbir
        d = tempfile.mkdtemp(prefix='ddt')
        tema = {'name': 'Comunidade', 'dataColors': ['#123456', '#654321'], 'background': '#FAFAFA',
                'foreground': '#111111', 'visualStyles': {'*': {'*': {'border': [{'show': True}]}}}}
        with open(os.path.join(d, 'tema.json'), 'w', encoding='utf-8') as f:
            json.dump(tema, f)
        a = _base()
        a['tema'] = {'arquivo': 'tema.json'}
        a['_pasta'] = d
        m, p = _resolver(a)
        self.assertEqual(p.erros, [])
        self.assertEqual((m['tema']['cores'], m['tema']['fundo'], m['tema']['texto']),
                         (['#123456', '#654321'], '#FAFAFA', '#111111'))
        saida = pbir._tema(m)
        self.assertEqual(saida['name'], 'Deidara')
        self.assertIn('visualStyles', saida)                         # vai inteiro
        self.assertIn('textClasses', saida)                          # e o Deidara completa o que falta
        self.assertTrue(any('licença' in x for x in p.avisos), p.avisos)
        a['tema'] = {'arquivo': 'nao_existe.json'}
        _, p = _resolver(a)
        self.assertTrue(any('não consegui ler o tema' in e for e in p.erros), p.erros)
        shutil.rmtree(d, ignore_errors=True)


class TestFluxoCompleto(unittest.TestCase):
    def test_pbip_e_prototipo(self):
        d = tempfile.mkdtemp(prefix='ddm')
        shutil.copytree(os.path.join(EXEMPLO, 'catalogos'), os.path.join(d, 'catalogos'))
        arq = os.path.join(d, 'argila.json')
        with open(arq, 'w', encoding='utf-8') as f:
            json.dump(_argila(), f, ensure_ascii=False)
        self.assertEqual(_calado(_aprovar_com_prototipo, ['aprovar', arq, '--por', 'T'])[0], 0)
        saida = os.path.join(d, 'o')
        self.assertEqual(_calado(deidara.main, ['gerar', arq, '-o', saida, '--demo'])[0], 0)
        self.assertEqual(validar_pbip.conferir(saida), [])
        rep = os.path.join(saida, 'Quadro_e_Turnover.Report', 'definition')
        mapas, paginas, html_ = [], {}, []
        for raiz, _, fs in os.walk(rep):
            if 'page.json' in fs:
                with open(os.path.join(raiz, 'page.json'), encoding='utf-8') as f:
                    pg = json.load(f)
                paginas[pg['displayName']] = pg
            if 'visual.json' in fs:
                with open(os.path.join(raiz, 'visual.json'), encoding='utf-8') as f:
                    v = json.load(f)['visual']
                if v['visualType'] == 'azureMap':
                    mapas.append(v.get('objects') or {})
                if v['visualType'].startswith('htmlContent'):
                    html_.append(v)
        marcador = next(o for o in mapas if 'imageUrl' in json.dumps(o.get('bubbleLayer')))
        self.assertIn("'image'", json.dumps(marcador['bubbleLayer']))
        self.assertTrue(any(o.get('barChart') for o in mapas))                    # colunas 3D
        self.assertEqual(paginas['Tour · Visão Geral']['visibility'], 'HiddenInViewMode')
        self.assertEqual(len(html_), 1)
        with open(os.path.join(rep, 'report.json'), encoding='utf-8') as f:
            self.assertTrue(any(x.startswith('htmlContent') for x in json.load(f)['publicCustomVisuals']))
        with open(os.path.join(d, 'argila.prototipo.html'), encoding='utf-8') as f:
            proto = f.read()
        for trecho in ('tg-tour', 'abre-tour', '★', '%</text>'):                  # tour, estrelas e progresso
            self.assertIn(trecho, proto)
        shutil.rmtree(d, ignore_errors=True)


class TestGrupoDeCalculo(unittest.TestCase):
    def _argila(self):
        a = _base()
        a['grupo_calculo'] = {'nome': 'Período', 'itens': ['atual', 'acumulado_ano', 'variacao_ano_anterior']}
        a['paginas'][1]['visuais'].insert(0, {'tipo': 'botoes', 'campo': 'Período[Período]'})
        return a

    def test_tabela_e_tmdl(self):
        from tecnicas import sasori as dicionario
        from tecnicas.c3 import tmdl
        from kibaku_nendo.especificacao import tabela_do_modelo
        from tecnicas.bunshin.simulacao import categorias
        m, p = _resolver(self._argila())
        self.assertEqual(p.erros, [])
        t = tabela_do_modelo(m, 'Período')
        itens = t['grupo_calculo']['itens']
        self.assertEqual([x['rotulo'] for x in itens], ['Atual', 'Acumulado no ano', 'Var. ano anterior'])
        for x in itens:
            self.assertEqual(dicionario.desconhecidas(x['dax']), [], x['rotulo'])
        texto = tmdl.tabela(m, t)
        for trecho in ('\tcalculationGroup', "calculationItem 'Acumulado no ano' = CALCULATE(SELECTEDMEASURE(), "
                       'DATESYTD(dCalendario[Data]))', 'formatStringDefinition = IF(ISNUMBER(SELECTEDMEASURE())',
                       'sourceColumn: Name', 'sortByColumn: Ordem', "partition 'Período' = calculationGroup"):
            self.assertIn(trecho, texto)
        self.assertEqual(categorias(m, {'tabela': 'Período', 'nome': 'Período'})[:2], ['Atual', 'Acumulado no ano'])

    def test_erros(self):
        a = self._argila()
        a['grupo_calculo']['itens'] = ['atual', 'trimestre']
        _, p = _resolver(a)
        self.assertTrue(any('item desconhecido: trimestre' in e for e in p.erros), p.erros)
        a = self._argila()
        a.pop('calendario')
        _, p = _resolver(a)
        self.assertTrue(any('pede "calendario"' in e for e in p.erros), p.erros)

    def test_pbip(self):
        d = tempfile.mkdtemp(prefix='ddg')
        shutil.copytree(os.path.join(EXEMPLO, 'catalogos'), os.path.join(d, 'catalogos'))
        arq = os.path.join(d, 'argila.json')
        with open(arq, 'w', encoding='utf-8') as f:
            json.dump(self._argila(), f, ensure_ascii=False)
        self.assertEqual(_calado(_aprovar_com_prototipo, ['aprovar', arq, '--por', 'T'])[0], 0)
        saida = os.path.join(d, 'o')
        self.assertEqual(_calado(deidara.main, ['gerar', arq, '-o', saida, '--demo'])[0], 0)
        self.assertEqual(validar_pbip.conferir(saida), [])
        with open(os.path.join(saida, 'Quadro_e_Turnover.SemanticModel', 'definition', 'tables', 'Período.tmdl'),
                  encoding='utf-8') as f:
            self.assertIn('calculationGroup', f.read())
        shutil.rmtree(d, ignore_errors=True)


class TestDicaEDetalhe(unittest.TestCase):
    def _argila(self):
        a = _base()
        a['paginas'][0]['visuais'][-1]['dica'] = 'Resumo do cargo'
        a['paginas'] += [
            {'nome': 'Resumo do cargo', 'dica': True,
             'visuais': [{'tipo': 'cartao', 'medida': 'Headcount'}, {'tipo': 'cartao', 'medida': 'Remuneração Média'}]},
            {'nome': 'Cargo em detalhe', 'detalhe': 'dCargo[Cargo]',
             'visuais': [{'tipo': 'cartao', 'medida': 'Headcount'},
                         {'tipo': 'barras', 'categoria': 'dEmpresa[Empresa]', 'valores': ['Headcount']}]},
        ]
        return a

    def test_validacao(self):
        m, p = _resolver(self._argila())
        self.assertEqual(p.erros, [])
        self.assertEqual(m['paginas'][3]['detalhe']['nome'], 'Cargo')
        casos = [
            (lambda a: a['paginas'][0]['visuais'][-1].update(dica='Nada'), 'página com "dica": true'),
            (lambda a: a['paginas'][3].update(detalhe='Headcount'), '"detalhe"'),
            (lambda a: a['paginas'][2].update(ajuda=True), 'página de dica'),
        ]
        for mudar, trecho in casos:
            a = self._argila()
            mudar(a)
            _, p = _resolver(a)
            self.assertTrue(any(trecho in e for e in p.erros), (trecho, p.erros))

    def test_pbip(self):
        from tecnicas.arte.modelos import paginas_do_relatorio
        d = tempfile.mkdtemp(prefix='ddd')
        shutil.copytree(os.path.join(EXEMPLO, 'catalogos'), os.path.join(d, 'catalogos'))
        arq = os.path.join(d, 'argila.json')
        with open(arq, 'w', encoding='utf-8') as f:
            json.dump(self._argila(), f, ensure_ascii=False)
        self.assertEqual(_calado(_aprovar_com_prototipo, ['aprovar', arq, '--por', 'T'])[0], 0)
        saida = os.path.join(d, 'o')
        self.assertEqual(_calado(deidara.main, ['gerar', arq, '-o', saida, '--demo'])[0], 0)
        self.assertEqual(validar_pbip.conferir(saida), [])
        rep = os.path.join(saida, 'Quadro_e_Turnover.Report', 'definition', 'pages')
        paginas, dicas, voltar = {}, [], False
        for raiz, _, fs in os.walk(rep):
            if 'page.json' in fs:
                with open(os.path.join(raiz, 'page.json'), encoding='utf-8') as f:
                    pg = json.load(f)
                paginas[pg['displayName']] = pg
            if 'visual.json' in fs:
                with open(os.path.join(raiz, 'visual.json'), encoding='utf-8') as f:
                    v = json.load(f)['visual']
                dicas += v.get('visualContainerObjects', {}).get('visualTooltip', [])
                voltar = voltar or "'Back'" in json.dumps(v)
        dica, detalhe = paginas['Resumo do cargo'], paginas['Cargo em detalhe']
        self.assertEqual((dica['type'], dica['width'], dica['height']), ('Tooltip', 320, 240))
        self.assertEqual(detalhe['type'], 'Drillthrough')
        self.assertEqual(detalhe['filterConfig']['filters'][0]['howCreated'], 'Drillthrough')
        self.assertEqual(detalhe['pageBinding']['parameters'][0]['boundFilter'], detalhe['filterConfig']['filters'][0]['name'])
        self.assertEqual(dicas[0]['properties']['section']['expr']['Literal']['Value'], f"'{dica['name']}'")
        self.assertTrue(voltar)
        m, _ = _resolver(self._argila())
        rel = paginas_do_relatorio(m)
        self.assertEqual([x['nome'] for x in rel if not x['oculta']], ['Visão Geral', 'Turnover'])   # fora da navegação
        with open(os.path.join(d, 'argila.prototipo.html'), encoding='utf-8') as f:
            proto = f.read()
        for trecho in ('Dica · Resumo do cargo', 'Detalhe · Cargo em detalhe', 'escolha Detalhar'):
            self.assertIn(trecho, proto)
        shutil.rmtree(d, ignore_errors=True)


class TestAgruparTextos(unittest.TestCase):
    def test_temas_e_similaridade(self):
        import agrupar_textos                                        # ferramentas/ já está no caminho (test_deidara)
        d = tempfile.mkdtemp(prefix='dda')
        entrada = os.path.join(d, 'chamados.csv')
        linhas = [('Senha expirou no sistema', 'Senha resetada'), ('Esqueci a senha do email', 'Nova senha enviada'),
                  ('Impressora sem toner', 'Toner da impressora trocado'), ('Impressora offline', 'Impressora religada'),
                  ('VPN não conecta', 'VPN reinstalada'), ('Erro na VPN', 'VPN ajustada')]
        with open(entrada, 'w', encoding='utf-8', newline='') as f:
            w = csv.writer(f, delimiter=';')
            w.writerow(['Descricao', 'Resposta'])
            w.writerows(linhas)
        codigo, _ = _calado(agrupar_textos.main, [entrada, '--texto', 'Descricao', '--resposta', 'Resposta', '-k', '3'])
        self.assertEqual(codigo, 0)
        with open(os.path.join(d, 'chamados_temas.csv'), encoding='utf-8-sig', newline='') as f:
            saida = list(csv.DictReader(f, delimiter=';'))
        self.assertEqual({x['Tema'] for x in saida}, {'1', '2', '3'})
        temas = {x['Descricao']: x['Tema'] for x in saida}
        self.assertEqual(temas['Impressora sem toner'], temas['Impressora offline'])
        self.assertTrue(all(0 < float(x['Similaridade']) <= 1 for x in saida))
        self.assertEqual(_calado(agrupar_textos.main, [entrada, '--texto', 'Nada'])[0], 1)
        shutil.rmtree(d, ignore_errors=True)
