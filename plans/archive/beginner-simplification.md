# Beginner simplification of the Enterprise RAG Assistant
Ticket: none (requested in chat on 2026-11-08)

Goal: a person with zero programming experience can open any file and follow it,
with every feature still working exactly as before.

**Measurable success:**
1. Only 7 third-party libraries are left in `requirements.txt` (today: 10 plus pytest).
2. No `@dataclass`, no custom decorators, no `lambda` in app code (tests may keep fakes).
3. Every file starts with a plain-English note saying what it does and who calls it.
4. All tests pass, coverage on `core/` stays at or above 80%, and the live checks
   (ingest, ask, all 6 pages) behave the same as at commit `e2a094c`.

## Phases

### Phase 1: Remove three libraries (riskiest first: real behaviour can change)
Verified when: `pytest` is green and a live ingest of one PDF plus one weather fetch works.

#### Step 1.1: Replace `tenacity` with a plain retry loop (Size: S)
- Acceptance: `generate.py` and `ingest.fetch_api` retry with a `for attempt in range(3)` loop and `time.sleep`; same retry counts and waits as today.
- Verification command: `pytest tests/test_generate.py tests/test_ingest_db.py`
- Files likely touched: `core/generate.py`, `core/ingest.py`, tests
- Test seams: `generate_text` (fake `_call_model`), `fetch_api` (fake network call)
- Blocked by: none

#### Step 1.2: Replace `httpx` with Python's built-in `urllib` (Size: S)
- Acceptance: weather fetch works live; network errors are retried, HTTP errors are not.
- Verification command: `pytest tests/test_ingest_db.py` + live "Fetch latest data"
- Files likely touched: `core/ingest.py`
- Test seams: `fetch_api`
- Blocked by: 1.1

#### Step 1.3: Replace `pymupdf4llm` with plain `pymupdf` (Size: XS)
- Acceptance: `parse_pdf` returns one text per page; the existing PDF test passes.
- Verification command: `pytest tests/test_parse.py`
- Files likely touched: `core/parse.py`, `requirements.txt`
- Blocked by: none

### Phase 2: Replace advanced Python with basics
Verified when: `pytest` is green, and the grep for `@dataclass|lambda|@retry` in `core/ utils/ pages/ app.py` finds nothing.

#### Step 2.1: Settings as plain variables (Size: S)
- Acceptance: `config.py` exposes `DATABASE_URL`, `GEMINI_API_KEY` and `missing_settings()`, which app.py uses (removes the duplicate the simplify review found).
- Files likely touched: `core/config.py`, `core/db.py`, `core/embed.py`, `core/generate.py`, `utils/ui.py`
- Blocked by: none

#### Step 2.2: Validation returns a plain list of problems (Size: S)
- Acceptance: `validate_csv` / `validate_pages` return `[]` when the file is fine and a list of sentences when not; `ValidationResult` is gone.
- Files likely touched: `core/validate.py`, `core/ingest.py`, `tests/test_validate.py`
- Blocked by: none

#### Step 2.3: Loops instead of tricky one-liners (Size: M)
- Acceptance: per gate answer Q1; names spelled out (`_12_normalize` becomes `normalize`, `r`/`c`/`d` become `row`/`chunk`/`document`).
- Files likely touched: every `core/` and `pages/` file
- Blocked by: 2.1, 2.2 (same files)

### Phase 3: Tidy the structure
Verified when: `pytest` is green and the app loads all 6 pages headless with no errors.

#### Step 3.1: Fewer, clearer files (Size: S)
- Acceptance: `core/vectors.py` (one function) moves into `core/db.py`; `utils/logger.py` + `utils/messages.py` merge into `utils/ui.py`; the 8 empty folders are deleted.
- Blocked by: Phase 2

#### Step 3.2: A plain-English header on every file (Size: S)
- Acceptance: each file opens with 2 to 4 lines: what it does, who uses it, how to run it if runnable.
- Blocked by: 3.1

### Phase 4: Reviews, then fixes
Verified when: `/simplify` and `/engineering:code-review` findings are fixed or listed as skipped with a reason, and all checks from the Goal pass.
- Blocked by: Phase 3

### Phase 5: Commit and close
- One commit per phase (green at each). Move this plan to `plans/archive/` with an execution record.

## Decision log
| Decision | Chosen option | Why |
| --- | --- | --- |
| Keep `pandas`, `streamlit`, `psycopg`, `google-genai`, `python-docx`, `pymupdf`, `python-dotenv` | Keep | Each does a job that would take far more code without it |
| Retry logic | Plain loop | Same behaviour, no library, readable top to bottom |
| Type hints | Keep the simple ones (`text: str`) | They tell a beginner what goes in and out |
| Q1 One-liners | Plain loops when a one-liner has an `if` or two `for`s; very simple ones stay | User choice: readable without hiding logic |
| Q2 PDF reading | Plain `pymupdf` (`page.get_text()`) | User choice: one less library; tables become plain text |
| Q3 Weather download | Built-in `urllib` | User choice: nothing extra to install |
| Q4 Demo data | Delete all `demo-*` data and `demo_*` uploads before Phase 1 | User choice: the demo data was stored incomplete by the embedding bug |

## Not yet specified
- Phase 4: the review findings (unknown until the reviews run).

## Always / Never
- Always: every current feature keeps working; tests stay green between phases.
- Never: new features, new libraries, database schema changes, deleting the `venv/` folder, or touching `.env`.

## Progress
| Phase | Status |
| --- | --- |
| 1 Remove libraries | done: 7 app libraries left, live download + PDF verified |
| 2 Basic Python | done: no dataclass/lambda/decorator/filtered one-liners left |
| 3 Structure | done: vectors.py, logger.py, messages.py merged; 8 empty folders gone; live end-to-end check passed |
| 4 Reviews | done: code review approved (1 fix), /simplify 11 fixes applied, 3 skipped |
| 5 Commit | done |

## Execution record (2026-11-08)
**Shipped:** commits 2213b6a (libraries), 57c5c3c (basic Python + structure),
d768a24 (code-review fix), and the /simplify pass.

**Goal check:**
1. Libraries: 7 app libraries left (was 10): tenacity, httpx, pymupdf4llm removed.
2. No `@dataclass`, custom decorator, `lambda` or filtered one-liner in app code.
   Streamlit's own `@st.cache_data` / `@st.cache_resource` stay (nothing plainer does the job).
3. Every file opens with a plain-English note.
4. 106 tests pass, 84% coverage on `core/`; live run: 60-row CSV stores 60 chunks,
   saved answers reused, evaluation hit, all 6 pages load.

**Deviations from the plan:**
- `attach_filenames()` and `source_of_documents()` were removed: `retrieve()` returns
  each passage's file name and source from one query.
- One `check_table()` now serves both CSV uploads and weather data.
- Skipped: moving the documents join into `match_chunks()` (needs a live database
  change, which is out of scope); one shared "unsupported type" check (both copies
  are needed, before saving and on the command line).
