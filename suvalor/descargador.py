"""Gestion de la descarga de un documento individual.

La logica es exacta del monolito (NO cambiar):
    1. `__doPostBack('...$gvDocumentos','Select$N')` - dispara la descarga.
    2. El sitio escribe el PDF en disco como `BASE/VerDocumentoElectronico.pdf`.
    3. Polleamos hasta que aparezca el archivo (timeout dinamico via timings).
    4. `tmp.replace(destino_final)` con nombre `YYYY-MM-DD_TIPO_NUMERO.pdf`.
    5. Cerrar tabs colgantes del visor.

Se reintenta `retry_doc` veces; si todas fallan, se registra en fallos.tsv.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from playwright.sync_api import BrowserContext, Error as PWError, Page
from rich.console import Console

from .diagnosticos import diagnosticar_fallo_portal, sanitizar_diagnostico
from .estado import Inventario, registrar_fallo
from .parseo import parsear_fecha_grilla
from .pagina import Fila, detectar_sesion_expirada
from .timings import MemoriaTimings
from .tipos import DOWNLOAD_FILENAME, POSTBACK_TARGET_GV
from .verificacion import verificar_descarga


class Resultado:
    NUEVO = "nuevo"
    SKIP = "skip"
    FAIL = "fail"


@dataclass(frozen=True)
class IdentidadDescarga:
    fecha_iso: str
    clave: str
    nombre: str


def construir_identidad_descarga(fila: Fila, codigo: str) -> IdentidadDescarga:
    fecha_iso = parsear_fecha_grilla(fila.fecha)
    doc_num = fila.doc_num
    clave = f"{codigo}_{doc_num}"
    return IdentidadDescarga(
        fecha_iso=fecha_iso,
        clave=clave,
        nombre=f"{fecha_iso}_{codigo}_{doc_num}.pdf",
    )


def cerrar_tabs_pdf(context: BrowserContext) -> None:
    """Cierra cualquier pestania que el sitio haya abierto con el visor."""
    for p in list(context.pages):
        if "VerDocumentoElectronico" in (p.url or ""):
            try:
                p.close()
            except Exception:
                pass


def _disparar_postback(page: Page, idx: int) -> None:
    page.evaluate(f"__doPostBack('{POSTBACK_TARGET_GV}','Select${idx}');")


def _esperar_tmp(tmp_path: Path, timeout_s: float, paso_s: float = 1.0) -> bool:
    """Polling hasta que aparezca el PDF o se acabe el timeout."""
    fin = time.monotonic() + timeout_s
    while time.monotonic() < fin:
        if tmp_path.exists():
            return True
        time.sleep(paso_s)
    return False


def poll_archivo(
    tmp_path: Path,
    timeout_s: float,
    paso_s: float = 0.5,
    estable_s: float = 0.8,
) -> bool:
    """Polling hasta que `tmp_path` exista Y su tamanio se mantenga estable.

    Usado por los subcomandos `extractos` y `cartera` (descargas via GET / submit
    normal - el navegador escribe el archivo de a chunks). Devuelve True si el
    archivo aparecio y dejo de crecer dentro del timeout.
    """
    fin = time.monotonic() + timeout_s
    ultimo_size = -1
    estable_desde: float | None = None
    while time.monotonic() < fin:
        if tmp_path.exists():
            try:
                size = tmp_path.stat().st_size
            except OSError:
                size = -1
            ahora = time.monotonic()
            if size > 0 and size == ultimo_size:
                if estable_desde is None:
                    estable_desde = ahora
                elif (ahora - estable_desde) >= estable_s:
                    return True
            else:
                estable_desde = None
                ultimo_size = size
        time.sleep(paso_s)
    return tmp_path.exists() and tmp_path.stat().st_size > 0


def _descargar_via_popup_o_download(
    page: Page, idx: int, destino: Path, timeout_s: float
) -> tuple[bool, str]:
    """Hibrido: maneja los dos casos posibles del postback ASP.NET.

    Caso A - sin Adobe extension: la nueva pestania dispara `download`
        directo, lo guardamos con `download.save_as`.
    Caso B - con Adobe extension: la pestania abre el PDF en visor inline
        (no hay download event). Sacamos la URL del popup y descargamos
        los bytes via `page.context.request.get(url)` - usa las cookies
        de sesion automaticamente.

    Devuelve `(ok, motivo)`. Cierra el popup en ambos casos.
    """
    timeout_ms = int(timeout_s * 1000)
    popup = None
    try:
        with page.context.expect_page(timeout=timeout_ms) as popup_info:
            try:
                with page.expect_download(timeout=timeout_ms) as dl_info:
                    _disparar_postback(page, idx)
                # Caso A: download directo (no necesitamos el popup)
                download = dl_info.value
                download.save_as(str(destino))
                cerrar_tabs_pdf(page.context)
                return True, ""
            except PWError:
                # No hubo download dentro del timeout. Puede ser caso B
                # (popup abrio el visor) - caemos al manejo de popup abajo.
                pass
    except PWError as e:
        return False, f"no se abrio popup ni download: {e}"

    # expect_page resolvio: tenemos un popup pero no hubo download.
    try:
        popup = popup_info.value
    except Exception as e:
        return False, f"popup_info sin valor: {e}"

    # Esperar URL estable (el popup tarda en cargar, hacemos polling).
    deadline = time.monotonic() + 5.0
    url = ""
    while time.monotonic() < deadline:
        try:
            u = popup.url or ""
        except Exception:
            u = ""
        if "VerDocumentoElectronico" in u and "jwt=" in u:
            url = u
            break
        try:
            popup.wait_for_load_state("domcontentloaded", timeout=2_000)
        except Exception:
            pass
        time.sleep(0.3)

    if not url:
        try:
            popup.close()
        except Exception:
            pass
        return False, "popup sin URL valida"

    # Descargar via context.request - reutiliza cookies de la sesion.
    try:
        resp = page.context.request.get(url, timeout=timeout_ms)
        body = resp.body()
        if resp.status != 200:
            return False, diagnosticar_fallo_portal(
                status=resp.status,
                contenido=body,
                detalle=f"status HTTP {resp.status}",
            )
        destino.write_bytes(body)
    except PWError as e:
        return False, sanitizar_diagnostico(f"fallo HTTP get: {e}")
    finally:
        try:
            popup.close()
        except Exception:
            pass
    return True, ""


def descargar_doc(
    *,
    page: Page,
    fila: Fila,
    codigo: str,
    dir_destino: Path,
    inventario: Inventario,
    tmp_path: Path,
    mem: MemoriaTimings,
    retry_doc: int = 3,
    console: Optional[Console] = None,
    motivos_fallidos: Optional[list[tuple[str, str]]] = None,
) -> str:
    """Descarga un documento. Retorna `Resultado.{NUEVO,SKIP,FAIL}`.

    Si se pasa `motivos_fallidos`, en caso de FAIL se appendea
    `(clave_inv, motivo)` para que el caller lo propague al resumen.
    """
    clave_inv = f"{codigo}_{fila.doc_num}"
    if clave_inv in inventario:
        if console:
            console.print(f"  [yellow][skip][/yellow] {clave_inv} ya esta")
        return Resultado.SKIP

    identidad = construir_identidad_descarga(fila, codigo)
    destino = dir_destino / identidad.nombre
    if destino.exists():
        inventario.add(clave_inv)
        if console:
            console.print(f"  [yellow][skip][/yellow] {clave_inv} ya esta")
        return Resultado.SKIP

    nombre_destino = identidad.nombre

    timeout_s = mem.timeout_ms("descarga") / 1000.0
    p95_s = mem.p95_ms("descarga") / 1000.0

    ultimo_motivo = ""
    intentos_max = max(1, retry_doc)
    for intento in range(intentos_max):
        if console and intento == 0:
            console.print(
                f"  [cyan][...] Esperando descarga (p95: {p95_s:.1f}s, "
                f"max: {timeout_s:.1f}s)...[/cyan]"
            )

        t0 = time.perf_counter()
        try:
            # Estrategia hibrida: el postback ASP.NET puede (a) disparar
            # un download directo o (b) abrir una pestania visor con el
            # PDF inline (Adobe extension intercepta). El helper maneja
            # ambos casos.
            ok_dl, motivo_dl = _descargar_via_popup_o_download(
                page, fila.idx, destino, timeout_s
            )
        except Exception as e:
            mem.registrar("descarga", (time.perf_counter() - t0) * 1000.0)
            ultimo_motivo = sanitizar_diagnostico(f"error inesperado en descarga: {e}")
            cerrar_tabs_pdf(page.context)
            if detectar_sesion_expirada(page):
                if console:
                    console.print(
                        "[red]  [fail] sesion expirada durante descarga[/red]"
                    )
                if motivos_fallidos is not None:
                    motivos_fallidos.append((clave_inv, "sesion expirada"))
                return Resultado.FAIL
            if intento < intentos_max - 1 and console:
                console.print(
                    f"  [yellow][retry {intento + 1}/{intentos_max}][/yellow] "
                    f"{clave_inv} (excepcion)"
                )
            continue

        mem.registrar("descarga", (time.perf_counter() - t0) * 1000.0)

        if not ok_dl:
            ultimo_motivo = diagnosticar_fallo_portal(
                detalle=motivo_dl,
                fallback="no aparecio el archivo (timeout)",
            )
            cerrar_tabs_pdf(page.context)
            if detectar_sesion_expirada(page):
                if console:
                    console.print(
                        "[red]  [fail] sesion expirada durante descarga[/red]"
                    )
                if motivos_fallidos is not None:
                    motivos_fallidos.append((clave_inv, "sesion expirada"))
                return Resultado.FAIL
            if intento < intentos_max - 1 and console:
                console.print(
                    f"  [yellow][retry {intento + 1}/{intentos_max}][/yellow] "
                    f"{clave_inv} ({ultimo_motivo})"
                )
            continue

        # save_as / write_bytes escribieron en `destino`. Verificamos contenido.
        if not destino.exists():
            ultimo_motivo = "descarga no escribio el archivo"
            if console:
                console.print(f"  [yellow][warn] {ultimo_motivo}[/yellow]")
            if intento < intentos_max - 1 and console:
                console.print(
                    f"  [yellow][retry {intento + 1}/{intentos_max}][/yellow] {clave_inv}"
                )
            continue

        ok_ver, motivo = verificar_descarga(destino, "pdf")
        if not ok_ver:
            contenido = destino.read_bytes() if destino.exists() else None
            ultimo_motivo = diagnosticar_fallo_portal(
                contenido=contenido,
                detalle=motivo,
                fallback=motivo or "verificacion fallo",
            )
            if console:
                console.print(
                    f"  [yellow][warn] verificacion fallo:[/yellow] {ultimo_motivo}"
                )
            try:
                destino.unlink(missing_ok=True)
            except TypeError:
                if destino.exists():
                    destino.unlink()
            if intento < intentos_max - 1 and console:
                console.print(
                    f"  [yellow][retry {intento + 1}/{intentos_max}][/yellow] "
                    f"{clave_inv} (verificacion)"
                )
            continue

        inventario.add(clave_inv)
        if console:
            console.print(f"  [green][ok ][/green] {nombre_destino}")
        cerrar_tabs_pdf(page.context)
        return Resultado.NUEVO

    if console:
        console.print(f"  [red][FAIL][/red] {clave_inv}: {ultimo_motivo}")
    registrar_fallo(codigo, fila.doc_num, fila.to_dict())
    if motivos_fallidos is not None:
        motivos_fallidos.append((clave_inv, ultimo_motivo or "desconocido"))
    return Resultado.FAIL


def tmp_path_default(base: Path) -> Path:
    """`BASE/VerDocumentoElectronico.pdf` - el sitio siempre escribe ahi."""
    return base / DOWNLOAD_FILENAME
