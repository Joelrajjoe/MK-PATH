# MK-Path MVP Status — Phase 1 Foundation Audit

**Audit date:** 2026-10-06
**Phase:** PHASE 1 — FOUNDATION AUDIT (no application features implemented)
**Auditor scope:** Full repository structure, backend, frontend, database, auth, agents, API routes, docs, tests, environment files, upload/ingestion functionality.

---

## 0. CRITICAL FINDING — PROJECT LOCATION DISCREPANCY

**Required root (per specification):** `E:\MK-PATH`
**Actual workspace root (found):** `E:\MKPATH` (no hyphen)
**Also searched:** No directory named `E:\MK-PATH` exists anywhere on `E:` (or under `C:\Users\`).

Per specification section 14, the project was **NOT** moved or relocated. The discrepancy was reported to the user, who has decided:

- ✅ **DECISION (2026-10-06): `E:\MKPATH` is accepted as the project root.** All spec references to `E:\MK-PATH` (storage paths such as `.venv`, `data`, `datasets`, `models`, `artifacts`, `logs`, `reports`, `temp`, `docs`) resolve to `E:\MKPATH` equivalents going forward.

**Second critical finding:** the workspace is **empty**. A full recursive scan found exactly **1 file**:

```
E:\MKPATH\.freebuff\project-id      (workspace metadata, not application code)
```

There is **no git repository, no source code, no docs, no tests, no .env, no venv** in the workspace. There is no existing MK-Path *data platform* implementation to preserve inside this repository.

**Adjacent system detected (outside workspace):** `E:\MKLP` — a complete, git-tracked project whose README titles itself *"MK-Path: Enterprise Multimodal Knowledge-Graph Framework for Adaptive Learning"*. It is a **different product domain** (EdTech adaptive learning), not the autonomous data-transformation platform described in this specification. It was inspected read-only for this audit; **no files in it were modified, moved, or deleted.**

- ✅ **DECISION (2026-10-06): `E:\MKLP` is to be IGNORED entirely.** It will not be forked, copied, or referenced as a code source. The platform is built greenfield in this workspace. (Historical audit notes about `E:\MKLP` below are retained for traceability only.)

---

## 1. IMPLEMENTED

Nothing is implemented **inside this workspace** (`E:\MKPATH`).

| Item | Status | Evidence |
| --- | --- | --- |
| Project directory `E:\MKPATH` exists | Implemented | Directory present on `E:` drive |
| This status document | Implemented | `docs/MVP_STATUS.md` (this file) |

### Reusable assets available in adjacent repo `E:\MKLP` (read-only, not part of this workspace)

| Capability | Evidence in `E:\MKLP` | Reusable for this spec? |
| --- | --- | --- |
| FastAPI app skeleton | `backend/app/main.py` (~151 routes) | Partially — domain differs |
| MongoDB Atlas integration (Motor async, env-driven, graceful offline mode) | `backend/app/database.py`, `backend/app/config.py` (`MONGODB_URI`, `MONGODB_DATABASE`, db default `mk_path`) | Yes — pattern is spec-compliant |
| Clerk RS256 JWKS authentication | `backend/app/auth.py` (JWKS cache, `get_current_user`) | Yes — must be preserved per spec §5 if auth is adopted |
| React + Vite + Tailwind frontend | `frontend/` (React 19, Vite 8, Tailwind 4, Clerk, React Router) | Yes — spec says keep existing frontend stack |
| Upload endpoint with validation | `POST /api/materials/upload` (extension/MIME routing, 25 MB cap, empty-file check) | Pattern only — accepts PDF/TXT/images/audio/video, **not** CSV/XLSX/JSON/Parquet/SQL/ZIP |
| Test suite | 25+ `test_phase*.py` unittest harnesses | Pattern only — all EdTech-domain tests |
| Documentation set | `docs/` (25 files) + root-level README/ARCHITECTURE/SECURITY/API_SPEC | Partially — 5 of 8 required docs exist there |

### Available host tooling (already installed on machine, no installation performed)

System Python **3.10.7** (`C:\Program Files\Python310\python.exe`) already has: `fastapi 0.136.1`, `pydantic 2.12.5`, `uvicorn 0.47.0`, `langgraph 1.0.5`, `langchain 1.2.0`, `duckdb 0.10.0`, `pandas 2.3.3`, `pyarrow 19.0.1`, `scikit-learn 1.6.1`, `lightgbm 4.6.0`, `openpyxl 3.1.5`, `motor 3.7.1`, `pymongo 4.15.1`, `python-multipart 0.0.20`, `pytest 9.1.1`. (Missing from that list: `optuna`, `dowhy`, `shap`, `xlrd` — not installed, per §"no unnecessary packages".)

---

## 2. PARTIALLY IMPLEMENTED

| Item | What exists | What is missing |
| --- | --- | --- |
| Project root location | Root is on `E:` (correct drive, per §3) | Name is `MKPATH`, spec requires `MK-PATH` (§14) — **not relocated, awaiting decision** |
| Documentation set | This file created | 7 of 8 required docs not yet present in workspace: `ARCHITECTURE.md`, `MVP_SCOPE.md`, `INNOVATION.md`, `DATA_INGESTION.md`, `SECURITY.md`, `VERIFICATION_GATES.md`, `API_SPEC.md` |
| Candidate existing repo | `E:\MKLP` has 5/8 required docs (`ARCHITECTURE`, `MVP_SCOPE`, `API_SPEC`, `MVP_STATUS`, root `SECURITY`) | Missing `INNOVATION`, `DATA_INGESTION`, `VERIFICATION_GATES`; and its docs describe the EdTech product, not this data platform |
| Authentication | Clerk RS256 JWKS implemented in `E:\MKLP` | Not present in this workspace; no decision yet on whether this project adopts it |
| MongoDB Atlas credentials | Provided by user in prompt; `E:\MKLP\.env` already carries `MONGODB_URI`/`MONGODB_DATABASE` (gitignored) | Not written to any file in this workspace (deliberately — see Security) |

---

## 3. MISSING (entirely absent from workspace)

| # | Spec requirement | Status |
| --- | --- | --- |
| 1 | Project structure (backend/frontend/docs layout) | Missing |
| 2 | Backend (FastAPI application) | Missing |
| 3 | Frontend application | Missing |
| 4 | Python version configuration / `requirements.txt` / lockfile | Missing |
| 5 | Virtual environment `E:\MK-PATH\.venv` (spec §3) | Missing (no `.venv` in workspace; `E:\MKLP\backend\.venv` exists but is Python **3.11.15**, not the required 3.10.x) |
| 6 | FastAPI application + API routes | Missing |
| 7 | MongoDB Atlas integration (`MONGODB_URI`, `MONGODB_DATABASE`, db `mk_path`) | Missing (pattern exists only in `E:\MKLP`) |
| 8 | LangGraph / LangChain multi-agent orchestration | Missing (no agent code anywhere; `E:\MKLP` contains **no** real LangGraph usage — only keyword strings in intent regexes) |
| 9 | Upload functionality (CSV/XLSX/XLS/JSON/Parquet/SQL/ZIP) | Missing |
| 10 | Data ingestion, validation, schema/metadata extraction | Missing |
| 11 | Profiling (DuckDB/Pandas/PyArrow) | Missing |
| 12 | Semantic understanding / NL business-goal intake | Missing |
| 13 | Data Analyst / Data Scientist / ML Engineer agents | Missing |
| 14 | Deterministic verification gates (PASS/FAIL/HUMAN REVIEW) | Missing |
| 15 | Data-quality, ambiguity, leakage detection | Missing |
| 16 | Causal analysis (DoWhy), model comparison, explainability (SHAP) | Missing |
| 17 | FastAPI artifact generation for deployment | Missing |
| 18 | Audit trail / audit events | Missing |
| 19 | Safe transformation/healing with evidence + approval | Missing |
| 20 | Tests (any framework) | Missing |
| 21 | `.env` / `.env.example` / `.gitignore` | Missing |
| 22 | Git repository | Missing (`fatal: not a git repository`) |
| 23 | Storage scaffolding (`data/`, `datasets/`, `models/`, `artifacts/`, `logs/`, `reports/`, `temp/`) | Missing |
| 24 | README / status documentation (beyond this file) | Missing |

---

## 4. BROKEN

| Item | Problem | Impact |
| --- | --- | --- |
| Project root naming | Workspace is `E:\MKPATH`; spec mandates `E:\MK-PATH` (§14) | Must be resolved by user before later phases that hardcode storage paths |
| Workspace emptiness vs "existing repository" premise | The brief assumes an existing MK-Path repo; the workspace contains none | All "reuse existing components / don't duplicate" checks currently resolve to *nothing to reuse inside the workspace* |
| `E:\MKLP` name collision | An unrelated EdTech project also brands itself "MK-Path" | Risk of auditing/modifying the wrong repo; it must not be treated as this platform's codebase without explicit approval |
| Spec vs available Python env in `E:\MKLP` | Its `.venv` is 3.11.15; spec requires 3.10.x | Only relevant if `E:\MKLP` code is ever adopted; host system Python 3.10.7 satisfies the spec |
| Credential exposure in transcript | MongoDB username/password were pasted in plain text into this conversation | Not written to disk here; rotation recommended (see §8) |

---

## 5. PLANNED (not started — subsequent phases require explicit go-ahead)

- Phase 2+: repository scaffolding under the confirmed project root (`pyproject`/`requirements`, `.venv` on `E:`, `.env.example`, `.gitignore`, git init).
- FastAPI backend with auth-verified, user-scoped API routes.
- Secure upload/ingestion pipeline for `.csv .xlsx .xls .json .parquet .sql .zip` with ZIP-traversal/size/malware-class validation (spec §6).
- Deterministic schema/metadata extraction + DuckDB/Pandas/PyArrow profiling → §13 output contract.
- LangGraph orchestration (Analyst / Scientist / ML Engineer) with LLM-output validation.
- Evidence-Gated Autonomous Data Transformation core (Proposal → Evidence → Verification → PASS/FAIL/HUMAN REVIEW).
- MongoDB Atlas metadata/audit store (metadata only — no raw datasets/model blobs).
- Remaining required docs: `ARCHITECTURE.md`, `MVP_SCOPE.md`, `INNOVATION.md`, `DATA_INGESTION.md`, `SECURITY.md`, `VERIFICATION_GATES.md`, `API_SPEC.md`.
- Test suite (pytest already available on host).

---

## 6. IMPLEMENTATION GAP REPORT (precise)

| Spec area | Required | Actual (workspace) | Gap |
| --- | --- | --- | --- |
| Root path | `E:\MK-PATH` | `E:\MKPATH` (empty) | Rename decision + full scaffold needed |
| Backend | Python 3.10 + FastAPI + Pydantic | none | 100% |
| Agents | LangGraph/LangChain | none | 100% |
| Data stack | DuckDB/Pandas/PyArrow/sklearn/LightGBM/Optuna/DoWhy/SHAP | none installed in project env (several present in system Python, unmanaged) | 100% |
| Frontend | existing stack or React+Vite+Tailwind | none in workspace | 100% |
| Database | MongoDB Atlas, `mk_path`, env-driven | none in workspace | 100% |
| Auth | preserve existing (Clerk if present) | none in workspace (Clerk exists only in `E:\MKLP`) | Decision needed |
| Upload formats | 6 types + ZIP | none | 100% |
| Verification gates | deterministic PASS/FAIL/REVIEW | none | 100% |
| Audit trail | event per important op | none | 100% |
| Docs | 8 files | 1 of 8 (`MVP_STATUS.md`) | 7 files |
| Tests | run + report | none exist to run | 100% |

**Bottom line:** MK-Path, as specified in this brief, is a **greenfield build** at `E:\MKPATH`. Per user decision (2026-10-06), `E:\MKLP` is ignored entirely — no code, patterns, or dependencies are adopted from it.

---

## 7. PHASE 1 COMPLIANCE

- ✅ Inspected repository (workspace + adjacent candidate repo).
- ✅ No packages installed.
- ✅ No architecture changed.
- ✅ No code deleted or modified outside this document.
- ✅ No project relocation performed (discrepancy reported instead).
- ✅ No mock data, fake results, or fabricated metrics.
- ❌ Tests executed: **none** — no test files exist in the workspace (reported honestly).
- ✅ Project-root decision resolved: **`E:\MKPATH` is the project root.**
- ✅ Adjacent-repo decision resolved: **ignore `E:\MKLP`.**
- ✅ Phase 1 complete (2026-10-06).

---

## 8. PHASE 2 — E-DRIVE DEVELOPMENT ENVIRONMENT (COMPLETE, 2026-10-06)

> Path mapping: spec `E:\MK-PATH` = workspace `E:\MKPATH` (per recorded Phase 1 decision).

### Created

| Item | Value |
| --- | --- |
| Storage directories | `data/`, `datasets/`, `models/`, `artifacts/`, `logs/`, `reports/`, `temp/`, `docs/` — all on `E:\MKPATH` |
| Virtual environment | `E:\MKPATH\.venv` — **Python 3.10.7** ✅ (spec requires 3.10.x) |
| pip | 26.2.1 inside `.venv` |
| pip cache | redirected to `E:\MKPATH\.pip-cache` (142 MB) via `pip config --user global.cache-dir` — no large cache created on `C:` |
| `requirements.txt` | 67 pinned packages generated from the resolved environment |
| `.env` / `.env.example` / `.gitignore` | created; `.env` gitignored, credentials never committed |

### Dependency inspection before install (as required)

System Python 3.10.7 already had all 15 required packages (fastapi, uvicorn, pydantic, python-dotenv, pymongo, duckdb, pandas, pyarrow, openpyxl, scikit-learn, scipy, langgraph, langchain, plotly — plus python-multipart required for FastAPI uploads). The isolated `.venv` was still provisioned hermetically so MK-Path is not coupled to machine-global state.

### Installed versions (`.venv`)

fastapi 0.142.2 · uvicorn 0.54.0 · pydantic 2.13.5 · python-dotenv 1.2.4 · pymongo 4.18.2 · duckdb 1.5.6 · pandas 2.3.3 · pyarrow 25.0.1 · openpyxl 3.1.5 · scikit-learn 1.7.2 · scipy 1.15.3 · langgraph 1.2.13 · langchain 1.4.3 · plotly 7.1.0 · python-multipart 0.0.32

### Not installed (per spec)

PyTorch, TensorFlow, CUDA, local LLMs, Spark, Kubernetes, Docker — **0 matches** in `requirements.txt` (verified by grep).

### Phase 2 tests

| Test | Result |
| --- | --- |
| `python --version` | `Python 3.10.7` ✅ |
| `pip --version` | `pip 26.2.1 from E:\MKPATH\.venv\...` ✅ |
| `python -c "import duckdb, pandas, pyarrow, pymongo"` | `IMPORT OK: 1.5.6 / 2.3.3 / 25.0.1 / 4.18.2` (exit 0) ✅ |
| Forbidden-package scan of `requirements.txt` | 0 matches ✅ |

---

## 9. PHASE 3 — MONGODB ATLAS FOUNDATION (COMPLETE, 2026-10-06)

### Created

| File | Purpose |
| --- | --- |
| `backend/app/config.py` | env-driven settings (`MONGODB_URI`, `MONGODB_DATABASE`) — no hardcoded credentials |
| `backend/app/database.py` | reusable async `DatabaseManager`: connect/ping, graceful failure, `get_database()`, `get_collection()` (allow-list of declared collections), `ensure_collections()`, `health()` |
| `backend/app/main.py` | FastAPI app with non-fatal lifespan bootstrap + `GET /api/health/database` |
| `backend/app/__init__.py` | package marker |
| `.env` | real Atlas URI + `MONGODB_DATABASE=mk_path` (gitignored, backend-only, never sent to any frontend) |

### Design decisions

- **pymongo native `AsyncMongoClient`** used (pymongo 4.18.2 ships an async client) — honors the spec's package list without adding `motor`.
- **Non-fatal startup:** connection + collection bootstrap run once inside `lifespan` with try/except; failure logs a warning and the API serves degraded. Verified: server with empty `MONGODB_URI` still answers `/` with 200.
- **Credentials never in responses:** health returns exception class names only; secret-scan of responses = 0 matches.
- **Collections created on real Atlas (10/10):** `projects`, `datasets`, `ontology`, `agent_runs`, `clarification_questions`, `validation_results`, `models`, `artifacts`, `audit_events`, `healing_events`.
- **Indexes — only where justified:** `audit_events.created_at` (-1) and `agent_runs.created_at` (-1) for reverse-chronological audit/run queries. All other collections intentionally left unindexed (no read pattern yet; indexes cost write throughput). No fake data inserted.
- **Collection allow-list:** `get_collection()` returns None for any collection outside the declared set (blocks accidental writes elsewhere).

### Phase 3 tests (all against REAL MongoDB Atlas)

| Test | Result |
| --- | --- |
| `GET /api/health/database` (configured server, :8000) | **HTTP 200** `{"status":"healthy","database":"mk_path"}` ✅ (exact spec format) |
| Direct verification: collections present on Atlas | **10 / 10**, missing = [] ✅ |
| Index verification on Atlas | `audit_events`: `[_id_, created_at_-1]`, `agent_runs`: `[_id_, created_at_-1]` ✅ |
| Undeclared collection access | BLOCKED (`None`) ✅ |
| Graceful failure (empty `MONGODB_URI`, server :8010) | health = **HTTP 503** `{"status":"unhealthy","database":"mk_path","reason":"MONGODB_URI_NOT_CONFIGURED"}`, `/` still **200** ✅ |
| Secret leakage scan of all responses | 0 matches ✅ |
| Bug found & fixed during testing | `CollectionExists` → `CollectionInvalid` (ImportError); un-awaited `AsyncMongoClient.close()` → awaited; re-verified clean (stderr empty, exit 0) ✅ |

### Run command

```bash
cd E:\MKPATH\backend
..\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# Health:  http://127.0.0.1:8000/api/health/database
# API docs: http://127.0.0.1:8000/docs
```

(Server left running on :8000 at time of report.)

### Remaining limitations (Phases 2-3)

- No auth on the health endpoint yet (auth arrives with the API-routes phase).
- No `.env` encryption beyond gitignore (OS user-level file ACLs only).
- No frontend; no CORS configured yet.
- Collection baselines are empty (no fake data inserted, per spec §8).
- `pyproject.toml` not created — plain `requirements.txt` used (matches the minimal greenfield architecture; can be adopted later).

---

## 10. PHASE 4 — UNIVERSAL DATA INGESTION ENGINE (COMPLETE, 2026-10-06)

### Created

| File | Purpose |
| --- | --- |
| `backend/app/ingestion/security.py` | Untrusted-input guards: ZIP Slip/traversal/symlink/absolute-path rejection, duplicate-name disambiguation, entry-count/estimated-size/compression-ratio budgets, running-byte extraction budget, `sanitize_filename`, `safe_join` |
| `backend/app/ingestion/parsers.py` | Deterministic parsers: CSV (delimiter/encoding/header detection, malformed-row line errors), Excel (.xlsx via openpyxl read-only metadata; .xls via xlrd; sheet selection), JSON (array/NDJSON/single-object/scalar-array; nested flattening; unsupported-shape errors), Parquet (PyArrow metadata, no conversion), SQL (allow-list execution layer) |
| `backend/app/ingestion/service.py` | Pipeline orchestration: signature validation, secure storage, ZIP extraction + recursive discovery (MAX_ZIP_DEPTH), manifest, per-file parsing, normalized storage, metadata docs, structured fatal errors |
| `backend/app/ingestion/registry.py` | DuckDB registration (lazy `ds_<dataset_id>` views over Parquet) + JSON-safe preview/describe |
| `backend/app/routers/datasets.py` | 8 endpoints (upload/list/get/schema/preview/quality + profile POST/GET), streamed multipart upload with size cap, error→HTTP mapping, audit events |
| `backend/app/audit.py` | Audit-trail writer (never fatal, never records credentials) |
| `backend/app/repo.py` | Dataset metadata repository (MongoDB) |
| `backend/tests/conftest.py`, `backend/tests/test_ingestion.py` | Fixtures + all 13 required scenarios & security units |

### Verified behaviour (live smoke test, real files, real Atlas)

- CSV upload → 201, dataset with 4 rows/4 cols, preview rows correct, quality 404 `NOT_PROFILED` before profiling (controlled state).
- ZIP with mixed CSV+JSON + a `../slip.txt` entry → 201, 2 datasets ingested, slip entry reported `PATH_TRAVERSAL`, manifest lists every member, **zero escape** outside `temp/` (verified on disk).
- Unsupported files inside archives reported separately (`unsupported_files`), never silently ignored.

### Storage impact

Originals in `datasets/<upload_id>/`, normalized Parquet in `data/<upload_id>/`, extraction scratch in `temp/<upload_id>/` (removed after processing) — all on `E:`.

---

## 11. PHASE 5 — ZERO-LLM DATA PROFILING (COMPLETE, 2026-10-06)

### Created

| File | Purpose |
| --- | --- |
| `backend/app/profiling/profiler.py` | Deterministic `DataQualityReport` (DuckDB + PyArrow + pandas; engine tag `deterministic:v1:duckdb+pyarrow+pandas`): all 25 required metrics incl. exact duplicate rows, IQR outliers, date detection, ID/target/leakage candidates, correlation summary |
| `backend/tests/test_profiling.py` | Hand-computed score tests, determinism, grade thresholds, empty dataset, 404 paths |

### Quality score (documented formula, never an LLM)

`score = 100 − min(40, 40×missing_ratio) − min(20, 20×duplicate_ratio) − min(20, 10×constant_cols) − min(20, 10×high_issues) − min(10, 5×medium_issues)` → grade A/B/C/D/F at 90/80/70/60.

Hand-computed fixtures assert **exactly 63.8 (D)** for a dirty dataset and **90.0 (A)** for a clean one; re-profiling produces byte-identical statistics/issues (determinism verified).

### Storage

Summary (score/grade/issue counts/top issues/report path) in MongoDB `datasets.profile`; full report JSON on `E:` at `data/profiles/<dataset_id>.json`.

---

## 12. PHASE 4-5 TEST RESULTS

```
cd E:\MKPATH\backend
..\.venv\Scripts\python -m pytest tests -q
→ 42 passed in 34.51s   (PYTEST_EXIT=0)
```

Coverage: CSV, XLSX (+sheet selection), XLS, JSON, NDJSON, nested JSON, Parquet,
SQL, ZIP mixed, invalid ZIP, ZIP Slip (escape-proof), over-depth nesting, duplicate
names, unsupported extension, empty file, upload size limit, binary masquerade,
malformed CSV/JSON/Parquet, unsafe SQL (rejection + non-execution proof),
headerless CSV, BOM/delimiter detection, full contract fields, preview, quality
404-before-profile, exact scores, determinism, grade mapping, empty-dataset
profiling, security units. All fixtures tiny; all test data auto-cleaned from Atlas.

### Bugs found by tests and fixed (not suppressed)

1. SQL export ran before INSERTs executed → tables exported empty (two-phase execute→export).
2. `unique_count` used `count(col)` instead of `count(DISTINCT col)` → constant/ID/binary detection broken.
3. Outlier query unpacked one column into two values → profiler 500.
4. Leakage check accused the target column itself when both columns were targets → exactly-one-target rule.
5. Datetime columns could appear in two roles + be flagged as IDs → single-role + datetime exclusion.
6. Corrupt nested archives / corrupt entries could raise raw exceptions → reported as rejected/unsupported.
7. `fetch_arrow_table` deprecation → `to_arrow_table`.
8. Temp extraction dirs leaked on some error paths → cleanup on every failure path.

---

## 13. REMAINING LIMITATIONS (as of Phase 5)

- No authentication/authorization on dataset endpoints yet (next phase); no user scoping.
- No frontend/CORS yet.
- Exact duplicate detection is O(distinct rows); sampling optimization documented for very large data.
- Pairwise correlation capped at first 20 numeric columns (warning emitted).
- `pyproject.toml` not created (plain pinned `requirements.txt`, 75 packages, 0 forbidden).
- `.env` protected by gitignore only; repository not yet git-initialized.

---

## 14. PHASE 6 — SEMANTIC KNOWLEDGE LAYER (COMPLETE, 2026-10-06)

### Created

| File | Purpose |
| --- | --- |
| `backend/app/semantic/models.py` | All 13 required concept types (`ConceptType`: dataset, table, column, metric, dimension, target, feature, event, business_term, definition, relationship, ambiguity, user_decision) + `SemanticContext` (every spec field), `Concept`, `Ambiguity`, `UserDecision`, `Relationship`, `ColumnDefinition`, evidence model |
| `backend/app/semantic/builder.py` | Deterministic context builder: structural roles from the Phase 5 profile (fallback: schema types + name patterns), tiny business glossary (terms + definitions), relationships, ambiguity detectors, documented confidence formula, interrupt logic, version carry-over of user decisions |
| `backend/app/semantic/llm.py` | Pluggable proposal provider: `GeminiProvider` (REST, structured JSON, key from env only, degrades to unavailable on any failure) + `NullProvider`; proposals are ALWAYS `source=llm_proposed / status=needs_review` — the provider layer cannot finalize semantics |
| `backend/app/semantic/service.py` | Persistence (`ontology` versioned contexts, `clarification_questions`), never-ask-twice signature dedupe, user-decision resolve flow, audit events |
| `backend/app/routers/semantic.py` | 5 endpoints (below) |
| `backend/tests/test_semantic.py` | 12 tests incl. scripted-LLM non-finalization proof |
| `backend/app/database.py` (modified) | Justified indexes: `ontology(dataset_id, created_at)`, `clarification_questions(dataset_id, status, created_at)` |
| `backend/app/config.py` (modified) | `MKPATH_SEMANTIC_CONFIDENCE_THRESHOLD` (default 0.7), `MKPATH_SEMANTIC_MAX_LLM_COLUMNS` |

### API

```
POST /api/datasets/{id}/semantic              {"business_goal": ...} -> build; may INTERRUPT
GET  /api/datasets/{id}/semantic              latest versioned context
GET  /api/datasets/{id}/semantic/ambiguities  open ambiguities + linked questions
GET  /api/clarifications?dataset_id=&status=  clarification question listing
POST /api/clarifications/{qid}/resolve        {"choice", "note"} -> UserDecision, resume
```

### Confidence / interrupt mechanism (documented, deterministic)

```
confidence = max(0, 1 - 0.35×open_blocking - 0.15×open_advisory - 0.15×(no business_goal))
workflow_status = "interrupted" if confidence < MKPATH_SEMANTIC_CONFIDENCE_THRESHOLD else "ready"
```

Blocking ambiguities (default threshold 0.7): `TARGET_SELECTION` (0 or ≥2 target
candidates) and `VALUE_MAPPING` (coded columns like the spec's `status` example).
One open blocking ambiguity (0.65) always interrupts and creates a clarification
question in `clarification_questions`. The same signature is never asked twice
while open. Resolving re-computes confidence (versioned context) and emits
`semantic_ready` when the threshold is met again.

### Non-finalization guarantee (spec: LLM may propose, never finalize)

- LLM proposals carry `source=llm_proposed`, `status=needs_review`, confidence
  capped in reporting; a `needs_review` interpretation concept is recorded.
- Business meaning (`ColumnDefinition.business_meaning`, target confirmation) is
  set ONLY by `POST /api/clarifications/{qid}/resolve` (a `UserDecision`).
- Deterministic finalization is limited to structural facts (dataset/table/column
  existence, identifier and event-time detection) and a single explicitly
  name-matched target; when ≥2 name-matched targets exist ALL are demoted to
  candidates and the choice is forced through a clarification question.
- Without `GEMINI_API_KEY` the layer runs deterministic-only, states so in
  warnings, and invents nothing (verified by tests).

### Tests

Full suite: **54 passed / 0 failed** (`pytest tests -q`, PYTEST_EXIT=0).
New Phase 6 coverage: coded-column interrupt + Mongo persistence of
`clarification_questions`/`ontology`, all required `SemanticContext` fields,
concept-type coverage, target selection (multi/zero candidates),
target-must-be-real-column validation, double-resolve 409, unknown 404s,
confidence formula exactness (0.65 / 0.5 / 0.3), no-goal penalty,
LLM-unavailable warning, scripted-LLM proposals stay non-final, rebuild does
not re-ask resolved questions.

### Live smoke test (real Atlas, real API)

Upload → profile → `POST .../semantic` on a dataset with a coded `status`
column (values 1,2,3,4) → **workflow interrupted, confidence 0.65**, one
`VALUE_MAPPING` clarification question stored → resolve with
`"4=cancelled;1=active;2=test order;3=fraud hold"` → **workflow ready,
confidence 1.0, version 2**, `business_meaning` set with
`meaning_source=user_decision`, audit trail:
`dataset_ingested → dataset_profiled → semantic_context_built → semantic_interrupt → clarification_resolved → user_decision_recorded → semantic_ready`.
All smoke data removed afterwards (collections back to 0).

### Known limitations (Phase 6)

- Gemini proposals are implemented but unverified against the live API (no
  `GEMINI_API_KEY` configured); the provider degrades to deterministic-only and
  is covered by a scripted provider in tests.
- The business glossary is a small deterministic seed; richer term extraction
  arrives with LLM-driven agent phases.
- Ambiguity detectors are heuristic (name patterns + cardinality) by design;
  evidence-gated transformation (later phase) will consume these explicitly.
- No frontend for clarification questions yet (API-only).

- ⏹ **STOPPING HERE per instructions — Phase 6 complete; awaiting next-phase authorization.**
