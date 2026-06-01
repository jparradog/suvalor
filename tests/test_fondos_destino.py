from __future__ import annotations

import datetime as dt
import pytest

from suvalor.fondos import construir_destino_fondos, construir_plan_fondos, validar_tag_fondos


def test_destino_fondos_sin_tag(tmp_path):
    destino = construir_destino_fondos(base=tmp_path, desde=dt.date(2026, 1, 1), hasta=dt.date(2026, 1, 31))
    assert destino == tmp_path / "Fondos" / "2026" / "2026-01-01_2026-01-31_movimientos_fondos.xls"


def test_destino_fondos_con_tag_seguro(tmp_path):
    destino = construir_destino_fondos(base=tmp_path, desde=dt.date(2026, 1, 1), hasta=dt.date(2026, 1, 31), tag="safe-tag_1")
    assert destino.name == "2026-01-01_2026-01-31_movimientos_fondos_safe-tag_1.xls"
    assert "cuenta" not in str(destino).lower()


@pytest.mark.parametrize("tag", ["safe", "safe-tag", "safe_tag_1", "A1"])
def test_validar_tag_fondos_acepta_slug_seguro(tag):
    assert validar_tag_fondos(tag) == tag


@pytest.mark.parametrize("tag", ["cuenta 123", "../x", "x/y", "x.y", "", "a" * 41])
def test_validar_tag_fondos_rechaza_inseguro(tag):
    with pytest.raises(ValueError):
        validar_tag_fondos(tag)


def test_plan_fondos_parte_en_rangos_de_89_dias(tmp_path):
    plan = construir_plan_fondos(base=tmp_path, desde_iso="2026-01-01", hasta_iso="2026-04-01", tag="safe")
    assert len(plan.rangos) == 2
    assert plan.destinos[0].name == "2026-01-01_2026-03-30_movimientos_fondos_safe.xls"
    assert plan.destinos[1].name == "2026-03-31_2026-04-01_movimientos_fondos_safe.xls"
