# API Test Auto-Generation from Specification - Design Document

This document is for Claude Code session continuity.
It captures the design decisions and current status for auto-generating API test scripts from TOKIUM's API specification.

## Goal

Automatically generate `.cmd` test scripts (curl-based) from the TOKIUM API specification document, instead of manually copying and editing existing `.cmd` files.

## Current Status: NOT YET IMPLEMENTED

As of 2026-02-25, there is no auto-generation mechanism. All test scripts are manually created by copying existing `.cmd` templates and editing endpoints/parameters/expected status codes.

### Current manual workflow

```
Developer reads API spec (Excel)
    -> Manually copies existing .cmd file
    -> Manually edits endpoint, parameters, body, expected status
    -> Manually adds call line to run-all.cmd
```

## Input Source: TOKIUM API Specification (Excel)

- File: `【TOKIUM】標準API仕様書（20260630）`
- Format: Excel workbook with multiple sheets
- Each sheet = one API definition (endpoint, parameters, response)
- Sheet naming: `{number}{API name}` (e.g., "3部署取得API", "38経費取得API")

### Known sheets (from change history)

| Sheet | API | Relevance to existing tests |
|---|---|---|
| 1共通事項 | Common (base URL, auth) | HIGH - base configuration |
| 2従業員取得API | GET /members | Not tested yet |
| 3部署取得API | GET /groups.json | TESTED - get-groups.cmd |
| 4役職取得API | GET /posts | Not tested yet |
| 5プロジェクト取得API | GET /projects | Not tested yet |
| 6承認フロー取得API | GET /approval_flows | Not tested yet |
| 7申請フォーム取得API | GET /application_forms | Not tested yet |
| 38経費取得API | GET /expenses | Not tested yet |
| 39経費科目取得API | GET /categories | Not tested yet |
| 40経費精算取得API | GET /reports (expenses) | Related to existing reports tests |
| 41-46 | Batch job APIs for generic master | Not tested yet |
| 47-48 | Generic master APIs | Not tested yet |
| 49 | Accounting data export API | Not tested yet |
| 50 | Receipt image API | Not tested yet |
| 51-54 | SAML APIs | Not tested yet |

### Available file in document/

- `【TOKIUM】標準API仕様書（20260630） - 更新履歴.csv` — Change history only. Does NOT contain API definitions (no endpoints, parameters, or response structures). Not usable for test generation.

### Files still needed (CSV export from Excel)

To proceed, the following sheets must be exported as CSV and placed in `document/`:
1. **1共通事項** — Base URL pattern, authentication method, common headers, rate limits
2. **One or more API definition sheets** — e.g., "3部署取得API" for groups

Each API definition sheet is expected to contain:
- Endpoint path
- HTTP method
- Request parameters (name, type, required, description)
- Request body structure (if any)
- Response structure and status codes

## Chosen Approach: CSV -> .cmd Auto-Generation

### Why CSV (not screenshot)

| Factor | CSV | Screenshot |
|---|---|---|
| Parse accuracy | 100% (structured data) | ~95% (LLM-dependent) |
| Input effort | Excel "Save As CSV" | Take screenshot |
| Reproducibility | Deterministic | May vary per analysis |
| CI/CD compatibility | Easy | Difficult |
| Complex JSON handling | Exact (if CSV is correct) | Risk of misreading nested structures |
| Cell merges in Excel | Flattened on export | May cause misattribution |

**Decision: CSV is the primary input method.** Screenshot is a fallback only when CSV export is not possible.

### Hybrid approach (optional enhancement)

```
Screenshot of API spec
    -> Claude Code analyzes image
    -> Generates intermediate CSV
    -> Human reviews/corrects CSV (quick check)
    -> generate-tests.py produces .cmd files
```

This combines screenshot convenience with CSV accuracy, but is not the initial implementation target.

## Planned Architecture

```
document/
├── 【TOKIUM】標準API仕様書 - 1共通事項.csv        # Input: common config
├── 【TOKIUM】標準API仕様書 - 3部署取得API.csv      # Input: API spec
├── 【TOKIUM】標準API仕様書 - 更新履歴.csv          # Reference only
└── README.md                                       # This file

tools/
├── format-json.py                                  # Existing: JSON formatter
└── generate-tests.py                               # NEW: CSV -> .cmd generator

tests/
├── _load-env.cmd                                   # Existing: common
├── _setup-results.cmd                              # Existing: common
├── generated/                                      # NEW: auto-generated .cmd files
│   └── *.cmd
└── ...                                             # Existing: manually created tests
```

### generate-tests.py responsibilities

1. Read API spec CSV from `document/`
2. Parse columns: endpoint, method, parameters, body, expected status
3. Generate `.cmd` files using the established test pattern:
   - `call _load-env.cmd`
   - `call _setup-results.cmd`
   - `curl` with appropriate flags
   - `python tools\format-json.py` for response formatting
   - Status code assertion (`[PASS]` / `[FAIL]`)
4. Output to `tests/generated/`

### Test pattern template (existing convention)

```cmd
@echo off
setlocal enabledelayedexpansion

call "%~dp0..\_load-env.cmd"
if errorlevel 1 exit /b 1
call "%~dp0..\_setup-results.cmd"

echo --- {TEST_NAME} ---
curl -s -o "%RESULTS_DIR%\{OUTPUT_FILE}.json" -w "%%{http_code}" ^
  -X {METHOD} ^
  -H "Authorization: Bearer %API_KEY%" ^
  -H "Accept: application/json" ^
  "{URL}" > "%RESULTS_DIR%\_status.tmp"

set /p STATUS=<"%RESULTS_DIR%\_status.tmp"
del "%RESULTS_DIR%\_status.tmp"
python "%~dp0..\..\tools\format-json.py" "%RESULTS_DIR%\{OUTPUT_FILE}.json" 2>nul

if "%STATUS%"=="{EXPECTED}" (
    echo [PASS] {TEST_NAME} - {EXPECTED} OK
    exit /b 0
) else (
    echo [FAIL] {TEST_NAME} - Expected {EXPECTED}, got %STATUS%
    exit /b 1
)
```

## Blockers

- **Cannot proceed until API definition CSVs are provided.** The change history CSV does not contain endpoint/parameter/response information.
- CSV column structure is unknown until an actual API sheet is exported and analyzed.

## Next Steps

1. Export at least one API definition sheet as CSV (e.g., "3部署取得API")
2. Export "1共通事項" sheet as CSV
3. Analyze CSV column structure
4. Implement `generate-tests.py`
5. Validate generated `.cmd` against existing manually-created tests
