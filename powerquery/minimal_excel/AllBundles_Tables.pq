let
    Source = fxCombineCsvFromBundles("tables.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {
            {"page_number", Int64.Type},
            {"row_count", Int64.Type},
            {"column_count", Int64.Type},
            {"cell_count", Int64.Type},
            {"text_element_count", Int64.Type},
            {"line_element_count", Int64.Type},
            {"frame_element_count", Int64.Type},
            {"x1", type number},
            {"y1", type number},
            {"x2", type number},
            {"y2", type number},
            {"width", type number},
            {"height", type number},
            {"bbox_area", type number}
        },
        "en-US"
    )
in
    Typed
