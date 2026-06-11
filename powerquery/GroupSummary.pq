let
    Source = fxCsv("group_summary.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {
            {"page_number", Int64.Type},
            {"element_count", Int64.Type},
            {"bbox_area_total", type number},
            {"line_length_total", type number},
            {"table_count", Int64.Type},
            {"cell_count", Int64.Type},
            {"broken_encoding_count", Int64.Type}
        },
        "en-US"
    )
in
    Typed
