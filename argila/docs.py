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
    out += ['', '## Origem dos dados', '', '| Tabela do modelo | Tipo | Origem no banco | View |', '|---|---|---|---|']
    for t in m['tabelas']:
        out.append(f'| {t["nome"]} | {t["tipo"]} | {t["origem"] or "gerada no Power Query"} | '
                   f'{nome_view(m, t) if t["origem"] else "—"} |')
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


def leia_me(m, nome, aprovacao, avisos):
    f = m['fonte']
    pend = '\n'.join(f'- {a}' for a in avisos) or '- Nenhuma.'
    seg = ''
    if m.get('seguranca'):
        papeis = ', '.join(f'**{p["papel"]}**' for p in m['seguranca'])
        seg = ('\n7. **Segurança.** No serviço, em *Segurança* do modelo semântico, inclua as pessoas ou grupos '
               f'em {papeis}. Teste antes no Desktop: *Modelagem > Exibir como*.')
    return f"""# {m['projeto']} — como tornar o protótipo real

Gerado pelo Deidara a partir do `argila.json` aprovado por **{aprovacao.get('aprovado_por', '?')}**
em {aprovacao.get('em', '?')}.

## O que tem nesta pasta

| Arquivo | Para quê |
|---|---|
| `{nome}.pbip` | o projeto Power BI: abra no Power BI Desktop |
| `{nome}.SemanticModel/` | o modelo (tabelas, relacionamentos, medidas) em TMDL |
| `{nome}.Report/` | as páginas e os visuais, na mesma posição do protótipo |
| `sql/01_views.sql` | as views que o modelo lê (schema `{f['esquema_views']}`) |
| `sql/02_conferencia.sql` | o total de cada indicador direto no banco (geral e por ano), para homologar |
| `sql/03_qualidade.sql` | chave repetida, órfãos e datas fora do calendário: tudo tem que dar zero |
| `docs/dicionario_indicadores.md` | definição, fórmula, origem e prova de cada número |
| `docs/medidas.dax` | as medidas em texto (referência) |
| `prototipo.html` | o protótipo aprovado |

## Passo a passo

1. **Banco (DBA, SQL Server 2016 SP1+).** Revise e rode `sql/01_views.sql` no banco `{f['banco']}`. Ele cria o
   schema `{f['esquema_views']}` e uma view por tabela do modelo. Dê `SELECT` no schema à conta do
   gateway (a linha comentada no fim do arquivo).
2. **Power BI Desktop** (versão de 2024 em diante). Abra `{nome}.pbip`.
   Se aparecer aviso de recurso em versão prévia, habilite em *Arquivo > Opções > Recursos em
   versão prévia*: "Salvar como Projeto do Power BI (.pbip)" e "Armazenar relatórios no formato
   PBIR". Nas versões em que esses recursos já são padrão, não aparece nada.
3. **Conexão.** *Página Inicial > Transformar dados > Editar parâmetros*: preencha
   **Servidor** e **Banco** (hoje: `{f['servidor']}` / `{f['banco']}`). Depois *Atualizar*.
4. **Homologação.** Rode `sql/03_qualidade.sql` (tudo zero) e `sql/02_conferencia.sql` e compare cada total com o cartão do
   painel, sem nenhum filtro marcado. Divergência = não publique; volte ao dono do indicador.
5. **Gerar o .pbix.** *Arquivo > Salvar como* e escolha "Arquivo do Power BI (*.pbix)".
   O `.pbip` continua sendo a fonte versionável (git); o `.pbix` é o que vai para o serviço.
6. **Publicar.** *Página Inicial > Publicar* no workspace do time. No serviço, configure o
   gateway e a atualização agendada.{seg}

## Pendências registradas na aprovação

{pend}

## Regras desta entrega

- Nenhum dado do banco foi lido para gerar estes arquivos: só a estrutura (via Vegapunk).
- Toda tabela, coluna e ligação aqui veio do `detalhar` do Vegapunk; as ligações trazem a
  prova no dicionário de indicadores.
- Mudou algo? Edite o `argila.json`, gere o protótipo de novo, aprove e gere outra vez. Não
  edite o `.pbip` à mão se quiser continuar gerando pelo Deidara.
"""
