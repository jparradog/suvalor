# Proposal: Handle FB 504 Diagnostics

## Intent

Make opt-in `FB` CloudFront/HTTP 504 failures explicit, bounded, sanitized, and non-destructive without making `FB` default or automating portal access.

## Scope

### In Scope
- Classify popup HTTP 504 and direct-download CloudFront/504 HTML saved as `.pdf`.
- Surface sanitized diagnostics in `sync` and `descargar` summaries/logs.
- Preserve `retry_doc` bounds, invalid-file deletion, and no inventory entry for failures.
- Add strict pure-pytest coverage and update `docs/SITE_NOTES.md`.

### Out of Scope
- Making `FB` reliable/default; changing defaults.
- Automating login, captcha, OTP, credentials, or portal runs.
- Changing `_Fallidos/fallos.tsv` schema or adding telemetry.

## Approach

Add generic portal-failure classification in `descargador` / `verificacion`. Keep configured `max(1, retry_doc)` behavior; do not short-circuit 504 unless a later spec changes policy. Normalize reasons like `portal respondio HTTP 504 (CloudFront Gateway Timeout)`. Redact raw URLs, `jwt=`, and query tokens; never pass raw exception text into diagnostics.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `suvalor/descargador.py` | Modified | Classify popup HTTP failures; sanitize diagnostics; keep bounded retries. |
| `suvalor/verificacion.py` | Modified | Detect CloudFront/504 HTML as invalid PDF. |
| `suvalor/cli.py`, `suvalor/orquestador.py` | Modified | Surface normalized failure reasons. |
| `suvalor/tipos.py`, `suvalor/config.py` | Unchanged | Preserve non-default `FB`. |
| `tests/`, `docs/SITE_NOTES.md` | Modified | TDD evidence and site note. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| CloudFront wording changes | Low | Generic HTML fallback. |
| URL/JWT leakage | Medium | Redaction tests; no raw exception pass-through. |
| Retry-policy ambiguity | Medium | Preserve configured `retry_doc`. |
| State compatibility regression | Low | Keep `fallos.tsv` unchanged. |

## Rollback Plan

Revert implementation commits touching these modules/tests/docs. Defaults and state schema stay unchanged, so no migration is required.

## Dependencies

- Strict TDD: `uv run pytest`; pure tests only, no network/Playwright/portal commands.
- Existing manual-login, privacy, and no-telemetry constraints.

## Success Criteria

- [ ] `FB` remains explicit opt-in and absent from defaults.
- [ ] HTTP 504 / CloudFront HTML failures produce sanitized diagnostics with URL/JWT redaction.
- [ ] Retries remain bounded by `retry_doc`; invalid files are deleted; inventory is not updated.
- [ ] Pure tests cover popup 504, direct HTML/PDF-invalid path, and default/explicit `FB` behavior.
- [ ] Review forecast: small single PR, under 400 changed lines; no chained PR expected.
