# Proposal: Support PB Opt-In

## Intent
Enable explicit `PB` (Papeletas de Bolsa) downloads without changing defaults. PB is accepted by CLI/type config, but grid parsing assumes RC/NC/CE columns and PDF validation does not sanitize trailing bytes after EOF.

## Problem
Issue #2 needs PB parser/date/PDF handling only: no FB, Tesoreria, Fondos, login automation, or new defaults.

## Scope

### In Scope
- PB header-aware parsing: `N°Papeleta` -> id, `Fecha Operacion` -> filename date.
- Numeric `DD/MM/YYYY` plus Spanish month date parsing.
- Generic PDF EOF sanitization before validation/storage.
- Pure pytest strict TDD; no real portal execution.

### Out of Scope
- FB, Tesoreria, Fondos, or new default types.
- Login, captcha, OTP, credential, or manual-login automation.
- Inventory JSON changes or metadata persistence.

## Approach
Keep downloading generic. Pass document type into extraction, add PB-only header mapping, preserve RC/NC/CE, and truncate valid-looking PDFs after the last `%%EOF` before validation.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `suvalor/pagina.py` | Modified | PB extraction. |
| `suvalor/orquestador.py` | Modified | Type-aware call. |
| `suvalor/parseo.py` | Modified | Numeric dates. |
| `suvalor/verificacion.py` | Modified | EOF sanitizer. |
| `tests/` | Modified | Pure coverage. |
| `docs/SITE_NOTES.md` | Modified | Redacted notes. |

## Strict TDD Plan
1. RED: failing pure tests for PB parsing, numeric dates, PB default exclusion/explicit opt-in, and EOF sanitization.
2. GREEN: minimal parser/date/sanitizer implementation.
3. REFACTOR: preserve state contracts; run `uv run pytest`.

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| PB header variants | Med | Normalize labels. |
| Permanent filename date | Med | Lock `Fecha Operacion`. |
| Sanitizer hides HTML/login | Low | Require PDF header and revalidate. |
| RC/NC/CE regression | Low | Keep legacy path/tests. |

## Rollback Plan
Revert touched `suvalor/`, `tests/`, and `docs/SITE_NOTES.md` files. PB stays non-default; no inventory migration.

## Dependencies
- `openspec/changes/support-pb-opt-in/exploration.md`.
- Redacted PB header evidence from issue #2.

## Review Workload Forecast
Expected diff: under 400 changed lines; single PR, no chained PR forecast.

## Success Criteria
- [ ] `PB` remains opt-in and absent from defaults.
- [ ] PB files use `YYYY-MM-DD_PB_<papeleta>.pdf` from `Fecha Operacion`.
- [ ] Numeric and Spanish month dates parse deterministically.
- [ ] Trailing bytes after last `%%EOF` are sanitized without accepting HTML/login failures.
- [ ] `uv run pytest` passes.
