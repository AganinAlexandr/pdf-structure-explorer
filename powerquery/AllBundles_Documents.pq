let
    Source = fxCombineCsvFromBundles("documents.csv"),
    Typed = Table.TransformColumnTypes(
        Source,
        {
            {"file_size_bytes", Int64.Type},
            {"page_count", Int64.Type},
            {"has_native_layers", type logical},
            {"has_text_layer", type logical},
            {"has_images", type logical},
            {"has_tables", type logical}
        },
        "en-US"
    )
in
    Typed
