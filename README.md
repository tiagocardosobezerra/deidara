# Deidara

**Do dado ao painel Power BI: protótipo primeiro, projeto completo depois do "sim".**

O Deidara é uma skill do Claude Code para times de indicadores. Ele não se conecta a nenhuma
fonte: entrega a **receita** (uma consulta SQL, DAX ou Power Query), a pessoa roda onde os dados
já estão (SQL Server, um modelo Power BI que já existe, Excel, SharePoint, CSV, API) e devolve
só a estrutura. A partir daí, nada é adivinhado.

## O que ele faz

1. **Cataloga** cada fonte a partir do resultado colado da receita: tabelas, colunas, tipos,
   chaves, ligações e a consulta Power Query de origem. Nenhuma linha de dado.
2. **Molda** a especificação do painel (`argila.json`): modelo estrela, medidas, metas,
   calendário, páginas e visuais. Confere cada nome contra o catálogo e cada função DAX
   contra o dicionário.
3. **Esculpe** um protótipo HTML navegável, com números fictícios coerentes, para o gestor
   validar layout, indicadores e navegação antes de qualquer linha de DAX ir para produção.
4. **Detona** (só com o aceite registrado): gera o projeto Power BI completo.

| Entrega | Para quê |
|---|---|
| `Painel.pbip` + `.SemanticModel` (TMDL) + `.Report` (PBIR) | abre no Power BI Desktop, que salva como `.pbix` |
| `sql/<fonte>/01_views.sql` | camada de views (`bi.vw_*`) das fontes SQL Server |
| `sql/<fonte>/02_conferencia.sql` | total de cada indicador no banco (geral e por ano), para homologar |
| `sql/<fonte>/03_qualidade.sql` | chave repetida, órfãos e datas fora do calendário (tudo tem que dar zero) |
| `docs/dicionario_indicadores.md` | definição, fórmula, origem, prova de cada ligação e histórico de mudanças |
| `LEIA-ME.md` | o passo a passo para tornar o protótipo real |

As fontes que não são SQL Server (Excel, SharePoint, API...) entram no painel pela **mesma
consulta Power Query** que o time já usa: o Deidara só acrescenta seleção, nomes, tipos e chaves.

## Por que .pbip e não .pbix direto

O `.pbix` é binário e fechado (o modelo vai num formato interno que só o Power BI Desktop
escreve). O `.pbip` é o formato texto oficial da Microsoft para o mesmo conteúdo: o Desktop
abre e salva como `.pbix` em um clique, e o `.pbip` fica versionável no git. Ver
[referencias/powerbi.md](referencias/powerbi.md).

## Comece

```bash
python3 deidara.py receita sql --tabelas F_DESLIGAMENTO,F_FUNCIONARIO -o receita.sql   # ou: dax, m
python3 deidara.py catalogar --de resultado.txt --fonte erp -o meu/catalogos/erp.json
python3 deidara.py buscar "turnover por cargo com meta" --catalogos meu/catalogos/*.json
python3 deidara.py relacionar --catalogos meu/catalogos/*.json --json   # ligações que faltam, com evidência
python3 deidara.py receita prova --argila meu/argila.json --de "fMeta[Cód. Empresa]" --para "dEmpresa[CODEMPRESA]"
python3 deidara.py provar --de prova.txt
python3 deidara.py padroes turnover            # como criar o indicador
python3 deidara.py validar meu/argila.json
python3 deidara.py prototipar meu/argila.json
python3 deidara.py aprovar meu/argila.json --por "Nome"
python3 deidara.py gerar meu/argila.json -o C:/paineis/meu
```

Exemplo completo, com um ERP fictício em SQL Server e uma planilha de metas no Excel, do
resultado colado ao painel: [exemplos/aurora](exemplos/aurora).

## O que mais vem junto

- **Dicionário de funções:** 462 funções DAX e 667 de Power Query, com categoria, assinatura e
  link da documentação oficial; as mais usadas com descrição e uso em indicadores em pt-BR.
  Função inexistente no DAX livre é erro (`deidara.py funcoes buscar "ano anterior"`).
- **Padrões de indicador e onde criar cada coisa:** medida, cálculo visual, grupo de cálculo,
  Power Query ou view SQL (`deidara.py padroes`).
- **Indicadores de verdade:** estoque na data (headcount ativo), média mensal, acumulado no ano,
  ano anterior, variação, móvel de 12 meses; metas com status verde/vermelho pela polaridade.
- **Modelo conferido:** avisa quando um segmentador ou corte não filtra (ou só filtra parte de) um
  indicador, quando um trimestre soma todos os anos e quando um corte mostra o cadastro atual.
- **Informações soltas:** `buscar` acha as tabelas de um pedido em todas as fontes; `relacionar` sugere
  as ligações que faltam, com a evidência de cada uma (nome, chave, tipo, sinônimos); a receita de prova
  mede a candidata na fonte (só percentuais e sim/não). A ligação entre fontes vira "declarada", com quem
  confirmou e a prova, registrada na entrega.
- **Governança:** versão, histórico de aprovações, `deidara.py diff` e segurança por linha (RLS).

## Instalação como skill

Copie a pasta para `~/.claude/skills/deidara`. Python 3.8+, sem dependências. O
`ferramentas/validar_pbip.py` usa o pacote opcional `jsonschema`.

## Conferir a instalação

```bash
python3 -m unittest discover -s testes
python3 ferramentas/validar_pbip.py <pasta gerada>
```

## Regras

- Nunca adivinha tabela, coluna, ligação ou função.
- Só estrutura, nunca dados: as receitas devolvem metadados (a de prova, só percentuais) e o protótipo usa
  números fictícios.
- Sugere ligações, nunca as cria sozinho: quem confirma é uma pessoa.
- Nada é gerado sem protótipo aprovado; mudou depois do aceite, aprova de novo.

## Sobre o dicionário de funções

Nomes, categorias, assinaturas e links vêm da referência oficial da Microsoft (Microsoft Learn);
as descrições e os usos em pt-BR foram escritos para o Deidara. A documentação completa é a da
Microsoft, no link de cada função.

## Licença

MIT. Ver [LICENSE](LICENSE).
