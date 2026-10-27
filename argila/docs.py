"""
A documentação que acompanha a entrega: o passo a passo para tornar o
protótipo real, o dicionário de indicadores e as medidas em .dax.
"""

from .sql import nome_view
from .util import FORMATOS


def medidas_dax(m):
    out = [f'// {m["projeto"]} — medidas DAX (referência; o .pbip já traz todas)', '']
    for md in m['medidas']:
        if md['descricao']:
            out.append(f'// {md["descricao"]}')
        out.append(f'// tabela: {md["tabela"]} · formato: {FORMATOS.get(md["formato"], "texto")}'
                   + (f' · pasta: {md["pasta"]}' if md['pasta'] else ''))
        out.append(f'[{md["nome"]}] =\n{md["dax"]}\n')
    return '\n'.join(out)


def dicionario(m, historico=()):
    out = [f'# {m["projeto"]} — dicionário de indicadores' + (f' (versão {m["versao"]})' if m.get('versao') else ''), '']
    if m['descricao']:
        out += [m['descricao'], '']
    out += ['| Indicador | Definição | Fórmula (DAX) | Formato | Polaridade | Meta |', '|---|---|---|---|---|---|']
    for md in [x for x in m['medidas'] if x['tipo'] != 'cor']:
        dax = md['dax'].replace('\n', ' ').replace('|', '\\|')
        out.append(f'| **{md["nome"]}** | {md["descricao"] or "—"} | `{dax}` | {md["formato"]} | '
                   f'{md["polaridade"].replace("_", " ")} | {md["meta_medida"] or "—"} |')
    out += ['', '## Origem dos dados', '', '| Tabela do modelo | Tipo | Fonte · origem | Lida por |', '|---|---|---|---|']
    for t in m['tabelas']:
        leitura = (nome_view(m, t) if t.get('fonte_tipo') == 'sqlserver' else
                   'consulta Power Query da fonte' if t['origem'] else '—')
        out.append(f'| {t["nome"]} | {t["tipo"]} | {(t.get("fonte") or "") + " · " if t["origem"] else ""}'
                   f'{t["origem"] or "gerada no Power Query"} | {leitura} |')
    out += ['', '## Colunas', '']
    for t in m['tabelas']:
        if not t['origem']:
            continue
        out += [f'### {t["nome"]}', '', '| Coluna | Origem | Descrição |', '|---|---|---|']
        for c in t['colunas']:
            origem = c['expressao_sql'] or f'{t["origem"]}.{c["origem"]}'
            out.append(f'| {c["nome"]}{" (oculta)" if c["oculta"] else ""} | `{origem}` | {c["descricao"] or "—"} |')
        out.append('')
    out += ['', '## Relacionamentos', '', '| De (muitos) | Para (um) | Estado | Prova |', '|---|---|---|---|']
    for r in m['relacionamentos']:
        out.append(f'| {r["de"]}[{r["de_coluna"]}] | {r["para"]}[{r["para_coluna"]}] | '
                   f'{"ativa" if r["ativo"] else "inativa"} | {r["prova"]} |')
    if m.get('seguranca'):
        out += ['', '## Segurança (RLS)', '', '| Papel | Tabela | Filtro |', '|---|---|---|']
        for papel in m['seguranca']:
            for r in papel['regras']:
                out.append(f'| {papel["papel"]} | {r["tabela"]} | `{r["filtro"].replace("|", chr(92) + "|")}` |')
    if historico:
        out += ['', '## Histórico de mudanças', '']
        for h in reversed(list(historico)):
            out.append(f'### {h.get("versao") or "sem versão"} — {h["em"]} — aprovado por {h["aprovado_por"]}')
            if h.get('observacao'):
                out.append(f'_{h["observacao"]}_')
            out += [f'- {x}' for x in h.get('mudancas') or []] + ['']
    return '\n'.join(out) + '\n'


def _passos_fontes(m, nome):
    from .tmdl import parametros
    from .sql import fontes_sql
    linhas, n = [], 1
    for f in fontes_sql(m):
        serv, banco = parametros(f)
        linhas.append(f"""{n}. **Banco {f['nome']} (DBA, SQL Server 2016 SP1+).** Revise e rode `sql/{f['nome']}/01_views.sql` no banco
   `{f['banco']}`. Ele cria o schema `{f['esquema_views']}` e uma view por tabela. Dê `SELECT` no schema à conta do
   gateway (linha comentada no fim do arquivo). Parâmetros no Power BI: **{serv}** e **{banco}**.""")
        n += 1
    outras = [f for f in m['fontes'].values() if f['tipo'] != 'sqlserver'
              and any(t.get('fonte') == f['nome'] for t in m['tabelas'])]
    for f in outras:
        nomes = [t['nome'] for t in m['tabelas'] if t.get('fonte') == f['nome']]
        tabs = (f'A tabela {nomes[0]} usa' if len(nomes) == 1 else f'As tabelas {", ".join(nomes)} usam')
        linhas.append(f"""{n}. **Fonte {f['nome']} ({'modelo Power BI' if f['tipo'] == 'powerbi' else 'Power Query'}).** {tabs} a mesma
   consulta Power Query de origem (arquivo, SharePoint, API...). No primeiro *Atualizar*, o Desktop pede a credencial
   dessa fonte. Arquivo em pasta da rede precisa de gateway no serviço; arquivo no SharePoint/OneDrive, não.""")
        n += 1
    return '\n'.join(linhas), n


def leia_me(m, nome, aprovacao, avisos):
    from .sql import fontes_sql
    pend = '\n'.join(f'- {a}' for a in avisos) or '- Nenhuma.'
    fontes, n = _passos_fontes(m, nome)
    sqls = fontes_sql(m)
    arquivos = ''.join(f"| `sql/{f['nome']}/01_views.sql` | as views que o modelo lê da fonte {f['nome']} |\n"
                       f"| `sql/{f['nome']}/02_conferencia.sql` | o total de cada indicador no banco (geral e por ano) |\n"
                       f"| `sql/{f['nome']}/03_qualidade.sql` | chave repetida, órfãos, datas fora do calendário: tudo zero |\n"
                       for f in sqls)
    homolog = ('Rode `03_qualidade.sql` (tudo zero) e `02_conferencia.sql` de cada fonte SQL e compare cada total '
               'com o cartão do painel, sem filtro.' if sqls else 'Compare cada indicador com a fonte de origem, sem filtro.')
    seg = ''
    if m.get('seguranca'):
        papeis = ', '.join(f'**{p["papel"]}**' for p in m['seguranca'])
        seg = (f'\n{n + 5}. **Segurança.** No serviço, em *Segurança* do modelo semântico, inclua as pessoas ou grupos '
               f'em {papeis}. Teste antes no Desktop: *Modelagem > Exibir como*.')
    declaradas = [r for r in m['relacionamentos'] if str(r['prova']).startswith('declarada')]
    decl = ''
    if declaradas:
        decl = ' Ligações declaradas (sem prova na fonte): ' + '; '.join(
            f'{r["de"]}[{r["de_coluna"]}] → {r["para"]}[{r["para_coluna"]}]' for r in declaradas) + \
            '. Confira se não há código repetido no lado "um" nem código sem par.'
    return f"""# {m['projeto']} — como tornar o protótipo real

Gerado pelo Deidara a partir do `argila.json` aprovado por **{aprovacao.get('aprovado_por', '?')}**
em {aprovacao.get('em', '?')}.

## O que tem nesta pasta

| Arquivo | Para quê |
|---|---|
| `{nome}.pbip` | o projeto Power BI: abra no Power BI Desktop |
| `{nome}.SemanticModel/` | o modelo (tabelas, relacionamentos, medidas) em TMDL |
| `{nome}.Report/` | as páginas e os visuais, na mesma posição do protótipo |
{arquivos}| `docs/dicionario_indicadores.md` | definição, fórmula, origem e prova de cada número |
| `docs/medidas.dax` | as medidas em texto (referência) |
| `prototipo.html` | o protótipo aprovado |

## Passo a passo

{fontes}
{n}. **Power BI Desktop** (versão de 2024 em diante). Abra `{nome}.pbip`.
   Se aparecer aviso de recurso em versão prévia, habilite em *Arquivo > Opções > Recursos em
   versão prévia*: "Salvar como Projeto do Power BI (.pbip)" e "Armazenar relatórios no formato
   PBIR". Nas versões em que esses recursos já são padrão, não aparece nada.
{n + 1}. **Conexão.** *Página Inicial > Transformar dados > Editar parâmetros*: confira cada parâmetro. Depois
   *Atualizar*.
{n + 2}. **Homologação.** {homolog}{decl} Divergência = não publique; volte ao dono do indicador.
{n + 3}. **Gerar o .pbix.** *Arquivo > Salvar como* e escolha "Arquivo do Power BI (*.pbix)".
   O `.pbip` continua sendo a fonte versionável (git); o `.pbix` é o que vai para o serviço.
{n + 4}. **Publicar.** *Página Inicial > Publicar* no workspace do time. No serviço, configure o
   gateway (se houver fonte na rede ou banco local) e a atualização agendada.{seg}

## Pendências registradas na aprovação

{pend}

## Regras desta entrega

- Nenhuma linha de dado foi lida para gerar estes arquivos: só a estrutura, pelas receitas do Deidara.
- Toda tabela, coluna e ligação aqui está no catálogo da fonte; cada ligação traz a prova (ou quem a
  declarou) no dicionário de indicadores.
- Mudou algo? Edite o `argila.json`, gere o protótipo de novo, aprove e gere outra vez. Não
  edite o `.pbip` à mão se quiser continuar gerando pelo Deidara.
"""
