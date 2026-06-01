"""Tests del subcomando `sync`: argument parsing + plan de etapas.

CRITICO: NO tocan Playwright ni red. Solo validan la logica pura de
construccion del plan y del CLI (ayuda, deteccion de subcomandos, etc.).
"""

from __future__ import annotations

import pytest
import typer
from typer.testing import CliRunner

import suvalor.cli as cli_mod
from suvalor.cli import (
    _PlanSync,
    _parsear_tipos,
    _plan_desde_flags,
    _renderear_resumen_sync,
    app,
)
from suvalor.config import Config, TEMPLATE_TOML, escribir_template
from suvalor.tipos import (
    TIPOS_DEFAULT,
    TIPOS_LEGACY_NO_DISPONIBLES,
    TIPOS_SELECTOR_ACTUALES,
)
from suvalor.orquestador import (
    ResumenCartera,
    ResumenCorrida,
    ResumenExtractos,
)


runner = CliRunner()


# --------------------------------------------------------------------------- #
# Disponibilidad de tipos de documentos                                       #
# --------------------------------------------------------------------------- #


class TestTiposDocumentosDisponibles:
    def test_defaults_excluyen_cc(self):
        assert TIPOS_DEFAULT == ["RC", "NC", "CE"]
        assert Config().tipos_default == ["RC", "NC", "CE"]
        assert "CC" not in TIPOS_DEFAULT
        assert TIPOS_LEGACY_NO_DISPONIBLES == {"CC"}
        assert TIPOS_SELECTOR_ACTUALES == {"CE", "FB", "NC", "PB", "RC"}

    def test_template_y_config_generada_excluyen_cc(self, tmp_path):
        assert 'tipos_default = ["RC", "NC", "CE"]' in TEMPLATE_TOML
        assert 'tipos_default = ["RC", "NC", "CE", "CC"]' not in TEMPLATE_TOML

        destino = escribir_template(tmp_path / "config.toml")
        contenido = destino.read_text(encoding="utf-8")
        assert 'tipos_default = ["RC", "NC", "CE"]' in contenido
        assert 'tipos_default = ["RC", "NC", "CE", "CC"]' not in contenido

    @pytest.mark.parametrize("types_raw", ["CC", "RC,CC"])
    def test_parsear_tipos_rechaza_cc(self, types_raw, capsys):
        with pytest.raises(typer.Exit) as exc:
            _parsear_tipos(types_raw, Config())
        salida = capsys.readouterr().out
        assert exc.value.exit_code == 2
        assert "CC" in salida
        assert "CE" in salida and "FB" in salida and "NC" in salida
        assert "PB" in salida and "RC" in salida

    def test_parsear_tipos_rechaza_cc_configurado(self, capsys):
        cfg = Config(tipos_default=["RC", "NC", "CE", "CC"])
        with pytest.raises(typer.Exit) as exc:
            _parsear_tipos("", cfg)
        salida = capsys.readouterr().out
        assert exc.value.exit_code == 2
        assert "CC" in salida
        assert "CE" in salida and "FB" in salida and "NC" in salida
        assert "PB" in salida and "RC" in salida

    def test_parsear_tipos_acepta_selectores_actuales(self):
        cfg = Config()
        assert _parsear_tipos("CE,FB,NC,PB,RC", cfg) == [
            "CE",
            "FB",
            "NC",
            "PB",
            "RC",
        ]


class _MemFake:
    def guardar(self):
        pass


class _NavFake:
    def __enter__(self):
        return object(), object()

    def __exit__(self, type, value, traceback):
        return False


def _fallo(tipo: str, doc_num: str) -> dict[str, str]:
    return {
        "timestamp": "2026-01-01T00:00:00",
        "tipo": tipo,
        "doc_num": doc_num,
        "fecha_doc": "2026-01-15",
        "valor": "0",
    }


class TestRecuperarFallidosTiposLegacy:
    def test_solo_cc_no_carga_config_ni_abre_browser(self, monkeypatch):
        monkeypatch.setattr(
            cli_mod, "leer_fallos_pendientes", lambda: [_fallo("CC", "1")]
        )
        monkeypatch.setattr(
            cli_mod.Config,
            "cargar",
            classmethod(lambda cls: pytest.fail("Config.cargar no debe llamarse")),
        )
        monkeypatch.setattr(
            cli_mod,
            "MemoriaTimings",
            lambda: pytest.fail("MemoriaTimings no debe instanciarse"),
        )
        monkeypatch.setattr(
            cli_mod,
            "abrir_navegador",
            lambda: pytest.fail("abrir_navegador no debe llamarse"),
        )
        monkeypatch.setattr(
            cli_mod,
            "login_manual",
            lambda *a, **k: pytest.fail("login_manual no debe llamarse"),
        )
        monkeypatch.setattr(
            cli_mod,
            "setear_filtros",
            lambda *a, **k: pytest.fail("setear_filtros no debe llamarse"),
        )

        result = runner.invoke(app, ["recuperar-fallidos"])

        assert result.exit_code == 0
        assert "CC" in result.stdout
        assert "salt" in result.stdout.lower()

    def test_mixto_cc_y_actual_solo_filtra_actual(self, monkeypatch):
        filtros: list[str] = []

        monkeypatch.setattr(
            cli_mod,
            "leer_fallos_pendientes",
            lambda: [_fallo("CC", "1"), _fallo("RC", "2")],
        )
        monkeypatch.setattr(cli_mod.Config, "cargar", classmethod(lambda cls: Config()))
        monkeypatch.setattr(cli_mod, "cargar_inventario", lambda: set())
        monkeypatch.setattr(cli_mod, "MemoriaTimings", lambda: _MemFake())
        monkeypatch.setattr(cli_mod, "tmp_path_default", lambda base: base / "tmp.pdf")
        monkeypatch.setattr(cli_mod, "abrir_navegador", lambda: _NavFake())
        monkeypatch.setattr(cli_mod, "login_manual", lambda *a, **k: None)
        monkeypatch.setattr(cli_mod, "goto_robusto", lambda *a, **k: None)
        monkeypatch.setattr(
            cli_mod, "dismiss_componentart_banner", lambda *a, **k: None
        )
        monkeypatch.setattr(
            cli_mod, "setear_filtros", lambda page, tipo, *a: filtros.append(tipo)
        )
        monkeypatch.setattr(cli_mod, "consultar", lambda *a, **k: None)
        monkeypatch.setattr(cli_mod, "extraer_filas", lambda page: [])
        monkeypatch.setattr(
            cli_mod,
            "descargar_doc",
            lambda *a, **k: pytest.fail("no debe descargar sin fila"),
        )
        monkeypatch.setattr("suvalor.estado.guardar_inventario", lambda inv: None)

        result = runner.invoke(app, ["recuperar-fallidos"])

        assert result.exit_code == 0
        assert filtros == ["RC"]
        assert "CC" in result.stdout


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
            ok=True,
            destino=tmp_path / "snap.xls",
            size_kb=88.0,
            error=None,
        )
        # No assert - solo validamos que no levante.
        _renderear_resumen_sync(
            plan=plan,
            res_docs=rdocs,
            err_docs=None,
            res_ext=rext,
            err_ext=None,
            res_cart=rcart,
            err_cart=None,
        )

    def test_con_etapas_skipped(self, tmp_path):
        plan = _PlanSync(do_docs=False, do_extractos=False, do_cartera=True)
        rcart = ResumenCartera(
            ok=True,
            destino=tmp_path / "snap.xls",
            size_kb=88.0,
            error=None,
        )
        _renderear_resumen_sync(
            plan=plan,
            res_docs=None,
            err_docs=None,
            res_ext=None,
            err_ext=None,
            res_cart=rcart,
            err_cart=None,
        )

    def test_con_errores_parciales_no_truena(self):
        plan = _PlanSync(do_docs=True, do_extractos=True, do_cartera=True)
        _renderear_resumen_sync(
            plan=plan,
            res_docs=None,
            err_docs="sesion expirada",
            res_ext=ResumenExtractos(nuevos=1, saltados=0, fallidos=0),
            err_ext=None,
            res_cart=None,
            err_cart="No pude llegar a portafolio",
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
