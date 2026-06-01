from __future__ import annotations

from typing import Any, cast

from rich.console import Console

import suvalor.orquestador as orq
from suvalor.config import Config
from suvalor.estado import Inventario
from suvalor.orquestador import ResumenCorrida, _procesar_paginas
from suvalor.pagina import Fila
from suvalor.rangos import RangoFechas


def test_procesar_paginas_pasa_codigo_a_extraer_filas(monkeypatch, tmp_path) -> None:
    codigos: list[str] = []

    def fake_extraer_filas(page, codigo=None):
        codigos.append(str(codigo))
        return [Fila(idx=0, fecha="05/04/2025", doc_num="12345", valor="0")]

    monkeypatch.setattr(orq, "extraer_filas", fake_extraer_filas)
    monkeypatch.setattr(orq, "extraer_paginas", lambda page: [])
    monkeypatch.setattr(orq, "descargar_doc", lambda **kwargs: orq.Resultado.SKIP)

    resumen = ResumenCorrida()
    _procesar_paginas(
        page=cast(Any, object()), context=cast(Any, object()), codigo="PB",
        rango=RangoFechas("01/04/2025", "30/04/2025"),
        dir_destino=tmp_path, inventario=Inventario(), tmp_path=tmp_path / "tmp.pdf",
        mem=cast(Any, object()), config=Config(max_pages_per_query=1), max_docs=0,
        resumen=resumen, console=Console(file=None),
    )

    assert codigos == ["PB"]
    assert resumen.saltados == 1


def test_procesar_paginas_sanitiza_excepcion_en_detalle_fallidos(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(orq, "extraer_filas", lambda page, codigo=None: [Fila(idx=0, fecha="05/04/2025", doc_num="12345", valor="0")])
    monkeypatch.setattr(orq, "extraer_paginas", lambda page: [])

    def fake_descargar_doc(**kwargs):
        raise RuntimeError("GET https://portal/x.pdf?jwt=secreto status HTTP 504")

    monkeypatch.setattr(orq, "descargar_doc", fake_descargar_doc)
    resumen = ResumenCorrida()
    _procesar_paginas(
        page=cast(Any, object()), context=cast(Any, object()), codigo="FB",
        rango=RangoFechas("01/04/2025", "30/04/2025"),
        dir_destino=tmp_path, inventario=Inventario(), tmp_path=tmp_path / "tmp.pdf",
        mem=cast(Any, object()), config=Config(max_pages_per_query=1), max_docs=0,
        resumen=resumen, console=Console(file=None),
    )

    assert resumen.fallidos == 1
    motivo = resumen.detalle_fallidos[0][1]
    assert "https://" not in motivo
    assert "jwt=" not in motivo
    assert "secreto" not in motivo
