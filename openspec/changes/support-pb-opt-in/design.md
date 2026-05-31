# Design: Support PB Opt-In

## Technical Approach

Keep PB opt-in and make only the document-grid path type-aware. `orquestador` will pass the current document type to `pagina.extraer_filas`; legacy RC/NC/CE/CC/FB extraction keeps the existing fixed-index behavior, while PB uses normalized headers. PDF sanitization is generic in `verificacion` so document PDFs and extractos share the same conservative rule. No real portal commands, login automation, captcha, OTP, or credential handling are part of this change.

## Architecture Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| PB extraction | Add a PB header-aware branch in `pagina.py`; keep `Fila` unchanged. | Universal header parser for all types; PB branch in downloader. | Minimizes regression risk and keeps parsing separate from filesystem/download code. |
| Missing PB headers | Fail closed for the grid by raising a deterministic extraction error. | Skip rows silently; guess from legacy positions. | Resolves reviewer blocker: tests can assert one observable failure and PB rows cannot be hidden. |
| PB date source | Use `Fecha Operacion` for `fila.fecha`; ignore `Fecha Cumplimiento` for identity. | Use fulfillment date; store both dates. | Matches approved spec and avoids inventory JSON migration. |
| PDF sanitizer | Truncate bytes after the last `%%EOF`, then validate again. | First EOF; accept as-is if EOF is near tail; PB-only sanitizer. | Handles incremental PDFs safely and does not turn HTML/login responses into successes. |
| Idempotency | Preserve key `PB_<papeleta>` and filename `YYYY-MM-DD_PB_<papeleta>.pdf`; test skip before postback. | Add metadata to inventory; date in key. | Keeps state compatibility and resolves missing testable idempotency scenario. |

## Data Flow

    CLI/config types -> orquestador(codigo)
        -> pagina.extraer_filas(page, codigo)
            -> PB: table headers -> normalized indexes -> Fila(idx, Fecha Operacion, N°Papeleta, valor)
            -> other: existing fixed indexes -> Fila
        -> descargador identity: parse date -> PB_<papeleta> -> target filename
        -> download/write PDF -> verificacion sanitize last EOF -> validate -> inventory add

Failure path: PB required header missing -> `extraer_filas(..., "PB")` raises -> page/range fails visibly; no guessed rows, no downloads, no inventory writes.

## File Changes

| File | Action | Description |
|---|---|---|
| `suvalor/pagina.py` | Modify | Add `codigo` parameter, header normalization, PB required-header extraction, and deterministic exception for missing `N°Papeleta` or `Fecha Operacion`. |
| `suvalor/orquestador.py` | Modify | Pass `codigo` into `extraer_filas`; treat extraction failure as a failed consultation/page without real portal side effects. |
| `suvalor/parseo.py` | Modify | Parse numeric `DD/MM/YYYY` with `datetime`; keep Spanish month support; invalid numeric dates raise deterministically. |
| `suvalor/verificacion.py` | Modify | Add byte/path PDF EOF sanitizer and call it for `verificar_descarga(..., "pdf")` before final validation. |
| `suvalor/descargador.py` | Modify | Extract pure identity construction if needed for tests; preserve existing skip-before-download order. |
| `tests/test_pagina_pb.py` | Create | Pure tests for header normalization, PB extraction, and fail-closed missing headers. |
| `tests/test_parseo.py` | Modify | Numeric valid/invalid date cases. |
| `tests/test_verificacion.py` | Modify | Last-EOF truncation, idempotent sanitization, HTML/non-PDF rejection. |
| `tests/test_sync_args.py` | Modify | PB explicit opt-in and default exclusion assertions. |
| `tests/test_descargador.py` | Create | Pure identity/idempotency tests, including pre-existing `PB_<papeleta>` skip without postback. |
| `docs/SITE_NOTES.md` | Modify | Add redacted PB header observations and manual smoke-test guidance only. |

## Interfaces / Contracts

- `extraer_filas(page, codigo: str | None = None) -> list[Fila]`; callers may omit `codigo` for legacy behavior.
- PB normalized header aliases must match punctuation/accent/case variants of `N°Papeleta` and `Fecha Operacion`.
- PDF sanitizer contract: input bytes starting with `%PDF-` and containing at least one `%%EOF` return bytes through the last EOF marker; otherwise verification fails.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | PB header parsing, numeric dates, sanitizer, identity/idempotency. | Strict TDD pure pytest with fake table data/files under `tmp_path`. |
| Integration | Orchestrator passes `codigo`; verifier used by document and extracto PDF paths. | Mock/stub functions; no Playwright or network. |
| E2E | Manual smoke only, not automated. | Document safe command guidance; do not run real portal commands in tests. |

## Migration / Rollout

No data migration required. Rollout is safe because PB remains excluded from defaults; rollback is reverting touched `suvalor/`, `tests/`, and `docs/SITE_NOTES.md` files. Existing inventory shape remains compatible.

## Open Questions

None.
