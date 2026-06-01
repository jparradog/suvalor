"""Memoria adaptativa de tiempos de operaciones.

Idea: el sitio es lento y variable; en vez de hardcodear `wait_for_timeout(8000)`
dejamos que el script aprenda cuanto tarda en promedio cada operacion y use
`p95 + buffer` como timeout, con un piso configurable.

Operaciones medidas (claves):
    - "consulta"      tiempo desde click "Consultar" hasta que aparece la grilla.
    - "descarga"      tiempo desde el postBack `Select$N` hasta que aparece el PDF.
    - "page_change"   tiempo desde click en pagina N hasta que la grilla recarga.
    - "navegacion"    `goto` a la pagina de consulta.
    - "extracto"      GET de `pdfExtractoConsolidado.aspx?id=...` -> archivo en disco.
    - "cartera"       click `btnExcel` -> `Portafolio.xls` en disco.

Persistencia: `_state/timings.json`. Por cada operacion se guarda una ventana
movil de las ultimas N=50 mediciones (en milisegundos) y los percentiles
calculados. Si el archivo no existe, partimos de los defaults conservadores.
"""

from __future__ import annotations

import json
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .tipos import TIMINGS_FILE

# Tamano de ventana movil (cuantas mediciones recientes guardamos).
WINDOW_SIZE = 50

# Defaults conservadores (ms) — se usan cuando aun no hay historial.
# Heredados del monolito (8s consulta, 15s descarga, 7s page change).
DEFAULTS_MS: dict[str, int] = {
    "consulta": 8_000,
    "descarga": 15_000,
    "page_change": 7_000,
    "navegacion": 5_000,
    # Subcomandos nuevos:
    "extracto": 8_000,  # GET de pdfExtractoConsolidado.aspx?id=...
    "cartera": 10_000,  # POST btnExcel -> Portafolio.xls
    "tesoreria": 10_000,  # POST export Tesoreria -> PDF/XLS
}

# Piso minimo (ms) — nunca esperar menos que esto, aunque el p95 sea bajisimo.
MINIMO_MS: dict[str, int] = {
    "consulta": 3_000,
    "descarga": 5_000,
    "page_change": 3_000,
    "navegacion": 2_000,
    "extracto": 4_000,
    "cartera": 4_000,
    "tesoreria": 4_000,
}

# Buffer agregado al p95 para fijar el timeout maximo (ms).
BUFFER_MS = 2_500


def _percentile(values: list[float], p: float) -> float:
    """Percentil p (0..1) por interpolacion lineal. `values` debe estar ordenado."""
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    rank = p * (len(values) - 1)
    lo = int(rank)
    hi = min(lo + 1, len(values) - 1)
    frac = rank - lo
    return values[lo] + (values[hi] - values[lo]) * frac


@dataclass
class StatsOperacion:
    """Estadisticas rodantes de una operacion."""

    muestras: deque[float] = field(default_factory=lambda: deque(maxlen=WINDOW_SIZE))
    p50: float = 0.0
    p90: float = 0.0
    p95: float = 0.0
    max_visto: float = 0.0
    n_total: int = 0  # contador acumulado (no solo la ventana)

    def registrar(self, ms: float) -> None:
        self.muestras.append(ms)
        self.n_total += 1
        if ms > self.max_visto:
            self.max_visto = ms
        ordenados = sorted(self.muestras)
        self.p50 = _percentile(ordenados, 0.50)
        self.p90 = _percentile(ordenados, 0.90)
        self.p95 = _percentile(ordenados, 0.95)

    def to_dict(self) -> dict:
        return {
            "muestras": list(self.muestras),
            "p50": round(self.p50, 1),
            "p90": round(self.p90, 1),
            "p95": round(self.p95, 1),
            "max_visto": round(self.max_visto, 1),
            "n_total": self.n_total,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StatsOperacion":
        s = cls()
        muestras = d.get("muestras", [])
        s.muestras = deque(muestras, maxlen=WINDOW_SIZE)
        s.p50 = float(d.get("p50", 0))
        s.p90 = float(d.get("p90", 0))
        s.p95 = float(d.get("p95", 0))
        s.max_visto = float(d.get("max_visto", 0))
        s.n_total = int(d.get("n_total", len(muestras)))
        return s


class MemoriaTimings:
    """Repositorio de stats por operacion + helpers para medir y consultar."""

    def __init__(self, path: Path = TIMINGS_FILE) -> None:
        self.path = path
        self.stats: dict[str, StatsOperacion] = {}
        self._cargar()

    # ------------ persistencia ------------ #
    def _cargar(self) -> None:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self.stats = {k: StatsOperacion.from_dict(v) for k, v in data.items()}
            except (json.JSONDecodeError, ValueError):
                # archivo corrupto -> empezamos limpio
                self.stats = {}
        for op in DEFAULTS_MS:
            self.stats.setdefault(op, StatsOperacion())

    def guardar(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v.to_dict() for k, v in self.stats.items()}
        self.path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ------------ API publica ------------ #
    def registrar(self, op: str, ms: float) -> None:
        self.stats.setdefault(op, StatsOperacion()).registrar(ms)

    def p95_ms(self, op: str) -> float:
        s = self.stats.get(op)
        if not s or s.n_total == 0:
            return float(DEFAULTS_MS.get(op, 5_000))
        return s.p95

    def timeout_ms(self, op: str) -> float:
        """Timeout sugerido = max(piso, p95 + buffer, default si sin historia)."""
        s = self.stats.get(op)
        piso = MINIMO_MS.get(op, 2_000)
        if not s or s.n_total < 3:  # poca historia -> usar default
            return max(float(DEFAULTS_MS.get(op, 5_000)), piso)
        return max(s.p95 + BUFFER_MS, piso)

    def wait_ms(self, op: str) -> float:
        """Cuanto esperar tipicamente (p50) — para estimar UX, no bloqueos duros."""
        s = self.stats.get(op)
        if not s or s.n_total < 3:
            return float(DEFAULTS_MS.get(op, 5_000)) * 0.6
        return max(s.p50, MINIMO_MS.get(op, 1_000))

    def resumen(self, op: str) -> str:
        s = self.stats.get(op)
        if not s or s.n_total == 0:
            d = DEFAULTS_MS.get(op, 5_000)
            return f"sin historial (default {d / 1000:.1f}s)"
        return (
            f"p50={s.p50 / 1000:.1f}s p95={s.p95 / 1000:.1f}s "
            f"max={s.max_visto / 1000:.1f}s n={s.n_total}"
        )

    def operaciones(self) -> Iterable[str]:
        return self.stats.keys()


# --------------------------------------------------------------------------- #
# Context manager para medir.                                                 #
# --------------------------------------------------------------------------- #


class Cronometro:
    """`with mem.medir("consulta") as c: ...`  -> registra duracion al salir."""

    def __init__(self, mem: MemoriaTimings, op: str) -> None:
        self.mem = mem
        self.op = op
        self.t0: float = 0.0
        self.duracion_ms: float = 0.0

    def __enter__(self) -> "Cronometro":
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.duracion_ms = (time.perf_counter() - self.t0) * 1000.0
        # registramos incluso si hubo excepcion: nos interesa el tiempo real
        # transcurrido para no quedarnos cortos en el siguiente intento.
        self.mem.registrar(self.op, self.duracion_ms)


def medir(mem: MemoriaTimings, op: str) -> Cronometro:
    return Cronometro(mem, op)
