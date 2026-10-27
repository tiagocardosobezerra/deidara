# Deidara

**Do schema ao painel Power BI: protótipo primeiro, projeto completo depois do "sim".**

O Deidara é uma skill do Claude Code para times de indicadores. Ele é o irmão do
[Vegapunk](https://github.com/tiagocardosobezerra/vegapunk): o Vegapunk descobre a
estrutura real do banco (tabelas, colunas, FKs provadas), e o Deidara transforma isso em
painel.

## O que ele faz

1. **Molda** a especificação do painel (`argila.json`): modelo estrela, medidas,
   calendário, páginas e visuais, e confere cada nome contra o Vegapunk. Nada é adivinhado.
2. **Esculpe** um protótipo HTML navegável, com números fictícios, para o gestor validar
   layout, indicadores e navegação antes de qualquer linha de DAX ir para produção.
3. **Detona** (só com o aceite registrado): gera o projeto Power BI completo.

| Entrega | Para quê |
|---|---|
| `Painel.pbip` + `.SemanticModel` (TMDL) + `.Report` (PBIR) | abre no Power BI Desktop, que salva como `.pbix` |
| `sql/01_views.sql` | camada de views (`bi.vw_*`) que o modelo lê |
| `sql/02_conferencia.sql` | total de cada indicador no banco (geral e por ano), para homologar |
| `sql/03_qualidade.sql` | chave repetida, órfãos e datas fora do calendário (tudo tem que dar zero) |
| `docs/dicionario_indicadores.md` | definição, fórmula, origem e prova de cada número |
| `LEIA-ME.md` | o passo a passo para tornar o protótipo real |

## Por que .pbip e não .pbix direto

O `.pbix` é binário e fechado (o modelo vai num formato interno do Analysis Services que só
o Desktop escreve). O `.pbip` é o formato texto oficial da Microsoft para o mesmo conteúdo:
o Desktop abre e salva como `.pbix` em um clique, e o `.pbip` fica versionável no git. Ver
[referencias/powerbi.md](referencias/powerbi.md).

## Comece

```bash
python3 deidara.py coletar --vegapunk ../vegapunk F_DESLIGAMENTO F_FUNCIONARIO -o meu/schema.json
python3 deidara.py validar meu/argila.json
python3 deidara.py prototipar meu/argila.json
python3 deidara.py aprovar meu/argila.json --por "Nome"
python3 deidara.py gerar meu/argila.json -o C:/paineis/meu
```

Exemplo completo, sobre o schema fictício do Vegapunk: [exemplos/aurora](exemplos/aurora).

## O que mais vem junto

- **Indicadores de verdade:** estoque na data (headcount ativo), média mensal, acumulado no ano,
  ano anterior, variação, móvel de 12 meses; metas com status verde/vermelho pela polaridade.
- **Modelo conferido:** avisa quando um segmentador ou corte não filtra (ou só filtra parte de) um
  indicador, quando um trimestre soma todos os anos e quando um corte mostra o cadastro atual.
- **Governança:** versão, histórico de aprovações, `deidara.py diff` e segurança por linha (RLS).

## Instalação como skill

Copie a pasta para `~/.claude/skills/deidara` (ou empacote junto com o Vegapunk) e defina
`VEGAPUNK_DIR` apontando para a pasta do Vegapunk. Python 3.8+, sem dependências. O
`ferramentas/validar_pbip.py` usa o pacote opcional `jsonschema`.

## Conferir a instalação

```bash
python3 -m unittest discover -s testes
python3 ferramentas/validar_pbip.py <pasta gerada>
```

## Regras (as mesmas do Vegapunk)

- Nunca adivinha tabela, coluna ou ligação.
- Só estrutura, nunca dados: o protótipo usa números fictícios.
- Nada é gerado sem protótipo aprovado; mudou depois do aceite, aprova de novo.
