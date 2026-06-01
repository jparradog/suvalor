from __future__ import annotations

from pathlib import Path

import pytest

from suvalor.tesoreria import (
    debe_descargar_tesoreria,
    promover_candidato_tesoreria,
)


def _pdf_valido(marca: bytes = b"actual") -> bytes:
    return b"%PDF-1.4\n" + marca + (b"x" * 2100) + b"\n%%EOF"


def _xls_valido(marca: str = "actual") -> str:
    return f"Fecha\tValor\n2026-01-01\t{marca}\n"


def test_debe_descargar_salta_final_valido_y_redownload_fuerza(tmp_path):
    final = tmp_path / "Tesoreria" / "2026" / "movimientos.xls"
    final.parent.mkdir(parents=True)
    final.write_text(_xls_valido(), encoding="utf-8")

    assert debe_descargar_tesoreria(final, formato="xls", redownload=False) is False
    assert debe_descargar_tesoreria(final, formato="xls", redownload=True) is True


def test_debe_descargar_reintenta_final_invalido_sin_borrarlo(tmp_path):
    final = tmp_path / "Tesoreria" / "2026" / "movimientos.xls"
    final.parent.mkdir(parents=True)
    final.write_text("<html><body>Iniciar sesion</body></html>", encoding="utf-8")

    assert debe_descargar_tesoreria(final, formato="xls", redownload=False) is True
    assert final.exists()


def test_debe_descargar_valida_formato_aunque_redownload(tmp_path):
    final = tmp_path / "Tesoreria" / "2026" / "movimientos.csv"

    with pytest.raises(ValueError, match="formato debe ser pdf o xls"):
        debe_descargar_tesoreria(final, formato="csv", redownload=True)


def test_debe_descargar_falla_cerrado_si_validacion_lanza_oserror(
    monkeypatch, tmp_path
):
    import suvalor.tesoreria as tesoreria

    final = tmp_path / "Tesoreria" / "2026" / "movimientos.xls"

    def falla(_path: Path, _tipo: str):
        raise OSError("bloqueado")

    monkeypatch.setattr(tesoreria, "verificar_descarga", falla)

    assert debe_descargar_tesoreria(final, formato="xls", redownload=False) is True


def test_promueve_candidato_valido_al_destino_final(tmp_path):
    candidato = tmp_path / "descarga.tmp"
    destino = tmp_path / "Tesoreria" / "2026" / "movimientos.xls"
    candidato.write_text(_xls_valido("nuevo"), encoding="utf-8")

    resultado = promover_candidato_tesoreria(candidato, destino, formato="xls")

    assert resultado.ok is True
    assert resultado.motivo == ""
    assert destino.read_text(encoding="utf-8") == _xls_valido("nuevo")
    assert not candidato.exists()


def test_candidato_invalido_se_elimina_y_preserva_final_valido(tmp_path):
    candidato = tmp_path / "descarga.tmp"
    destino = tmp_path / "Tesoreria" / "2026" / "movimientos.xls"
    destino.parent.mkdir(parents=True)
    destino.write_text(_xls_valido("previo"), encoding="utf-8")
    candidato.write_text("<html><body>Iniciar sesion</body></html>", encoding="utf-8")

    resultado = promover_candidato_tesoreria(candidato, destino, formato="xls")

    assert resultado.ok is False
    assert resultado.motivo
    assert destino.read_text(encoding="utf-8") == _xls_valido("previo")
    assert not candidato.exists()


def test_error_de_validacion_elimina_candidato_y_preserva_final(
    monkeypatch, tmp_path
):
    import suvalor.tesoreria as tesoreria

    candidato = tmp_path / "descarga.tmp"
    destino = tmp_path / "Tesoreria" / "2026" / "movimientos.xls"
    destino.parent.mkdir(parents=True)
    destino.write_text(_xls_valido("previo"), encoding="utf-8")
    candidato.write_text(_xls_valido("nuevo"), encoding="utf-8")

    def falla(_path: Path, _tipo: str):
        raise OSError("bloqueado")

    monkeypatch.setattr(tesoreria, "verificar_descarga", falla)

    resultado = promover_candidato_tesoreria(candidato, destino, formato="xls")

    assert resultado.ok is False
    assert "bloqueado" in resultado.motivo
    assert destino.read_text(encoding="utf-8") == _xls_valido("previo")
    assert not candidato.exists()


def test_error_al_promover_elimina_candidato_y_preserva_final(
    monkeypatch, tmp_path
):
    candidato = tmp_path / "descarga.tmp"
    destino = tmp_path / "Tesoreria" / "2026" / "movimientos.xls"
    destino.parent.mkdir(parents=True)
    destino.write_text(_xls_valido("previo"), encoding="utf-8")
    candidato.write_text(_xls_valido("nuevo"), encoding="utf-8")

    def falla_replace(self: Path, target: Path):
        raise OSError("bloqueado")

    monkeypatch.setattr(Path, "replace", falla_replace)

    resultado = promover_candidato_tesoreria(candidato, destino, formato="xls")

    assert resultado.ok is False
    assert "bloqueado" in resultado.motivo
    assert destino.read_text(encoding="utf-8") == _xls_valido("previo")
    assert not candidato.exists()


def test_candidato_igual_a_destino_no_elimina_final(tmp_path):
    destino = tmp_path / "Tesoreria" / "2026" / "movimientos.xls"
    destino.parent.mkdir(parents=True)
    destino.write_text(_xls_valido("previo"), encoding="utf-8")

    resultado = promover_candidato_tesoreria(destino, destino, formato="xls")

    assert resultado.ok is False
    assert "mismo archivo" in resultado.motivo
    assert destino.read_text(encoding="utf-8") == _xls_valido("previo")


def test_redownload_both_preserva_xls_previo_si_falla_candidato_xls(tmp_path):
    pdf_final = tmp_path / "Tesoreria" / "2026" / "movimientos.pdf"
    xls_final = tmp_path / "Tesoreria" / "2026" / "movimientos.xls"
    pdf_final.parent.mkdir(parents=True)
    pdf_final.write_bytes(_pdf_valido(b"pdf-previo"))
    xls_final.write_text(_xls_valido("xls-previo"), encoding="utf-8")

    pdf_candidato = tmp_path / "pdf.tmp"
    xls_candidato = tmp_path / "xls.tmp"
    pdf_candidato.write_bytes(_pdf_valido(b"pdf-nuevo"))
    xls_candidato.write_text("Fecha,Valor\n2026-01-01\n", encoding="utf-8")

    pdf_resultado = promover_candidato_tesoreria(
        pdf_candidato, pdf_final, formato="pdf"
    )
    xls_resultado = promover_candidato_tesoreria(
        xls_candidato, xls_final, formato="xls"
    )

    assert pdf_resultado.ok is True
    assert xls_resultado.ok is False
    assert pdf_final.read_bytes() == _pdf_valido(b"pdf-nuevo")
    assert xls_final.read_text(encoding="utf-8") == _xls_valido("xls-previo")
    assert not pdf_candidato.exists()
    assert not xls_candidato.exists()
