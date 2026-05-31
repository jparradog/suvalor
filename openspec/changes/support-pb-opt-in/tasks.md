# Tasks: Support PB Opt-In

## Review Workload Forecast

Estimated implementation diff: 250-350 changed lines, below the 400-line chained-PR threshold. Keep one PR unless RED/GREEN work reveals broader parser or inventory changes.

## Phase 1: RED Tests

- [ ] 1.1 Create `tests/test_pagina_pb.py` PB fixtures proving normalized `N°Papeleta`/`Fecha Operacion` extraction and no RC fixed-index fallback.
- [ ] 1.2 Add `tests/test_pagina_pb.py` missing-header cases that assert a deterministic extraction error; no skip, guess, or legacy fallback.
- [ ] 1.3 Extend `tests/test_parseo.py` for `05/04/2025`, invalid `31/02/2025`, unknown Spanish month, impossible Spanish dates, and no `YYYY-00-DD`.
- [ ] 1.4 Extend `tests/test_sync_args.py` proving defaults exclude `PB` and explicit `PB` includes only PB, not FB/other opt-ins.
- [ ] 1.5 Extend `tests/test_verificacion.py` for last-`%%EOF` truncation, idempotent sanitizing, missing EOF/header rejection, and HTML/non-PDF safety.
- [ ] 1.6 Create/extend `tests/test_descargador.py` for `YYYY-MM-DD_PB_<papeleta>.pdf`, key `PB_<papeleta>`, and `Fecha Operacion` identity.
- [ ] 1.7 Add RED idempotency tests in `tests/test_descargador.py`: existing `PB_<papeleta>` key or target file skips before `_disparar_postback`.
- [ ] 1.8 Add RED integration tests in `tests/test_orquestador.py`: `orquestador` calls `extraer_filas(page, codigo)` with `PB` and preserves legacy non-PB behavior.
- [ ] 1.9 Add RED integration tests proving `verificar_descarga(..., "pdf")` sanitizes/truncates trailing bytes for document PDFs and extractos, or that both call the same sanitizer helper.

## Phase 2: GREEN Core Implementation

- [ ] 2.1 Modify `suvalor/parseo.py` so matched numeric/Spanish grid dates use validated `datetime` paths and reject invalid dates.
- [ ] 2.2 Modify `suvalor/pagina.py` to accept `codigo`, normalize PB headers, map papeleta/date, and raise on missing required PB headers.
- [ ] 2.3 Modify `suvalor/orquestador.py` to pass current `codigo` into `extraer_filas` without changing legacy default behavior.
- [ ] 2.4 Modify `suvalor/verificacion.py` to truncate PDF bytes after the last `%%EOF`, write sanitized bytes, then validate conservatively.
- [ ] 2.5 Modify `suvalor/descargador.py` so PB key/filename calculation and inventory-or-file skip happen before postback.
- [ ] 2.6 Keep CLI/type resolution unchanged except for explicit PB acceptance and default exclusion proven by tests.

## Phase 3: REFACTOR and Integration Checks

- [ ] 3.1 Refactor shared header/date/PDF helpers only after GREEN, preserving public contracts and state JSON shape.
- [ ] 3.2 Verify RC/NC/CE/CC/FB extraction still uses existing behavior when `codigo` is omitted or non-PB.
- [ ] 3.3 Confirm sanitizer never converts HTML/login responses into successful PDFs for documents or extractos.

## Phase 4: Documentation and Final Verification

- [ ] 4.1 Update `docs/SITE_NOTES.md` with redacted PB header observations and safe manual `--smoke-test --max-docs 3 --types PB` guidance.
- [ ] 4.2 Run targeted RED/GREEN evidence commands for changed tests, then full `uv run pytest` before marking complete.
- [ ] 4.3 If diff exceeds 400 lines, stop and propose chained PR boundaries before implementation continues.
