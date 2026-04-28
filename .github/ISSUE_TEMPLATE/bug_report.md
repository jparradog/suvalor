---
name: Bug report
about: Reportar un bug del cliente. NO uses esta plantilla para vulnerabilidades de seguridad.
title: "[bug] "
labels: bug
assignees: ''
---

## ⚠️ Antes de enviar

- [ ] Lei el [DISCLAIMER](../../DISCLAIMER.md) y entiendo los limites del proyecto.
- [ ] **Redacte cualquier dato personal** de logs / screenshots / outputs:
      numeros de cliente, COYDs, numeros de cuenta, nombres reales, IDs de
      documento. En caso de duda, no subir el archivo.
- [ ] Busque issues existentes y no encontre duplicados.
- [ ] No es un bug del PORTAL (eso debe reportarse al banco), es un bug
      del CLIENTE.

## Descripcion

Describir el bug en una o dos lineas.

## Pasos para reproducir

1. ...
2. ...
3. ...

Ideal: usar `--smoke-test --max-docs 1 --types RC` para minimizar ruido.

## Comportamiento esperado

Que se esperaba que ocurriera.

## Comportamiento real

Que ocurrio (con stacktrace si lo hay).

```
<paste stacktrace REDACTADO aqui>
```

## Entorno

- **Version**: `uv run suvalor --version` =
- **Python**: `python --version` =
- **SO**: Windows 11 / macOS 14 / Linux X
- **Chrome version**:
- **Modo**: `sync` / `descargar` / `extractos` / `cartera` / otro
- **`SUVALOR_HOME`**: (no subir el path absoluto si contiene el nombre
  real del usuario)

## Logs

Si se tiene `_state/run.log`, **redactar** los datos personales y pegar
un fragmento relevante. **No** subir el archivo completo.

```
<log REDACTADO>
```

## Contexto adicional

Cualquier informacion extra (¿el portal cambio recientemente?, ¿se probo
con otro navegador?, ¿una version anterior funcionaba?).
