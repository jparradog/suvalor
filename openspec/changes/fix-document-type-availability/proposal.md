# Proposal: Fix Document Type Availability

## Intent

Fix GitHub issue #1: the portal selector exposes `CE`, `FB`, `NC`, `PB`, `RC`, but the client still defaults to/advertises legacy `CC`. Block unavailable types before Playwright while keeping state readable.

## Scope

### In Scope
- Split current portal types from legacy metadata.
- Remove `CC` from safe defaults and generated config.
- Reject explicit legacy requests (`CC`, including `RC,CC`) before browser startup.
- Update CLI help/errors, README, and site notes.
- Add pure pytest coverage.

### Out of Scope
- Login, CAPTCHA, OTP, credential, or portal automation changes.
- Live selector probing/runtime introspection.
- Migrating/deleting `_state`, downloads, or legacy folders.
- Making `FB`/`PB` default; they remain opt-in due known 504 behavior.

## Approach

Use a static availability/legacy split. Keep `CC` in `TipoDoc`/name metadata for compatibility, but add current-selector constants and make defaults/config produce only safe current types: `RC`, `NC`, `CE`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `suvalor/tipos.py` | Modified | Availability/legacy split; defaults. |
| `suvalor/config.py` | Modified | Template/default config excludes `CC`. |
| `suvalor/cli.py` | Modified | Validation, help, errors. |
| `suvalor/orquestador.py` | Protected | Receives only current valid types. |
| `tests/test_sync_args.py` | Modified | Strict TDD tests. |
| `README.md`, `docs/SITE_NOTES.md` | Modified | Current selector docs. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Existing configs contain `CC` | Medium | Clear pre-browser error. |
| Portal options drift again | Medium | Central constants and dated docs. |
| `FB`/`PB` become defaults by mistake | Low | Tests assert safe defaults only. |

## Rollback Plan

Revert the code/docs/test changes: restore prior defaults/template/help and remove availability validation. No data migration means rollback is code-only.

## Dependencies

- Issue #1 redacted selector evidence.
- `uv run pytest` pure test suite.

## Strict TDD Plan

1. RED: tests for default exclusion, explicit/mixed `CC` rejection, active type acceptance, and legacy state readability.
2. GREEN: minimal constants/config/CLI/docs changes.
3. REFACTOR: centralize messages; run full suite.

## Review Workload Forecast

Small single PR, expected under 400 changed lines; no chained PR needed.

## Success Criteria

- [ ] Defaults/generated config exclude `CC`.
- [ ] Explicit legacy `CC` fails before browser startup.
- [ ] Legacy state with `CC` remains readable.
- [ ] Docs match current selector/safety limits.
- [ ] `uv run pytest` passes.
