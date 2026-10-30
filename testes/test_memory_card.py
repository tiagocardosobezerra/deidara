"""
Memory Card.

    python3 -m unittest discover -s testes
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apoio import *  # noqa: E402,F401,F403


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


class TestCartaoNoEsboco(unittest.TestCase):
    """Indicador oficial do Memory Card entra no esboço com a mesma definição e fórmula."""

    def _cartao(self, status):
        d = tempfile.mkdtemp(prefix='ddmc')
        pasta = os.path.join(d, 'deidara', 'saves', 'indicadores', 'turnover', 'turnover')
        os.makedirs(pasta)
        esp = {'nome': 'Turnover', 'tipo': 'divisao', 'numerador': 'Desligamentos', 'denominador': 'Headcount',
               'formato': 'percentual', 'polaridade': 'menor_melhor', 'descricao': 'Definição oficial do time.'}
        with open(os.path.join(pasta, 'ficha.json'), 'w', encoding='utf-8') as f:
            json.dump({'tipo': 'indicador', 'nome': 'Turnover', 'status': status, 'versao': 3, 'especificacao': esp}, f)
        return d

    def test_oficial_substitui_o_que_o_esboco_escreveria(self):
        from tecnicas import memory_card, te_no_kuchi
        d = self._cartao('oficial')
        argila, notas = te_no_kuchi.esbocar(CATALOGOS, 'turnover por cargo', do_cartao=memory_card.indicadores(d))
        tv = next(x for x in argila['medidas'] if x['nome'] == 'Turnover')
        self.assertEqual(tv['descricao'], 'Definição oficial do time.')
        self.assertEqual(tv['denominador'], 'Headcount')
        self.assertTrue(any('veio do Memory Card (oficial' in n for n in notas), notas)
        shutil.rmtree(d, ignore_errors=True)

    def test_rascunho_nao_entra(self):
        from tecnicas import memory_card, te_no_kuchi
        d = self._cartao('rascunho')
        argila, notas = te_no_kuchi.esbocar(CATALOGOS, 'turnover por cargo', do_cartao=memory_card.indicadores(d))
        tv = next(x for x in argila['medidas'] if x['nome'] == 'Turnover')
        self.assertNotEqual(tv.get('descricao'), 'Definição oficial do time.')
        shutil.rmtree(d, ignore_errors=True)
