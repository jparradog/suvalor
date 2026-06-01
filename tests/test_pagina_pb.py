from __future__ import annotations

import pytest

from suvalor.pagina import (
    ErrorExtraccionFilas,
    Fila,
    _extraer_filas_pb_desde_tabla,
    extraer_filas,
)


class _PagePB:
    def __init__(self, payload):
        self.payload = payload

    def evaluate(self, script):
        return self.payload


def test_pb_extrae_por_headers_normalizados() -> None:
    filas = _extraer_filas_pb_desde_tabla(
        headers=[
            "Accion",
            "N° Papeleta",
            "Fecha Operación",
            "Fecha Cumplimiento",
            "Valor",
        ],
        rows=[["Ver", "PB-12345", "05/04/2025", "08/04/2025", "$ 10.000"]],
    )

    assert filas == [
        Fila(idx=0, fecha="05/04/2025", doc_num="PB-12345", valor="$ 10.000")
    ]


def test_pb_no_usa_indices_legacy_rc_nc_ce() -> None:
    filas = _extraer_filas_pb_desde_tabla(
        headers=[
            "Fecha Cumplimiento",
            "Valor",
            "N°Papeleta",
            "Otro",
            "Fecha Operacion",
        ],
        rows=[["08/04/2025", "$ 10.000", "9988", "x", "05/04/2025"]],
    )

    assert filas[0].fecha == "05/04/2025"
    assert filas[0].doc_num == "9988"


@pytest.mark.parametrize(
    "headers",
    [
        ["Fecha Operacion", "Valor"],
        ["N°Papeleta", "Valor"],
    ],
)
def test_pb_headers_requeridos_fallan_cerrado(headers) -> None:
    with pytest.raises(ErrorExtraccionFilas):
        _extraer_filas_pb_desde_tabla(headers=headers, rows=[["x", "y"]])


def test_extraer_filas_pb_usa_payload_con_headers() -> None:
    page = _PagePB(
        {
            "headers": ["N°Papeleta", "Fecha Operacion", "Valor"],
            "rows": [["777", "05/04/2025", "$ 1"]],
        }
    )

    assert extraer_filas(page, "PB") == [
        Fila(idx=0, fecha="05/04/2025", doc_num="777", valor="$ 1")
    ]
