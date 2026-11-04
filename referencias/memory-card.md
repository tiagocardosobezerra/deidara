# Memory Card: o cartão do time, o mesmo do Vegapunk

Carregado sob demanda pelo `SKILL.md`. Como o memory card de um videogame:
cada painel aprovado fica salvo (um "save"), com versão e histórico, para ser
carregado de novo quando precisar. E cada indicador também: é aqui que o time
guarda a **definição oficial** de cada número.

**Um cartão só, um nível por solução.** O cartão é UM repositório git do
time no GitHub, **`memory-card`**, privado por padrão, o mesmo que o Vegapunk
usa: cada save fica em `saves/<solucao>/<categoria>/<secao>/<artigo>/`. O
Vegapunk grava em `saves/vegapunk/`; o Deidara, em **`saves/deidara/`**.

O Deidara só grava `saves/deidara/` e o `CATALOGO.md` da raiz. O catálogo
lista os saves de **todas** as soluções, no mesmo formato que o Vegapunk gera
(byte a byte, com teste): quem enviar por último, Deidara ou Vegapunk, escreve
o mesmo arquivo, sem um desfazer o do outro. O Deidara nunca altera os saves
das outras soluções nem o `README.md` de um cartão que já existe, e só commita
o que é seu (arquivos pendentes de outras pessoas ou soluções ficam como
estão). Antes de gravar, ele traz o que os outros enviaram (`git pull`). Qual é
o cartão fica só nesta máquina (`~/.deidara/memory_card.json`, fora do git e da
distribuição).

**Os catálogos nunca vão para o cartão.** O cartão guarda o `argila.json`
aprovado, o dicionário de indicadores e o protótipo; a estrutura das fontes
fica com quem tem acesso a elas, e o `conferir` usa os catálogos locais.

## O que é preciso

- O [GitHub CLI](https://cli.github.com/) (`gh`) instalado e autenticado
  (`gh auth login`). O envio usa a sua autenticação: nenhum token fica na skill.
- O `git`.

Funciona no Claude Code (ou num terminal) da máquina onde o cartão está
clonado. Numa sandbox sem o `gh` autenticado (como a do claude.ai), os comandos
recusam com uma mensagem que diz isso, e o Claude avisa em vez de prometer o
envio. Sem GitHub, `iniciar` sem `--repo` cria um cartão local (git sem remoto).

## Criar o cartão (uma vez)

```bash
python3 deidara.py memory-card iniciar --repo DONO/memory-card
```

- Se o cartão do time já existe, ele é usado (e recusado se estiver público);
  se a pasta `~/memory-card` já é um clone dele (o do Vegapunk, por exemplo), o
  Deidara usa o mesmo clone. Ligar a um cartão que já existe não grava nada nele.
- Se não existe, ele é criado **privado**, com o `README.md` e o `CATALOGO.md`
  da raiz.
- A pasta `saves/deidara/` nasce no primeiro envio.
- Um cartão da versão anterior do Deidara (seção `deidara/saves/` na raiz) é
  movido sozinho para `saves/deidara/`, com um commit, na primeira vez que o
  Deidara o abre.
- O cartão fica em `~/memory-card` (ou em `--pasta DIR`).
- `--publico` cria (ou aceita) um cartão público. Use só se for de
  propósito: um painel leva nomes de tabela e coluna das fontes.

As variáveis `DEIDARA_MEMORY_CARD_REPO` e `DEIDARA_MEMORY_CARD_DIR` têm
precedência sobre a configuração (`DEIDARA_MEMORY_CARD_DIR=-` desliga).

## Como o cartão é organizado

```
memory-card/                           o cartão do time
├── README.md                          da raiz (o Deidara só cria num cartão novo)
├── CATALOGO.md                        todas as soluções, por solução, categoria e seção (gerado a cada envio)
└── saves/
    ├── vegapunk/...                   os relatórios do Vegapunk (o Deidara não toca)
    └── deidara/
        ├── <categoria>/<secao>/<artigo>/          um painel
        │   ├── README.md              o artigo (o GitHub mostra ao abrir a pasta)
        │   ├── ficha.json             solução, versão, status, aprovação, fontes (só nome e tipo), indicadores, histórico, conferência
        │   ├── argila.json            a especificação aprovada
        │   ├── dicionario_indicadores.md
        │   └── prototipo.html
        └── indicadores/<pasta>/<indicador>/       um indicador
            ├── README.md              definição, fórmula, especificação, painéis que usam, histórico
            └── ficha.json
```

A ficha leva os campos que o catálogo e a busca do Vegapunk leem (`solucao`,
`categoria`, `secao`, `artigo`, `descricao`, `versao`, `status` e
`conferencia.ok`): um `stella.py cartao buscar` também acha os painéis do
Deidara.

- **Categoria** é a área (ex.: `Recursos Humanos`), **seção** é o assunto
  (ex.: `Turnover`) e **artigo** é o painel (padrão: o nome do projeto).
  Indicadores ficam em `indicadores/<pasta do indicador>/`. As pastas usam o
  nome sem acento e com hífen.
- Um save é citado por **REF** = `<categoria>/<secao>/<artigo>`, relativo a
  `saves/deidara/`, com os nomes das pastas (ex.: `recursos-humanos/turnover/quadro-e-turnover`,
  `indicadores/turnover/turnover`).
- **Status**: `rascunho` (padrão) ou `em-uso` (publicado em produção). Um
  indicador também pode ser **`oficial`**: a definição que vale para o time.
- Painel e indicadores ficam ligados como **relacionados**, nos dois sentidos.

### O artigo

O `README.md` de cada save tem: título, categoria, seção, versão e status; a
descrição; o texto do artigo entre `<!-- corpo -->` e `<!-- /corpo -->` (num
painel: O que faz, Quando usar, Como funciona, Indicadores, Regras de negócio,
Limitações; gerado a partir do argila.json se você não passar `--texto`); os
arquivos e a última conferência; os relacionados; o histórico. Só o corpo pode
ser editado à mão, e os marcadores não devem ser apagados.

## Comandos

Os que gravam mostram uma **prévia** primeiro e só gravam com `--confirmar`.

| Comando | O que faz |
|---|---|
| `memory-card iniciar --repo DONO/memory-card [--pasta DIR] [--publico]` | liga ao cartão do time (ou cria) e prepara a seção `deidara/` |
| `memory-card catalogo [--json]` | lista os saves |
| `memory-card buscar TERMO [TERMO ...]` | procura em painéis e indicadores (título e descrição pesam mais; oficiais sobem) |
| `memory-card enviar argila.json --categoria C --secao S [--artigo A] [--texto ARQ.md] [--motivo M] [--relacionado REF] [--status S] [--confirmar]` | salva um painel aprovado e os indicadores dele |
| `memory-card marcar REF --status rascunho\|em-uso\|oficial [--motivo M]` | muda o status (oficial pede motivo) |
| `memory-card conferir [REF ...] --catalogos A.json B.json [--registrar]` | revalida os painéis salvos contra os catálogos atuais |

### Lembretes (como no Vegapunk)

Com um cartão que funciona nesta máquina, os comandos lembram o Claude do
próximo passo, com uma linha `LEMBRETE:` em stderr:

- o `gerar` (o fim do fluxo) lembra de **oferecer salvar** o painel no cartão;
- o `esbocar` (o começo) lembra de procurar no cartão (`memory-card buscar`);
- o `catalogar` de uma fonte que já tinha catálogo lembra de rodar o
  `memory-card conferir`.

Com um cartão configurado que não funciona aqui (outra máquina, sem o `gh`), o
`gerar` lembra de entregar o projeto e dizer que salvar é pelo Claude Code na
máquina do cartão, sem tentar enviar nem configurar. Sem cartão, nada aparece.

### Regras

- **Procure antes.** Antes de um painel ou indicador novo: `memory-card buscar`.
  Se algo serve, ofereça reaproveitar. O `validar` avisa quando uma medida tem
  o nome de um indicador do cartão, mas outra definição.
- **Só aprovado entra.** O `enviar` recusa painel sem aprovação válida.
- **Mudança pede motivo.** Painel ou indicador já salvo que mudou: `--motivo`.
  O histórico guarda quem, quando, por quê e, no indicador, a fórmula anterior.
- **Oficial não se reescreve num painel.** Um painel que muda a definição de um
  indicador oficial é recusado: use a definição oficial, dê outro nome ao
  indicador, ou tire o oficial antes (`marcar ... --status em-uso --motivo`).
- **Ofereça salvar depois.** Depois do `gerar` (o lembrete aparece sozinho),
  ofereça o `enviar`; mostre a prévia e só com o "sim" use `--confirmar`.
- **Confira quando a fonte mudar.** `conferir --registrar` grava o resultado em
  cada save: `ok`, `divergente` (difere de um oficial) ou `quebrado` (coluna,
  tabela ou ligação que sumiu da fonte).
