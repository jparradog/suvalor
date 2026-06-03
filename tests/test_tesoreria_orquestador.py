from __future__ import annotations

import datetime as dt
import io
from pathlib import Path
from typing import Any, cast

import pytest
from rich.console import Console

import suvalor.orquestador as orq
from suvalor.orquestador import (
    ResumenTesoreria,
    sincronizar_tesoreria,
    sincronizar_tesoreria_plan,
)
from suvalor.pagina import CuentaTesoreriaNoEncontrada
from suvalor.tesoreria import ResultadoPromocionTesoreria
from suvalor.tesoreria import construir_plan_tesoreria
from suvalor.timings import MemoriaTimings
from suvalor.tipos import MOTIVO_TESORERIA_SIN_MOVIMIENTOS


def _pdf_valido(marca: bytes = b"actual") -> bytes:
    return b"%PDF-1.4\n" + marca + (b"x" * 2100) + b"\n%%EOF"


def _xls_valido(marca: str = "actual") -> str:
    return f"Fecha\tValor\n2026-01-01\t{marca}\n"


def _plan(tmp_path: Path, *, formato: str = "xls", redownload: bool = False):
    return construir_plan_tesoreria(
        base=tmp_path,
        desde_iso="2026-01-01",
        hasta_iso="2026-01-31",
        formato=formato,
        redownload=redownload,
    )


def test_sincronizar_tesoreria_salta_final_valido_sin_exportar(tmp_path):
    plan = _plan(tmp_path, formato="xls")
    destino = plan.destinos[0]
    destino.parent.mkdir(parents=True)
    destino.write_text(_xls_valido(), encoding="utf-8")

    def exportar(_destino: Path, _formato: str) -> Path:
        pytest.fail("no debe exportar finales validos")

    resumen = sincronizar_tesoreria_plan(plan=plan, exportar=exportar)

    assert resumen.total == 1
    assert resumen.saltados == 1
    assert resumen.nuevos == 0
    assert resumen.fallidos == 0


def test_sincronizar_tesoreria_promueve_candidato_valido(tmp_path):
    plan = _plan(tmp_path, formato="xls")

    def exportar(_destino: Path, _formato: str) -> Path:
        candidato = tmp_path / "candidato.xls"
        candidato.write_text(_xls_valido("nuevo"), encoding="utf-8")
        return candidato

    resumen = sincronizar_tesoreria_plan(plan=plan, exportar=exportar)

    assert resumen.total == 1
    assert resumen.nuevos == 1
    assert resumen.saltados == 0
    assert resumen.fallidos == 0
    assert plan.destinos[0].read_text(encoding="utf-8") == _xls_valido("nuevo")
    assert not (tmp_path / "candidato.xls").exists()


def test_sincronizar_tesoreria_sin_movimientos_no_crea_final_ni_falla(tmp_path):
    plan = _plan(tmp_path, formato="xls")

    def exportar(_destino: Path, _formato: str) -> Path:
        candidato = tmp_path / "candidato.xls"
        candidato.write_text(
            "Fecha\tDocumento\tDetalle\tObservacion\tValor\t\r\n",
            encoding="utf-8",
        )
        return candidato

    resumen = sincronizar_tesoreria_plan(plan=plan, exportar=exportar)

    assert resumen.total == 1
    assert resumen.nuevos == 0
    assert resumen.saltados == 1
    assert resumen.fallidos == 0
    assert not plan.destinos[0].exists()
    assert not (tmp_path / "candidato.xls").exists()


def test_sincronizar_tesoreria_fallo_preserva_final_previo(tmp_path):
    plan = _plan(tmp_path, formato="xls", redownload=True)
    destino = plan.destinos[0]
    destino.parent.mkdir(parents=True)
    destino.write_text(_xls_valido("previo"), encoding="utf-8")

    def exportar(_destino: Path, _formato: str) -> Path:
        candidato = tmp_path / "candidato.xls"
        candidato.write_text("Fecha,Valor\n2026-01-01\n", encoding="utf-8")
        return candidato

    resumen = sincronizar_tesoreria_plan(plan=plan, exportar=exportar)

    assert resumen.total == 1
    assert resumen.nuevos == 0
    assert resumen.fallidos == 1
    assert destino.read_text(encoding="utf-8") == _xls_valido("previo")
    assert not (tmp_path / "candidato.xls").exists()


def test_sincronizar_tesoreria_both_independiente_por_formato(tmp_path):
    plan = _plan(tmp_path, formato="both", redownload=True)
    pdf_final, xls_final = plan.destinos
    xls_final.parent.mkdir(parents=True)
    xls_final.write_text(_xls_valido("previo"), encoding="utf-8")

    def exportar(_destino: Path, formato: str) -> Path:
        candidato = tmp_path / f"candidato.{formato}"
        if formato == "pdf":
            candidato.write_bytes(_pdf_valido(b"nuevo"))
        else:
            candidato.write_text("Fecha,Valor\n2026-01-01\n", encoding="utf-8")
        return candidato

    resumen = sincronizar_tesoreria_plan(plan=plan, exportar=exportar)

    assert resumen.total == 2
    assert resumen.nuevos == 1
    assert resumen.fallidos == 1
    assert pdf_final.read_bytes() == _pdf_valido(b"nuevo")
    assert xls_final.read_text(encoding="utf-8") == _xls_valido("previo")


def test_resumen_tesoreria_no_expone_account_raw(tmp_path):
    raw_account = "Cuenta Privada 123"
    plan = construir_plan_tesoreria(
        base=tmp_path,
        desde_iso="2026-01-01",
        hasta_iso="2026-01-31",
        formato="xls",
        account=raw_account,
        tag="seguro",
    )

    def exportar(_destino: Path, _formato: str) -> Path:
        raise RuntimeError(raw_account)

    resumen = sincronizar_tesoreria_plan(plan=plan, exportar=exportar)

    assert resumen.fallidos == 1
    assert raw_account not in repr(resumen)
    assert raw_account not in str(resumen.detalle_fallidos)


class FakeMem:
    def __init__(self):
        self.medidas: list[tuple[str, float]] = []

    def timeout_ms(self, _op: str) -> int:
        return 1000

    def registrar(self, op: str, ms: float) -> None:
        self.medidas.append((op, ms))


def test_sincronizar_tesoreria_page_prepara_y_exporta(monkeypatch, tmp_path):
    plan = _plan(tmp_path, formato="xls")
    llamadas: list[tuple[str, object]] = []

    monkeypatch.setattr(
        orq,
        "goto_robusto",
        lambda *args, **kwargs: llamadas.append(
            ("goto", args[1] if len(args) > 1 else kwargs.get("url"))
        ),
    )
    monkeypatch.setattr(
        orq,
        "dismiss_componentart_banner",
        lambda *args, **kwargs: llamadas.append(("banner", None)),
    )

    def preparar(
        _page, *, desde: dt.date, hasta: dt.date, account: str | None = None
    ) -> None:
        llamadas.append(("preparar", (desde, hasta, account)))

    def exportar(*, page, destino: Path, formato: str, timeout_s: float):
        llamadas.append(("exportar", (destino.name, formato, timeout_s)))
        return ResultadoPromocionTesoreria(True, "", destino)

    monkeypatch.setattr(orq, "preparar_tesoreria", preparar)
    monkeypatch.setattr(orq, "exportar_reporte_tesoreria", exportar)

    mem = FakeMem()
    resumen = sincronizar_tesoreria(
        page=cast(Any, object()),
        plan=plan,
        mem=cast(MemoriaTimings, mem),
        console=Console(file=io.StringIO()),
        account="Cuenta Privada 123",
    )

    assert resumen == ResumenTesoreria(nuevos=1, saltados=0, fallidos=0, total=1)
    assert llamadas[0][0] == "goto"
    assert llamadas[2] == (
        "preparar",
        (dt.date(2026, 1, 1), dt.date(2026, 1, 31), "Cuenta Privada 123"),
    )
    assert llamadas[3][0] == "exportar"
    assert mem.medidas[0][0] == "tesoreria"


def test_sincronizar_tesoreria_page_sin_movimientos_no_falla(monkeypatch, tmp_path):
    plan = _plan(tmp_path, formato="xls")
    monkeypatch.setattr(orq, "goto_robusto", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        orq, "dismiss_componentart_banner", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(orq, "preparar_tesoreria", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        orq,
        "exportar_reporte_tesoreria",
        lambda **kwargs: ResultadoPromocionTesoreria(
            False,
            f"{MOTIVO_TESORERIA_SIN_MOVIMIENTOS} (size=44; lineas=1)",
            kwargs["destino"],
        ),
    )

    resumen = sincronizar_tesoreria(
        page=cast(Any, object()),
        plan=plan,
        mem=cast(MemoriaTimings, FakeMem()),
        console=Console(file=io.StringIO()),
    )

    assert resumen == ResumenTesoreria(nuevos=0, saltados=1, fallidos=0, total=1)


def test_sincronizar_tesoreria_page_no_filtra_account_si_no_encuentra(
    monkeypatch, tmp_path
):
    raw_account = "Cuenta Privada 123"
    plan = construir_plan_tesoreria(
        base=tmp_path,
        desde_iso="2026-01-01",
        hasta_iso="2026-01-31",
        formato="xls",
        account=raw_account,
        tag="seguro",
    )
    monkeypatch.setattr(orq, "goto_robusto", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        orq, "dismiss_componentart_banner", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(
        orq,
        "preparar_tesoreria",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            CuentaTesoreriaNoEncontrada(raw_account)
        ),
    )

    resumen = sincronizar_tesoreria(
        page=cast(Any, object()),
        plan=plan,
        mem=cast(MemoriaTimings, FakeMem()),
        console=Console(file=io.StringIO()),
        account=raw_account,
    )

    assert resumen.fallidos == 1
    assert raw_account not in str(resumen.detalle_fallidos)
