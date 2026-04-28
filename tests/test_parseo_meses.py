"""Tests del helper `mes_es_a_iso` (subcomando `extractos`).

Convierte periodos en castellano ("marzo 2026", "ene 2026", etc.) a `YYYY-MM`.
"""
from __future__ import annotations

import pytest

from suvalor.parseo import mes_es_a_iso


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        # nombres completos minuscula
        ("marzo 2026", "2026-03"),
        ("febrero 2025", "2025-02"),
        ("agosto 2025", "2025-08"),
        ("diciembre 2025", "2025-12"),
        ("enero 2026", "2026-01"),
        # abreviado de 3 letras
        ("ene 2026", "2026-01"),
        ("dic 2025", "2025-12"),
        ("abr 2025", "2025-04"),
        # con punto al final del mes (a veces aparece "ene.")
        ("ene. 2026", "2026-01"),
        ("feb. 2025", "2025-02"),
        # mayusculas mezcladas
        ("MARZO 2026", "2026-03"),
        ("Diciembre 2025", "2025-12"),
        ("ENE 2026", "2026-01"),
        # con palabra "de" en el medio
        ("marzo de 2026", "2026-03"),
        ("noviembre de 2025", "2025-11"),
        # separadores no estandar
        ("ene-2026", "2026-01"),
        ("feb/2025", "2025-02"),
        # variantes de septiembre
        ("septiembre 2025", "2025-09"),
        ("setiembre 2025", "2025-09"),
        ("set 2025", "2025-09"),
        ("sep 2025", "2025-09"),
        # anio primero (ej. si vienen en otro orden)
        ("2026 marzo", "2026-03"),
    ],
)
def test_mes_es_a_iso_casos_validos(entrada: str, esperado: str) -> None:
    assert mes_es_a_iso(entrada) == esperado


@pytest.mark.parametrize(
    "entrada",
    [
        "",
        "   ",
        "marzo",          # sin anio
        "2026",           # sin mes
        "kwfoo 2026",     # mes invalido
        "blabla",         # nada utilizable
    ],
)
def test_mes_es_a_iso_invalidos_levantan(entrada: str) -> None:
    with pytest.raises(ValueError):
        mes_es_a_iso(entrada)


def test_mes_es_a_iso_tolera_espacios_extras() -> None:
    assert mes_es_a_iso("   marzo   2026   ") == "2026-03"
