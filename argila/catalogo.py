"""
O catálogo: a estrutura de uma fonte de dados, no formato do Deidara.

O Deidara não se conecta a nada. Ele entrega uma receita (consulta SQL, DAX
ou Power Query, ver receitas.py), a pessoa roda onde os dados já estão e
devolve o resultado; o `catalogar` transforma esse resultado num catálogo.
Do catálogo vale a regra de ouro: tabela, coluna ou ligação que não está nele
não existe para o Deidara.

Formato (um arquivo por fonte):

    {"formato": "deidara-catalogo/1", "fonte": "erp", "tipo": "sqlserver",
     "receita": "sql", "coletado_em": "27/10/2026 14:00",
     "tabelas": {"F_CARGO": {"descricao": "...", "pk": ["CODCARGO"], "expressao_m": null,
                             "colunas": [{"coluna": "CODCARGO", "familia": "inteiro", "tipo": "int",
                                          "tamanho": 4, "precisao": 10, "escala": 0, "nulo": 0,
                                          "descricao": "..."}]}},
     "fks": [{"nome": "FK_...", "origem": "constraint", "tabela_filha": "F_FUNCIONARIO",
              "tabela_mae": "F_CARGO", "colunas": [{"campo_filho": "CODCARGO", "campo_mae": "CODCARGO"}]}],
     "expressoes": {"CaminhoMetas": "\\"C:\\\\metas.xlsx\\" meta [IsParameterQuery=true, ...]"}}

`tipo`: sqlserver (tabelas do banco, lidas por views), powerbi (tabelas de um
modelo Power BI existente, lidas pela expressão Power Query dele) ou
powerquery (consultas Power Query de qualquer conector: Excel, SharePoint,
CSV, API...). Só estrutura: nenhuma linha de dado entra no catálogo.
"""

import difflib

from .util import chave, ler_json

FORMATO = 'deidara-catalogo/1'
TIPOS_FONTE = {'sqlserver', 'powerbi', 'powerquery'}
FAMILIAS = {'inteiro', 'decimal', 'real', 'data', 'datahora', 'hora', 'logico', 'texto'}


class Fonte:
    def __init__(self, nome, dados, caminho):
        self.nome, self.caminho = nome, caminho
        self.tipo = dados.get('tipo')
        self.receita = dados.get('receita', '')
        self.tabelas = {}
        for n, t in (dados.get('tabelas') or {}).items():
            self.tabelas[chave(n)] = {'nome': n, 'descricao': t.get('descricao') or '', 'pk': list(t.get('pk') or []),
                                      'expressao_m': t.get('expressao_m'),
                                      'colunas': {chave(c['coluna']): c for c in t.get('colunas') or []}}
        self.fks = list(dados.get('fks') or [])
        self.expressoes = dict(dados.get('expressoes') or {})
        self.origem = dict(dados.get('origem') or {})     # servidor, banco e esquema onde a receita SQL rodou

    def tabela(self, nome):
        return self.tabelas.get(chave(nome))

    def coluna(self, tabela, coluna):
        t = self.tabela(tabela)
        return t['colunas'].get(chave(coluna)) if t else None

    def fks_entre(self, filha, mae):
        return [fk for fk in self.fks
                if chave(fk['tabela_filha']) == chave(filha) and chave(fk['tabela_mae']) == chave(mae)]

    def parecidas(self, nome, limite=3):
        return [self.tabelas[k]['nome'] for k in
                difflib.get_close_matches(chave(nome), list(self.tabelas), n=limite, cutoff=0.6)]

    def colunas_parecidas(self, tabela, coluna, limite=3):
        t = self.tabela(tabela)
        if not t:
            return []
        return [t['colunas'][k]['coluna'] for k in
                difflib.get_close_matches(chave(coluna), list(t['colunas']), n=limite, cutoff=0.6)]


def validar(dados, caminho=''):
    """Erros de formato de um catálogo (lista vazia = ok)."""
    erros = []
    if dados.get('formato') != FORMATO:
        erros.append(f'{caminho}: não é um catálogo do Deidara (falta "formato": "{FORMATO}"); gere com `catalogar`')
        return erros
    if dados.get('tipo') not in TIPOS_FONTE:
        erros.append(f'{caminho}: tipo "{dados.get("tipo")}" inválido ({", ".join(sorted(TIPOS_FONTE))})')
    for n, t in (dados.get('tabelas') or {}).items():
        for c in t.get('colunas') or []:
            if not c.get('coluna'):
                erros.append(f'{caminho}: tabela {n} tem coluna sem nome')
            elif c.get('familia') not in FAMILIAS:
                erros.append(f'{caminho}: {n}.{c["coluna"]} com família "{c.get("familia")}" inválida')
    return erros


def carregar(caminho, nome=None):
    dados = ler_json(caminho)
    erros = validar(dados, caminho)
    if erros:
        raise ValueError('\n'.join(erros))
    return Fonte(nome or dados.get('fonte') or 'fonte', dados, caminho)
