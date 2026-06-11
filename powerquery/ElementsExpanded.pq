let
    Source = Elements,
    WithGroups = Table.NestedJoin(Source, {"group_id"}, ElementGroups, {"group_id"}, "GroupInfo", JoinKind.LeftOuter),
    ExpandedGroups = Table.ExpandTableColumn(WithGroups, "GroupInfo", {"group_name", "description"}, {"group_name", "group_description"}),
    WithSubtypes = Table.NestedJoin(ExpandedGroups, {"subtype_id"}, ElementSubtypes, {"subtype_id"}, "SubtypeInfo", JoinKind.LeftOuter),
    ExpandedSubtypes = Table.ExpandTableColumn(WithSubtypes, "SubtypeInfo", {"subtype_name", "description"}, {"subtype_name", "subtype_description"}),
    WithPages = Table.NestedJoin(ExpandedSubtypes, {"page_id"}, Pages, {"page_id"}, "PageInfo", JoinKind.LeftOuter),
    ExpandedPages = Table.ExpandTableColumn(WithPages, "PageInfo", {"page_width", "page_height", "rotation"}, {"page_width", "page_height", "page_rotation"})
in
    ExpandedPages
