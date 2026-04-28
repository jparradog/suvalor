# Changelog

Todos los cambios notables se documentan aqui. Formato basado en
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Versionado [SemVer 2.0.0](https://semver.org/lang/es/).

## [0.3.0] — 2026-04-28

Primera release publica bajo Apache-2.0.

### Added
- `SUVALOR_HOME`: variable de entorno para apuntar a la carpeta de datos.
  Si no se define, se usa el `cwd` del proceso. Ver `README.md`.
- Guardrail en `suvalor/tipos.py:_resolver_base()` que aborta si
  `SUVALOR_HOME` (o `cwd`) apunta al codigo fuente del paquete.
- `AGENTS.md` con instrucciones para agentes IA.
- `DISCLAIMER.md` con limites legales y de responsabilidad.
- `SECURITY.md` con politica de disclosure de vulnerabilidades.
- `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1).
- `CONTRIBUTING.md` con flujo de PRs + conventional commits.
- `docs/SITE_NOTES.md` con hallazgos tecnicos del portal.
- `.env.example` para SUVALOR_HOME.
- `conftest.py` que aisla los tests del filesystem real.
- GitHub Actions CI (pytest matrix sobre Python 3.10–3.13).

### Changed
- `BASE` en `suvalor/tipos.py` ahora se calcula via `_resolver_base()`
  con prioridad `SUVALOR_HOME` > `cwd`. Antes asumia layout
  `_script/suvalor/` adentro de la carpeta de datos.
- `__version__` en `suvalor/__init__.py` ahora se lee desde el package
  metadata (`importlib.metadata.version`). Antes estaba hardcodeado.
- Default del CLI: `suvalor` (sin subcomando) ejecuta `sync` (docs +
  extractos + cartera). Antes (v0.2) ejecutaba `descargar` solo.
- Licencia: ahora **Apache-2.0** declarada explicitamente en
  `pyproject.toml` y `LICENSE`.

### Removed
- Codigo monolitico legacy (`descargar_suvalor.py`, ya no se distribuye).
- Constante `SCRIPT_DIR` en `tipos.py` (no se usaba).
- Comentarios y paths con datos personales del autor.

### Migracion desde 0.2.x

Si se venia de la version 0.2 con layout `_script/suvalor/` dentro de la
carpeta de datos:

1. **Mover el codigo**. Clonar el repositorio a una carpeta separada de
   los datos:
   ```bash
   git clone https://github.com/jparradog/suvalor.git ~/proyectos/suvalor
   ```
2. **Elegir una carpeta de datos**. Ejemplo:
   ```bash
   mkdir -p ~/Documents/suvalor-data
   ```
3. **Mover los datos**: copiar/mover `2024/`, `2025/`, `2026/`,
   `Extractos/`, `Cartera/`, `_state/`, `_chrome_profile/`, `_Fallidos/`
   desde la carpeta antigua a `~/Documents/suvalor-data/`.
4. **Configurar SUVALOR_HOME**:
   ```bash
   export SUVALOR_HOME=~/Documents/suvalor-data
   ```
5. **Probar**:
   ```bash
   cd ~/proyectos/suvalor
   uv sync
   uv run playwright install
   uv run suvalor inventario
   ```
6. **Una vez confirmado** que el inventario detecta los archivos
   previos, se puede borrar el `_script/` viejo de la carpeta de datos.

> Nota: el inventario JSON (`_state/inventario.json`) y la lista de
> extractos (`_state/inventario_extractos.json`) se reconstruyen
> automaticamente escaneando los PDFs si faltan, por lo que si algo se
> borra por error, el cliente lo regenera en la proxima corrida.

### Breaking changes

- **El layout fisico cambio**: el paquete ya no asume vivir en
  `_script/suvalor/`. Ahora el codigo y los datos viven en carpetas
  separadas.
- **`suvalor` (sin subcomando) ahora ejecuta `sync`** en vez de
  `descargar`. Para preservar el comportamiento anterior, usa explicitamente
  `suvalor descargar`.

---

## [0.2.0] — pre-release privada

Refactor del monolito original a paquete modular `suvalor/`. No publicada
publicamente.

## [0.1.0] — pre-release privada

Monolito original (`descargar_suvalor.py`). No publicada publicamente.
