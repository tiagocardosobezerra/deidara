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


def _pendencias_por_tema(avisos):
    from .relato import TEMAS, tema_do_aviso
    if not avisos:
        return '- Nenhuma.'
    grupos = {}
    for a in avisos:
        grupos.setdefault(tema_do_aviso(a), []).append(a)
    linhas = []
    for tema, _ in TEMAS + (('Outros', ()),):
        if grupos.get(tema):
            linhas.append(f'**{tema}**\n')
            linhas += [f'- {a}' for a in grupos[tema]]
            linhas.append('')
    return '\n'.join(linhas).strip()


def _onde_ler(m, nome):
    """O primeiro visual que mostra a medida: página e título (o cartão primeiro, que é um número só)."""
    achados = []
    for pg in m['paginas']:
        for v in pg['visuais']:
            usa = [x for x in [v.get('categoria'), v.get('legenda')] + v['valores'] + v['campos'] + v['linhas'] + v['colunas']
                   if x and x.get('tipo') == 'medida' and x.get('nome') == nome]
            if usa:
                achados.append((v['tipo'] != 'cartao', f'{pg["nome"]} › {v.get("titulo") or v["tipo"]}'))
    if not achados:
        dono = next((x['nome'] for x in m['medidas'] if x.get('meta_medida') == nome), None)
        if dono:
            return f'cor/meta de {dono}'
        apoia = [x['nome'] for x in m['medidas'] if nome in (x.get('depende') or [])]
        return f'apoia {", ".join(apoia)}' if apoia else 'não aparece em nenhum visual'
    return sorted(achados, key=lambda x: x[0])[0][1]


def homologacao(m, nome, aprovacao):
    """A folha de homologação: o que conferir, onde anotar e o critério de cada item."""
    from .sql import fontes_sql
    linhas = [f'# {m["projeto"]} — homologação', '',
              f'Painel aprovado por **{aprovacao.get("aprovado_por", "?")}** em {aprovacao.get("em", "?")}. '
              'Preencha depois da primeira atualização no Power BI Desktop. Só publique com tudo marcado.', '',
              '## 1. Qualidade dos dados', '']
    sqls = fontes_sql(m)
    for f in sqls:
        linhas.append(f'- [ ] `sql/{f["nome"]}/03_qualidade.sql` rodou e **todas as linhas deram 0** '
                      '(chave repetida, órfãos, datas fora do calendário)')
    declaradas = [r for r in m['relacionamentos'] if str(r['prova']).startswith('declarada')]
    for r in declaradas:
        linhas.append(f'- [ ] ligação declarada {r["de"]}[{r["de_coluna"]}] → {r["para"]}[{r["para_coluna"]}]: a '
                      'atualização não reclamou de valor duplicado, e o corte por ela não tem "(Em branco)" inesperado')
    if not sqls and not declaradas:
        linhas.append('- [ ] a primeira atualização terminou sem erro')
    linhas += ['', '## 2. Cada indicador bate com a fonte', '',
               'Sem nenhum filtro marcado no painel. Para os de agregação simples, o total do banco sai de '
               '`02_conferencia.sql`; para os outros, confira os componentes (numerador e denominador).', '',
               '| ✓ | Indicador | Onde ler no painel | Como conferir | Total na fonte | Total no painel |',
               '|---|---|---|---|---|---|']
    for md in m['medidas']:
        if md['tipo'] in ('cor', 'meta') or md.get('imagem'):
            continue
        tab = next((t for t in m['tabelas'] if t['nome'] == (md.get('conferencia') or {}).get('tabela')), None)
        da_planilha = tab is not None and tab.get('fonte_tipo') != 'sqlserver'
        como = (f'na própria fonte ({tab["fonte"]}: {tab["origem"]})' if da_planilha else
                '02_conferencia.sql' if md.get('conferencia') else
                f'pelos componentes: {", ".join(md.get("depende") or [])}' if md.get('depende') else 'com o dono do indicador')
        if md.get('estoque'):
            como = '02_conferencia.sql (um número por fim de mês)'
        linhas.append(f'| [ ] | {md["nome"]} | {_onde_ler(m, md["nome"])} | {como} |  |  |')
    linhas += ['', '## 3. Cortes e metas', '',
               '- [ ] cada segmentador muda os números esperados (e só eles)',
               '- [ ] os indicadores com meta mostram a cor certa (verde = bateu a meta)',
               '- [ ] o gestor viu o painel com dados reais e confirmou que os números fazem sentido', '',
               '## 4. Publicação', '',
               '- [ ] salvo como .pbix e publicado no workspace do time',
               '- [ ] atualização agendada configurada (e gateway, se a fonte for local ou de rede)',
               f'- [ ] painel salvo no Memory Card (`deidara.py memory-card enviar ... --status em-uso`)']
    return '\n'.join(linhas) + '\n'


def _passos_fontes(m, nome):
    from .tmdl import parametros
    from .sql import fontes_sql
    linhas, n = [], 1
    for f in fontes_sql(m):
        serv, banco = parametros(f)
        linhas.append(f"""{n}. **[DBA] Banco {f['nome']} (SQL Server 2016 SP1+).** Revise e rode `sql/{f['nome']}/01_views.sql` no banco
   `{f['banco']}`. Ele cria o schema `{f['esquema_views']}` e uma view por tabela. Dê `SELECT` no schema à conta do
   gateway (linha comentada no fim do arquivo). Parâmetros no Power BI: **{serv}** e **{banco}**.""")
        n += 1
    outras = [f for f in m['fontes'].values() if f['tipo'] != 'sqlserver'
              and any(t.get('fonte') == f['nome'] for t in m['tabelas'])]
    for f in outras:
        nomes = [t['nome'] for t in m['tabelas'] if t.get('fonte') == f['nome']]
        tabs = (f'A tabela {nomes[0]} usa' if len(nomes) == 1 else f'As tabelas {", ".join(nomes)} usam')
        linhas.append(f"""{n}. **[Analista] Fonte {f['nome']} ({'modelo Power BI' if f['tipo'] == 'powerbi' else 'Power Query'}).** {tabs} a mesma
   consulta Power Query de origem (arquivo, SharePoint, API...). No primeiro *Atualizar*, o Desktop pede a credencial
   dessa fonte. Arquivo em pasta da rede precisa de gateway no serviço; arquivo no SharePoint/OneDrive, não.""")
        n += 1
    return '\n'.join(linhas), n


def leia_me(m, nome, aprovacao, avisos):
    from .sql import fontes_sql
    pend = _pendencias_por_tema(avisos)
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
{arquivos}| `HOMOLOGACAO.md` | a folha de homologação: o que conferir e onde anotar |
| `docs/dicionario_indicadores.md` | definição, fórmula, origem e prova de cada número |
| `docs/medidas.dax` | as medidas em texto (referência) |
| `prototipo.html` | o protótipo aprovado |

## Passo a passo

{fontes}
{n}. **[Analista] Power BI Desktop** (versão de 2024 em diante). Abra `{nome}.pbip`.
   Se aparecer aviso de recurso em versão prévia, habilite em *Arquivo > Opções > Recursos em
   versão prévia*: "Salvar como Projeto do Power BI (.pbip)" e "Armazenar relatórios no formato
   PBIR". Nas versões em que esses recursos já são padrão, não aparece nada.
{n + 1}. **[Analista] Conexão.** *Página Inicial > Transformar dados > Editar parâmetros*: confira cada parâmetro.
   Depois *Atualizar*.
{n + 2}. **[Analista + dono do indicador] Homologação.** Preencha o `HOMOLOGACAO.md` desta pasta. {homolog}{decl}
   Divergência = não publique; volte ao dono do indicador.
{n + 3}. **[Analista] Gerar o .pbix.** *Arquivo > Salvar como* e escolha "Arquivo do Power BI (*.pbix)".
   O `.pbip` continua sendo a fonte versionável (git); o `.pbix` é o que vai para o serviço.
{n + 4}. **[Analista] Publicar.** *Página Inicial > Publicar* no workspace do time. No serviço, configure o
   gateway (se houver fonte na rede ou banco local) e a atualização agendada.{seg}

## Se algo der errado na primeira atualização

| Mensagem (ou sintoma) | O que fazer |
|---|---|
| pede credencial / "acesso negado" | *Arquivo > Opções > Configurações da fonte de dados*: informe a credencial da fonte; no SQL, confira o `GRANT SELECT` |
| "contém um valor duplicado" ao carregar uma tabela | a chave do lado "um" de uma relação se repete na fonte: rode `03_qualidade.sql` (ou a receita de prova) e trate na origem |
| "não é possível converter o valor ... para o tipo" | uma coluna trouxe um valor de outro tipo: ajuste o tipo na consulta de origem ou na view |
| visual em branco / "(Em branco)" num corte | códigos da fato sem par na dimensão: veja a linha "orfaos" de `03_qualidade.sql` |
| o .pbip não abre ou abre sem páginas | atualize o Power BI Desktop e habilite os recursos em versão prévia do passo de abertura |
| números diferentes do esperado | compare com `02_conferencia.sql`; confira os filtros da página e a definição no `docs/dicionario_indicadores.md` |

## Pendências registradas na aprovação

{pend}

## Regras desta entrega

- Nenhuma linha de dado foi lida para gerar estes arquivos: só a estrutura, pelas receitas do Deidara.
- Toda tabela, coluna e ligação aqui está no catálogo da fonte; cada ligação traz a prova (ou quem a
  declarou) no dicionário de indicadores.
- Mudou algo? Edite o `argila.json`, gere o protótipo de novo, aprove e gere outra vez. Não
  edite o `.pbip` à mão se quiser continuar gerando pelo Deidara.
"""
