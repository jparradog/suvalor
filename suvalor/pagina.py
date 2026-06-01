"""Interacciones con la pagina ASP.NET WebForms del sitio suvalor.

Cubre:
    - Login manual (abrimos la pagina y le pedimos al usuario hacer login).
    - Navegacion robusta a la pagina de consulta (`goto_robusto`).
    - Banner ComponentArt (a veces aparece y bloquea: reload).
    - Filtros + click "Consultar".
    - Extraccion de filas y paginacion.
    - Detector de sesion expirada.

NOTA: la logica de descarga via `__doPostBack(...)` esta en `descargador.py`
porque maneja el archivo en disco (tmp -> destino).
"""
from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass
from typing import Optional

from playwright.sync_api import Page, TimeoutError as PWTimeout
from rich.console import Console
from rich.prompt import Confirm
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .timings import MemoriaTimings, medir
from .tipos import (
    CONSULTA_URL,
    ID_BTN_CONSULTAR,
    ID_FECHA_FIN,
    ID_FECHA_INI,
    ID_TIPO_DOC,
    LOGIN_URL,
    SESSION_TERMINATED_HINT,
)


class SessionExpired(RuntimeError):
    """Se levanta cuando se detecta que el usuario ya no esta autenticado."""


class NavegacionFallida(RuntimeError):
    """No se pudo llegar a la URL objetivo despues de los reintentos."""


class ErrorExtraccionFilas(RuntimeError):
    """La grilla no tiene la estructura esperada para extraer filas."""


@dataclass
class Fila:
    idx: int
    fecha: str
    doc_num: str
    valor: str

    def to_dict(self) -> dict:
        return {
            "idx": self.idx,
            "fecha": self.fecha,
            "doc_num": self.doc_num,
            "valor": self.valor,
        }


# --------------------------------------------------------------------------- #
# Login                                                                       #
# --------------------------------------------------------------------------- #


def login_manual(page: Page, console: Console) -> None:
    """Abre la pagina de login y bloquea hasta que el usuario confirme."""
    console.print(
        "[cyan]>>> Se abrira el sitio. Inicie sesion con usuario, clave y autorizado."
        "[/cyan]"
    )
    console.print(
        "[cyan]>>> Cuando este autenticado en la sucursal virtual, regrese aqui."
        "[/cyan]"
    )
    try:
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30_000)
    except Exception as e:
        console.print(f"[yellow]  [warn] goto login: {e}[/yellow]")
    Confirm.ask("Presione ENTER cuando este autenticado", default=True, show_default=False)
    try:
        page.wait_for_load_state("domcontentloaded", timeout=10_000)
    except Exception:
        pass
    page.wait_for_timeout(2_500)


def detectar_sesion_expirada(page: Page) -> bool:
    """True si la URL apunta a terminarSesion o si volvio al form de login."""
    try:
        url = page.url or ""
    except Exception:
        return False
    if SESSION_TERMINATED_HINT in url:
        return True
    if "login.aspx" in url:
        return True
    # heuristica: el form de login expone un input typed="password"
    try:
        if page.locator("input[type='password']").count() > 0:
            return True
    except Exception:
        pass
    return False


def reloguear_si_expiro(page: Page, console: Console) -> None:
    """Si se detecta sesion expirada, se solicita relogin al usuario."""
    if not detectar_sesion_expirada(page):
        return
    console.print(
        "[bold red]>>> Sesion expirada — el sitio cerro la sesion.[/bold red]"
    )
    console.print(
        "[yellow]>>> Inicie sesion de nuevo en la ventana de Chrome y luego confirme.[/yellow]"
    )
    try:
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30_000)
    except Exception:
        pass
    Confirm.ask("Presione ENTER cuando este autenticado nuevamente", default=True, show_default=False)
    page.wait_for_timeout(2_500)
    if detectar_sesion_expirada(page):
        raise SessionExpired("La sesion sigue cerrada despues del prompt manual.")


# --------------------------------------------------------------------------- #
# Navegacion                                                                  #
# --------------------------------------------------------------------------- #


def _intento_goto(page: Page, url: str) -> bool:
    page.goto(url, wait_until="domcontentloaded", timeout=30_000)
    page.wait_for_timeout(1_500)
    actual = page.url or ""
    return ("consultarDocumentosElectronicos" in actual) or actual.startswith(url)


def goto_robusto(
    page: Page,
    url: str = CONSULTA_URL,
    *,
    intentos: int = 3,
    mem: Optional[MemoriaTimings] = None,
    console: Optional[Console] = None,
) -> None:
    """Navega a `url` tolerando redirects y reintentando con backoff.

    Levanta `NavegacionFallida` si tras `intentos` no llega; o `SessionExpired`
    si detecta que la sesion expiro.
    """
    for n in range(intentos):
        try:
            if mem is not None:
                with medir(mem, "navegacion"):
                    ok = _intento_goto(page, url)
            else:
                ok = _intento_goto(page, url)
            if ok:
                return
            if console:
                console.print(
                    f"[dim]  [info] redirect a {page.url}, reintento navegacion...[/dim]"
                )
            page.wait_for_timeout(1_500)
        except Exception as e:
            msg = str(e)
            if "interrupted by another navigation" in msg or "ERR_ABORTED" in msg:
                if console:
                    console.print(
                        "[dim]  [info] navegacion interrumpida por redirect, reintento...[/dim]"
                    )
                page.wait_for_timeout(2_500)
            else:
                if console:
                    console.print(f"[yellow]  [warn] goto {url}: {e}[/yellow]")
                page.wait_for_timeout(2_000)
        # tras cada vuelta, chequeo de sesion
        if detectar_sesion_expirada(page):
            raise SessionExpired(f"Sesion expirada al navegar a {url}.")
    raise NavegacionFallida(f"No pude llegar a {url} despues de {intentos} intentos.")


# --------------------------------------------------------------------------- #
# Banner ComponentArt                                                         #
# --------------------------------------------------------------------------- #


def dismiss_componentart_banner(page: Page, console: Optional[Console] = None) -> None:
    """A veces aparece el banner de demo ComponentArt; se quita con un reload."""
    try:
        if page.locator("text=ComponentArt Menu").count() > 0:
            if console:
                console.print(
                    "[dim]  [info] banner ComponentArt detectado, recargando...[/dim]"
                )
            page.reload(wait_until="domcontentloaded")
            page.wait_for_timeout(3_000)
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# Filtros y consulta                                                          #
# --------------------------------------------------------------------------- #


def setear_filtros(page: Page, codigo: str, fi_dmy: str, ff_dmy: str) -> None:
    """Inyecta los valores en los inputs ASP.NET por id (no usa selectores frageiles)."""
    page.evaluate(
        f"""
        document.getElementById('{ID_TIPO_DOC}').value = '{codigo}';
        document.getElementById('{ID_FECHA_INI}').value = '{fi_dmy}';
        document.getElementById('{ID_FECHA_FIN}').value = '{ff_dmy}';
        """
    )


def consultar(page: Page, mem: MemoriaTimings) -> None:
    """Click "Consultar" y espera dinamica segun timings aprendidos."""
    page.evaluate(f"document.getElementById('{ID_BTN_CONSULTAR}').click();")
    espera_ms = mem.timeout_ms("consulta")
    with medir(mem, "consulta"):
        page.wait_for_timeout(int(espera_ms))


# --------------------------------------------------------------------------- #
# Extraccion de filas / paginacion                                            #
# --------------------------------------------------------------------------- #


_JS_EXTRAER_FILAS = """
(() => {
    const t = document.querySelector('table[id*="gvDocumentos"]');
    if (!t) return [];
    return Array.from(t.querySelectorAll('tr')).slice(1)
        .filter(r => r.querySelectorAll('td').length >= 5)
        .map((r, i) => {
            const c = Array.from(r.querySelectorAll('td')).map(x => x.textContent.trim());
            return {idx: i, fecha: c[0], doc_num: c[2], valor: c[4]};
        });
})()
"""

_JS_EXTRAER_TABLA = """
(() => {
    const t = document.querySelector('table[id*="gvDocumentos"]');
    if (!t) return {headers: [], rows: []};
    const trs = Array.from(t.querySelectorAll('tr'));
    if (trs.length === 0) return {headers: [], rows: []};
    const headerCells = Array.from(trs[0].querySelectorAll('th,td'))
        .map(x => x.textContent.trim());
    const rows = trs.slice(1)
        .map(r => Array.from(r.querySelectorAll('td')).map(x => x.textContent.trim()))
        .filter(c => c.length > 0);
    return {headers: headerCells, rows};
})()
"""

_JS_PAGINAS = """
Array.from(document.querySelectorAll('a[href*="Page$"]'))
    .map(a => parseInt(a.textContent.trim()))
    .filter(n => !isNaN(n))
"""


def _normalizar_header_grilla(texto: str) -> str:
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"[^a-z0-9]+", "", sin_acentos.lower())


def _buscar_header(headers: list[str], aliases: set[str]) -> int:
    normalizados = [_normalizar_header_grilla(h) for h in headers]
    for idx, header in enumerate(normalizados):
        if header in aliases:
            return idx
    raise ErrorExtraccionFilas(
        f"No encontre header requerido; disponibles={normalizados}"
    )


def _extraer_filas_pb_desde_tabla(headers: list[str], rows: list[list[str]]) -> list[Fila]:
    idx_papeleta = _buscar_header(
        headers, {"npapeleta", "nopapeleta", "numeropapeleta"}
    )
    idx_fecha = _buscar_header(headers, {"fechaoperacion"})
    try:
        idx_valor = _buscar_header(headers, {"valor"})
    except ErrorExtraccionFilas:
        idx_valor = len(headers) - 1

    filas: list[Fila] = []
    for i, row in enumerate(rows):
        if len(row) <= max(idx_papeleta, idx_fecha, idx_valor):
            continue
        filas.append(
            Fila(
                idx=i,
                fecha=row[idx_fecha],
                doc_num=row[idx_papeleta],
                valor=row[idx_valor],
            )
        )
    return filas


def extraer_filas(page: Page, codigo: str | None = None) -> list[Fila]:
    if codigo == "PB":
        raw = page.evaluate(_JS_EXTRAER_TABLA) or {"headers": [], "rows": []}
        return _extraer_filas_pb_desde_tabla(
            headers=list(raw.get("headers") or []),
            rows=list(raw.get("rows") or []),
        )
    raw = page.evaluate(_JS_EXTRAER_FILAS) or []
    return [Fila(**r) for r in raw]


def extraer_paginas(page: Page) -> list[int]:
    return page.evaluate(_JS_PAGINAS) or []


def ir_a_pagina(page: Page, num: int, mem: MemoriaTimings) -> bool:
    js = (
        "(() => {"
        f"  const links = Array.from(document.querySelectorAll('a[href*=\"Page${num}\"]'));"
        "   if (links.length === 0) return false;"
        "   links[0].click();"
        "   return true;"
        "})()"
    )
    ok = page.evaluate(js)
    if ok:
        with medir(mem, "page_change"):
            page.wait_for_timeout(int(mem.timeout_ms("page_change")))
    return bool(ok)
