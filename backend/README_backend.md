# Backend pdf-structure-explorer (MVP)

FastAPI + PyMuPDF. Реализует «Спецификацию API и экспорта» v1:
все endpoint'ы раздела 15 (минимальный порядок) + status, hit-test,
карточки элементов/таблиц, экспортный пакет из 13 CSV + manifest.json.

## Установка и запуск (Windows)

```bat
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set PSE_STORAGE_DIR=E:/output/pdf-structure-explorer/storage
set PSE_EXPORT_DIR=E:/output/pdf-structure-explorer/exports
uvicorn app.main:app --reload --port 8000
```

Swagger UI: http://127.0.0.1:8000/docs

## Быстрая проверка

```bat
curl http://127.0.0.1:8000/api/v1/health
curl -F "file=@E:\Projects\...\file.pdf" http://127.0.0.1:8000/api/v1/documents
curl -X POST http://127.0.0.1:8000/api/v1/documents/{id}/parse
curl http://127.0.0.1:8000/api/v1/documents/{id}/status
curl http://127.0.0.1:8000/api/v1/documents/{id}/pages
curl "http://127.0.0.1:8000/api/v1/documents/{id}/tables?pageNumber=3"
curl -X POST http://127.0.0.1:8000/api/v1/documents/{id}/export -H "Content-Type: application/json" -d "{\"format\":\"csv_bundle\"}"
```

## Состав

- `app/main.py` — маршруты API, конверт ok/data, коды ошибок раздела 14
- `app/store.py` — реестр документов, фоновый разбор с прогрессом, слои
  (логические + нативные OCG), агрегаты страниц
- `app/model.py` — страница -> модель спецификации: elements,
  text_segments (язык ru/en/unknown/broken_encoding), images
  (дедупликация по xref, тайлы штриховки -> tiled_pattern),
  tables + table_cells
- `app/exporter.py` — 13 CSV + manifest.json (разделы 5–6)
- `pdf_structure/geometry.py` — геометрический движок v2
- `pdf_structure/text_binding.py` — привязка текста и подтверждение таблиц

## Результат интеграционного теста (4_КР_Храм.pdf, 58 стр.)

- разбор: 37 с в фоне, прогресс через /status
- стр.3: 3 таблицы (содержание 21 ячейка high + штамп), hit-test попадает
- стр.29 (кладочный план): 6872 линии, 469 текстов, ведомость 8x4
- языки: ru 4227 / unknown 4581 (числа и размеры) / en 238 сегментов
- экспорт: 14 файлов, elements.csv ~21 МБ

## Известные упрощения MVP

- хранение в памяти процесса (реестр документов не переживает рестарт);
- parse выполняется одним фоновым потоком на документ;
- preview рендерится по запросу, без кэша;
- includePreviews в экспорте пока игнорируется.
