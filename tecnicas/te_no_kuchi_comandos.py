"""
Os comandos das Bocas das Mãos: novo (a pasta do painel com o roteiro e o briefing) e esbocar (o primeiro argila.json).
"""

import os

from tecnicas.luneta import catalogo
from tecnicas import te_no_kuchi as esboco
from tecnicas.luneta import receitas
from kibaku_nendo.util import gravar_json, gravar_texto, ler_json


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
    print('  ROTEIRO.md  o passo a passo deste painel')
    print('  painel.json o briefing: as respostas do gestor (indicadores, definição, meta, cortes)')
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
