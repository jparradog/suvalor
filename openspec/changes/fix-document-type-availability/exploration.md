status: completed
executive_summary: >
  Explored issue #1. The repo still treats `CC` as supported/default, while the reported current portal selector exposes only `CE`, `FB`, `NC`, `PB`, and `RC`. Recommended fix is to keep `CC` as legacy metadata for compatibility, remove it from defaults, and prevent unavailable legacy types from reaching the browser.
skill_resolution: none

## Exploration: fix-document-type-availability

### Current State
- `suvalor/tipos.py` models `TipoDoc.CC`, maps `CC` to `CertificadosDeCustodia`, and includes `CC` in `TIPOS_DEFAULT = ["RC", "NC", "CE", "CC"]`.
- `suvalor/config.py` mirrors that default in `Config.tipos_default` and in `TEMPLATE_TOML`, so new configs and existing configs may still include `CC`.
- `suvalor/cli.py::_parsear_tipos()` accepts any key in `NOMBRES_TIPOS`; both `descargar` and `sync` help text still advertise `(RC,NC,FB,PB,CE,CC)`.
- `suvalor/orquestador.py` trusts `opciones.tipos` and calls `setear_filtros(page, codigo, ...)`. If `CC` is not present in the HTML `<select>`, the browser flow can attempt an unavailable value.
- `docs/SITE_NOTES.md` and `README.md` still document `CC` as available/default. Issue #1 provides redacted manual evidence that the current selector is `CE`, `FB`, `NC`, `PB`, `RC`.
- Existing state compatibility matters: `tests/test_estado.py` verifies legacy state can contain `tipos_chequeados: ["RC", "NC", "CE", "CC"]`; this should remain readable.

### Affected Areas
- `suvalor/tipos.py` — source of supported names, defaults, and likely place for an explicit current-selector/legacy distinction.
- `suvalor/config.py` — generated config template and default config inherit `TIPOS_DEFAULT`.
- `suvalor/cli.py` — parses `--types`, prints validation errors/help, and can block unavailable types before Playwright.
- `suvalor/orquestador.py` / `suvalor/pagina.py` — downstream risk area; should ideally receive only selector-available types.
- `tests/test_sync_args.py` — best home for pure CLI parsing tests; no Playwright or network needed.
- `docs/SITE_NOTES.md` and `README.md` — user-facing/current-portal docs must stop advertising `CC` as default/current.
- Existing `_state/*.json` data — must remain compatible; do not migrate or reject historical `CC` inventory/state entries.

### Approaches
1. **Static current-selector allow-list with legacy compatibility** — Add a clear distinction such as current portal types (`CE`, `FB`, `NC`, `PB`, `RC`), safe defaults (`RC`, `NC`, `CE`), and legacy types (`CC`). Keep `CC` metadata, but remove it from defaults and prevent it from reaching the portal.
   - Pros: Pure, testable, minimal diff; preserves folders/inventory compatibility; avoids real portal commands; gives deterministic CLI feedback.
   - Cons: Requires docs to be kept current if the portal selector changes again; existing user configs containing `CC` need graceful handling.
   - Effort: Medium

2. **Runtime selector introspection** — After manual login, read actual `<select>` options and filter/validate requested types dynamically.
   - Pros: Most accurate against future portal changes; reduces hardcoded drift.
   - Cons: More invasive; validation happens after opening the real portal; harder to cover with existing pure tests; still needs static defaults and legacy compatibility.
   - Effort: High

3. **Remove `CC` completely** — Delete `CC` from enum/map/defaults/help/docs.
   - Pros: Simple conceptual alignment with the current selector.
   - Cons: Risks breaking historical inventory/state compatibility and folder naming; less safe for users with existing `CC` files/configs; contrary to “legacy safely”.
   - Effort: Low, but high compatibility risk

### Recommendation
Use **Approach 1**.

Implementation proposal for the next phase:
- Keep `CC` in `TipoDoc` and `NOMBRES_TIPOS` as legacy metadata only.
- Change `TIPOS_DEFAULT` to `['RC', 'NC', 'CE']`; keep `FB`/`PB` opt-in because documented 504 behavior remains.
- Introduce explicit constants for current selector availability and legacy/unavailable types, e.g. `TIPOS_PORTAL_ACTUALES = ['CE', 'FB', 'NC', 'PB', 'RC']` and `TIPOS_LEGACY = ['CC']`.
- Update `_parsear_tipos()` so legacy `CC` from default/config is omitted with a clear warning, while explicit `--types CC` (or mixed explicit lists containing `CC`) exits with code 2 and a clear message before Playwright starts.
- Add pure tests in `tests/test_sync_args.py`: default parsing excludes `CC`; legacy configured default is skipped or rejected according to the chosen spec; explicit `--types CC` fails before browser; valid active types still parse case-insensitively.
- Update CLI help, `README.md`, and `docs/SITE_NOTES.md` with the issue evidence and verification date. Do not run real portal commands.

### Risks
- Existing user `config.toml` may still contain `CC`; behavior must be explicit and non-surprising.
- Rejecting mixed explicit lists like `RC,CC` is safer but may be stricter than “omit with warning”; proposal/spec should choose one exact UX.
- Documentation must distinguish “known legacy folder/type” from “currently selectable in portal”.
- `FB`/`PB` are available in the selector but unsafe as defaults due to known 504 behavior; do not accidentally add them to defaults.
- No live portal verification was performed in this exploration; selector evidence comes from issue #1’s redacted manual inspection.

### Ready for Proposal
Yes — propose a small bug fix with strict TDD. Tell the user the recommended scope is a static availability/legacy distinction, not portal automation. Expected diff is well under the 400-line review budget and does not need chained PRs.

artifacts:
  - openspec/changes/fix-document-type-availability/exploration.md
next_recommended: Create proposal/spec for `fix-document-type-availability`, then implement with pure pytest RED/GREEN and full `uv run pytest` verification.
risks:
  - Need an explicit UX decision for explicit mixed legacy types (`RC,CC`): fail fast vs omit with warning.
  - Keep historical `CC` state/inventory compatibility intact.
