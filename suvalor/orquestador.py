"""Loop principal: para cada (rango_fechas, tipo_doc) consulta y descarga todo.

Mantiene el flujo del monolito pero con:
    - Progress bars de rich.
    - Memoria adaptativa de timings (`MemoriaTimings`).
    - Resiliencia con tenacity (backoff en consulta y goto_robusto).
    - Deteccion proactiva de sesion expirada -> prompt al usuario.
    - Logging estructurado a archivo + consola (loguru).

Tambien expone funciones core reutilizables que reciben un `page` ya autenticado:
    - sincronizar_documentos(page, ...) -> ResumenCorrida
    - sincronizar_extractos(page, ...)  -> ResumenExtractos
    - sincronizar_cartera(page, ...)    -> ResumenCartera

Estas funciones NO lanzan navegador ni hacen login. El subcomando `sync` del
CLI las invoca en serie sobre una sola sesion de Playwright; los subcomandos
individuales (`descargar`, `extractos`, `cartera`) son envoltorios que tambien
las invocan despues de abrir browser + login_manual.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from loguru import logger
from playwright.sync_api import BrowserContext, Page
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from .config import Config
from .descargador import (
    Resultado,
    descargar_doc,
    exportar_reporte_tesoreria,
    tmp_path_default,
)
from .diagnosticos import sanitizar_diagnostico
from .estado import (
    EstadoCorrida,
    Inventario,
    InventarioExtractos,
    guardar_estado,
    guardar_inventario,
)
from .pagina import (
    NavegacionFallida,
    SessionExpired,
    consultar,
    dismiss_componentart_banner,
    extraer_filas,
    extraer_paginas,
    goto_robusto,
    ir_a_pagina,
    login_manual,
    preparar_tesoreria,
    reloguear_si_expiro,
    setear_filtros,
)
from .parseo import mes_es_a_iso
from .rangos import RangoFechas
from .tesoreria import (
    PlanTesoreria,
    debe_descargar_tesoreria,
    es_tesoreria_sin_movimientos,
    promover_candidato_tesoreria,
)
from .timings import MemoriaTimings, medir
from .verificacion import verificar_descarga
from .tipos import (
    BASE,
    CARTERA_DIR,
    CARTERA_URL,
    CONSULTA_URL,
    EXTRACTO_PDF_URL,
    EXTRACTO_TMP_PATTERN,
    EXTRACTOS_DIR,
    EXTRACTOS_URL,
    ID_BTN_EXCEL,
    ID_DDL_CUENTA,
    ID_DDL_PERIODO,
    NOMBRES_TIPOS,
    TESORERIA_URL,
)


@dataclass
class ResumenCorrida:
    nuevos: int = 0
    saltados: int = 0
    fallidos: int = 0
    consultas_realizadas: int = 0
    consultas_vacias: int = 0
    rangos_total: int = 0
    tipos: list[str] = field(default_factory=list)
    rangos: list[RangoFechas] = field(default_factory=list)
    # (clave_doc, motivo) por cada doc que paso la descarga pero fallo la
    # verificacion post-descarga (PDF truncado, HTML, etc.).
    detalle_fallidos: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class OpcionesCorrida:
    tipos: list[str]
    rangos: list[RangoFechas]
    config: Config
    max_docs: int = 0
    smoke_test: bool = False


@dataclass
class ResumenExtractos:
    nuevos: int = 0
    saltados: int = 0
    fallidos: int = 0
    detalle_fallidos: list[tuple[str, str]] = field(default_factory=list)
    total_inventario: int = 0


@dataclass
class ResumenCartera:
    ok: bool = False
    destino: Optional[Path] = None
    size_kb: float = 0.0
    error: Optional[str] = None
    # Motivo de la verificacion post-descarga si fallo (HTML de login, etc.).
    motivo_verificacion: Optional[str] = None


@dataclass
class ResumenTesoreria:
    nuevos: int = 0
    saltados: int = 0
    fallidos: int = 0
    total: int = 0
    detalle_fallidos: list[tuple[str, str]] = field(default_factory=list)


ExportadorTesoreria = Callable[[Path, str], Path]


def sincronizar_tesoreria_plan(
    *, plan: PlanTesoreria, exportar: ExportadorTesoreria
) -> ResumenTesoreria:
    """Procesa un plan de tesoreria con un exportador inyectado y offline.

    No navega ni abre browser: el caller provee candidatos ya descargados.
    """
    resumen = ResumenTesoreria(total=len(plan.destinos))
    for destino in plan.destinos:
        formato = destino.suffix.lstrip(".")
        if not debe_descargar_tesoreria(
            destino, formato=formato, redownload=plan.redownload
        ):
            resumen.saltados += 1
            continue

        try:
            candidato = exportar(destino, formato)
        except Exception:
            resumen.fallidos += 1
            resumen.detalle_fallidos.append((destino.name, "exportacion fallo"))
            continue

        resultado = promover_candidato_tesoreria(candidato, destino, formato=formato)
        if resultado.ok:
            resumen.nuevos += 1
        elif es_tesoreria_sin_movimientos(resultado.motivo):
            resumen.saltados += 1
        else:
            resumen.fallidos += 1
            resumen.detalle_fallidos.append((destino.name, "promocion fallo"))
    return resumen


def sincronizar_tesoreria(
    *,
    page: Page,
    plan: PlanTesoreria,
    mem: MemoriaTimings,
    console: Console,
    account: str | None = None,
    retry_doc: int = 1,
) -> ResumenTesoreria:
    """Ejecuta Tesoreria opt-in sobre una sesion ya autenticada."""
    resumen = ResumenTesoreria(total=len(plan.destinos))
    try:
        goto_robusto(page, TESORERIA_URL, mem=mem, console=console)
    except SessionExpired:
        reloguear_si_expiro(page, console)
        goto_robusto(page, TESORERIA_URL, mem=mem, console=console)
    dismiss_componentart_banner(page, console)

    idx_destino = 0
    for desde, hasta in plan.rangos:
        destinos_rango = plan.destinos[idx_destino : idx_destino + len(plan.formatos)]
        idx_destino += len(plan.formatos)
        pendientes: list[tuple[Path, str]] = []
        for destino in destinos_rango:
            formato = destino.suffix.lstrip(".")
            if not debe_descargar_tesoreria(
                destino, formato=formato, redownload=plan.redownload
            ):
                resumen.saltados += 1
                continue
            pendientes.append((destino, formato))
        if not pendientes:
            continue

        try:
            preparar_tesoreria(page, desde=desde, hasta=hasta, account=account)
        except Exception as e:
            if account:
                motivo = "no pude preparar tesoreria"
            else:
                motivo = sanitizar_diagnostico(str(e) or "no pude preparar tesoreria")
            for destino, _formato in pendientes:
                resumen.fallidos += 1
                resumen.detalle_fallidos.append((destino.name, motivo))
            continue

        for destino, formato in pendientes:
            timeout_s = mem.timeout_ms("tesoreria") / 1000.0
            ultimo_motivo = ""
            for intento in range(max(1, retry_doc)):
                with medir(mem, "tesoreria"):
                    resultado = exportar_reporte_tesoreria(
                        page=page,
                        destino=destino,
                        formato=formato,
                        timeout_s=timeout_s,
                    )
                if resultado.ok:
                    resumen.nuevos += 1
                    console.print(f"  [green][ok ][/green] {destino.name}")
                    break
                ultimo_motivo = resultado.motivo or "exportacion fallo"
                if es_tesoreria_sin_movimientos(ultimo_motivo):
                    resumen.saltados += 1
                    console.print(
                        f"  [yellow][skip][/yellow] {destino.name}: sin movimientos"
                    )
                    break
                if intento < max(1, retry_doc) - 1:
                    console.print(
                        f"  [yellow][retry {intento + 1}/{max(1, retry_doc)}][/yellow] "
                        f"tesoreria {destino.name}"
                    )
            else:
                resumen.fallidos += 1
                motivo_visible = sanitizar_diagnostico(ultimo_motivo)
                resumen.detalle_fallidos.append((destino.name, motivo_visible))
                console.print(f"  [red][FAIL][/red] {destino.name}: {motivo_visible}")
    return resumen


def _renderear_panel_rango(
    console: Console, rango: RangoFechas, tipos: list[str]
) -> None:
    titulo = f"Rango {rango.desde_dmy} -> {rango.hasta_dmy}"
    body = f"Tipos a procesar: [bold]{', '.join(tipos)}[/bold]"
    console.print(Panel(body, title=titulo, border_style="cyan"))


def correr(
    *,
    context: BrowserContext,
    page: Page,
    opciones: OpcionesCorrida,
    inventario: Inventario,
    estado: EstadoCorrida,
    mem: MemoriaTimings,
    console: Console,
) -> ResumenCorrida:
    """Loop principal (subcomando `descargar` clasico). Hace login_manual y
    luego delega en `_correr_loop`. Para uso desde `sync` (sin re-login),
    usar `sincronizar_documentos`.
    """
    login_manual(page, console)
    return _correr_loop(
        context=context,
        page=page,
        opciones=opciones,
        inventario=inventario,
        estado=estado,
        mem=mem,
        console=console,
    )


def _correr_loop(
    *,
    context: BrowserContext,
    page: Page,
    opciones: OpcionesCorrida,
    inventario: Inventario,
    estado: EstadoCorrida,
    mem: MemoriaTimings,
    console: Console,
) -> ResumenCorrida:
    """Loop puro: asume `page` ya autenticado. Devuelve `ResumenCorrida`."""
    resumen = ResumenCorrida(
        rangos_total=len(opciones.rangos),
        tipos=list(opciones.tipos),
        rangos=list(opciones.rangos),
    )

    tmp_path = tmp_path_default(BASE)

    console.print(f"[cyan]Inventario actual:[/cyan] {len(inventario)} documentos")

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )

    with progress:
        task_rangos = progress.add_task(
            "Rangos", total=len(opciones.rangos) * len(opciones.tipos)
        )

        for rango in opciones.rangos:
            _renderear_panel_rango(console, rango, opciones.tipos)
            year_dir = rango.anio

            for codigo in opciones.tipos:
                progress.update(
                    task_rangos,
                    description=f"[cyan]{rango.desde_dmy}->{rango.hasta_dmy}[/cyan] [bold]{codigo}[/bold]",
                )

                if opciones.max_docs and resumen.nuevos >= opciones.max_docs:
                    console.print(
                        f"[yellow]  [stop] alcanzado max-docs={opciones.max_docs}[/yellow]"
                    )
                    return resumen

                dir_destino = BASE / year_dir / NOMBRES_TIPOS[codigo]
                dir_destino.mkdir(parents=True, exist_ok=True)

                try:
                    goto_robusto(page, CONSULTA_URL, mem=mem, console=console)
                except SessionExpired:
                    reloguear_si_expiro(page, console)
                    goto_robusto(page, CONSULTA_URL, mem=mem, console=console)
                except NavegacionFallida as e:
                    logger.warning(f"goto_robusto fallo: {e}")
                    console.print(
                        "[yellow]  [warn] no pude llegar a la consulta. Verifica login.[/yellow]"
                    )
                    continue

                dismiss_componentart_banner(page, console)
                setear_filtros(page, codigo, rango.desde_dmy, rango.hasta_dmy)

                try:
                    consultar(page, mem)
                except Exception as e:
                    logger.error(f"Error en consultar({codigo}): {e}")
                    console.print(f"[red]  [err] consulta fallo: {e}[/red]")
                    continue
                resumen.consultas_realizadas += 1

                _procesar_paginas(
                    page=page,
                    context=context,
                    codigo=codigo,
                    rango=rango,
                    dir_destino=dir_destino,
                    inventario=inventario,
                    tmp_path=tmp_path,
                    mem=mem,
                    config=opciones.config,
                    max_docs=opciones.max_docs,
                    resumen=resumen,
                    console=console,
                )

                progress.update(task_rangos, advance=1)

    return resumen


def _procesar_paginas(
    *,
    page: Page,
    context: BrowserContext,
    codigo: str,
    rango: RangoFechas,
    dir_destino: Path,
    inventario: Inventario,
    tmp_path: Path,
    mem: MemoriaTimings,
    config: Config,
    max_docs: int,
    resumen: ResumenCorrida,
    console: Console,
) -> None:
    pagina_actual = 1
    paginas_procesadas = 0

    while paginas_procesadas < config.max_pages_per_query:
        filas = extraer_filas(page, codigo)
        if not filas:
            if pagina_actual == 1:
                console.print(f"  [dim]{codigo}: vacio[/dim]")
                resumen.consultas_vacias += 1
            break

        console.print(
            f"  [cyan]{codigo}[/cyan] pag.{pagina_actual}: [bold]{len(filas)}[/bold] doc(s)"
        )

        for fila in filas:
            if max_docs and resumen.nuevos >= max_docs:
                return
            motivos_fila: list[tuple[str, str]] = []
            try:
                resultado = descargar_doc(
                    page=page,
                    fila=fila,
                    codigo=codigo,
                    dir_destino=dir_destino,
                    inventario=inventario,
                    tmp_path=tmp_path,
                    mem=mem,
                    retry_doc=config.retry_doc,
                    console=console,
                    motivos_fallidos=motivos_fila,
                )
            except Exception as e:
                motivo = sanitizar_diagnostico(f"{type(e).__name__}: {e}")
                logger.exception(
                    f"Error inesperado descargando {codigo} idx={fila.idx}: {motivo}"
                )
                resumen.fallidos += 1
                resumen.detalle_fallidos.append((f"{codigo}_{fila.doc_num}", motivo))
                continue

            if resultado == Resultado.NUEVO:
                resumen.nuevos += 1
            elif resultado == Resultado.SKIP:
                resumen.saltados += 1
            else:
                resumen.fallidos += 1
                resumen.detalle_fallidos.extend(motivos_fila)

        paginas_disp = extraer_paginas(page)
        siguiente = next((n for n in paginas_disp if n > pagina_actual), None)
        if not siguiente:
            break
        if not ir_a_pagina(page, siguiente, mem):
            break
        pagina_actual = siguiente
        paginas_procesadas += 1


def renderear_resumen(
    console: Console, resumen: ResumenCorrida, inventario: Inventario
) -> None:
    tabla = Table(
        title="Resumen de la corrida", show_header=True, header_style="bold cyan"
    )
    tabla.add_column("Metrica")
    tabla.add_column("Valor", justify="right")

    tabla.add_row("Tipos procesados", ", ".join(resumen.tipos))
    tabla.add_row("Rangos consultados", str(resumen.rangos_total))
    tabla.add_row("Consultas realizadas", str(resumen.consultas_realizadas))
    tabla.add_row("Consultas vacias", str(resumen.consultas_vacias))
    tabla.add_row("[green]Nuevos descargados[/green]", str(resumen.nuevos))
    tabla.add_row("[yellow]Saltados (ya estaban)[/yellow]", str(resumen.saltados))
    tabla.add_row("[red]Fallidos[/red]", str(resumen.fallidos))
    tabla.add_row("Inventario total", str(len(inventario)))
    console.print(tabla)


def persistir_estado(
    *,
    estado: EstadoCorrida,
    inventario: Inventario,
    resumen: ResumenCorrida,
) -> None:
    guardar_inventario(inventario)
    estado.ultima_corrida = dt.date.today().isoformat()
    estado.rangos_consultados.append(
        {
            "fecha": estado.ultima_corrida,
            "tipos": resumen.tipos,
            "rangos": [(r.desde_dmy, r.hasta_dmy) for r in resumen.rangos],
            "nuevos_esta_corrida": resumen.nuevos,
            "saltados_esta_corrida": resumen.saltados,
            "fallidos_esta_corrida": resumen.fallidos,
            "total_inventario": len(inventario),
        }
    )
    guardar_estado(estado)


# --------------------------------------------------------------------------- #
# Funciones core reutilizables (asumen page ya autenticado).                  #
# --------------------------------------------------------------------------- #


def sincronizar_documentos(
    *,
    context: BrowserContext,
    page: Page,
    opciones: OpcionesCorrida,
    inventario: Inventario,
    estado: EstadoCorrida,
    mem: MemoriaTimings,
    console: Console,
) -> ResumenCorrida:
    """Sincroniza documentos contables. Asume `page` ya autenticado."""
    return _correr_loop(
        context=context,
        page=page,
        opciones=opciones,
        inventario=inventario,
        estado=estado,
        mem=mem,
        console=console,
    )


def _leer_periodos_extractos(page: Page) -> list[tuple[str, str]]:
    """Lee `<select id="ddlPeriodo">` y devuelve [(extractoId, "marzo 2026"), ...]."""
    js = (
        "(() => {"
        f"  const s = document.getElementById('{ID_DDL_PERIODO}');"
        "   if (!s) return null;"
        "   return Array.from(s.options).map(o => ({value: o.value, text: o.textContent.trim()}));"
        "})()"
    )
    res = page.evaluate(js)
    if res is None:
        page.wait_for_timeout(2_000)
        res = page.evaluate(js)
    if res is None:
        return []
    return [(o["value"], o["text"]) for o in res if o.get("value")]


def sincronizar_extractos(
    *,
    page: Page,
    inv_ext: InventarioExtractos,
    mem: MemoriaTimings,
    console: Console,
    solo: Optional[str] = None,
    redownload: bool = False,
    max_n: int = 0,
    retry_doc: int = 1,
) -> ResumenExtractos:
    """Sincroniza extractos consolidados (PDF). Asume `page` ya autenticado."""
    EXTRACTOS_DIR.mkdir(parents=True, exist_ok=True)
    res = ResumenExtractos()

    try:
        goto_robusto(page, EXTRACTOS_URL, mem=mem, console=console)
    except SessionExpired:
        reloguear_si_expiro(page, console)
        goto_robusto(page, EXTRACTOS_URL, mem=mem, console=console)
    except NavegacionFallida as e:
        console.print(f"[red]No pude llegar a la pagina de extractos: {e}[/red]")
        raise

    dismiss_componentart_banner(page, console)
    page.wait_for_timeout(1_500)

    opciones = _leer_periodos_extractos(page)
    if not opciones:
        console.print(
            "[red]No pude leer el dropdown ddlPeriodo. "
            "Revisa la cuenta o el login.[/red]"
        )
        raise NavegacionFallida("ddlPeriodo no disponible")

    tareas: list[tuple[str, str, str]] = []
    for ext_id, texto in opciones:
        try:
            ym = mes_es_a_iso(texto)
        except ValueError as e:
            console.print(f"[yellow]  [warn] no parsee periodo '{texto}': {e}[/yellow]")
            continue
        tareas.append((ext_id, ym, texto))

    if solo:
        tareas = [t for t in tareas if t[1] == solo]
        if not tareas:
            console.print(
                f"[yellow]No hay extracto para {solo} en el dropdown actual.[/yellow]"
            )

    console.print(
        Panel(
            f"Periodos disponibles: [cyan]{len(opciones)}[/cyan]\n"
            f"Inventario actual: [cyan]{len(inv_ext)}[/cyan]\n"
            f"A procesar: [cyan]{len(tareas)}[/cyan]"
            + (f"  filtro --solo={solo}" if solo else ""),
            title="Extractos",
            border_style="cyan",
        )
    )

    for ext_id, ym, texto in tareas:
        if max_n and res.nuevos >= max_n:
            console.print(f"[yellow]  [stop] alcanzado --max={max_n}[/yellow]")
            break

        year = ym.split("-")[0]
        dir_destino = EXTRACTOS_DIR / year
        dir_destino.mkdir(parents=True, exist_ok=True)
        destino = dir_destino / f"{ym}_extracto.pdf"

        if not redownload and (ym in inv_ext or destino.exists()):
            console.print(f"  [yellow][skip][/yellow] {ym} ya existe")
            res.saltados += 1
            inv_ext.add(ym)
            continue

        tmp_path = BASE / EXTRACTO_TMP_PATTERN.format(id=ext_id)
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass

        url = EXTRACTO_PDF_URL.format(id=ext_id)
        console.print(f"  [cyan][...] {ym} ({texto}) -> id={ext_id}[/cyan]")

        timeout_s = mem.timeout_ms("extracto") / 1000.0
        # Pre-borrar destino si re-download
        if destino.exists() and redownload:
            try:
                destino.unlink()
            except Exception:
                pass

        intentos_max = max(1, retry_doc)
        ok = False
        ultimo_motivo = ""
        for intento in range(intentos_max):
            try:
                with medir(mem, "extracto"):
                    # Playwright con accept_downloads=True intercepta la
                    # descarga y le da nombre UUID. Hay que capturar el evento
                    # de download y guardar al destino con save_as.
                    with page.expect_download(timeout=int(timeout_s * 1000)) as dl_info:
                        try:
                            page.goto(
                                url, wait_until="domcontentloaded", timeout=15_000
                            )
                        except Exception:
                            # Navegar a un PDF puede "abortar"
                            # (NS_BINDING_ABORTED) cuando el browser detecta
                            # el attachment. El download igual se dispara.
                            pass
                    download = dl_info.value
                    download.save_as(str(destino))
            except Exception as e:
                logger.exception(f"Error bajando extracto {ym} (id={ext_id}): {e}")
                ultimo_motivo = f"download fallo: {e}"
                if intento < intentos_max - 1:
                    console.print(
                        f"  [yellow][retry {intento + 1}/{intentos_max}][/yellow] {ym}: {ultimo_motivo}"
                    )
                continue

            ok_ver, motivo = verificar_descarga(destino, "pdf")
            if ok_ver:
                ok = True
                break

            ultimo_motivo = motivo
            logger.warning(
                f"Verificacion post-descarga fallo para extracto {ym} "
                f"(id={ext_id}): {motivo}"
            )
            try:
                destino.unlink(missing_ok=True)
            except TypeError:
                # py<3.8 no tiene missing_ok; defensa por si acaso
                if destino.exists():
                    destino.unlink()
            if intento < intentos_max - 1:
                console.print(
                    f"  [yellow][retry {intento + 1}/{intentos_max}][/yellow] "
                    f"{ym}: verificacion fallo ({motivo})"
                )

        if not ok:
            res.fallidos += 1
            motivo_final = ultimo_motivo or "no aparecio el PDF"
            res.detalle_fallidos.append((ym, motivo_final))
            console.print(f"  [red][FAIL][/red] {ym} (id={ext_id}): {motivo_final}")
            continue

        inv_ext.add(ym)
        res.nuevos += 1
        console.print(f"  [green][ok ][/green] {destino.name}")

    res.total_inventario = len(inv_ext)
    return res


def sincronizar_cartera(
    *,
    page: Page,
    mem: MemoriaTimings,
    console: Console,
    account: Optional[str] = None,
    retry_doc: int = 1,
) -> ResumenCartera:
    """Toma snapshot del portafolio actual. Asume `page` ya autenticado.

    Comportamiento clave: SIEMPRE intenta el snapshot. Si ya existe uno con
    fecha de hoy, agrega sufijo `_HHMMSS`. Devuelve `ResumenCartera`.
    """
    CARTERA_DIR.mkdir(parents=True, exist_ok=True)
    res = ResumenCartera()

    try:
        goto_robusto(page, CARTERA_URL, mem=mem, console=console)
    except SessionExpired:
        reloguear_si_expiro(page, console)
        goto_robusto(page, CARTERA_URL, mem=mem, console=console)
    except NavegacionFallida as e:
        res.error = f"No pude llegar a portafolioConsolidado: {e}"
        console.print(f"[red]{res.error}[/red]")
        return res

    dismiss_componentart_banner(page, console)
    page.wait_for_timeout(1_500)

    if account:
        js_select = (
            "(label) => {"
            f"  const s = document.getElementById('{ID_DDL_CUENTA}');"
            "   if (!s) return false;"
            "   const opt = Array.from(s.options).find("
            "     o => o.textContent.toUpperCase().includes(label.toUpperCase())"
            "   );"
            "   if (!opt) return false;"
            "   s.value = opt.value;"
            "   s.dispatchEvent(new Event('change', {bubbles: true}));"
            "   return opt.textContent.trim();"
            "}"
        )
        try:
            elegida = page.evaluate(js_select, account)
        except Exception as e:
            elegida = False
            logger.warning(f"No se pudo configurar la cuenta: {e}")
        if not elegida:
            console.print(
                f"[yellow]No se encontro cuenta con substring '{account}'. "
                "Se continua con la cuenta preseleccionada.[/yellow]"
            )
        else:
            console.print(f"  [cyan]Cuenta seleccionada:[/cyan] {elegida}")
            page.wait_for_timeout(2_500)

    console.print("  [cyan][...] Click btnExcel y esperando Portafolio.xls[/cyan]")

    timeout_s = mem.timeout_ms("cartera") / 1000.0

    # Calcular destino antes (lo necesitamos para save_as)
    hoy = dt.date.today().isoformat()
    destino = CARTERA_DIR / f"{hoy}_portafolio.xls"
    if destino.exists():
        # Snapshot SIEMPRE: sufijo HHMMSS si ya existe uno de hoy.
        hms = dt.datetime.now().strftime("%H%M%S")
        destino = CARTERA_DIR / f"{hoy}_portafolio_{hms}.xls"

    intentos_max = max(1, retry_doc)
    ok = False
    ultimo_motivo = ""
    for intento in range(intentos_max):
        try:
            with medir(mem, "cartera"):
                # Playwright con accept_downloads=True intercepta la descarga
                # y le da nombre UUID. Hay que capturar el evento y save_as.
                with page.expect_download(timeout=int(timeout_s * 1000)) as dl_info:
                    try:
                        page.evaluate(
                            f"document.getElementById('{ID_BTN_EXCEL}').click();"
                        )
                    except Exception as e:
                        logger.warning(f"click btnExcel via evaluate fallo: {e}")
                        try:
                            page.click(f"#{ID_BTN_EXCEL}")
                        except Exception as e2:
                            res.error = f"No pude click btnExcel: {e2}"
                            console.print(f"[red]{res.error}[/red]")
                            return res
                download = dl_info.value
                download.save_as(str(destino))
        except Exception as e:
            logger.exception(f"Error bajando cartera: {e}")
            ultimo_motivo = f"download fallo: {e}"
            if intento < intentos_max - 1:
                console.print(
                    f"  [yellow][retry {intento + 1}/{intentos_max}][/yellow] cartera: {ultimo_motivo}"
                )
            continue

        ok_ver, motivo = verificar_descarga(destino, "xls_html")
        if ok_ver:
            ok = True
            break

        ultimo_motivo = motivo
        logger.warning(f"Verificacion post-descarga fallo para cartera: {motivo}")
        try:
            destino.unlink(missing_ok=True)
        except TypeError:
            if destino.exists():
                destino.unlink()
        if intento < intentos_max - 1:
            console.print(
                f"  [yellow][retry {intento + 1}/{intentos_max}][/yellow] "
                f"cartera: verificacion fallo ({motivo})"
            )

    if not ok:
        res.motivo_verificacion = ultimo_motivo or None
        if not res.error:
            res.error = (
                f"verificacion post-descarga fallo: {ultimo_motivo}"
                if ultimo_motivo
                else "no pude descargar Portafolio.xls"
            )
        console.print(f"[red]{res.error}[/red]")
        return res

    try:
        size_kb = destino.stat().st_size / 1024
    except OSError:
        size_kb = 0.0

    res.ok = True
    res.destino = destino
    res.size_kb = size_kb

    console.print(
        Panel(
            f"[green]OK[/green] {destino}\nTamanio: {size_kb:.1f} KB",
            title="Cartera",
        )
    )
    return res
