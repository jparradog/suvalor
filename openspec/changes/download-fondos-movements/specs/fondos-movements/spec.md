# Delta for Fondos Movements

## ADDED Requirements

### Requirement: Staged Fondos command scope
The system MUST expose Fondos downloads through `suvalor fondos --from YYYY-MM-DD --to YYYY-MM-DD [--tag SAFE] [--redownload]` while page automation is being validated. During this staging phase, default `sync` MUST NOT include Fondos. v1 MUST use the portal default account and fund `TODOS`; raw `--account` or `--fund` selectors MUST NOT exist.

#### Scenario: Explicit command uses default scope
- GIVEN a user requests `fondos` with valid `--from` and `--to`
- WHEN the command starts
- THEN the run targets the default portal account and fund `TODOS`
- AND no raw account or fund selector is accepted

### Requirement: Manual login boundary
The system MUST preserve manual login. It MUST NOT automate credentials, OTP, captcha, reCAPTCHA, or virtual keyboard entry.

#### Scenario: Authentication remains user-controlled
- GIVEN the browser is opened for Fondos
- WHEN authentication is required
- THEN the system waits for manual user completion
- AND it does not submit secret or challenge inputs

### Requirement: Privacy-safe destination layout
The system MUST store successful reports under `SUVALOR_HOME/Fondos/YYYY/` using only date range, fixed Fondos movement text, and optional safe tag in the filename. Paths, logs, state, and docs MUST NOT include portal account labels, fund labels, numbers, or selectors.

#### Scenario: Safe tagged filename
- GIVEN dates `2026-01-01` to `2026-01-31` and tag `safe-tag`
- WHEN a valid report is saved
- THEN the destination is under `Fondos/2026/`
- AND the filename contains dates and `safe-tag` only

### Requirement: Report validation
The system MUST accept only valid report artifacts: OLE XLS magic, XLSX zip with workbook structures, HTML containing a report table, or CSV/TSV-like text with a header, at least one data row, consistent delimiter and column count, and no login/error markers. It MUST reject login/error pages, malformed/headerless text, wrong magic, and malformed archives.

#### Scenario: Invalid report is rejected
- GIVEN a downloaded artifact contains a login page or wrong magic bytes
- WHEN Fondos validation runs
- THEN the artifact is rejected
- AND it is not persisted as a successful report

### Requirement: No-record semantics
The system MUST report no-record portal responses as `sin_datos`. It MUST NOT create a fake file or permanent no-data inventory entry.

#### Scenario: No movements found
- GIVEN the portal returns the no-record message for a date range
- WHEN the range is processed
- THEN the result is `sin_datos`
- AND no output file or no-data state entry is created

### Requirement: Idempotency and redownload
The system MUST skip an existing valid destination unless `--redownload` is provided. It SHOULD replace invalid existing files only after a fresh downloaded report validates successfully.

#### Scenario: Existing valid report
- GIVEN a valid destination file already exists
- WHEN the same date range is requested without `--redownload`
- THEN the range is skipped
- AND the existing file remains unchanged

### Requirement: Failure atomicity
The system MUST keep prior valid files intact when download, validation, or move fails. It MUST NOT leave partial files at final destinations.

#### Scenario: Replacement validation fails
- GIVEN a prior valid destination exists
- WHEN `--redownload` receives an invalid artifact
- THEN the prior file remains intact
- AND the failed artifact is not promoted to final path

### Requirement: Final sync integration
Once Fondos page automation is fully evidence-gated, validated, and no longer fail-closed, the system MUST integrate Fondos into `suvalor sync` so users do not need to run a separate operational command for routine synchronization. The isolated `fondos` command MAY remain as a manual/debug entry point, but it MUST NOT be the only routine synchronization path after completion.

#### Scenario: Completed Fondos participates in sync
- GIVEN Fondos automation has selector evidence, validation, no-record handling, idempotency, and tests
- WHEN a user runs the normal `suvalor sync`
- THEN Fondos SHALL run as part of the sync plan unless disabled by explicit config or flag
- AND the isolated `fondos` command remains optional

### Requirement: Pure tests and privacy documentation
Automated tests MUST be pure: no network, no real Playwright, no real portal commands, and no filesystem outside temporary test paths. Documentation SHALL describe staged opt-in usage, final `sync` integration intent, manual-login limits, default account plus `TODOS` scope, validation, idempotency, `sin_datos`, and privacy constraints.

#### Scenario: Automated coverage stays offline
- GIVEN the test suite covers Fondos behavior
- WHEN tests execute
- THEN they use fakes and temporary paths only
- AND they do not run `sync`, `fondos`, `descargar`, or `cartera`

## MODIFIED Requirements

None.

## REMOVED Requirements

None.
