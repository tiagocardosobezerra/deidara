let
    Fonte = Excel.Workbook(File.Contents(CaminhoMetas), null, true),
    Metas = Fonte{[Item="Metas", Kind="Table"]}[Data],
    Tipos = Table.TransformColumnTypes(Metas, {{"Cód. Empresa", Int64.Type}, {"Empresa", type text}, {"Meta Turnover", Percentage.Type}})
in
    Tipos
