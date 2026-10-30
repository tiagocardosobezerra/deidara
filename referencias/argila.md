# argila.json — a especificação do painel

Um arquivo JSON (UTF-8) por painel. Exemplo completo:
[../exemplos/aurora/argila.json](../exemplos/aurora/argila.json).

## Raiz

| Campo | Obrigatório | O que é |
|---|---|---|
| `projeto` | sim | nome do painel (vira o nome do .pbip) |
| `fontes` | sim | `{"nome": {"catalogo": "caminho do catálogo", ...}}`; fonte SQL Server aceita também `servidor`, `banco` (valores iniciais dos parâmetros), `esquema_origem` (padrão `dbo`) e `esquema_views` (padrão `bi`). Ver [fontes.md](fontes.md) |
| `versao` | recomendado | versão do painel (ex.: `1.0`), vai para o histórico de mudanças |
| `descricao`, `publico`, `responsavel` | não | aparecem no protótipo e na documentação |
| `modelo` | não | o layout das páginas: `faixa-de-kpis`, `coluna-de-kpis`, `secoes-com-rolagem`, `trilho-escuro`, `kpis-clicaveis`, `historia-longa` ou `padrao` (o sem `modelo`); ver [modelos.md](modelos.md) |
| `tema` | não | `cores` (lista hex, a 1ª é a principal), `fundo`, `texto`; ou `{"paleta": "matrix-escuro"}` (paletas dos dashboards de origem: `contraste-executivo`, `matrix-escuro`, `azul-noturno`, `azul-carros`); ou `{"arquivo": "temas/tema.json"}`, um tema JSON do Power BI (do time ou da comunidade), com o caminho a partir do `argila.json`, que vai inteiro no relatório; o `validar` confere o contraste ([design.md](design.md)) |
| `tabelas` | sim | tabelas do modelo |
| `relacionamentos` | não | ligações entre tabelas do modelo |
| `calendario` | não | tabela de datas gerada |
| `medidas` | sim | os indicadores |
| `grupo_calculo` | não | `{"nome": "Período", "itens": ["atual", "acumulado_ano", "ano_anterior", "variacao_ano_anterior"]}`: um grupo de cálculo que aplica a conta de tempo escolhida a todas as medidas do visual (itens: `atual`, `acumulado_ano`, `ano_anterior`, `variacao_ano_anterior`, `mes_anterior`, `variacao_mes_anterior`, `movel_12m`; as variações saem em percentual). Pede `calendario`. Ponha `{"tipo": "botoes", "campo": "Período[Período]"}` na página |
| `paginas` | sim | as páginas e os visuais |
| `seguranca` | não | papéis de segurança por linha (RLS) |

## tabelas

```json
{"nome": "dCargo", "tipo": "dimensao", "fonte": "erp", "origem": "F_CARGO",
 "colunas": [{"coluna": "CODCARGO", "nome": "Cód. Cargo"}, "DESCRICAOCARGO"],
 "filtro": "t.ATIVO = 1"}
```

- `nome`: nome no Power BI. Convenção: `f` + nome para fato, `d` para dimensão.
- `tipo`: `fato` ou `dimensao`.
- `fonte`: nome da fonte em `fontes` (pode omitir quando há uma só).
- `origem`: tabela ou consulta, **exatamente** como está no catálogo da fonte.
- `colunas`: texto (nome igual à origem) ou objeto com `coluna` (origem),
  `nome` (amigável), `formato` (`inteiro`, `decimal`, `moeda`, `percentual`,
  `data`), `oculta`, `descricao` (padrão: a do catálogo) e `tipo` (só quando
  a fonte não trouxe o tipo: `inteiro`, `decimal`, `real`, `data`,
  `datahora`, `hora`, `logico`, `texto`).
- `filtro`: só fonte SQL Server; entra no `WHERE` da view como está (o alias
  da origem é `t`). Não é conferido: revise o SQL. Nas outras fontes, filtre na
  própria consulta Power Query.

Colunas de ligação que você não listou entram sozinhas, ocultas.

## relacionamentos

```json
{"de": "fDesligamento", "para": "dMotivo"}
{"de": "fMovimento", "para": "dData", "via": ["DATAPAGAMENTO"], "ativo": false}
{"de": "fMeta", "para": "dEmpresa",
 "declarada": {"campos": [["Cód. Empresa", "CODEMPRESA"]], "por": "Ana (RH)", "motivo": "mesmo código do ERP"}}
```

- `de` = lado muitos (a filha), `para` = lado um (a mãe).
- A ligação vem do catálogo da fonte (FK do banco ou relação do modelo Power
  BI de origem). Chave composta vira a coluna oculta `Chave <para>` nas duas
  pontas (na view ou no Power Query): o Power BI só relaciona por uma coluna.
- `via`: os campos da filha, quando há mais de uma ligação entre as tabelas.
- `ativo`: só uma relação ativa por par de tabelas.
- `declarada`: entre fontes diferentes ou sem prova, depois de confirmar os
  campos com o dono do dado; `por` é obrigatório; `prova` (opcional) é o bloco
  impresso pelo `deidara.py provar` ([descoberta.md](descoberta.md)).

## calendario

```json
{"nome": "dCalendario", "inicio": 2020, "fim": 2026,
 "datas": [{"tabela": "fDesligamento", "coluna": "Data do Desligamento"},
           {"tabela": "fDesligamento", "coluna": "Data de Aviso", "ativo": false}]}
```

Gera a tabela (Power Query) com `Data`, `Ano`, `Mês`, `Nome do Mês`,
`Trimestre`, `Ano-Mês`, `Mês/Ano` (ordenada certo) e marca como tabela de
datas. As colunas de `datas` viram `date` na view (sem hora).

## medidas

Tipos prontos (preferidos: validação completa e consulta de conferência):

```json
{"nome": "Headcount", "agregacao": "contagem_linhas", "tabela": "dColaborador", "formato": "inteiro"}
{"nome": "Remuneração Total", "agregacao": "soma", "coluna": "dColaborador[Remuneração]", "formato": "moeda"}
{"nome": "Turnover", "tipo": "divisao", "numerador": "Desligamentos", "denominador": "Headcount", "formato": "percentual"}
{"nome": "Desligamentos Acum. Ano", "tipo": "acumulado_ano", "base": "Desligamentos"}
```

- `agregacao`: `soma`, `media`, `minimo`, `maximo`, `contagem`,
  `contagem_distinta` (ignora em branco), `contagem_linhas` (esta pede `tabela`).
- `tipo`: `divisao` (DIVIDE, sem erro de divisão por zero), `acumulado_ano`,
  `ano_anterior`, `variacao_ano_anterior`, `variacao_mes_anterior`,
  `media_mensal` (média dos valores de fim de mês no período) e `movel_12m`
  (estas pedem `calendario` e `base`; nenhuma mostra valor em mês futuro).
- `estoque_na_data`: quantos estão "dentro" no último dia do período
  (headcount ativo, contratos vigentes). `entradas` = coluna de data de
  entrada; a saída é `fim` (coluna de data na mesma tabela, em branco =
  ainda dentro) **ou** `saidas` (coluna de data de outra tabela, ex.: a fato
  de desligamentos). Não precisa de relacionamento com o calendário.
- `svg_barra_meta`: uma imagem por linha de tabela com a barra do valor de
  `medida` contra a linha da meta dela, no mesmo eixo para todas as linhas de
  `categoria` (a coluna das linhas). A `medida` precisa ter `meta`. Só em
  tabela, com `categoria` entre os campos. Ver [svg.md](svg.md).
- `dax`: DAX livre, para o que os tipos não cobrem. O Deidara confere toda
  referência `Tabela[Coluna]` e `[Medida]` e toda função contra o dicionário
  (função inexistente é erro), mas não a lógica. Ver [metricas.md](metricas.md).
  Se o DAX devolve SVG (`data:image/svg+xml...`), ele ganha a categoria Image
  URL no modelo e passa pela conferência de [svg.md](svg.md); só aparece em
  tabela ou matriz.

```json
{"nome": "Headcount", "tipo": "estoque_na_data", "entradas": "dColaborador[Data de Admissão]",
 "saidas": "fDesligamento[Data do Desligamento]"}
{"nome": "HC Médio", "tipo": "media_mensal", "base": "Headcount"}
{"nome": "Turnover", "tipo": "divisao", "numerador": "Desligamentos", "denominador": "HC Médio",
 "formato": "percentual", "polaridade": "menor_melhor", "meta": 0.05}
{"nome": "Turnover x Meta", "tipo": "svg_barra_meta", "medida": "Turnover", "categoria": "dEmpresa[Empresa]"}
{"nome": "Status da meta", "tipo": "svg_pilula", "medida": "Turnover", "categoria": "dEmpresa[Empresa]"}
{"nome": "Variação", "tipo": "svg_seta", "medida": "Desligamentos", "comparar": "Desligamentos Ano Anterior", "categoria": "dCargo[Cargo]"}
{"nome": "Selo da posição", "tipo": "svg_posicao", "medida": "Desligamentos", "categoria": "dCargo[Cargo]"}
{"nome": "Posição", "tipo": "posicao", "medida": "Desligamentos", "categoria": "dCargo[Cargo]"}
{"nome": "% acumulado", "tipo": "pareto", "medida": "Desligamentos", "categoria": "dCargo[Cargo]"}
{"nome": "3 mais e 3 menos", "tipo": "melhores_piores", "medida": "Desligamentos", "categoria": "dMotivo[Motivo]", "n": 3}
{"nome": "Perfil do cargo", "tipo": "svg_radar", "medidas": ["Headcount", "Remuneração Média", "Turnover"], "categoria": "dCargo[Cargo]"}
{"nome": "Bolha do custo", "tipo": "svg_bolha", "medida": "Remuneração Total", "categoria": "dCargo[Cargo]", "colunas": "dEmpresa[Empresa]"}
{"nome": "Desvio", "tipo": "svg_variacao", "medida": "Headcount", "comparar": "Headcount Ano Anterior", "categoria": "dEmpresa[Empresa]"}
{"nome": "Cargos mais caros", "tipo": "lista_top", "medida": "Remuneração Total", "categoria": "dCargo[Cargo]", "n": 5}
{"nome": "X Turnover", "tipo": "jitter", "medida": "Turnover", "categoria": "dCargo[Cargo]"}
{"nome": "Impacto Desligamentos", "tipo": "impacto", "medida": "Desligamentos", "comparar": "Desligamentos Ano Anterior", "categoria": "dCargo[Cargo]"}
{"nome": "Estrelas", "tipo": "svg_estrelas", "medida": "Headcount", "categoria": "dEmpresa[Empresa]"}
{"nome": "Progresso", "tipo": "svg_progresso", "medida": "Turnover", "categoria": "dEmpresa[Empresa]"}
```

Medidas por linha de tabela (todas pedem `medida` e `categoria`, a coluna das linhas, e ficam em branco no total):

- `svg_pilula`: "Na meta" ou "Fora da meta" (a `medida` precisa de `meta`).
- `svg_seta`: seta do valor de `comparar` (anterior) até o atual, no mesmo eixo para todas as linhas; verde se
  melhorou pela polaridade.
- `svg_posicao`: selo redondo com a posição; os três primeiros na cor de destaque.
- `svg_radar`: em vez de `medida`, `medidas` (3 a 8, um eixo cada); cada eixo vai de zero ao maior valor entre
  as linhas visíveis. A tabela sai com a imagem em 64 x 64.
- `svg_bolha`: para a matriz; `categoria` é a coluna das linhas e `colunas` a das colunas. O raio segue a raiz do
  valor (a área fica proporcional), no mesmo eixo para a matriz toda.
- `svg_variacao`: barra do desvio (`medida` menos `comparar`) a partir de um eixo no centro, no estilo IBCS; verde
  ou vermelha pela polaridade.
- `svg_estrelas`: cinco estrelas, a parte amarela na largura da nota (de 0 a 5). Com `maximo` (número), a nota é
  o valor sobre ele (ex.: `5` numa pesquisa de 1 a 5); sem ele, a melhor linha visível vale cinco, pela
  polaridade.
- `svg_progresso`: cartão de 120 x 34 com "87% da meta" e a barra, verde ou vermelha pela polaridade (a `medida`
  precisa de `meta`). Feito para o `marcador` do mapa; na tabela, prefira `svg_barra_meta`.
- Qualquer uma destas também serve de `marcador` no mapa, se a `categoria` for a coluna do `local`.
- `posicao`: o número da posição (RANKX). `pareto`: o percentual acumulado do maior para o menor.
  `melhores_piores`: a medida só nos `n` primeiros e nos `n` últimos (a linha some no resto).
- `lista_top`: texto com os `n` primeiros e o valor de cada um (TOPN e CONCATENATEX), para um cartão.
- `leitura` (o Tobi): a frase de leitura, para um cartão. Pede `medida`, `comparar` (a do ano anterior) e
  `categoria` (a coluna de quem puxou): "Desligamentos: subiu 38 contra o ano anterior (730 → 768), piorou; Cargo D
  explica 61% da alta." O "explica X%" só sai em medida aditiva (soma, contagem); em taxa, a frase diz onde a
  variação foi maior. "Melhorou" e "piorou" seguem a polaridade.
  `lista_top` e `leitura` são as únicas destas que funcionam fora da tabela.
- `jitter` e `impacto` são as duas da causa raiz, feitas para o eixo de um gráfico (a `categoria` do visual é a
  mesma coluna). `jitter`: o X do jitter plot, entre 0 e 1, que espalha os pontos pela posição no ranking (sem
  sorteio: o desenho não muda a cada atualização); vai no `x` da `dispersao`, com o indicador no `y`, e o eixo X
  sai escondido. `impacto`: `medida` menos `comparar` em cada item (quem mais mexeu no total entre os dois
  períodos); gera também `Cor <nome>` (verde quando ajudou o indicador, vermelho quando atrapalhou, pela
  polaridade), que pinta as barras sozinha. Vai em `barras` ou `colunas`, com uma medida só.

Medidas que trazem uma técnica inteira (o Deidara escreve a medida e, quando precisa, uma **tabela auxiliar**
calculada em DAX, sem fonte nem relacionamento, que só o segmentador de botões usa):

```json
{"nome": "Indicador escolhido", "tipo": "escolha", "opcoes": {"Pessoas": "Headcount", "Custo": "Remuneração Total"}}
{"nome": "Quadro ou custo", "tipo": "alternar", "rotulo": "Ver custo", "desligado": "Headcount", "ligado": "Remuneração Total"}
{"nome": "Cor do destaque", "tipo": "cor_destaque", "categoria": "dCargo[Cargo]"}
{"nome": "Aviso do teto", "tipo": "aviso", "medida": "Remuneração Média", "categoria": "dCargo[Cargo]"}
{"nome": "Iniciais da empresa", "tipo": "svg_iniciais", "categoria": "dEmpresa[Empresa]"}
{"nome": "Dispersão dos cargos", "tipo": "svg_dispersao", "categoria": "dCargo[Cargo]", "x": "Headcount", "y": "Remuneração Média"}
{"nome": "Faixa HTML", "tipo": "html_kpis", "medidas": ["Headcount", "Turnover"]}
{"nome": "Espinha do turnover", "tipo": "svg_espinha", "medida": "Turnover", "cortes": ["dEmpresa[Empresa]", "dCargo[Cargo]"], "n": 3}
```

- `escolha`: a medida que vale a opção escolhida (`SWITCH` sobre a tabela `<nome> (opções)`); `opcoes` é uma
  lista de medidas ou `{"rótulo": "medida"}`. Com formatos diferentes, a medida ganha formato dinâmico (o modelo
  passa para o nível de compatibilidade 1601). Vai no visual `abas`.
- `alternar`: a chave liga/desliga; vale `desligado` e, com o botão selecionado, `ligado` (tabela `<nome>
  (chave)` com uma linha só). Gera também as duas imagens da chave. Vai no visual `alternar`.
- `cor_destaque`: cópia solta da coluna (tabela `Destacar <coluna>`); a cor de destaque para o que foi escolhido
  num segmentador sobre essa cópia, cinza para o resto (tudo aceso quando nada foi escolhido). Vai no `"cor"` de
  barras ou colunas.
- `aviso`: o texto "⚠ 3 de 8 fora da meta de ...: A, B, C" (os mais distantes da meta primeiro), vazio quando
  ninguém está fora; gera também `<nome> · fundo`, que pinta o fundo de vermelho claro só quando avisa. A `medida`
  precisa de `meta`. Vai no visual `aviso`.
- `svg_iniciais`: círculo com as iniciais do item (cinza e, na `(ligado)`, na cor de destaque), para a `imagem`
  do segmentador de botões.
- `svg_dispersao`: a dispersão inteira numa imagem SVG; cada eixo vai do menor ao maior valor, com folga.
  `imagem` (opcional) é a coluna ou medida com a imagem de cada ponto, em `data:image/...` (base64): link externo
  não carrega dentro do SVG. Sem `imagem`, cada ponto é um círculo com as iniciais. Vai no visual `imagem`.
- `html_kpis`: um bloco HTML por medida, com a cor da meta; vai no visual `html`.
- `svg_espinha`: a espinha de peixe (Ishikawa) numa imagem SVG. A cabeça é a `medida`; cada coluna de `cortes`
  (2 a 6) vira uma espinha com os `n` itens (1 a 5, padrão 3) piores que a média do corte, do pior para o menos
  ruim. "Pior" segue a polaridade. Vai no visual `imagem`.
- `ordem` (opcional): `maior_primeiro` ou `menor_primeiro`; o padrão segue a polaridade da `medida`.

Comuns a todas: `formato` (padrão: `inteiro` para contagem e estoque,
`percentual` para variação, o da base para tempo, `decimal` no resto),
`descricao` (obrigatória na prática: regra 4), `pasta` (display folder),
`tabela` (onde a medida mora; padrão: a tabela da coluna ou a primeira
fato), `oculta`, `polaridade` (`maior_melhor` ou `menor_melhor`) e `meta`.

**Meta.** Um número gera a medida `Meta <nome>`; o nome de outra medida usa
essa medida como meta. Toda meta gera também `Cor <nome>` (oculta), verde
quando bate a meta pela polaridade e vermelha quando não bate. O cartão
mostra "Meta: …" no título e pinta o valor; tabela e matriz pintam a
coluna; o medidor usa a meta como alvo. Em barras, colunas, linha e área,
`"meta": true` (ou o nome da medida de meta) desenha a linha tracejada "Meta"
no eixo; só sai com meta fixa (número), e o `validar` avisa quando a meta
muda com o filtro.

## paginas

```json
{"nome": "Turnover", "descricao": "…", "visuais": [
  {"tipo": "segmentador", "campo": "dCalendario[Ano]"},
  {"tipo": "cartao", "medida": "Turnover"},
  {"tipo": "medidor", "medida": "Turnover", "meta": "Meta Turnover"},
  {"tipo": "colunas", "categoria": "dCalendario[Mês/Ano]", "valores": ["Desligamentos"], "legenda": "dMotivo[Motivo]"},
  {"tipo": "barras",  "categoria": "dCargo[Cargo]", "valores": ["Headcount"]},
  {"tipo": "linha",   "categoria": "dCalendario[Mês/Ano]", "valores": ["A", "B"]},
  {"tipo": "rosca",   "categoria": "dMotivo[Motivo]", "valores": ["Desligamentos"]},
  {"tipo": "tabela",  "campos": ["dCargo[Cargo]", "Headcount"]},
  {"tipo": "matriz",  "linhas": ["dCargo[Cargo]"], "colunas": ["dCalendario[Trimestre]"], "valores": ["Desligamentos"]},
  {"tipo": "botoes",  "campo": "dCalendario[Ano]"},
  {"tipo": "cartoes", "medidas": ["Desligamentos", "Desligamentos Ano Anterior", "Var. Desligamentos A/A"]},
  {"tipo": "decomposicao", "medida": "Desligamentos", "cortes": ["dMotivo[Motivo]", "dCargo[Cargo]"]},
  {"tipo": "dispersao", "categoria": "dEmpresa[Empresa]", "x": "Headcount", "y": "Turnover", "tamanho": "Desligamentos"},
  {"tipo": "area",    "categoria": "dCalendario[Mês/Ano]", "valores": ["Desligamentos Acum. Ano"]},
  {"tipo": "mapa",    "local": "dLoja[Cidade]", "valores": ["Vendas"]}
]}
```

- `botoes`: segmentador de botões (as opções lado a lado); para poucas opções.
- `cartoes`: o cartão novo do Power BI, com vários indicadores no mesmo bloco.
- `decomposicao`: árvore de decomposição; a medida em Analisar, os `cortes` em Explicar por, na ordem.
- `dispersao`: um ponto por `categoria`, com `x`, `y` e, opcional, `tamanho` (medidas).
- `area`: como `linha`, com a área preenchida.
- `mapa`: Azure Maps com bolhas do tamanho da medida no `local` (o administrador precisa liberar o Azure Maps);
  com `legenda`, cada bolha vira uma pizza com a composição. Com `"marcador": "<medida de imagem>"` (no lugar de
  `valores`), cada ponto vira a imagem SVG da medida (`svg_estrelas`, `svg_progresso`, `svg_pilula`...). Com
  `"camada": "colunas"`, as bolhas dão lugar às colunas 3D, da altura da medida (incline o mapa para ver).

Técnicas do Power BI Design Files que saem prontas:

```json
{"tipo": "abas", "medida": "Indicador escolhido"}
{"tipo": "alternar", "medida": "Quadro ou custo"}
{"tipo": "aviso", "medida": "Aviso do teto"}
{"tipo": "botoes", "campo": "Destacar Cargo[Cargo]", "icone": true}
{"tipo": "botoes", "campo": "dEmpresa[Empresa]", "imagem": "Iniciais da empresa"}
{"tipo": "barras", "categoria": "dCargo[Cargo]", "valores": ["Remuneração Total"], "cor": "Cor do destaque"}
{"tipo": "colunas", "categoria": "dEmpresa[Empresa]", "valores": ["Remuneração Média"], "meta": true}
{"tipo": "setas", "categoria": "dEmpresa[Empresa]", "medida": "Headcount", "comparar": "Headcount Ano Anterior"}
{"tipo": "skyline", "categoria": "dCalendario[Mês/Ano]", "legenda": "dMotivo[Motivo]", "valores": ["Desligamentos"]}
{"tipo": "imagem", "medida": "Dispersão dos cargos"}
{"tipo": "html", "medida": "Faixa HTML"}
{"tipo": "vegalite", "categoria": "dCargo[Cargo]", "valores": ["Remuneração Total"]}
```

- `abas`: segmentador de botões sobre as opções de uma medida `escolha`, uma aba por opção, com a barra de
  destaque em cima da escolhida; só uma por vez e a primeira já vem escolhida.
- `alternar`: um botão só, com a imagem da chave desligada e ligada; o `titulo` padrão é o `rotulo`.
- `aviso`: a faixa de aviso (cartão novo) com o texto da medida `aviso`; fica no canto de cima da página.
- `botoes` com `"icone": true`: o ícone de selecionado no botão; com `"imagem"`: a imagem de cada item vem da
  medida (e da `(ligado)` quando o botão está escolhido).
- `"cor"` em barras ou colunas (uma série só): a cor de cada barra vem da medida (`cor_destaque`).
- `"meta"` em barras, colunas, linha ou área: `true` (a meta da medida) ou o nome da medida de meta; vira a
  linha tracejada "Meta" no eixo, só com meta fixa.
- `setas`: do valor de `comparar` (ponto cinza) até o de `medida` (ponto na cor de destaque), com a variação em
  percentual; são as barras de erro do gráfico de barras nativo, com as barras invisíveis.
- `skyline`: colunas empilhadas com um respiro entre os blocos; `legenda` é obrigatória.
- `imagem`: uma medida de imagem ocupando o cartão novo inteiro (`svg_dispersao`, `svg_radar`...).
- `html` e `vegalite`: visuais certificados do AppSource (HTML Content e Deneb), não nativos. O `validar` avisa:
  o administrador precisa liberar visuais do AppSource, e quem abre baixa o visual na primeira vez. O
  `vegalite` sai com um pirulito (linha e ponto) da primeira medida; `spec` troca pela sua especificação
  Vega-Lite (os campos têm o nome que aparece no modelo, e os dados vêm de `{"name": "dataset"}`).

Página com `"ajuda": true` ganha o botão "?" no canto de baixo, que leva a uma página escondida com uma nota por
cima de cada visual (o título e o que cada indicador significa, das definições) e o botão Voltar.

Página com `"tour": true` ganha o botão "Tour guiado", que leva a uma página escondida com os mesmos visuais e,
por cima, o tour no HTML Content (versão certificada): um passo por visual (até 8, na ordem do layout), com
holofote, o título e as definições, e os botões Próximo, Voltar e Encerrar. É só HTML e CSS, sem script: a
versão certificada aceita. O Deidara gera a medida `Tour · <página>` (oculta) e o protótipo roda o mesmo tour.
A história longa fica sem tour (é uma página só, que rola).

Página com `"detalhe": "dCargo[Cargo]"` é de **detalhamento** (drillthrough): fica fora da navegação, e no
Power BI a pessoa clica com o botão direito num cargo de qualquer página e escolhe Detalhar; a página abre
filtrada por aquele cargo, com o botão Voltar no canto. Página com `"dica": true` é **de dica** (tooltip): 320 x
240, os visuais um embaixo do outro (até 4), fora da navegação; um visual de outra página com
`"dica": "<nome da página de dica>"` mostra essa página ao passar o mouse, no lugar da dica padrão. No
protótipo, as duas aparecem como abas ("Detalhe · ..." e "Dica · ...") para o gestor aprovar.

```json
{"nome": "Cargo em detalhe", "detalhe": "dCargo[Cargo]", "visuais": [...]}
{"nome": "Resumo do cargo", "dica": true, "visuais": [{"tipo": "cartao", "medida": "Headcount"}]}
{"tipo": "barras", "categoria": "dCargo[Cargo]", "valores": ["Headcount"], "dica": "Resumo do cargo"}
```

```json
{"tipo": "tabela", "campos": ["dCargo[Cargo]", "Desligamentos"]}
```

Coluna é sempre `Tabela[Coluna]` (nomes do modelo); medida é o nome solto.
`titulo` é opcional em qualquer visual. A posição é automática e igual no
protótipo e no Power BI: o `modelo` do painel ([modelos.md](modelos.md)) põe
filtros, cartões, gráficos e tabelas cada um na sua região; sem `modelo`,
segmentadores no topo, cartões e medidores, gráficos em duas colunas e
tabelas/matrizes em largura inteira.

`id` (opcional, em qualquer visual): nome fixo do visual no PBIR. Sem ele, o
nome sai de página + tipo + título, e reordenar os visuais não muda nada.

## seguranca (RLS)

```json
"seguranca": [
  {"papel": "Gestor da empresa", "descricao": "Cada gestor vê só a própria empresa.",
   "regras": [{"tabela": "dEmpresa", "filtro": "dEmpresa[E-mail do Gestor] = USERPRINCIPALNAME()"}]}
]
```

Cada regra é um filtro DAX booleano sobre uma tabela do modelo (as colunas são
conferidas). Vira `roles/<papel>.tmdl`; os membros de cada papel se configuram
no serviço (LEIA-ME). A coluna com o e-mail precisa estar no catálogo de uma
fonte, como qualquer outra. Funções do filtro são conferidas no dicionário.

## Versões e mudanças

Cada `aprovar` grava o retrato do painel aprovado e, a partir do segundo, a
lista do que mudou (indicador novo, fórmula alterada, visual que saiu…), que
vira o "Histórico de mudanças" do dicionário de indicadores.

```bash
python3 deidara.py diff argila.json                 # contra a última aprovação
python3 deidara.py diff argila.json --contra v1.json  # contra outro argila
```

Uma fórmula que muda é destacada ("FÓRMULA mudou (o número muda)"): avise
quem consome o painel antes de publicar. O `gerar` também recusa uma
aprovação feita com outra versão do Deidara.
