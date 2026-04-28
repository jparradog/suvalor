"""Setup de Playwright con Chrome real y banderas anti-deteccion.

Estas opciones estan testeadas y NO se deben cambiar a la ligera — el sitio
usa reCAPTCHA y bloquea Chromium controlado de manera estandar:

    channel="chrome"                    # Chrome real, no Chromium
    args=[..."--disable-blink-features=AutomationControlled"]
    ignore_default_args=["--enable-automation"]
    add_init_script(...)                # navigator.webdriver = undefined, etc.

Ademas:
    accept_downloads=True
    downloads_path=str(BASE)            # los PDFs caen en BASE como
                                        # "VerDocumentoElectronico.pdf"
    user_data_dir=PROFILE_DIR           # cookies/sesion persistentes
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from playwright.sync_api import (
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
)

from .tipos import BASE, PROFILE_DIR

# Script que se inyecta en cada pagina antes de cualquier otro JS.
# Despista a las heuristicas mas comunes (navigator.webdriver, plugins, idioma).
INIT_SCRIPT = """
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
    Object.defineProperty(navigator, 'languages', {get: () => ['es-CO','es','en']});
    window.chrome = window.chrome || {runtime: {}};
"""


def _crear_contexto(p: Playwright) -> BrowserContext:
    PROFILE_DIR.mkdir(exist_ok=True)
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=str(PROFILE_DIR),
        channel="chrome",                # Chrome real (instalado en el sistema)
        headless=False,                  # debe ser visible para login manual
        accept_downloads=True,
        downloads_path=str(BASE),        # los PDFs caen como archivo en BASE
        args=["--disable-blink-features=AutomationControlled"],
        ignore_default_args=["--enable-automation"],
    )
    ctx.add_init_script(INIT_SCRIPT)
    return ctx


@contextmanager
def abrir_navegador() -> Iterator[tuple[BrowserContext, Page]]:
    """Context manager: yield `(context, page)`. Cierra al salir."""
    with sync_playwright() as p:
        ctx = _crear_contexto(p)
        try:
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            yield ctx, page
        finally:
            try:
                ctx.close()
            except Exception:
                pass
