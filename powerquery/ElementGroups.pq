let
    Source = fxCsv("element_groups.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {
            {"is_enabled_by_default", type logical}
        },
        "en-US"
    )
in
    Typed
