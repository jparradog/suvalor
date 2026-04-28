"""Configuracion editable por el usuario en `_state/config.toml`.

Si el archivo no existe, se usan defaults y NO se crea automaticamente
(para no ensuciar `_state/`). El comando `suvalor config init` puede
escribir un template; ver cli.py.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .tipos import CONFIG_FILE, MAX_DIAS_POR_RANGO, TIPOS_DEFAULT

if sys.version_info >= (3, 11):
    import tomllib  # type: ignore[import-not-found]
else:  # pragma: no cover
    import tomli as tomllib  # type: ignore[import-not-found]


@dataclass
class Config:
    """Parametros configurables. Todos tienen un default sensato."""

    retro_days: int = 60
    range_days: int = MAX_DIAS_POR_RANGO  # 89, no subir
    retry_doc: int = 3
    max_pages_per_query: int = 50
    tipos_default: list[str] = field(default_factory=lambda: list(TIPOS_DEFAULT))

    # Waits minimos (segundos). Valores bajos -> mas rapido pero mas frageil.
    wait_min_consulta_s: float = 3.0
    wait_min_descarga_s: float = 5.0
    wait_min_page_change_s: float = 3.0

    @classmethod
    def cargar(cls, path: Path = CONFIG_FILE) -> "Config":
        if not path.exists():
            return cls()
        with path.open("rb") as f:
            data = tomllib.load(f)
        # filtramos a solo las claves conocidas para no romper si hay cosas viejas
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid)

    def to_dict(self) -> dict:
        return asdict(self)


TEMPLATE_TOML = """\
# Configuracion de suvalor. Editable. Todas las claves son opcionales.

# Cuantos dias hacia atras consultar desde la ultima corrida (incremental).
retro_days = 60

# Tamano maximo de cada rango. NO subir de 89 — el sitio limita ahi.
range_days = 89

# Cuantas veces reintentar bajar un mismo documento antes de marcarlo fallido.
retry_doc = 3

# Cota dura por consulta para evitar loops infinitos en paginacion.
max_pages_per_query = 50

# Tipos a procesar en una corrida normal (sin --types). FB y PB suelen dar 504.
tipos_default = ["RC", "NC", "CE", "CC"]

# Waits minimos (segundos). El sistema usa max(piso, p95 + buffer).
wait_min_consulta_s = 3.0
wait_min_descarga_s = 5.0
wait_min_page_change_s = 3.0
"""


def escribir_template(path: Path = CONFIG_FILE) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(TEMPLATE_TOML, encoding="utf-8")
    return path
