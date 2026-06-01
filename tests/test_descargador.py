from __future__ import annotations

from typing import Any, cast

import pytest

import suvalor.descargador as descargador_mod
from suvalor.descargador import Resultado, construir_identidad_descarga, descargar_doc
from suvalor.estado import Inventario
from suvalor.pagina import Fila


class _MemFake:
    def timeout_ms(self, op: str) -> int: return 1
    def p95_ms(self, op: str) -> int: return 1
    def registrar(self, op: str, ms: float) -> None: pass


class _PageFake:
    context = object()


def _fila() -> Fila:
    return Fila(idx=0, fecha="05/04/2025", doc_num="12345", valor="0")


def test_pb_identidad_usa_fecha_operacion_y_papeleta() -> None:
    identidad = construir_identidad_descarga(_fila(), "PB")
    assert identidad.fecha_iso == "2025-04-05"
    assert identidad.clave == "PB_12345"
    assert identidad.nombre == "2025-04-05_PB_12345.pdf"


@pytest.mark.parametrize("inventario,crear_archivo", [({"PB_12345"}, False), (set(), True)])
def test_pb_salta_antes_de_postback_si_inventario_o_archivo_existe(
    monkeypatch, tmp_path, inventario, crear_archivo
) -> None:
    if crear_archivo:
        (tmp_path / "2025-04-05_PB_12345.pdf").write_bytes(b"ya estaba")
    inv = Inventario(ids=inventario)
    monkeypatch.setattr(
        descargador_mod,
        "_descargar_via_popup_o_download",
        lambda *a, **k: pytest.fail("no debe disparar postback"),
    )

    resultado = descargar_doc(
        page=cast(Any, _PageFake()), fila=_fila(), codigo="PB", dir_destino=tmp_path,
        inventario=inv, tmp_path=tmp_path / "tmp.pdf", mem=cast(Any, _MemFake()),
    )

    assert resultado == Resultado.SKIP
    assert "PB_12345" in inv
