let
    Source = fxCsv("layers.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {
            {"is_native_pdf_layer", type logical},
            {"is_logical_layer", type logical},
            {"display_order", Int64.Type},
            {"is_visible_by_default", type logical}
        },
        "en-US"
    )
in
    Typed
