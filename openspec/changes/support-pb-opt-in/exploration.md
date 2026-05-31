status: completed
executive_summary: >
  Explored GitHub issue #2 for `support-pb-opt-in`. PB is already accepted as an explicit document type and excluded from defaults, but the current document-grid parser assumes RC/NC/CE-style columns. Recommended scope is a small opt-in feature: add a header-aware PB row parser, choose `Fecha Operacion` as the filename date, keep inventory keys as `PB_<papeleta>`, and add a generic PDF EOF sanitizer that truncates bytes after the last `%%EOF` before final validation/storage. No login/captcha/OTP automation or real portal commands are required.
skill_resolution: none

## Exploration: support-pb-opt-in

### Current State
- `suvalor/tipos.py` already defines `TipoDoc.PB`, maps `PB` to `PapeletasDeBolsa`, and excludes `PB` from `TIPOS_DEFAULT`. `--types PB` is therefore already syntactically opt-in.
- `suvalor/cli.py::_parsear_tipos()` accepts any key in `NOMBRES_TIPOS`; both `sync` and `descargar` route selected types into `OpcionesCorrida` before any browser work.
- `suvalor/pagina.py::extraer_filas()` uses a fixed RC/NC/CE-style grid projection: `fecha=c[0]`, `doc_num=c[2]`, `valor=c[4]`. Issue #2 reports PB-specific columns such as `N°Papeleta`, `Fecha Operacion`, and `Fecha Cumplimiento`, so fixed indexes are fragile.
- `suvalor/descargador.py::descargar_doc()` is generic once it receives `Fila(idx, fecha, doc_num, valor)`: it parses `fila.fecha`, names files as `YYYY-MM-DD_<TIPO>_<NUMERO>.pdf`, and uses inventory key `<TIPO>_<NUMERO>`.
- `suvalor/parseo.py::parsear_fecha_grilla()` handles `12/abr/2025` and `12/abr./2025`, but not plain numeric `DD/MM/YYYY` correctly; the current regex can match numeric months and map them to `00`, producing an invalid value such as `2025-00-12`. This is not suitable for deterministic PB filenames if the PB grid uses numeric dates.
- `suvalor/verificacion.py::es_pdf_valido()` checks `%PDF-`, minimum size, and presence of `%%EOF` in the last 1KB. It does not sanitize trailing bytes; a PB response with HTML after EOF may be stored as-is if the marker remains near the end, or falsely fail if trailing HTML pushes EOF outside the final 1KB.
- Existing tests are pure pytest tests for parsing, verification, state compatibility, and CLI help/planning. There are no current tests for `pagina.extraer_filas()` or PB-specific parsing.

### Affected Areas
- `suvalor/pagina.py` — needs type-aware or header-aware row extraction for PB while preserving existing RC/NC/CE behavior.
- `suvalor/orquestador.py` — currently calls `extraer_filas(page)` without the document type; may need to pass `codigo` so PB can use the PB parser.
- `suvalor/descargador.py` — should keep the generic download/idempotency flow, but should receive PB rows whose `fecha` and `doc_num` are already normalized by the parser; may call PDF sanitization before verification.
- `suvalor/verificacion.py` — best home for a pure PDF EOF sanitizer/helper used before `es_pdf_valido`.
- `suvalor/parseo.py` — should parse numeric `DD/MM/YYYY` in addition to month-name grid dates.
- `suvalor/tipos.py` / `suvalor/config.py` — confirm PB remains opt-in only; no default inclusion.
- `tests/test_parseo.py` — add numeric date cases.
- `tests/test_verificacion.py` — add trailing-HTML-after-EOF sanitization and idempotency tests.
- `tests/test_sync_args.py` — add explicit PB opt-in/default exclusion tests around `_parsear_tipos()` / config defaults.
- New or existing parser tests — add pure tests for PB row extraction using a fake/evaluable page or by extracting parser logic into a pure helper.
- `docs/SITE_NOTES.md` — update after implementation with redacted PB evidence and current EOF/trailing-HTML behavior.

### Approaches
1. **Header-aware PB parser, generic downloader** — Keep `Fila` and `descargar_doc()` generic. Teach page parsing to select columns by header text for `PB`, mapping `N°Papeleta` -> `doc_num` and `Fecha Operacion` -> `fecha`; leave other types on existing behavior or migrate them cautiously.
   - Pros: Minimal behavioral change; preserves existing inventory/file naming contract; easy to test with pure parser fixtures; keeps PB opt-in.
   - Cons: Requires passing `codigo` into extraction or adding a new extraction function; depends on stable PB header labels.
   - Effort: Medium

2. **Universal header-aware parser for all document types** — Replace fixed indexes with header-name extraction for every grid type.
   - Pros: More robust if RC/NC/CE columns move; one parser model.
   - Cons: Larger regression surface for working types; needs more fixture coverage; unnecessary for issue #2.
   - Effort: High

3. **PB-specific branch inside `descargar_doc()`** — Keep current row extraction and special-case PB naming/idempotency during download.
   - Pros: Avoids changing orchestration signatures.
   - Cons: Wrong layer: download code cannot reliably recover missing PB columns; mixes parsing with filesystem/download concerns; harder to test cleanly.
   - Effort: Medium with worse architecture

4. **PB-only PDF sanitizer** — Sanitize only when `codigo == "PB"`.
   - Pros: Smallest runtime blast radius.
   - Cons: Duplicates PDF rules by document type; trailing HTML after EOF is a PDF transport/content issue, not a PB semantic issue; extractos/docs may benefit too.
   - Effort: Low

### Recommendation
Use **Approach 1** for parsing plus a **generic PDF EOF sanitizer** in verification/download plumbing.

Design choices for proposal/spec:
- PB remains opt-in: `PB` MUST NOT be added to `TIPOS_DEFAULT` or config template defaults.
- Parser: use `Fecha Operacion` as the canonical filename date because it identifies when the trade/order happened; keep `Fecha Cumplimiento` as non-naming metadata unless later state shape explicitly supports metadata.
- Filename: `YYYY-MM-DD_PB_<papeleta>.pdf`, where `YYYY-MM-DD` comes from parsed `Fecha Operacion` and `<papeleta>` is sanitized consistently with existing document number behavior.
- Idempotency: keep current inventory key shape `PB_<papeleta>`; do not change `_state/inventario.json` format.
- Date parsing: extend `parsear_fecha_grilla()` or add a helper so both `DD/mmm/YYYY` and `DD/MM/YYYY` produce ISO dates.
- Sanitization: add a pure helper that requires `%PDF-`, finds the last `%%EOF`, truncates bytes after that marker, and then runs normal validation. It should be idempotent and must not convert non-PDF/HTML-login responses into successes.
- Test strategy: strict TDD with pure pytest only. Start with failing tests for PB row parsing, numeric dates, PB default exclusion/explicit opt-in, and EOF trailing HTML sanitization; then implement minimally and run `uv run pytest`.

### Risks
- PB grid evidence in issue #2 is redacted and not a complete fixture; exact header text may vary (`N°`, `No.`, accents, whitespace). Parser should normalize headers defensively.
- Choosing `Fecha Operacion` affects filenames permanently; changing later would create duplicate/renamed files. Proposal should explicitly lock this decision.
- Multiple `%%EOF` markers are valid in incremental PDFs; sanitizer must truncate at the last marker, not the first.
- Sanitization must not hide login redirects or corrupt/truncated PDFs; validation still needs to fail when header/min-size/EOF checks fail.
- Any change in `orquestador.py` extraction signature affects the working RC/NC/CE flow; keep compatibility tests focused and diff small.
- Do not run real portal commands during implementation; if live PB behavior needs confirmation, document a manual smoke-test command for the maintainer only.

### Ready for Proposal
Yes — propose a bounded opt-in feature. Tell the user the safe implementation path is parser-first and test-first: PB is already opt-in at CLI/type level, but needs PB-specific row extraction, a deliberate `Fecha Operacion` filename decision, and generic PDF trailing-HTML sanitization. Expected implementation should stay under the 400-line review budget and does not need chained PRs.

artifacts:
  - openspec/changes/support-pb-opt-in/exploration.md
  - sdd/support-pb-opt-in/explore.md
next_recommended: Create proposal/spec/design/tasks for `support-pb-opt-in`; require strict TDD evidence and no real portal execution.
risks:
  - Need a real or redacted PB table fixture before implementation, or tests must encode the issue's known header labels with defensive normalization.
  - Filename-date choice (`Fecha Operacion`) should be approved in proposal/spec because it affects long-term idempotency.
  - EOF sanitization must be generic but conservative so it does not mask invalid login/error HTML.
