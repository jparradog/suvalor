# Design: Handle FB 504 Diagnostics

## Technical Approach

Add a pure diagnostics boundary around document downloads. Popup HTTP failures and downloaded HTML masquerading as PDFs are classified into normalized, sanitized runtime reasons, then carried through console/log output and `ResumenCorrida.detalle_fallidos`. `FB` remains opt-in, `_Fallidos/fallos.tsv` remains the legacy five-column retry queue only, and retries stay bounded by `max(1, retry_doc)` so a later valid PDF attempt can still succeed.

## Architecture Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| Diagnostics model | Add small pure helpers for classification/redaction, used by downloader and verification. | Inline string checks in each caller. | Keeps redaction consistent and testable without Playwright/network. |
| 504 retry policy | Treat portal 504/CloudFront as retryable until `max(1, retry_doc)` attempts are exhausted. | Short-circuit 504 after first attempt. | Matches config semantics and spec: later bounded retry can succeed. |
| TSV compatibility | Keep `registrar_fallo()` unchanged: `timestamp`, `tipo`, `doc_num`, `fecha_doc`, `valor` only. | Add/overload a reason column. | Avoids state migration and prevents reason/URL persistence in `_Fallidos/fallos.tsv`. |
| Reporting scope | Store sanitized reasons only in runtime summaries/logs (`detalle_fallidos` or equivalent). | Persist reasons in state files. | Solves user diagnostics while minimizing privacy and compatibility risk. |

## Data Flow

    postback row
        |
        v
    _descargar_via_popup_o_download
      | popup HTTP status      | direct saved file
      v                        v
    classify+redact       verificar_descarga -> classify HTML/504
        |                        |
        +---------- sanitized reason ----------+
                                                v
    retry loop max(1, retry_doc)
       | later valid PDF          | attempts exhausted
       v                          v
    inventory add + OK       registrar_fallo legacy TSV
                              detalle_fallidos + log/CLI summary

Raw popup URLs, query strings, JWTs, tokens, and session identifiers never leave the download helper except after redaction.

## File Changes

| File | Action | Description |
|---|---|---|
| `suvalor/diagnosticos.py` | Create | Pure classification/redaction helpers for HTTP status, HTML bodies, and exception text. |
| `suvalor/descargador.py` | Modify | Normalize attempts with `max(1, retry_doc)`, classify popup HTTP 504, sanitize all failure reasons before console/log/summary, preserve legacy `registrar_fallo()` call. |
| `suvalor/verificacion.py` | Modify | Detect CloudFront/HTTP 504 HTML as invalid PDF with a normalized sanitized reason; valid PDFs still pass. |
| `suvalor/orquestador.py` | Modify | Ensure unexpected document failure details are sanitized before `ResumenCorrida.detalle_fallidos` and logs. |
| `suvalor/cli.py` | Modify | Show document failure details for classic `descargar` as `sync` already does; output only sanitized reasons. |
| `suvalor/tipos.py`, `suvalor/config.py` | Keep/verify | `FB` remains accepted but excluded from default configured document types. |
| `docs/SITE_NOTES.md` | Modify | Document FB opt-in and known 504 diagnostic behavior; not a reliability fix. |
| `tests/test_verificacion.py`, `tests/test_sync_args.py`, `tests/test_descargador.py`, `tests/test_estado.py` | Modify/Create | Pure coverage for HTML/504 classification, FB opt-in/defaults, retry bounds/success-after-failure, reporting redaction, and TSV schema compatibility. |

## Interfaces / Contracts

- `sanitizar_diagnostico(texto: str) -> str`: removes full URLs, query strings, JWT/token/session identifiers, and unsafe raw exception payloads.
- `clasificar_fallo_portal(status: int | None = None, contenido: bytes | str | None = None, detalle: str = "") -> str | None`: returns normalized reasons such as `portal respondio HTTP 504 (CloudFront Gateway Timeout)`.
- `ResumenCorrida.detalle_fallidos` contains `(clave_doc, motivo_sanitizado)` only.
- `_Fallidos/fallos.tsv` remains exactly five columns and MUST NOT include reasons.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | Redaction removes URLs, queries, `jwt`, token and session identifiers. | Pure helper tests. |
| Unit | Popup HTTP 504 and CloudFront HTML produce normalized reasons. | Fake response/body fixtures. |
| Unit | Retry count is `max(1, retry_doc)` and later valid retry succeeds. | Monkeypatch downloader helper and inventory. |
| Unit | Invalid HTML `.pdf` is deleted, not inventoried, and failure detail is sanitized. | `tmp_path` + fakes. |
| Compatibility | `fallos.tsv` keeps five columns and no reason value. | State/file assertion. |
| CLI | `FB` excluded by defaults, explicit `--types FB` accepted; summaries print sanitized reasons. | Pure CLI/helper tests, no Playwright. |

## Migration / Rollout

No migration required. Existing inventories, state JSON, and `_Fallidos/fallos.tsv` remain readable. Rollout is a small single PR under the configured 400-line review budget.

## Open Questions

None.
