status: completed
executive_summary: >
  Explored GitHub issue #3 for `handle-fb-504-diagnostics`. FB is already accepted only by explicit type selection and excluded from defaults, and the current downloader already avoids storing non-PDF content after verification. The missing piece is clearer, typed diagnostics for portal-side HTTP 504 / CloudFront HTML responses across both popup-request and direct-download paths, plus pure tests proving retries remain bounded by `retry_doc` and no HTML is recorded as a successful PDF.
skill_resolution: none

## Exploration: handle-fb-504-diagnostics

### Current State
- Issue #3 reports that `FB` rows can exist in the document grid, but opening `VerDocumentoElectronico.aspx?...Cd=FB...` returns `CloudFront 504 Gateway Timeout`. The requested behavior is diagnostic/safety handling, not making FB default.
- `suvalor/tipos.py` defines `FB` and maps it to `FacturasDeBolsa`; `TIPOS_DEFAULT = ["RC", "NC", "CE", "CC"]`, so `FB` is not selected by default. `suvalor/config.py` mirrors that default in `Config.tipos_default` and `TEMPLATE_TOML`.
- `suvalor/cli.py::_parsear_tipos()` accepts `FB` when explicitly requested through `--types FB`, so the CLI path is already opt-in. Both `sync` and `descargar` pass the selected types into `OpcionesCorrida` before browser work.
- `suvalor/orquestador.py::_procesar_paginas()` calls `descargar_doc()` for each grid row and records `resumen.fallidos` plus `detalle_fallidos` when the downloader returns `Resultado.FAIL`.
- `suvalor/descargador.py::_descargar_via_popup_o_download()` has two download paths:
  - direct Playwright download: `download.save_as(destino)`, with no HTTP status available to this code;
  - popup/Adobe path: extracts the popup URL and uses `context.request.get(url)`, returning `False, "status HTTP 504"` for non-200 responses.
- `descargar_doc()` retries failures up to `retry_doc` (default 3), deletes files that fail `verificar_descarga(destino, "pdf")`, registers the failed row in `_Fallidos/fallos.tsv`, and can propagate `(clave, motivo)` through `motivos_fallidos`.
- `suvalor/verificacion.py::es_pdf_valido()` rejects missing/empty/small files, non-`%PDF-` headers, and missing `%%EOF`. It detects generic HTML as `"es HTML (probable redirect a login)"`, but does not distinguish CloudFront 504 HTML from login HTML or other portal HTML errors.
- The `sync` final summary prints `Detalle fallidos`, but the standalone `descargar` command only prints aggregate counts and the `fallos.tsv` path; a user doing `descargar --types FB` may not see the specific CloudFront/504 reason in the final summary.
- Existing pure tests cover verification heuristics (`tests/test_verificacion.py`), state compatibility (`tests/test_estado.py`), and CLI planning/help (`tests/test_sync_args.py`). There are no downloader-specific tests for bounded retry counts, HTTP status propagation, or failed-document reason reporting.

### Affected Areas
- `suvalor/descargador.py` — primary place to classify HTTP 504 / portal HTML failures, preserve bounded retry behavior, avoid writing successful inventory on failure, and propagate a precise final reason.
- `suvalor/verificacion.py` — should identify CloudFront/504 HTML bodies when a direct download saves HTML with a `.pdf` name, while still rejecting all non-PDF content.
- `suvalor/orquestador.py` — already carries `detalle_fallidos`; may need minor adjustment only if downloader returns a structured or normalized reason.
- `suvalor/cli.py` — standalone `descargar` should show failure details similarly to `sync`; `_parsear_tipos()` tests should assert FB remains explicit opt-in and absent from defaults.
- `suvalor/estado.py` — `registrar_fallo()` currently writes only timestamp/type/doc/date/value. Avoid changing existing TSV shape unless a compatibility plan is included; diagnostics can be kept in console/log/summary instead.
- `suvalor/config.py` / `suvalor/tipos.py` — must preserve FB exclusion from defaults and the documented `retry_doc=3` bound.
- `docs/SITE_NOTES.md` — update the FB observation date and document the expected diagnostic behavior for opt-in FB 504 responses.
- `tests/test_verificacion.py` — add pure fixtures for CloudFront 504 HTML masquerading as PDF.
- New `tests/test_descargador.py` or similar — add pure/mock tests for retry count, status propagation, failure recording, and no inventory write on 504.
- `tests/test_sync_args.py` — add/keep tests that default type resolution excludes FB and explicit `--types FB` is accepted.

### Approaches
1. **Generic portal-failure classification in download + verification** — Normalize HTTP status failures from popup requests and HTML error bodies from direct downloads into clear reasons such as `portal respondio HTTP 504 (CloudFront Gateway Timeout)`. Keep the existing `retry_doc` cap and propagate the normalized reason through summaries/logs.
   - Pros: Covers FB without hard-coding all behavior to FB; improves diagnostics for any document type hit by portal/CloudFront errors; small and testable with pure fakes/fixtures; preserves state and defaults.
   - Cons: Requires introducing a small error-classification helper and downloader tests; direct-download path can infer 504 only from saved HTML body text, not HTTP status.
   - Effort: Medium

2. **FB-specific short-circuit on first 504** — If `codigo == "FB"` and a 504 is observed, stop retrying that row immediately and emit an FB-specific message.
   - Pros: Minimizes portal load for a known consistently failing type; user gets a direct FB diagnostic.
   - Cons: Adds type-specific policy inside generic download code; may surprise users who configured `retry_doc`; misses non-FB CloudFront failures; needs a clear spec decision that 504 is non-retryable.
   - Effort: Low/Medium

3. **Only improve PDF verification messages** — Teach `verificacion.py` to report CloudFront/504 HTML, but leave downloader retry and CLI summary behavior unchanged.
   - Pros: Very small diff; pure tests are easy.
   - Cons: Does not improve popup-request `status HTTP 504` wording, standalone `descargar` final diagnostics, or retry-count evidence; incomplete for issue #3.
   - Effort: Low

4. **Persist failure reasons in `fallos.tsv`** — Add a `motivo` column so later recovery/reporting can show why a row failed.
   - Pros: Durable diagnostics outside console/log.
   - Cons: Existing files have a 5-column header; appending 6-column rows to old files would make `leer_fallos_pendientes()` skip rows unless migration/header handling is added. Higher compatibility risk than needed for this issue.
   - Effort: Medium with migration risk

### Recommendation
Use **Approach 1**, with a narrow optional rule from Approach 2 only if the proposal explicitly declares HTTP 504 non-retryable.

Recommended proposal scope:
- Keep `FB` opt-in only: do not add it to `TIPOS_DEFAULT` or config template defaults.
- Add a pure classifier for portal/download failures that recognizes:
  - HTTP 504 status from `context.request.get()`;
  - HTML bodies containing `504`, `Gateway Timeout`, or `CloudFront` when a `.pdf` file is saved by the direct download path;
  - existing login/session HTML as a distinct reason, not as CloudFront.
- Keep retries bounded by `max(1, retry_doc)` / existing `retry_doc` behavior. Prefer preserving the configured retry count for all failures unless the spec decides that HTTP 504 should stop after one attempt to reduce portal load.
- Ensure failed FB documents do not add inventory entries and do not leave HTML/PDF-invalid files on disk.
- Surface the final diagnostic in both `sync` and standalone `descargar` summaries; log it as well. Avoid changing `_Fallidos/fallos.tsv` shape in this change.
- Strict TDD path: first add failing pure tests for CloudFront HTML verification, popup HTTP 504 propagation, bounded retry count, no inventory write/file retention on failure, and FB default exclusion/explicit acceptance; then implement minimally and run `uv run pytest`.
- Update `docs/SITE_NOTES.md` with issue #3's redacted evidence and expected behavior, without running real portal commands or adding credentials/session automation.

### Risks
- Direct Playwright `download.save_as()` does not expose HTTP status here; 504 diagnostics in that path must rely on HTML body content. If CloudFront changes wording, the message may fall back to generic HTML/non-PDF.
- Changing `fallos.tsv` format is tempting but risks compatibility with existing pending-failure files; keep durable state unchanged unless a separate migration is designed.
- Short-circuiting 504 after one attempt would reduce portal load but changes the meaning of `retry_doc`; this needs an explicit spec decision.
- Existing related OpenSpec changes (`fix-document-type-availability`, `support-pb-opt-in`) may alter defaults/type handling; coordinate before applying to avoid conflicting expectations around `CC`, `FB`, and `PB`.
- No live portal commands were run in this exploration; evidence comes from issue #3 and existing `docs/SITE_NOTES.md`.

### Ready for Proposal
Yes — propose a bounded bug fix. Tell the user the safe path is not to make FB reliable or default, but to make opt-in FB failures explicit, bounded, and non-destructive: classify CloudFront/HTTP 504, keep retries capped, delete invalid HTML/PDF files, preserve inventory/state compatibility, and cover it with pure pytest before any implementation.

artifacts:
  - openspec/changes/handle-fb-504-diagnostics/exploration.md
next_recommended: Create proposal/spec/design/tasks for `handle-fb-504-diagnostics`; require strict TDD evidence and no real portal execution.
risks:
  - Need a spec decision on whether HTTP 504 should consume all `retry_doc` attempts or short-circuit after the first classified 504.
  - Avoid `fallos.tsv` schema changes unless migration/header compatibility is explicitly designed.
  - Related OpenSpec changes may affect default type expectations and should be reconciled before implementation.
