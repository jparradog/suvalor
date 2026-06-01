from __future__ import annotations

from pathlib import Path

from suvalor.descargador import guardar_reporte_tesoreria


def _xls_valido(marca: str = "actual") -> str:
    return f"Fecha\tValor\n2026-01-01\t{marca}\n"


def _pdf_valido(marca: bytes = b"actual") -> bytes:
    return b"%PDF-1.4\n" + marca + (b"x" * 2100) + b"\n%%EOF"


def test_guardar_reporte_tesoreria_usa_candidato_y_promueve_valido(tmp_path):
    destino = tmp_path / "Tesoreria" / "2026" / "movimientos.xls"
    candidatos: list[Path] = []

    def guardar(candidato: Path) -> None:
        candidatos.append(candidato)
        candidato.write_text(_xls_valido("nuevo"), encoding="utf-8")

    resultado = guardar_reporte_tesoreria(
        destino=destino,
        formato="xls",
        guardar=guardar,
    )

    assert resultado.ok is True
    assert destino.read_text(encoding="utf-8") == _xls_valido("nuevo")
    assert candidatos == [destino.with_name(f"{destino.name}.tmp")]
    assert not candidatos[0].exists()


def test_guardar_reporte_tesoreria_limpia_candidato_si_exportador_falla(tmp_path):
    destino = tmp_path / "Tesoreria" / "2026" / "movimientos.xls"
    destino.parent.mkdir(parents=True)
    destino.write_text(_xls_valido("previo"), encoding="utf-8")

    def guardar(candidato: Path) -> None:
        candidato.write_text("parcial", encoding="utf-8")
        raise RuntimeError("Cuenta Privada 123")

    resultado = guardar_reporte_tesoreria(
        destino=destino,
        formato="xls",
        guardar=guardar,
    )

    assert resultado.ok is False
    assert resultado.motivo == "exportacion fallo"
    assert destino.read_text(encoding="utf-8") == _xls_valido("previo")
    assert not destino.with_name(f"{destino.name}.tmp").exists()


def test_guardar_reporte_tesoreria_elimina_candidato_obsoleto(tmp_path):
    destino = tmp_path / "Tesoreria" / "2026" / "movimientos.xls"
    candidato = destino.with_name(f"{destino.name}.tmp")
    candidato.parent.mkdir(parents=True)
    candidato.write_text("basura previa", encoding="utf-8")

    def guardar(nuevo_candidato: Path) -> None:
        assert nuevo_candidato == candidato
        nuevo_candidato.write_text(_xls_valido("nuevo"), encoding="utf-8")

    resultado = guardar_reporte_tesoreria(
        destino=destino,
        formato="xls",
        guardar=guardar,
    )

    assert resultado.ok is True
    assert destino.read_text(encoding="utf-8") == _xls_valido("nuevo")


def test_guardar_reporte_tesoreria_promueve_pdf_valido(tmp_path):
    destino = tmp_path / "Tesoreria" / "2026" / "movimientos.pdf"

    def guardar(candidato: Path) -> None:
        candidato.write_bytes(_pdf_valido(b"nuevo"))

    resultado = guardar_reporte_tesoreria(
        destino=destino,
        formato="pdf",
        guardar=guardar,
    )

    assert resultado.ok is True
    assert destino.read_bytes() == _pdf_valido(b"nuevo")


def test_guardar_reporte_tesoreria_rechaza_formato_invalido_sin_exportar(tmp_path):
    destino = tmp_path / "Tesoreria" / "2026" / "movimientos.csv"
    llamadas = 0

    def guardar(candidato: Path) -> None:
        nonlocal llamadas
        llamadas += 1
        candidato.write_text("x", encoding="utf-8")

    resultado = guardar_reporte_tesoreria(
        destino=destino,
        formato="csv",
        guardar=guardar,
    )

    assert resultado.ok is False
    assert resultado.motivo == "formato invalido"
    assert llamadas == 0
    assert not destino.exists()
    assert not destino.with_name(f"{destino.name}.tmp").exists()


def test_guardar_reporte_tesoreria_reporta_error_si_no_crea_directorio(
    monkeypatch, tmp_path
):
    destino = tmp_path / "Tesoreria" / "2026" / "movimientos.xls"
    mkdir_original = Path.mkdir

    def falla_mkdir(self: Path, *args, **kwargs) -> None:
        if self == destino.parent:
            raise OSError("bloqueado")
        mkdir_original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", falla_mkdir)

    resultado = guardar_reporte_tesoreria(
        destino=destino,
        formato="xls",
        guardar=lambda _candidato: None,
    )

    assert resultado.ok is False
    assert resultado.motivo == "no pude preparar candidato"
    assert not destino.exists()
