status: completed
executive_summary: >
  Explored GitHub issue #4 for `download-tesoreria-movements`. The repo already has safe manual-login Playwright flows for documents, extractos, and cartera, but Tesoreria is only documented as an unimplemented endpoint. Recommended scope is an opt-in `tesoreria` command plus a reusable authenticated-page function, deterministic `Tesoreria/YYYY/` outputs, file-existence validation for idempotency, and conservative PDF/Excel-or-TSV validation. Do not add it to default `sync` initially.
skill_resolution: none

## Exploration: download-tesoreria-movements

### Current State
- `suvalor/cli.py` exposes Typer commands for `sync`, `descargar`, `extractos`, `cartera`, `inventario`, `reset`, `recuperar-fallidos`, `config`, and `timings`. There is no `tesoreria` command today.
- Runtime commands open Chrome via `abrir_navegador()`, require `login_manual()`, then call reusable orchestration functions that assume an authenticated `page`. This is the right boundary for Tesoreria; no credential, captcha, OTP, or login automation is needed.
- `suvalor/orquestador.py` has reusable functions for authenticated document, extract, and cartera flows. `sincronizar_cartera()` is closest structurally: navigate to a report page, optionally select account, click an export button, `expect_download`, save to a deterministic destination, then validate.
- `suvalor/descargador.py` contains generic polling/download utilities and a document-specific popup fallback for inline PDF viewer behavior. Tesoreria PDF may need a generalized click/download helper rather than reusing the document-grid `Select$N` helper directly.
- `suvalor/verificacion.py` validates PDFs and the cartera `.xls` that is actually HTML. It does not currently validate TSV-like tabular exports or binary Excel signatures.
- `suvalor/tipos.py` centralizes base data paths, output dirs, endpoint URLs, temporary filenames, and ASP.NET IDs. Tesoreria constants are absent.
- `docs/SITE_NOTES.md` documents the Tesoreria endpoint `/consultas/consultarMovimientoTesoreria.aspx`, date fields, account selector, and buttons `btnMovTesoreriaPDF` / `btnMovTesoreriaExcel`, but exact date input IDs are not fully captured beyond `FechaInicial/FechaFinal` naming.
- Existing tests are pure pytest tests for state, extractos inventory, parsing, rangos, timings, verification, and CLI help/planning. `conftest.py` isolates `SUVALOR_HOME` in a temporary directory. No tests call Playwright or the real portal.

### Affected Areas
- `suvalor/tipos.py` — add Tesoreria URL, output dir, temp filenames, format constants, and ASP.NET IDs/selectors once confirmed.
- `suvalor/cli.py` — add opt-in `tesoreria` subcommand, pure argument parsing for dates/format/account/tag/redownload, and possibly include Tesoreria counts in `inventario`.
- `suvalor/orquestador.py` — add `ResumenTesoreria` and `sincronizar_tesoreria(page, ...)` that reuses the authenticated-session pattern.
- `suvalor/descargador.py` — likely add a generic click-to-download helper with optional popup/PDF fallback, instead of coupling Tesoreria to document-grid postback logic.
- `suvalor/verificacion.py` — extend validation to support Excel exports that may be HTML table, TSV/CSV-like text, OLE `.xls`, or OOXML zip, while still rejecting login/error HTML.
- `suvalor/rangos.py` — reuse the 89-day partitioning logic or reject over-limit ranges; do not raise portal load by increasing `range_days`.
- `suvalor/estado.py` — likely no new persistent state required for v1 if idempotency is based on deterministic target paths plus validation; only add state if proposal requires richer reporting.
- `tests/test_sync_args.py` or new `tests/test_tesoreria_args.py` — cover CLI help, format parsing, range planning, and no-Playwright short-circuit behavior.
- `tests/test_verificacion.py` — cover valid PDF, login HTML, valid HTML-XLS, TSV-like export, small/no-records export, and invalid/unknown Excel responses.
- `README.md` — document command usage, output layout, manual-login boundary, privacy of account selectors, and no default sync inclusion.
- `docs/SITE_NOTES.md` — update after implementation/manual evidence with exact redacted selectors and observed export formats.

### Approaches
1. **Opt-in Tesoreria command with deterministic files** — Add `suvalor tesoreria --from YYYY-MM-DD --to YYYY-MM-DD --format pdf|xls|both [--account TEXT] [--tag SAFE] [--redownload]`. Save to `Tesoreria/YYYY/YYYY-MM-DD_YYYY-MM-DD_movimientos_tesoreria.{pdf,xls}`; if `--tag` is supplied, append a safe tag before the extension.
   - Pros: Smallest safe feature; does not increase default portal load; mirrors existing manual-login command pattern; easy to test pure helpers; predictable idempotency by file path.
   - Cons: New orchestration and validation code still needed; exact date selectors need confirmation; account-specific disambiguation requires user discipline via `--tag`.
   - Effort: Medium

2. **Optional `sync --with-tesoreria` stage** — Add Tesoreria as a disabled-by-default sync stage that can run in the same browser session after docs/extractos/cartera.
   - Pros: One login for users who want all reports; aligns with existing `sync` summary pattern.
   - Cons: Needs more CLI planning and summary changes; review diff grows; date range arguments for sync become ambiguous; easier to accidentally increase portal load.
   - Effort: Medium/High

3. **Generic report-download framework** — Abstract cartera/extractos/tesoreria into reusable report descriptors and common download/validation primitives.
   - Pros: Best long-term architecture if more report endpoints are added.
   - Cons: Larger refactor across working flows; higher regression risk; not necessary for issue #4.
   - Effort: High

4. **Add Tesoreria to default `sync`** — Run movements as part of the default no-args command.
   - Pros: Maximum convenience.
   - Cons: Explicitly riskier portal load and unexpected sensitive outputs; contradicts the issue's alternative analysis; requires picking default dates and account semantics.
   - Effort: Medium with poor safety profile

### Recommendation
Use **Approach 1**.

Design guidance for the proposal/spec:
- Keep Tesoreria **opt-in only**. Do not add it to default `sync` in the first PR.
- Reuse manual login and authenticated-page orchestration: CLI opens browser, calls `login_manual()`, then `sincronizar_tesoreria()`.
- Date range: require explicit `--from` and `--to`. Reuse the existing 89-day safety model by partitioning with `rangos.partir_en_rangos()` or rejecting ranges above 89 days with a clear error; do not increase `range_days`.
- Destination layout: default to the issue proposal:
  - `Tesoreria/YYYY/YYYY-MM-DD_YYYY-MM-DD_movimientos_tesoreria.pdf`
  - `Tesoreria/YYYY/YYYY-MM-DD_YYYY-MM-DD_movimientos_tesoreria.xls`
  Use the chunk start year for `YYYY`. If an optional safe `--tag` is accepted, append `_<tag>` to avoid collisions for multiple accounts without writing account numbers.
- Account privacy: by default do not change the portal-selected account. If `--account` is passed, select by substring but never print the raw selected account label or account numbers. Prefer generic console text such as `Cuenta seleccionada` without the label.
- Idempotency: skip a target only when it already exists **and passes the expected validation**. Invalid existing files should be deleted/redownloaded unless `--redownload` semantics say otherwise. A new `_state/inventario_tesoreria.json` is not needed for v1 unless the proposal wants an inventory UI.
- Validation: keep PDF checks (`%PDF-`, `%%EOF`, minimum size) and add a conservative Excel/tabular validator that accepts known-good formats: HTML table, TSV/CSV-like text with headers, OLE `.xls`, or OOXML zip. It must reject login/error HTML via the existing login hints. Allow small but structured no-records exports if they contain headers or explicit no-records markers.
- Download helper: prefer a generic click/export helper that captures `expect_download` and can fall back to popup/PDF URL download if the browser opens a PDF inline. Avoid coupling to document-grid `Select$N` postbacks.
- Tests: strict TDD with pure pytest. Start with failing tests for CLI help/format parsing, range planning, path building, idempotent skip decisions, and validation for HTML-XLS/TSV/login/no-records files; then implement minimally and run `uv run pytest`.
- Docs: update `README.md` for the new command and `docs/SITE_NOTES.md` only with redacted, verified selectors/formats.

### Risks
- Exact Tesoreria date field IDs are not fully documented; implementation may need defensive suffix selectors or a redacted manual confirmation before coding.
- Account selection is sensitive. Logging or embedding account labels/numbers in filenames would violate privacy expectations.
- Same range + different account can collide if filenames do not include a safe user-provided tag.
- TSV/no-records validation can be too permissive and accidentally accept login/error HTML; keep negative login tests first.
- PDF empty/no-record reports may be smaller than current `min_bytes=2048`; if observed, use a Tesoreria-specific minimum only with tests and evidence.
- Adding Tesoreria to `sync` now would expand review scope and portal load; avoid for this change.

### Ready for Proposal
Yes — propose a bounded opt-in command, not a default sync stage. Tell the user the safe path is CLI/path/validation first under strict TDD, with runtime Playwright changes limited to a reusable authenticated-page Tesoreria flow and no real portal execution by agents.

artifacts:
  - openspec/changes/download-tesoreria-movements/exploration.md
next_recommended: Create proposal/spec/design/tasks for `download-tesoreria-movements`, with explicit decisions on 89-day handling and account-safe filename disambiguation.
risks:
  - Exact portal selectors for Tesoreria date inputs need confirmation before implementation.
  - Account privacy and filename/idempotency trade-off must be locked in the proposal.
  - Excel/TSV validation must stay conservative enough to reject login/error pages.
