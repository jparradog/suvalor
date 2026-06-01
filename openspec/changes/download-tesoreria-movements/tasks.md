# Tasks: Download Tesoreria Movements

## Phase 1: RED Contract Tests

- [x] 1.1 Create `tests/test_tesoreria_cli.py` RED: `tesoreria --from --to --format pdf|xls|both` parses, bad dates/format fail, and default `sync` excludes Tesoreria.
- [ ] 1.2 Add RED tests in `tests/test_tesoreria_cli.py`: `--account` without safe non-empty canonical `--tag` fails before browser; empty/same sanitized tags are rejected or collision-guarded.
- [x] 1.3 Create `tests/test_tesoreria_plan.py` RED: 120-day range becomes chunks <=89 days through Tesoreria CLI/planning path; 89-day boundary stays single chunk.
- [ ] 1.4 Create `tests/test_tesoreria_destinos.py` RED: final paths use `Tesoreria/YYYY/...[_tag].{pdf,xls}`, never raw account text, skip valid finals, replace invalid finals only.
- [x] 1.5 Extend `tests/test_verificacion.py` RED: accept OLE XLS, XLSX workbook ZIP, HTML table row/cell, and CSV/TSV text with required delimiter/header/token constraints; reject empty, login/error HTML, headerless text.
- [x] 1.6 Create `tests/test_tesoreria_atomicidad.py` RED: `--redownload --format both` PDF success + XLS validation failure leaves previous valid XLS final untouched and deletes failed candidate.
- [ ] 1.7 Add docs RED check in `tests/test_tesoreria_docs.py`: `README.md` documents opt-in/manual login/safe tags/privacy and contains no raw sample account data.

## Phase 2: GREEN Pure Implementation

- [x] 2.1 Modify `suvalor/cli.py`: add `tesoreria` Typer command with pre-browser validation and no Tesoreria work in default `sync`.
- [x] 2.2 Modify `suvalor/rangos.py` or a pure helper: plan explicit Tesoreria date chunks using `MAX_DIAS_POR_RANGO == 89`.
- [ ] 2.3 Modify `suvalor/tipos.py`: add safe constants/formats/temp naming and destination builder; enforce sanitized tag/collision rules before path creation.
- [x] 2.4 Modify `suvalor/verificacion.py`: implement `es_tabular_tesoreria_valido` and PDF/XLS dispatcher with exact structures from the spec.
- [ ] 2.5 Modify `suvalor/descargador.py`: download each format to candidate temp, validate, then atomic `replace()` final; never delete prior valid finals on failure.
- [x] 2.6 Modify `suvalor/orquestador.py`: add `ResumenTesoreria` and pure/integration-lite flow hooks; summaries expose counts only, not account labels.

## Phase 3: Selector Evidence Gate and Automation

- [ ] 3.1 Before page automation, update `docs/SITE_NOTES.md` or redacted fixtures with Tesoreria ASP.NET URL and date/account/PDF/Excel control IDs/selectors; if missing, stop implementation.
- [ ] 3.2 Only after 3.1, modify `suvalor/pagina.py`/`suvalor/descargador.py` to navigate Tesoreria, fill dates, optionally select account without echoing labels, and export PDF/XLS.
- [x] 3.3 Add pure integration-lite tests in `tests/test_tesoreria_orquestador.py` using monkeypatches only; no network, Playwright, or portal access.

## Phase 4: Sync Integration / Docs / Verification

- [ ] 4.1 After page automation is evidence-gated, idempotent, and no longer fail-closed, integrate Tesoreria into `suvalor sync` so routine synchronization does not require running `suvalor tesoreria` separately.
- [ ] 4.2 Add explicit config/CLI disable controls for Tesoreria in `sync` (for example `--no-tesoreria` and config default), while keeping the isolated command as an optional manual/debug entry point.
- [ ] 4.3 Document/test conservative empty/no-record behavior before `sync` integration: use a redacted no-record marker if available, otherwise fail export errors without creating fake success files.
- [ ] 4.4 Update `README.md` with `suvalor tesoreria` examples, final `sync` integration behavior, staged opt-in scope, manual login, `--tag`, `--redownload`, and privacy notes.
- [ ] 4.5 Run `uv run pytest`; record RED/GREEN/REFACTOR evidence and fix only via strict TDD.
- [ ] 4.6 Review `git diff --stat`; if forecast exceeds 400 changed lines, stop and split/chained-PR before implementation review.
