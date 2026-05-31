# Design: Download Tesoreria Movements

## Technical Approach

Add an opt-in `tesoreria` command on the existing Typer -> `abrir_navegador()` -> `login_manual()` -> authenticated orchestrator pattern. Default `sync` stays unchanged. Build pure helpers first for dates, safe tag canonicalization, destination planning, and validation; only then add Playwright page automation once redacted Tesoreria selectors are documented in `docs/SITE_NOTES.md` or fixtures.

## Architecture Decisions

| Option | Tradeoff | Decision |
|---|---|---|
| Use raw account label in filenames/logs | Easy but leaks banking data and creates ambiguous collisions | Reject. Raw account selector text is input-only and never appears in paths, logs, state, or summaries. |
| Require user tag for account scope | Adds one CLI argument but preserves privacy | If `--account` is supplied, `--tag` is mandatory and validated before browser startup. Same tag across separate runs is user-controlled identity; the tool cannot infer account identity without leaking data, so docs warn users to keep tags unique. |
| Canonicalize tags | Prevents `Cuenta A`, `cuenta-a`, and unsafe path variants from diverging | `canonicalizar_tag_tesoreria()` trims, Unicode-normalizes, lowercases, converts whitespace runs to `-`, allows only `[a-z0-9._-]`, rejects empty/unsafe/path-like values, and fails the plan if two requested account scopes resolve to the same canonical tag in one run. |
| Reuse 89-day range helper | Less custom code, inherits documented site limit | Use `partir_en_rangos(..., MAX_DIAS_POR_RANGO)` for CLI planning and orchestration. |
| Validate `.xls` as only cartera HTML | Too narrow for Tesoreria exports | Add `es_tabular_tesoreria_valido` for OLE XLS, XLSX ZIP, HTML table, and constrained delimited text. |
| Replace final before validation | Simple but can destroy valid prior files | Download to candidate temp, validate, then atomic `replace()` final per format. Failed candidates are deleted; prior finals remain. |

## Data Flow

```text
CLI args -> pure validation/plan -> canonical tag + chunks <=89d
       -> safe destinations -> login manual -> Tesoreria page
       -> optional account selection without echo -> export PDF/XLS
       -> temp candidate -> validate -> atomic replace final
```

For `--format both`, each format has an independent candidate/final. A PDF success may commit while an XLS failure leaves any previous valid XLS final untouched. Existing final-file idempotency applies within the canonical tag scope.

## File Changes

| File | Action | Description |
|---|---|---|
| `suvalor/cli.py` | Modify | Add `tesoreria`; pre-browser validation for dates, format, `--account`/`--tag`, and duplicate canonical tags. |
| `suvalor/rangos.py` | Reuse/Modify | Reuse `partir_en_rangos`; add only small explicit-date planner helper if needed. |
| `suvalor/tipos.py` | Modify | Add `TESORERIA_DIR`, URL, temp names, formats, and only confirmed selector constants. |
| `suvalor/verificacion.py` | Modify | Add Tesoreria PDF/tabular validator dispatch. |
| `suvalor/descargador.py` | Modify | Add export-to-temp helper after selector evidence exists. |
| `suvalor/orquestador.py` | Modify | Add `ResumenTesoreria` and `sincronizar_tesoreria()` authenticated flow. |
| `docs/SITE_NOTES.md` | Modify | Record redacted selector/export evidence. |
| `tests/test_tesoreria_*.py`, `tests/test_verificacion.py` | Create/Modify | Pure pytest coverage for args, tags, collisions, paths, chunking, validation, and atomic redownload. |
| `README.md` | Modify | Document opt-in use, manual login, safe tags, privacy, and tag uniqueness responsibility. |

## Interfaces / Contracts

`OpcionesTesoreria` carries `desde`, `hasta`, `formato: "pdf"|"xls"|"both"`, `account: str|None`, canonical `tag: str|None`, and `redownload`.

`construir_destino_tesoreria(rango, formato, tag)` returns `BASE / "Tesoreria" / YYYY / "YYYY-MM-DD_YYYY-MM-DD_movimientos_tesoreria[_tag].ext"`; `_tag` is canonical and never derived from account text.

Delimited Tesoreria text is valid only when it has all constraints: at least two non-empty rows; one stable delimiter chosen from tab, semicolon, comma; at least two header columns; and at least one lowercased header token among `fecha`, `descripcion`, `movimiento`, `valor`, `saldo`. Empty, headerless, login, and error responses are rejected.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | CLI/account/tag rules and duplicate canonical tags | Typer runner and pure planner tests; assert fail before browser startup and no raw account text. |
| Unit | Destination names and 89-day chunking | `tmp_path` and `partir_en_rangos` tests. |
| Unit | Tabular validation | Fixtures for OLE, XLSX, HTML table, valid/invalid CSV/TSV, empty/login/error/headerless. |
| Unit | Redownload atomicity | Fake candidate/final files; failed XLS preserves previous valid final. |
| Integration-lite | Orchestrator branching | Monkeypatch downloader/selectors; no Playwright/network. |

## Migration / Rollout

No state migration required. Generated files are deterministic under `SUVALOR_HOME/Tesoreria/YYYY/`. Rollout: tests, docs/selector evidence, then gated page automation.

## Open Questions

None. Selector evidence is an implementation gate, not an unresolved design question.
