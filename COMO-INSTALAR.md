# Como instalar o Deidara

A skill é a pasta inteira. Python 3.8+ com a biblioteca padrão, sem nada para
instalar. Para abrir o projeto gerado, o Power BI Desktop (versão com suporte a
projetos `.pbip`, TMDL e PBIR; ver [referencias/powerbi.md](referencias/powerbi.md)).

## No Claude Code

Para todos os projetos, clone na pasta de skills do usuário:

```bash
git clone https://github.com/tiagocardosobezerra/deidara.git ~/.claude/skills/deidara
```

```powershell
git clone https://github.com/tiagocardosobezerra/deidara.git "$env:USERPROFILE\.claude\skills\deidara"
```

Só para um projeto, clone em `.claude/skills/deidara` dentro dele. Sem git,
baixe o zip do repositório no GitHub e extraia a pasta com o nome `deidara`.

## No claude.ai

O claude.ai recebe a skill como um arquivo `.zip` (sem zip dentro de zip).
Gere o pacote a partir da pasta da skill:

```bash
python3 ferramentas/empacotar.py
```

Ele cria `deidara-skill.zip` ao lado da pasta, só com o que a skill usa: num
clone git, só arquivo rastreado (pasta de cliente ou rascunho solto nunca vai
junto), sem imagens do README, saídas geradas nem aprovações locais. Suba o arquivo
na área de Skills das configurações do claude.ai.

No claude.ai, a skill funciona até o protótipo e a geração do projeto. O
Memory Card precisa do `gh` autenticado, que só existe no Claude Code.

## Conferir a instalação

```bash
python3 deidara.py status
pip install -r ferramentas/requisitos-dev.txt    # só para os testes: o jsonschema
python3 -m unittest discover -s testes
```

O `status` mostra a versão e a pasta da skill; os testes rodam sobre o exemplo
fictício e não tocam em nada fora de uma pasta temporária.

Para conferir um projeto gerado contra os JSON Schemas oficiais da Microsoft
(opcional; precisa do pacote `jsonschema`; os schemas já vêm em `ferramentas/schemas/`):

```bash
pip install -r ferramentas/requisitos-dev.txt
python3 ferramentas/validar_pbip.py <pasta do projeto gerado>
```

## O que fica no seu computador (e não na skill)

| O quê | Onde | Vai para o git? |
|---|---|---|
| A pasta de cada painel: receitas, resultados colados, catálogos, `argila.json`, protótipo e aprovação | onde você criar com `deidara.py novo` | só se você quiser, e nunca num repositório público (ver [AVISO.md](AVISO.md)) |
| Projetos gerados | a pasta do `gerar -o`, ou `<painel>/saida/` | não (está no `.gitignore`) |
| Configuração do Memory Card | `~/.deidara/memory_card.json` | não |
| Cópia local do cartão do time | a pasta escolhida no `memory-card iniciar` | é o próprio repositório do cartão |
| Dicionário de funções da sua versão do Power BI (opcional) | `dicionario/local/` | não (está no `.gitignore`) |
| Cache dos schemas da Microsoft | `~/.cache/deidara/schemas` | não |

Como nada disso fica nos arquivos da skill, atualizar ou reinstalar não apaga
painéis, cartão nem configuração.

## Atualizar

```bash
git -C ~/.claude/skills/deidara pull
```

No claude.ai, gere o zip de novo e substitua a skill. Depois de atualizar,
rode `python3 deidara.py status` para ver a versão.

## Memory Card (opcional)

Precisa do [GitHub CLI](https://cli.github.com/) autenticado (`gh auth login`)
com acesso ao repositório do time:

```bash
python3 deidara.py memory-card iniciar --repo DONO/memory-card
```

Se o repositório não existe, ele é criado **privado**. Para desligar o cartão
nesta máquina: `python3 deidara.py memory-card desligar`. Guia completo em
[referencias/memory-card.md](referencias/memory-card.md).

## Desinstalar

Apague a pasta da skill. Se quiser apagar também a configuração do Memory
Card, apague `~/.deidara/`. Os painéis e o cartão do time continuam onde estão.
