"""Helpers puros para el flujo opt-in de fondos."""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path

from .rangos import partir_en_rangos

_RE_TAG_FONDOS = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,39}$")


@dataclass(frozen=True)
class PlanFondos:
    desde: dt.date
    hasta: dt.date
    tag: str
    redownload: bool
    rangos: list[tuple[dt.date, dt.date]]
    destinos: list[Path]


def validar_tag_fondos(tag: str) -> str:
    """Valida un tag seguro para nombre de archivo; no selecciona cuenta/fondo."""
    if not _RE_TAG_FONDOS.fullmatch(tag):
        raise ValueError(
            "--tag debe usar solo letras, numeros, '-' o '_' (1..40 chars)"
        )
    return tag


def construir_destino_fondos(
    *,
    base: Path,
    desde: dt.date,
    hasta: dt.date,
    tag: str = "",
) -> Path:
    """Construye `Fondos/YYYY/YYYY-MM-DD_YYYY-MM-DD_movimientos_fondos[_tag].xls`."""
    sufijo = f"_{validar_tag_fondos(tag)}" if tag else ""
    nombre = f"{desde.isoformat()}_{hasta.isoformat()}_movimientos_fondos{sufijo}.xls"
    return base / "Fondos" / str(desde.year) / nombre


def _dmy_a_date(valor: str) -> dt.date:
    return dt.datetime.strptime(valor, "%d/%m/%Y").date()


def construir_plan_fondos(
    *,
    base: Path,
    desde_iso: str,
    hasta_iso: str,
    tag: str = "",
    redownload: bool = False,
) -> PlanFondos:
    """Valida fechas/tag y parte la corrida en chunks de hasta 89 dias."""
    try:
        desde = dt.date.fromisoformat(desde_iso)
        hasta = dt.date.fromisoformat(hasta_iso)
    except ValueError as e:
        raise ValueError("--from y --to deben usar formato YYYY-MM-DD") from e
    if desde > hasta:
        raise ValueError("--from no puede ser posterior a --to")
    tag_ok = validar_tag_fondos(tag) if tag else ""
    rangos = [
        (_dmy_a_date(r.desde_dmy), _dmy_a_date(r.hasta_dmy))
        for r in partir_en_rangos(desde, hasta)
    ]
    destinos = [
        construir_destino_fondos(base=base, desde=ini, hasta=fin, tag=tag_ok)
        for ini, fin in rangos
    ]
    return PlanFondos(
        desde=desde,
        hasta=hasta,
        tag=tag_ok,
        redownload=redownload,
        rangos=rangos,
        destinos=destinos,
    )
