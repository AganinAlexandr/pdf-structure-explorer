let
    Source = fxCsv("text_segments.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {
            {"page_number", Int64.Type},
            {"language_confidence", type number},
            {"char_count", Int64.Type},
            {"word_count", Int64.Type},
            {"x1", type number},
            {"y1", type number},
            {"x2", type number},
            {"y2", type number},
            {"width", type number},
            {"height", type number}
        },
        "en-US"
    )
in
    Typed
