# Power Query Scripts For `pdf-structure-explorer`

## Назначение

Этот набор `.pq`-скриптов предназначен для загрузки экспортов приложения `pdf-structure-explorer` в Excel через Power Query.

Поддерживаются два режима:
- загрузка одного экспортного пакета `doc_xxxxxxxx`;
- объединение одноименных таблиц сразу по всем экспортированным PDF в каталоге `exports`.

## Что лежит в наборе

- `CurrentBundlePath.pq` — параметр пути к одному экспортному пакету
- `ExportRootPath.pq` — параметр пути к корню всех экспортов
- `fxCsv.pq` — функция чтения CSV из одного пакета
- `fxCombineCsvFromBundles.pq` — функция объединения одноименных CSV по всем пакетам
- сущностные запросы:
  - `Documents.pq`
  - `Pages.pq`
  - `Layers.pq`
  - `ElementGroups.pq`
  - `ElementSubtypes.pq`
  - `Elements.pq`
  - `TextSegments.pq`
  - `Images.pq`
  - `Tables.pq`
  - `TableCells.pq`
  - `LanguageSummary.pq`
  - `GroupSummary.pq`
  - `PageSummary.pq`
- производные запросы:
  - `Manifest.pq`
  - `ElementsExpanded.pq`
  - `TablesExpanded.pq`
- объединенные запросы по всем пакетам:
  - `AllBundles_Documents.pq`
  - `AllBundles_Elements.pq`
  - `AllBundles_Tables.pq`
  - `AllBundles_TableCells.pq`
  - `AllBundles_PageSummary.pq`

## Как подключить в Excel

1. Откройте Excel.
2. Перейдите в `Данные -> Получить данные -> Из других источников -> Пустой запрос`.
3. Откройте `Дополнительный редактор`.
4. Вставьте содержимое файла запроса.
5. Сохраните запрос с именем, совпадающим с именем файла без расширения.

Рекомендуемый порядок создания запросов:

1. `CurrentBundlePath`
2. `ExportRootPath`
3. `fxCsv`
4. `fxCombineCsvFromBundles`
5. `Manifest`
6. `Documents`
7. `Pages`
8. `Layers`
9. `ElementGroups`
10. `ElementSubtypes`
11. `Elements`
12. `TextSegments`
13. `Images`
14. `Tables`
15. `TableCells`
16. `LanguageSummary`
17. `GroupSummary`
18. `PageSummary`
19. `ElementsExpanded`
20. `TablesExpanded`
21. `AllBundles_Documents`
22. `AllBundles_Elements`
23. `AllBundles_Tables`
24. `AllBundles_TableCells`
25. `AllBundles_PageSummary`

## Что поменять перед использованием

В `CurrentBundlePath.pq` укажите путь к нужному пакету:

```text
E:\output\pdf-structure-explorer\exports\doc_dceda46d
```

В `ExportRootPath.pq` укажите корневую папку всех экспортов:

```text
E:\output\pdf-structure-explorer\exports
```

## Практический совет

Если вы анализируете один PDF, обычно достаточно загрузить:
- `Documents`
- `Pages`
- `ElementsExpanded`
- `TablesExpanded`
- `LanguageSummary`
- `GroupSummary`

Если вы хотите сравнивать сразу много PDF, удобнее использовать:
- `AllBundles_Documents`
- `AllBundles_Elements`
- `AllBundles_Tables`
- `AllBundles_TableCells`
- `AllBundles_PageSummary`
