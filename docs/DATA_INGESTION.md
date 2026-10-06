# MK-Path — Universal Data Ingestion Engine & Deterministic Profiling (Phases 4–5)

Status: **implemented and tested** (42/42 automated tests + live smoke test, 2026-10-06).
Path mapping: spec `E:\MK-PATH` = workspace `E:\MKPATH` (recorded Phase 1 decision).

---

## 1. What the platform accepts

| Input | Handling |
| --- | --- |
| `.csv` | delimiter sniffing (`,` `;` `\t` `|`), UTF-8/UTF-8-BOM (cp1252/latin-1 fallback with warnings), header detection, malformed-row errors with line numbers |
| `.xlsx` | openpyxl read-only metadata (workbook, sheet names, dimensions); only the selected sheet is loaded; `sheet_name` form field selects a sheet |
| `.xls` | supported via `xlrd` (small pure-Python dependency); same sheet-selection semantics |
| `.json` | array of objects, scalar arrays (→ `value` column), single object (→ 1 row), NDJSON; nested objects flattened with dot notation (warning); clear errors for unsupported shapes |
| `.parquet` | PyArrow metadata read (lazy/columnar); original file used as normalized form — no conversion |
| `.sql` | untrusted; allow-list execution layer (see §3); loaded into a throwaway in-memory DuckDB, exported to Parquet |
| `.zip` | secure extraction with budget checks; recursive discovery to a configured depth; per-file processing; manifest; unsupported files reported, never ignored |

## 2. Upload pipeline

```
POST /api/datasets/upload  (multipart, streamed to disk in 1 MB chunks)
  → size limit (MAX_UPLOAD_MB, default 50) → content/extension signature checks
  → secure storage: datasets/<upload_id>/<sanitized_name>
  → ZIP: extraction to temp/<upload_id>/depth_<n>_<rand>/ (validated entry-by-entry)
  → supported-file discovery (recursive, MAX_ZIP_DEPTH=1)
  → deterministic parser → normalized Parquet (data/<upload_id>/<dataset_id>.parquet)
  → DuckDB registration (view ds_<dataset_id> over Parquet — lazy)
  → metadata document in MongoDB `datasets` collection
  → audit_events entries (dataset_upload, dataset_ingested)
```

Normalized result contract (every ingested source): `dataset_id, source_file_id,
original_filename, source_format, storage_path, normalized_path, table_name, schema,
row_count, column_count, ingestion_status, warnings, errors, created_at` (+ `upload_id`,
`archive_member`, `parent_archive`, `view_name`, `profile`).

## 3. Security model (untrusted input)

- **ZIP Slip / traversal**: every entry validated (`..`, absolute paths, drive letters,
  NUL, backslash normalization) *before* extraction; targets re-checked with
  `realpath` containment inside the unique extraction dir.
- **Symlinks/special files**: rejected via external-attr mode bits.
- **Encrypted entries**: rejected (stdlib zipfile cannot open them safely).
- **Decompression bombs**: entry-count limit (200), estimated extracted size limit
  (200 MB), compression-ratio limit (100:1 above 10 MB), plus a *running byte
  budget* during extraction so lying headers cannot bypass estimates.
- **Duplicate filenames**: case-insensitive detection inside archives → renamed
  `name(1).ext` with a `DUPLICATE_NAME` report.
- **Corrupt entries**: extraction errors are reported (`CORRUPT_ENTRY`), never crash
  the pipeline; corrupt *nested* archives are reported unsupported.
- **Malformed files**: CSV (ParserError with line numbers), JSON (line/column),
  Parquet (magic + PyArrow errors), Excel (clear engine errors) → structured 4xx.
- **SQL safety**: only `CREATE TABLE` and `INSERT INTO ... VALUES` are executed,
  inside a throwaway in-memory DuckDB. Everything else (`DROP/DELETE/UPDATE/ALTER/
  TRUNCATE/ATTACH/LOAD/COPY/SET/EXEC/...`, `CREATE TABLE AS SELECT`,
  `INSERT ... SELECT`, and filesystem-capable functions like `read_csv()`) is
  rejected with an explanation before execution. Export uses a server-generated
  path, never one from the file.
- **Filenames**: uploaded names are never used as paths; `sanitize_filename()`
  reduces them to safe basenames.
- **No arbitrary code execution**: parsing is pandas/PyArrow/DuckDB/openpyxl only;
  nothing from uploads is `eval`ed, imported, or executed.

Error codes (structured, no internals leaked): `UNSUPPORTED_EXTENSION` (415),
`BINARY_NOT_TEXT` (415), `INVALID_ZIP`/`EMPTY_FILE` (400), `UPLOAD_TOO_LARGE` (413),
`TOO_MANY_ENTRIES`/`ESTIMATED_SIZE_EXCEEDED`/`COMPRESSION_RATIO_EXCEEDED`/
`EXTRACTED_SIZE_EXCEEDED` (413), `EMPTY_ZIP`/`MALFORMED_*`/`SHEET_NOT_FOUND`/
`SQL_NO_SUPPORTED_STATEMENTS`/`PATH_TRAVERSAL`/`NO_SUPPORTED_FILES` (422).

## 4. API

| Endpoint | Purpose |
| --- | --- |
| `POST /api/datasets/upload` | multipart upload (+ optional `sheet_name`), returns datasets + manifest + unsupported + rejected + parse failures |
| `GET /api/datasets` | list (`limit`, `offset`) |
| `GET /api/datasets/{id}` | full metadata document |
| `GET /api/datasets/{id}/schema` | column names/types/nullability |
| `GET /api/datasets/{id}/preview` | first rows (≤ `MAX_PREVIEW_ROWS`, default 100), JSON-safe |
| `GET /api/datasets/{id}/quality` | stored quality summary; 404 `NOT_PROFILED` before profiling (controlled state, never fake) |
| `POST /api/datasets/{id}/profile` | run deterministic profiling; writes full report to `data/profiles/<id>.json`, summary to Mongo |
| `GET /api/datasets/{id}/profile` | full DataQualityReport |
| `GET /api/health/database` | MongoDB health (Phase 3) |

## 5. Deterministic profiling (Phase 5) — ZERO LLM

Engine tag on every report: `deterministic:v1:duckdb+pyarrow+pandas`.
All 25 required metrics are computed with DuckDB SQL over the normalized Parquet
(file + optional DuckDB/PyArrow): rows, columns, types, missing count/%, unique
count, cardinality ratio, duplicate rows (exact `SELECT DISTINCT *`), constant
columns, numeric stats (min/max/mean/median/std/q1/q3/count), IQR-based outlier
indicators (low/high counts), date/time detection (arrow types, or name pattern +
strict sample parse), potential IDs (uniqueness == row count; name patterns;
datetime columns excluded), categorical/numeric/boolean/text roles, target
candidates (name semantics + binary columns), leakage candidates (name patterns +
|Pearson| ≥ 0.98 with a target candidate; pairs where *both* are targets are not
accused), correlation summary (top pairs |r| ≥ 0.7, capped at 20 numeric columns).

### DataQualityReport

`quality_score, quality_grade, issues[{code,severity,column,message}], warnings,
statistics, schema, recommendations` (+ `roles`, `generated_at`, `engine`,
`dataset_id`, `original_filename`).

**Quality score formula (documented, reproducible — never an LLM):**

```
score = 100
      - min(40, 40 × overall_missing_ratio)
      - min(20, 20 × duplicate_row_ratio)
      - min(20, 10 × constant_column_count)
      - min(20, 10 × high_severity_issue_count)
      - min(10,  5 × medium_severity_issue_count)
      (floored at 0, one decimal)
grade: A ≥ 90 | B ≥ 80 | C ≥ 70 | D ≥ 60 | F < 60
```

Mongo stores the **summary** (score, grade, issue counts, top issues, report path);
the **full report** stays on E: at `data/profiles/<dataset_id>.json`.

## 6. Storage layout (all on E:)

```
datasets/<upload_id>/                  original uploads (+ extracted members)
data/<upload_id>/<dataset_id>.parquet  normalized representation
data/profiles/<dataset_id>.json        full quality reports
temp/<upload_id>/depth_<n>_<rand>/     ZIP extraction (deleted after processing)
```

MongoDB stores metadata + audit events only — never raw datasets, Parquet files,
or model binaries.

## 7. Tests

42 automated tests (`backend/tests/`, pytest, real API + real MongoDB Atlas,
all fixtures tiny and self-cleaning): all six formats, ZIP with mixed formats,
invalid ZIP, ZIP-slip (blocked + escape-proof verified), over-depth nesting,
duplicate filenames, unsupported extension, empty file, size limit, binary-masquerade,
malformed CSV/JSON/Parquet, unsafe SQL (rejection + non-execution proof),
sheet selection, headerless CSV, BOM/delimiters, contract completeness, preview,
quality 404-before-profile, exact hand-computed quality scores (63.8/D and 90.0/A),
determinism across runs, grade-threshold mapping, empty-dataset profiling, and
pure security units (sanitize_filename, zip limits, traversal entry rejection).

## 8. Known limitations

- No authentication yet on dataset endpoints (auth phase pending); user scoping
  will be added with it.
- Correlation/leakage are heuristic *candidates* for human/agent review — they are
  inputs to the future evidence-gated transformation, not verdicts.
- Exact duplicate detection is O(distinct rows); very large datasets will need
  the documented DuckDB-sampling optimization.
- Pairwise correlation capped at the first 20 numeric columns (warning emitted).
- `.xls` write tests require the dev-only `xlwt` fixture writer (runtime reads use `xlrd`).
- CPU-bound parse/profile work runs in worker threads (fine for the prototype;
  a task queue is a later-phase concern).
