from __future__ import annotations

import datetime as dt
import pytest

from suvalor.tesoreria import (
    canonicalizar_tag_tesoreria,
    construir_destino_tesoreria,
    construir_plan_tesoreria,
)


def test_destino_tesoreria_por_formato_y_tag(tmp_path):
    pdf = construir_destino_tesoreria(
        base=tmp_path,
        desde=dt.date(2026, 1, 1),
        hasta=dt.date(2026, 1, 31),
        formato="pdf",
        tag="corto",
    )
    xls = construir_destino_tesoreria(
        base=tmp_path,
        desde=dt.date(2026, 1, 1),
        hasta=dt.date(2026, 1, 31),
        formato="xls",
        tag="corto",
    )
    assert (
        pdf
        == tmp_path
        / "Tesoreria"
        / "2026"
        / "2026-01-01_2026-01-31_movimientos_tesoreria_corto.pdf"
    )
    assert xls.name == "2026-01-01_2026-01-31_movimientos_tesoreria_corto.xls"


@pytest.mark.parametrize(
    "tag,esperado",
    [(" Corto ", "corto"), ("Mi Cuenta", "mi-cuenta"), ("safe_1", "safe_1")],
)
def test_canonicalizar_tag_tesoreria(tag, esperado):
    assert canonicalizar_tag_tesoreria(tag) == esperado


@pytest.mark.parametrize("tag", ["", "../x", "x/y", "x\\y", "x?y", ".oculto"])
def test_canonicalizar_tag_tesoreria_rechaza_inseguro(tag):
    with pytest.raises(ValueError):
        canonicalizar_tag_tesoreria(tag)


def test_plan_tesoreria_parte_120_dias_y_no_filtra_account(tmp_path):
    plan = construir_plan_tesoreria(
        base=tmp_path,
        desde_iso="2026-01-01",
        hasta_iso="2026-04-30",
        formato="both",
        account="Cuenta Privada 123",
        tag="corto",
    )
    assert len(plan.rangos) == 2
    assert all((fin - ini).days + 1 <= 89 for ini, fin in plan.rangos)
    assert set(plan.formatos) == {"pdf", "xls"}
    assert all("Cuenta Privada" not in str(destino) for destino in plan.destinos)


def test_plan_tesoreria_rango_89_dias_unico(tmp_path):
    plan = construir_plan_tesoreria(
        base=tmp_path, desde_iso="2026-01-01", hasta_iso="2026-03-30", formato="xls"
    )
    assert len(plan.rangos) == 1
    assert [p.suffix for p in plan.destinos] == [".xls"]
