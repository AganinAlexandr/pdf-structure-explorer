let
    fxCsv = (fileName as text) as table =>
        let
            FilePath = CurrentBundlePath & "\" & fileName,
            Source = Csv.Document(
                File.Contents(FilePath),
                [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
            ),
            Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true])
        in
            Promoted
in
    fxCsv
