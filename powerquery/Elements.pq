let
    Source = fxCsv("elements.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {
            {"page_number", Int64.Type},
            {"draw_order", Int64.Type},
            {"depth_level", type number},
            {"x1", type number},
            {"y1", type number},
            {"x2", type number},
            {"y2", type number},
            {"width", type number},
            {"height", type number},
            {"bbox_area", type number},
            {"stroke_width", type number},
            {"line_length", type number},
            {"perimeter", type number},
            {"font_size", type number},
            {"rotation", type number},
            {"char_count", Int64.Type},
            {"text_length", Int64.Type},
            {"binary_size_bytes", Int64.Type},
            {"is_visible", type logical},
            {"is_selected_by_default", type logical}
        },
        "en-US"
    )
in
    Typed
