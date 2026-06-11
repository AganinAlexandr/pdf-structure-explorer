let
    Source = fxCsv("pages.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {
            {"page_number", Int64.Type},
            {"page_width", type number},
            {"page_height", type number},
            {"rotation", Int64.Type},
            {"element_count", Int64.Type},
            {"text_count", Int64.Type},
            {"line_count", Int64.Type},
            {"frame_count", Int64.Type},
            {"image_count", Int64.Type},
            {"table_count", Int64.Type},
            {"language_count", Int64.Type}
        },
        "en-US"
    )
in
    Typed
