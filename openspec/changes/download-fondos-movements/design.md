# Design: Download Fondos Movements

## Technical Approach

Add an opt-in `suvalor fondos` command that reuses the existing manual-login Playwright lifecycle and cartera/extractos download-validation patterns. v1 is intentionally default-only: current portal account and fund `TODOS`; no raw or alias account/fund selectors are exposed. Explicit ISO dates are split with the existing 89-day range primitive, each chunk navigates to `InformeFondos.aspx`, fills verified date inputs, exports the movement report, validates it, and persists only successful artifacts.

## Architecture Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| CLI surface | `fondos --from --to [--tag SAFE] [--redownload]`; default `sync` unchanged | Add `--account`/`--fund`, or include in `sync` | Keeps load opt-in and removes selector/idempotency privacy risk from v1. |
| Idempotency key | Filename is date range plus optional safe tag only | Infer key from mutable account/fund labels | v1 always uses default account + `TODOS`; `--tag` is user-controlled disambiguation, not selection. Future non-default aliases must require safe unique tag/collision checks before browser startup. |
| Selector evidence gate | Do not automate page flow until `docs/SITE_NOTES.md` has redacted evidence for URL, date inputs, export action, and no-record marker | Guess ASP.NET IDs or rely on current “No explorado” note | Matches existing fragile WebForms practice and prevents unsafe automation based on unverified selectors. |
| Module boundary | CLI validates; `orquestador.py` sequences; `pagina.py` owns DOM helpers; `descargador.py` captures downloads; `verificacion.py` validates bytes | Inline browser code in CLI | Follows current separation used by docs, extractos, and cartera. |
| State | No Fondos inventory and no fake no-data files | Add new JSON state | Existing-file validation gives deterministic skip/redownload without migration or persistent no-data records. |

## Data Flow

    cli.fondos validates dates/tag
      -> abrir_navegador + login_manual
      -> orquestador.sincronizar_fondos chunks <= 89 days
      -> pagina.goto_robusto(FONDOS_URL) + verified date fill + export/no-record checks
      -> descargador Excel/report click helper
      -> verificacion fondos validator
      -> Fondos/YYYY/YYYY-MM-DD_YYYY-MM-DD_movimientos_fondos[_tag].xls

If a verified no-record marker appears, return `sin_datos` with no file/state entry. If the destination exists and validates, return `skip` unless `--redownload`; invalid existing files are replaced only after a fresh valid download is available.

## File Changes

| File | Action | Description |
|---|---|---|
| `suvalor/cli.py` | Modify | Add default-only `fondos` command and pre-browser date/tag validation. |
| `suvalor/orquestador.py` | Modify | Add Fondos options/resume dataclasses, chunk loop, idempotency, retries, redacted summaries, atomic persistence. |
| `suvalor/pagina.py` | Modify | Add Fondos helpers gated by documented URL/date/export/no-record evidence. |
| `suvalor/descargador.py` | Modify | Add reusable `expect_download` helper for Excel/report button flows. |
| `suvalor/verificacion.py` | Modify | Add Fondos validator for OLE XLS, XLSX, HTML table report, CSV/TSV-like text; reject login/error HTML. |
| `suvalor/tipos.py` | Modify | Add Fondos directory, URL, and only evidence-backed selector constants. |
| `tests/` | Modify | Add pure pytest coverage for CLI validation, default-only privacy, destination/idempotency, validation, no-record, atomicity. |
| `README.md`, `docs/SITE_NOTES.md` | Modify | Document opt-in usage, privacy, manual login, evidence gate, validation, idempotency, `sin_datos`. |

## Interfaces / Contracts

- CLI accepts only `--from`, `--to`, optional safe `--tag`, and `--redownload`.
- `--tag` is slug-like filename disambiguation only; it never selects account/fund.
- Raw/non-default account or fund selection is unsupported in v1 and must fail before browser startup if introduced accidentally.
- Final paths stay under `SUVALOR_HOME/Fondos/YYYY/` and exclude portal labels, numbers, selectors, state, logs, and docs.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | CLI date/tag/default-only validation | `CliRunner`; assert no browser launch on validation failure. |
| Unit | destination naming, skip, invalid redownload, forced redownload | `tmp_path` files and monkeypatched validators. |
| Unit | Fondos validators and rejection of login/error HTML | Byte/text fixtures in `tests/test_verificacion.py`. |
| Integration-ish | chunk loop, `sin_datos`, failure atomicity, redacted failures | Fake page/download helpers; no network or real Playwright. |
| Manual | Real portal smoke | Maintainer only after selector evidence; agents must not run real portal commands. |

## Migration / Rollout

No migration required. Roll out behind the new command only. Implementation must stop before Fondos page automation while `docs/SITE_NOTES.md` lacks redacted default-flow evidence.

## Open Questions

- [ ] Redacted selector evidence for `InformeFondos.aspx` URL, date inputs, export action, and no-record marker must be captured before implementation enables page automation.
