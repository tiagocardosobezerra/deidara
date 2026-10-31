# Roteiro: `deidara-fluxo.svg`

**Português** | [English](deidara-fluxo.en.md)

| | |
|---|---|
| Arquivos | `assets/deidara-fluxo.svg` (pt-BR) e `assets/deidara-fluxo-en.svg` |
| Onde | `README.md` / `README.en.md`, seção "Como funciona por dentro", antes da tabela de peças |
| Tela | 1280 × 640, fundo `#0B1220`, grade de 32 px em `#1E2A44` |
| Duração | 36 s em laço, 5 passos |
| `aria-label` / `alt` (pt) | Como o Deidara funciona: receita, catálogo, esboço, validar, protótipo, aceite e gerar |
| `aria-label` / `alt` (en) | How Deidara works: recipe, catalog, draft, validate, prototype, approval and generate |
| Paralelo no Vegapunk | `vegapunk-sonar.svg` (31 s, 4 passos, faixa de progresso, uma legenda por vez) |

## A ideia em uma frase

O sonar do Vegapunk mostra a busca indo de achado em achado e deixando para
trás o que não serve. O fluxo do Deidara mostra a **argila tomando forma**: no
centro, um bloco de argila (o `argila.json`) ganha uma peça de cada vez, e só
gruda o que tem origem conhecida. O que foi adivinhado bate e cai, como o eco
cinza do Vegapunk. Depois a argila vira escultura (protótipo), recebe o "sim"
e explode no projeto.

## Linha do tempo

```css
/* Linha do tempo: 36 s. 1 Você pede 0–4.5 · 2 A estrutura volta 4.5–11 · 3 A argila toma forma 11–21 · 4 O gestor decide 21–28 · 5 Katsu! 28–36 */
```

| Passo | Tempo | Etapas do Deidara (os 7 blocos do fluxo atual) | Comandos | Ensina |
|---|---|---|---|---|
| 1 · Você pede | 0–4,5 s | (Entender) | `novo` | o pedido é em português, com indicadores, cortes e de onde vem cada dado |
| 2 · A estrutura volta | 4,5–11 s | 1 Receita · 2 Catálogo | `receita`, `catalogar` | o Deidara não se conecta a nada; só estrutura volta |
| 3 · A argila toma forma | 11–21 s | 3 Esboço · 4 Validar | `esbocar`, `padroes`, `confirmar`, `validar` | nome só do catálogo, função só do dicionário, ligação só com prova ou pessoa |
| 4 · O gestor decide | 21–28 s | 5 Protótipo · 6 Aceite | `prototipar`, `aprovar` | protótipo fictício, aceite explícito, e o aceite trava a especificação |
| 5 · Katsu! | 28–36 s | 7 Katsu! | `gerar` | o que sai, e o que ainda é tarefa de uma pessoa |

## Elementos fixos (o tempo todo)

- **Faixa de progresso no topo** (y 24–60), igual à do sonar: cinco rótulos
  numerados lado a lado e, embaixo de cada um, um segmento de 4 px. Só o
  rótulo do passo atual fica visível em texto grande no centro da faixa (troca
  com subida de 8 px); os segmentos dos passos já feitos ficam claros
  (`#F1F5F9`), os que faltam ficam `#334155`.
- **Legenda embaixo** (y 590), uma por vez, Inter 20 px, `#CBD5E1`.
- **A argila no centro** (x 640, y 330): a partir do passo 1, um bloco
  arredondado âmbar, de borda irregular (um `path` com cantos suaves), com o
  rótulo `argila.json` em JetBrains Mono. Ela muda de forma a cada passo.

**Texto fixo da faixa.**

| # | pt-BR | en |
|---|---|---|
| 1 | 1 · Você pede | 1 · You ask |
| 2 | 2 · A estrutura volta | 2 · The structure comes back |
| 3 | 3 · A argila toma forma | 3 · The clay takes shape |
| 4 | 4 · O gestor decide | 4 · The manager decides |
| 5 | 5 · Katsu! | 5 · Katsu! |

---

## Passo 1 · Você pede (0–4,5 s)

**Ensina.** O começo é uma conversa, não um formulário: para quem é, quais
indicadores, por quais cortes, de onde vem cada dado. O Deidara separa o que
importa do pedido.

**O que aparece.** Um balão de fala no centro, largo, com o pedido. Palavras
destacadas uma a uma. Embaixo do balão, seis etiquetas pequenas nascem das
palavras. No fim do passo, as etiquetas voam para o centro e viram a argila.

**Texto na tela.**

| Elemento | pt-BR | en |
|---|---|---|
| pedido | Desligamentos por **motivo** e **cargo**, com a **meta de turnover** por **empresa**. O ERP é SQL Server; a meta vem de uma planilha do RH. | Terminations by **reason** and **role**, with the **turnover target** by **company**. The ERP is SQL Server; the target comes from an HR spreadsheet. |
| etiquetas | indicador · corte · corte · meta · fonte: SQL Server · fonte: Excel | KPI · breakdown · breakdown · target · source: SQL Server · source: Excel |
| argila (nasce) | `argila.json` | `argila.json` |
| legenda (1,6–4,0 s) | O Deidara lê o pedido e separa o que importa. | Deidara reads the request and picks out what matters. |

**Movimento.**

| Marca | O que acontece |
|---|---|
| 0,0–0,35 s | o balão sobe 10 px e aparece |
| 0,4–1,4 s | as palavras em negrito ganham fundo `rgba(241,245,249,.16)`, 0,2 s entre elas |
| 1,0–1,6 s | as seis etiquetas aparecem com escala 0,7 → 1, 0,1 s entre elas, coloridas pelo tipo (indicador e meta em âmbar, cortes em laranja, fontes em azul) |
| 1,6 s | a legenda entra |
| 4,0–4,5 s | o balão some; as etiquetas encolhem para 0,6 e voam para o centro (`cubic-bezier(.5,0,.7,1)`); onde elas chegam, a argila nasce com escala 0,6 → 1,12 → 1 |

---

## Passo 2 · A estrutura volta (4,5–11 s)

**Ensina.** A receita vai até a fonte, quem tem acesso roda, e só a estrutura
volta. O que é dado de verdade fica do lado de lá. Cada fonte vira um
catálogo.

**O que aparece.**

- À esquerda, a faixa azul "NA SUA FONTE" (x 0–240), com a parede tracejada
  na borda direita, e dois ícones: banco (ERP) e planilha (Metas). É a mesma
  faixa do fluxo atual, agora vertical.
- A argila manda duas receitas para a esquerda: cartões pequenos com o nome
  do arquivo e uma etiqueta de linguagem.
- De volta, chegam fichas com nomes de tabela e coluna. Elas não vão para a
  argila ainda: formam dois **catálogos** (cartões com cabeçalho azul) à
  esquerda da argila, um por fonte.
- Uma ficha de dado (uma linha de cadastro) tenta voltar junto e é barrada
  pela parede: fica cinza e cai. É o eco cinza deste passo.

**Texto na tela.**

| Elemento | pt-BR | en |
|---|---|---|
| faixa | NA SUA FONTE | AT YOUR SOURCE |
| sob a faixa | o Deidara não se conecta a nada | Deidara connects to nothing |
| receitas | `receita_sql.sql` · SQL / `receita_m.pq` · M | iguais |
| quem roda | quem tem acesso roda e cola o resultado | someone with access runs it and pastes the result |
| catálogo 1 | `catalogos/erp.json` · F_DESLIGAMENTO · F_FUNCIONARIO · F_CARGO · F_MOTIVO_DESLIGAMENTO · N_EMPRESA | iguais |
| catálogo 2 | `catalogos/metas.json` · Metas | iguais |
| ficha barrada | 1043 · Ana S. · 12/03/2024 | igual |
| rótulo da barrada | dado não sai da fonte | data never leaves the source |
| legenda A (5,5–7,8 s) | A receita vai até onde os dados estão. | The recipe goes where the data lives. |
| legenda B (8,0–10,6 s) | Só a estrutura volta: tabelas, colunas, tipos e chaves. | Only the structure comes back: tables, columns, types and keys. |

**Movimento.**

| Marca | O que acontece |
|---|---|
| 4,5–5,1 s | a faixa entra da esquerda; a parede desenha de cima para baixo |
| 5,1–6,3 s | as duas receitas saem da argila e deslizam até os ícones, uma atrás da outra (0,3 s), e são "engolidas" (escala 1 → 0) |
| 6,0 s | cada ícone pulsa uma vez; o texto "quem tem acesso roda e cola o resultado" aparece sob a faixa e fica até 10,6 s |
| 6,8–8,6 s | as fichas atravessam a parede para a direita, 0,25 s entre elas, com rastro azul, e se empilham nos dois catálogos |
| 7,4 s | a ficha de dado parte junto, bate na parede, recua 6 px, perde a cor e cai 30 px; o rótulo aparece e some em 9,4 s |
| 8,6 s | os cabeçalhos dos catálogos acendem (borda `#60A5FA` com brilho de 4 px) |
| 10,6–11,0 s | a faixa da fonte esmaece para 35% e fica assim até o fim (a fonte continua lá, mas a cena muda) |

---

## Passo 3 · A argila toma forma (11–21 s)

**Ensina.** O esboço sai sozinho do pedido e dos catálogos, mas tudo que
entra na argila tem origem: nome do catálogo, função do dicionário, medida de
um padrão, ligação provada ou confirmada por uma pessoa. O que não tem origem
é recusado, e o `validar` diz o que existe no lugar.

**O que aparece.** O passo central, o "sonar" do Deidara.

- A argila cresce e as peças grudam nela em volta, como nós de um mapa:
  tabelas (fatos em âmbar, dimensões em laranja claro) e o calendário.
- Linhas ligam as tabelas. As do ERP são cheias e verdes, com selo "FK do
  banco". A ligação `fMetas → dEmpresa` (entre fontes) chega tracejada e
  âmbar com o rótulo "A CONFIRMAR"; depois uma pessoa confirma e ela fica
  cheia e verde.
- De um canto, a cadeia de medidas do padrão `turnover` entra em fila e gruda
  embaixo da argila: Qtd Desligamento → Headcount → HC Médio → Turnover.
- Dois intrusos tentam grudar e caem como eco cinza: um nome de coluna
  adivinhado e uma função DAX que não existe. Ao lado de cada um, a correção
  que o `validar` sugere.
- Selo final: "validar: 0 erros".

**Texto na tela.**

| Elemento | pt-BR | en |
|---|---|---|
| tabelas | fDesligamento · dMotivoDesligamento · dCargo · dFuncionario · dEmpresa · fMetas · Calendário | iguais (são nomes gerados) |
| selo das ligações do ERP | FK do banco | database FK |
| ligação entre fontes, antes | fMetas → dEmpresa · A CONFIRMAR | fMetas → dEmpresa · TO CONFIRM |
| ligação entre fontes, depois | confirmada por Ana (RH) | confirmed by Ana (HR) |
| cadeia de medidas | Qtd Desligamento → Headcount (estoque na data) → HC Médio → Turnover | Qtd Desligamento → Headcount (stock at date) → HC Médio → Turnover |
| rótulo da cadeia | padrão: turnover | pattern: turnover |
| intruso 1 | `dFuncionario[DATA_DEMISSAO]` | igual |
| correção 1 | não está no catálogo · existe: DATADESLIGAMENTO em F_DESLIGAMENTO | not in the catalog · exists: DATADESLIGAMENTO in F_DESLIGAMENTO |
| intruso 2 | `CALCULA_TURNOVER()` | igual |
| correção 2 | não está no dicionário · use DIVIDE com o padrão turnover | not in the dictionary · use DIVIDE with the turnover pattern |
| selo final | validar: 0 erros | validate: 0 errors |
| legenda A (11,6–15,8 s) | Nome só do catálogo. Função só do dicionário. | Names only from the catalog. Functions only from the dictionary. |
| legenda B (16,0–20,6 s) | Ligação só com prova, ou confirmada por quem conhece o dado. | Links only with proof, or confirmed by someone who knows the data. |

**Movimento.**

| Marca | O que acontece |
|---|---|
| 11,0 s | os catálogos se desmancham em fichas que vão para a argila; a argila cresce (escala 1 → 1,3) e muda de forma (o `path` passa de bloco a um oval com saliências) |
| 11,6 s | primeiro pulso: um anel claro sai da argila e se expande (escala 0,02 → 1, opacidade 0,9 → 0, 1,4 s, linear), como o sonar do Vegapunk |
| 12,2–13,8 s | as sete tabelas acendem em volta, uma a cada 0,25 s, cada uma com escala 0,6 → 1,12 → 1 |
| 13,0 s | intruso 1 entra pela direita, encosta na argila, treme, fica cinza e cai 30 px; a correção aparece ao lado e fica até 15,6 s |
| 13,8–14,8 s | as ligações do ERP desenham do lado muitos para o lado um (`stroke-dashoffset`), 0,2 s entre elas; o selo "FK do banco" aparece na primeira |
| 14,8 s | segundo pulso, saindo de `dEmpresa` (o último achado, como no sonar) |
| 15,2 s | a ligação `fMetas → dEmpresa` desenha tracejada em âmbar com "A CONFIRMAR" |
| 16,4 s | um pequeno cartão de pessoa ("Ana (RH)") encosta na ligação; ela vira cheia e verde, e o rótulo troca para "confirmada por Ana (RH)" |
| 17,2–18,6 s | as quatro medidas entram em fila da esquerda e grudam embaixo da argila, ligadas por setas finas, 0,35 s entre elas |
| 18,2 s | intruso 2 tenta grudar na fila de medidas e cai como o primeiro; a correção fica até 20,2 s |
| 19,4 s | o selo "validar: 0 erros" estala sobre a argila (escala 0,6 → 1,1 → 1, verde) |
| 20,6–21,0 s | os ecos cinza somem; tabelas e ligações encolhem para dentro da argila |

---

## Passo 4 · O gestor decide (21–28 s)

**Ensina.** A argila vira escultura: um protótipo com números fictícios, com
explicação em cada visual e uma aba para aprovar. O aceite é de uma pessoa e
fica gravado com o código da argila e dos catálogos. Mudou depois? Novo
protótipo, novo "sim".

**O que aparece.**

- A argila se transforma numa miniatura de página de painel (no modelo
  `faixa-de-kpis`), 420 × 240, com a faixa "números fictícios" no alto.
- Um ⓘ abre e fecha num cartão.
- A aba "Para aprovar" com três ✓ e o carimbo APROVADO.
- Um cadeado fecha sobre a miniatura com o código do aceite.
- Uma seta de volta, tracejada, sai do cadeado e volta para a argila, com o
  aviso do que acontece se algo mudar. É a mesma seta de volta do fluxo atual.

**Texto na tela.**

| Elemento | pt-BR | en |
|---|---|---|
| arquivo | `argila.prototipo.html` | igual |
| faixa | números fictícios | fictional numbers |
| dica do ⓘ | o que o número significa | what the number means |
| aba | Para aprovar | Para aprovar (aba real, em pt-BR) |
| checklist | ✓ indicadores · ✓ cortes · ✓ pendências | ✓ KPIs · ✓ breakdowns · ✓ open items |
| carimbo | APROVADO | APPROVED |
| comando | `aprovar --por "Gestor de RH"` | igual |
| código | aceite 7F3A·C21E | approval 7F3A·C21E |
| seta de volta | mudou depois do aceite? novo protótipo, novo "sim" | changed after approval? new prototype, new "yes" |
| legenda (22,0–27,6 s) | O gestor aprova o que vai ver, antes de existir. | The manager approves what they will see, before it exists. |

**Movimento.**

| Marca | O que acontece |
|---|---|
| 21,0–21,8 s | a argila se achata e se divide em retângulos que viram a página (trilho, título, três cartões, barras); os números contam de 0 |
| 22,0 s | a legenda entra |
| 22,8 s | o ⓘ abre (escala 0,92 → 1), fica 1,2 s e fecha |
| 24,2 s | a página desliza para a esquerda e a aba "Para aprovar" aparece |
| 24,6–25,5 s | os três ✓ verdes, 0,3 s entre eles |
| 25,8 s | o carimbo APROVADO cai (`stamp`: rotação −10°, escala 1,6 → 1) e o comando aparece embaixo em JetBrains Mono |
| 26,3 s | o cadeado fecha (a alça desce 6 px) e o código aparece |
| 26,8 s | a seta de volta desenha do cadeado até a argila, tracejada em cinza, com o aviso; fica até 27,6 s |
| 27,6–28,0 s | a seta e a legenda somem; a miniatura volta ao centro e encolhe |

---

## Passo 5 · Katsu! (28–36 s)

**Ensina.** Só agora o projeto existe: `.pbip` com TMDL e PBIR, SQL das fontes
e a documentação para homologar. E o que ainda é trabalho de uma pessoa fica
escrito, como a lacuna do sonar do Vegapunk.

**O que aparece.**

- A miniatura vira a estrela "Katsu!" e explode.
- Da explosão saem três cartões de entrega, lado a lado (como os dois cartões
  finais do sonar), cada um com um selo verde.
- Embaixo, uma caixa âmbar com o que falta fazer.
- Por último, a frase de fecho.

**Texto na tela.**

| Elemento | pt-BR | en |
|---|---|---|
| explosão | Katsu! | Katsu! |
| comando | `gerar argila.json -o C:/paineis/turnover` | igual |
| cartão 1, título | Projeto Power BI | Power BI project |
| cartão 1, linhas | `Painel.pbip` · TMDL + PBIR · abre no Desktop, salva como .pbix | `Painel.pbip` · TMDL + PBIR · opens in Desktop, saves as .pbix |
| cartão 1, selo | 24 de 24 JSON válidos | 24 of 24 JSON valid |
| cartão 2, título | SQL das fontes | Source SQL |
| cartão 2, linhas | `01_views.sql` · `02_conferencia.sql` · `03_qualidade.sql` | iguais |
| cartão 2, selo | qualidade: tudo tem que dar zero | quality: everything must be zero |
| cartão 3, título | Para homologar | For sign-off |
| cartão 3, linhas | `HOMOLOGACAO.md` · `LEIA-ME.md` · `dicionario_indicadores.md` | iguais |
| cartão 3, selo | quem faz o quê | who does what |
| caixa do que falta | Falta você: depois da primeira atualização, conferir 5 números com a fonte. | Still on you: after the first refresh, check 5 numbers against the source. |
| fecho | Molda com o que existe. Mostra antes. Explode depois do "sim". | Shapes with what exists. Shows first. Explodes after the "yes". |
| legenda (29,2–33,0 s) | O projeto completo, só depois do aceite. | The complete project, only after approval. |

A caixa "Falta você" repete a frase do README ("Depois da primeira
atualização, confira estes cinco números com a fonte.") e aparece no mesmo
lugar em que o sonar do Vegapunk mostra "Falta você preencher".

**Movimento.**

| Marca | O que acontece |
|---|---|
| 28,0–28,6 s | a miniatura vira a estrela de oito pontas (escala 0,2 → 1, "Katsu!" em Poppins 800); o comando aparece embaixo |
| 28,6–29,2 s | a estrela incha (1 → 1,25) e explode em 16 partículas; o brilho âmbar do fundo dobra por 0,4 s |
| 29,2 s | a legenda entra |
| 29,4–30,4 s | os três cartões sobem 40 px das partículas, 0,3 s entre eles |
| 30,6–31,5 s | os três selos verdes estalam (escala 0,6 → 1,1 → 1), 0,3 s entre eles |
| 32,0 s | a caixa "Falta você" entra de baixo |
| 33,0 s | a legenda sai; a frase de fecho entra no lugar dela |
| 33,0–35,5 s | todos os segmentos da faixa de progresso ficam claros |
| 35,5–36,0 s | tudo some (opacidade 1 → 0), inclusive a faixa da fonte, e o laço volta ao passo 1 |

---

## Movimento reduzido

Com `prefers-reduced-motion: reduce`, a tela mostra um quadro parado que
resume os cinco passos: a faixa de progresso com os cinco segmentos claros, a
faixa "NA SUA FONTE" à esquerda, a argila com as tabelas e as ligações (a de
`fMetas → dEmpresa` já confirmada), o carimbo APROVADO e os três cartões de
entrega. É o conteúdo do fluxo estático atual, reorganizado; nada se perde.

## Erros a evitar

- Mostrar o Deidara "conectando" ou "lendo" o banco: a seta para a fonte é
  sempre uma receita levada por uma pessoa.
- Mostrar a ligação entre fontes ficando verde sozinha: ela só muda quando a
  pessoa chega.
- Escrever a prova à mão: se o passo 3 mostrar uma prova em vez da
  confirmação, ela vem de um resultado colado (`provar --de resultado.txt`),
  com percentuais, nunca linhas.
- Usar "turnover" como contagem de cadastro: a cadeia de medidas mostra
  Headcount como estoque na data e HC Médio no denominador (regra 4 do
  `SKILL.md`).
- Mudar a ordem: Katsu! nunca antes do APROVADO.
