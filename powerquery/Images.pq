let
    Source = fxCsv("images.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {
            {"page_number", Int64.Type},
            {"width_px", Int64.Type},
            {"height_px", Int64.Type},
            {"bbox_width", type number},
            {"bbox_height", type number},
            {"bbox_area", type number},
            {"binary_size_bytes", Int64.Type}
        },
        "en-US"
    )
in
    Typed
