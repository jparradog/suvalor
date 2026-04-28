"""Tests del inventario de extractos (subcomando `extractos`)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from suvalor import estado as estado_mod
from suvalor.estado import (
    InventarioExtractos,
    cargar_inventario_extractos,
    guardar_inventario_extractos,
)


@pytest.fixture
def state_dir(tmp_path, monkeypatch):
    """Redirige las rutas de estado y de Extractos/ a un tmp_path por test."""
    inv_file = tmp_path / "inventario_extractos.json"
    extractos_dir = tmp_path / "Extractos"
    monkeypatch.setattr(estado_mod, "STATE_DIR", tmp_path)
    monkeypatch.setattr(estado_mod, "INVENTORY_EXTRACTOS_FILE", inv_file)
    monkeypatch.setattr(estado_mod, "EXTRACTOS_DIR", extractos_dir)
    return tmp_path


def test_inventario_extractos_vacio_si_no_existe_nada(state_dir):
    inv = cargar_inventario_extractos()
    assert isinstance(inv, InventarioExtractos)
    assert len(inv) == 0


def test_inventario_extractos_round_trip(state_dir):
    inv = InventarioExtractos(ids={"2025-04", "2025-05", "2026-01"})
    guardar_inventario_extractos(inv)

    inv2 = cargar_inventario_extractos()
    assert inv2.ids == {"2025-04", "2025-05", "2026-01"}
    assert "2025-04" in inv2
    assert "2099-12" not in inv2


def test_inventario_extractos_lee_legacy_lista(state_dir):
    f = state_dir / "inventario_extractos.json"
    f.write_text(json.dumps(["2025-10", "2025-11", "2025-12"]), encoding="utf-8")
    inv = cargar_inventario_extractos()
    assert inv.ids == {"2025-10", "2025-11", "2025-12"}


def test_inventario_extractos_reconstruye_desde_pdfs(state_dir):
    base = state_dir / "Extractos"
    (base / "2025").mkdir(parents=True)
    (base / "2026").mkdir(parents=True)
    (base / "2025" / "2025-10_extracto.pdf").write_text("x")
    (base / "2025" / "2025-11_extracto.pdf").write_text("x")
    (base / "2025" / "2025-12_extracto.pdf").write_text("x")
    (base / "2026" / "2026-01_extracto.pdf").write_text("x")
    # un archivo que no debe matchear
    (base / "2025" / "otra_cosa.pdf").write_text("x")

    inv = cargar_inventario_extractos()
    assert inv.ids == {"2025-10", "2025-11", "2025-12", "2026-01"}


def test_inventario_extractos_save_creates_state_dir(tmp_path, monkeypatch):
    nuevo = tmp_path / "nueva_state"
    inv_file = nuevo / "inventario_extractos.json"
    monkeypatch.setattr(estado_mod, "STATE_DIR", nuevo)
    monkeypatch.setattr(estado_mod, "INVENTORY_EXTRACTOS_FILE", inv_file)

    inv = InventarioExtractos(ids={"2024-01"})
    guardar_inventario_extractos(inv)
    assert inv_file.exists()
    data = json.loads(inv_file.read_text(encoding="utf-8"))
    assert data == ["2024-01"]


def test_inventario_extractos_add_y_contains():
    inv = InventarioExtractos()
    assert len(inv) == 0
    inv.add("2025-04")
    assert "2025-04" in inv
    assert "2025-05" not in inv
    inv.add("2025-04")  # idempotente (set)
    assert len(inv) == 1


def test_inventario_extractos_archivo_corrupto_fallback(state_dir):
    # archivo no parseable: extractor por regex de YYYY-MM en strings
    f = state_dir / "inventario_extractos.json"
    f.write_text('["2025-04", "2025-05", broken not closed', encoding="utf-8")
    inv = cargar_inventario_extractos()
    assert "2025-04" in inv
    assert "2025-05" in inv
