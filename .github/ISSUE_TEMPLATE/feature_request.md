---
name: Feature request
about: Proponer una mejora o un nuevo subcomando.
title: "[feat] "
labels: enhancement
assignees: ''
---

## Problema

Que problema resolveria esta feature? "Como usuario, quiero ... para ...".

## Solucion propuesta

Describi la feature. Si es un subcomando nuevo, mostralo en uso:

```bash
uv run suvalor <subcomando> --flag
```

## Alternativas consideradas

Otras formas de resolverlo y por que las descartaste.

## Compatibilidad

- [ ] No requiere automatizar login / captcha / OTP.
- [ ] No requiere subir `range_days` arriba de 89.
- [ ] No requiere telemetria ni servidores externos.
- [ ] Esta dentro del scope del [DISCLAIMER](../../DISCLAIMER.md).

## Impacto

- **Breaking**: ¿rompe usuarios existentes? Si es asi, ¿como migran?
- **Tests**: ¿se puede cubrir con tests puros (sin Playwright real)?
