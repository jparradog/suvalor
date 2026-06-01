from __future__ import annotations

import pytest
from typer.testing import CliRunner

import suvalor.cli as cli_mod
from suvalor.cli import app
from suvalor.orquestador import ResumenTesoreria

runner = CliRunner()


def _no_browser(*args, **kwargs):
    pytest.fail("abrir_navegador no debe ejecutarse")


class FakeBrowser:
    def __init__(self):
        self.context = object()
        self.page = object()

    def __enter__(self):
        return self.context, self.page

    def __exit__(self, type, value, traceback):
        return False


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
        [
            "tesoreria",
            "--from",
            "2026-01-01",
            "--to",
            "2026-01-31",
            "--account",
            "",
            "--tag",
            "corto",
        ],
        [
            "tesoreria",
            "--from",
            "2026-01-01",
            "--to",
            "2026-01-31",
            "--account",
            "raw",
            "--tag",
            "   ",
        ],
        [
            "tesoreria",
            "--from",
            "2026-01-01",
            "--to",
            "2026-01-31",
            "--account",
            "raw",
            "--tag",
            "mi cuenta",
        ],
        [
            "tesoreria",
            "--from",
            "2026-01-01",
            "--to",
            "2026-01-31",
            "--account",
            "raw",
            "--tag",
            " corto ",
        ],
        ["tesoreria", "--from", "2026-01-01", "--to", "2026-01-31", "--tag", "../x"],
    ],
)
def test_tesoreria_valida_antes_de_abrir_browser(monkeypatch, args):
    monkeypatch.setattr(cli_mod, "abrir_navegador", _no_browser)
    result = runner.invoke(app, args)
    assert result.exit_code == 2


@pytest.mark.parametrize("formato", ["pdf", "xls", "both"])
def test_tesoreria_valido_ejecuta_opt_in_con_login_manual(monkeypatch, formato):
    fake = FakeBrowser()
    llamadas: dict[str, object] = {}
    monkeypatch.setattr(cli_mod, "abrir_navegador", lambda: fake)
    monkeypatch.setattr(
        cli_mod,
        "login_manual",
        lambda page, console: llamadas.setdefault("login", page),
    )

    def sincronizar(*, page, plan, mem, console, account, retry_doc):
        llamadas["page"] = page
        llamadas["account"] = account
        llamadas["formatos"] = plan.formatos
        llamadas["retry_doc"] = retry_doc
        return ResumenTesoreria(nuevos=1, total=len(plan.destinos))

    monkeypatch.setattr(cli_mod, "sincronizar_tesoreria", sincronizar)

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
    assert result.exit_code == 0
    assert llamadas["login"] is fake.page
    assert llamadas["page"] is fake.page
    assert llamadas["account"] == "texto privado"
    assert "Tesoreria" in result.stdout
    assert "texto privado" not in result.stdout
    assert "deshabilitada" not in result.stdout


def test_tesoreria_account_con_tag_seguro_no_filtra_account(monkeypatch):
    monkeypatch.setattr(cli_mod, "abrir_navegador", lambda: FakeBrowser())
    monkeypatch.setattr(cli_mod, "login_manual", lambda _page, _console: None)
    monkeypatch.setattr(
        cli_mod,
        "sincronizar_tesoreria",
        lambda **_kwargs: ResumenTesoreria(nuevos=1, total=1),
    )
    result = runner.invoke(
        app,
        [
            "tesoreria",
            "--from",
            "2026-01-01",
            "--to",
            "2026-01-31",
            "--account",
            "Cuenta Privada 123",
            "--tag",
            "mi-cuenta",
        ],
    )
    assert result.exit_code == 0
    assert "Cuenta Privada" not in result.stdout
    assert "123" not in result.stdout
    assert "mi-cuenta" in result.stdout


def test_sync_help_no_incluye_tesoreria(monkeypatch):
    monkeypatch.setattr(cli_mod, "abrir_navegador", _no_browser)
    result = runner.invoke(app, ["sync", "--help"])
    assert result.exit_code == 0
    assert "tesoreria" not in result.stdout.lower()
