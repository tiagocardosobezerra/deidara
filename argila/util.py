"""
Utilidades comuns: nomes (TMDL, DAX, T-SQL), tipos, formatos e hashes.

Tudo determinístico: o mesmo argila.json gera sempre os mesmos arquivos
(lineageTag e nomes de visual vêm de uuid5/sha1 do caminho do objeto), para
que o diff entre duas gerações mostre só o que mudou de verdade.
"""

import hashlib
import json
import os
import re
import unicodedata
import uuid

NAMESPACE = uuid.UUID('6d1f3c2e-9a4b-5c7d-8e0f-de1da7a0c1a7')

# Tipo base do SQL Server (catálogo da receita sql) -> família.
_FAMILIA_SQL = {
    'int': 'inteiro', 'bigint': 'inteiro', 'smallint': 'inteiro', 'tinyint': 'inteiro',
    'decimal': 'decimal', 'numeric': 'decimal', 'money': 'decimal', 'smallmoney': 'decimal',
    'float': 'real', 'real': 'real',
    'date': 'data', 'datetime': 'datahora', 'datetime2': 'datahora', 'smalldatetime': 'datahora',
    'datetimeoffset': 'datahora', 'time': 'hora',
    'bit': 'logico',
    'char': 'texto', 'varchar': 'texto', 'nchar': 'texto', 'nvarchar': 'texto', 'text': 'texto',
    'ntext': 'texto', 'uniqueidentifier': 'texto', 'xml': 'texto', 'sysname': 'texto',
}

# Família -> dataType do TMDL.
_TIPO_TMDL = {
    'inteiro': 'int64', 'decimal': 'decimal', 'real': 'double', 'data': 'dateTime',
    'datahora': 'dateTime', 'hora': 'dateTime', 'logico': 'boolean', 'texto': 'string',
}

NUMERICAS = {'inteiro', 'decimal', 'real'}

# Família -> tipo SQL Server (CAST na view quando a mãe vem de outra fonte).
SQL_POR_FAMILIA = {
    'inteiro': 'bigint', 'decimal': 'decimal(19,4)', 'real': 'float', 'data': 'date', 'datahora': 'datetime2',
    'hora': 'time', 'logico': 'bit', 'texto': 'nvarchar(4000)',
}

# Família -> tipo do Power Query (Table.TransformColumnTypes).
M_POR_FAMILIA = {
    'inteiro': 'Int64.Type', 'decimal': 'Currency.Type', 'real': 'type number', 'data': 'type date',
    'datahora': 'type datetime', 'hora': 'type time', 'logico': 'type logical', 'texto': 'type text',
}

# Formato amigável do argila.json -> formatString do Power BI (cultura pt-BR
# troca os separadores sozinha) e exemplo para o protótipo.
FORMATOS = {
    'inteiro': '#,0',
    'decimal': '#,0.00',
    'moeda': '"R$"\\ #,0.00;-"R$"\\ #,0.00;"R$"\\ #,0.00',
    'percentual': '0.0%',
    'data': 'Short Date',
    'hora': 'Long Time',
}


def familia_sql(tipo):
    return _FAMILIA_SQL.get((tipo or '').strip().lower())


def familia_da_coluna(oc):
    """Família de uma coluna do catálogo SQL. decimal com mais de 4 casas vira
    real (double): o decimal do Power BI é fixo em 4 casas e truncaria."""
    f = familia_sql(oc.get('tipo'))
    if f == 'decimal' and (oc.get('escala') or 0) > 4:
        return 'real'
    return f


def sql_tipo(oc):
    """Tipo SQL completo de uma coluna do catálogo SQL (para CAST), ou None."""
    t = (oc.get('tipo') or '').lower()
    if not t:
        return None
    if t in ('decimal', 'numeric'):
        return f'{t}({oc.get("precisao") or 18},{oc.get("escala") or 0})'
    if t in ('varchar', 'char', 'varbinary', 'binary', 'nvarchar', 'nchar'):
        n = oc.get('tamanho')
        if t.startswith('n') and n and n != -1 and n > 4000:
            n = -1
        return f'{t}({"max" if n == -1 else n or 50})'
    return t


def tipo_tmdl(familia):
    return _TIPO_TMDL.get(familia, 'string')


def sem_acento(texto):
    return ''.join(c for c in unicodedata.normalize('NFKD', texto) if not unicodedata.combining(c))


def chave(texto):
    """Comparação de nomes sem caixa e sem acento."""
    return sem_acento(texto or '').strip().lower()


def ident(texto, prefixo=''):
    """Identificador simples [A-Za-z0-9_] a partir de um nome amigável."""
    s = re.sub(r'[^A-Za-z0-9]+', '_', sem_acento(texto)).strip('_')
    if not s or s[0].isdigit():
        s = (prefixo or 'x') + '_' + s
    return s


def tmdl_nome(nome):
    """Nome de objeto no TMDL: aspas simples quando não é um identificador simples."""
    if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', nome):
        return nome
    return "'" + nome.replace("'", "''") + "'"


def dax_tabela(nome):
    if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', nome):
        return nome
    return "'" + nome.replace("'", "''") + "'"


def dax_coluna(tabela, coluna):
    return f"{dax_tabela(tabela)}[{coluna.replace(']', ']]')}]"


def dax_medida(nome):
    return f"[{nome.replace(']', ']]')}]"


def sql_nome(nome):
    return '[' + nome.replace(']', ']]') + ']'


def sql_texto(texto):
    return "N'" + texto.replace("'", "''") + "'"


def m_texto(texto):
    return '"' + texto.replace('"', '""') + '"'


def guid(*partes):
    return str(uuid.uuid5(NAMESPACE, '/'.join(partes)))


def curto(*partes):
    """Nome curto e estável (20 hex) para página e visual do PBIR."""
    return hashlib.sha1('/'.join(partes).encode('utf-8')).hexdigest()[:20]


def sha256_arquivo(caminho):
    with open(caminho, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


class ErroDeUso(Exception):
    """Erro de quem usa (arquivo ausente, JSON quebrado): vira mensagem, nunca traceback."""


def ler_json(caminho):
    if not os.path.exists(caminho):
        raise ErroDeUso(f'arquivo não encontrado: {caminho}')
    with open(caminho, encoding='utf-8-sig') as f:
        texto = f.read()
    try:
        return json.loads(texto)
    except json.JSONDecodeError as e:
        linhas = texto.splitlines()
        trecho = linhas[e.lineno - 1] if 0 < e.lineno <= len(linhas) else ''
        anterior = linhas[e.lineno - 2] if e.lineno > 1 else ''
        dica = ''
        if trecho.strip().startswith(('}', ']')) and anterior.rstrip().endswith(','):
            dica = ' (provável vírgula sobrando no fim da linha anterior)'
        elif 'Expecting \',\' delimiter' in e.msg:
            dica = ' (provável vírgula faltando entre dois itens)'
        raise ErroDeUso(f'{caminho}: JSON inválido na linha {e.lineno}, coluna {e.colno}{dica}.\n'
                        f'    {e.lineno - 1}: {anterior}\n  > {e.lineno}: {trecho}') from None


def gravar_json(caminho, obj):
    with open(caminho, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')


def gravar_texto(caminho, texto, bom=False):
    with open(caminho, 'w', encoding='utf-8-sig' if bom else 'utf-8', newline='\n') as f:
        f.write(texto)


def numero_br(valor, casas=0):
    """1234567.891 -> '1.234.567,89' (saída sempre em pt-BR)."""
    s = f'{valor:,.{casas}f}'
    return s.replace(',', '§').replace('.', ',').replace('§', '.')
