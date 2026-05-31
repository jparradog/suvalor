# Tasks: Investigate ReteFuente Certificate

## Forecast
Docs/test-only investigation guardrails. Expected diff: <150 changed lines, 1 PR, no chained PR needed. No package code, state migration, generated data, or real portal commands.

## Phase 1: RED Docs Checks / Guardrails

- [ ] 1.1 Create pure pytest docs checks in `tests/test_site_notes_retefuente.py` that fail until `docs/SITE_NOTES.md` marks ReteFuente unsupported/investigation-only.
- [ ] 1.2 In `tests/test_site_notes_retefuente.py`, assert `docs/SITE_NOTES.md` records `operaciones/reteFuente.aspx`, `ddlAnioRetencion`, `btnDescargarPDF`, and the observed no-download/no-popup result.
- [ ] 1.3 In `tests/test_site_notes_retefuente.py`, assert future-evidence requirements include redacted selectors, DevTools/network response metadata, and PDF-byte verification (`%PDF-`/EOF/size) OR a classified no-certificate state.
- [ ] 1.4 In `tests/test_site_notes_retefuente.py`, assert future-evidence requirements document session-expired/login-redirect behavior without reauthentication automation.
- [ ] 1.5 In `tests/test_site_notes_retefuente.py`, assert privacy rules exclude client IDs, COYDs, account numbers, names, screenshots, raw personal paths, credentials, OTP, captcha, and virtual-keyboard data.
- [ ] 1.6 In `tests/test_site_notes_retefuente.py`, assert GMF is explicitly out of scope because evidence shows redirect/unavailable behavior, not a supported certificate flow.

## Phase 2: GREEN Documentation

- [ ] 2.1 Add a `ReteFuente certificate investigation` section to `docs/SITE_NOTES.md` stating the feature is disabled and unsupported.
- [ ] 2.2 Document the concrete evidence record in `docs/SITE_NOTES.md`: endpoint `operaciones/reteFuente.aspx`, controls `ddlAnioRetencion`/`btnDescargarPDF`, and no-download/no-popup probe outcome.
- [ ] 2.3 Document the future evidence gate in `docs/SITE_NOTES.md`: selectors, request URL/method/status/content-type/content-disposition/size, redirect chain, and PDF bytes OR no-certificate classification.
- [ ] 2.4 Document session-expired behavior in `docs/SITE_NOTES.md`: login/expired redirect is a distinct outcome and must not trigger credential, OTP, captcha, or virtual-keyboard automation.
- [ ] 2.5 Document redaction/privacy rules in `docs/SITE_NOTES.md` for all future ReteFuente evidence and fixtures.
- [ ] 2.6 Document GMF as a non-goal in `docs/SITE_NOTES.md`, citing redirect/unavailable evidence and no implementation scope.

## Phase 3: Verification / Scope Control

- [ ] 3.1 Refactor `tests/test_site_notes_retefuente.py` only for readable shared fixtures/helpers; keep checks documentation-only.
- [ ] 3.2 Run `uv run pytest tests/test_site_notes_retefuente.py -v` and confirm docs checks pass after `docs/SITE_NOTES.md` changes.
- [ ] 3.3 Run `uv run pytest` and confirm the pure suite passes without network, Playwright, user profile, or real portal commands.
- [ ] 3.4 Verify `git diff --name-only` changes only `docs/SITE_NOTES.md`, `tests/test_site_notes_retefuente.py`, and SDD artifacts; no `suvalor/` package files.
