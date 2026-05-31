# Tasks: Download Fondos Movements

## Phase 1: RED Tests / Contract Lock

- [ ] 1.1 Create `tests/test_fondos_cli.py` covering `suvalor fondos --from --to`, invalid/inverted dates, safe `--tag`, help text without `--account`/`--fund`, and no browser launch on validation failure.
- [ ] 1.2 Extend CLI tests so default `suvalor sync` never calls Fondos orchestration and unexpected raw selector options fail before portal interaction.
- [ ] 1.3 Create `tests/test_fondos_destino.py` for `Fondos/YYYY/YYYY-MM-DD_YYYY-MM-DD_movimientos_fondos[_tag].xls`, safe tag disambiguation, valid skip, invalid redownload, and `--redownload` replacement.
- [ ] 1.4 Extend `tests/test_verificacion.py` for Fondos validation: accept OLE XLS, XLSX, HTML table, CSV/TSV; reject login/error HTML, malformed text, and wrong magic bytes.
- [ ] 1.5 Create `tests/test_fondos_orquestador.py` with fakes for 89-day chunking, `sin_datos` with no file/state entry, validation failure atomicity, move failure atomicity, and redacted errors.
- [ ] 1.6 Add docs/privacy tests or assertions for manual login, opt-in scope, no raw account/fund selectors, tag-as-filename-only, and no real portal commands in automated tests.

## Phase 2: GREEN Foundation

- [ ] 2.1 Modify `suvalor/tipos.py` with `FONDOS_DIR`, `FONDOS_URL`, and fail-closed constants only for documented default-flow selectors.
- [ ] 2.2 Modify `suvalor/verificacion.py` with a Fondos validator for accepted Excel/tabular formats and explicit login/error rejection.
- [ ] 2.3 Modify `suvalor/descargador.py` with a reusable report `expect_download` click helper that has no account/fund selector responsibility.
- [ ] 2.4 Modify `suvalor/cli.py` to expose only `fondos --from --to [--tag SAFE] [--redownload]`; treat `--tag` only as filename disambiguation and reject invalid dates/tags before browser startup.

## Phase 3: GREEN Flow / Persistence

- [ ] 3.1 Modify `suvalor/pagina.py` with Fondos helpers gated by redacted `docs/SITE_NOTES.md` evidence for default-flow URL, date inputs, export action, and no-record marker.
- [ ] 3.2 Keep page automation disabled/fail-closed until all selector evidence exists; do not add raw or alias account/fund selection in v1.
- [ ] 3.3 Modify `suvalor/orquestador.py` with `OpcionesFondos`, `ResumenFondos`, chunk loop, `skip`/`nuevo`/`sin_datos`/`fail`, retries, redaction, and atomic temp-to-final persistence.

## Phase 4: Docs / Refactor / Verification

- [ ] 4.1 Update `README.md` with safe Fondos usage, manual-login boundary, default account plus `TODOS` v1 scope, validation, idempotency, and `sin_datos`.
- [ ] 4.2 Update `docs/SITE_NOTES.md` with verified redacted evidence or explicitly state Fondos page automation remains disabled; non-default account/fund selection is deferred pending a future privacy-safe alias design.
- [ ] 4.3 Refactor only after tests pass, preserving Spanish identifiers, `pathlib.Path`, no telemetry, and no persistent Fondos inventory.
- [ ] 4.4 Run `uv run pytest`; never run real portal commands (`sync`, `fondos`, `descargar`, `cartera`) during automated agent verification.

## Forecast

Single PR if under 400 changed lines; split validation/CLI/orchestration/docs if review budget is exceeded.
