"""
Leitura da estrutura que vem do Vegapunk.

O Deidara nunca abre a Punk Records: ele lê só a saída de
`stella.py detalhar --dominio schema --json` (um ou mais arquivos), que já
traz as colunas com descrição e tipo, a PK e as FKs com agrupamento provado.
É a mesma regra do Vegapunk: nome de tabela ou coluna que não veio daqui não
existe.
"""

from .util import chave, ler_json

ORIGENS_PROVADAS = {'constraint', 'dicionário', 'dicionario', 'ligação única + chave da mãe', 'chave da mãe'}


class Schema:
    def __init__(self):
        self.tabelas = {}        # CHAVE -> {'nome', 'descricao', 'pk', 'colunas': {CHAVE: col}}
        self.fks = []            # FKs provadas (agrupamento conhecido)
        self.sem_prova = []      # linhas de `fks_sem_constraint`
        self.arquivos = []

    # ------------------------------------------------------------------ carga
    @classmethod
    def carregar(cls, caminhos):
        s = cls()
        vistos = set()
        for caminho in caminhos:
            dados = ler_json(caminho)
            if 'tabelas' not in dados:
                raise ValueError(f'{caminho}: não parece saída de `stella.py detalhar --json` (falta "tabelas").')
            s.arquivos.append(caminho)
            for nome, t in dados['tabelas'].items():
                cols = {}
                descricao = (t.get('metadados') or {}).get('descricao')
                for c in t.get('colunas', []):
                    if c.get('coluna') == '#':          # a descrição da tabela vem como coluna '#'
                        descricao = descricao or c.get('descricao')
                        continue
                    cols[chave(c['coluna'])] = c
                s.tabelas[chave(nome)] = {'nome': nome, 'descricao': descricao,
                                          'pk': list((t.get('metadados') or {}).get('pk') or []),
                                          'colunas': cols}
                for fk in t.get('fks', []):
                    k = (chave(fk['tabela_filha']), chave(fk['tabela_mae']),
                         tuple((chave(x['campo_filho']), chave(x['campo_mae'])) for x in fk['colunas']))
                    if k not in vistos:
                        vistos.add(k)
                        s.fks.append(fk)
                for linha in t.get('fks_sem_constraint', []):
                    s.sem_prova.append(linha)
        return s

    # --------------------------------------------------------------- consulta
    def tabela(self, nome):
        return self.tabelas.get(chave(nome))

    def coluna(self, tabela, coluna):
        t = self.tabela(tabela)
        return t['colunas'].get(chave(coluna)) if t else None

    def fks_entre(self, filha, mae):
        return [fk for fk in self.fks
                if chave(fk['tabela_filha']) == chave(filha) and chave(fk['tabela_mae']) == chave(mae)]

    def sem_prova_entre(self, filha, mae):
        return [l for l in self.sem_prova
                if chave(l.get('tabela_filha')) == chave(filha) and chave(l.get('tabela_mae')) == chave(mae)]

    def parecidas(self, nome, limite=3):
        """Sugestões para um nome que não existe (só entre o que veio do Vegapunk)."""
        import difflib
        return difflib.get_close_matches(chave(nome), list(self.tabelas), n=limite, cutoff=0.6)

    def colunas_parecidas(self, tabela, coluna, limite=3):
        import difflib
        t = self.tabela(tabela)
        if not t:
            return []
        return [t['colunas'][k]['coluna'] for k in
                difflib.get_close_matches(chave(coluna), list(t['colunas']), n=limite, cutoff=0.6)]
