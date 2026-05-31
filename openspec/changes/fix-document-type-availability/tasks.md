# Tasks: Fix Document Type Availability

## Phase 1: RED Tests (Strict TDD)

- [ ] 1.1 In `tests/test_sync_args.py`, add failing tests that `TIPOS_DEFAULT` and `Config().tipos_default` exclude `CC` and default to `RC,NC,CE` only.
- [ ] 1.2 In `tests/test_sync_args.py`, add failing tests that `TEMPLATE_TOML` and generated config init output exclude `CC` and show only safe defaults `RC,NC,CE`.
- [ ] 1.3 In `tests/test_sync_args.py`, add failing tests that `_parsear_tipos("CC", cfg)` and `_parsear_tipos("RC,CC", cfg)` raise `typer.Exit(2)` before any browser work.
- [ ] 1.4 In `tests/test_sync_args.py`, add failing tests that legacy configured defaults containing `CC` fail pre-browser, while `CE,FB,NC,PB,RC` parse successfully.
- [ ] 1.5 In `tests/test_sync_args.py`, add failing `recuperar-fallidos` all-`CC` coverage asserting no `Config.cargar()`, `MemoriaTimings()`, `abrir_navegador()`, `login_manual()`, or `setear_filtros()`.
- [ ] 1.6 RED: In `tests/test_sync_args.py`, add failing pure pytest coverage for mixed `fallos.tsv` rows (`CC` plus current type): skip `CC`, process only current rows, and never call `setear_filtros()` with `CC`.
- [ ] 1.7 In `tests/test_estado.py`, keep or add coverage proving historical `tipos_chequeados=[..., "CC"]` remains readable.

## Phase 2: Foundation / Availability Model

- [ ] 2.1 In `suvalor/tipos.py`, add current selector and legacy constants: current `CE,FB,NC,PB,RC`; legacy `CC`.
- [ ] 2.2 In `suvalor/tipos.py`, change `TIPOS_DEFAULT` to `RC,NC,CE`, keeping `CC` in `TipoDoc` and `NOMBRES_TIPOS` for metadata compatibility.
- [ ] 2.3 In `suvalor/config.py`, update `TEMPLATE_TOML`, generated config output, and `Config.tipos_default` so default config never includes `CC`.

## Phase 3: GREEN Implementation / CLI Gates

- [ ] 3.1 In `suvalor/cli.py`, update imports/help for `descargar` and `sync`: advertise defaults `RC,NC,CE` plus opt-in `FB,PB`; do not advertise `CC`.
- [ ] 3.2 In `suvalor/cli.py::_parsear_tipos()`, reject any resolved query list containing legacy/unavailable types with exit code 2 and a message listing current selector values.
- [ ] 3.3 In `suvalor/cli.py::recuperar_fallidos()`, partition pending failures before config/timings/browser startup; skip/report legacy `CC` rows and return immediately when no retryable rows remain.
- [ ] 3.4 Ensure `suvalor/orquestador.py` and `suvalor/pagina.py` need no behavioral change because entrypoints now pass only current selector types.

## Phase 4: Docs and Verification

- [ ] 4.1 Update `README.md` to document current selector types, safe defaults `RC,NC,CE`, opt-in `FB/PB`, legacy-only `CC`, and retry skip behavior.
- [ ] 4.2 Update `docs/SITE_NOTES.md` with issue #1 selector evidence and the no-login/no-live-probing boundary.
- [ ] 4.3 REFACTOR: centralize repeated current/legacy error wording without changing behavior; keep comments/docstrings in existing Spanish style.
- [ ] 4.4 Run `uv run pytest tests/test_sync_args.py tests/test_estado.py -v`, then full `uv run pytest`; do not run real portal commands.

## Review Workload Forecast

Expected diff: ~170-270 changed lines. Single PR is appropriate.
Decision needed before apply: No
Chained PRs recommended: No
400-line budget risk: Low
