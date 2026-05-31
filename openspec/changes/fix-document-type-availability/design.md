# Design: Fix Document Type Availability

## Technical Approach

Add one static availability boundary shared by all document-query entry points before Playwright is opened. `CC` stays valid stored metadata for historical state, inventory rebuilds, folder names, and legacy `fallos.tsv` rows, but it is never treated as retryable portal work. `descargar` and `sync` fail fast on unavailable requested/configured types; `recuperar-fallidos` partitions pending rows first, reports unavailable rows as skipped, and opens the browser only if at least one current selector row remains.

## Architecture Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| Availability model | Add constants in `suvalor/tipos.py` for current selector types, safe defaults, and legacy/unavailable types; keep `CC` in `TipoDoc`/`NOMBRES_TIPOS`. | Delete `CC`; probe selector live. | Preserves old data and keeps validation pure, deterministic, and testable without login. |
| New query validation | `_parsear_tipos()` rejects any resolved list containing `CC` before `abrir_navegador()` for `descargar` and docs-enabled `sync`. | Silently drop `CC`. | Configured/explicit types are user intent; partial sync would hide missing work. |
| Failed retry validation | `recuperar-fallidos` skips and reports unavailable rows, then retries only current selector rows. If none remain, return before `Config.cargar()`, `MemoriaTimings()`, `abrir_navegador()`, login, or `setear_filtros()`. | Fail-fast on the first `CC`; open browser then skip inside loop. | Mixed files can still recover `RC`/`NC` rows, while only-legacy files avoid unnecessary manual login and portal work. |
| Persistence of skipped retries | Do not rewrite `fallos.tsv` in this issue; report skipped rows/counts in stdout. | Remove or mark rows in-place. | Avoids data migration and keeps scope limited to issue #1. |

## Data Flow

    CLI/config/fallos.tsv
            |
            v
    static availability gate
      |                 |
      | invalid query   | retry rows with CC
      v                 v
    exit 2        report skipped rows
                         |
                 current rows remain?
                   | no        | yes
                   v           v
                return      abrir_navegador -> login -> setear_filtros(current only)

Historical `_state/*.json`, inventory keys, and existing `CertificadosDeCustodia/` folders bypass the query gate because they are stored data, not a new portal query plan.

## File Changes

| File | Action | Description |
|---|---|---|
| `suvalor/tipos.py` | Modify | Define `TIPOS_SELECTOR_ACTUALES`, `TIPOS_LEGACY_NO_DISPONIBLES`, safe `TIPOS_DEFAULT = ["RC", "NC", "CE"]`; keep `CC` metadata. |
| `suvalor/config.py` | Modify | Generated template excludes `CC`; default config inherits safe defaults. |
| `suvalor/cli.py` | Modify | Use the shared current-selector gate in `_parsear_tipos()` and add a pure helper for `recuperar-fallidos` that partitions retryable vs unavailable rows before browser startup. |
| `tests/test_sync_args.py` | Modify | Add pure CLI/helper tests for defaults, explicit/mixed `CC`, legacy config rejection, and `recuperar-fallidos` only-`CC` short-circuit. |
| `tests/test_estado.py` | Modify/keep | Ensure historical state with `CC` remains readable. |
| `README.md` | Modify | Document current selector set, safe defaults, opt-in `FB`/`PB`, legacy `CC`, and retry skip behavior. |
| `docs/SITE_NOTES.md` | Modify | Record issue #1 selector evidence and static no-login validation boundary. |

## Interfaces / Contracts

```python
TIPOS_SELECTOR_ACTUALES = {"CE", "FB", "NC", "PB", "RC"}
TIPOS_LEGACY_NO_DISPONIBLES = {"CC"}
TIPOS_DEFAULT = ["RC", "NC", "CE"]
```

`_parsear_tipos(types_raw, cfg)` remains the fail-fast gate for new planned queries. `recuperar-fallidos` uses a separate partition helper because unavailable retry rows are skipped/reported rather than fatal.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | Constants/default config exclude `CC`; current types accepted. | Pure pytest assertions/imports. |
| CLI unit | `--types CC`, `--types RC,CC`, and config default with `CC` exit 2 before Playwright. | `CliRunner` or direct helper tests with `abrir_navegador` patched to fail if called. |
| Retry unit | Only-`CC` `fallos.tsv` causes no `abrir_navegador()` and no `setear_filtros()`, reports skipped unavailable rows. | Monkeypatch `leer_fallos_pendientes`, `abrir_navegador`, and `setear_filtros`; invoke `recuperar-fallidos`. |
| Retry unit | Mixed `CC`/`RC` skips `CC` before portal work and calls filters only for current rows. | Helper-level partition test; optional CLI test with mocks. |
| State compatibility | Historical state containing `CC` loads unchanged. | Existing `tests/test_estado.py` coverage. |
| E2E | Not applicable. | No real portal, no login automation. |

## Migration / Rollout

No migration required. Existing configs containing `CC` fail with guidance. Existing `fallos.tsv` rows with `CC` are left intact and reported as skipped on retry runs.

## Open Questions

None.
