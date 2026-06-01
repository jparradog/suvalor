"""Diagnosticos sanitizados para fallos del portal."""

from __future__ import annotations

import re

_MOTIVO_CLOUDFRONT_504 = "portal respondio HTTP 504 (CloudFront Gateway Timeout)"
_MOTIVO_HTML_PDF = "portal respondio HTML en vez de PDF"
_RE_URL = re.compile(r"https?://\S+", re.IGNORECASE)
_RE_SENSITIVE_KV = re.compile(
    r"(?i)\b(?:jwt|token|sessionid|session|sid|auth|authorization)=\S+"
)
_RE_QUERY = re.compile(r"\?[^\s)]+")


def _normalizar_texto(contenido: bytes | str | None) -> str:
    if contenido is None:
        return ""
    if isinstance(contenido, bytes):
        return contenido.decode("utf-8", errors="ignore")
    return contenido


def sanitizar_diagnostico(texto: object) -> str:
    """Redacta datos sensibles antes de mostrarlos."""
    salida = _RE_URL.sub("[url-redactada]", str(texto))
    salida = _RE_SENSITIVE_KV.sub("[dato-redactado]", salida)
    return _RE_QUERY.sub("?[query-redactada]", salida).strip()


def clasificar_fallo_portal(
    *,
    status: int | None = None,
    contenido: bytes | str | None = None,
    detalle: object = "",
) -> str | None:
    """Devuelve un motivo normalizado si reconoce un fallo del portal."""
    combinado = f"{_normalizar_texto(contenido)}\n{detalle}".lower()
    if status == 504 or (
        "504" in combinado
        and any(
            marca in combinado
            for marca in (
                "http",
                "status",
                "gateway timeout",
                "cloudfront",
                "request could not be satisfied",
            )
        )
    ):
        return _MOTIVO_CLOUDFRONT_504
    if "cloudfront" in combinado and "gateway timeout" in combinado:
        return _MOTIVO_CLOUDFRONT_504
    if "<html" in combinado or "<!doctype" in combinado:
        return _MOTIVO_HTML_PDF
    return None


def diagnosticar_fallo_portal(
    *,
    status: int | None = None,
    contenido: bytes | str | None = None,
    detalle: object = "",
    fallback: str = "fallo de descarga",
) -> str:
    """Clasifica si puede; si no, devuelve un fallback sanitizado."""
    motivo = clasificar_fallo_portal(
        status=status, contenido=contenido, detalle=detalle
    )
    return motivo or sanitizar_diagnostico(detalle or fallback)
