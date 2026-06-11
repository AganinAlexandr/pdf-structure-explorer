let
    fxCombineCsvFromBundles = (fileName as text) as table =>
        let
            Source = Folder.Files(ExportRootPath),
            Filtered = Table.SelectRows(Source, each [Name] = fileName),
            WithData = Table.AddColumn(
                Filtered,
                "Data",
                each Table.PromoteHeaders(
                    Csv.Document(
                        [Content],
                        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
                    ),
                    [PromoteAllScalars = true]
                ),
                type table
            ),
            Expanded =
                if Table.RowCount(WithData) = 0 then
                    #table({}, {})
                else
                    Table.ExpandTableColumn(
                        WithData,
                        "Data",
                        Table.ColumnNames(WithData{0}[Data]),
                        Table.ColumnNames(WithData{0}[Data])
                    ),
            Renamed = Table.RenameColumns(
                Expanded,
                {
                    {"Folder Path", "bundle_path"},
                    {"Name", "source_file"}
                },
                MissingField.Ignore
            ),
            Cleaned = Table.RemoveColumns(
                Renamed,
                {"Content", "Extension", "Date accessed", "Date modified", "Date created", "Attributes"},
                MissingField.Ignore
            )
        in
            Cleaned
in
    fxCombineCsvFromBundles
