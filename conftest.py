"""Configuracion global de pytest.

Aislamiento del filesystem real:
- Configura SUVALOR_HOME en un directorio temporal ANTES de importar el
  paquete.
- Esto evita que el guardrail de `suvalor/tipos.py:_resolver_base()`
  aborte cuando pytest se ejecuta desde la raiz del repo (donde cwd
  contiene el codigo fuente).
- Tambien evita side effects: que el paquete cree `_state/`, `run.log`,
  etc. en el repo durante la corrida de tests.

Pytest carga conftest.py muy temprano, antes de descubrir tests, por lo
que establecer la variable de entorno aqui (en top-level, no en fixture)
garantiza que el primer `from suvalor import ...` ya vea SUVALOR_HOME
apuntando a un directorio temporal y descartable.
"""
from __future__ import annotations

import os
import tempfile

# Solo se asigna si el usuario no la definio antes (asi un dev puede
# correr pytest contra una carpeta de datos especifica si lo desea).
if not os.environ.get("SUVALOR_HOME", "").strip():
    os.environ["SUVALOR_HOME"] = tempfile.mkdtemp(prefix="suvalor-tests-")
