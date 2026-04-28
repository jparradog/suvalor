"""Tests del subcomando `sync`: argument parsing + plan de etapas.

CRITICO: NO tocan Playwright ni red. Solo validan la logica pura de
construccion del plan y del CLI (ayuda, deteccion de subcomandos, etc.).
"""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from suvalor.cli import (
    _PlanSync,
    _plan_desde_flags,
    _renderear_resumen_sync,
    app,
)
from suvalor.orquestador import (
    ResumenCartera,
    ResumenCorrida,
    ResumenExtractos,
)


runner = CliRunner()


# --------------------------------------------------------------------------- #
# _plan_desde_flags: traduce los `--no-X` a un plan de etapas                 #
# --------------------------------------------------------------------------- #


class TestPlanDesdeFlags:
    def test_default_corre_todas(self):
        plan = _plan_desde_flags(no_docs=False, no_extractos=False, no_cartera=False)
        assert plan.do_docs is True
        assert plan.do_extractos is True
        assert plan.do_cartera is True
        assert plan.nada_que_hacer() is False

    def test_no_docs_se_respeta(self):
        plan = _plan_desde_flags(no_docs=True, no_extractos=False, no_cartera=False)
        assert plan.do_docs is False
        assert plan.do_extractos is True
        assert plan.do_cartera is True

    def test_no_extractos_se_respeta(self):
        plan = _plan_desde_flags(no_docs=False, no_extractos=True, no_cartera=False)
        assert plan.do_docs is True
        assert plan.do_extractos is False
        assert plan.do_cartera is True

    def test_no_cartera_se_respeta(self):
        plan = _plan_desde_flags(no_docs=False, no_extractos=False, no_cartera=True)
        assert plan.do_docs is True
        assert plan.do_extractos is True
        assert plan.do_cartera is False

    def test_combinacion_no_docs_no_cartera(self):
        plan = _plan_desde_flags(no_docs=True, no_extractos=False, no_cartera=True)
        assert plan.do_docs is False
        assert plan.do_extractos is True
        assert plan.do_cartera is False

    def test_todo_apagado_marca_nada_que_hacer(self):
        plan = _plan_desde_flags(no_docs=True, no_extractos=True, no_cartera=True)
        assert plan.nada_que_hacer() is True


# --------------------------------------------------------------------------- #
# CLI: --help muestra `sync` y sus flags. No lanza Playwright.                #
# --------------------------------------------------------------------------- #


class TestCliHelp:
    def test_help_principal_lista_sync(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "sync" in result.stdout

    def test_help_principal_lista_subcomandos_clasicos(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        for cmd in ("descargar", "extractos", "cartera", "inventario"):
            assert cmd in result.stdout

    def test_sync_help_lista_no_docs(self):
        result = runner.invoke(app, ["sync", "--help"])
        assert result.exit_code == 0
        assert "--no-docs" in result.stdout

    def test_sync_help_lista_no_extractos(self):
        result = runner.invoke(app, ["sync", "--help"])
        assert result.exit_code == 0
        assert "--no-extractos" in result.stdout

    def test_sync_help_lista_no_cartera(self):
        result = runner.invoke(app, ["sync", "--help"])
        assert result.exit_code == 0
        assert "--no-cartera" in result.stdout

    def test_sync_help_lista_types(self):
        result = runner.invoke(app, ["sync", "--help"])
        assert result.exit_code == 0
        assert "--types" in result.stdout

    def test_sync_help_lista_max_docs(self):
        result = runner.invoke(app, ["sync", "--help"])
        assert result.exit_code == 0
        assert "--max-docs" in result.stdout


# --------------------------------------------------------------------------- #
# sync con todos los `--no-*` activos: error 2 (nada que hacer).              #
# Esto valida que el chequeo previo cortocircuita ANTES de tocar Playwright.  #
# --------------------------------------------------------------------------- #


class TestSyncSinEtapas:
    def test_todas_etapas_apagadas_falla_con_exit_2(self):
        # Si entrara al try/with abrir_navegador() se intentaria lanzar Chrome
        # y el test tronaria con timeout. Si llega a exit_code=2 antes,
        # significa que _plan_desde_flags + el chequeo de nada_que_hacer
        # cortocircuitan correctamente.
        result = runner.invoke(
            app, ["sync", "--no-docs", "--no-extractos", "--no-cartera"]
        )
        assert result.exit_code == 2
        assert "ERROR" in result.stdout
        assert "deshabilitadas" in result.stdout


# --------------------------------------------------------------------------- #
# _renderear_resumen_sync no truena con resultados arbitrarios.               #
# --------------------------------------------------------------------------- #


class TestRenderearResumen:
    def test_con_los_tres_ok(self, tmp_path):
        plan = _PlanSync(do_docs=True, do_extractos=True, do_cartera=True)
        rdocs = ResumenCorrida(nuevos=5, saltados=10, fallidos=0)
        rext = ResumenExtractos(nuevos=2, saltados=4, fallidos=0)
        rcart = ResumenCartera(
            ok=True, destino=tmp_path / "snap.xls", size_kb=88.0, error=None,
        )
        # No assert - solo validamos que no levante.
        _renderear_resumen_sync(
            plan=plan,
            res_docs=rdocs, err_docs=None,
            res_ext=rext, err_ext=None,
            res_cart=rcart, err_cart=None,
        )

    def test_con_etapas_skipped(self, tmp_path):
        plan = _PlanSync(do_docs=False, do_extractos=False, do_cartera=True)
        rcart = ResumenCartera(
            ok=True, destino=tmp_path / "snap.xls", size_kb=88.0, error=None,
        )
        _renderear_resumen_sync(
            plan=plan,
            res_docs=None, err_docs=None,
            res_ext=None, err_ext=None,
            res_cart=rcart, err_cart=None,
        )

    def test_con_errores_parciales_no_truena(self):
        plan = _PlanSync(do_docs=True, do_extractos=True, do_cartera=True)
        _renderear_resumen_sync(
            plan=plan,
            res_docs=None, err_docs="sesion expirada",
            res_ext=ResumenExtractos(nuevos=1, saltados=0, fallidos=0), err_ext=None,
            res_cart=None, err_cart="No pude llegar a portafolio",
        )


# --------------------------------------------------------------------------- #
# Subcomandos individuales: --help no truena (smoke test del CLI).            #
# Confirma que el refactor (envoltorios -> funciones core) no rompio nada.    #
# --------------------------------------------------------------------------- #


class TestSubcomandosClasicos:
    def test_descargar_help_ok(self):
        result = runner.invoke(app, ["descargar", "--help"])
        assert result.exit_code == 0
        assert "--types" in result.stdout
        assert "--backfill" in result.stdout

    def test_extractos_help_ok(self):
        result = runner.invoke(app, ["extractos", "--help"])
        assert result.exit_code == 0
        assert "--solo" in result.stdout
        assert "--redownload" in result.stdout

    def test_cartera_help_ok(self):
        result = runner.invoke(app, ["cartera", "--help"])
        assert result.exit_code == 0
        assert "--account" in result.stdout
