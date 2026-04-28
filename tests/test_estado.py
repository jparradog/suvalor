"""Tests de compatibilidad con el formato de estado existente.

CRITICO: el script ya genero `_state/inventario.json` (lista de strings) y
`_state/ultima_corrida.json` (dict con `ultima_corrida` y `rangos_consultados`).
El nuevo codigo DEBE seguir leyendolos sin pelear.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from suvalor import estado as estado_mod
from suvalor.estado import (
    EstadoCorrida,
    Inventario,
    cargar_estado,
    cargar_inventario,
    guardar_estado,
    guardar_inventario,
)


@pytest.fixture
def state_dir(tmp_path, monkeypatch):
    """Redirige las rutas de estado a un tmp_path por test."""
    inv_file = tmp_path / "inventario.json"
    state_file = tmp_path / "ultima_corrida.json"
    monkeypatch.setattr(estado_mod, "STATE_DIR", tmp_path)
    monkeypatch.setattr(estado_mod, "INVENTORY_FILE", inv_file)
    monkeypatch.setattr(estado_mod, "STATE_FILE", state_file)
    monkeypatch.setattr(estado_mod, "BASE", tmp_path)  # rebuild fallback
    return tmp_path


def test_lee_inventario_formato_legacy(state_dir):
    inv_file = state_dir / "inventario.json"
    inv_file.write_text(
        json.dumps(["RC_1294144", "NC_151016", "CE_3731"]),
        encoding="utf-8",
    )
    inv = cargar_inventario()
    assert isinstance(inv, Inventario)
    assert "RC_1294144" in inv
    assert len(inv) == 3


def test_lee_ultima_corrida_formato_legacy(state_dir):
    state_file = state_dir / "ultima_corrida.json"
    # formato real visto en el repo del usuario
    state_file.write_text(json.dumps({
        "ultima_corrida": "2026-04-27",
        "rangos_consultados": [
            {
                "fecha": "2026-04-28",
                "tipos_chequeados": ["RC", "NC", "CE", "CC"],
                "rangos": "2024-Q1 a 2026-Q2 (90d cada uno)",
                "descargados_esta_corrida": 82,
                "total_inventario": 800,
            }
        ]
    }), encoding="utf-8")
    estado = cargar_estado()
    assert estado.ultima_corrida == "2026-04-27"
    assert len(estado.rangos_consultados) == 1
    # campo no estandar `tipos_chequeados` se preserva en el dict
    assert estado.rangos_consultados[0]["tipos_chequeados"] == ["RC", "NC", "CE", "CC"]


def test_round_trip_inventario(state_dir):
    inv = Inventario(ids={"RC_111", "NC_222"})
    guardar_inventario(inv)

    inv2 = cargar_inventario()
    assert inv.ids == inv2.ids


def test_round_trip_estado(state_dir):
    estado = EstadoCorrida(
        ultima_corrida="2026-04-27",
        rangos_consultados=[{"fecha": "2026-04-27", "extra": "field"}],
    )
    guardar_estado(estado)

    estado2 = cargar_estado()
    assert estado2.ultima_corrida == "2026-04-27"
    assert estado2.rangos_consultados[0]["extra"] == "field"


def test_estado_vacio_si_no_existe(state_dir):
    estado = cargar_estado()
    assert estado.ultima_corrida is None
    assert estado.rangos_consultados == []


def test_inventario_inicial_sin_archivo_y_sin_pdfs(state_dir):
    inv = cargar_inventario()
    # sin pdfs, deberia estar vacio
    assert len(inv) == 0


def test_inventario_reconstruye_desde_pdfs(state_dir):
    # crear PDFs falsos en la jerarquia esperada
    (state_dir / "2025" / "RecibosDeCaja").mkdir(parents=True)
    (state_dir / "2025" / "RecibosDeCaja" / "2025-04-12_RC_999.pdf").write_text("x")
    (state_dir / "2025" / "RecibosDeCaja" / "2025-04-13_NC_888.pdf").write_text("x")

    inv = cargar_inventario()
    assert "RC_999" in inv
    assert "NC_888" in inv
