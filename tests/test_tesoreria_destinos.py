from __future__ import annotations

import datetime as dt

from suvalor.tesoreria import (
    construir_destino_tesoreria,
    construir_plan_tesoreria,
    debe_descargar_tesoreria,
    promover_candidato_tesoreria,
)
from suvalor.tipos import TESORERIA_DIR, TESORERIA_FORMATOS_EXPORT, TESORERIA_TMP_SUFFIX


def _xls_valido(marca: str = "actual") -> str:
    return f"Fecha\tValor\n2026-01-01\t{marca}\n"


def test_destinos_tesoreria_usan_constantes_y_no_account_raw(tmp_path):
    plan = construir_plan_tesoreria(
        base=tmp_path,
        desde_iso="2026-01-01",
        hasta_iso="2026-01-31",
        formato="xls",
        account="Cuenta Privada 123",
        tag="cuenta-corta",
    )
    destino = plan.destinos[0]

    assert TESORERIA_FORMATOS_EXPORT == ("pdf", "xls")
    assert TESORERIA_TMP_SUFFIX == ".tmp"
    assert destino == (
        tmp_path
        / TESORERIA_DIR.name
        / "2026"
        / "2026-01-01_2026-01-31_movimientos_tesoreria_cuenta-corta.xls"
    )
    relativo = str(destino.relative_to(tmp_path))
    assert "Cuenta Privada" not in relativo
    assert "123" not in relativo


def test_destinos_tesoreria_saltan_final_valido(tmp_path):
    destino = construir_destino_tesoreria(
        base=tmp_path,
        desde=dt.date(2026, 1, 1),
        hasta=dt.date(2026, 1, 31),
        formato="xls",
    )
    destino.parent.mkdir(parents=True)
    destino.write_text(_xls_valido("previo"), encoding="utf-8")

    assert debe_descargar_tesoreria(destino, formato="xls") is False


def test_destinos_tesoreria_reemplazan_final_invalido_solo_con_candidato_valido(
    tmp_path,
):
    destino = construir_destino_tesoreria(
        base=tmp_path,
        desde=dt.date(2026, 1, 1),
        hasta=dt.date(2026, 1, 31),
        formato="xls",
    )
    destino.parent.mkdir(parents=True)
    destino.write_text("<html><body>Iniciar sesion</body></html>", encoding="utf-8")
    candidato = tmp_path / "candidato.xls"
    candidato.write_text(_xls_valido("nuevo"), encoding="utf-8")

    assert debe_descargar_tesoreria(destino, formato="xls") is True
    resultado = promover_candidato_tesoreria(candidato, destino, formato="xls")

    assert resultado.ok is True
    assert destino.read_text(encoding="utf-8") == _xls_valido("nuevo")
