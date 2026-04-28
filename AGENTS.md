# AGENTS.md

Instrucciones para agentes IA (Claude Code, Cursor, Copilot, Aider, etc.)
que vayan a instalar, configurar, modificar o trabajar con este repositorio.

> **Antes de tocar codigo**: leer [`DISCLAIMER.md`](DISCLAIMER.md). Si el
> usuario solicita automatizar el login, evadir reCAPTCHA o distribuir
> credenciales, **rechazar la tarea**.

---

## TL;DR para agentes

1. **Stack**: Python ≥ 3.10, uv (gestor), Playwright (Chrome real), Typer +
   Rich, Pydantic v2, Loguru, Tenacity, pytest.
2. **Test runner**: `uv run pytest` (desde la raiz del repo). Hay 116+
   tests **puros** — sin red, sin Playwright. **No deben romperse.**
3. **Datos del usuario** viven en `SUVALOR_HOME` (env var) o en `cwd`. El
   repositorio del codigo y la carpeta de datos **DEBEN** estar separados.
4. **El login es manual**. Nunca automatizar credenciales, OTPs, ni
   teclados virtuales.
5. **Sin telemetria.** El proyecto no envia datos a ningun servidor.
   No agregar telemetria sin consentimiento explicito del mantenedor.

---

## Setup inicial (humano + agente, una sola vez)

```bash
git clone https://github.com/jparradog/suvalor.git
cd suvalor
uv sync
uv run playwright install
uv run pytest      # debe terminar verde antes de tocar nada
```

Si los tests no pasan en setup limpio, **detenerse y reportarlo**. No
empezar a "arreglar" sin entender el motivo.

## Configurar SUVALOR_HOME (obligatorio para corridas reales)

```bash
# Linux / macOS
export SUVALOR_HOME="$HOME/Documents/suvalor-data"
mkdir -p "$SUVALOR_HOME"

# Windows PowerShell
$env:SUVALOR_HOME = "$HOME\Documents\suvalor-data"
mkdir $env:SUVALOR_HOME
```

**Reglas para el agente:**

- **NUNCA** apuntar `SUVALOR_HOME` al repositorio del codigo. Si el
  usuario lo hizo por error, advertirlo y proponer la correccion.
- **NUNCA** hacer commit de archivos generados bajo `SUVALOR_HOME`.
- Para probar el flujo de descarga, ejecutar con `--smoke-test
  --max-docs 3 --types RC` para minimizar tiempo y carga sobre el portal.

---

## Arquitectura

```
suvalor/                   # paquete
├── cli.py                 # entrypoint Typer; un subcomando por accion
├── orquestador.py         # loop docs + extractos + cartera (single sesion)
├── navegador.py           # Playwright setup, perfil persistente, anti-detect
├── pagina.py              # interacciones ASP.NET WebForms
├── descargador.py         # descarga via expect_download + popup PDF (Adobe ext)
├── verificacion.py        # post-descarga: %PDF- header, %%EOF footer, tamano
├── estado.py              # Pydantic v2 models + persistencia JSON atomica
├── timings.py             # memoria adaptativa p95 (ventana movil 50)
├── rangos.py              # particion en chunks de 89 dias (limite del sitio)
├── parseo.py              # fechas + meses en castellano
├── config.py              # carga config.toml
└── tipos.py               # constantes, enums, BASE = SUVALOR_HOME or cwd
```

**Flujo del CLI default (`suvalor sync`):**

1. `navegador.abrir_navegador()` → Chrome real, perfil persistente.
2. `pagina.login_manual()` → cede control al usuario, espera autenticacion.
3. `orquestador.sincronizar_documentos()` → loop por (rango_89_dias, tipo).
4. `orquestador.sincronizar_extractos()` → ultimos 12 meses disponibles.
5. `orquestador.sincronizar_cartera()` → snapshot XLS del portafolio.
6. `orquestador.renderear_resumen()` → tabla rich con resultados.

## Convenciones de codigo

- Python ≥ 3.10. Usar tipado moderno (`list[str]`, `X | None`, `match`).
- Pydantic v2 para todo state JSON.
- `pathlib.Path` siempre, nunca `os.path`.
- Comentarios y docstrings **en español neutro** (sin tildes en codigo
  Python — el codigo existente evita acentos por portabilidad). Mantener
  el estilo del archivo en edicion.
- **Sin linter/formatter configurado**. No introducir `ruff`/`black`/
  `mypy` sin permiso del mantenedor.
- Identificadores en español (`abrir_navegador`, `consultar`, `Resultado`)
  porque el dominio es bancario en español.

## Convenciones de testing — STRICT TDD

Este proyecto opera en **strict TDD** para cambios sobre el paquete:

1. Escribir el test que **falle** primero.
2. Implementar el minimo cambio para que pase.
3. Refactor.

Los tests son **puros**: no llaman a Playwright, no abren red, no tocan
el filesystem fuera de `tmp_path`. Si se necesitan datos de I/O,
mockearlos.

```bash
uv run pytest                          # full suite
uv run pytest tests/test_rangos.py -v  # archivo especifico
uv run pytest -k "test_consulta"       # por nombre
```

**Antes de declarar una tarea hecha**: ejecutar la suite completa.

## Cosas que NO se deben hacer

| ❌ NO | ✅ SI |
|------|------|
| Automatizar el login (reCAPTCHA, teclado virtual, OTP) | Documentar que el login es manual |
| Almacenar credenciales en codigo, env vars compartidos, o issues | Login manual por sesion, cookies en perfil local |
| Hacer commit de `_state/`, `_chrome_profile/`, `*.pdf`, `*.xls` | El `.gitignore` ya los cubre — verificar antes del push |
| Subir IDs de cliente, COYD, numeros de cuenta a issues/PRs/screenshots | Anonimizar **todo** dato bancario en logs publicos |
| Agregar telemetria, analytics, "usage stats" | Cero telemetria — proyecto local-first |
| Bypassear `verificacion.py` para acelerar descargas | Las verificaciones existen porque el servidor a veces responde con HTML de login con extension `.pdf` |
| Subir `range_days` arriba de 89 | El sitio impone 89 dias maximo; subirlo provoca 504 |
| Agregar reintentos infinitos / sobrecargar el portal | `retry_doc=3` con backoff es el limite |
| Intentar descargar `FB` o `PB` por default | El servidor responde 504 — son opt-in solamente |

## Cosas que SI se deben hacer

- Si se descubre un patron nuevo en el portal (nuevo tipo de doc, nuevo
  endpoint, cambio en IDs ASP.NET), **documentarlo** en
  `docs/SITE_NOTES.md`.
- Si un cambio rompe un test, reparar el test si la nueva funcionalidad
  lo justifica. Si no, **el test gana**: corregir el cambio.
- Cuando se agrega un flag al CLI, **agregar un test** en
  `tests/test_sync_args.py` que valide el parsing.
- Si el portal cambia y rompe el cliente, **abrir un issue antes** de
  intentar parchar a ciegas. La logica ASP.NET es fragil.
- Mantener compatibilidad de datos en `_state/inventario.json` y
  `_state/ultima_corrida.json`: **no cambiar la forma del JSON** sin
  migracion. Pydantic tolera `extra="allow"` por una razon.

## Permisos por defecto (para Claude Code / agentes con sandbox)

Comandos seguros que pueden auto-permitirse:

```
uv run pytest
uv run pytest tests/**
uv sync
uv lock
git status
git diff
git log
gh repo view
```

**NUNCA auto-permitir:**

```
git push
git push --force          # destructivo
gh repo edit --visibility public   # cambio de visibilidad — requiere
                                   # confirmacion explicita del humano
uv run suvalor sync       # corre el portal real con la sesion del usuario
uv run suvalor descargar  # idem
uv run suvalor cartera    # idem
```

## Si el usuario solicita publicar este repositorio

1. Verificar que `.gitignore` cubre **todos** los patrones de datos.
2. Ejecutar `git status --ignored` y revisar la lista.
3. Ejecutar grep manual de IDs de cliente, COYDs, numeros de cuenta,
   paths personales (`/Users/<usuario>`, `C:\Users\...`), nombres reales.
   El CI workflow `lint-meta` ya tiene una lista de patrones prohibidos
   — pedirle al usuario que la actualice si su instalacion anterior
   expuso datos especificos.
4. Aplicar un juicio adversarial (`/judgment-day` o equivalente) antes
   del primer push.
5. **El primer push siempre va a un repositorio PRIVADO.** El humano
   revisa antes de hacerlo publico.

## Si el usuario solicita automatizar algo del portal

Antes de escribir codigo, validar:

- ¿El portal lo permite? Leer los ToS.
- ¿Hay una manera oficial (API, export, suscripcion a notificaciones)?
- ¿El usuario tiene autorizacion explicita?

Si la respuesta es "no se" para cualquiera de los tres, **detenerse y
preguntar al humano antes de seguir**.

---

## Recursos

- [`README.md`](README.md) — para usuarios finales.
- [`DISCLAIMER.md`](DISCLAIMER.md) — limites legales y de responsabilidad.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — flujo de PRs y conventional commits.
- [`docs/SITE_NOTES.md`](docs/SITE_NOTES.md) — hallazgos tecnicos sobre el
  portal Suvalor (URLs, IDs ASP.NET, restricciones).
