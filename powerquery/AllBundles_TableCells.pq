let
    Source = fxCombineCsvFromBundles("table_cells.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {
            {"page_number", Int64.Type},
            {"row_index", Int64.Type},
            {"column_index", Int64.Type},
            {"row_span", Int64.Type},
            {"column_span", Int64.Type},
            {"child_element_count", Int64.Type},
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
