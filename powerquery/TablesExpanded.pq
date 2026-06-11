let
    Source = Tables,
    WithCells = Table.NestedJoin(Source, {"table_id"}, TableCells, {"table_id"}, "Cells", JoinKind.LeftOuter),
    WithPages = Table.NestedJoin(WithCells, {"page_id"}, Pages, {"page_id"}, "PageInfo", JoinKind.LeftOuter),
    ExpandedPages = Table.ExpandTableColumn(WithPages, "PageInfo", {"page_width", "page_height", "rotation"}, {"page_width", "page_height", "page_rotation"})
in
    ExpandedPages
