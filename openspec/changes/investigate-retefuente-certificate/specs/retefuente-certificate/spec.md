# Delta for ReteFuente Certificate

## ADDED Requirements

### Requirement: Investigation-Only Scope

ReteFuente certificate support MUST remain investigation-only, disabled, and unsupported. The system MUST NOT expose a CLI command, feature flag, default sync path, or download workflow until a later approved evidence-gated change.

#### Scenario: Existing flows do not include ReteFuente

- GIVEN a user runs any existing Suvalor command
- WHEN sync, download, or cartera flows are evaluated
- THEN no ReteFuente endpoint is visited
- AND no ReteFuente files or state are created

#### Scenario: Premature automation is blocked

- GIVEN future work proposes ReteFuente automation without approved evidence
- WHEN the change is reviewed
- THEN it MUST be rejected as out of scope

### Requirement: Manual Login Boundary

The system MUST preserve manual authentication. It MUST NOT automate credentials, OTP, reCAPTCHA, virtual keyboards, or session recovery for ReteFuente.

#### Scenario: Session expires during investigation

- GIVEN the authenticated session expires while observing ReteFuente
- WHEN the portal redirects to login or an expired-session page
- THEN the outcome MUST be recorded as session-expired
- AND no reauthentication automation is attempted

### Requirement: Evidence Gate Before Automation

Future ReteFuente automation SHALL require approved, redacted evidence: endpoint and selectors, network response metadata, content type and status, PDF-byte verification OR classified no-certificate state, and session-expired behavior.

#### Scenario: PDF evidence is sufficient

- GIVEN redacted network evidence shows a successful certificate response
- WHEN the response has PDF content type, `%PDF-` header, EOF marker, and plausible size
- THEN future automation MAY be proposed in a separate change

#### Scenario: No-certificate evidence is classified

- GIVEN the portal returns a non-PDF response for a selected year
- WHEN redacted evidence classifies it as no-certificate rather than failure
- THEN future behavior MUST preserve that distinct state

### Requirement: SITE_NOTES Documentation

`docs/SITE_NOTES.md` MUST document `operaciones/reteFuente.aspx`, `ddlAnioRetencion`, `btnDescargarPDF`, the no-download/no-popup observation, redaction rules, required future evidence, and GMF as a non-goal.

#### Scenario: Documentation records known observations

- GIVEN this investigation change is applied
- WHEN `docs/SITE_NOTES.md` is reviewed
- THEN it contains the endpoint, controls, probe result, evidence gate, privacy rules, and GMF non-goal

### Requirement: Pure Privacy-Preserving Future Tests

Future tests SHALL be pure and privacy-preserving. They MUST NOT require network, Playwright, authenticated sessions, user data, screenshots, raw portal artifacts, or filesystem access outside test-controlled paths.

#### Scenario: Future tests avoid sensitive evidence

- GIVEN tests are added for ReteFuente behavior
- WHEN fixtures or assertions are reviewed
- THEN they contain only redacted or synthetic data
- AND they run without contacting the portal

### Requirement: Explicit Non-Goals

This change SHALL NOT add GMF support, runtime code, data migrations, telemetry, real portal commands, or any workflow that downloads ReteFuente certificates.

#### Scenario: Scope remains documentation-only

- GIVEN the change diff is reviewed
- WHEN package files or runtime commands are inspected
- THEN no ReteFuente implementation is present

## MODIFIED Requirements

No existing requirements are modified.

## REMOVED Requirements

No existing requirements are removed.
