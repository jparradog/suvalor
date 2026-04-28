"""Tests puros (no requieren Playwright) para suvalor.rangos."""
from __future__ import annotations

import datetime as dt

import pytest

from suvalor.rangos import (
    RangoFechas,
    calcular_ventana,
    partir_en_rangos,
    rangos_para_corrida,
)


HOY = dt.date(2026, 4, 27)


# --------------------------------------------------------------------------- #
# partir_en_rangos                                                            #
# --------------------------------------------------------------------------- #


def test_partir_un_solo_rango_corto():
    rangos = partir_en_rangos(dt.date(2026, 1, 1), dt.date(2026, 1, 10))
    assert len(rangos) == 1
    assert rangos[0] == RangoFechas("01/01/2026", "10/01/2026")


def test_partir_exactamente_89_dias_es_un_solo_rango():
    desde = dt.date(2026, 1, 1)
    hasta = desde + dt.timedelta(days=88)  # 89 dias inclusivos
    rangos = partir_en_rangos(desde, hasta)
    assert len(rangos) == 1


def test_partir_90_dias_se_parte_en_dos():
    desde = dt.date(2026, 1, 1)
    hasta = desde + dt.timedelta(days=89)  # 90 dias inclusivos
    rangos = partir_en_rangos(desde, hasta)
    assert len(rangos) == 2
    # primer rango = 89 dias inclusivos -> [1/1, 31/3]
    assert rangos[0].desde_dmy == "01/01/2026"
    # el segundo arranca al dia siguiente del primero
    fin_primero = dt.datetime.strptime(rangos[0].hasta_dmy, "%d/%m/%Y").date()
    inicio_segundo = dt.datetime.strptime(rangos[1].desde_dmy, "%d/%m/%Y").date()
    assert inicio_segundo == fin_primero + dt.timedelta(days=1)


def test_rango_invertido_devuelve_vacio():
    assert partir_en_rangos(dt.date(2026, 5, 1), dt.date(2026, 1, 1)) == []


def test_rangos_son_contiguos_y_cubren_todo():
    desde = dt.date(2024, 1, 1)
    hasta = dt.date(2026, 4, 27)
    rangos = partir_en_rangos(desde, hasta)

    inicio_total = dt.datetime.strptime(rangos[0].desde_dmy, "%d/%m/%Y").date()
    fin_total = dt.datetime.strptime(rangos[-1].hasta_dmy, "%d/%m/%Y").date()
    assert inicio_total == desde
    assert fin_total == hasta

    # contiguo: cada hasta + 1 dia == siguiente desde
    for a, b in zip(rangos, rangos[1:]):
        fin_a = dt.datetime.strptime(a.hasta_dmy, "%d/%m/%Y").date()
        ini_b = dt.datetime.strptime(b.desde_dmy, "%d/%m/%Y").date()
        assert ini_b == fin_a + dt.timedelta(days=1)


def test_dias_por_rango_invalido():
    with pytest.raises(ValueError):
        partir_en_rangos(dt.date(2026, 1, 1), dt.date(2026, 1, 10), dias_por_rango=0)


def test_anio_property():
    r = RangoFechas("15/06/2025", "10/08/2025")
    assert r.anio == "2025"


def test_unpacking():
    r = RangoFechas("01/01/2026", "10/01/2026")
    fi, ff = r
    assert fi == "01/01/2026"
    assert ff == "10/01/2026"


# --------------------------------------------------------------------------- #
# calcular_ventana                                                            #
# --------------------------------------------------------------------------- #


def test_ventana_explicita_gana():
    desde, hasta = calcular_ventana(
        hoy=HOY, desde_iso="2025-01-01", hasta_iso="2025-03-15",
        smoke_test=True, backfill=True, ultima_corrida_iso="2026-04-01",
        retro_days=60,
    )
    assert desde == dt.date(2025, 1, 1)
    assert hasta == dt.date(2025, 3, 15)


def test_ventana_smoke_test_30_dias():
    desde, hasta = calcular_ventana(
        hoy=HOY, desde_iso=None, hasta_iso=None,
        smoke_test=True, backfill=False, ultima_corrida_iso=None, retro_days=60,
    )
    assert hasta == HOY
    assert desde == HOY - dt.timedelta(days=30)


def test_ventana_backfill_desde_2024():
    desde, hasta = calcular_ventana(
        hoy=HOY, desde_iso=None, hasta_iso=None,
        smoke_test=False, backfill=True, ultima_corrida_iso=None, retro_days=60,
    )
    assert desde == dt.date(2024, 1, 1)
    assert hasta == HOY


def test_ventana_default_con_ultima_corrida():
    desde, hasta = calcular_ventana(
        hoy=HOY, desde_iso=None, hasta_iso=None,
        smoke_test=False, backfill=False,
        ultima_corrida_iso="2026-04-01", retro_days=60,
    )
    # 60 dias antes de 2026-04-01 -> 2026-01-31
    assert desde == dt.date(2026, 1, 31)
    assert hasta == HOY


def test_ventana_default_sin_ultima_corrida_va_a_backfill():
    desde, hasta = calcular_ventana(
        hoy=HOY, desde_iso=None, hasta_iso=None,
        smoke_test=False, backfill=False,
        ultima_corrida_iso=None, retro_days=60,
    )
    assert desde == dt.date(2024, 1, 1)
    assert hasta == HOY


def test_rangos_para_corrida_smoke_test_un_solo_rango():
    rangos = rangos_para_corrida(
        hoy=HOY, desde_iso=None, hasta_iso=None,
        smoke_test=True, backfill=False,
        ultima_corrida_iso=None, retro_days=60,
    )
    # 30 dias < 89, deberia ser un solo rango
    assert len(rangos) == 1
    assert rangos[0].hasta_dmy == HOY.strftime("%d/%m/%Y")
