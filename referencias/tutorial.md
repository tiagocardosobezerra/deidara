# Tutorial: do zero ao projeto Power BI em 15 minutos

Um painel de turnover com o exemplo do repositório (um ERP fictício em SQL
Server e uma planilha de metas no Excel). Rode os comandos da pasta da skill.
No dia a dia, quem roda é o Claude; aqui você vê cada passo por dentro. Todos
os nomes abaixo são os que o exemplo realmente produz.

## 1. A pasta do painel (1 min)

```
python deidara.py novo C:/paineis/turnover --projeto "Turnover RH"
```

Ela vem com `receitas/` (as três consultas, prontas para mandar a quem tem
acesso às fontes), `colado/`, `catalogos/` e um `ROTEIRO.md`.

## 2. A estrutura das fontes (3 min)

Num caso real, o DBA roda `receitas/receita_sql.sql` no SSMS e você cola a
grade em `colado/erp.txt`; a receita M faz o mesmo para a planilha. No
tutorial, use os resultados que já vêm no exemplo:

```
python deidara.py catalogar --de exemplos/aurora/colado/erp_receita_sql.txt --fonte erp -o C:/paineis/turnover/catalogos/erp.json
python deidara.py catalogar --de exemplos/aurora/colado/metas_receita_m.txt --fonte metas --m exemplos/aurora/colado/m -o C:/paineis/turnover/catalogos/metas.json
```

## 3. O primeiro esboço e a ligação sugerida (2 min)

```
python deidara.py esbocar C:/paineis/turnover --pedido "desligamentos por motivo e cargo com a meta de turnover por empresa"
python deidara.py validar C:/paineis/turnover/argila.json
```

O esboço traz 6 tabelas e o calendário (`fDesligamento`, `dMotivoDesligamento`,
`dCargo`, `dFuncionario`, `dEmpresa`, `fMetas`) e duas medidas: `Qtd
Desligamento` e `Meta de turnover`. O `validar` aponta **1 erro**: a ligação da
planilha com a empresa foi *sugerida*. Num caso real, confira os campos com o
dono do dado; aqui, confirme:

```
python deidara.py confirmar C:/paineis/turnover/argila.json --ligacao "fMetas->dEmpresa" --por "Ana (RH)"
```

`--por` é o nome de quem confirmou (fica no dicionário de indicadores). Se o
dono disser que não é essa a ligação, use `--remover`. Para provar com números,
o próprio `confirmar` imprime a `receita prova`; o resultado volta com
`provar --de resultado.txt --argila ...`, que grava a prova na ligação.

## 4. O turnover de verdade (4 min)

```
python deidara.py padroes turnover
```

O padrão mostra a cadeia inteira, na ordem. Com os nomes deste modelo, acrescente
em `"medidas"` do `argila.json`:

```json
{"nome": "Headcount", "tipo": "estoque_na_data", "tabela": "dFuncionario",
 "entradas": "dFuncionario[Data de admissão]", "saidas": "fDesligamento[Data de desligamento]",
 "descricao": "Ativos no último dia do período."},
{"nome": "HC Médio", "tipo": "media_mensal", "base": "Headcount",
 "descricao": "Média do headcount de fim de mês no período."},
{"nome": "Turnover", "tipo": "divisao", "numerador": "Qtd Desligamento", "denominador": "HC Médio",
 "formato": "percentual", "polaridade": "menor_melhor", "meta": "Meta de turnover",
 "descricao": "Desligamentos do período divididos pelo headcount médio."}
```

E um cartão na página: `{"tipo": "cartao", "medida": "Turnover"}`. Valide. O
erro que aparece é de propósito: a data de admissão ainda não está no modelo, e
o `validar` diz exatamente o que acrescentar em `dFuncionario`:

```
{"coluna": "DATAADMISSAO", "nome": "Data de admissão"}
```

Depois, troque os "A DEFINIR" que sobraram: a `descricao` das duas medidas do
esboço e a `descricao` e o `publico` do painel. Errou uma vírgula no JSON? O
`validar` mostra a linha. Sobram só avisos (decisões para levar ao usuário),
como o "valor ATUAL" do cargo e o servidor de exemplo em `"fontes"`.

## 5. O protótipo (2 min)

```
python deidara.py prototipar C:/paineis/turnover/argila.json
```

Abra o `argila.prototipo.html`: clique no ⓘ de um cartão e veja a aba **Para
aprovar**. É isso que o gestor usa para dizer "sim" (ou pedir mudanças). O
botão "Copiar resumo do aceite" gera um texto com o código do protótipo e a
decisão; salve em um arquivo e passe em `aprovar --resumo resumo.txt`.

## 6. Aceite e projeto (2 min)

```
python deidara.py aprovar C:/paineis/turnover/argila.json --por "Gestor de RH"
python deidara.py gerar C:/paineis/turnover/argila.json -o C:/paineis/turnover/pbi
python deidara.py situacao C:/paineis/turnover/argila.json
```

Na pasta `pbi/`: o `.pbip`, o `LEIA-ME.md` (quem faz o quê e o que fazer se
algo der errado), o `HOMOLOGACAO.md` (o que conferir antes de publicar, com
onde ler cada número no painel) e o SQL, incluindo o headcount de cada fim de
mês para comparar com o painel.

## 7. (Opcional) O Memory Card do time (1 min)

```
python deidara.py memory-card iniciar --pasta C:/paineis/cartao-teste
python deidara.py memory-card enviar C:/paineis/turnover/argila.json --categoria "Recursos Humanos" --secao "Turnover"
```

O primeiro `enviar` mostra a prévia; com `--confirmar`, grava. Num caso real,
use `iniciar --repo DONO/memory-card` (o cartão do time no GitHub).
