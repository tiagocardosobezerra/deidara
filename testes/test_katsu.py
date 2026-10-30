"""
Katsu: o retrato aprovado e a diferença entre versões.

    python3 -m unittest discover -s testes
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apoio import *  # noqa: E402,F401,F403


class TestGovernanca(unittest.TestCase):
    def test_rls_gera_papel(self):
        from tecnicas.c3 import tmdl
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
        from tecnicas.c3 import pbir

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
