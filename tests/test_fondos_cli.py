from __future__ import annotations

import pytest
from typer.testing import CliRunner

import suvalor.cli as cli_mod
from suvalor.cli import app

runner = CliRunner()


def _no_browser(*args, **kwargs):
    pytest.fail("abrir_navegador no debe ejecutarse")


def test_fondos_help_expone_solo_scope_default(monkeypatch):
    monkeypatch.setattr(cli_mod, "abrir_navegador", _no_browser)

    result = runner.invoke(app, ["fondos", "--help"])

    assert result.exit_code == 0
    assert "--from" in result.stdout
    assert "--to" in result.stdout
    assert "--tag" in result.stdout
    assert "--redownload" in result.stdout
    assert "--account" not in result.stdout
    assert "--fund" not in result.stdout


@pytest.mark.parametrize(
    "args",
    [
        ["fondos", "--from", "2026-99-01", "--to", "2026-01-31"],
        ["fondos", "--from", "2026-02-01", "--to", "2026-01-31"],
        ["fondos", "--from", "2026-01-01", "--to", "2026-01-31", "--tag", "Cuenta 123"],
    ],
)
def test_fondos_valida_antes_de_abrir_browser(monkeypatch, args):
    monkeypatch.setattr(cli_mod, "abrir_navegador", _no_browser)

    result = runner.invoke(app, args)

    assert result.exit_code == 2


@pytest.mark.parametrize("opcion", ["--account", "--fund"])
def test_fondos_rechaza_selectores_raw_antes_de_abrir_browser(monkeypatch, opcion):
    monkeypatch.setattr(cli_mod, "abrir_navegador", _no_browser)

    result = runner.invoke(
        app,
        ["fondos", "--from", "2026-01-01", "--to", "2026-01-31", opcion, "raw"],
    )

    assert result.exit_code == 2


def test_fondos_valido_falla_cerrado_sin_abrir_browser(monkeypatch):
    monkeypatch.setattr(cli_mod, "abrir_navegador", _no_browser)

    result = runner.invoke(
        app,
        ["fondos", "--from", "2026-01-01", "--to", "2026-01-31", "--tag", "safe-tag"],
    )

    assert result.exit_code == 3
    assert "Fondos" in result.stdout
    assert "deshabilitada" in result.stdout
    assert "selector" in result.stdout.lower()


def test_sync_help_no_incluye_fondos(monkeypatch):
    monkeypatch.setattr(cli_mod, "abrir_navegador", _no_browser)

    result = runner.invoke(app, ["sync", "--help"])

    assert result.exit_code == 0
    assert "--no-fondos" not in result.stdout
    assert "fondos" not in result.stdout.lower()
