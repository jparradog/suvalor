status: completed
executive_summary: >
  Explored GitHub issue #5 for `download-fondos-movements`. The repo already has safe manual-login Playwright flows for documents, extractos, and cartera, but Fondos movements are only listed as an unimplemented endpoint in `docs/SITE_NOTES.md`. Recommended scope is an opt-in `fondos` command that reuses the authenticated-page pattern, keeps default portal selectors unless explicitly requested, writes deterministic `Fondos/YYYY/` Excel outputs, treats “No se encontraron registros” as `sin_datos`, and adds conservative pure validation for Excel/tabular exports. Do not add Fondos to default `sync` in the first change.
skill_resolution: none

## Exploration: download-fondos-movements

### Current State
- `suvalor/cli.py` exposes Typer commands for `sync`, `descargar`, `extractos`, `cartera`, `inventario`, `reset`, `recuperar-fallidos`, `config`, and `timings`. There is no `fondos` command today.
- Runtime commands open Chrome via `abrir_navegador()`, require `login_manual()`, then call orchestration functions that assume an authenticated `page`. This is the correct boundary for Fondos; no credential, captcha, OTP, keyboard, or login automation is needed.
- `suvalor/orquestador.py` has reusable authenticated flows for documents, extractos, and cartera. `sincronizar_cartera()` is the closest pattern: navigate to a report page, optionally select a dropdown, click an Excel export button, capture `expect_download`, save to a deterministic destination, then validate.
- `suvalor/descargador.py` has document-specific PDF popup handling and generic polling helpers, but no generic report export helper for arbitrary Excel buttons.
- `suvalor/verificacion.py` validates PDFs and cartera `.xls` files that are actually HTML tables. It does not yet validate binary `.xls`, OOXML `.xlsx`, TSV/CSV-like exports, or no-record tabular reports.
- `suvalor/tipos.py` centralizes URLs, output directories, temporary filenames, and ASP.NET IDs. Fondos constants are absent.
- `docs/SITE_NOTES.md` lists `/consultas/InformeFondos.aspx` as “No explorado”. Issue #5 adds redacted portal evidence: the flow exists, uses `txtFechaInicial` / `txtFechaFinal`, defaults `ddlFondo` to `TODOS`, exports through `btnMovExcel`, and can show “No se encontraron registros”. The prompt adds that the default probe returned no records.
- Existing tests are pure pytest tests for state, extractos inventory, parsing, date ranges, timings, verification, and CLI help/planning. No tests call Playwright or the real portal. Strict TDD is active with `uv run pytest`.

### Affected Areas
- `suvalor/tipos.py` — add Fondos URL, output directory, temporary/export filename constants, and ASP.NET IDs/selectors (`InformeFondos.aspx`, `txtFechaInicial`, `txtFechaFinal`, `ddlFondo`, `btnMovExcel`; account selector only if present/confirmed).
- `suvalor/cli.py` — add opt-in `fondos` subcommand, pure date/selector argument validation, and help text; keep it out of default `sync` initially.
- `suvalor/orquestador.py` — add `ResumenFondos` and `sincronizar_fondos(page, ...)` that assumes authenticated session, navigates robustly, fills filters, handles no-record dialogs, captures the Excel download, validates, and returns counts.
- `suvalor/descargador.py` — preferably add a small generic click-to-download helper for report buttons, rather than coupling Fondos to document-grid postback logic.
- `suvalor/verificacion.py` — add a conservative Excel/tabular validator that accepts HTML table `.xls`, TSV/CSV-like text, OLE `.xls`, and OOXML zip when appropriate, while rejecting login/error HTML.
- `suvalor/rangos.py` — reuse `partir_en_rangos()` / `MAX_DIAS_POR_RANGO` for conservative chunking; do not increase the 89-day portal safety limit.
- `tests/test_sync_args.py` or `tests/test_fondos_args.py` — cover CLI help, required dates, date validation, selector/tag parsing, and short-circuit behavior without Playwright.
- `tests/test_verificacion.py` — cover valid HTML-XLS, TSV-like export, OLE/OOXML signatures if accepted, login HTML rejection, unknown format rejection, and explicit no-record content if the portal returns a file instead of an alert.
- `tests/test_rangos.py` or a new pure helper test — cover Fondos path planning/chunking and deterministic output names.
- `README.md` — document the new opt-in command, output layout, selector privacy, manual-login boundary, no default sync inclusion, and no real portal tests.
- `docs/SITE_NOTES.md` — update with redacted, verified Fondos selectors and observed export format after implementation/manual confirmation.

### Approaches
1. **Minimal issue-shaped command** — Add `suvalor fondos --from YYYY-MM-DD --to YYYY-MM-DD`, leave the portal-selected account untouched, leave `ddlFondo` at its default `TODOS`, click `btnMovExcel`, and save one or more chunked `.xls` files under `Fondos/YYYY/`.
   - Pros: Smallest surface area; lowest privacy risk; matches issue #5; easy to keep out of default `sync`; easiest to test with pure helpers.
   - Cons: Users with multiple accounts/funds cannot disambiguate outputs except by separate manual portal state; same date range can collide across selector choices; may need a later PR for selector support.
   - Effort: Medium

2. **Opt-in command with privacy-safe selectors** — Add `suvalor fondos --from YYYY-MM-DD --to YYYY-MM-DD [--account TEXT] [--fund TEXT] [--tag SAFE] [--redownload]`. Defaults remain unchanged: do not change account and keep `ddlFondo=TODOS`. If selectors are passed, select by substring but do not print raw account/fund labels or include them in filenames; use `--tag` for safe filename disambiguation.
   - Pros: Still bounded and opt-in; handles account/fund selector privacy explicitly; avoids leaking account numbers or fund names in logs/paths; `--tag` solves idempotency collisions without storing sensitive labels.
   - Cons: More tests and selector code; account selector on this page is not documented yet; `--tag` requires user discipline for multiple selector combinations.
   - Effort: Medium

3. **Add Fondos as disabled `sync --with-fondos` stage** — Add a sync stage that runs in the existing single browser session only when explicitly enabled.
   - Pros: One manual login for users who routinely download all reports; consistent with `sync` summary.
   - Cons: Larger CLI planning and summary changes; date semantics inside `sync` become less clear; increased review burden and portal load risk for the first PR.
   - Effort: Medium/High

4. **Generic report-download framework** — Abstract cartera, tesoreria, and fondos into report descriptors with shared selector/download/validation primitives.
   - Pros: Best long-term direction if more report endpoints are added.
   - Cons: Refactors working flows; higher regression risk; likely exceeds the issue’s scope and the 400-line review budget once tests/docs are included.
   - Effort: High

### Recommendation
Use **Approach 2**, but keep it strictly opt-in and conservative.

Design guidance for the proposal/spec:
- CLI shape: `uv run suvalor fondos --from YYYY-MM-DD --to YYYY-MM-DD [--account TEXT] [--fund TEXT] [--tag SAFE] [--redownload]`.
- Do not add Fondos to default `sync` in the first change. A later `sync --with-fondos` can be proposed after selectors and validation are stable.
- Require explicit `--from` and `--to`; no default historic/backfill behavior for Fondos. For ranges longer than 89 inclusive days, reuse existing chunking instead of increasing portal range size.
- Destination layout: `Fondos/YYYY/YYYY-MM-DD_YYYY-MM-DD_movimientos_fondos.xls`, using the chunk start year. If `--tag SAFE` is supplied, write `YYYY-MM-DD_YYYY-MM-DD_movimientos_fondos_<tag>.xls`. Validate tag characters with a pure helper and reject path separators.
- Selector privacy: default to the portal’s current/preselected account and `ddlFondo=TODOS`. If `--account` or `--fund` is used, select by substring but do not log raw selected labels and do not embed account numbers/fund labels in filenames. Console output should say only `Cuenta seleccionada` / `Fondo seleccionado`.
- Idempotency: skip a target only when it already exists and passes Fondos Excel validation. If the file exists but fails validation, delete/redownload unless `--redownload` explicitly forces a fresh download. For no-record alerts, return `sin_datos` without creating a fake data file; do not persist a no-data inventory in v1, so later late-arriving movements are not hidden.
- No-record handling: register a Playwright `dialog` handler around the export click. If the message contains “No se encontraron registros”, accept/dismiss it and return a `sin_datos` result, not an exception. Also support the edge case where the server exports a small tabular no-record file by detecting an explicit no-record marker separately from successful data.
- Validation: add a new type such as `excel_tabular` rather than weakening `xls_html`. It should reject login/session HTML using the existing hints, accept HTML with `<table`, accept TSV/CSV-like text with multiple rows or known headers, and accept binary OLE `.xls` / OOXML zip signatures with reasonable size checks. Avoid adding heavy dependencies like pandas/openpyxl/xlrd just for validation.
- Tests: follow strict TDD. Start with failing pure tests for CLI help/arguments, path/tag planning, 89-day chunking, idempotent skip decisions, no-record result mapping, and tabular validation; then implement minimally and run `uv run pytest`.
- Docs: update README with command examples and privacy warnings; update `docs/SITE_NOTES.md` with exact redacted selectors/export format after a human confirms them. Agents should not run real portal commands.

### Risks
- Exact Fondos account selector behavior is not documented; implementation may need defensive selectors or manual redacted confirmation before coding selector support.
- The portal probe returned no records, so the real export format for non-empty data is not yet proven. Validation must be broad enough for Excel variants but narrow enough to reject login/error pages.
- Existing `es_xls_html_valido()` decodes bytes as UTF-8 only; ISO-8859-1/CP1252 TSV or HTML may require best-effort multi-encoding heuristics.
- Same date range with different account/fund selectors can collide unless users provide a safe `--tag`.
- Treating no-data as permanently idempotent would be risky because records may appear later; avoid no-data inventory in v1.
- Adding Fondos to `sync` or refactoring all report downloads now could exceed the review budget and increase portal-load risk.

### Ready for Proposal
Yes — propose a bounded opt-in `fondos` command with privacy-safe optional selectors, deterministic `Fondos/YYYY/` outputs, conservative Excel/tabular validation, and explicit no-record handling. Tell the user that implementation should be strict TDD with pure tests first and no real portal execution by agents.

artifacts:
  - openspec/changes/download-fondos-movements/exploration.md
next_recommended: Create proposal/spec/design/tasks for `download-fondos-movements`, locking the CLI shape, selector privacy rules, 89-day chunking, no-record semantics, and Excel/tabular validation contract.
risks:
  - Non-empty Fondos export format is unconfirmed because the default portal probe returned no records.
  - Account/fund selector handling must avoid logging or persisting sensitive labels.
  - Validation must not accept login/error HTML masquerading as `.xls`.
