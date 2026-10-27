# Fontes: receitas, catálogo e ligação declarada

O Deidara não se conecta a nada: sem credencial, sem driver, sem conector
para manter. Ele entrega uma **receita** (a consulta certa), a pessoa roda
onde os dados já estão e cola o resultado num `.txt`; o `catalogar`
transforma isso no **catálogo** da fonte. Toda receita devolve só metadados
(nome, tipo, descrição, chave, ligação, a consulta de origem), nunca linhas.

## Qual receita usar

| Onde está o dado | Receita | Onde rodar | Traz ligação? |
|---|---|---|---|
| Banco SQL Server | `deidara.py receita sql --esquema dbo --tabelas T1,T2` | SSMS, resultado em grade | sim: FKs do banco |
| Já num modelo Power BI (de qualquer origem: Excel, SharePoint, API, outro banco) | `deidara.py receita dax` | Power BI Desktop, *Exibição de consulta DAX* | sim: relações do modelo |
| Consulta Power Query ainda fora de um modelo (Excel, SharePoint, CSV, pasta, API...) | `deidara.py receita m --consultas Metas,Lista` | Power BI ou Excel, *Consulta nula* | não: ligação vira declarada |

Cada receita traz no cabeçalho o passo a passo para quem vai rodar. Grave a
receita num arquivo com `-o` para mandar por e-mail ou chat.

### Copiar o resultado

- **SSMS:** clique na grade, Ctrl+A, botão direito > *Copiar com Cabeçalhos*.
- **Exibição de consulta DAX:** botão *Copiar* da grade de resultado.
- **Power Query:** canto superior esquerdo da visualização > *Copiar tabela inteira*.

Cole num `.txt` (o Bloco de Notas serve). O leitor aceita tabulação, `;` ou
`,`, UTF-8 ou UTF-16, cabeçalhos no formato `[secao]` ou `Tabela[secao]`.

### Receita M: a consulta de origem

A receita M descreve as colunas, mas o painel também precisa saber **de
onde** ler. Para cada consulta, copie o texto do *Editor Avançado* e salve
como `<Nome>.m` numa pasta; parâmetros e consultas auxiliares que ela usa,
um `.m` por nome. Depois: `catalogar ... --m PASTA`. A receita DAX traz
isso sozinha (partições e expressões do modelo).

## Catalogar

```bash
python3 deidara.py catalogar --de erp.txt --fonte erp -o meu_painel/catalogos/erp.json
python3 deidara.py catalogar --de metas.txt --fonte metas --m pasta_dos_m -o meu_painel/catalogos/metas.json
```

O tipo de receita é reconhecido pelo cabeçalho. Os avisos dizem o que ficou
de fora ou precisa de atenção: coluna sem tipo (defina na consulta de origem),
tabela ou coluna **calculada** no modelo de origem (recrie como medida do
Deidara), relação muitos-para-muitos, consulta sem `.m`.

Depois, no argila.json:

```json
"fontes": {
  "erp":   {"catalogo": "catalogos/erp.json", "servidor": "SRV-SQL", "banco": "ERP",
            "esquema_origem": "dbo", "esquema_views": "bi"},
  "metas": {"catalogo": "catalogos/metas.json"}
}
```

e cada tabela diz `"fonte": "erp"` ou `"fonte": "metas"` (com uma fonte só,
pode omitir). `servidor`/`banco`/esquemas só valem para fonte SQL Server.

## Como cada fonte vira painel

| Tipo | Leitura no Power BI | SQL gerado |
|---|---|---|
| sqlserver | views `bi.vw_<tabela>` por dois parâmetros (`<fonte>_Servidor`, `<fonte>_Banco`) | `sql/<fonte>/01_views.sql`, `02_conferencia.sql`, `03_qualidade.sql` |
| powerbi / powerquery | a **própria consulta Power Query** do usuário, mais seleção e nome das colunas, tipos e chave composta; parâmetros e consultas auxiliares vão junto | nenhum |

Credenciais ficam no Power BI (o Desktop pede no primeiro *Atualizar*);
arquivo em pasta de rede pede gateway no serviço, SharePoint/OneDrive não.

## Ligação declarada (entre fontes, ou sem prova)

Não existe FK entre uma planilha e o ERP. Quando o dono do dado confirmar
os campos, declare:

```json
{"de": "fMeta", "para": "dEmpresa",
 "declarada": {"campos": [["Cód. Empresa", "CODEMPRESA"]], "por": "Ana (RH)",
               "motivo": "a planilha usa o mesmo código de empresa do ERP"}}
```

`campos` = pares [coluna da filha, coluna da mãe], com os nomes do catálogo
(conferidos). `por` é obrigatório. Não sabe quais campos? `deidara.py
relacionar` sugere, e a receita de prova mede: ver [descoberta.md](descoberta.md).
Com o bloco `"prova"` (do `provar`), a ligação provada deixa de gerar aviso, e
a reprovada (código repetido na mãe) vira erro. A ligação vira aviso na validação e fica
registrada no dicionário de indicadores e no LEIA-ME ("declarada por …").
Chave repetida no lado "um" derruba a atualização do Power BI; código sem par
some do corte: confira na primeira atualização.

## Dicionário de funções da sua versão

```bash
python3 deidara.py receita funcoes-dax    # EVALUATE INFO.FUNCTIONS(), na Exibição de consulta DAX
python3 deidara.py receita funcoes-m      # #shared, numa consulta nula
python3 deidara.py catalogar --funcoes dax --de funcoes.txt
```

Grava `dicionario/local/<dax|m>.json` (fora do controle de versão). Funções
que existem na sua versão e o Deidara ainda não conhecia passam a valer.
