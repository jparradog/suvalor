"""Paquete suvalor: descarga automatizada de documentos electronicos
de la sucursal virtual de Cibest Capital / Valores Bancolombia.

Modulos principales:
    cli           Entrypoint Typer (`suvalor descargar`, `suvalor inventario`...).
    orquestador   Loop principal por (rango_de_fechas, tipo_documento).
    navegador     Setup de Playwright + perfil persistente + anti-deteccion.
    pagina        Interacciones con la pagina ASP.NET WebForms.
    descargador   Polling del archivo descargado, rename y mueve a destino final.
    estado        Modelos pydantic + persistencia en _state/.
    timings       Memoria adaptativa de tiempos de operaciones (p50/p90/p95).
    rangos        Generacion de rangos de 89 dias (limite del sitio).
    parseo        Parseo de fechas en castellano, etc.
    tipos         Constantes y enums de tipos de documento.
"""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:
    __version__ = _pkg_version("suvalor")
except PackageNotFoundError:  # paquete no instalado (corrida desde fuente sin pip install -e)
    __version__ = "0.0.0+unknown"
