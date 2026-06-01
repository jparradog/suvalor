"""Tests puros (no requieren Playwright) para suvalor.parseo."""

from __future__ import annotations

import pytest

from suvalor.parseo import (
    extraer_anio_de_dmy,
    fecha_dmy_a_iso,
    fecha_iso_a_dmy,
    parsear_fecha_grilla,
)


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("12/abr/2025", "2025-04-12"),
        ("01/ene/2024", "2024-01-01"),
        ("31/dic/2026", "2026-12-31"),
        # con punto extra al final del mes
        ("5/feb./2025", "2025-02-05"),
        # mayusculas
        ("15/MAR/2025", "2025-03-15"),
    ],
)
def test_parsear_fecha_grilla_estandar(entrada, esperado):
    assert parsear_fecha_grilla(entrada) == esperado


def test_parsear_fecha_grilla_no_matchea_fallback():
    # si no matchea el patron, hace fallback (igual que el monolito)
    out = parsear_fecha_grilla("2025-04-12")
    assert "/" not in out
    assert "." not in out


def test_parsear_fecha_grilla_vacio():
    assert parsear_fecha_grilla("") == ""


def test_parsear_fecha_grilla_numerica_valida():
    assert parsear_fecha_grilla("05/04/2025") == "2025-04-05"


@pytest.mark.parametrize("entrada", ["31/02/2025", "12/xyz/2025", "32/ene/2025"])
def test_parsear_fecha_grilla_fecha_matcheada_invalida_falla(entrada):
    with pytest.raises(ValueError):
        parsear_fecha_grilla(entrada)


def test_parsear_fecha_grilla_no_emite_mes_cero():
    with pytest.raises(ValueError):
        parsear_fecha_grilla("12/04x/2025")


def test_fecha_iso_a_dmy():
    assert fecha_iso_a_dmy("2025-04-12") == "12/04/2025"
    assert fecha_iso_a_dmy("2024-01-01") == "01/01/2024"


def test_fecha_dmy_a_iso():
    assert fecha_dmy_a_iso("12/04/2025") == "2025-04-12"
    assert fecha_dmy_a_iso("01/01/2024") == "2024-01-01"


def test_round_trip_iso_dmy():
    iso = "2026-04-27"
    assert fecha_dmy_a_iso(fecha_iso_a_dmy(iso)) == iso


def test_extraer_anio():
    assert extraer_anio_de_dmy("12/04/2025") == "2025"
    assert extraer_anio_de_dmy("01/01/2024") == "2024"
