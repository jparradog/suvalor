from __future__ import annotations

import pytest
from typer.testing import CliRunner

import suvalor.cli as cli_mod
from suvalor.cli import app

runner = CliRunner()


def _no_browser(*args, **kwargs):
    pytest.fail("abrir_navegador no debe ejecutarse")


def test_tesoreria_help_expone_scope_privado(monkeypatch):
    monkeypatch.setattr(cli_mod, "abrir_navegador", _no_browser)
    result = runner.invoke(app, ["tesoreria", "--help"])
    assert result.exit_code == 0
    for flag in ("--from", "--to", "--format", "--account", "--tag", "--redownload"):
        assert flag in result.stdout


@pytest.mark.parametrize(
    "args",
    [
        ["tesoreria", "--from", "2026-99-01", "--to", "2026-01-31"],
        ["tesoreria", "--from", "2026-02-01", "--to", "2026-01-31"],
        ["tesoreria", "--from", "2026-01-01", "--to", "2026-01-31", "--format", "csv"],
        ["tesoreria", "--from", "2026-01-01", "--to", "2026-01-31", "--account", "raw"],
        ["tesoreria", "--from", "2026-01-01", "--to", "2026-01-31", "--account", ""],
        ["tesoreria", "--from", "2026-01-01", "--to", "2026-01-31", "--tag", "../x"],
    ],
)
def test_tesoreria_valida_antes_de_abrir_browser(monkeypatch, args):
    monkeypatch.setattr(cli_mod, "abrir_navegador", _no_browser)
    result = runner.invoke(app, args)
    assert result.exit_code == 2


@pytest.mark.parametrize("formato", ["pdf", "xls", "both"])
def test_tesoreria_valido_falla_cerrado_sin_abrir_browser(monkeypatch, formato):
    monkeypatch.setattr(cli_mod, "abrir_navegador", _no_browser)
    result = runner.invoke(
        app,
        [
            "tesoreria",
            "--from",
            "2026-01-01",
            "--to",
            "2026-01-31",
            "--format",
            formato,
            "--account",
            "texto privado",
            "--tag",
            "corto",
        ],
    )
    assert result.exit_code == 3
    assert "Tesoreria" in result.stdout
    assert "deshabilitada" in result.stdout
    assert "texto privado" not in result.stdout


def test_sync_help_no_incluye_tesoreria(monkeypatch):
    monkeypatch.setattr(cli_mod, "abrir_navegador", _no_browser)
    result = runner.invoke(app, ["sync", "--help"])
    assert result.exit_code == 0
    assert "tesoreria" not in result.stdout.lower()
