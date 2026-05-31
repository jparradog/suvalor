# Design: Investigate ReteFuente Certificate

## Technical Approach

This is a documentation/SDD-only investigation guardrail. The approved approach maps directly to the proposal and `retefuente-certificate` spec: record the known ReteFuente portal observations in `docs/SITE_NOTES.md`, add pure documentation tests, and explicitly prevent runtime automation until redacted evidence proves the download/no-certificate/session-expired behavior.

No package code is added. Existing CLI, sync, downloader, constants, state, and verification modules remain unchanged.

## Architecture Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| Scope boundary | Keep ReteFuente investigation-only and unsupported | Add `suvalor retefuente`, hidden flag, or `sync` integration | Current evidence shows `operaciones/reteFuente.aspx` and controls, but `btnDescargarPDF` produced no download or popup. Runtime code would imply support without a verified contract. |
| Evidence location | Record endpoint, controls, probe result, privacy rules, GMF non-goal, and future gate in `docs/SITE_NOTES.md` | Put evidence in README, package comments, or fixtures | `SITE_NOTES.md` is the existing repository pattern for fragile portal behavior and maintenance notes. It also keeps user docs free of unsupported feature promises. |
| Tests | Add pure pytest checks over documentation text only | Playwright/browser tests, network probes, or committed portal artifacts | Project tests must be pure and privacy-preserving. Agents must not run real portal commands or store sensitive portal evidence. |
| Future automation gate | Require redacted selectors/network/PDF evidence or classified no-certificate/session-expired evidence before a new change | Infer behavior from existing document/cartera download helpers | Existing helpers are flow-specific. Reusing them blindly risks misclassifying HTML/login/error pages as successful certificate outcomes. |

## Data Flow

No runtime data flow is introduced in this change.

Documentation flow only:

```text
Issue evidence + approved SDD scope
        -> tests/test_site_notes_retefuente.py
        -> docs/SITE_NOTES.md ReteFuente section
        -> future approved automation decision
```

Future automation, if approved later, must be a separate opt-in flow after manual login and must not enter default `sync` until separately justified.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `openspec/changes/investigate-retefuente-certificate/design.md` | Create | Restores the approved docs-only technical design artifact. |
| `docs/SITE_NOTES.md` | Modify | Add ReteFuente investigation section: endpoint, `ddlAnioRetencion`, `btnDescargarPDF`, no-download/no-popup probe, redaction/privacy rules, GMF non-goal, and evidence gate. |
| `tests/test_site_notes_retefuente.py` | Create | Pure pytest documentation checks proving the SITE_NOTES section contains the approved guardrails. |
| `suvalor/cli.py` | No change | No `suvalor retefuente` command in this change. |
| `suvalor/orquestador.py` | No change | No sync/default integration. |
| `suvalor/descargador.py` | No change | No download workflow or helper reuse. |
| `suvalor/tipos.py` | No change | No ReteFuente URL, selector, or output constants. |

## Interfaces / Contracts

Current contract is documentation-only:

```text
ReteFuente status: known portal endpoint, unsupported by the CLI.
Future evidence gate: redacted selectors + network metadata + PDF bytes
OR classified no-certificate state + session-expired behavior.
Privacy contract: no client IDs, COYDs, account numbers, names, credentials,
OTP, captcha, virtual-keyboard data, screenshots, raw portal artifacts, or
personal local paths in repo artifacts.
```

No public API, CLI option, state schema, file naming contract, or downloader interface is introduced.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | SITE_NOTES contains unsupported status, endpoint, controls, failed probe, evidence gate, privacy rules, session-expired rule, and GMF non-goal | Pure pytest reading repository markdown. |
| Integration | Existing package behavior remains unchanged | Full `uv run pytest`; no Playwright, no network, no real portal commands. |
| E2E | Future ReteFuente automation behavior | Deferred until approved evidence exists; human-collected redacted evidence only. |

## Migration / Rollout

No migration required. Rollout is a docs/test-only PR. Revert by removing the ReteFuente SITE_NOTES section, its pure documentation tests, and this OpenSpec change.

## Open Questions

None for this docs-only design. Future automation remains blocked until the evidence gate is satisfied.
