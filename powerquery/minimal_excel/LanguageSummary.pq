let
    Source = fxCsv("language_summary.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {
            {"page_number", Int64.Type},
            {"segment_count", Int64.Type},
            {"char_count", Int64.Type},
            {"broken_encoding_count", Int64.Type}
        },
        "en-US"
    )
in
    Typed
