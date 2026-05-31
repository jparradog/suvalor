# Documentos Specification

## Purpose

Define PB opt-in behavior, row extraction, naming identity, idempotency, date parsing, and PDF verification.

## Requirements

### Requirement: PB opt-in only

The system MUST keep PB excluded from default document synchronization. The system MAY process PB only when the user explicitly selects PB.

#### Scenario: Defaults exclude PB
- GIVEN a user runs document synchronization with default types
- WHEN the document type set is resolved
- THEN PB MUST NOT be included

#### Scenario: Explicit PB is accepted
- GIVEN a user requests only PB documents
- WHEN the document type set is resolved
- THEN PB SHALL be included without adding FB or other non-default types

### Requirement: PB row parsing by normalized headers

For PB grids, the system MUST map normalized `N°Papeleta` to document id and `Fecha Operacion` to row date. Header normalization SHOULD tolerate case, accents, punctuation, symbols, and whitespace. Missing required PB headers MUST fail closed for the whole grid.

#### Scenario: PB row is extracted
- GIVEN a PB grid with headers equivalent to `N°Papeleta` and `Fecha Operacion`
- WHEN rows are extracted
- THEN each row SHALL expose papeleta as document number
- AND operation date as row date

#### Scenario: Required PB header is missing
- GIVEN a PB grid missing the papeleta or operation-date header
- WHEN rows are extracted
- THEN extraction MUST fail deterministically for the grid
- AND no row SHALL be silently skipped or guessed from legacy positions

### Requirement: PB filename, inventory identity, and idempotency

The system MUST name PB files `YYYY-MM-DD_PB_<papeleta>.pdf` using `Fecha Operacion`. The inventory key MUST be `PB_<papeleta>`. Existing inventory key or target filename MUST skip download/postback and MUST NOT create duplicates.

#### Scenario: PB identity is stable
- GIVEN a PB row with papeleta `12345` and operation date `05/04/2025`
- WHEN the download identity is built
- THEN the filename SHALL be dated `2025-04-05`
- AND the inventory key SHALL be `PB_12345`

#### Scenario: PB download is idempotent
- GIVEN inventory has key `PB_12345` or the target filename exists
- WHEN the same PB row is considered for download
- THEN the system MUST skip download and postback
- AND it SHALL NOT record duplicate inventory or success

### Requirement: Numeric and Spanish grid dates

The system MUST parse numeric `DD/MM/YYYY` using the numeric month. It MUST continue parsing supported Spanish month-name dates. Invalid dates MUST fail instead of producing month `00`.

#### Scenario: Numeric date parses correctly
- GIVEN the grid date `05/04/2025`
- WHEN it is normalized
- THEN the result SHALL be `2025-04-05`

#### Scenario: Invalid numeric date is rejected
- GIVEN the grid date `31/02/2025`
- WHEN it is normalized
- THEN parsing MUST fail deterministically

### Requirement: Conservative PDF EOF sanitization and verification

The system MUST truncate only bytes after the last `%%EOF`. Sanitized bytes MUST still pass PDF validation. HTML-login, non-PDF, missing-header, or missing-EOF content MUST NOT validate.

#### Scenario: Trailing bytes are removed
- GIVEN bytes that start with `%PDF-` and contain trailing bytes after the last `%%EOF`
- WHEN the PDF is sanitized and verified
- THEN only bytes after the last EOF SHALL be removed
- AND the resulting PDF SHALL be valid

#### Scenario: Verification failure prevents success
- GIVEN HTML-login or non-PDF content
- WHEN sanitization and verification run
- THEN verification MUST fail
- AND the document MUST NOT be recorded as successfully downloaded

### Requirement: Evidence, documentation, and tests

The change MUST include pure tests for PB opt-in, header normalization, filename/inventory identity, idempotency, numeric dates, EOF sanitization, and verification failures. Tests MUST NOT automate login, captcha, OTP, or real portal access.

#### Scenario: Evidence covers the change
- GIVEN the feature is ready for review
- WHEN test and documentation artifacts are inspected
- THEN each required behavior SHALL have pure test coverage
- AND docs SHALL avoid credentials or personal banking data
