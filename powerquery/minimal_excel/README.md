# Power Query Minimal Pack For Excel

## Purpose

This folder contains a compact set of `.pq` queries for loading `pdf-structure-explorer` exports into Excel through Power Query.

The pack supports two scenarios:

- one exported PDF bundle such as `doc_dceda46d`
- combined analysis across all exported bundles in the `exports` folder

## Files In This Pack

### Parameters and functions

Load these as `Connection only`:

- `CurrentBundlePath.pq`
- `ExportRootPath.pq`
- `fxCsv.pq`
- `fxCombineCsvFromBundles.pq`

### Base queries used by dependent reports

Load these as `Connection only`:

- `Documents.pq`
- `Pages.pq`
- `Elements.pq`
- `ElementGroups.pq`
- `ElementSubtypes.pq`
- `Tables.pq`
- `TableCells.pq`

### Recommended worksheet tables

Load these to worksheet tables:

- `PageSummary.pq`
- `ElementsExpanded.pq`
- `TablesExpanded.pq`
- `LanguageSummary.pq`

### Cross-bundle comparison queries

Load these to worksheet tables when you want to compare many PDFs:

- `AllBundles_PageSummary.pq`
- `AllBundles_Tables.pq`

## Recommended Import Order

Create the queries in this order:

1. `CurrentBundlePath`
2. `ExportRootPath`
3. `fxCsv`
4. `fxCombineCsvFromBundles`
5. `Documents`
6. `Pages`
7. `Elements`
8. `ElementGroups`
9. `ElementSubtypes`
10. `Tables`
11. `TableCells`
12. `PageSummary`
13. `ElementsExpanded`
14. `TablesExpanded`
15. `LanguageSummary`
16. `AllBundles_PageSummary`
17. `AllBundles_Tables`

## Paths To Update Before Use

Set the exported bundle path in `CurrentBundlePath.pq`, for example:

```text
E:\output\pdf-structure-explorer\exports\doc_dceda46d
```

Set the common exports root in `ExportRootPath.pq`:

```text
E:\output\pdf-structure-explorer\exports
```

## Practical Use

For everyday analysis of one PDF, the most useful worksheet tables are:

- `PageSummary`
- `ElementsExpanded`
- `TablesExpanded`
- `LanguageSummary`

For comparing many PDF exports, start with:

- `AllBundles_PageSummary`
- `AllBundles_Tables`

## Notes

- `ElementsExpanded` joins element rows with page, group, and subtype metadata.
- `TablesExpanded` joins tables with page info and nested cell data.
- If you do not need raw technical tables in Excel sheets, keep the base queries as `Connection only`.
