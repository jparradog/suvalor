# Document Type Availability Specification

## Purpose

Define which document types may be planned for new portal queries while preserving readability of legacy local state from older runs.

## Requirements

### Requirement: Current Query Type Set

The system MUST plan new portal document queries only for current selector types `CE`, `FB`, `NC`, `PB`, and `RC`. Default query lists SHALL be the safe subset `RC`, `NC`, `CE`; `FB` and `PB` MAY be requested explicitly.

#### Scenario: Safe default query list

- GIVEN no `--types` argument and no user config override
- WHEN the command resolves document types for a new query
- THEN the resolved list SHALL be exactly `RC`, `NC`, `CE`
- AND it MUST NOT include legacy type `CC`

#### Scenario: Current opt-in types

- GIVEN the user requests `CE,FB,NC,PB,RC`
- WHEN the command resolves document types for a new query
- THEN all requested current selector types SHALL be accepted

### Requirement: Legacy Defaults Fail Fast

The system MUST reject any resolved default or configured query list containing legacy or unavailable type `CC` before browser startup. It MUST give clear guidance to remove `CC` from config or pass current selector types, and MUST NOT silently drop `CC` or run a partial query.

#### Scenario: Existing config contains CC

- GIVEN an existing `config.toml` or `Config.tipos_default` contains `RC,NC,CE,CC`
- WHEN `sync` or `descargar` resolves types without an overriding current-only list
- THEN the command MUST fail before browser startup
- AND the message SHALL identify `CC` as unavailable and list current selector types

#### Scenario: Mixed explicit request contains CC

- GIVEN the user requests `RC,CC`
- WHEN the command resolves document types
- THEN the command MUST fail before browser startup
- AND it MUST NOT query `RC` as a partial success

### Requirement: Recover Failed Rows Safely

The `recuperar-fallidos` flow MUST NOT start a browser or perform portal filter-setting for pending rows whose type is legacy or unavailable (`CC`). It SHALL report or mark those rows as skipped without treating them as retryable portal work.

#### Scenario: Only CC failures pending

- GIVEN the pending failures file contains only rows with `tipo=CC`
- WHEN `recuperar-fallidos` runs
- THEN no browser SHALL be opened
- AND no `setear_filtros` action SHALL be attempted
- AND the rows SHALL be reported or marked as safely skipped

#### Scenario: Mixed pending failures

- GIVEN pending failures include `tipo=CC` and `tipo=RC`
- WHEN `recuperar-fallidos` prepares retries
- THEN `CC` rows SHALL be skipped before browser startup decisions
- AND only current selector rows MAY proceed to portal retry work

### Requirement: Legacy State Readability

The system MUST keep historical state, inventory, and local metadata containing `CC` readable. Legacy stored values SHALL NOT be interpreted as permission to plan new portal queries.

#### Scenario: Historical state contains CC

- GIVEN stored state includes `tipos_chequeados` or inventory entries with `CC`
- WHEN the system reads that state for reporting or compatibility
- THEN the state SHALL load without migration or deletion
- AND no new query plan SHALL be created for `CC`

### Requirement: Documentation and Test Evidence

README.md and docs/SITE_NOTES.md MUST document current selector types, safe defaults, FB/PB opt-in behavior, legacy `CC`, and `recuperar-fallidos` skip behavior. Verification MUST use pure pytest coverage for all specified behaviors without real browser, network, or portal access.

#### Scenario: User documentation states availability policy

- GIVEN README.md and docs/SITE_NOTES.md are reviewed
- WHEN document type availability guidance is checked
- THEN both documents SHALL describe current selector types, defaults `RC,NC,CE`, FB/PB opt-in, legacy `CC`, and recovery skip behavior

#### Scenario: Pure pytest verification covers policy

- GIVEN the pure pytest suite is run
- WHEN document type availability behavior is verified
- THEN tests MUST cover defaults, TEMPLATE_TOML/generated config, configured `CC` fail-fast, explicit/mixed `CC` rejection, all-CC recovery skip without Config/Memoria/browser path, mixed recovery, and legacy state readability
