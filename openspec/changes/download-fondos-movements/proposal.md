# Proposal: Download Fondos Movements

## Intent

Add a staged opt-in manual-login CLI flow for Fondos movement exports over explicit date ranges, without automating credentials/captcha/OTP, exposing account/fund labels, adding telemetry, or increasing default `sync` load while the flow is fail-closed. Once the flow is complete and safe, the final product UX must integrate Fondos into `suvalor sync` so routine synchronization does not require a separate command.

## Scope

### In Scope
- `suvalor fondos --from YYYY-MM-DD --to YYYY-MM-DD [--tag SAFE] [--redownload]`.
- Default portal account and default fund `TODOS` only.
- `--tag` as a filename disambiguator only; not a selector.
- Deterministic `Fondos/YYYY/` outputs, no-record handling, validation-based idempotency, docs, strict pure-pytest TDD.

### Out of Scope
- Non-default account/fund selection in v1 unless future privacy-safe aliases are designed.
- Raw account/fund labels, numbers, or selector strings on CLI, shell history, process listings, console, filenames, state, logs, or docs.
- Default `sync` inclusion while Fondos remains incomplete/fail-closed, agent-run real portal commands, telemetry, or credential/session automation.

## Approach

Reuse the CLI/browser/session pattern. Require explicit dates, chunk by 89 days, open `/consultas/InformeFondos.aspx`, fill `txtFechaInicial`/`txtFechaFinal`, keep default account and `ddlFondo=TODOS`, export via `btnMovExcel`, then validate a conservative Excel/tabular artifact. The isolated `fondos` command is a staging/manual/debug surface; after selector evidence, validation, no-record handling, and tests are complete, add Fondos to `suvalor sync` with explicit disable controls.

## Storage / Idempotency / No Records

Save `Fondos/YYYY/YYYY-MM-DD_YYYY-MM-DD_movimientos_fondos[_tag].xls`. Skip only valid existing files; replace invalid files unless `--redownload` forces replacement. `No se encontraron registros` returns `sin_datos` without fake files or permanent no-data inventory.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `suvalor/cli.py`, `suvalor/orquestador.py` | Modified | Command, planning, default-only flow, summary. |
| `suvalor/descargador.py`, `suvalor/verificacion.py` | Modified | Download helper; Excel/tabular validation. |
| `suvalor/tipos.py`, `suvalor/rangos.py` | Modified | URL, selectors, outputs, chunks. |
| `tests/`, `README.md`, `docs/SITE_NOTES.md` | Modified | Pure tests and redacted docs. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Export format unconfirmed | Medium | Accept Excel/tabular variants; reject login/error HTML. |
| Future selector leakage | Medium | Defer selection until privacy-safe aliases exist. |
| Sensitive data leakage | Low | No raw selector CLI values; safe tags only. |

## Rollback Plan

Remove the command, constants, orchestration, validation, tests, and docs. User-owned `Fondos/` files can be deleted manually outside the repo.

## Dependencies

- Existing manual login/session flow.
- Strict TDD with `uv run pytest`.

## Success Criteria

- [ ] Opt-in Fondos export works for explicit dates using default account and `TODOS`.
- [ ] Completed safe Fondos flow is integrated into `suvalor sync` with explicit disable controls.
- [ ] CLI exposes no raw account/fund selector values.
- [ ] Existing valid files skip; invalid files redownload.
- [ ] No-record responses return `sin_datos` without fake files.
- [ ] Pure tests and `uv run pytest` pass.
