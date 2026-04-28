"""Modelos pydantic + persistencia del estado de la app.

Compatibilidad con el formato existente:
    `_state/inventario.json`     -> lista plana de strings `TIPO_NUMERO`.
    `_state/ultima_corrida.json` -> dict con `ultima_corrida` (str ISO) y
                                    `rangos_consultados` (lista de dicts libres).

Ambos se cargan tal cual estan; se escriben en el mismo formato.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .tipos import (
    BASE,
    EXTRACTOS_DIR,
    FALLOS_TSV,
    INVENTORY_EXTRACTOS_FILE,
    INVENTORY_FILE,
    STATE_DIR,
    STATE_FILE,
)


class RegistroCorrida(BaseModel):
    """Una entrada del historial `rangos_consultados`."""

    fecha: str
    tipos: list[str] = Field(default_factory=list)
    rangos: list[Any] = Field(default_factory=list)
    nuevos_esta_corrida: int = 0
    saltados_esta_corrida: int = 0
    fallidos_esta_corrida: int = 0
    total_inventario: int = 0

    # Permitimos campos viejos extra (p.ej. `tipos_chequeados`,
    # `descargados_esta_corrida`) sin romper compatibilidad.
    model_config = {"extra": "allow"}


class EstadoCorrida(BaseModel):
    """Contenido de `ultima_corrida.json`."""

    ultima_corrida: str | None = None
    rangos_consultados: list[dict[str, Any]] = Field(default_factory=list)


class Inventario(BaseModel):
    """Coleccion de IDs `TIPO_NUMERO` ya descargados.

    Se serializa como lista ordenada para coincidir con el formato del
    monolito (que tambien hacia `sorted(...)` antes de guardar).
    """

    ids: set[str] = Field(default_factory=set)

    def __contains__(self, key: str) -> bool:
        return key in self.ids

    def add(self, key: str) -> None:
        self.ids.add(key)

    def __len__(self) -> int:
        return len(self.ids)


# --------------------------------------------------------------------------- #
# Carga / guardado                                                            #
# --------------------------------------------------------------------------- #


def cargar_estado() -> EstadoCorrida:
    if STATE_FILE.exists():
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return EstadoCorrida.model_validate(data)
    return EstadoCorrida()


def guardar_estado(estado: EstadoCorrida) -> None:
    STATE_DIR.mkdir(exist_ok=True)
    STATE_FILE.write_text(
        json.dumps(estado.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def cargar_inventario() -> Inventario:
    """Lee el JSON existente, o reconstruye desde PDFs si no existe.

    Es tolerante a JSON truncado: si la lista no tiene ']' final (caso real
    visto en `_state/inventario.json` tras una corrida interrumpida), intenta
    extraer todos los IDs presentes y sigue.
    """
    if INVENTORY_FILE.exists():
        text = INVENTORY_FILE.read_text(encoding="utf-8")
        try:
            data = json.loads(text)
            return Inventario(ids=set(data))
        except json.JSONDecodeError:
            # fallback: extraer todos los strings entre comillas
            ids = set(re.findall(r'"([A-Z]{2}_[A-Za-z0-9]+)"', text))
            return Inventario(ids=ids)

    # Fallback: rebuild desde los archivos en BASE/{anio}/{tipo}/*.pdf
    encontrados: set[str] = set()
    for pdf in BASE.rglob("*.pdf"):
        m = re.search(r"_([A-Z]{2})_(\w+)\.pdf$", pdf.name)
        if m:
            encontrados.add(f"{m.group(1)}_{m.group(2)}")
    return Inventario(ids=encontrados)


def guardar_inventario(inv: Inventario) -> None:
    STATE_DIR.mkdir(exist_ok=True)
    INVENTORY_FILE.write_text(
        json.dumps(sorted(inv.ids), indent=2),
        encoding="utf-8",
    )


# --------------------------------------------------------------------------- #
# Inventario de extractos (subcomando `extractos`)                            #
# --------------------------------------------------------------------------- #


class InventarioExtractos(BaseModel):
    """Coleccion de keys YYYY-MM ya descargados (extractos consolidados).

    Se serializa como lista ordenada de strings para mantener el patron del
    inventario principal (lista plana en JSON).
    """

    ids: set[str] = Field(default_factory=set)

    def __contains__(self, key: str) -> bool:
        return key in self.ids

    def add(self, key: str) -> None:
        self.ids.add(key)

    def __len__(self) -> int:
        return len(self.ids)


_RE_EXTRACTO_NOMBRE = re.compile(r"(\d{4}-\d{2})_extracto\.pdf$", re.IGNORECASE)


def cargar_inventario_extractos() -> InventarioExtractos:
    """Lee `_state/inventario_extractos.json`. Si no existe, reconstruye
    escaneando `Extractos/**/*.pdf` con nombre `YYYY-MM_extracto.pdf`.
    """
    if INVENTORY_EXTRACTOS_FILE.exists():
        text = INVENTORY_EXTRACTOS_FILE.read_text(encoding="utf-8")
        try:
            data = json.loads(text)
            return InventarioExtractos(ids=set(data))
        except json.JSONDecodeError:
            ids = set(re.findall(r'"(\d{4}-\d{2})"', text))
            return InventarioExtractos(ids=ids)

    encontrados: set[str] = set()
    if EXTRACTOS_DIR.exists():
        for pdf in EXTRACTOS_DIR.rglob("*.pdf"):
            m = _RE_EXTRACTO_NOMBRE.search(pdf.name)
            if m:
                encontrados.add(m.group(1))
    return InventarioExtractos(ids=encontrados)


def guardar_inventario_extractos(inv: InventarioExtractos) -> None:
    STATE_DIR.mkdir(exist_ok=True)
    INVENTORY_EXTRACTOS_FILE.write_text(
        json.dumps(sorted(inv.ids), indent=2),
        encoding="utf-8",
    )


def reset_estado() -> tuple[bool, bool]:
    """Borra archivos de estado. Devuelve `(borro_inventario, borro_corrida)`."""
    a = b = False
    if INVENTORY_FILE.exists():
        INVENTORY_FILE.unlink()
        a = True
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        b = True
    return a, b


# --------------------------------------------------------------------------- #
# Fallos                                                                      #
# --------------------------------------------------------------------------- #


def registrar_fallo(codigo: str, doc_num: str, fila: dict[str, Any]) -> None:
    """Append a `_Fallidos/fallos.tsv` con el doc que no pudo bajarse."""
    FALLOS_TSV.parent.mkdir(exist_ok=True)
    nuevo = not FALLOS_TSV.exists()
    with FALLOS_TSV.open("a", encoding="utf-8") as f:
        if nuevo:
            f.write("timestamp\ttipo\tdoc_num\tfecha_doc\tvalor\n")
        f.write(
            f"{dt.datetime.now().isoformat()}\t{codigo}\t{doc_num}\t"
            f"{fila.get('fecha', '')}\t{fila.get('valor', '')}\n"
        )


def leer_fallos_pendientes() -> list[dict[str, str]]:
    """Lee `fallos.tsv` y devuelve filas como dicts. Para `recuperar-fallidos`."""
    if not FALLOS_TSV.exists():
        return []
    out: list[dict[str, str]] = []
    with FALLOS_TSV.open(encoding="utf-8") as f:
        header = f.readline().rstrip("\n").split("\t")
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != len(header):
                continue
            out.append(dict(zip(header, parts)))
    return out
