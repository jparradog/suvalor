# suvalor

> Cliente **no oficial** y de linea de comandos para descargar, de forma
> incremental y reproducible, **documentacion contable propia** desde el
> portal Suvalor / Cibest Capital (Valores Bancolombia) en `suvalor.com`.

[![CI](https://github.com/jparradog/suvalor/actions/workflows/ci.yml/badge.svg)](https://github.com/jparradog/suvalor/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](pyproject.toml)
[![Disclaimer](https://img.shields.io/badge/⚠️-DISCLAIMER-red)](DISCLAIMER.md)

> ⚠️ **LEA [DISCLAIMER.md](DISCLAIMER.md) ANTES DE USAR ESTE CLIENTE.**
> Esto es software no oficial. **No estoy afiliado a Bancolombia, Valores
> Bancolombia, Cibest Capital ni Suvalor.** Usar este cliente puede violar
> los terminos del portal y derivar en sancion sobre la cuenta del usuario.
> **Se usa bajo riesgo y responsabilidad propios.**

---

## Que hace

Automatiza la descarga de:

- **Documentos contables** (Recibos de Caja, Notas Contables, Comprobantes
  de Egreso, Certificados de Custodia, etc.) por rangos de fecha, con
  inventario incremental: solo descarga lo que falta.
- **Extractos consolidados mensuales** (PDF) — los ultimos 12 meses
  disponibles.
- **Snapshot del portafolio** consolidado (XLS).

Todo en una sola sesion de Playwright + un solo login manual.

## Que NO hace

- **No automatiza el login.** El portal usa un teclado virtual que cambia de
  posicion + reCAPTCHA. El cliente abre el navegador y cede el control al
  usuario; el usuario autentica manualmente y el cliente toma el control
  despues.
- **No evade reCAPTCHA, OTP ni 2FA.**
- **No envia ni almacena credenciales.** Las cookies viven en el perfil
  persistente de Chrome local (`_chrome_profile/`), nunca abandonan el
  equipo del usuario.

## Por que existe

Porque sacar 80+ documentos contables a mano tipeando rangos de 89 dias en
un formulario ASP.NET es tortura. Si el portal ofreciera una API, esto no
seria necesario.

---

## Requisitos

- **Python ≥ 3.10**
- **[uv](https://github.com/astral-sh/uv)** (recomendado) o `pip`.
- **Google Chrome instalado** en el sistema. El cliente usa Chrome real
  (no Chromium) porque reCAPTCHA bloquea Chromium controlado.

Para instalar uv:

```bash
# Windows
winget install --id=astral-sh.uv -e

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Instalacion

```bash
git clone https://github.com/jparradog/suvalor.git
cd suvalor
uv sync
uv run playwright install
```

## Migracion desde 0.2.x

Si se venia usando una version anterior con layout `_script/suvalor/`
dentro de la carpeta de datos, ver [`CHANGELOG.md`](CHANGELOG.md) para la
guia paso a paso de migracion.

## Configuracion: SUVALOR_HOME

`suvalor` necesita un **directorio de datos** donde escribir:

- Inventarios JSON (`_state/`)
- Perfil persistente de Chrome (`_chrome_profile/`)
- Carpetas de salida (`2024/`, `2025/`, `Extractos/`, `Cartera/`, ...)
- Logs (`_state/run.log`)

**Por seguridad, este directorio debe ser distinto del repositorio del
codigo.**

Hay dos formas de indicarlo:

### Opcion A: variable de entorno (recomendado)

```bash
# Linux / macOS
export SUVALOR_HOME=~/Documents/suvalor-data
mkdir -p "$SUVALOR_HOME"

# Windows PowerShell
$env:SUVALOR_HOME = "$HOME\Documents\suvalor-data"
mkdir $env:SUVALOR_HOME

# Windows CMD
set SUVALOR_HOME=%USERPROFILE%\Documents\suvalor-data
mkdir %SUVALOR_HOME%
```

### Opcion B: cwd al invocar

Si `SUVALOR_HOME` no esta definida, el cliente usa el **directorio activo
desde el que se invoca el comando**:

```bash
cd ~/Documents/suvalor-data
uv run --directory /path/to/suvalor-repo suvalor sync
```

> ⚠️ **No** se debe apuntar `SUVALOR_HOME` al repositorio del codigo. El
> `.gitignore` protege contra accidentes, pero la mejor proteccion es la
> separacion fisica.

---

## Uso

Todos los ejemplos asumen que `SUVALOR_HOME` apunta a la carpeta de datos.

### Sincronizar todo (default)

```bash
uv run suvalor              # equivalente a `uv run suvalor sync`
uv run suvalor sync
```

`sync` ejecuta **docs + extractos + cartera en una sola sesion** con un
solo login manual. Imprime una tabla rich con el resumen al final.

Si una etapa falla (sesion expirada, error de red), las demas siguen y el
resumen lo refleja. Exit code 0 si todo OK, 3 si hubo errores parciales.

Flags utiles:

```bash
uv run suvalor sync --no-docs              # saltar documentos
uv run suvalor sync --no-extractos         # saltar extractos
uv run suvalor sync --no-cartera           # saltar snapshot de cartera
uv run suvalor sync --types RC,NC          # filtrar tipos de docs
uv run suvalor sync --backfill             # docs: historico desde 2024-01-01
```

### Smoke test (recomendado primero)

```bash
uv run suvalor descargar --smoke-test --types RC --max-docs 3
```

Ultimos 30 dias, solo Recibos de Caja, max 3 docs.

### Solo documentos (incremental)

```bash
uv run suvalor descargar
```

Consulta desde `retro_days` antes de la ultima corrida hasta hoy. Salta
documentos que ya estan en el inventario. Por default usa solo `RC`, `NC`,
`CE`. `FB` y `PB` son opt-in con `--types`; `CC` queda como tipo legacy
local para leer inventarios/estado historico, pero ya no se consulta en el
selector actual del portal.

### Backfill historico

```bash
uv run suvalor descargar --backfill
```

Consulta todo desde 2024-01-01.

### Rango personalizado

```bash
uv run suvalor descargar --from 2025-06-01 --to 2025-09-30
```

### Tipos de documento

| Codigo | Tipo | Notas |
|---|---|---|
| `RC` | Recibos de Caja | Default |
| `NC` | Notas Contables | Default |
| `CE` | Comprobantes de Egreso | Default |
| `FB` | Facturas de Bolsa | Opt-in (`--types FB`); no default |
| `PB` | Papeletas de Bolsa | Opt-in (`--types PB`); no default |
| `CC` | Certificados de Custodia | Legacy local; no disponible para consultas nuevas |

El selector actual del portal expone `CE`, `FB`, `NC`, `PB` y `RC`. Si un
`config.toml` antiguo o un `--types` explicito incluye `CC`, el comando falla
antes de abrir el navegador y pide usar tipos actuales. En
`recuperar-fallidos`, las filas legacy `CC` se reportan como saltadas; si no
queda ningun tipo actual para reintentar, no se abre Chrome ni se pide login.

### Otros subcomandos

| Comando | Que hace |
|---|---|
| `suvalor sync` | (default) Ejecuta docs + extractos + cartera. |
| `suvalor extractos` | Sincroniza extractos consolidados (PDF). |
| `suvalor cartera` | Snapshot del portafolio actual (XLS). |
| `suvalor inventario` | Resumen del inventario actual. |
| `suvalor reset` | Borra `_state/inventario.json` y `_state/ultima_corrida.json`. |
| `suvalor recuperar-fallidos` | Reintenta cada fallo en `_Fallidos/fallos.tsv`. |
| `suvalor config show` | Muestra la configuracion efectiva. |
| `suvalor config init` | Crea `_state/config.toml` con un template editable. |
| `suvalor timings` | Muestra los percentiles aprendidos por operacion. |

### Tesoreria (staging fail-closed)

`suvalor tesoreria` existe como superficie opt-in de staging/debug para
preparar movimientos de Tesoreria por rango explicito:

```bash
uv run suvalor tesoreria --from 2026-01-01 --to 2026-01-31 --format both --tag cuenta-corta
uv run suvalor tesoreria --from 2026-01-01 --to 2026-01-31 --format xls --redownload
```

Por ahora el comando valida argumentos, calcula destinos seguros y termina en
modo **fail-closed** antes de tocar el portal. Sigue aplicando el mismo limite
de **login manual**: no se automatizan credenciales, teclado virtual, OTP ni
reCAPTCHA. Si se usa `--account`, tambien se debe pasar un `--tag` seguro; el
texto real de la cuenta nunca debe aparecer en rutas, logs ni resumenes.

Tesoreria todavia no corre dentro de `sync`. El objetivo final es integrarla a
`suvalor sync` cuando la automatizacion deje de estar fail-closed, con un
control explicito como `--no-tesoreria`. Antes de esa integracion falta cerrar
la evidencia redacted del portal para el caso **sin datos**. Hasta entonces,
cualquier export vacio, error del portal o ausencia de marcador confiable debe
tratarse como fallo conservador: no crea archivos de exito falsos.

## Configuracion (`$SUVALOR_HOME/_state/config.toml`)

Opcional. Si no existe se usan defaults. Para crearlo:

```bash
uv run suvalor config init
```

Claves disponibles (con sus defaults):

```toml
retro_days = 60
range_days = 89                # NO subir, el sitio limita en 89 dias
retry_doc = 3
max_pages_per_query = 50
tipos_default = ["RC", "NC", "CE"]
wait_min_consulta_s = 3.0
wait_min_descarga_s = 5.0
wait_min_page_change_s = 3.0
```

## Memoria adaptativa de tiempos

El portal es lento y variable. En vez de hardcodear esperas, el cliente
**aprende** cuanto tardan las operaciones y usa `p95 + buffer` como
timeout con un piso configurable. Persistido en `_state/timings.json` con
ventana movil de 50 mediciones.

```bash
uv run suvalor timings
```

## Resiliencia

- **Verificacion post-descarga**: PDFs validados por header (`%PDF-`),
  footer (`%%EOF`) y tamaño minimo. XLS-HTML validado por presencia de
  `<table` y ausencia de `login`/`iniciar sesion`. Archivos invalidos se
  borran y se reintenta.
- **Visor PDF inline (Adobe Acrobat ext)**: si Chrome tiene la extension
  de Adobe Acrobat instalada, los PDFs abren en visor (sin disparar
  download event). El cliente captura la pestaña popup, extrae la URL y
  descarga via `context.request.get(url)` reusando las cookies de sesion.
- **Sesion expirada**: detectada por redirect a `terminarSesion.aspx`; el
  resumen lo refleja con indicador rojo.
- **Reintentos adaptativos**: cada operacion reintenta hasta `retry_doc`
  veces (default 3). Solo las exitosas alimentan la memoria de tiempos.

---

## Tests

```bash
uv run pytest
```

Suite pura de **116+ tests** (sin Playwright, sin red). Cubre rangos,
parseo, timings, formato de estado, heuristicas de verificacion y argument
parsing del CLI.

## Estructura

```
suvalor/
├── pyproject.toml
├── README.md
├── LICENSE              (Apache-2.0)
├── NOTICE
├── DISCLAIMER.md        (lectura obligatoria)
├── AGENTS.md            (instrucciones para agentes IA)
├── CONTRIBUTING.md
├── .gitignore
├── docs/
│   └── SITE_NOTES.md    (hallazgos tecnicos del portal)
├── suvalor/             (paquete)
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py           (entrypoint Typer)
│   ├── orquestador.py   (loop docs + extractos + cartera)
│   ├── navegador.py     (Playwright + perfil persistente + anti-deteccion)
│   ├── pagina.py        (interacciones ASP.NET)
│   ├── descargador.py   (descarga + popup PDF)
│   ├── verificacion.py  (post-descarga: header PDF / HTML-as-XLS)
│   ├── estado.py        (inventario + extractos + ultima_corrida pydantic)
│   ├── timings.py       (memoria adaptativa de tiempos)
│   ├── rangos.py        (particion en rangos de 89 dias)
│   ├── parseo.py        (fechas + meses_es)
│   ├── config.py        (config.toml loader)
│   └── tipos.py         (constantes y enums; resuelve SUVALOR_HOME)
└── tests/
```

## Decisiones de diseño

- **Typer + Rich**: ecosistema unificado, `--help` legible, progress bars
  y tablas en corridas largas.
- **Pydantic v2** para state: validacion automatica, `extra="allow"` en
  `RegistroCorrida` para tolerar campos viejos no estandar.
- **Tenacity**: usado de forma puntual; no se decora la cadena entera para
  preservar control fino sobre la deteccion de sesion expirada.
- **Loguru**: dual log (DEBUG a archivo + INFO a consola) sin boilerplate.
- **Memoria adaptativa**: ventana movil de 50, p95 recalculado en cada
  registro, `timeout = max(piso, p95 + 2.5s, default)`. Conservador al
  inicio, se ajusta solo despues de 3 mediciones.

## Hallazgos tecnicos del portal

Ver [`docs/SITE_NOTES.md`](docs/SITE_NOTES.md): URLs, IDs ASP.NET,
restricciones (89 dias por consulta, 12 meses de extractos, 504 en FB/PB,
session timeout de 7 minutos).

## Contribuir

Ver [`CONTRIBUTING.md`](CONTRIBUTING.md). Resumen:

1. Issue antes de PR (excepto fixes triviales).
2. Conventional commits.
3. Tests pasando: `uv run pytest`.
4. Sin filtrar datos personales en commits o issues.

## Para agentes IA

Ver [`AGENTS.md`](AGENTS.md). Instrucciones especificas para que un
agente (Claude Code, Cursor, Copilot, etc.) pueda instalar, configurar y
trabajar con este cliente de forma segura.

## Comunidad

- 📜 [DISCLAIMER](DISCLAIMER.md) — limites legales y de responsabilidad (lectura obligatoria).
- 🤝 [CONTRIBUTING](CONTRIBUTING.md) — como abrir issues y PRs.
- 🛡️ [SECURITY](SECURITY.md) — reportar vulnerabilidades.
- 📋 [CODE_OF_CONDUCT](CODE_OF_CONDUCT.md) — Contributor Covenant 2.1.
- 📝 [CHANGELOG](CHANGELOG.md) — historia de versiones.

## Autor

**John Alberto Parrado Gordillo** ([@jparradog](https://github.com/jparradog))

Contribuciones de la comunidad bienvenidas — ver [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licencia

[Apache License 2.0](LICENSE) — © 2026 John Alberto Parrado Gordillo.

Sujeto a los terminos de [`DISCLAIMER.md`](DISCLAIMER.md).
