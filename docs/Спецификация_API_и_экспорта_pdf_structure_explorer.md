# Спецификация API и экспорта

## 1. Назначение

Документ описывает:
- backend API для локального приложения `pdf-structure-explorer`;
- структуру экспортного пакета для Power Query и Excel;
- нормализованную модель данных для страниц, элементов, слоев, языков и таблиц.

Документ является прикладным дополнением к основному ТЗ.

## 2. Архитектурные допущения

- приложение локальное, однопользовательское;
- backend работает локально на `http://127.0.0.1:<port>`;
- frontend работает локально и обращается к backend по HTTP;
- экспорт выполняется backend и сохраняется в `E:/output/pdf-structure-explorer/exports`;
- все идентификаторы стабильны в рамках одного документа и его экспортного пакета.

## 3. Базовая модель данных

Иерархия:

```text
Document
  -> Page
    -> Layer
      -> ElementGroup
        -> ElementSubtype
          -> Element
```

Дополнительные сущности:
- `TextSegment`
- `ImageAsset`
- `TableAsset`
- `TableCell`
- `LanguageSummary`
- `GroupSummary`
- `PageSummary`

## 4. Соглашения по идентификаторам

- `document_id`: `doc_<uuid-or-shortid>`
- `page_id`: `doc_<id>_p_<page_number>`
- `layer_id`: `layer_<name-or-seq>`
- `group_id`: одно из фиксированных значений `text`, `lines`, `frames`, `images`, `tables`, `other_vector`
- `subtype_id`: фиксированное значение уровня подтипа
- `element_id`: `el_<page>_<seq>`
- `table_id`: `tbl_<page>_<seq>`
- `cell_id`: `cell_<table_seq>_<row>_<col>`
- `image_id`: `img_<page>_<seq>`
- `text_segment_id`: `txt_<page>_<seq>`

## 5. Экспортный пакет

### 5.1. Формат пакета

Экспорт одного документа должен создаваться в отдельной папке:

```text
E:/output/pdf-structure-explorer/exports/<document_id>/
```

Состав пакета MVP:
- `manifest.json`
- `documents.csv`
- `pages.csv`
- `layers.csv`
- `element_groups.csv`
- `element_subtypes.csv`
- `elements.csv`
- `text_segments.csv`
- `images.csv`
- `tables.csv`
- `table_cells.csv`
- `language_summary.csv`
- `group_summary.csv`
- `page_summary.csv`

### 5.2. Общие правила для CSV

- разделитель: запятая;
- кодировка: `UTF-8`;
- первая строка: заголовки колонок;
- пустые значения: пустая строка;
- логические поля: `true` / `false`;
- даты и время: ISO 8601;
- десятичный разделитель: точка.

### 5.3. `manifest.json`

Назначение:
- описывает документ;
- перечисляет файлы пакета;
- фиксирует версию схемы;
- содержит контрольные метаданные экспорта.

Пример:

```json
{
  "schemaVersion": "1.0.0",
  "documentId": "doc_001",
  "exportedAt": "2026-06-10T21:15:00Z",
  "appMode": "local",
  "files": [
    "documents.csv",
    "pages.csv",
    "layers.csv",
    "element_groups.csv",
    "element_subtypes.csv",
    "elements.csv",
    "text_segments.csv",
    "images.csv",
    "tables.csv",
    "table_cells.csv",
    "language_summary.csv",
    "group_summary.csv",
    "page_summary.csv"
  ]
}
```

## 6. Схема CSV-таблиц

### 6.1. `documents.csv`

Одна строка на документ.

Колонки:
- `document_id`
- `file_name`
- `file_crc32`
- `file_path`
- `file_size_bytes`
- `page_count`
- `pdf_version`
- `has_native_layers`
- `has_text_layer`
- `has_images`
- `has_tables`
- `parse_status`
- `parsed_at`

### 6.2. `pages.csv`

Одна строка на страницу.

Колонки:
- `page_id`
- `document_id`
- `page_number`
- `page_width`
- `page_height`
- `rotation`
- `element_count`
- `text_count`
- `line_count`
- `frame_count`
- `image_count`
- `table_count`
- `language_count`

### 6.3. `layers.csv`

Одна строка на слой в рамках документа или страницы.

Колонки:
- `layer_id`
- `document_id`
- `page_id`
- `layer_name`
- `layer_kind`
- `is_native_pdf_layer`
- `is_logical_layer`
- `display_order`
- `is_visible_by_default`

`layer_kind`:
- `text`
- `vector_graphics`
- `images`
- `ui_overlay`
- `native_pdf_layer`

### 6.4. `element_groups.csv`

Справочник верхних групп.

Колонки:
- `group_id`
- `group_name`
- `description`
- `is_enabled_by_default`

Фиксированные значения MVP:
- `text`
- `lines`
- `frames`
- `images`
- `tables`
- `other_vector`

### 6.5. `element_subtypes.csv`

Справочник подтипов.

Колонки:
- `subtype_id`
- `group_id`
- `subtype_name`
- `description`

Примеры:
- `text_block`
- `text_line`
- `text_span`
- `glyph`
- `line_segment`
- `rectangle_frame`
- `path_frame`
- `raster_image`
- `inline_image`
- `grid_table`
- `borderless_table`

### 6.6. `elements.csv`

Центральная таблица всех элементов документа.

Одна строка на элемент верхнего уровня или базовый элемент.

Колонки:
- `element_id`
- `document_id`
- `page_id`
- `page_number`
- `layer_id`
- `group_id`
- `subtype_id`
- `parent_element_id`
- `related_table_id`
- `related_image_id`
- `related_text_segment_id`
- `draw_order`
- `depth_level`
- `x1`
- `y1`
- `x2`
- `y2`
- `width`
- `height`
- `bbox_area`
- `stroke_width`
- `line_length`
- `perimeter`
- `font_name`
- `font_size`
- `font_color`
- `fill_color`
- `rotation`
- `language_code`
- `encoding_status`
- `char_count`
- `text_length`
- `binary_size_bytes`
- `is_visible`
- `is_selected_by_default`

Примечания:
- для неприменимых полей допускается пустое значение;
- `parent_element_id` используется для вложенных структур;
- `related_table_id` заполняется для элементов, принадлежащих таблице.

### 6.7. `text_segments.csv`

Одна строка на текстовый сегмент.

Колонки:
- `text_segment_id`
- `element_id`
- `document_id`
- `page_id`
- `page_number`
- `layer_id`
- `language_code`
- `language_confidence`
- `encoding_status`
- `text_value`
- `normalized_text`
- `char_count`
- `word_count`
- `x1`
- `y1`
- `x2`
- `y2`
- `width`
- `height`

`encoding_status`:
- `ok`
- `broken_encoding`
- `unknown`

### 6.8. `images.csv`

Одна строка на изображение.

Колонки:
- `image_id`
- `element_id`
- `document_id`
- `page_id`
- `page_number`
- `layer_id`
- `image_format`
- `color_space`
- `width_px`
- `height_px`
- `bbox_width`
- `bbox_height`
- `bbox_area`
- `binary_size_bytes`
- `preview_path`

### 6.9. `tables.csv`

Одна строка на таблицу.

Колонки:
- `table_id`
- `element_id`
- `document_id`
- `page_id`
- `page_number`
- `layer_id`
- `table_kind`
- `detection_confidence`
- `row_count`
- `column_count`
- `cell_count`
- `text_element_count`
- `line_element_count`
- `frame_element_count`
- `x1`
- `y1`
- `x2`
- `y2`
- `width`
- `height`
- `bbox_area`

`table_kind`:
- `grid_table`
- `borderless_table`
- `mixed_table`

`detection_confidence`:
- `high`
- `medium`
- `partial`

### 6.10. `table_cells.csv`

Одна строка на ячейку таблицы.

Колонки:
- `cell_id`
- `table_id`
- `document_id`
- `page_id`
- `page_number`
- `row_index`
- `column_index`
- `row_span`
- `column_span`
- `text_value`
- `language_code`
- `encoding_status`
- `child_element_count`
- `x1`
- `y1`
- `x2`
- `y2`
- `width`
- `height`
- `bbox_area`

### 6.11. `language_summary.csv`

Агрегаты по языкам.

Колонки:
- `document_id`
- `page_id`
- `page_number`
- `language_code`
- `segment_count`
- `char_count`
- `broken_encoding_count`

### 6.12. `group_summary.csv`

Агрегаты по группам элементов.

Колонки:
- `document_id`
- `page_id`
- `page_number`
- `group_id`
- `element_count`
- `bbox_area_total`
- `line_length_total`
- `table_count`
- `cell_count`
- `broken_encoding_count`

### 6.13. `page_summary.csv`

Агрегаты по страницам.

Колонки:
- `document_id`
- `page_id`
- `page_number`
- `element_count`
- `text_count`
- `line_count`
- `frame_count`
- `image_count`
- `table_count`
- `table_cell_count`
- `language_count`
- `broken_encoding_count`

## 7. API backend

### 7.1. Общие правила

- базовый префикс: `/api/v1`;
- формат обмена: `application/json`;
- загрузка файла: `multipart/form-data`;
- ошибки возвращаются в унифицированном формате;
- все API рассчитаны на локальный frontend.

### 7.2. Общий формат ответа

Успешный ответ:

```json
{
  "ok": true,
  "data": {}
}
```

Ответ с ошибкой:

```json
{
  "ok": false,
  "error": {
    "code": "DOCUMENT_NOT_FOUND",
    "message": "Document not found"
  }
}
```

## 8. Справочные endpoint'ы

### 8.1. `GET /api/v1/health`

Назначение:
- проверить доступность backend.

Ответ:

```json
{
  "ok": true,
  "data": {
    "status": "ok"
  }
}
```

### 8.2. `GET /api/v1/config`

Назначение:
- вернуть параметры локального приложения и справочники UI.

Ответ должен включать:
- список верхних групп;
- список режимов курсора;
- список языковых кодов по умолчанию;
- поддерживаемые форматы экспорта.

## 9. Работа с документами

### 9.1. `POST /api/v1/documents`

Назначение:
- загрузить PDF и создать запись документа.

Запрос:
- `file`: PDF-файл.

Ответ:

```json
{
  "ok": true,
  "data": {
    "documentId": "doc_001",
    "fileName": "sample.pdf",
    "fileCrc32": "8A52FDF1",
    "status": "uploaded"
  }
}
```

### 9.2. `POST /api/v1/documents/{documentId}/parse`

Назначение:
- запустить разбор документа.

Тело запроса:

```json
{
  "parseTables": true,
  "parseImages": true,
  "parseTextGlyphs": false
}
```

Ответ:

```json
{
  "ok": true,
  "data": {
    "documentId": "doc_001",
    "status": "processing"
  }
}
```

### 9.3. `GET /api/v1/documents`

Назначение:
- список загруженных документов.

### 9.4. `GET /api/v1/documents/{documentId}`

Назначение:
- получить карточку документа.

Поля ответа:
- метаданные PDF;
- статус разбора;
- число страниц;
- наличие нативных слоев;
- наличие изображений;
- наличие таблиц.

### 9.5. `GET /api/v1/documents/{documentId}/status`

Назначение:
- получить прогресс обработки.

Ответ:

```json
{
  "ok": true,
  "data": {
    "documentId": "doc_001",
    "status": "processing",
    "processedPages": 12,
    "totalPages": 84,
    "progressPercent": 14.3
  }
}
```

## 10. Страницы и визуализация

### 10.1. `GET /api/v1/documents/{documentId}/pages`

Назначение:
- вернуть список страниц с агрегатами.

Параметры:
- `includeSummary=true|false`

### 10.2. `GET /api/v1/documents/{documentId}/pages/{pageNumber}`

Назначение:
- вернуть метаданные одной страницы.

### 10.3. `GET /api/v1/documents/{documentId}/pages/{pageNumber}/preview`

Назначение:
- вернуть превью страницы.

Формат:
- `image/png` или ссылка на локальный preview-файл.

Параметры:
- `scale`

## 11. Элементы и фильтрация

### 11.1. `GET /api/v1/documents/{documentId}/elements`

Назначение:
- вернуть список элементов по документу или фильтрам.

Параметры:
- `pageNumber`
- `layerId`
- `groupId`
- `subtypeId`
- `languageCode`
- `encodingStatus`
- `tableId`
- `cursorMode`
- `limit`
- `offset`

Ответ:
- список элементов;
- общее количество;
- агрегаты по текущему фильтру.

### 11.2. `GET /api/v1/documents/{documentId}/elements/{elementId}`

Назначение:
- вернуть полную карточку элемента.

Для таблицы ответ должен включать:
- количественные признаки;
- связи с дочерними элементами;
- список ячеек или ссылку на ячейки.

### 11.3. `GET /api/v1/documents/{documentId}/groups`

Назначение:
- вернуть верхние группы элементов и их агрегаты.

Параметры:
- `pageNumber`
- `layerId`

Пример ответа:

```json
{
  "ok": true,
  "data": {
    "items": [
      { "groupId": "text", "elementCount": 428 },
      { "groupId": "frames", "elementCount": 27 },
      { "groupId": "tables", "elementCount": 3 }
    ]
  }
}
```

### 11.4. `GET /api/v1/documents/{documentId}/layers`

Назначение:
- список слоев и их состояние.

### 11.5. `GET /api/v1/documents/{documentId}/languages`

Назначение:
- список языков и количественные показатели.

### 11.6. `GET /api/v1/documents/{documentId}/tables`

Назначение:
- вернуть список таблиц документа или страницы.

Параметры:
- `pageNumber`
- `detectionConfidence`

### 11.7. `GET /api/v1/documents/{documentId}/tables/{tableId}`

Назначение:
- карточка таблицы.

Ответ должен включать:
- базовые поля таблицы;
- список ячеек;
- связи с элементами текста и линий;
- признак уверенности распознавания.

## 12. Инспекция по координатам

### 12.1. `GET /api/v1/documents/{documentId}/pages/{pageNumber}/hit-test`

Назначение:
- вернуть элемент под курсором или ближайшие элементы.

Параметры:
- `x`
- `y`
- `groupId`
- `layerId`
- `cursorMode`

`cursorMode`:
- `pointer`
- `crosshair`
- `precision`
- `focus`

Ответ:

```json
{
  "ok": true,
  "data": {
    "primaryElementId": "el_5_210",
    "candidates": [
      {
        "elementId": "el_5_210",
        "groupId": "tables",
        "distance": 0.0
      }
    ]
  }
}
```

## 13. Экспорт

### 13.1. `POST /api/v1/documents/{documentId}/export`

Назначение:
- сформировать экспортный пакет.

Тело запроса:

```json
{
  "format": "csv_bundle",
  "includePreviews": false,
  "includeTableCells": true
}
```

Ответ:

```json
{
  "ok": true,
  "data": {
    "documentId": "doc_001",
    "exportId": "exp_001",
    "status": "ready",
    "exportPath": "E:/output/pdf-structure-explorer/exports/doc_001"
  }
}
```

### 13.2. `GET /api/v1/documents/{documentId}/export`

Назначение:
- вернуть состояние последнего экспорта и пути к файлам.

## 14. Ошибки API

Минимальные коды ошибок:
- `INVALID_FILE_TYPE`
- `UPLOAD_FAILED`
- `DOCUMENT_NOT_FOUND`
- `PAGE_NOT_FOUND`
- `ELEMENT_NOT_FOUND`
- `TABLE_NOT_FOUND`
- `EXPORT_FAILED`
- `PARSE_FAILED`
- `VALIDATION_ERROR`

## 15. Минимальный порядок реализации backend

1. `POST /documents`
2. `POST /documents/{id}/parse`
3. `GET /documents/{id}`
4. `GET /documents/{id}/pages`
5. `GET /documents/{id}/pages/{page}/preview`
6. `GET /documents/{id}/elements`
7. `GET /documents/{id}/groups`
8. `GET /documents/{id}/layers`
9. `GET /documents/{id}/languages`
10. `GET /documents/{id}/tables`
11. `POST /documents/{id}/export`

## 16. Рекомендация для backend-структуры

```text
backend/
  app/
    api/
    services/
    parsers/
    exporters/
    models/
    schemas/
    storage/
```

Роли модулей:
- `parsers/` — разбор PDF и построение сущностей;
- `services/` — orchestration обработки;
- `exporters/` — формирование CSV и manifest;
- `schemas/` — Pydantic-схемы API;
- `storage/` — локальный кэш, preview, экспорт.
