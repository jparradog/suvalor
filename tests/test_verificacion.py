"""Tests del modulo `suvalor.verificacion`.

Estos tests son completamente puros: no tocan red, Playwright ni el
filesystem real. Solo escriben archivos a `tmp_path` y validan que las
heuristicas detecten los falsos positivos mas comunes.
"""
from __future__ import annotations

import pytest

from suvalor.verificacion import (
    es_pdf_valido,
    es_xls_html_valido,
    verificar_descarga,
)


# --------------------------------------------------------------------------- #
# Helpers para fabricar contenido de archivos de test                         #
# --------------------------------------------------------------------------- #


def _pdf_minimo_valido(rel_size: int = 3_000) -> bytes:
    """Construye bytes que pasan la heuristica de `es_pdf_valido`.

    Empieza con el header `%PDF-1.4`, contenido relleno en el medio, y termina
    con el marker `%%EOF`. El size total queda alrededor de `rel_size` bytes.
    """
    header = b"%PDF-1.4\n"
    footer = b"\n%%EOF\n"
    relleno_n = max(0, rel_size - len(header) - len(footer))
    relleno = b"x" * relleno_n
    return header + relleno + footer


# --------------------------------------------------------------------------- #
# es_pdf_valido                                                               #
# --------------------------------------------------------------------------- #


class TestEsPdfValido:
    def test_pdf_valido_pasa(self, tmp_path):
        p = tmp_path / "ok.pdf"
        p.write_bytes(_pdf_minimo_valido())
        ok, motivo = es_pdf_valido(p)
        assert ok is True
        assert motivo == ""

    def test_archivo_inexistente_falla(self, tmp_path):
        ok, motivo = es_pdf_valido(tmp_path / "nope.pdf")
        assert ok is False
        assert "no existe" in motivo

    def test_archivo_vacio_falla(self, tmp_path):
        p = tmp_path / "vacio.pdf"
        p.write_bytes(b"")
        ok, motivo = es_pdf_valido(p)
        assert ok is False
        assert "0" in motivo

    def test_archivo_muy_chico_falla(self, tmp_path):
        p = tmp_path / "chico.pdf"
        # 100 bytes — pasa header check, pero size < 2048 default
        p.write_bytes(b"%PDF-1.4\n" + b"x" * 80 + b"\n%%EOF\n")
        ok, motivo = es_pdf_valido(p)
        assert ok is False
        assert "size=" in motivo

    def test_pdf_sin_eof_falla(self, tmp_path):
        # Empieza con %PDF- pero no tiene %%EOF al final.
        p = tmp_path / "sin_eof.pdf"
        p.write_bytes(b"%PDF-1.4\n" + b"x" * 5_000)
        ok, motivo = es_pdf_valido(p)
        assert ok is False
        assert "EOF" in motivo

    def test_pdf_solo_header_falla_por_size(self, tmp_path):
        # Tip: '%PDF-' solo (5 bytes) NO basta — falla por size primero.
        p = tmp_path / "solo_header.pdf"
        p.write_bytes(b"%PDF-")
        ok, motivo = es_pdf_valido(p)
        assert ok is False

    def test_html_camuflado_de_pdf_falla(self, tmp_path):
        # Cookie expirada -> server devuelve HTML de login en vez del PDF.
        p = tmp_path / "fake.pdf"
        p.write_bytes(
            b"<!DOCTYPE html><html><body><h1>Iniciar sesion</h1>"
            + b"<p>Tu sesion ha expirado.</p>" * 100
            + b"</body></html>"
        )
        ok, motivo = es_pdf_valido(p)
        assert ok is False
        # diagnostico amigable: detecta que es HTML
        assert "HTML" in motivo or "header" in motivo

    def test_min_bytes_custom(self, tmp_path):
        p = tmp_path / "ok.pdf"
        p.write_bytes(_pdf_minimo_valido(rel_size=3_000))
        # con min muy alto deberia fallar
        ok, motivo = es_pdf_valido(p, min_bytes=10_000)
        assert ok is False
        assert "size=" in motivo


# --------------------------------------------------------------------------- #
# es_xls_html_valido                                                          #
# --------------------------------------------------------------------------- #


class TestEsXlsHtmlValido:
    def test_html_con_table_pasa(self, tmp_path):
        p = tmp_path / "portafolio.xls"
        contenido = (
            b"<html><body>" + b"<p>relleno</p>" * 200
            + b"<table border=1><tr><td>Saldo</td><td>123</td></tr></table>"
            + b"</body></html>"
        )
        p.write_bytes(contenido)
        ok, motivo = es_xls_html_valido(p)
        assert ok is True
        assert motivo == ""

    def test_html_de_login_falla(self, tmp_path):
        p = tmp_path / "fake.xls"
        # Tiene <table> pero tambien "iniciar sesion" -> debe fallar.
        contenido = (
            b"<html><body>" + b"x" * 3000
            + b"<form>Iniciar sesion</form>"
            + b"<table><tr><td>foo</td></tr></table>"
            + b"</body></html>"
        )
        p.write_bytes(contenido)
        ok, motivo = es_xls_html_valido(p)
        assert ok is False
        assert "login" in motivo.lower() or "iniciar" in motivo.lower()

    def test_html_sin_table_falla(self, tmp_path):
        p = tmp_path / "sin_table.xls"
        p.write_bytes(b"<html><body>" + b"x" * 3000 + b"</body></html>")
        ok, motivo = es_xls_html_valido(p)
        assert ok is False
        assert "table" in motivo.lower()

    def test_archivo_vacio_falla(self, tmp_path):
        p = tmp_path / "vacio.xls"
        p.write_bytes(b"")
        ok, motivo = es_xls_html_valido(p)
        assert ok is False
        assert "0" in motivo

    def test_archivo_inexistente_falla(self, tmp_path):
        ok, motivo = es_xls_html_valido(tmp_path / "nope.xls")
        assert ok is False
        assert "no existe" in motivo

    def test_table_case_insensitive(self, tmp_path):
        p = tmp_path / "ok_upper.xls"
        contenido = (
            b"<HTML><BODY>" + b"y" * 3000
            + b"<TABLE><TR><TD>x</TD></TR></TABLE></BODY></HTML>"
        )
        p.write_bytes(contenido)
        ok, motivo = es_xls_html_valido(p)
        assert ok is True


# --------------------------------------------------------------------------- #
# verificar_descarga: despachador                                             #
# --------------------------------------------------------------------------- #


class TestVerificarDescarga:
    def test_despacha_a_pdf(self, tmp_path):
        p = tmp_path / "ok.pdf"
        p.write_bytes(_pdf_minimo_valido())
        ok, motivo = verificar_descarga(p, "pdf")
        assert ok is True

    def test_despacha_a_xls_html(self, tmp_path):
        p = tmp_path / "ok.xls"
        p.write_bytes(
            b"<html><body>" + b"z" * 3000
            + b"<table><tr><td>1</td></tr></table></body></html>"
        )
        ok, motivo = verificar_descarga(p, "xls_html")
        assert ok is True

    def test_tipo_desconocido_falla(self, tmp_path):
        p = tmp_path / "x.bin"
        p.write_bytes(b"x" * 5000)
        ok, motivo = verificar_descarga(p, "csv")
        assert ok is False
        assert "tipo" in motivo.lower() or "desconocido" in motivo.lower()

    def test_pdf_invalido_propaga_motivo(self, tmp_path):
        p = tmp_path / "vacio.pdf"
        p.write_bytes(b"")
        ok, motivo = verificar_descarga(p, "pdf")
        assert ok is False
        assert motivo  # tiene algun motivo
