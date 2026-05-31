# Proposal: Investigate ReteFuente Certificate

## Intent

Investigate issue #6 safely by documenting the known ReteFuente endpoint and the evidence required before any certificate automation. Current evidence shows `operaciones/reteFuente.aspx` with `ddlAnioRetencion` / `btnDescargarPDF`, but the initial click produced no download or popup.

## Scope

### In Scope
- Add investigation/evidence guidance for ReteFuente to `docs/SITE_NOTES.md`.
- Encode gates for future implementation: redacted selectors, network response, PDF bytes, no-certificate state, and session-expired behavior.
- Forecast future pure tests/CLI shape without adding runtime code.

### Out of Scope
- No `suvalor retefuente` command, feature flag, or default `sync` integration.
- No credential, OTP, captcha, virtual-keyboard, or manual-login automation.
- No GMF support; observed redirect to `mensajes.aspx?id=000-01` stays out of scope.

## Approach

Use an investigation/documentation-only change. Document observed controls, failed probe result, privacy rules, and required redacted evidence. Future automation may use a separate opt-in command only after `btnDescargarPDF` is proven to return a verifiable PDF or a classified no-certificate state.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `docs/SITE_NOTES.md` | Modified | Add ReteFuente endpoint, controls, evidence gates, and GMF no-goal. |
| `openspec/changes/investigate-retefuente-certificate/` | Modified | Capture proposal/spec/tasks for investigation-first scope. |
| `suvalor/cli.py`, `suvalor/orquestador.py`, `suvalor/tipos.py`, `suvalor/descargador.py` | Deferred | Future-only; no code in this change. |
| `tests/` | Deferred | Future pure tests only if runtime support is approved. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Premature automation misclassifies portal errors. | High | Keep this PR docs-only. |
| Sensitive portal evidence leaks. | Medium | Require redaction; no screenshots/IDs in repo. |
| Future PDF validation rejects small certificates. | Low | Adjust only with redacted real-file evidence and pure tests. |

## Rollback Plan

Revert the OpenSpec change and the `docs/SITE_NOTES.md` ReteFuente section. No package code, state files, or user data should change.

## Dependencies

- Human-provided, redacted selector and DevTools Network evidence from an authenticated manual session.

## Success Criteria

- [ ] ReteFuente is documented as known but unsupported.
- [ ] Evidence gates and non-goals are explicit.
- [ ] Forecast: one docs/spec PR, low risk, no real portal commands, expected diff under 100 lines.
