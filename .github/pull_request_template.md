<!--
Antes de abrir el PR:
- Lei DISCLAIMER.md y CONTRIBUTING.md.
- Mis commits siguen Conventional Commits (ver .gitmessage).
- NO incluyo datos personales (numeros de cliente, COYDs, cuentas, nombres).
-->

## Descripcion

Que cambia y **por que** (no que — el diff lo muestra).

## Tipo de cambio

- [ ] `feat` — funcionalidad nueva
- [ ] `fix` — bug fix
- [ ] `docs` — solo documentacion
- [ ] `refactor` — cambio interno sin alterar comportamiento
- [ ] `test` — agregar o ajustar tests
- [ ] `chore` — mantenimiento (deps, CI, gitignore)
- [ ] `perf` — performance
- [ ] `build` — build system
- [ ] `ci` — CI/CD
- [ ] `style` — formato

## Issue relacionado

Closes #<numero>

## Como se probo

- [ ] `uv run pytest` (toda la suite verde)
- [ ] Smoke test contra el portal real:
  - Comando exacto: `uv run suvalor ...`
  - Resultado: ...
- [ ] No aplica (cambio solo de docs)

## Checklist

- [ ] Mi codigo sigue las convenciones existentes (estilo, identifiers en
      español, sin tildes en codigo Python, Pydantic v2, pathlib).
- [ ] Agregué/actualicé tests cuando aplica.
- [ ] Actualicé `CHANGELOG.md` si es un cambio user-facing.
- [ ] Actualicé `docs/SITE_NOTES.md` si descubrí cambios en el portal.
- [ ] **Verifiqué que el diff no incluye datos personales** (busqué con
      grep IDs propios, paths de mi maquina, nombres reales).
- [ ] No introduzco telemetria ni servicios externos.
- [ ] No automatizo login, captcha ni OTP.

## Notas para el reviewer

Cualquier punto que merezca atencion especial.
