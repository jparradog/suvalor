# Proposal: Download Tesoreria Movements

## Intent

Add a staged opt-in manual-login CLI flow to download Tesoreria movements for explicit date ranges without leaking account data or increasing default portal load while the flow is fail-closed. Once the flow is complete and safe, the final product UX must integrate Tesoreria into `suvalor sync` so routine synchronization does not require a separate command.

## Scope

### In Scope
- `suvalor tesoreria --from YYYY-MM-DD --to YYYY-MM-DD --format pdf|xls|both [--account TEXT] [--tag SAFE] [--redownload]`.
- Authenticated Tesoreria flow after existing manual login; no credential, OTP, captcha, or keyboard automation.
- Deterministic `Tesoreria/YYYY/` storage, validation-based idempotency, strict pure-pytest TDD, and docs.

### Out of Scope
- Adding Tesoreria to default `sync` while Tesoreria remains incomplete/fail-closed.
- Printing/storing raw account labels or numbers in console, filenames, state, logs, or docs.
- Telemetry, new portal-load defaults, or agent-run portal execution.

## Approach

Reuse the current CLI/browser/session pattern. Require explicit dates, apply the 89-day safety model, open `/consultas/consultarMovimientoTesoreria.aspx`, optionally select account by substring without echoing its label, export PDF/XLS, then validate. The isolated `tesoreria` command is a staging/manual/debug surface; after selector evidence, validation, idempotency, and tests are complete, add Tesoreria to `suvalor sync` with explicit disable controls.

## CLI/User Flow

User runs `suvalor tesoreria ...`, completes manual login, and sees safe counts. `--tag` is the only account disambiguator written to filenames.

## Storage / Idempotency

Save chunks as `Tesoreria/YYYY/YYYY-MM-DD_YYYY-MM-DD_movimientos_tesoreria[_tag].{pdf,xls}`. Skip only valid existing files; replace invalid files unless `--redownload` forces replacement. No new state for v1.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `suvalor/cli.py`, `suvalor/orquestador.py` | Modified | Command, planning, authenticated flow, summary. |
| `suvalor/descargador.py`, `suvalor/verificacion.py` | Modified | Export helper and PDF/Excel/tabular validation. |
| `suvalor/tipos.py` | Modified | URL, output path, formats, selectors. |
| `tests/`, `README.md`, `docs/SITE_NOTES.md` | Modified | Pure tests and redacted docs. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Unknown date selectors | Medium | Confirm redacted evidence; use defensive selectors. |
| Account data leakage | Medium | Never print raw labels/numbers; require safe `--tag`. |
| Bad XLS/TSV accepted | Medium | Write negative login/error tests first. |

## Rollback Plan

Remove command, constants, orchestration, validation, tests, and docs. User-owned generated `Tesoreria/` files can be deleted manually outside the repo.

## Dependencies

- Existing manual login/session flow.
- Strict TDD: RED/GREEN/REFACTOR with `uv run pytest`.

## Forecast

Single PR expected; split if changed lines exceed 400 or generic download refactor grows beyond Tesoreria.

## Success Criteria

- [ ] Opt-in Tesoreria PDF/XLS downloads work for explicit dates.
- [ ] Completed safe Tesoreria flow is integrated into `suvalor sync` with explicit disable controls.
- [ ] Valid existing files skip; invalid files redownload.
- [ ] No raw account labels/numbers appear in output or filenames.
- [ ] Pure tests and `uv run pytest` pass.
