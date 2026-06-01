from __future__ import annotations

from pathlib import Path

import pytest

from suvalor.orquestador import sincronizar_tesoreria_plan
from suvalor.tesoreria import construir_plan_tesoreria


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
