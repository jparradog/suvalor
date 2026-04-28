"""Tests de la memoria adaptativa de timings (no requiere Playwright)."""
from __future__ import annotations

from pathlib import Path

import pytest

from suvalor.timings import (
    BUFFER_MS,
    DEFAULTS_MS,
    MINIMO_MS,
    Cronometro,
    MemoriaTimings,
    StatsOperacion,
    medir,
)


@pytest.fixture
def mem(tmp_path: Path) -> MemoriaTimings:
    return MemoriaTimings(path=tmp_path / "timings.json")


def test_sin_historial_usa_default(mem: MemoriaTimings):
    # con n_total=0 devuelve el default conservador
    assert mem.timeout_ms("descarga") >= DEFAULTS_MS["descarga"]
    assert mem.timeout_ms("consulta") >= DEFAULTS_MS["consulta"]


def test_registrar_actualiza_percentiles(mem: MemoriaTimings):
    for v in [1000, 2000, 3000, 4000, 5000]:
        mem.registrar("consulta", v)
    s = mem.stats["consulta"]
    assert s.n_total == 5
    assert s.p50 == pytest.approx(3000)
    assert s.p95 == pytest.approx(4800)
    assert s.max_visto == 5000


def test_timeout_es_p95_mas_buffer_con_suficiente_historia(mem: MemoriaTimings):
    for v in [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000]:
        mem.registrar("descarga", v)
    s = mem.stats["descarga"]
    timeout = mem.timeout_ms("descarga")
    # debe ser >= p95 + buffer (o el piso)
    assert timeout >= s.p95 + BUFFER_MS - 1


def test_piso_minimo_se_respeta(mem: MemoriaTimings):
    # registrar valores bajisimos: el timeout no debe caer debajo del piso
    for v in [10, 20, 30, 40, 50]:
        mem.registrar("descarga", v)
    timeout = mem.timeout_ms("descarga")
    assert timeout >= MINIMO_MS["descarga"]


def test_ventana_movil(mem: MemoriaTimings):
    # registramos mas que el WINDOW_SIZE para validar que la ventana descarta
    for v in range(1, 80):
        mem.registrar("consulta", v * 100.0)
    s = mem.stats["consulta"]
    assert s.n_total == 79  # contador acumulado
    assert len(s.muestras) <= 50  # ventana movil


def test_persistencia_round_trip(tmp_path: Path):
    p = tmp_path / "timings.json"
    m1 = MemoriaTimings(path=p)
    for v in [1500, 2500, 3500, 4500]:
        m1.registrar("consulta", v)
    m1.guardar()

    m2 = MemoriaTimings(path=p)
    s = m2.stats["consulta"]
    assert s.n_total == 4
    assert s.p50 == pytest.approx(3000)


def test_archivo_corrupto_no_revienta(tmp_path: Path):
    p = tmp_path / "timings.json"
    p.write_text("{not valid json", encoding="utf-8")
    # no debe lanzar
    m = MemoriaTimings(path=p)
    assert "consulta" in m.stats


def test_cronometro_registra(mem: MemoriaTimings):
    with medir(mem, "consulta") as c:
        # operacion ficticia
        sum(range(10000))
    assert c.duracion_ms >= 0
    assert mem.stats["consulta"].n_total == 1


def test_cronometro_registra_aun_con_excepcion(mem: MemoriaTimings):
    with pytest.raises(RuntimeError):
        with medir(mem, "consulta"):
            raise RuntimeError("boom")
    # deberia haber registrado igual
    assert mem.stats["consulta"].n_total == 1


def test_resumen_str(mem: MemoriaTimings):
    assert "default" in mem.resumen("consulta")  # sin historia
    for v in [1000, 2000, 3000]:
        mem.registrar("consulta", v)
    assert "p50=" in mem.resumen("consulta")
