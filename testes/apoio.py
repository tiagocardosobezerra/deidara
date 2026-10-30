"""
Apoio comum dos testes do Deidara sobre o exemplo fictício "Aurora" (ERP em SQL Server + planilha de metas).

    python3 -m unittest discover -s testes
"""

import copy
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

__all__ = ['copy', 'io', 'json', 'os', 'shutil', 'sys', 'tempfile', 'unittest', 'redirect_stderr', 'redirect_stdout', 'RAIZ', 'deidara', 'empacotar', 'validar_pbip', 'referencias_dax', 'resolver', 'catalogo', 'receitas', 'EXEMPLO', 'RAIZ', 'EXEMPLO', '_base', '_md', 'CATALOGOS', '_resolver', '_aprovar_com_prototipo', '_calado', '_linha', '_schema_sintetico', 'ARGILA_PEDIDOS', 'COLADO_DAX', '_catalogo_grande']


RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.environ['DEIDARA_MEMORY_CARD_DIR'] = '-'      # o cartão de quem roda os testes não interfere
sys.path.insert(0, os.path.join(RAIZ, 'ferramentas'))

import deidara  # noqa: E402
import empacotar  # noqa: E402
import validar_pbip  # noqa: E402
from kibaku_nendo.especificacao import referencias_dax, resolver  # noqa: E402
from tecnicas.luneta import catalogo  # noqa: E402
from tecnicas.luneta import receitas  # noqa: E402


EXEMPLO = os.path.join(RAIZ, 'exemplos', 'aurora')


def _base():
    with open(os.path.join(EXEMPLO, 'argila.json'), encoding='utf-8') as f:
        return json.load(f)


def _md(argila, nome):
    return next(x for x in argila['medidas'] if x['nome'] == nome)


CATALOGOS = {n: catalogo.carregar(os.path.join(EXEMPLO, 'catalogos', f'{n}.json'), n) for n in ('erp', 'metas')}


def _resolver(argila):
    return resolver(argila, CATALOGOS)


def _aprovar_com_prototipo(argv):
    """O fluxo real: o gestor vê o protótipo atual e então aprova."""
    deidara.main(['prototipar', argv[1]])
    return deidara.main(argv)


def _calado(fn, *args):
    with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()):
        codigo = fn(*args)
    return codigo, out.getvalue()


def _linha(secao, tabela, coluna='', tipo='', tamanho='', precisao='', escala='', nulo='', pk='', mae='', cmae='',
           fk='', ordem=''):
    return {'secao': secao, 'tabela': tabela, 'coluna': coluna, 'tipo': tipo, 'tamanho': str(tamanho),
            'precisao': str(precisao), 'escala': str(escala), 'nulo': str(nulo), 'pk_ordem': str(pk),
            'descricao': coluna.lower(), 'tabela_mae': mae, 'campo_mae': cmae, 'fk': fk, 'fk_ordem': str(ordem)}


def _schema_sintetico():
    """Pedidos x clientes, como se viessem da receita SQL: FK em tipos diferentes (varchar -> int),
    FK composta e colunas de borda."""
    L = _linha
    linhas = [
        L('coluna', 'PEDIDO', 'ID', 'int', 4, 10, 0, 0, 1), L('coluna', 'PEDIDO', 'CODCLI', 'varchar', 10, 0, 0, 1),
        L('coluna', 'PEDIDO', 'TAXA', 'decimal', 9, 18, 6, 1), L('coluna', 'PEDIDO', 'DATA', 'datetime', 8, 23, 3, 1),
        L('coluna', 'PEDIDO', 'HORA', 'time', 5, 16, 7, 1), L('coluna', 'PEDIDO', 'EMP', 'int', 4, 10, 0, 1),
        L('coluna', 'PEDIDO', 'LOJA', 'smallint', 2, 5, 0, 1),
        L('coluna', 'CLIENTE', 'COD', 'int', 4, 10, 0, 0, 1), L('coluna', 'CLIENTE', 'NOME', 'varchar', 60, 0, 0, 1),
        L('coluna', 'LOJA', 'EMP', 'int', 4, 10, 0, 0, 1), L('coluna', 'LOJA', 'LOJA', 'smallint', 2, 5, 0, 0, 2),
        L('coluna', 'LOJA', 'NOMELOJA', 'varchar', 60, 0, 0, 1),
        L('fk', 'PEDIDO', 'CODCLI', mae='CLIENTE', cmae='COD', fk='FK_PED_CLI', ordem=1),
        L('fk', 'PEDIDO', 'EMP', mae='LOJA', cmae='EMP', fk='FK_PED_LOJA', ordem=1),
        L('fk', 'PEDIDO', 'LOJA', mae='LOJA', cmae='LOJA', fk='FK_PED_LOJA', ordem=2),
    ]
    cat, _ = receitas.catalogo_de_sql(linhas, 'loja')
    return {'loja': catalogo.Fonte('loja', cat, '')}


ARGILA_PEDIDOS = {
    'projeto': 'Pedidos', 'tabelas': [
        {'nome': 'fPedido', 'tipo': 'fato', 'origem': 'PEDIDO', 'colunas': ['ID', 'TAXA', 'DATA', 'HORA']},
        {'nome': 'dCliente', 'tipo': 'dimensao', 'origem': 'CLIENTE', 'colunas': ['COD', 'NOME']},
        {'nome': 'dLoja', 'tipo': 'dimensao', 'origem': 'LOJA', 'colunas': ['NOMELOJA']}],
    'relacionamentos': [{'de': 'fPedido', 'para': 'dCliente'}, {'de': 'fPedido', 'para': 'dLoja'}],
    'medidas': [{'nome': 'Pedidos', 'agregacao': 'contagem_linhas', 'tabela': 'fPedido'},
                {'nome': 'Clientes', 'agregacao': 'contagem_distinta', 'coluna': 'dCliente[COD]'}],
    'paginas': [{'nome': 'P', 'visuais': [{'tipo': 'cartao', 'medida': 'Pedidos'}]}]}


COLADO_DAX = "\n".join("\t".join(l) for l in [
    ["[secao]", "[tabela]", "[coluna]", "[tipo]", "[descricao]", "[extra]", "[expressao]"],
    ["tabela", "Vendas", "", "", "Vendas do SharePoint", "", ""],
    ["tabela", "Calc", "", "", "", "calculada", ""],
    ["coluna", "Vendas", "Loja", "Int64", "", "", ""],
    ["coluna", "Vendas", "Valor", "Decimal", "Valor da venda", "", ""],
    ["coluna", "Vendas", "Data", "DateTime", "", "", ""],
    ["coluna", "Vendas", "Margem", "Double", "", "calculada", ""],
    ["coluna", "Lojas", "Loja", "Int64", "", "", ""],
    ["coluna", "Lojas", "Nome", "String", "", "", ""],
    ["relacao", "Vendas", "Loja", "Many>One", "Lojas[Loja]", "ativa", ""],
    ["particao", "Vendas", "", "4", "", "", "let⏎    Fonte = SharePoint.Tables(Site)⏎in⏎    Fonte"],
    ["particao", "Lojas", "", "4", "", "", "let⏎    Fonte = Excel.Workbook(File.Contents(Arq))⏎in⏎    Fonte"],
    ["expressao", "Site", "", "0", "", "", "\"https://x.sharepoint.com/sites/rh\" meta [IsParameterQuery=true]"],
])


def _catalogo_grande(n=600, colunas=15):
    """ERP sintético grande, como sairia da receita SQL."""
    import random
    r = random.Random(7)
    dom = ['empresa', 'filial', 'cargo', 'setor', 'cliente', 'produto', 'pedido', 'nota', 'titulo', 'conta']
    linhas = []
    for i in range(n):
        t = f'T{i:05d}'
        linhas.append(_linha('coluna', t, 'ID', 'int', 4, 10, 0, 0, 1))
        for j in range(colunas):
            o = r.choice(dom)
            linhas.append(_linha('coluna', t, f'COD{o.upper()}{j}', r.choice(['int', 'varchar', 'decimal']), 4, 10, 2, 1))
    cat, _ = receitas.catalogo_de_sql(linhas, 'erp')
    return catalogo.Fonte('erp', cat, '')
