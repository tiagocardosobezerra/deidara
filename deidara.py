#!/usr/bin/env python3
"""
================================================================================
 DEIDARA — do schema ao painel: protótipo primeiro, Power BI depois
================================================================================
"Arte é uma explosão!" O Deidara molda a argila (a especificação do painel),
mostra a escultura (o protótipo) e, só depois do "sim" do usuário, detona
(gera o projeto Power BI completo).

Fluxo:
    receita     a consulta (SQL, DAX ou Power Query) que a pessoa roda onde os
                dados estão; devolve só estrutura, nunca linhas de dado
    catalogar   transforma o resultado colado num catálogo da fonte
    buscar      acha as tabelas de um pedido em todos os catálogos
    relacionar  sugere as ligações que faltam, com a evidência de cada uma
    provar      lê o resultado da receita de prova (percentuais, nunca linhas)
    memory-card a seção deidara/ do cartão de memória do time (repositório memory-card):
                iniciar, catalogo, buscar, enviar, marcar, conferir
    validar     confere o argila.json contra os catálogos (nunca adivinha nome)
    prototipar  protótipo navegável em HTML, com números fictícios
    aprovar     grava o "sim" do usuário (hash do argila.json + do schema)
    gerar       .pbip (TMDL + PBIR) + views SQL + conferência + documentação

Uso:
    python3 deidara.py receita   sql [--esquema dbo] [--tabelas T1,T2] | dax | m [--consultas C1,C2] [-o ARQ]
    python3 deidara.py catalogar --de RESULTADO.txt --fonte NOME [--m PASTA_DOS_.m] [-o catalogo.json]
    python3 deidara.py buscar    "<pedido>" (--argila argila.json | --catalogos A.json B.json)
    python3 deidara.py relacionar (--argila argila.json | --catalogos A.json B.json [--tabelas T1,T2])
    python3 deidara.py receita   prova --argila argila.json --de "Tabela[COLUNA]" --para "Tabela[COLUNA]"
    python3 deidara.py provar    --de RESULTADO.txt [--argila argila.json]
    python3 deidara.py confirmar argila.json --ligacao DE->PARA --por NOME [--motivo M] | --remover
    python3 deidara.py memory-card iniciar --repo DONO/memory-card [--pasta DIR] [--publico]
    python3 deidara.py memory-card buscar TERMO [TERMO ...]
    python3 deidara.py memory-card enviar argila.json --categoria C --secao S [--artigo A] [--texto ARQ.md]
                                          [--motivo M] [--relacionado REF] [--status S] [--confirmar]
    python3 deidara.py memory-card marcar REF --status rascunho|em-uso|oficial [--motivo M]
    python3 deidara.py memory-card conferir [REF ...] --catalogos A.json B.json [--registrar]
    python3 deidara.py validar   argila.json [--json]
    python3 deidara.py prototipar argila.json [-o prototipo.html]
    python3 deidara.py aprovar   argila.json --por NOME [--observacao TEXTO]
    python3 deidara.py gerar     argila.json [-o PASTA]
    python3 deidara.py diff      argila.json [--contra OUTRO.json]
    python3 deidara.py funcoes   buscar "acumulado" | ver SAMEPERIODLASTYEAR [--linguagem dax|m]
    python3 deidara.py padroes   [turnover | taxa | estoque | ...]
    python3 deidara.py visuais   [meta | ranking | causa | status | ...]
    python3 deidara.py status

O argila.json lista as fontes em "fontes" ({"erp": {"catalogo": "catalogos/erp.json"}}),
com caminhos relativos a ele. Formato completo: referencias/argila.md.
================================================================================
"""

import argparse
import datetime
import json
import os
import re
import shutil
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)

from argila import (VERSAO, catalogo, descoberta, dicionario, docs, esboco, governanca, memory_card,  # noqa: E402
                    pbir, prova, prototipo, receitas, relato, sql, tmdl)
from argila.especificacao import resolver  # noqa: E402
from argila.util import ErroDeUso, gravar_json, gravar_texto, ident, ler_json, sha256_arquivo  # noqa: E402


# pasta do projeto + nome + o arquivo mais fundo do .pbip (visual.json de uma página)
LONGEST_RELATIVO = len('/.Report/definition/pages/0123456789abcdef0123/visuals/0123456789abcdef0123/visual.json')


def _lembrete(texto):
    print(f'LEMBRETE: {texto}', file=sys.stderr)


# ------------------------------------------------------------------- carga
def _carregar(caminho_argila):
    argila = ler_json(caminho_argila)
    base = os.path.dirname(os.path.abspath(caminho_argila))
    fontes = argila.get('fontes') or {}
    if not fontes:
        raise SystemExit('argila.json sem "fontes": rode uma receita (`deidara.py receita`), o `catalogar` e aponte '
                         'o catálogo, ex.: "fontes": {"erp": {"catalogo": "catalogos/erp.json"}}')
    catalogos, caminhos = {}, []
    for nome, cfg in fontes.items():
        if not (cfg or {}).get('catalogo'):
            raise SystemExit(f'fonte {nome} sem "catalogo"')
        c = os.path.join(base, cfg['catalogo'])
        if not os.path.exists(c):
            raise SystemExit(f'catálogo da fonte {nome} não encontrado: {c}')
        try:
            catalogos[nome] = catalogo.carregar(c, nome)
        except ValueError as e:
            raise SystemExit(str(e))
        caminhos.append(c)
    modelo, problemas = resolver(argila, catalogos)
    cartao = memory_card.configuracao().get('pasta')
    if cartao:
        problemas.avisos += memory_card.avisos_do_modelo(cartao, modelo)
    return argila, catalogos, modelo, problemas, caminhos


def _relatorio(problemas, modelo=None, caminho='argila.json'):
    if modelo is not None:
        print(relato.validacao(modelo, problemas, caminho))
        return
    for e in problemas.erros:
        print(f'  ERRO   {e}')
    for a in problemas.avisos:
        print(f'  AVISO  {a}')


def _hashes(caminho_argila, caminhos_schema):
    return {'argila_sha256': sha256_arquivo(caminho_argila),
            'catalogos_sha256': {os.path.basename(c): sha256_arquivo(c) for c in caminhos_schema}}


def _arquivo_aprovacao(caminho_argila):
    raiz, _ = os.path.splitext(caminho_argila)
    return raiz + '.aprovacao.json'


# ---------------------------------------------------------------- comandos
def _catalogos(a):
    """Catálogos (e o modelo, se veio o argila.json) para buscar/relacionar/provar."""
    if getattr(a, 'argila', None):
        _, cats, modelo, _, _ = _carregar(a.argila)
        return cats, modelo
    if not getattr(a, 'catalogos', None):
        raise SystemExit('informe --argila argila.json ou --catalogos A.json B.json')
    cats = {}
    for c in a.catalogos:
        try:
            f = catalogo.carregar(c)
        except ValueError as e:
            raise SystemExit(str(e))
        cats[f.nome] = f
    return cats, None


def _ponta(cats, modelo, ref):
    """'Tabela[COLUNA]' (nome no modelo ou origem no catálogo) -> dados da ponta para a receita de prova."""
    import re as _re
    mt = _re.fullmatch(r"\s*'?(.+?)'?\[(.+)\]\s*", ref or '')
    if not mt:
        raise SystemExit(f'"{ref}": use Tabela[COLUNA]')
    tab, col = mt.group(1), mt.group(2)
    cand = []
    if modelo:
        cand = [(t['fonte'], t['origem']) for t in modelo['tabelas']
                if t.get('origem') and (t['nome'].upper() == tab.upper() or t['origem'].upper() == tab.upper())]
    cand += [(n, f.tabela(tab)['nome']) for n, f in cats.items() if f.tabela(tab)]
    if not cand:
        raise SystemExit(f'tabela "{tab}" não está no modelo nem nos catálogos')
    fonte, origem = cand[0]
    oc = cats[fonte].coluna(origem, col)
    if not oc and modelo:                                   # nome da coluna no modelo -> coluna da fonte
        t = next((x for x in modelo['tabelas'] if x.get('origem') == origem and x['fonte'] == fonte), None)
        c = next((c for c in (t or {}).get('colunas', []) if c['nome'].upper() == col.upper() and c['origem']), None)
        if c:
            oc = cats[fonte].coluna(origem, c['origem'])
    if not oc:
        sug = cats[fonte].colunas_parecidas(origem, col)
        raise SystemExit(f'coluna "{col}" não existe em {origem} (fonte {fonte})' + (f'; parecidas: {", ".join(sug)}' if sug else ''))
    cfg = (modelo or {}).get('fontes', {}).get(fonte, {})
    return {'fonte': fonte, 'tipo': cats[fonte].tipo, 'origem': origem, 'coluna': oc['coluna'],
            'rotulo': f'{tab}[{oc["coluna"]}]', 'servidor': cfg.get('servidor', 'SEU_SERVIDOR'),
            'banco': cfg.get('banco', 'SEU_BANCO'), 'esquema': cfg.get('esquema_origem', 'dbo')}


def cmd_receita(a):
    if a.tipo == 'prova':
        cats, modelo = _catalogos(a)
        de, para = _ponta(cats, modelo, a.de), _ponta(cats, modelo, a.para)
        if de['fonte'] == para['fonte'] and de['tipo'] == 'sqlserver':
            texto = prova.receita_sql((de['origem'], de['coluna'], de['rotulo']), (para['origem'], para['coluna'], para['rotulo']),
                                      de['esquema'], para['esquema'])
        else:
            texto = prova.receita_m(de, para)
        if a.saida:
            gravar_texto(a.saida, texto, bom=texto.startswith('/*'))
            print(f'Receita de prova em {a.saida}')
        else:
            print(texto)
        _lembrete('esta receita conta (percentuais e sim/não, nenhuma linha). Com o resultado colado: '
                  f'`deidara.py provar --de resultado.txt --argila {a.argila or "argila.json"}` (grava a prova na ligação).')
        return 0
    if a.tipo == 'sql':
        texto = receitas.receita_sql(a.esquema, [t.strip() for t in (a.tabelas or '').split(',') if t.strip()])
    elif a.tipo == 'dax':
        texto = receitas.receita_dax()
    elif a.tipo == 'funcoes-dax':
        texto = receitas.receita_funcoes_dax()
    elif a.tipo == 'funcoes-m':
        texto = receitas.receita_funcoes_m()
    else:
        texto = receitas.receita_m([c.strip() for c in (a.consultas or '').split(',') if c.strip()])
    if a.saida:
        gravar_texto(a.saida, texto, bom=a.tipo == 'sql')
        print(f'Receita {a.tipo} em {a.saida}')
    else:
        print(texto)
    _lembrete('a pessoa roda a receita onde os dados estão, copia a grade com o cabeçalho para um .txt e você roda '
              '`deidara.py catalogar --de ARQUIVO.txt --fonte NOME`. Nada de dado sai: só estrutura.')
    return 0


def cmd_catalogar(a):
    if a.funcoes:
        try:
            d = receitas.dicionario_local(a.de, a.funcoes)
        except ValueError as e:
            print(str(e))
            return 1
        pasta = os.path.join(dicionario.PASTA, 'local')
        os.makedirs(pasta, exist_ok=True)
        gravar_json(os.path.join(pasta, f'{a.funcoes}.json'), d)
        novas = [n for n in d['funcoes'] if n not in dicionario.funcoes(a.funcoes)]
        print(f'Dicionário local {a.funcoes}: {len(d["funcoes"])} função(ões), {len(novas)} que o Deidara não conhecia'
              + (f' (ex.: {", ".join(novas[:5])})' if novas else ''))
        return 0
    if not a.fonte:
        print('informe --fonte (ou --funcoes dax|m para o dicionário de funções)')
        return 1
    try:
        cat, avisos = receitas.catalogar(a.de, a.fonte, a.m)
    except ValueError as e:
        print(str(e))
        return 1
    pasta_de = os.path.dirname(os.path.abspath(a.de))
    pasta_cat = os.path.join(os.path.dirname(pasta_de), 'catalogos')
    if not a.saida and os.path.basename(pasta_de) == 'colado' and os.path.isdir(pasta_cat):
        saida = os.path.join(pasta_cat, f'{a.fonte}.json')          # pasta criada pelo `novo`
    else:
        saida = a.saida or os.path.join(pasta_de, f'{a.fonte}.catalogo.json')
    gravar_json(saida, cat)
    ncol = sum(len(t['colunas']) for t in cat['tabelas'].values())
    print(f'Fonte {a.fonte} ({cat["tipo"]}, receita {cat["receita"]}): {len(cat["tabelas"])} tabela(s), {ncol} coluna(s), '
          f'{len(cat["fks"])} ligação(ões), {len(cat["expressoes"])} expressão(ões) auxiliar(es)')
    for x in avisos:
        print(f'  AVISO  {x}')
    print(f'Catálogo: {saida}')
    if os.path.basename(os.path.dirname(os.path.abspath(saida))) == 'catalogos':
        print(f'Próximo passo: `deidara.py esbocar {os.path.dirname(os.path.dirname(os.path.abspath(saida)))} --pedido "..."` '
              '(ou, se o argila.json já existe, aponte este catálogo em "fontes")')
    else:
        _lembrete(f'aponte no argila.json: "fontes": {{"{a.fonte}": {{"catalogo": "<caminho relativo de '
                  f'{os.path.basename(saida)}>"}}}}')
    return 0


ROTEIRO = """# {projeto} — roteiro

Pasta criada pelo Deidara em {data}. Rode os comandos da pasta da skill.

## 1. Briefing (as respostas do gestor)

Preencha `painel.json` → `"briefing"` com as palavras do gestor, antes do esboço:

- `decisao`: que decisão o painel apoia; `publico`: quem abre.
- `indicadores`: um por indicador, com `nome`, `definicao` (o que conta, o que divide, que filtro, que período),
  `polaridade` (`maior_melhor` ou `menor_melhor`) e `meta` (número, ou o nome da meta que vem de uma fonte).
- `cortes`: por onde abrir os números (cargo, empresa, mês...).
- `fontes`: de onde vem cada dado (banco, modelo Power BI, planilha) — decide a receita do passo 2.

O esboço usa tudo isso: sai com as definições, a polaridade e a meta, e o protótipo já tem o que o gestor pediu.

## 2. Estrutura das fontes (só estrutura, nenhum dado)

Mande a receita certa para quem tem acesso a cada fonte (estão em `receitas/`):

| Onde está o dado | Receita | Onde rodar |
|---|---|---|
| Banco SQL Server | `receitas/receita_sql.sql` (ajuste `@tabelas`) | SSMS |
| Modelo Power BI que já existe | `receitas/receita_dax.dax` | Power BI Desktop, Exibição de consulta DAX |
| Excel, SharePoint, CSV, API | `receitas/receita_m.pq` (ajuste a lista de consultas) | Power Query, consulta nula |

Cole cada resultado em `colado/<fonte>.txt` (e, na receita M, o texto de cada consulta em `colado/m/<Nome>.m`). Depois:

```
python deidara.py catalogar --de {pasta}/colado/erp.txt --fonte erp -o {pasta}/catalogos/erp.json
python deidara.py catalogar --de {pasta}/colado/metas.txt --fonte metas --m {pasta}/colado/m -o {pasta}/catalogos/metas.json
```

A receita SQL devolve também o servidor e o banco em que rodou: o esboço já os põe em "fontes".

## 3. Esboço, validação e protótipo

```
python deidara.py esbocar {pasta}
python deidara.py validar {pasta}/argila.json
python deidara.py prototipar {pasta}/argila.json
```

Sem briefing, diga o assunto: `esbocar {pasta} --pedido "<o que o painel precisa mostrar>"`. Indicador com padrão
(`python deidara.py padroes <assunto>`, ex.: turnover) entra com a cadeia inteira. O esboço marca o que precisa de
gente: ligação "A CONFIRMAR" (o protótipo já sai, com ela nas pendências) e indicador "A DEFINIR".

## 4. Confirmação, aprovação e entrega

```
python deidara.py confirmar {pasta}/argila.json --ligacao "DE->PARA" --por "<quem confirmou>"
python deidara.py aprovar {pasta}/argila.json --por "<quem aprovou>"
python deidara.py gerar {pasta}/argila.json -o C:/paineis/<nome>
python deidara.py memory-card enviar {pasta}/argila.json --categoria "<área>" --secao "<assunto>"
```

A qualquer momento: `python deidara.py situacao {pasta}/argila.json`
"""


BRIEFING = {                            # o que o gestor responde no passo 1 (ver ROTEIRO.md); o esbocar lê
    'decisao': '', 'publico': '',
    'indicadores': [{'nome': '', 'definicao': '', 'polaridade': '', 'meta': None}],
    'cortes': [], 'fontes': {},
}


def cmd_novo(a):
    import datetime as _dt
    if os.path.exists(a.pasta) and os.listdir(a.pasta):
        print(f'{a.pasta} já existe e não está vazia: escolha outra pasta')
        return 1
    for d in ('catalogos', 'colado', os.path.join('colado', 'm'), 'receitas'):
        os.makedirs(os.path.join(a.pasta, d), exist_ok=True)
    gravar_texto(os.path.join(a.pasta, 'receitas', 'receita_sql.sql'), receitas.receita_sql('dbo', []), bom=True)
    gravar_texto(os.path.join(a.pasta, 'receitas', 'receita_dax.dax'), receitas.receita_dax())
    gravar_texto(os.path.join(a.pasta, 'receitas', 'receita_m.pq'), receitas.receita_m([]))
    projeto = a.projeto or os.path.basename(os.path.abspath(a.pasta))
    gravar_json(os.path.join(a.pasta, 'painel.json'), {'projeto': projeto, 'briefing': BRIEFING})
    gravar_texto(os.path.join(a.pasta, 'ROTEIRO.md'), ROTEIRO.format(
        projeto=projeto, pasta=a.pasta.replace(os.sep, '/'), data=_dt.datetime.now().strftime('%d/%m/%Y')))
    print(f'Pasta do painel criada: {a.pasta}')
    print('  receitas/   as três receitas, prontas para mandar a quem tem acesso às fontes')
    print('  colado/     onde vão os resultados colados')
    print('  catalogos/  onde o `catalogar` grava')
    print(f'  ROTEIRO.md  o passo a passo deste painel')
    print(f'  painel.json o briefing: as respostas do gestor (indicadores, definição, meta, cortes)')
    print(f'Próximo passo: preencha o briefing e mande a receita de cada fonte '
          f'(ver {os.path.normpath(os.path.join(a.pasta, "ROTEIRO.md"))}).')
    return 0


def cmd_esbocar(a):
    if os.path.isdir(a.alvo):
        pasta = a.alvo
        dcat = os.path.join(pasta, 'catalogos')
        arquivos = sorted(os.path.join(dcat, x) for x in os.listdir(dcat) if x.endswith('.json')) if os.path.isdir(dcat) else []
        saida = os.path.normpath(a.saida or os.path.join(pasta, 'argila.json'))
    else:
        pasta, arquivos = os.path.dirname(os.path.abspath(a.saida or 'argila.json')), [a.alvo] + (a.catalogos or [])
        saida = a.saida or 'argila.json'
    if not arquivos:
        print('Nenhum catálogo: rode a receita e o `catalogar` antes (ver ROTEIRO.md).')
        return 1
    if os.path.exists(saida) and not a.forcar:
        print(f'{saida} já existe: o esboço não sobrescreve trabalho (use --forcar ou -o outro.json)')
        return 1
    cats, caminhos = {}, {}
    for c in arquivos:
        f = catalogo.carregar(c)
        cats[f.nome], caminhos[f.nome] = f, c
    tabelas = None
    if a.tabelas:
        tabelas = []
        for x in a.tabelas.split(','):
            fonte, _, tab = x.strip().rpartition(':')
            tabelas.append((fonte or next(iter(cats)), tab))
    projeto, briefing = a.projeto, {}
    if os.path.isdir(a.alvo) and os.path.exists(os.path.join(a.alvo, 'painel.json')):
        painel = ler_json(os.path.join(a.alvo, 'painel.json'))
        projeto = projeto or painel.get('projeto')
        briefing = painel.get('briefing') or {}
    try:
        argila, notas = esboco.esbocar(cats, a.pedido, projeto, tabelas, briefing=briefing)
    except ValueError as e:
        print(str(e))
        return 1
    base = os.path.dirname(os.path.abspath(saida))
    sem_origem = []
    for nome, f in cats.items():
        cfg = {'catalogo': os.path.relpath(os.path.abspath(caminhos[nome]), base).replace(os.sep, '/')}
        if f.tipo == 'sqlserver':                  # a receita SQL nova traz onde rodou; a antiga, não
            cfg.update({'servidor': f.origem.get('servidor') or 'SEU_SERVIDOR', 'banco': f.origem.get('banco') or 'SEU_BANCO',
                        'esquema_origem': f.origem.get('esquema') or 'dbo', 'esquema_views': 'bi'})
            if not f.origem.get('servidor'):
                sem_origem.append(nome)
        argila['fontes'][nome] = cfg
    usadas = {t['fonte'] for t in argila['tabelas']}
    argila['fontes'] = {n: c for n, c in argila['fontes'].items() if n in usadas}
    gravar_json(saida, argila)
    print(f'Esboço em {saida}: {len(argila["tabelas"])} tabela(s)' + (' + calendário' if argila.get('calendario') else '')
          + f', {len(argila["relacionamentos"])} ligação(ões), '
          f'{len(argila["medidas"])} medida(s), 1 página')
    for n in notas:
        print(f'  · {n}')
    if sem_origem:
        print(f'  · troque SEU_SERVIDOR / SEU_BANCO em "fontes" ({", ".join(sem_origem)}; valores iniciais dos parâmetros '
              'do Power BI) ou rode a receita SQL nova, que já devolve o servidor e o banco')
    if not any((i.get('nome') or '').strip() for i in briefing.get('indicadores') or []):
        print('  · sem briefing no painel.json: as definições ficaram "A DEFINIR" (preencha o briefing com as respostas '
              'do gestor e rode de novo com --forcar)')
    print(f'Próximo passo: `deidara.py validar {saida}` e ajuste o esboço com o usuário; com ligação "A CONFIRMAR", '
          'o protótipo já sai (a ligação fica nas pendências) para o gestor reagir cedo.')
    return 0


def cmd_buscar(a):
    cats, _ = _catalogos(a)
    achados = descoberta.buscar(cats, a.pedido, a.limite)
    if not achados:
        print('Nada encontrado. Tente palavras do negócio mais gerais, ou acrescente sinônimos em dicionario/sinonimos.json.')
        return 0
    for i, r in enumerate(achados, 1):
        print(f'{i:>2}. {r["fonte"]} · {r["tabela"]}  (pontos {str(r["pontos"]).replace(".", ",")})'
              + (f' — {r["descricao"]}' if r['descricao'] else ''))
        if r['colunas']:
            print(f'      colunas: {", ".join(r["colunas"][:8])}')
    _lembrete('confirme com o usuário as tabelas antes de montar o argila.json; depois rode `relacionar`.')
    return 0


def cmd_relacionar(a):
    cats, modelo = _catalogos(a)
    if modelo:
        tabelas = [(t['fonte'], t['origem'], t['nome']) for t in modelo['tabelas'] if t.get('origem')]
        ja = {(r['de'], r['para']) for r in modelo['relacionamentos']}
    else:
        filtro = {x.strip().upper() for x in (a.tabelas or '').split(',') if x.strip()}
        if a.pedido and not filtro:
            filtro = {r['tabela'].upper() for r in descoberta.buscar(cats, a.pedido, 15)}
            print(f'Tabelas do pedido (pela busca): {", ".join(sorted(filtro))}')
        tabelas = [(n, t['nome'], t['nome']) for n, f in cats.items() for t in f.tabelas.values()
                   if not filtro or t['nome'].upper() in filtro]
        ja = set()
        if len(tabelas) > 40:
            print(f'{len(tabelas)} tabelas é demais para sugerir ligações de uma vez (o resultado seria ilegível). '
                  'Diga o assunto com --pedido "<o que o painel mostra>" ou escolha com --tabelas T1,T2,...')
            return 1
    sugestoes = descoberta.relacionar(cats, tabelas, ja)
    escondidas = []
    if not a.todas and len(sugestoes) > 25:
        sugestoes, escondidas = sugestoes[:25], sugestoes[25:]
    if not sugestoes:
        print('Nenhuma ligação candidata. Se as tabelas se ligam, os nomes das colunas não deixam isso claro: '
              'pergunte ao dono do dado e acrescente sinônimos em dicionario/sinonimos.json.')
    for i, s in enumerate(sugestoes, 1):
        selo = 'PROVADA NO CATÁLOGO' if s['provada_no_catalogo'] else f'confiança {s["confianca"]}'
        if s.get('redundante'):
            selo += '; redundante se aceitar as de cima'
        print(f'{i:>2}. {s["de"]}[{s["campo_filho"]}] -> {s["para"]}[{s["campo_mae"]}]  ({selo}, {s["pontos"]} pts)')
        for mo in s['motivos']:
            print(f'      · {mo}')
        if not s['provada_no_catalogo'] and a.json:
            print('      ' + json.dumps(descoberta.trecho_argila(s), ensure_ascii=False))
    if escondidas:
        conf = sorted({s['confianca'] for s in escondidas})
        print(f'    … mais {len(escondidas)} sugestão(ões) ({", ".join(conf)}): use --todas para ver')
    ligadas = {n for s in sugestoes + escondidas for n in (s['de'], s['para'])} | {n for par in ja for n in par}
    soltas = [n for _, _, n in tabelas if n not in ligadas]
    if soltas:
        print(f'Sem nenhuma ligação nem candidata: {", ".join(soltas)}')
    _lembrete('nenhuma sugestão vira ligação sozinha: confirme os campos com o dono do dado, declare com "por" e, '
              'se puder, prove: `deidara.py receita prova --de "T[C]" --para "T[C]"`.')
    return 0


def cmd_provar(a):
    cab, linhas = receitas.ler_colado(a.de)
    provas = prova.ler(linhas)
    if not provas:
        print(f'{a.de}: não é resultado da receita de prova (cabeçalho: {", ".join(cab[:6])})')
        return 1
    argila = ler_json(a.argila) if a.argila else None
    for pv in provas:
        veredito, explicacao = prova.avaliar(pv)
        print(f'{pv["de"]} -> {pv["para"]}: {veredito.upper()} — {explicacao}')
        bloco = {k: v for k, v in pv.items() if k not in ('de', 'para')}
        if argila is None:
            print('  rode com --argila argila.json para gravar a prova na ligação (o bloco nunca se escreve à mão)')
            continue
        de, para = pv['de'].split('[')[0], pv['para'].split('[')[0]
        alvo = next((r for r in argila.get('relacionamentos', []) if r.get('declarada')
                     and r.get('de', '').upper() == de.upper() and r.get('para', '').upper() == para.upper()), None)
        if not alvo:
            print(f'  nenhuma ligação declarada {de} -> {para} no argila.json: declare (ou confirme) antes de provar')
            continue
        alvo['declarada']['prova'] = bloco
        gravar_json(a.argila, argila)
        print(f'  prova gravada na ligação {de} -> {para} do {a.argila}')
    return 0


def cmd_confirmar(a):
    """Confirma uma ligação sugerida ("A CONFIRMAR") com o nome de quem confirmou com o dono do dado."""
    argila = ler_json(a.argila)
    de, _, para = a.ligacao.replace(' ', '').partition('->')
    pend = [r for r in argila.get('relacionamentos', []) if r.get('declarada')]
    alvo = next((r for r in pend if r['de'].upper() == de.upper() and r['para'].upper() == para.upper()), None)
    if not alvo:
        opcoes = ', '.join(f'{r["de"]}->{r["para"]}' for r in pend) or 'nenhuma'
        print(f'Ligação {a.ligacao} não encontrada entre as declaradas ({opcoes}).')
        return 1
    if a.remover:
        argila['relacionamentos'].remove(alvo)
        gravar_json(a.argila, argila)
        print(f'Ligação {de}->{para} removida (o dono do dado não confirmou).')
        return 0
    alvo['declarada']['por'] = a.por
    if a.motivo:
        alvo['declarada']['motivo'] = a.motivo
    gravar_json(a.argila, argila)
    print(f'Ligação {de}->{para} confirmada por {a.por}. Para provar com números: '
          f'`deidara.py receita prova --argila {a.argila} --de "{de}[{alvo["declarada"]["campos"][0][0]}]" '
          f'--para "{para}[{alvo["declarada"]["campos"][0][1]}]"`')
    return 0


def _aprovacao_valida(caminho_argila, caminhos, modelo):
    """(registro de aprovação, None) ou (None, motivo da recusa)."""
    arq = _arquivo_aprovacao(caminho_argila)
    if not os.path.exists(arq):
        return None, 'ainda não aprovado'
    aprov = ler_json(arq)
    atual = _hashes(caminho_argila, caminhos)
    if aprov.get('argila_sha256') != atual['argila_sha256'] or \
            aprov.get('catalogos_sha256') != atual['catalogos_sha256']:
        return None, 'o argila.json ou um catálogo mudou depois da aprovação (aprove de novo)'
    return aprov, None


def _quem(a):
    if getattr(a, 'por', None):
        return a.por
    r = memory_card._rodar(['git', 'config', 'user.name'])
    return (r.stdout.strip() if r and r.returncode == 0 else '') or 'não informado'


def _cartao():
    cfg = memory_card.configuracao()
    if not cfg.get('pasta') or not os.path.isdir(cfg['pasta']):
        raise SystemExit('Memory Card não configurado nesta máquina: rode `deidara.py memory-card iniciar --repo '
                         f'DONO/{memory_card.NOME_PADRAO}` (o cartão do time; o Deidara usa a seção '
                         f'{memory_card.SECAO}/; precisa do `gh` autenticado e do `git`). Numa sandbox sem '
                         'o `gh` (como o claude.ai), o cartão não funciona: diga isso ao usuário.')
    memory_card._atualizar(cfg['pasta'])
    return cfg['pasta']


def cmd_memory_card(a):
    if a.acao == 'desligar':
        print(memory_card.desligar())
        return 0
    if a.acao == 'iniciar':
        try:
            for m in memory_card.iniciar(a.repo, a.pasta, a.publico):
                print(m)
        except ValueError as e:
            print(str(e))
            return 1
        return 0
    pasta = _cartao()
    if a.acao == 'catalogo':
        itens = memory_card.saves(pasta)
        if a.json:
            print(json.dumps([{'ref': r, **{k: f.get(k) for k in ('tipo', 'titulo', 'versao', 'status', 'descricao')}}
                              for r, f in itens], ensure_ascii=False, indent=2))
        for r, f in itens:
            print(f'  [{f["tipo"]}] {r}  v{f["versao"]} · {f["status"]} — {f.get("descricao") or ""}'[:160])
        if not itens:
            print('O cartão está vazio.')
        return 0
    if a.acao == 'buscar':
        achados = memory_card.buscar(pasta, a.termos or [], a.limite)
        for r, f in achados:
            selo = 'OFICIAL' if f.get('status') == 'oficial' else f['status']
            print(f'  [{f["tipo"]}] {f["titulo"]} ({selo}, v{f["versao"]}) — {r}')
            if f.get('descricao'):
                print(f'      {f["descricao"]}')
            if f['tipo'] == 'indicador':
                print(f'      DAX: {" ".join(f.get("dax", "").split())[:150]}')
        if not achados:
            print('Nada no cartão com esses termos: pode criar do zero.')
        _lembrete('se algo serviu, ofereça reaproveitar (a definição de um indicador OFICIAL não se reescreve).')
        return 0
    if a.acao == 'marcar':
        try:
            print(memory_card.marcar(pasta, a.ref, a.status, _quem(a), a.motivo))
        except ValueError as e:
            print(str(e))
            return 1
        return 0
    if a.acao == 'conferir':
        if not a.catalogos:
            print('informe --catalogos com os catálogos atuais das fontes (eles não ficam no cartão)')
            return 1
        cats = {}
        for c in a.catalogos:
            f = catalogo.carregar(c)
            cats[f.nome] = f
        res = memory_card.conferir(pasta, cats, resolver, a.refs or (), a.registrar, _quem(a))
        commit = res.pop('__commit__', None)
        for ref, (sit, det) in res.items():
            print(f'  {sit.upper():<12} {ref}')
            for d in det[:8]:
                print(f'      · {d}')
        if commit:
            print(commit[1][0])
        return 1 if any(s == 'quebrado' for s, _ in res.values()) else 0
    # enviar
    argila, cats, modelo, problemas, caminhos = _carregar(a.argila)
    if problemas.erros:
        _relatorio(problemas)
        return 1
    aprov, recusa = _aprovacao_valida(a.argila, caminhos, modelo)
    if recusa:
        print(f'Só painel aprovado entra no cartão: {recusa}.')
        return 1
    texto = None
    if a.texto:
        with open(a.texto, encoding='utf-8') as f:
            texto = f.read()
    plano = memory_card.planejar(pasta, argila, modelo, aprov, a.categoria, a.secao, a.artigo, a.motivo, texto,
                                 a.relacionado, a.status)
    print(f'Destino: {memory_card.SECAO}/saves/{plano["ref"]}  (v{plano["versao"]}, {"novo" if plano["novo"] else "versão nova" if plano["mudancas"] else "sem mudança no painel"}, status {plano["status"]})')
    for m in plano['mudancas']:
        print(f'  MUDOU  {m}')
    for i in plano['indicadores']:
        extra = f' — {"; ".join(i["mudancas"])}' if i['mudancas'] else ''
        print(f'  indicador {i["nome"]}: {i["estado"]} (v{i["versao"]}) {i["ref"]}{extra}')
    for b in plano['bloqueios'] + plano['erros']:
        print(f'  ERRO  {b}')
    if plano['bloqueios'] or plano['erros']:
        return 1
    if plano['novo']:
        print('\nArtigo (corpo):\n' + '\n'.join('  ' + l for l in (plano['texto'] or '').strip().splitlines()[:40]))
    if not a.confirmar:
        _lembrete('isto é só a prévia: mostre ao usuário e, só com o "sim", repita com --confirmar.')
        return 0
    import tempfile
    tmp = tempfile.mkdtemp(prefix='ddmc')
    dic = os.path.join(tmp, 'dicionario_indicadores.md')
    gravar_texto(dic, docs.dicionario(modelo, aprov.get('historico') or []))
    prot = os.path.join(tmp, 'prototipo.html')
    gravar_texto(prot, prototipo.gerar_html(modelo, problemas, VERSAO))
    try:
        resultado = memory_card.gravar(pasta, plano, _quem(a), a.argila,
                                       {'dicionario_indicadores.md': dic, 'prototipo.html': prot})
    except ValueError as e:
        print(str(e))
        return 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f'Salvo em {memory_card.SECAO}/saves/{plano["ref"]}: {resultado}')
    return 0


def cmd_funcoes(a):
    if a.acao == 'ver':
        achou = dicionario.ver(a.termo, a.linguagem)
        if not achou:
            print(f'{a.termo} não está no dicionário. Tente: deidara.py funcoes buscar "<o que você quer fazer>"')
            return 1
        ling, nome, e = achou
        print(f'{nome} ({ling.upper()} · {", ".join(e.get("categorias") or [])})')
        for s in e.get('sintaxe') or []:
            print(f'  {s}')
        if e.get('descricao'):
            print(f'  {e["descricao"]}')
        if e.get('uso'):
            print(f'  Em indicadores: {e["uso"]}')
        if e.get('url'):
            print(f'  Documentação oficial: {e["url"]}')
        return 0
    achados = dicionario.buscar(a.termo, a.linguagem)
    for nome, e in achados:
        print(f'  {nome:<28} {", ".join(e.get("categorias") or [])[:28]:<28} {e.get("descricao", "")}')
    if not achados:
        print('Nada encontrado. Busque pelo nome em inglês (ex.: "YTD", "DIVIDE") ou pela categoria.')
    return 0


def cmd_padroes(a):
    dados = dicionario.padroes()
    if not a.termo:
        print('Onde criar cada coisa:')
        for o in dados['onde_criar']:
            print(f'  {o["meio"]}: {o["quando"]}')
    for p in dicionario.padroes_para(a.termo or ''):
        print(f'\n{p["nome"]}  [{p["id"]}]')
        if p.get('argila'):
            print(f'  argila.json: {json.dumps(p["argila"], ensure_ascii=False)}')
        for i, x in enumerate(p.get('cadeia') or [], 1):
            print(f'  {i}. {json.dumps(x, ensure_ascii=False)}')
        if p.get('dax'):
            print(f'  DAX: {p["dax"]}')
        if p.get('onde'):
            print(f'  Onde: {p["onde"]}')
        if p.get('alternativa'):
            print(f'  Alternativa: {p["alternativa"]}')
        for x in p.get('armadilhas') or []:
            print(f'  Atenção: {x}')
    return 0


def cmd_visuais(a):
    achados = dicionario.visuais_para(a.termo or '')
    if not achados:
        print(f'Nenhuma técnica para "{a.termo}". Sem assunto, `deidara.py visuais` lista todas.')
        return 1
    for v in achados:
        selo = 'o Deidara gera' if v['deidara'].get('gera') else ('nativo' if v['nativo'] else 'visual personalizado')
        print(f'\n{v["nome"]}  [{v["id"]}] · {selo}')
        print(f'  Quando: {v["quando"]}')
        if v['deidara'].get('argila'):
            print(f'  argila.json (medida): {json.dumps(v["deidara"]["argila"], ensure_ascii=False)}')
        if v['deidara'].get('visual'):
            print(f'  argila.json (visual): {json.dumps(v["deidara"]["visual"], ensure_ascii=False)}')
        print(f'  No Power BI: {v["power_bi"]}')
        for x in v.get('cuidados') or []:
            print(f'  Atenção: {x}')
    print('\nGuia de design: referencias/design.md · medidas SVG: referencias/svg.md')
    return 0


def cmd_modelos(a):
    from argila.modelos import MODELOS
    print('Modelos de layout ("modelo" no argila.json; ver referencias/modelos.md):')
    for k, v in MODELOS.items():
        print(f'  {k:<20} {v}')
    return 0


def cmd_validar(a):
    _, _, modelo, problemas, _ = _carregar(a.argila)
    if a.json:
        print(json.dumps({'ok': not problemas.erros, 'erros': problemas.erros, 'avisos': problemas.avisos,
                          'resumo': _resumo(modelo)}, ensure_ascii=False, indent=2))
    else:
        print(relato.validacao(modelo, problemas, a.argila))
    return 1 if problemas.erros else 0


def _resumo(m):
    return {'tabelas': len(m['tabelas']), 'relacionamentos': len(m['relacionamentos']),
            'medidas': len(m['medidas']), 'paginas': len(m['paginas']),
            'visuais': sum(len(p['visuais']) for p in m['paginas'])}


LIGACAO_PENDENTE = 'ligação sugerida ainda não confirmada'


def cmd_prototipar(a):
    _, _, modelo, problemas, _ = _carregar(a.argila)
    pendentes = [e for e in problemas.erros if LIGACAO_PENDENTE in e]
    if pendentes and len(pendentes) == len(problemas.erros):
        # números fictícios: o gestor já pode reagir; a ligação vira pendência e o `aprovar` continua recusando
        problemas.erros = []
        for e in pendentes:
            problemas.aviso('[Ligações] ' + e.split(':')[0], 'ligação A CONFIRMAR: o protótipo mostra o painel SEM ela '
                            '(os números desta tabela não abrem pelos cortes dela); confirme com o dono do dado antes do '
                            'aceite')
        print(f'{len(pendentes)} ligação(ões) A CONFIRMAR: o protótipo sai com elas nas pendências; o `aprovar` só passa '
              'depois do `confirmar`.')
    if problemas.erros:
        _relatorio(problemas, modelo, a.argila)
        print('Protótipo não gerado: corrija os erros acima.')
        return 1
    saida = a.saida or os.path.splitext(a.argila)[0] + '.prototipo.html'
    gravar_texto(saida, prototipo.gerar_html(modelo, problemas, VERSAO))
    print(f'Protótipo: {saida}')
    _lembrete('mostre o protótipo ao usuário e peça o aceite explícito; só com o "sim" rode '
              '`deidara.py aprovar argila.json --por NOME`.')
    return 0


def cmd_aprovar(a):
    _, _, modelo, problemas, caminhos = _carregar(a.argila)
    if problemas.erros:
        _relatorio(problemas, modelo, a.argila)
        print('Não dá para aprovar com erro de validação.')
        return 1
    if modelo['pendencias']:
        print('Não dá para aprovar com indicador sem definição (o gestor estaria aprovando um número sem significado):')
        for x in modelo['pendencias']:
            print(f'  · {x}')
        return 1
    prot = os.path.splitext(a.argila)[0] + '.prototipo.html'
    if not _mais_novo(prot, a.argila, *caminhos):
        if not a.sem_prototipo:
            print('Não dá para aprovar: o protótipo não existe ou é anterior a esta versão do argila.json, e o gestor '
                  f'estaria aprovando algo que não viu. Gere (`deidara.py prototipar {a.argila}`), mostre e aprove de '
                  'novo. (Só se o gestor aprovou sem protótipo, de propósito: --sem-prototipo.)')
            return 1
        print('Atenção: aprovado SEM protótipo em dia (--sem-prototipo); isso fica registrado.', file=sys.stderr)
    arq = _arquivo_aprovacao(a.argila)
    anterior = ler_json(arq) if os.path.exists(arq) else None
    retrato = governanca.retrato(modelo)
    mudancas = governanca.diferencas(anterior['retrato'], retrato) if anterior and anterior.get('retrato') else []
    historico = (anterior or {}).get('historico', [])
    if a.resumo:
        conferido = _conferir_resumo(a.resumo, modelo)
        if conferido:
            print(conferido)
            return 1
    reg = {'projeto': modelo['projeto'], 'versao': modelo['versao'], 'aprovado_por': a.por,
           'prototipo_sha256': sha256_arquivo(prot) if os.path.exists(prot) else None,
           'sem_prototipo': bool(a.sem_prototipo and not _mais_novo(prot, a.argila, *caminhos)),
           'em': datetime.datetime.now().strftime('%d/%m/%Y %H:%M'), 'observacao': a.observacao or '',
           'avisos_aceitos': problemas.avisos, 'deidara': VERSAO, **_hashes(a.argila, caminhos)}
    if anterior and (mudancas or not historico):
        historico = historico + [{'versao': reg['versao'], 'em': reg['em'], 'aprovado_por': a.por,
                                  'observacao': reg['observacao'], 'mudancas': mudancas}]
    elif not anterior:
        historico = [{'versao': reg['versao'], 'em': reg['em'], 'aprovado_por': a.por,
                      'observacao': reg['observacao'], 'mudancas': ['primeira versão aprovada']}]
    reg['historico'], reg['retrato'] = historico, retrato
    gravar_json(arq, reg)
    print(f'Aprovado por {a.por} em {reg["em"]} ({len(problemas.avisos)} aviso(s) aceito(s)).')
    for x in mudancas:
        print(f'  MUDOU  {x}')
    print(f'Registro: {_arquivo_aprovacao(a.argila)}')
    return 0


def cmd_gerar(a):
    _, _, modelo, problemas, caminhos = _carregar(a.argila)
    if problemas.erros:
        _relatorio(problemas)
        return 1
    arq = _arquivo_aprovacao(a.argila)
    if not os.path.exists(arq):
        print('Sem aprovação: gere o protótipo, mostre ao usuário e rode `aprovar` só com o "sim" dele.')
        return 1
    aprov = ler_json(arq)
    atual = _hashes(a.argila, caminhos)
    if aprov.get('argila_sha256') != atual['argila_sha256'] or \
            aprov.get('catalogos_sha256') != atual['catalogos_sha256']:
        print('O argila.json ou um catálogo mudou depois da aprovação: gere o protótipo de novo e peça novo aceite.')
        for x in governanca.diferencas(aprov.get('retrato') or {}, governanca.retrato(modelo)):
            print(f'  MUDOU  {x}')
        return 1
    if aprov.get('deidara') != VERSAO:
        print(f'A aprovação foi feita com o Deidara {aprov.get("deidara")} e este é o {VERSAO}: a saída pode mudar. '
              'Gere o protótipo de novo e peça novo aceite.')
        return 1
    nome = ident(modelo['projeto'], 'Painel')
    pasta = a.saida or os.path.join(os.path.dirname(os.path.abspath(a.argila)), 'saida', nome)
    maior = len(os.path.abspath(pasta)) + len(nome) + LONGEST_RELATIVO
    if os.name == 'nt' and maior > 259:
        print(f'Caminho longo demais para o Windows ({maior} caracteres no arquivo mais fundo; o limite é 260). '
              f'Use uma pasta curta: deidara.py gerar {a.argila} -o C:/paineis/{nome}')
        return 1
    if os.path.exists(pasta):
        shutil.rmtree(pasta)
    os.makedirs(pasta)
    gravar_json(os.path.join(pasta, f'{nome}.pbip'), {
        '$schema': 'https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json',
        'version': '1.0', 'artifacts': [{'report': {'path': f'{nome}.Report'}}],
        'settings': {'enableAutoRecovery': True}})
    gravar_texto(os.path.join(pasta, '.gitignore'), '**/.pbi/localSettings.json\n**/.pbi/cache.abf\n')
    if a.demo:
        from argila import demo
        modelo['_demo'] = demo.expressoes(modelo)
    tmdl.gravar(modelo, pasta, nome)
    pbir.gravar(modelo, pasta, nome)
    for f in sql.fontes_sql(modelo):
        dsql = os.path.join(pasta, 'sql', f['nome'])
        os.makedirs(dsql)
        gravar_texto(os.path.join(dsql, '01_views.sql'), sql.views(modelo, f), bom=True)
        gravar_texto(os.path.join(dsql, '02_conferencia.sql'), sql.conferencia(modelo, f), bom=True)
        gravar_texto(os.path.join(dsql, '03_qualidade.sql'), sql.qualidade(modelo, f), bom=True)
    os.makedirs(os.path.join(pasta, 'docs'))
    gravar_texto(os.path.join(pasta, 'docs', 'dicionario_indicadores.md'),
                 docs.dicionario(modelo, aprov.get('historico') or []))
    gravar_texto(os.path.join(pasta, 'docs', 'medidas.dax'), docs.medidas_dax(modelo))
    leia = docs.leia_me(modelo, nome, aprov, problemas.avisos)
    if a.demo:
        leia = ('> **DEMONSTRAÇÃO.** Este projeto traz linhas fictícias embutidas (geradas pelo Deidara, sem fonte de '
                'dados): abra o .pbip, clique em **Atualizar** e todos os números são calculados pelo Power BI. Serve '
                'para testar e mostrar o painel; para o painel real, gere de novo sem `--demo`.\n\n') + leia
    gravar_texto(os.path.join(pasta, 'LEIA-ME.md'), leia)
    gravar_texto(os.path.join(pasta, 'HOMOLOGACAO.md'), docs.homologacao(modelo, nome, aprov))
    gravar_texto(os.path.join(pasta, 'prototipo.html'), prototipo.gerar_html(modelo, problemas, VERSAO))
    aprov['ultima_geracao'] = {'em': datetime.datetime.now().strftime('%d/%m/%Y %H:%M'), 'pasta': os.path.abspath(pasta),
                               'deidara': VERSAO}
    gravar_json(arq, aprov)
    print(f'Katsu! Projeto {"de DEMONSTRAÇÃO (linhas fictícias embutidas) " if a.demo else ""}gerado em {pasta}')
    if a.demo:
        print('  Abra o .pbip e clique em Atualizar: as tabelas vêm do próprio projeto, sem banco nenhum.')
    print(f'  {nome}.pbip  ·  LEIA-ME.md  ·  HOMOLOGACAO.md' + ''.join(f'  ·  sql/{f["nome"]}/' for f in sql.fontes_sql(modelo)))
    print('Agora:')
    passo = 1
    for f in sql.fontes_sql(modelo):
        print(f'  {passo}. [DBA] rodar sql/{f["nome"]}/01_views.sql no banco {f["banco"]}')
        passo += 1
    print(f'  {passo}. [Analista] abrir {nome}.pbip no Power BI Desktop, conferir parâmetros e credenciais, Atualizar')
    print(f'  {passo + 1}. [Analista + dono do indicador] preencher HOMOLOGACAO.md (qualidade, totais, cortes)')
    print(f'  {passo + 2}. [Analista] Salvar como .pbix e publicar; depois `memory-card enviar ... --status em-uso`')
    _lembrete('o .pbix sai do Power BI Desktop: abra o .pbip e use Arquivo > Salvar como (passo "Gerar o .pbix" do '
              'LEIA-ME), depois de preencher o HOMOLOGACAO.md.')
    return 0


def cmd_diff(a):
    """O que mudou no argila.json desde a última aprovação (ou entre dois argila.json)."""
    _, _, modelo, problemas, _ = _carregar(a.argila)
    if a.contra:
        _, _, outro, _, _ = _carregar(a.contra)
        antes, rotulo = governanca.retrato(outro), a.contra
    else:
        arq = _arquivo_aprovacao(a.argila)
        if not os.path.exists(arq):
            print('Sem aprovação para comparar: use --contra OUTRO_ARGILA.json')
            return 1
        aprov = ler_json(arq)
        antes, rotulo = aprov.get('retrato') or {}, f'aprovação de {aprov.get("em")} ({aprov.get("aprovado_por")})'
    mud = governanca.diferencas(antes, governanca.retrato(modelo))
    print(f'Comparando com: {rotulo}')
    for x in mud:
        print(f'  {x}')
    print('Nada mudou para quem consome o painel.' if not mud else f'{len(mud)} mudança(s).')
    return 0


def _mais_novo(arq, *outros):
    return os.path.exists(arq) and all(os.path.getmtime(arq) >= os.path.getmtime(o) for o in outros if os.path.exists(o))


def _conferir_resumo(caminho, modelo):
    """O resumo copiado da aba Para aprovar: confere código do protótipo e decisão. None = ok."""
    from argila import prototipo as _p
    with open(caminho, encoding='utf-8-sig') as f:
        texto = f.read()
    codigo = _p.codigo_do_prototipo(modelo)
    if f'Código: {codigo}' not in texto:
        return (f'O resumo não é deste protótipo (código esperado {codigo}): o gestor aprovou outra versão. '
                'Mande o protótipo atual e peça um resumo novo.')
    if 'Decisão: Aprovo' not in texto:
        return 'O resumo não traz "Decisão: Aprovo": o gestor pediu ajustes. Leia os comentários, ajuste e prototipe de novo.'
    return None


def cmd_situacao(a):
    """Onde o projeto está no fluxo e qual é o próximo passo."""
    if not os.path.exists(a.argila):
        print(f'{a.argila} não existe. Para começar: `deidara.py novo PASTA` (ver `deidara.py` sem argumentos).')
        return 1
    passos = []

    def passo(ok, texto, proximo=None):
        passos.append((ok, texto, proximo))
        return ok

    try:
        argila, cats, modelo, problemas, caminhos = _carregar(a.argila)
    except SystemExit as e:
        print(f'✗ fontes: {e}')
        print('Próximo passo: rode a receita da fonte e o `catalogar` (ver referencias/fontes.md).')
        return 1
    passo(True, f'fontes catalogadas: {", ".join(f"{n} ({c.tipo})" for n, c in cats.items())}')
    prot = os.path.splitext(a.argila)[0] + '.prototipo.html'
    pendentes = [e for e in problemas.erros if LIGACAO_PENDENTE in e]
    if pendentes and len(pendentes) == len(problemas.erros):   # o protótipo já sai; o aceite espera a confirmação
        passo(True, f'validação: só falta confirmar {len(pendentes)} ligação(ões) sugerida(s)')
        if passo(_mais_novo(prot, a.argila, *caminhos), 'protótipo em dia com o argila.json',
                 f'deidara.py prototipar {a.argila}'):
            ligacoes = ', '.join(re.sub(r'^relacionamentos\[\d+\]\s*', '', e.split(':')[0]).replace(' ', '') for e in pendentes)
            passo(False, f'ligação(ões) A CONFIRMAR: {ligacoes}',
                  f'confira os campos com o dono do dado e rode `deidara.py confirmar {a.argila} --ligacao DE->PARA '
                  '--por "<quem confirmou>"` (ou --remover); o aceite vem depois')
        return _imprimir_situacao(modelo, passos)
    if not passo(not problemas.erros, f'validação: {len(problemas.erros)} erro(s), {len(problemas.avisos)} aviso(s)',
                 f'deidara.py validar {a.argila}'):
        return _imprimir_situacao(modelo, passos)
    aprov, recusa = _aprovacao_valida(a.argila, caminhos, modelo)
    if not passo(_mais_novo(prot, a.argila, *caminhos) or bool(aprov and aprov.get('sem_prototipo')),
                 'protótipo em dia com o argila.json', f'deidara.py prototipar {a.argila}'):
        return _imprimir_situacao(modelo, passos)
    if not passo(aprov is not None, f'aprovação: {aprov["aprovado_por"]} em {aprov["em"]}' if aprov else
                 f'aprovação: {recusa}', f'mostre o protótipo e, com o "sim", `deidara.py aprovar {a.argila} --por NOME`'):
        return _imprimir_situacao(modelo, passos)
    ger = aprov.get('ultima_geracao')
    if not passo(bool(ger), f'projeto Power BI gerado em {ger["pasta"]} ({ger["em"]})' if ger else 'projeto Power BI gerado',
                 f'deidara.py gerar {a.argila} -o C:/paineis/<nome>'):
        return _imprimir_situacao(modelo, passos)
    cartao = memory_card.configuracao().get('pasta')
    if cartao and os.path.isdir(cartao):
        salvo = [r for r, f in memory_card.saves(cartao)
                 if f.get('tipo') == 'painel' and f.get('retrato') == governanca.retrato(modelo)]
        passo(bool(salvo), f'salvo no Memory Card: {salvo[0]}' if salvo else 'salvo no Memory Card (versão atual)',
              f'deidara.py memory-card enviar {a.argila} --categoria C --secao S')
    else:
        passo(True, 'Memory Card não configurado nesta máquina (opcional)')
    return _imprimir_situacao(modelo, passos)


def _imprimir_situacao(modelo, passos):
    print(relato.resumo(modelo))
    for ok, texto, _ in passos:
        print(f'  {"✓" if ok else "✗"} {texto}')
    pendente = next((p for p in passos if not p[0]), None)
    if pendente:
        print(f'Próximo passo: {pendente[2]}')
        return 0
    print('✓ Tudo feito. Siga o LEIA-ME da pasta gerada (views, atualizar, conferir, publicar).')
    return 0


GUIA = """Deidara — do dado ao painel Power BI: protótipo primeiro, projeto completo depois do "sim".

Por onde começar
  python deidara.py novo PASTA                     cria a pasta do painel, com o roteiro
  python deidara.py situacao PASTA/argila.json     onde estou e qual é o próximo passo

O fluxo
  1. briefing (painel.json)   as respostas do gestor: decisão, público, indicadores (definição, meta), cortes
  2. receita + catalogar      a pessoa roda a receita onde os dados estão; o resultado vira o catálogo
  3. esbocar                  o primeiro argila.json: padrões do indicador + briefing + catálogos
  4. validar                  nomes, funções e filtros, até zerar os erros
  5. prototipar               o protótipo HTML para o gestor (números fictícios; ligação a confirmar vira pendência)
  6. confirmar + aprovar      a ligação conferida com o dono do dado; o "sim" do gestor, registrado
  7. gerar                    o projeto Power BI (.pbip), views SQL, conferência e LEIA-ME
  8. memory-card enviar       salva no cartão do time

Apoio
  buscar / relacionar         quais tabelas e quais ligações (com evidência)
  padroes [assunto]           como criar cada indicador e onde
  visuais [assunto]           técnicas de visual: meta na tabela, ranking, causa, status...
  modelos                     os onze modelos de layout ("modelo" no argila.json)
  funcoes buscar|ver          dicionário de funções DAX e Power Query
  diff                        o que mudou desde a aprovação

Ajuda de um comando: python deidara.py COMANDO --help
"""


def cmd_status(a):
    print(f'Deidara {VERSAO} · Python {sys.version.split()[0]} · pasta {RAIZ}')
    return 0


class _Parser(argparse.ArgumentParser):
    """argparse falando português."""
    TROCAS = (('usage:', 'uso:'), ('positional arguments', 'argumentos'), ('options:', 'opções:'),
              ('optional arguments:', 'opções:'), ('show this help message and exit', 'mostra esta ajuda'))

    def format_help(self):
        texto = super().format_help()
        for a, b in self.TROCAS:
            texto = texto.replace(a, b)
        return texto

    def format_usage(self):
        return super().format_usage().replace('usage:', 'uso:')

    def error(self, message):
        import difflib
        if 'invalid choice' in message:
            escolhido = message.split("'")[1] if "'" in message else ''
            opcoes = [x.strip(" '") for x in message.split('choose from')[-1].strip(' ()').split(',')]
            parecido = difflib.get_close_matches(escolhido, opcoes, n=1)
            if parecido:
                message += f'. Você quis dizer: {parecido[0]}?'
        message = (message.replace('the following arguments are required', 'faltam os argumentos')
                   .replace('invalid choice', 'opção inválida').replace('choose from', 'escolha entre')
                   .replace('unrecognized arguments', 'argumentos desconhecidos'))
        self.print_usage(sys.stderr)
        self.exit(2, f'{self.prog}: {message}\nVeja: python deidara.py (sem argumentos) para o roteiro.\n')


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(GUIA)
        return 0
    ap = _Parser(prog='deidara', description='Do dado ao painel Power BI.')
    sub = ap.add_subparsers(dest='cmd', required=True, parser_class=_Parser, metavar='COMANDO')
    r = sub.add_parser('receita', help='a consulta que a pessoa roda onde os dados estão (só estrutura)')
    r.add_argument('tipo', choices=['sql', 'dax', 'm', 'funcoes-dax', 'funcoes-m', 'prova'])
    r.add_argument('--argila')
    r.add_argument('--catalogos', nargs='+')
    r.add_argument('--de', help='prova: Tabela[COLUNA] da filha (lado muitos)')
    r.add_argument('--para', help='prova: Tabela[COLUNA] da mãe (lado um)')
    r.add_argument('--esquema', default='dbo')
    r.add_argument('--tabelas', help='sql: tabelas separadas por vírgula (vazio = todas do esquema)')
    r.add_argument('--consultas', help='m: consultas Power Query separadas por vírgula')
    r.add_argument('-o', '--saida')
    c = sub.add_parser('catalogar', help='resultado colado de uma receita -> catálogo da fonte')
    c.add_argument('--de', required=True)
    c.add_argument('--fonte')
    c.add_argument('--funcoes', choices=['dax', 'm'], help='o resultado é da receita de funções (dicionário local)')
    c.add_argument('--m', help='pasta com os .m (texto do Editor Avançado) das consultas, para a receita m')
    c.add_argument('-o', '--saida')
    v = sub.add_parser('validar', help='confere o argila.json (nomes, ligações, funções, filtros)')
    v.add_argument('argila')
    v.add_argument('--json', action='store_true')
    p = sub.add_parser('prototipar', help='protótipo HTML para o gestor validar')
    p.add_argument('argila')
    p.add_argument('-o', '--saida')
    ap_ = sub.add_parser('aprovar', help='registra o "sim" do gestor')
    ap_.add_argument('argila')
    ap_.add_argument('--por', required=True)
    ap_.add_argument('--observacao')
    ap_.add_argument('--resumo', help='o resumo copiado da aba "Para aprovar" (confere versão e decisão)')
    ap_.add_argument('--sem-prototipo', action='store_true', help='o gestor aprovou sem protótipo, de propósito')
    g = sub.add_parser('gerar', help='gera o projeto Power BI, SQL e documentação')
    g.add_argument('argila')
    g.add_argument('-o', '--saida')
    g.add_argument('--demo', action='store_true',
                   help='projeto de demonstração: linhas fictícias embutidas, abre e calcula sem banco nenhum')
    bu = sub.add_parser('buscar', help='tabelas de um pedido, em todos os catálogos')
    bu.add_argument('pedido')
    bu.add_argument('--argila')
    bu.add_argument('--catalogos', nargs='+')
    bu.add_argument('--limite', type=int, default=10)
    rl = sub.add_parser('relacionar', help='sugere ligações com evidência')
    rl.add_argument('--argila')
    rl.add_argument('--catalogos', nargs='+')
    rl.add_argument('--tabelas', help='com --catalogos: só estas tabelas (separadas por vírgula)')
    rl.add_argument('--json', action='store_true', help='mostra o trecho do argila.json de cada sugestão')
    rl.add_argument('--pedido', help='com --catalogos: o assunto (a busca escolhe as tabelas)')
    rl.add_argument('--todas', action='store_true', help='mostra todas as sugestões (padrão: as 25 melhores)')
    pv = sub.add_parser('provar', help='lê o resultado da receita de prova e grava na ligação')
    pv.add_argument('--de', required=True)
    pv.add_argument('--argila', help='grava a prova na ligação declarada correspondente')
    cf = sub.add_parser('confirmar', help='confirma (ou remove) uma ligação sugerida "A CONFIRMAR"')
    cf.add_argument('argila')
    cf.add_argument('--ligacao', required=True, help='de->para, ex.: fMetas->dEmpresa')
    cf.add_argument('--por', help='quem confirmou com o dono do dado')
    cf.add_argument('--motivo')
    cf.add_argument('--remover', action='store_true', help='o dono do dado não confirmou: tira a ligação')
    mc = sub.add_parser('memory-card', help='o cartão de memória do time (painéis e indicadores)')
    mc.add_argument('acao', choices=['iniciar', 'catalogo', 'buscar', 'enviar', 'marcar', 'conferir', 'desligar'])
    mc.add_argument('alvo', nargs='*', help='buscar: termos; enviar: argila.json; marcar: REF; conferir: REFs')
    mc.add_argument('--repo')
    mc.add_argument('--pasta')
    mc.add_argument('--publico', action='store_true')
    mc.add_argument('--json', action='store_true')
    mc.add_argument('--limite', type=int, default=10)
    mc.add_argument('--categoria')
    mc.add_argument('--secao')
    mc.add_argument('--artigo')
    mc.add_argument('--texto')
    mc.add_argument('--motivo')
    mc.add_argument('--relacionado', action='append', default=[])
    mc.add_argument('--status')
    mc.add_argument('--por')
    mc.add_argument('--confirmar', action='store_true')
    mc.add_argument('--catalogos', nargs='+')
    mc.add_argument('--registrar', action='store_true')
    fu = sub.add_parser('funcoes', help='dicionário de funções DAX e M')
    fu.add_argument('acao', choices=['buscar', 'ver'])
    fu.add_argument('termo')
    fu.add_argument('--linguagem', choices=['dax', 'm'])
    pa = sub.add_parser('padroes', help='padrões de indicador e onde criar cada coisa')
    pa.add_argument('termo', nargs='?')
    sub.add_parser('modelos', help='os modelos de layout (faixa de KPIs, coluna de KPIs, história longa...)')
    vs = sub.add_parser('visuais', help='técnicas de visual (meta, ranking, causa, status...) e como fazer')
    vs.add_argument('termo', nargs='?')
    df = sub.add_parser('diff', help='o que mudou desde a aprovação')
    df.add_argument('argila')
    df.add_argument('--contra')
    nv = sub.add_parser('novo', help='cria a pasta de um painel novo, com receitas e roteiro')
    nv.add_argument('pasta')
    nv.add_argument('--projeto')
    es = sub.add_parser('esbocar', help='primeiro argila.json a partir dos catálogos e do pedido')
    es.add_argument('alvo', help='a pasta do painel (com catalogos/) ou um catálogo')
    es.add_argument('--catalogos', nargs='+', help='mais catálogos (quando o alvo é um catálogo)')
    es.add_argument('--pedido', help='o que o painel precisa mostrar, em português (sem ele, sai do briefing do painel.json)')
    es.add_argument('--projeto')
    es.add_argument('--tabelas', help='escolha à mão: fonte:TABELA,fonte:TABELA')
    es.add_argument('-o', '--saida')
    es.add_argument('--forcar', action='store_true')
    si = sub.add_parser('situacao', help='onde o projeto está e qual é o próximo passo')
    si.add_argument('argila')
    sub.add_parser('status', help='versão do Deidara')
    a = ap.parse_args(argv)
    if a.cmd == 'confirmar' and not a.remover and not a.por:
        ap.error('confirmar pede --por "<quem confirmou>" (ou --remover)')
    if a.cmd == 'memory-card':
        a.termos = a.refs = a.alvo
        a.argila = a.alvo[0] if a.alvo else None
        a.ref = a.alvo[0] if a.alvo else None
        if a.acao == 'enviar' and (not a.argila or not a.categoria or not a.secao):
            ap.error('memory-card enviar pede argila.json, --categoria e --secao')
        if a.acao == 'marcar' and (not a.ref or not a.status):
            ap.error('memory-card marcar pede REF e --status')
    return {'receita': cmd_receita, 'catalogar': cmd_catalogar, 'validar': cmd_validar, 'prototipar': cmd_prototipar, 'aprovar': cmd_aprovar,
            'gerar': cmd_gerar, 'diff': cmd_diff, 'funcoes': cmd_funcoes, 'padroes': cmd_padroes, 'visuais': cmd_visuais, 'modelos': cmd_modelos,
            'buscar': cmd_buscar, 'relacionar': cmd_relacionar, 'provar': cmd_provar,
            'memory-card': cmd_memory_card, 'confirmar': cmd_confirmar, 'situacao': cmd_situacao, 'novo': cmd_novo, 'esbocar': cmd_esbocar, 'status': cmd_status}[a.cmd](a) or 0


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    try:
        sys.exit(main())
    except ErroDeUso as e:
        print(f'✗ {e}')
        sys.exit(1)
    except FileNotFoundError as e:
        print(f'✗ arquivo ou pasta não encontrado: {e.filename}')
        sys.exit(1)
