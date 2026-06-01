from __future__ import annotations

from pathlib import Path


SITE_NOTES = Path("docs/SITE_NOTES.md")


def _site_notes() -> str:
    return SITE_NOTES.read_text(encoding="utf-8").lower()


def test_retefuente_esta_documentado_como_investigacion_deshabilitada() -> None:
    texto = _site_notes()

    assert "retefuente" in texto
    assert "investigacion" in texto
    assert "deshabil" in texto or "no soport" in texto


def test_retefuente_registra_endpoint_controles_y_probe_inconclusivo() -> None:
    texto = _site_notes()

    assert "operaciones/retefuente.aspx" in texto
    assert "ddlanio" in texto or "ddlañ" in texto
    assert "btndescargarpdf" in texto
    assert "no download" in texto or "sin descarga" in texto
    assert "no popup" in texto or "sin popup" in texto


def test_retefuente_exige_evidencia_antes_de_automatizar() -> None:
    texto = _site_notes()

    assert "devtools" in texto or "network" in texto or "red" in texto
    assert "content-type" in texto
    assert "status" in texto or "estado http" in texto
    assert "%pdf-" in texto
    assert "%%eof" in texto
    assert "sin certificado" in texto or "no-certificate" in texto


def test_retefuente_expiracion_sesion_no_automatiza_login() -> None:
    texto = _site_notes()

    assert "sesion expirada" in texto or "session-expired" in texto
    assert "otp" in texto
    assert "captcha" in texto
    assert "teclado virtual" in texto
    assert "no automat" in texto


def test_retefuente_privacidad_y_redaccion() -> None:
    texto = _site_notes()

    for termino in [
        "ids de cliente",
        "coyd",
        "numeros de cuenta",
        "nombres",
        "screenshots",
        "paths personales",
        "credenciales",
    ]:
        assert termino in texto


def test_gmf_esta_fuera_de_alcance() -> None:
    texto = _site_notes()

    assert "gmf" in texto
    assert "fuera de alcance" in texto or "out of scope" in texto
    assert "mensajes.aspx" in texto
