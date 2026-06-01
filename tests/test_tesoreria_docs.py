from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _texto(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8").lower()


def test_readme_documenta_tesoreria_staging_privacidad_y_sync_final():
    readme = _texto("README.md")

    assert "suvalor tesoreria" in readme
    assert "login manual" in readme
    assert "fail-closed" in readme
    assert "--tag" in readme
    assert "seguro" in readme
    assert "--account" in readme
    assert "texto real de la cuenta nunca" in readme
    assert "rutas, logs ni resumenes" in readme
    assert "--redownload" in readme
    assert "sync" in readme
    assert "--no-tesoreria" in readme
    assert "sin datos" in readme
    assert "no crea archivos de exito falsos" in readme

    muestras_prohibidas = [
        "cuenta privada 123",
        "texto privado",
        "123456789",
        "000123456789",
    ]
    for muestra in muestras_prohibidas:
        assert muestra not in readme


def test_site_notes_declara_sin_datos_bloqueado_y_fallo_conservador():
    site_notes = _texto("docs/SITE_NOTES.md")

    assert "movimientos de tesoreria" in site_notes
    assert "falta marcador redacted de sin datos" in site_notes
    assert "fallo conservador" in site_notes
    assert "no crear archivos de exito falsos" in site_notes
