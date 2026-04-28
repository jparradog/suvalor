# Contribuir a suvalor

Gracias por su interes. Antes de abrir un PR, por favor revisar estos
puntos.

## Antes que nada

1. Leer [`DISCLAIMER.md`](DISCLAIMER.md). Si su contenido no convence,
   este no es el proyecto donde se quiere contribuir.
2. Leer [`AGENTS.md`](AGENTS.md) si se va a usar un agente IA para
   trabajar (Claude Code, Cursor, Copilot, Aider, etc.).

## Que se acepta

- **Bug fixes**: ideal con test que reproduzca el bug.
- **Mejoras de resiliencia**: timeouts, reintentos, deteccion de edge
  cases del portal.
- **Nuevos subcomandos** que automaticen flujos del portal **dentro de
  los limites del DISCLAIMER**.
- **Documentacion**: hallazgos tecnicos, ejemplos, traducciones.
- **Tests**: siempre bienvenidos. La cobertura nunca es suficiente.

## Que NO se acepta

- Codigo que automatice login, evada captcha/OTP/teclado virtual.
- Telemetria, analytics, "usage stats" de cualquier tipo.
- Funcionalidad que requiera enviar credenciales o cookies a servidores
  de terceros.
- Datos personales en commits, issues o PRs (numeros de cliente, COYD,
  numeros de cuenta, nombres reales, screenshots sin redactar).
- Subir `range_days` arriba de 89 (limite duro del portal).
- Reintentos agresivos que puedan ser interpretados como abuso por el
  portal.

## Setup de dev environment

```bash
# 1. Clonar el fork
git clone https://github.com/<usuario>/suvalor.git
cd suvalor

# 2. Instalar deps (incluye dev: pytest)
uv sync --extra dev

# 3. Instalar el driver de Playwright (necesario solo para corridas reales,
#    NO para tests — los tests son puros)
uv run playwright install

# 4. Activar template de commit (conventional commits)
git config commit.template .gitmessage

# 5. Verificar que la suite pase en limpio antes de empezar
uv run pytest
```

Prerequisitos del SO:

- **Python ≥ 3.10**
- **Google Chrome** instalado (solo si se va a probar el flujo end-to-end
  contra el portal real; los tests no lo requieren).
- **uv** ≥ 0.4.x.

> **Importante**: no se debe configurar `SUVALOR_HOME` apuntando al
> repositorio del codigo. Los tests configuran su propio `SUVALOR_HOME`
> temporal via `conftest.py`.

## Flujo de trabajo

1. **Issue antes de PR** para cambios no triviales. Para typos o un par
   de lineas, se puede ir directo al PR.
2. **Fork + branch**: nombrar el branch con prefijo conventional
   (`feat/...`, `fix/...`, `docs/...`).
3. **Tests pasando**: `uv run pytest` debe terminar verde **antes** de
   abrir el PR.
4. **Conventional commits** en todos los commits del branch.
5. **PR description**: que cambia, por que, como se probo. Si se modifica
   el flujo de descarga, indicar con que `--smoke-test` se verifico.

## Conventional commits

Formato:

```
<tipo>(<scope opcional>): <descripcion corta en imperativo>

<cuerpo opcional explicando el "por que">

<footer opcional, ej. "Closes #42">
```

Tipos:

| Tipo | Cuando usar |
|---|---|
| `feat` | Funcionalidad nueva visible para el usuario. |
| `fix` | Bug fix. |
| `docs` | Solo documentacion. |
| `refactor` | Cambio interno sin alterar comportamiento. |
| `test` | Agregar o ajustar tests. |
| `chore` | Tareas de mantenimiento (deps, CI, gitignore). |
| `perf` | Mejora de performance. |
| `build` | Cambios al sistema de build (pyproject, hatch). |
| `ci` | Cambios a pipelines de CI. |
| `style` | Formato (sin cambio funcional). |

Ejemplos:

```
feat(extractos): agregar flag --solo YYYY-MM
fix(verificacion): aceptar PDFs con whitespace despues de %%EOF
docs(readme): clarificar SUVALOR_HOME en Windows
refactor(timings): extraer percentil_p95 a helper puro
test(rangos): cubrir caso de rango vacio
chore(gitignore): ignorar .ruff_cache
```

Para configurar el template localmente:

```bash
git config commit.template .gitmessage
```

## Tests

```bash
# Toda la suite (rapido — son puros)
uv run pytest

# Un archivo
uv run pytest tests/test_rangos.py -v

# Por nombre
uv run pytest -k "test_consulta"
```

**Reglas para tests nuevos**:

- Puros: sin red, sin Playwright real, sin filesystem fuera de `tmp_path`.
- Si se necesita mockear Playwright, usar dataclasses simples; no
  depender de la API real (es heavy).
- Nombres en español: `test_<modulo>_<comportamiento>`.
- Ubicacion: `tests/test_<modulo>.py`.

## Reportar bugs

Antes de abrir un issue:

1. Reproducirlo con `--smoke-test --max-docs 1` para minimizar ruido.
2. Capturar `_state/run.log` filtrando datos personales (IDs de cliente,
   nombres, numeros de doc).
3. Indicar version: `uv run suvalor --version`.
4. Indicar fecha del intento (porque el portal cambia).

**No subir screenshots ni logs sin redactar datos personales.**

## Reportar vulnerabilidades

Si se encuentra una vulnerabilidad (especialmente algo que pueda exponer
credenciales del usuario), **no abrir un issue publico**. Contactar al
mantenedor por canal privado primero (GitHub: `@jparradog`).

## Codigo de conducta

Trato respetuoso. Sin agresiones personales, sin tribalismo de
herramientas, sin gatekeeping. Las criticas tecnicas son bienvenidas; los
ataques no.

## Licencia de las contribuciones

Al abrir un PR, el contribuyente acepta que su contribucion se licencia
bajo la **Apache License 2.0** (ver [`LICENSE`](LICENSE)).
