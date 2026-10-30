"""
O Deidara de ponta a ponta: começo, fluxo pela linha de comando e empacotamento.

    python3 -m unittest discover -s testes
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apoio import *  # noqa: E402,F401,F403


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
                            {x.get('meta') for x in a['medidas']}
                            and not str(m.get('tipo', '')).startswith(('svg_', 'ano_anterior', 'leitura', 'impacto'))))
        # as que o C2 deriva de um indicador já trazem a descrição (não pedem definição de negócio)
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
