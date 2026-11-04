"""
Memory Card.

    python3 -m unittest discover -s testes
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apoio import *  # noqa: E402,F401,F403


class TestMemoryCard(unittest.TestCase):
    """Cartão do time local (sem GitHub); o Deidara grava em saves/deidara/, como o Vegapunk em saves/vegapunk/."""

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

    def test_estrutura_do_cartao_do_time(self):
        for x in ('README.md', 'CATALOGO.md'):
            self.assertTrue(os.path.exists(os.path.join(self.cartao, x)), x)      # cartão novo: raiz criada
        self.assertFalse(os.path.exists(os.path.join(self.cartao, 'deidara')))    # a seção antiga não existe mais
        self._aprovado_e_enviado()
        self.assertTrue(os.path.isdir(os.path.join(self.cartao, 'saves', 'deidara', 'recursos-humanos', 'turnover')))
        self.assertEqual((self.mc.NOME_PADRAO, self.mc.SECAO, self.mc.SOLUCAO), ('memory-card', 'deidara', 'Deidara'))
        ficha = dict(self.mc.saves(self.cartao))['recursos-humanos/turnover/quadro-e-turnover']
        for k in ('solucao', 'categoria', 'secao', 'artigo', 'versao', 'status'):    # o que o Vegapunk lê
            self.assertIn(k, ficha)

    def _cartao_do_vegapunk(self):
        """Um cartão como o do time: um save do Vegapunk e o README e o CATALOGO.md que ele gerou."""
        import subprocess
        outro = os.path.join(self.dir, 'cartao_do_time')
        save = os.path.join('saves', 'vegapunk', 'recursos-humanos', 'funcionarios', 'pessoas-acima-de-75-anos')
        os.makedirs(os.path.join(outro, save))
        ficha = {'categoria': 'Recursos Humanos', 'secao': 'Funcionários', 'artigo': 'Pessoas acima de 75 anos',
                 'descricao': 'Idade calculada', 'status': 'rascunho', 'versao': 2, 'tabelas': ['PFUNC', 'PPESSOA'],
                 'relacionados': [], 'historico': [], 'solucao': 'Vegapunk'}
        raiz = {'README.md': '# Memory Card\n(do Vegapunk)\n', 'CATALOGO.md': '# Catálogo\n',
                os.path.join(save, 'ficha.json'): json.dumps(ficha, ensure_ascii=False, indent=2) + '\n',
                os.path.join(save, 'relatorio.sql'): 'SELECT 1\n'}
        for nome, texto in raiz.items():
            with open(os.path.join(outro, nome), 'w', encoding='utf-8', newline='\n') as f:
                f.write(texto)
        for args in (['init', '-q'], ['add', '-A'], ['-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', 'outra']):
            subprocess.run(['git', '-C', outro, *args], capture_output=True)
        return outro, raiz

    def test_convive_com_o_vegapunk_no_mesmo_cartao(self):
        import subprocess
        outro, raiz = self._cartao_do_vegapunk()
        with open(os.path.join(outro, 'pendente.txt'), 'w', encoding='utf-8') as f:
            f.write('trabalho em andamento de outra solução')
        # identidade do git só para o teste (o CI não tem user.name global; sem ela o commit falhava)
        os.environ['GIT_AUTHOR_NAME'] = os.environ['GIT_COMMITTER_NAME'] = 't'
        os.environ['GIT_AUTHOR_EMAIL'] = os.environ['GIT_COMMITTER_EMAIL'] = 't@t'
        try:
            msgs = self.mc.iniciar(None, outro)
            self.assertIn('nada foi gravado', ' '.join(msgs))
            commits = subprocess.run(['git', '-C', outro, 'rev-list', '--count', 'HEAD'], capture_output=True, text=True)
            self.assertEqual(commits.stdout.strip(), '1')                           # ligar ao cartão não commita nada
            os.environ['DEIDARA_MEMORY_CARD_DIR'] = outro
            codigo, _ = self._aprovado_e_enviado()
        finally:
            for k in ('GIT_AUTHOR_NAME', 'GIT_COMMITTER_NAME', 'GIT_AUTHOR_EMAIL', 'GIT_COMMITTER_EMAIL'):
                os.environ.pop(k, None)
        self.assertEqual(codigo, 0)
        for nome, texto in raiz.items():
            if nome != 'CATALOGO.md':
                with open(os.path.join(outro, nome), encoding='utf-8') as f:
                    self.assertEqual(f.read(), texto, nome)
        with open(os.path.join(outro, 'CATALOGO.md'), encoding='utf-8') as f:
            catalogo = f.read()
        self.assertIn('## Deidara', catalogo)
        self.assertIn('## Vegapunk', catalogo)
        self.assertIn('(saves/vegapunk/recursos-humanos/funcionarios/pessoas-acima-de-75-anos/)', catalogo)
        tocados = subprocess.run(['git', '-C', outro, 'log', '--name-only', '--format=', '-n', '1'],
                                 capture_output=True, text=True).stdout.split()
        self.assertTrue(tocados and all(x.startswith('saves/deidara/') or x == 'CATALOGO.md' for x in tocados), tocados)
        status = subprocess.run(['git', '-C', outro, 'status', '--porcelain'], capture_output=True, text=True).stdout
        self.assertIn('pendente.txt', status)                                     # continua só de quem estava fazendo

    def test_catalogo_no_mesmo_formato_do_vegapunk(self):
        """O CATALOGO.md da raiz sai igual ao que o Vegapunk gera (satelites/memory_card.py, gerar_catalogo_md): quem
        enviar por último não desfaz o do outro. O texto esperado foi gerado pelo próprio Vegapunk."""
        fichas = [
            {'ref': 'vegapunk/rh/func/idosos', 'solucao': 'Vegapunk', 'categoria': 'Recursos Humanos',
             'secao': 'Funcionários', 'artigo': 'Pessoas acima de 75 anos', 'descricao': 'Idade calculada', 'versao': 2,
             'status': 'rascunho', 'tabelas': ['PFUNC', 'PPESSOA'], 'conferencia': {'ok': False}},
            {'ref': 'deidara/indicadores/turnover/turnover', 'solucao': 'Deidara', 'categoria': 'Indicadores',
             'secao': 'Turnover', 'artigo': 'Turnover', 'versao': 3, 'status': 'oficial',
             'conferencia': {'situacao': 'ok', 'ok': True}},
            {'ref': 'deidara/recursos-humanos/turnover/quadro-e-turnover', 'solucao': 'Deidara',
             'categoria': 'Recursos Humanos', 'secao': 'Turnover', 'artigo': 'Quadro e Turnover', 'descricao': 'Painel',
             'versao': 1, 'status': 'em-uso'}]
        fichas.sort(key=lambda x: (x['solucao'].lower(), x['categoria'].lower(), x['secao'].lower(), x['artigo'].lower()))
        esperado = (
            '# Catálogo\n\nGerado pelo envio. Não edite à mão.\n\n## Deidara\n\n### Indicadores\n\n#### Turnover\n\n'
            '- [Turnover](saves/deidara/indicadores/turnover/turnover/) · v3 · oficial\n\n### Recursos Humanos\n\n'
            '#### Turnover\n\n- [Quadro e Turnover](saves/deidara/recursos-humanos/turnover/quadro-e-turnover/) — Painel '
            '· v1 · em-uso\n\n## Vegapunk\n\n### Recursos Humanos\n\n#### Funcionários\n\n- [Pessoas acima de 75 anos]'
            '(saves/vegapunk/rh/func/idosos/) — Idade calculada · v2 · rascunho · **conferir: schema mudou**\n\n'
            '## Por tabela\n\n- `PFUNC`: [Pessoas acima de 75 anos](saves/vegapunk/rh/func/idosos/)\n'
            '- `PPESSOA`: [Pessoas acima de 75 anos](saves/vegapunk/rh/func/idosos/)\n\n')
        self.assertEqual(self.mc.catalogo_md(fichas), esperado)

    def test_secao_antiga_vai_para_saves_deidara(self):
        self._aprovado_e_enviado()
        base = os.path.join(self.cartao, 'saves', 'deidara')
        antiga = os.path.join(self.cartao, 'deidara', 'saves')
        os.makedirs(os.path.dirname(antiga))
        shutil.move(base, antiga)                                 # como ficava um cartão de antes do cartão do time
        arq = os.path.join(antiga, 'recursos-humanos', 'turnover', 'quadro-e-turnover', 'ficha.json')
        with open(arq, encoding='utf-8') as f:
            ficha = json.load(f)
        for k in ('solucao', 'artigo'):
            ficha.pop(k)
        with open(arq, 'w', encoding='utf-8') as f:
            json.dump(ficha, f)
        msgs = self.mc.atualizar(self.cartao)
        self.assertTrue(any('movida' in m for m in msgs), msgs)
        self.assertFalse(os.path.exists(os.path.join(self.cartao, 'deidara')))
        with open(os.path.join(base, 'recursos-humanos', 'turnover', 'quadro-e-turnover', 'ficha.json'),
                  encoding='utf-8') as f:
            ficha = json.load(f)
        self.assertEqual((ficha['solucao'], ficha['artigo']), ('Deidara', 'Quadro e Turnover'))
        self.assertEqual(self.mc.atualizar(self.cartao), [])

    def test_lembretes_como_no_vegapunk(self):
        from tecnicas import comum
        err = io.StringIO()
        with redirect_stderr(err):
            comum.lembrar_salvar_no_cartao('a.json')
            comum.lembrar_buscar_no_cartao('turnover')
        self.assertIn('ofereça salvar no Memory Card', err.getvalue())
        self.assertIn('memory-card buscar turnover', err.getvalue())
        os.environ['DEIDARA_MEMORY_CARD_DIR'] = os.path.join(self.dir, 'nao-existe')   # cartão de outra máquina
        err = io.StringIO()
        with redirect_stderr(err):
            comum.lembrar_salvar_no_cartao('a.json')
            comum.lembrar_buscar_no_cartao('turnover')
        self.assertIn('não funciona aqui', err.getvalue())
        self.assertNotIn('buscar', err.getvalue())
        os.environ['DEIDARA_MEMORY_CARD_DIR'] = '-'                                   # sem cartão: nada
        err = io.StringIO()
        with redirect_stderr(err):
            comum.lembrar_salvar_no_cartao('a.json')
        self.assertEqual(err.getvalue(), '')

    def test_enviar_pede_aprovacao_e_previa_nao_grava(self):
        codigo, out = self._enviar()
        self.assertEqual(codigo, 1)
        self.assertIn('Só painel aprovado entra no cartão', out)
        _calado(_aprovar_com_prototipo, ['aprovar', self.argila, '--por', 'Ana'])
        codigo, out = self._enviar()
        self.assertEqual(codigo, 0)
        self.assertIn('saves/deidara/recursos-humanos/turnover/quadro-e-turnover', out)
        self.assertEqual(self.mc.saves(self.cartao), [])

    def test_confirmar_grava_painel_indicadores_e_nunca_os_catalogos(self):
        codigo, _ = self._aprovado_e_enviado()
        self.assertEqual(codigo, 0)
        ref = 'recursos-humanos/turnover/quadro-e-turnover'
        save = os.path.join(self.cartao, 'saves', 'deidara', *ref.split('/'))
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
        pasta = os.path.join(d, 'saves', 'deidara', 'indicadores', 'turnover', 'turnover')
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
