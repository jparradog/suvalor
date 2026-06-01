from __future__ import annotations

from typing import Any, cast

import pytest

import suvalor.descargador as descargador_mod
from suvalor.descargador import Resultado, construir_identidad_descarga, descargar_doc
from suvalor.estado import Inventario
from suvalor.pagina import Fila


MOTIVO_504 = "portal respondio HTTP 504 (CloudFront Gateway Timeout)"


class _MemFake:
    def timeout_ms(self, op: str) -> int: return 1
    def p95_ms(self, op: str) -> int: return 1
    def registrar(self, op: str, ms: float) -> None: pass


class _ContextFake:
    pages: list[object] = []


class _PageFake:
    context = _ContextFake()


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


def _pdf_valido() -> bytes:
    return b"%PDF-1.4\n" + (b"x" * 3_000) + b"\n%%EOF\n"

def _descargar(tmp_path, inv=None, retry_doc=1, motivos=None):
    return descargar_doc(
        page=cast(Any, _PageFake()), fila=_fila(), codigo="FB", dir_destino=tmp_path,
        inventario=inv if inv is not None else Inventario(), tmp_path=tmp_path / "tmp.pdf",
        mem=cast(Any, _MemFake()), retry_doc=retry_doc, motivos_fallidos=motivos,
    )

def test_descargar_doc_sanitiza_504_sin_inventario_y_con_tsv_legacy(monkeypatch, tmp_path) -> None:
    fallos = []; motivos = []; llamadas = 0

    def fake_download(*a, **k):
        nonlocal llamadas
        llamadas += 1
        return False, "GET https://portal/x.pdf?jwt=secreto status HTTP 504"

    monkeypatch.setattr(descargador_mod, "_descargar_via_popup_o_download", fake_download)
    monkeypatch.setattr(descargador_mod, "registrar_fallo", lambda *args: fallos.append(args))
    inv = Inventario()

    assert _descargar(tmp_path, inv=inv, retry_doc=0, motivos=motivos) == Resultado.FAIL
    assert llamadas == 1
    assert inv.ids == set()
    assert motivos == [("FB_12345", MOTIVO_504)]
    assert fallos and len(fallos[0]) == 3
    assert "jwt=" not in motivos[0][1] and "secreto" not in motivos[0][1]

def test_descargar_doc_borra_html_camuflado_y_no_actualiza_inventario(monkeypatch, tmp_path) -> None:
    def fake_download(page, idx, destino, timeout_s):
        destino.write_bytes(b"<html><body>504 Gateway Timeout CloudFront</body></html>")
        return True, ""

    monkeypatch.setattr(descargador_mod, "_descargar_via_popup_o_download", fake_download)
    monkeypatch.setattr(descargador_mod, "registrar_fallo", lambda *a, **k: None)
    inv = Inventario(); motivos = []

    assert _descargar(tmp_path, inv=inv, retry_doc=1, motivos=motivos) == Resultado.FAIL
    assert not (tmp_path / "2025-04-05_FB_12345.pdf").exists()
    assert inv.ids == set()
    assert motivos == [("FB_12345", MOTIVO_504)]

def test_descargar_doc_reintento_posterior_valido_actualiza_inventario_una_vez(monkeypatch, tmp_path) -> None:
    llamadas = 0

    def fake_download(page, idx, destino, timeout_s):
        nonlocal llamadas
        llamadas += 1
        destino.write_bytes(b"<html>504 Gateway Timeout CloudFront</html>" if llamadas == 1 else _pdf_valido())
        return True, ""

    monkeypatch.setattr(descargador_mod, "_descargar_via_popup_o_download", fake_download)
    monkeypatch.setattr(descargador_mod, "registrar_fallo", lambda *a, **k: None)
    inv = Inventario(); motivos = []

    assert _descargar(tmp_path, inv=inv, retry_doc=3, motivos=motivos) == Resultado.NUEVO
    assert llamadas == 2
    assert inv.ids == {"FB_12345"}
    assert motivos == []
