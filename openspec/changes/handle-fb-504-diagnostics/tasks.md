# Tasks: Handle FB 504 Diagnostics

Strict TDD applies: write each RED pure pytest first, then minimal GREEN, then refactor. Forecast: one PR under 400 changed lines.

## Phase 1: RED Test Coverage

- [ ] 1.1 Add failing `tests/test_descargador.py` coverage for popup HTTP 504 classification, final-failure no inventory or final PDF file, and bounded `max(1, retry_doc)` attempts.
- [ ] 1.2 Add failing `tests/test_descargador.py` coverage where attempt 1 returns portal 504/HTML failure, a later bounded attempt returns a valid PDF, final result succeeds, and inventory updates once.
- [ ] 1.3 Add failing `tests/test_verificacion.py` coverage for direct HTML saved as `.pdf`: CloudFront/504 is invalid, file is deleted, and valid PDFs still pass.
- [ ] 1.4 Add failing `tests/test_descargador.py` or `tests/test_orquestador.py` log/detail redaction coverage: no raw URL, query string, `jwt=`, token, or session values; normalized reason remains.
- [ ] 1.5 Add failing `tests/test_orquestador.py` coverage that `ResumenCorrida.detalle_fallidos` stores only sanitized normalized reasons: no raw URL, query, `jwt=`, token, or session values.
- [ ] 1.6 Add failing `tests/test_sync_args.py` coverage that `sync`/`descargar` summaries print sanitized normalized reasons and no raw URL, query, `jwt=`, token, or session values.
- [ ] 1.7 Add failing `tests/test_sync_args.py` coverage that default types exclude `FB` and explicit `--types FB` is accepted.
- [ ] 1.8 Add failing `tests/test_estado.py` coverage that `_Fallidos/fallos.tsv` keeps exactly five legacy columns and stores no reason.

## Phase 2: Diagnostics Foundation

- [ ] 2.1 Create `suvalor/diagnosticos.py` with pure classification/redaction helpers; no persistence, telemetry, Playwright, or network dependencies.
- [ ] 2.2 Update `suvalor/verificacion.py` to classify CloudFront/HTTP 504 HTML as invalid PDF and delete invalid `.pdf` files.
- [ ] 2.3 Wire helper imports minimally so verification tests pass without changing state JSON or TSV schemas.

## Phase 3: Retry and Reporting Implementation

- [ ] 3.1 Update `suvalor/descargador.py` retry flow to use `max(1, retry_doc)`, retry portal failures, and stop at the configured bound.
- [ ] 3.2 Update `suvalor/descargador.py` success-after-retry path so valid later attempts record success and inventory exactly once.
- [ ] 3.3 Update `suvalor/descargador.py` final failure path to preserve legacy `registrar_fallo()` and avoid inventory/final PDF writes.
- [ ] 3.4 Update `suvalor/orquestador.py` so `ResumenCorrida.detalle_fallidos` receives sanitized normalized reasons only.
- [ ] 3.5 Update `suvalor/cli.py` so `sync` and `descargar` summaries print only sanitized failure details.

## Phase 4: Compatibility, Docs, Verification

- [ ] 4.1 Verify `suvalor/config.py` and `suvalor/tipos.py` keep `FB` opt-in/default-excluded; change only if RED tests expose regression.
- [ ] 4.2 Update `docs/SITE_NOTES.md` to document `FB` opt-in and 504 diagnostics without claiming reliability is fixed.
- [ ] 4.3 Run targeted pytest during RED/GREEN cycles, then full `uv run pytest` before completion.
- [ ] 4.4 Confirm final implementation diff remains under 400 changed lines; split before coding if forecast grows.
