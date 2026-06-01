from __future__ import annotations

import datetime as dt
from typing import Any, cast

import pytest

from suvalor.pagina import (
    CuentaTesoreriaNoEncontrada,
    preparar_tesoreria,
    seleccionar_cuenta_tesoreria,
    setear_filtros_tesoreria,
)
from suvalor.tipos import (
    ID_TESORERIA_CUENTA,
    ID_TESORERIA_FECHA_FIN,
    ID_TESORERIA_FECHA_INI,
)


class FakePage:
    def __init__(self, *, seleccion: bool = True, filtros: bool = True):
        self.seleccion = seleccion
        self.filtros = filtros
        self.calls: list[tuple[str, object]] = []
        self.waits: list[int] = []

    def evaluate(self, script: str, arg=None):
        self.calls.append((script, arg))
        if ID_TESORERIA_CUENTA in script:
            return self.seleccion
        return self.filtros

    def wait_for_timeout(self, ms: int) -> None:
        self.waits.append(ms)


def test_setear_filtros_tesoreria_usa_ids_y_formato_dmy():
    page = FakePage()

    setear_filtros_tesoreria(
        cast(Any, page),
        desde=dt.date(2026, 1, 2),
        hasta=dt.date(2026, 3, 4),
    )

    script, arg = page.calls[0]
    assert ID_TESORERIA_FECHA_INI in script
    assert ID_TESORERIA_FECHA_FIN in script
    assert arg == {"fi": "02/01/2026", "ff": "04/03/2026"}


def test_seleccionar_cuenta_tesoreria_no_devuelve_label_raw():
    page = FakePage(seleccion=True)

    seleccionada = seleccionar_cuenta_tesoreria(cast(Any, page), "Cuenta Privada 123")

    assert seleccionada is True
    script, arg = page.calls[0]
    assert ID_TESORERIA_CUENTA in script
    assert arg == "Cuenta Privada 123"
    assert "textContent.trim" not in script


def test_preparar_tesoreria_falla_cerrado_si_account_no_existe():
    page = FakePage(seleccion=False)

    with pytest.raises(CuentaTesoreriaNoEncontrada) as exc:
        preparar_tesoreria(
            cast(Any, page),
            desde=dt.date(2026, 1, 1),
            hasta=dt.date(2026, 1, 31),
            account="Cuenta Privada 123",
        )

    assert "Cuenta Privada" not in str(exc.value)
    assert "123" not in str(exc.value)


def test_preparar_tesoreria_espera_si_selecciona_account():
    page = FakePage(seleccion=True)

    preparar_tesoreria(
        cast(Any, page),
        desde=dt.date(2026, 1, 1),
        hasta=dt.date(2026, 1, 31),
        account="Cuenta Privada 123",
    )

    assert page.waits == [2500]
    assert ID_TESORERIA_CUENTA in page.calls[0][0]
    assert ID_TESORERIA_FECHA_INI in page.calls[1][0]
