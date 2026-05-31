status: completed
executive_summary: >
  Explored GitHub issue #6 for `investigate-retefuente-certificate`. The repo has safe manual-login Playwright download patterns for documents, extractos, and cartera, but no ReteFuente support or documented endpoint today. Issue evidence says `operaciones/reteFuente.aspx` loads and exposes `ddlAnioRetencion` / `btnDescargarPDF`, but the probe click produced no download or popup. Recommended scope is an investigation-only OpenSpec change: document the endpoint, no-goals, selector/network evidence required before automation, and future CLI acceptance criteria. Do not add a runtime command, feature flag, or sync stage until a human provides redacted proof of a reliable PDF response.
skill_resolution: none

## Exploration: investigate-retefuente-certificate

### Current State
- The project is a local, unofficial CLI that opens real Chrome, requires `login_manual()`, and only automates after the user is authenticated. `AGENTS.md`, `DISCLAIMER.md`, and `CONTRIBUTING.md` prohibit credential, captcha, OTP, virtual-keyboard, and telemetry changes.
- `suvalor/cli.py` exposes `sync`, `descargar`, `extractos`, `cartera`, `inventario`, `reset`, `recuperar-fallidos`, `config`, and `timings`. There is no `retefuente`, `certificados`, or experimental certificate command.
- `suvalor/orquestador.py` has reusable authenticated-page flows for documents, extractos, and cartera. `sincronizar_cartera()` is the closest pattern for a future simple report download: navigate, optional account selection, click export, `expect_download`, save deterministic path, verify.
- `suvalor/descargador.py` handles document-grid postbacks and includes a popup/PDF inline fallback for `VerDocumentoElectronico`. That helper is document-specific and should not be reused blindly for ReteFuente without evidence of the same behavior.
- `suvalor/verificacion.py` already has pure PDF validation (`%PDF-`, `%%EOF`, minimum size) and XLS-HTML validation. A future ReteFuente certificate PDF can likely reuse `verificar_descarga(path, "pdf")` unless evidence shows very small valid PDFs.
- `suvalor/tipos.py` centralizes URLs, output directories, temp filenames, and ASP.NET IDs. No constants exist for `operaciones/reteFuente.aspx`, `ddlAnioRetencion`, or `btnDescargarPDF`.
- `docs/SITE_NOTES.md` documents known portal flows and unimplemented endpoints, but does not mention ReteFuente. It says new portal patterns must be documented with redacted evidence and no personal identifiers.
- Existing tests are pure pytest tests for state compatibility, extractos inventory, parsing, ranges, timings, verification, and CLI help/planning. No tests use Playwright or the real portal.
- Issue #6 reports: ReteFuente page exists, initial probe click did not produce a download/popup, proposed future command may be `uv run suvalor retefuente --year latest`, output could be `Certificados/ReteFuente/`, and GMF is explicitly out of scope because it redirected to `mensajes.aspx?id=000-01`.

### Affected Areas
- `docs/SITE_NOTES.md` — immediate target for an investigation-only note: endpoint, observed controls, failed probe result, required evidence, and GMF no-goal.
- `openspec/changes/investigate-retefuente-certificate/` — proposal/spec/design/tasks should encode the gate: documentation/manual investigation first; no automation until evidence exists.
- `suvalor/tipos.py` — future-only target for `RETEFUENTE_URL`, output dir, temp filename, and selector constants once confirmed.
- `suvalor/cli.py` — future-only target for an opt-in `retefuente` command. It should not be added to default `sync`; a feature flag is not useful before a reliable download path exists.
- `suvalor/orquestador.py` — future-only target for `ResumenReteFuente` and `sincronizar_retefuente(page, ...)` after selector/network evidence is sufficient.
- `suvalor/descargador.py` — future-only target for a generic click-to-download helper if evidence shows `btnDescargarPDF` emits a download or popup.
- `suvalor/verificacion.py` — likely reuse existing PDF validation; adjust only with redacted evidence and pure tests if valid certificates are below current size threshold.
- `tests/test_sync_args.py` or new `tests/test_retefuente_args.py` — future pure CLI tests if a command is approved.
- `tests/test_verificacion.py` — future pure tests for valid/invalid certificate PDFs only if validation changes.
- `README.md` — update only when user-facing runtime support exists; for investigation-only scope, prefer `docs/SITE_NOTES.md`.

### Approaches
1. **Investigation-only documentation gate** — Do not add runtime code. Record known endpoint/controls, the no-download probe result, GMF exclusion, privacy/safety constraints, and the exact redacted evidence required before any automation.
   - Pros: Safest; matches issue wording; no portal load by agents; no false user promise; minimal review burden; keeps strict legal/manual-login boundary intact.
   - Cons: Does not yet let users download certificates from the CLI; requires a human/manual probe follow-up.
   - Effort: Low

2. **Experimental opt-in CLI stub** — Add a hidden or explicit `retefuente` command behind an experimental flag that navigates to the page and reports unsupported/no-op states until evidence exists.
   - Pros: Creates a future command shape early; can encode no-op/error semantics in tests.
   - Cons: Runtime code without reliable portal behavior invites confusion; any navigation command requires real portal use by users; a flag does not solve missing download evidence; larger diff than needed.
   - Effort: Medium

3. **Full ReteFuente automation now** — Implement `retefuente --year latest|YYYY`, click `btnDescargarPDF`, expect a PDF, verify, and save under `Certificados/ReteFuente/`.
   - Pros: Delivers the desired feature if the portal behavior is actually understood.
   - Cons: Not justified by current evidence; initial probe produced no download/popup; high risk of marking no-op/error pages as success or overfitting unknown ASP.NET behavior.
   - Effort: Medium/High

### Recommendation
Use **Approach 1: Investigation-only documentation gate** for this change.

Proposal guidance:
- **No CLI command, no feature flag, and no default `sync` integration in the first PR.** A hidden experimental command would still imply supported behavior while evidence is absent.
- Add/adjust docs to state that `operaciones/reteFuente.aspx` is known but unsupported, with observed controls `ddlAnioRetencion` and `btnDescargarPDF`, and that a click probe produced no download/popup.
- Keep GMF out of scope and document the observed unavailability redirect separately if needed.
- Define evidence required before future implementation:
  - redacted URL after navigation and whether it stays on `operaciones/reteFuente.aspx` or redirects;
  - full redacted HTML snippets or selector metadata for `ddlAnioRetencion`, `btnDescargarPDF`, and any status/error containers;
  - dropdown year options and behavior for years with/without certificates;
  - DevTools Network capture after clicking download: request URL, method, status, content-type, content-disposition, response size, and whether bytes start with `%PDF-` or an HTML/error page;
  - whether the browser emits a Playwright `download`, opens a popup/tab, performs form postback in-place, or silently renders a message;
  - redacted no-certificate message text and session-expired/login redirect behavior.
- Future CLI stance, once evidence exists: add a separate opt-in `suvalor retefuente --year latest|YYYY` command, never part of default `sync` initially. Save deterministic files under `Certificados/ReteFuente/`, avoid account/customer identifiers in names/logs, and use existing manual-login flow.
- Future failure/no-op behavior: distinguish `SIN_CERTIFICADO` (successful no-op, clear user message, no file), `SKIP` (valid destination already exists), `NUEVO` (downloaded and verified PDF), and `FAIL` (technical failure/session/download/verification error; exit code aligned with existing code 3 patterns).
- Future tests must remain pure: CLI help/argument parsing, year resolution, destination path building, no-op status classification from mocked page snippets, and PDF verification decisions. No Playwright or real portal commands by agents.

### Risks
- Implementing before network evidence could create a command that always no-ops or misclassifies portal errors as missing certificates.
- ReteFuente may use a form postback, inline PDF, disabled button, status message, or account/year-specific authorization path not covered by existing helpers.
- The current PDF validator may reject a valid but small certificate unless real file evidence proves a lower threshold is needed.
- Logging dropdown/account labels or screenshots without redaction could expose financial/personal data.
- Adding ReteFuente to default `sync` would increase portal load and surprise users with sensitive outputs.
- Agents must not run real portal commands; only humans with their own authenticated session should collect evidence.

### Ready for Proposal
Yes — propose a bounded investigation/documentation change first. Tell the user that automation should wait until redacted selector + network evidence proves `btnDescargarPDF` reliably returns a verifiable PDF and defines the no-certificate state.

artifacts:
  - openspec/changes/investigate-retefuente-certificate/exploration.md
next_recommended: Create proposal/spec/design/tasks for `investigate-retefuente-certificate` scoped to documentation and evidence gates only; defer runtime CLI implementation until the gate is satisfied.
risks:
  - Missing selector/network evidence for a reliable PDF response.
  - Possible confusion if a CLI flag/stub is introduced before support exists.
  - Privacy risk from unredacted portal evidence.
