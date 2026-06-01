"""Helpers puros para el flujo opt-in de tesoreria."""

from __future__ import annotations

import datetime as dt
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from .rangos import partir_en_rangos
from .tipos import TESORERIA_DIR, TESORERIA_FORMATOS, TESORERIA_FORMATOS_EXPORT
from .verificacion import verificar_descarga

_FORMATOS_TESORERIA = set(TESORERIA_FORMATOS)
_FORMATOS_EXPORT_TESORERIA = set(TESORERIA_FORMATOS_EXPORT)
_RE_TAG_TESORERIA = re.compile(r"^[a-z0-9][a-z0-9._-]{0,39}$")


@dataclass(frozen=True)
class PlanTesoreria:
    desde: dt.date
    hasta: dt.date
    formatos: list[str]
    tag: str
    redownload: bool
    cuenta_solicitada: bool
    rangos: list[tuple[dt.date, dt.date]]
    destinos: list[Path]


@dataclass(frozen=True)
class ResultadoPromocionTesoreria:
    ok: bool
    motivo: str
    destino: Path


def canonicalizar_tag_tesoreria(tag: str) -> str:
    """Normaliza un tag seguro para nombre de archivo; no selecciona cuenta."""
    normal = unicodedata.normalize("NFKD", tag.strip())
    ascii_txt = normal.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"\s+", "-", ascii_txt)
    if not _RE_TAG_TESORERIA.fullmatch(slug):
        raise ValueError("--tag debe resolver a [a-z0-9][a-z0-9._-]{0,39}")
    if ".." in slug or "/" in slug or "\\" in slug:
        raise ValueError("--tag no puede contener rutas")
    return slug


def formatos_tesoreria(formato: str) -> list[str]:
    if formato not in _FORMATOS_TESORERIA:
        raise ValueError("--format debe ser pdf, xls o both")
    return ["pdf", "xls"] if formato == "both" else [formato]


def _tipo_verificacion_tesoreria(formato: str) -> str:
    if formato == "pdf":
        return "pdf"
    if formato == "xls":
        return "tesoreria"
    raise ValueError("formato debe ser pdf o xls")


def _mismo_archivo(a: Path, b: Path) -> bool:
    try:
        return a.resolve(strict=False) == b.resolve(strict=False)
    except OSError:
        return a.absolute() == b.absolute()


def _borrar_candidato(candidato: Path, destino: Path) -> str:
    if _mismo_archivo(candidato, destino):
        return "candidato y destino son el mismo archivo"
    try:
        candidato.unlink(missing_ok=True)
    except OSError as e:
        return f"no pude borrar candidato: {e}"
    return ""


def debe_descargar_tesoreria(
    destino: Path, *, formato: str, redownload: bool = False
) -> bool:
    """Indica si falta descargar segun validez del final existente."""
    tipo = _tipo_verificacion_tesoreria(formato)
    if redownload:
        return True
    try:
        ok, _motivo = verificar_descarga(destino, tipo)
    except OSError:
        return True
    return not ok


def promover_candidato_tesoreria(
    candidato: Path, destino: Path, *, formato: str
) -> ResultadoPromocionTesoreria:
    """Valida un candidato y lo promueve sin borrar finales previos al fallar."""
    tipo = _tipo_verificacion_tesoreria(formato)
    if _mismo_archivo(candidato, destino):
        return ResultadoPromocionTesoreria(
            False, "candidato y destino son el mismo archivo", destino
        )
    try:
        ok, motivo = verificar_descarga(candidato, tipo)
    except OSError as e:
        motivo = str(e)
        detalle = _borrar_candidato(candidato, destino)
        if detalle:
            motivo = f"{motivo}; {detalle}"
        return ResultadoPromocionTesoreria(False, motivo, destino)
    if not ok:
        detalle = _borrar_candidato(candidato, destino)
        if detalle:
            motivo = f"{motivo}; {detalle}" if motivo else detalle
        return ResultadoPromocionTesoreria(
            False, motivo or "candidato invalido", destino
        )

    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        candidato.replace(destino)
    except OSError as e:
        motivo = f"no pude promover candidato: {e}"
        detalle = _borrar_candidato(candidato, destino)
        if detalle:
            motivo = f"{motivo}; {detalle}"
        return ResultadoPromocionTesoreria(False, motivo, destino)
    return ResultadoPromocionTesoreria(True, "", destino)


def construir_destino_tesoreria(
    *, base: Path, desde: dt.date, hasta: dt.date, formato: str, tag: str = ""
) -> Path:
    if formato not in _FORMATOS_EXPORT_TESORERIA:
        raise ValueError("formato destino debe ser pdf o xls")
    sufijo = f"_{canonicalizar_tag_tesoreria(tag)}" if tag else ""
    nombre = (
        f"{desde.isoformat()}_{hasta.isoformat()}_movimientos_tesoreria"
        f"{sufijo}.{formato}"
    )
    return base / TESORERIA_DIR.name / str(desde.year) / nombre


def _dmy_a_date(valor: str) -> dt.date:
    return dt.datetime.strptime(valor, "%d/%m/%Y").date()


def construir_plan_tesoreria(
    *,
    base: Path,
    desde_iso: str,
    hasta_iso: str,
    formato: str = "both",
    account: str | None = None,
    tag: str = "",
    redownload: bool = False,
) -> PlanTesoreria:
    """Valida argumentos y parte tesoreria en chunks de hasta 89 dias."""
    try:
        desde = dt.date.fromisoformat(desde_iso)
        hasta = dt.date.fromisoformat(hasta_iso)
    except ValueError as e:
        raise ValueError("--from y --to deben usar formato YYYY-MM-DD") from e
    if desde > hasta:
        raise ValueError("--from no puede ser posterior a --to")
    if account is not None and not account.strip():
        raise ValueError("--account no puede estar vacio")
    if account is not None and not tag:
        raise ValueError("--account requiere --tag seguro y no vacio")
    tag_ok = canonicalizar_tag_tesoreria(tag) if tag else ""
    if account is not None and tag != tag_ok:
        raise ValueError("--account requiere --tag canonico para evitar colisiones")
    formatos = formatos_tesoreria(formato)
    rangos = [
        (_dmy_a_date(r.desde_dmy), _dmy_a_date(r.hasta_dmy))
        for r in partir_en_rangos(desde, hasta)
    ]
    destinos = [
        construir_destino_tesoreria(
            base=base, desde=ini, hasta=fin, formato=f, tag=tag_ok
        )
        for ini, fin in rangos
        for f in formatos
    ]
    return PlanTesoreria(
        desde=desde,
        hasta=hasta,
        formatos=formatos,
        tag=tag_ok,
        redownload=redownload,
        cuenta_solicitada=bool(account),
        rangos=rangos,
        destinos=destinos,
    )
