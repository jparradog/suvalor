# Delta for Portal Download Diagnostics

## ADDED Requirements

### Requirement: FB Remains Explicit Opt-In

The system MUST keep `FB` excluded from default document type selection and SHALL process `FB` only when explicitly requested by the user.

#### Scenario: Default selection excludes FB
- GIVEN a run without explicit document types
- WHEN the document type list is built
- THEN `FB` SHALL NOT be included

#### Scenario: Explicit FB is allowed
- GIVEN the user explicitly requests `FB`
- WHEN downloads are planned
- THEN `FB` MAY be attempted under the same safety rules as other opt-in types

### Requirement: Portal 504 and HTML Error Classification

The system MUST classify popup HTTP 504 responses and downloaded HTML error pages, including CloudFront timeouts, as portal failures with normalized, sanitized reasons.

#### Scenario: Popup reports HTTP 504
- GIVEN a document opens through a popup request
- WHEN the popup response is HTTP 504
- THEN the failure reason SHALL identify a portal gateway timeout

#### Scenario: HTML is received instead of PDF
- GIVEN a download path saves HTML content
- WHEN the content indicates CloudFront or HTTP 504
- THEN the failure reason SHALL identify a portal gateway timeout

### Requirement: Invalid HTML Is Not a Successful PDF

The system MUST NOT retain HTML errors as successful PDFs and MUST NOT add failed downloads to inventory.

#### Scenario: HTML file has a PDF name
- GIVEN a downloaded `.pdf` file contains HTML
- WHEN verification runs
- THEN the file SHALL be invalid and removed
- AND no inventory entry SHALL be created

#### Scenario: Valid PDF still succeeds
- GIVEN a downloaded file is a valid PDF
- WHEN verification succeeds
- THEN normal success handling SHALL continue

### Requirement: Retries Remain Bounded

The system SHALL make at least one attempt and MUST NOT exceed configured `max(1, retry_doc)` attempts. The system MUST NOT retry indefinitely for portal failures.

#### Scenario: Retry limit is reached
- GIVEN `retry_doc` permits bounded attempts
- WHEN every attempt returns a portal failure
- THEN the final result SHALL be failed after that bound

#### Scenario: Later bounded retry succeeds
- GIVEN an earlier attempt returns a portal failure
- WHEN a later bounded attempt returns a valid PDF
- THEN the document SHALL be recorded as successful

### Requirement: Sanitized Failure Reporting and TSV Compatibility

The system MUST surface normalized, sanitized failure reasons in CLI summaries, logs, and `ResumenCorrida.detalle_fallidos` or equivalent in-memory run summary. `_Fallidos/fallos.tsv` MUST preserve its existing five-column schema and MUST NOT store raw URLs, query strings, JWTs, tokens, session identifiers, or normalized reasons. TSV failure recording MAY still record the failed row using the existing schema.

#### Scenario: Runtime summary reports a safe reason
- GIVEN a portal failure includes a URL with `jwt=` or query tokens
- WHEN the failure is summarized or logged
- THEN sensitive values MUST be absent
- AND a normalized reason SHALL be visible in the runtime summary

#### Scenario: TSV records only legacy fields
- GIVEN a failed document is recorded
- WHEN `_Fallidos/fallos.tsv` is updated
- THEN the existing columns SHALL be preserved
- AND no reason column or overloaded reason value SHALL be written

### Requirement: Documentation and Pure Test Coverage

The change MUST update project documentation about FB/504 portal behavior and MUST include pure pytest coverage for opt-in behavior, 504 classification, invalid HTML/PDF handling, bounded retries, sanitized reporting, and TSV compatibility. Tests MUST NOT use network, Playwright, or portal access.

#### Scenario: Tests validate safety behavior
- GIVEN the test suite runs with `uv run pytest`
- WHEN the diagnostics change is present
- THEN pure tests SHALL cover the specified safety cases

#### Scenario: Documentation records portal finding
- GIVEN the portal behavior is known
- WHEN documentation is updated
- THEN it SHALL state that `FB` remains opt-in and 504 reliability is not fixed
