# Tesoreria Movements Specification

## Purpose

Define opt-in Tesoreria downloads, privacy-safe account scoping, date planning, validation, and idempotent storage.

## Requirements

### Requirement: Opt-in Tesoreria command

The system MUST provide an opt-in `tesoreria` command for `--from`, `--to`, and `--format pdf|xls|both` after manual login. Tesoreria SHALL NOT run in default `sync`.

#### Scenario: User downloads one range
- GIVEN a user requests Tesoreria for a valid explicit date range
- WHEN login is complete and export succeeds
- THEN requested files SHALL be saved under `Tesoreria/YYYY/`

#### Scenario: Default sync excludes Tesoreria
- GIVEN a user runs default synchronization
- WHEN the plan is built
- THEN Tesoreria movements MUST NOT be included

### Requirement: Privacy-safe account identity

The system MUST require privacy-safe `--tag` or equivalent safe tag whenever `--account` is supplied. Same ranges across accounts MUST NOT collide. Raw account labels, numbers, and selector text MUST NOT appear in paths, logs, state, or summaries.

#### Scenario: Account selection requires tag
- GIVEN `--account` is supplied without a safe tag
- WHEN arguments are validated
- THEN the command MUST fail before browser startup with `--tag` guidance

#### Scenario: Account path is safe
- GIVEN `--account` and `--tag corto` are supplied
- WHEN destinations are planned
- THEN filenames SHALL include `_corto`
- AND MUST NOT include raw account text or numbers

### Requirement: Chunked date planning

The system MUST split Tesoreria requests longer than 89 days into chunks of at most 89 days in CLI and download flow.

#### Scenario: Long range is chunked
- GIVEN a 120-day Tesoreria request
- WHEN the plan is built
- THEN at least two chunks SHALL be created
- AND no chunk SHALL exceed 89 days

#### Scenario: Boundary range remains single chunk
- GIVEN an 89-day Tesoreria request
- WHEN the plan is built
- THEN exactly one chunk SHALL be created

### Requirement: Conservative tabular validation

The system MUST accept XLS/tabular output only when it matches one accepted structure: OLE XLS magic `D0 CF 11 E0 A1 B1 1A E1`; XLSX ZIP with `[Content_Types].xml` and `xl/workbook.xml`; HTML table with at least one row and one cell; or CSV/TSV-like text with at least two non-empty rows, one stable delimiter among tab/semicolon/comma, at least two header columns, and at least one header token (`fecha`, `descripcion`, `movimiento`, `valor`, `saldo`). It MUST reject empty, headerless, login, and error HTML.

#### Scenario: Structured export is accepted
- GIVEN OLE XLS, valid XLSX, valid table HTML, or valid delimited text
- WHEN validation runs
- THEN the file SHALL be valid

#### Scenario: Unsafe response is rejected
- GIVEN empty content, headerless text, login HTML, or error HTML
- WHEN validation runs
- THEN the file MUST be invalid

### Requirement: Idempotent final artifacts

The system MUST skip only valid existing final artifacts. Invalid finals MAY be replaced. For `--format both` or redownloads, failure of one format MUST leave prior valid finals for other formats untouched.

#### Scenario: Valid existing artifact is skipped
- GIVEN a destination already contains a valid Tesoreria export
- WHEN the same chunk and format are requested without forced redownload
- THEN portal export for that artifact SHALL be skipped

#### Scenario: Partial redownload preserves files
- GIVEN valid PDF and XLS finals already exist
- WHEN `--redownload --format both` succeeds for PDF but fails for XLS validation
- THEN the previous valid XLS final MUST remain available
- AND the failed XLS MUST NOT replace it

### Requirement: Evidence and documentation

The change MUST include pure pytest coverage for argument validation, safe paths, 89-day chunking, tabular validation, and redownload preservation. Documentation SHALL cover manual login, opt-in scope, safe tags, and privacy.

#### Scenario: Review evidence is complete
- GIVEN the change is ready for review
- WHEN tests and docs are inspected
- THEN each behavior SHALL have evidence
- AND no test SHALL use network, Playwright, or portal access
