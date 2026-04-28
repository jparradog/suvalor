"""Generacion de rangos de fechas a consultar.

Reglas (heredadas del monolito):
- El sitio acepta consultas de hasta **89 dias** (NO 90 — testeado).
- Si hay `--from / --to`, manda eso.
- Smoke test: ultimos 30 dias.
- Backfill: desde 2024-01-01.
- Default incremental: ultima_corrida - RETRO_DAYS hasta hoy.

Las funciones aqui son puras (no IO) -> facil de testear sin Playwright.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Iterable

from .tipos import MAX_DIAS_POR_RANGO


@dataclass(frozen=True)
class RangoFechas:
    """Rango inclusivo de fechas. Strings ya en formato `DD/MM/YYYY`."""

    desde_dmy: str
    hasta_dmy: str

    @property
    def anio(self) -> str:
        return self.desde_dmy.split("/")[-1]

    def __iter__(self):  # para soportar `fi, ff = rango`
        return iter((self.desde_dmy, self.hasta_dmy))


def partir_en_rangos(
    desde: dt.date,
    hasta: dt.date,
    dias_por_rango: int = MAX_DIAS_POR_RANGO,
) -> list[RangoFechas]:
    """Parte `[desde, hasta]` en rangos contiguos de hasta `dias_por_rango` dias."""
    if desde > hasta:
        return []
    if dias_por_rango < 1:
        raise ValueError("dias_por_rango debe ser >= 1")

    out: list[RangoFechas] = []
    cursor = desde
    while cursor <= hasta:
        fin = min(cursor + dt.timedelta(days=dias_por_rango - 1), hasta)
        out.append(
            RangoFechas(
                desde_dmy=cursor.strftime("%d/%m/%Y"),
                hasta_dmy=fin.strftime("%d/%m/%Y"),
            )
        )
        cursor = fin + dt.timedelta(days=1)
    return out


def calcular_ventana(
    *,
    hoy: dt.date,
    desde_iso: str | None,
    hasta_iso: str | None,
    smoke_test: bool,
    backfill: bool,
    ultima_corrida_iso: str | None,
    retro_days: int,
    fecha_inicio_backfill: dt.date = dt.date(2024, 1, 1),
) -> tuple[dt.date, dt.date]:
    """Calcula `(desde, hasta)` segun los flags pasados al CLI.

    Reglas (en orden de precedencia):
        1. Si `desde_iso` y `hasta_iso` -> esos dos.
        2. Si `smoke_test` -> ultimos 30 dias.
        3. Si `backfill` -> [`fecha_inicio_backfill`, hoy].
        4. Default: [ultima_corrida - retro_days, hoy].
                    Si no hay ultima_corrida -> [`fecha_inicio_backfill`, hoy].
    """
    if desde_iso and hasta_iso:
        return dt.date.fromisoformat(desde_iso), dt.date.fromisoformat(hasta_iso)
    if smoke_test:
        return hoy - dt.timedelta(days=30), hoy
    if backfill:
        return fecha_inicio_backfill, hoy
    if ultima_corrida_iso:
        base = dt.date.fromisoformat(ultima_corrida_iso)
        return base - dt.timedelta(days=retro_days), hoy
    return fecha_inicio_backfill, hoy


def rangos_para_corrida(
    *,
    hoy: dt.date,
    desde_iso: str | None,
    hasta_iso: str | None,
    smoke_test: bool,
    backfill: bool,
    ultima_corrida_iso: str | None,
    retro_days: int,
    range_days: int = MAX_DIAS_POR_RANGO,
) -> list[RangoFechas]:
    """Helper de alto nivel: calcula ventana y la parte en rangos."""
    desde, hasta = calcular_ventana(
        hoy=hoy,
        desde_iso=desde_iso,
        hasta_iso=hasta_iso,
        smoke_test=smoke_test,
        backfill=backfill,
        ultima_corrida_iso=ultima_corrida_iso,
        retro_days=retro_days,
    )
    return partir_en_rangos(desde, hasta, dias_por_rango=range_days)


def resumir_rangos(rangos: Iterable[RangoFechas]) -> str:
    """Render compacto de los rangos para el log."""
    items = list(rangos)
    if not items:
        return "(ninguno)"
    return f"{len(items)} rango(s): {items[0].desde_dmy} ... {items[-1].hasta_dmy}"
