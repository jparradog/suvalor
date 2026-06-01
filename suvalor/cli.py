"""Entrypoint Typer del paquete suvalor.

Subcomandos:
    sync               (default) sincroniza TODO en una sola sesion: docs +
                       extractos + snapshot de cartera, con un solo login.
    descargar          flujo de docs contables (lo que era el default antes).
    extractos          descarga extractos consolidados (PDF) por periodo (YYYY-MM).
    cartera            descarga el portafolio consolidado (Excel) y guarda snapshot.
    inventario         lista contadores por tipo + extractos + cartera.
    reset              borra el estado (inventario.json + ultima_corrida.json).
    recuperar-fallidos lee fallos.tsv y reintenta cada fallo.
    config             muestra (o inicializa) `_state/config.toml`.
    timings            imprime las stats actuales aprendidas por operacion.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import sys
from pathlib import Path
from typing import Optional

import typer
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import __version__
from .config import Config, escribir_template
from .diagnosticos import diagnosticar_fallo_portal
from .estado import (
    cargar_estado,
    cargar_inventario,
    cargar_inventario_extractos,
    guardar_inventario_extractos,
    leer_fallos_pendientes,
    reset_estado,
)
from .navegador import abrir_navegador
from .orquestador import (
    OpcionesCorrida,
    ResumenCartera,
    ResumenCorrida,
    ResumenExtractos,
    correr,
    persistir_estado,
    renderear_resumen,
    sincronizar_cartera,
    sincronizar_documentos,
    sincronizar_extractos,
)
from .pagina import (
    NavegacionFallida,
    SessionExpired,
    consultar,
    dismiss_componentart_banner,
    extraer_filas,
    goto_robusto,
    login_manual,
    setear_filtros,
)
from .descargador import Resultado, descargar_doc, tmp_path_default
from .rangos import rangos_para_corrida, resumir_rangos
from .timings import MemoriaTimings
from .tipos import (
    BASE,
    CARTERA_DIR,
    CONSULTA_URL,
    LOG_FILE,
    NOMBRES_TIPOS,
    TIPOS_LEGACY_NO_DISPONIBLES,
    TIPOS_SELECTOR_ACTUALES,
)

_HELP = """\
Descarga automatizada de documentos contables Suvalor / Cibest Capital.

[dim]Cliente no oficial. No esta afiliado a Bancolombia, Valores Bancolombia,
Cibest Capital ni Suvalor. Usar bajo riesgo y responsabilidad propios.

Autor: John Alberto Parrado Gordillo (@jparradog)
Licencia: Apache-2.0
Repositorio: https://github.com/jparradog/suvalor
Disclaimer: https://github.com/jparradog/suvalor/blob/main/DISCLAIMER.md[/dim]
"""

app = typer.Typer(
    name="suvalor",
    help=_HELP,
    no_args_is_help=False,
    rich_markup_mode="rich",
)
console = Console()


def _motivo_visible(motivo: str) -> str:
    """Normaliza y sanitiza motivos antes de mostrarlos al usuario."""
    return diagnosticar_fallo_portal(detalle=motivo, fallback=motivo)


def _renderear_detalle_fallidos_docs(
    console: Console, detalles: list[tuple[str, str]]
) -> None:
    if not detalles:
        return
    console.print("[bold]Detalle fallidos:[/bold]")
    for clave, motivo in detalles:
        console.print(
            f"  Documentos -> Fallo verificacion: {clave} ({_motivo_visible(motivo)})"
        )


# --------------------------------------------------------------------------- #
# Logging setup                                                               #
# --------------------------------------------------------------------------- #


def _setup_logging(verbose: bool = False) -> None:
    """File log: DEBUG (todo). Console: INFO+. (loguru maneja ambos)."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(
        LOG_FILE,
        level="DEBUG",
        rotation="2 MB",
        retention=5,
        encoding="utf-8",
        enqueue=False,
        backtrace=True,
        diagnose=False,
    )
    logger.add(
        sys.stderr,
        level="DEBUG" if verbose else "INFO",
        format="<level>{level:<7}</level> | {message}",
        colorize=True,
    )


def _version_callback(value: bool) -> None:
    if value:
        console.print(
            f"[bold cyan]suvalor[/bold cyan] v{__version__}\n"
            "[dim]Autor:    John Alberto Parrado Gordillo (@jparradog)\n"
            "Licencia: Apache-2.0\n"
            "Repo:     https://github.com/jparradog/suvalor[/dim]"
        )
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", "-V", callback=_version_callback,
        is_eager=True, help="Muestra la version y sale."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Logging DEBUG en consola."),
) -> None:
    _setup_logging(verbose=verbose)
    if ctx.invoked_subcommand is None:
        # sin subcomando -> default = sync con args por default.
        # Pasamos defaults explicitos porque ctx.invoke no resuelve los
        # typer.Option (sin esto, sync recibiria OptionInfo objects que
        # son truthy y dispararia "todas las etapas deshabilitadas").
        ctx.invoke(
            sync,
            no_docs=False,
            no_extractos=False,
            no_cartera=False,
            types="",
            backfill=False,
            desde=None,
            hasta=None,
            smoke_test=False,
            max_docs=0,
        )


# --------------------------------------------------------------------------- #
# Helpers compartidos por `descargar` y `sync`                                #
# --------------------------------------------------------------------------- #


def _tipos_actuales_texto() -> str:
    return ", ".join(sorted(TIPOS_SELECTOR_ACTUALES))


def _reportar_tipos_no_disponibles(tipos: list[str]) -> None:
    no_disponibles = [t for t in tipos if t in TIPOS_LEGACY_NO_DISPONIBLES]
    if not no_disponibles:
        return
    console.print(
        "[red]ERROR:[/red] tipos no disponibles en el selector actual "
        f"{no_disponibles}. Quite CC del config o use tipos actuales: "
        f"{_tipos_actuales_texto()}."
    )
    raise typer.Exit(code=2)


def _parsear_tipos(types_raw: str, cfg: Config) -> list[str]:
    """Toma el string `--types RC,NC` y devuelve la lista validada."""
    raw = types_raw.strip() or ",".join(cfg.tipos_default)
    tipos = [t.strip().upper() for t in raw.split(",") if t.strip()]
    invalidos = [t for t in tipos if t not in NOMBRES_TIPOS]
    if invalidos:
        console.print(
            f"[red]ERROR:[/red] tipos invalidos {invalidos}. "
            f"Validos actuales: {_tipos_actuales_texto()}"
        )
        raise typer.Exit(code=2)
    _reportar_tipos_no_disponibles(tipos)
    if not tipos:
        console.print("[red]ERROR:[/red] sin tipos seleccionados.")
        raise typer.Exit(code=2)
    return tipos


def _construir_opciones_docs(
    *,
    cfg: Config,
    estado,
    backfill: bool,
    desde: Optional[str],
    hasta: Optional[str],
    types: str,
    smoke_test: bool,
    max_docs: int,
) -> OpcionesCorrida:
    """Helper puro: parsea flags + arma OpcionesCorrida."""
    tipos = _parsear_tipos(types, cfg)
    rangos = rangos_para_corrida(
        hoy=dt.date.today(),
        desde_iso=desde,
        hasta_iso=hasta,
        smoke_test=smoke_test,
        backfill=backfill,
        ultima_corrida_iso=estado.ultima_corrida,
        retro_days=cfg.retro_days,
        range_days=cfg.range_days,
    )
    return OpcionesCorrida(
        tipos=tipos, rangos=rangos, config=cfg,
        max_docs=max_docs, smoke_test=smoke_test,
    )


# --------------------------------------------------------------------------- #
# Comando: descargar                                                          #
# --------------------------------------------------------------------------- #


@app.command()
def descargar(
    backfill: bool = typer.Option(False, "--backfill", help="Consulta historica desde 2024-01-01."),
    desde: Optional[str] = typer.Option(None, "--from", help="Fecha desde YYYY-MM-DD."),
    hasta: Optional[str] = typer.Option(None, "--to", help="Fecha hasta YYYY-MM-DD."),
    types: str = typer.Option(
        "",
        "--types",
        help="Tipos a consultar separados por coma (RC,NC,CE; FB/PB opt-in). "
             "Si vacio, usa el default del config.",
    ),
    smoke_test: bool = typer.Option(False, "--smoke-test", help="Solo ultimos 30 dias."),
    max_docs: int = typer.Option(0, "--max-docs", help="Limite de docs a descargar (0 = sin limite)."),
) -> None:
    """Corre el flujo principal: login manual + consulta y descarga por (rango, tipo)."""
    cfg = Config.cargar()
    estado = cargar_estado()
    inventario = cargar_inventario()
    mem = MemoriaTimings()

    opciones = _construir_opciones_docs(
        cfg=cfg, estado=estado,
        backfill=backfill, desde=desde, hasta=hasta,
        types=types, smoke_test=smoke_test, max_docs=max_docs,
    )

    console.print(
        Panel(
            f"[bold]suvalor[/bold] v{__version__}\n"
            f"Tipos: [cyan]{', '.join(opciones.tipos)}[/cyan]\n"
            f"Rangos: [cyan]{resumir_rangos(opciones.rangos)}[/cyan]\n"
            f"Inventario: [cyan]{len(inventario)}[/cyan] documentos",
            title="Iniciando corrida",
            border_style="cyan",
        )
    )
    for r in opciones.rangos:
        console.print(f"  - {r.desde_dmy} a {r.hasta_dmy}")
    logger.info(f"Corrida iniciada. Tipos={opciones.tipos} rangos={len(opciones.rangos)}")

    try:
        with abrir_navegador() as (context, page):
            resumen = correr(
                context=context, page=page, opciones=opciones,
                inventario=inventario, estado=estado, mem=mem, console=console,
            )
    except SessionExpired as e:
        console.print(f"[red]Sesion expirada y no se pudo recuperar: {e}[/red]")
        logger.error(f"SessionExpired: {e}")
        raise typer.Exit(code=3)
    finally:
        try:
            mem.guardar()
        except Exception as e:
            logger.warning(f"No pude guardar timings: {e}")

    persistir_estado(estado=estado, inventario=inventario, resumen=resumen)
    renderear_resumen(console, resumen, inventario)
    if resumen.fallidos > 0:
        from .tipos import FALLOS_TSV
        _renderear_detalle_fallidos_docs(console, list(resumen.detalle_fallidos))
        console.print(f"[yellow]Fallos esta corrida en:[/yellow] {FALLOS_TSV}")


# --------------------------------------------------------------------------- #
# Comando: inventario                                                         #
# --------------------------------------------------------------------------- #


@app.command()
def inventario() -> None:
    """Muestra resumen del inventario por tipo, extractos y cartera."""
    inv = cargar_inventario()
    inv_ext = cargar_inventario_extractos()
    estado = cargar_estado()

    por_tipo: dict[str, int] = {}
    for k in inv.ids:
        codigo = k.split("_", 1)[0] if "_" in k else "??"
        por_tipo[codigo] = por_tipo.get(codigo, 0) + 1

    tabla = Table(title=f"Inventario docs - {len(inv)} totales", header_style="bold cyan")
    tabla.add_column("Tipo")
    tabla.add_column("Nombre")
    tabla.add_column("Cantidad", justify="right")
    for codigo, n in sorted(por_tipo.items(), key=lambda x: -x[1]):
        tabla.add_row(codigo, NOMBRES_TIPOS.get(codigo, "?"), str(n))
    console.print(tabla)

    tabla_ext = Table(
        title=f"Inventario extractos - {len(inv_ext)} totales",
        header_style="bold cyan",
    )
    tabla_ext.add_column("Periodo (YYYY-MM)")
    if inv_ext.ids:
        for periodo in sorted(inv_ext.ids):
            tabla_ext.add_row(periodo)
    else:
        tabla_ext.add_row("[dim](sin extractos registrados)[/dim]")
    console.print(tabla_ext)

    snaps: list[Path] = []
    if CARTERA_DIR.exists():
        snaps = sorted(CARTERA_DIR.glob("*_portafolio.xls"))
    tabla_cart = Table(
        title=f"Cartera (snapshots) - {len(snaps)} archivos",
        header_style="bold cyan",
    )
    tabla_cart.add_column("Archivo")
    tabla_cart.add_column("Tamanio", justify="right")
    if snaps:
        for s in snaps[-10:]:
            try:
                kb = s.stat().st_size / 1024
                tabla_cart.add_row(s.name, f"{kb:.0f} KB")
            except OSError:
                tabla_cart.add_row(s.name, "?")
        if len(snaps) > 10:
            tabla_cart.caption = f"(mostrando ultimos 10 de {len(snaps)})"
    else:
        tabla_cart.add_row("[dim](sin snapshots)[/dim]", "")
    console.print(tabla_cart)

    if estado.ultima_corrida:
        console.print(f"[dim]Ultima corrida:[/dim] {estado.ultima_corrida}")
    if estado.rangos_consultados:
        console.print(
            f"[dim]Historial de corridas:[/dim] {len(estado.rangos_consultados)}"
        )


@app.command()
def reset(
    yes: bool = typer.Option(False, "--yes", "-y", help="No pedir confirmacion."),
) -> None:
    """Borra `_state/inventario.json` y `_state/ultima_corrida.json`."""
    if not yes:
        from rich.prompt import Confirm
        if not Confirm.ask(
            "[bold red]Esto borra inventario.json y ultima_corrida.json.[/bold red] Seguro?"
        ):
            raise typer.Exit()
    a, b = reset_estado()
    if a:
        console.print("[green]inventario.json borrado[/green]")
    if b:
        console.print("[green]ultima_corrida.json borrado[/green]")
    if not (a or b):
        console.print("[yellow]No habia nada que borrar[/yellow]")


def _particionar_fallos_recuperables(
    fallos: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Separa fallos retryables de tipos legacy/no disponibles."""
    recuperables: list[dict[str, str]] = []
    omitidos: list[dict[str, str]] = []
    for fallo in fallos:
        tipo = fallo.get("tipo", "").upper()
        if tipo in TIPOS_SELECTOR_ACTUALES:
            recuperables.append(fallo)
        else:
            omitidos.append(fallo)
    return recuperables, omitidos


@app.command("recuperar-fallidos")
def recuperar_fallidos() -> None:
    """Re-intenta cada fallo en `_Fallidos/fallos.tsv`."""
    fallos = leer_fallos_pendientes()
    if not fallos:
        console.print("[green]No hay fallos pendientes.[/green]")
        return

    fallos, omitidos = _particionar_fallos_recuperables(fallos)
    if omitidos:
        tipos_omitidos = sorted({f.get("tipo", "?") for f in omitidos})
        console.print(
            "[yellow]Saltados por tipo no disponible en el selector actual:[/yellow] "
            f"{len(omitidos)} ({', '.join(tipos_omitidos)})"
        )
    if not fallos:
        console.print(
            "[green]No hay fallos recuperables para consultar en el portal.[/green]"
        )
        return

    console.print(f"[cyan]Recuperando {len(fallos)} fallos...[/cyan]")

    cfg = Config.cargar()
    inv = cargar_inventario()
    mem = MemoriaTimings()
    tmp_path = tmp_path_default(BASE)

    nuevos = saltados = aun_falla = 0
    try:
        with abrir_navegador() as (context, page):
            login_manual(page, console)
            for fallo in fallos:
                tipo = fallo.get("tipo", "")
                doc_num = fallo.get("doc_num", "")
                fecha_iso = fallo.get("fecha_doc", "")
                if not (tipo and doc_num):
                    continue
                clave = f"{tipo}_{doc_num}"
                if clave in inv:
                    saltados += 1
                    continue
                try:
                    fecha = dt.date.fromisoformat(
                        fecha_iso if "-" in fecha_iso else fecha_iso.replace("/", "-")
                    )
                    desde_dmy = (fecha - dt.timedelta(days=2)).strftime("%d/%m/%Y")
                    hasta_dmy = (fecha + dt.timedelta(days=2)).strftime("%d/%m/%Y")
                except Exception:
                    hoy = dt.date.today()
                    desde_dmy = (hoy - dt.timedelta(days=30)).strftime("%d/%m/%Y")
                    hasta_dmy = hoy.strftime("%d/%m/%Y")

                year = desde_dmy.split("/")[-1]
                dir_destino = BASE / year / NOMBRES_TIPOS.get(tipo, tipo)
                dir_destino.mkdir(parents=True, exist_ok=True)

                try:
                    goto_robusto(page, CONSULTA_URL, mem=mem, console=console)
                except (SessionExpired, NavegacionFallida) as e:
                    console.print(f"[red]Error navegando: {e}[/red]")
                    aun_falla += 1
                    continue
                dismiss_componentart_banner(page, console)
                setear_filtros(page, tipo, desde_dmy, hasta_dmy)
                consultar(page, mem)

                filas = extraer_filas(page)
                fila = next((f for f in filas if f.doc_num == doc_num), None)
                if not fila:
                    console.print(f"[yellow]No encontre {clave} en {desde_dmy}->{hasta_dmy}[/yellow]")
                    aun_falla += 1
                    continue

                resultado = descargar_doc(
                    page=page, fila=fila, codigo=tipo,
                    dir_destino=dir_destino, inventario=inv,
                    tmp_path=tmp_path, mem=mem, retry_doc=cfg.retry_doc,
                    console=console,
                )
                if resultado == Resultado.NUEVO:
                    nuevos += 1
                elif resultado == Resultado.SKIP:
                    saltados += 1
                else:
                    aun_falla += 1
    finally:
        mem.guardar()
        from .estado import guardar_inventario
        guardar_inventario(inv)

    console.print(
        Panel(
            f"[green]Recuperados:[/green] {nuevos}\n"
            f"[yellow]Saltados:[/yellow] {saltados}\n"
            f"[red]Aun fallan:[/red] {aun_falla}",
            title="Recuperacion de fallidos",
            border_style="cyan",
        )
    )


config_app = typer.Typer(help="Mostrar / inicializar configuracion en _state/config.toml.")
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show() -> None:
    cfg = Config.cargar()
    tabla = Table(title="Configuracion", header_style="bold cyan")
    tabla.add_column("Clave")
    tabla.add_column("Valor")
    for k, v in cfg.to_dict().items():
        tabla.add_row(k, str(v))
    console.print(tabla)


@config_app.command("init")
def config_init(
    force: bool = typer.Option(False, "--force", help="Sobrescribir si existe."),
) -> None:
    from .tipos import CONFIG_FILE
    if CONFIG_FILE.exists() and not force:
        console.print(
            f"[yellow]Ya existe {CONFIG_FILE}. Usa --force para sobrescribir.[/yellow]"
        )
        raise typer.Exit(code=1)
    path = escribir_template()
    console.print(f"[green]Escrito:[/green] {path}")


@app.command()
def timings() -> None:
    mem = MemoriaTimings()
    tabla = Table(title="Timings aprendidos", header_style="bold cyan")
    tabla.add_column("Operacion")
    tabla.add_column("p50 (s)", justify="right")
    tabla.add_column("p95 (s)", justify="right")
    tabla.add_column("max (s)", justify="right")
    tabla.add_column("n", justify="right")
    tabla.add_column("timeout (s)", justify="right")
    for op in mem.operaciones():
        s = mem.stats[op]
        tabla.add_row(
            op,
            f"{s.p50/1000:.1f}",
            f"{s.p95/1000:.1f}",
            f"{s.max_visto/1000:.1f}",
            str(s.n_total),
            f"{mem.timeout_ms(op)/1000:.1f}",
        )
    console.print(tabla)


# --------------------------------------------------------------------------- #
# Comando: extractos                                                          #
# --------------------------------------------------------------------------- #


@app.command()
def extractos(
    solo: Optional[str] = typer.Option(
        None, "--solo",
        help="Descargar solo el periodo YYYY-MM (ej. 2025-04).",
    ),
    redownload: bool = typer.Option(
        False, "--redownload", help="Ignora inventario/disco y re-baja todos los disponibles."
    ),
    max_n: int = typer.Option(
        0, "--max", help="Limite de descargas en esta corrida (0 = sin limite)."
    ),
) -> None:
    """Descarga extractos consolidados (PDF) por periodo (YYYY-MM)."""
    cfg = Config.cargar()
    mem = MemoriaTimings()
    inv_ext = cargar_inventario_extractos()

    res: ResumenExtractos = ResumenExtractos()
    try:
        with abrir_navegador() as (context, page):
            login_manual(page, console)
            try:
                res = sincronizar_extractos(
                    page=page, inv_ext=inv_ext, mem=mem, console=console,
                    solo=solo, redownload=redownload, max_n=max_n,
                    retry_doc=cfg.retry_doc,
                )
            except (SessionExpired, NavegacionFallida) as e:
                console.print(f"[red]Error sincronizando extractos: {e}[/red]")
                raise typer.Exit(code=3)
    except SessionExpired as e:
        console.print(f"[red]Sesion expirada: {e}[/red]")
        raise typer.Exit(code=3)
    finally:
        try:
            mem.guardar()
        except Exception as e:
            logger.warning(f"No pude guardar timings: {e}")
        try:
            guardar_inventario_extractos(inv_ext)
        except Exception as e:
            logger.warning(f"No pude guardar inventario_extractos: {e}")

    console.print(
        Panel(
            f"[green]Nuevos:[/green] {res.nuevos}\n"
            f"[yellow]Saltados:[/yellow] {res.saltados}\n"
            f"[red]Fallidos:[/red] {res.fallidos}\n"
            f"Inventario total: {len(inv_ext)}",
            title="Resumen extractos",
            border_style="cyan",
        )
    )
    if res.detalle_fallidos:
        console.print("[red]Fallidos:[/red]")
        for ym, motivo in res.detalle_fallidos:
            console.print(f"  - {ym}: {motivo}")


# --------------------------------------------------------------------------- #
# Comando: cartera                                                            #
# --------------------------------------------------------------------------- #


@app.command()
def cartera(
    account: Optional[str] = typer.Option(
        None, "--account",
        help='Etiqueta (substring) de la cuenta a seleccionar. '
             'Default: la que este preseleccionada o "TODAS LAS CUENTAS".',
    ),
) -> None:
    """Descarga el portafolio consolidado (Excel) y lo guarda en `Cartera/`."""
    cfg = Config.cargar()
    mem = MemoriaTimings()

    res: ResumenCartera = ResumenCartera()
    try:
        with abrir_navegador() as (context, page):
            login_manual(page, console)
            res = sincronizar_cartera(
                page=page, mem=mem, console=console, account=account,
                retry_doc=cfg.retry_doc,
            )
    except SessionExpired as e:
        console.print(f"[red]Sesion expirada: {e}[/red]")
        raise typer.Exit(code=3)
    finally:
        try:
            mem.guardar()
        except Exception as e:
            logger.warning(f"No pude guardar timings: {e}")

    if not res.ok:
        raise typer.Exit(code=3)


# --------------------------------------------------------------------------- #
# Comando: sync (NUEVO - default)                                             #
# --------------------------------------------------------------------------- #


@dataclasses.dataclass
class _PlanSync:
    """Que etapas correr en `sync`. Util para tests del argument parsing."""
    do_docs: bool
    do_extractos: bool
    do_cartera: bool

    def nada_que_hacer(self) -> bool:
        return not (self.do_docs or self.do_extractos or self.do_cartera)


def _plan_desde_flags(
    *,
    no_docs: bool,
    no_extractos: bool,
    no_cartera: bool,
) -> _PlanSync:
    """Helper puro: traduce los `--no-X` a un plan de etapas. Testeable sin Playwright."""
    return _PlanSync(
        do_docs=not no_docs,
        do_extractos=not no_extractos,
        do_cartera=not no_cartera,
    )


def _renderear_resumen_sync(
    *,
    plan: _PlanSync,
    res_docs: Optional[ResumenCorrida],
    err_docs: Optional[str],
    res_ext: Optional[ResumenExtractos],
    err_ext: Optional[str],
    res_cart: Optional[ResumenCartera],
    err_cart: Optional[str],
) -> None:
    """Imprime tabla rich con el resumen unificado de las tres etapas."""
    tabla = Table(title="Resumen sync", show_header=True, header_style="bold cyan")
    tabla.add_column("Etapa")
    tabla.add_column("Resultado")

    if not plan.do_docs:
        tabla.add_row("Documentos", "[dim]saltado (--no-docs)[/dim]")
    elif err_docs:
        tabla.add_row("Documentos", f"[red]ERROR: {err_docs}[/red]")
    elif res_docs is not None:
        tabla.add_row(
            "Documentos",
            f"nuevos=[green]{res_docs.nuevos}[/green] "
            f"saltados=[yellow]{res_docs.saltados}[/yellow] "
            f"fallidos=[red]{res_docs.fallidos}[/red]",
        )
    else:
        tabla.add_row("Documentos", "[red]ERROR: sin resultado[/red]")

    if not plan.do_extractos:
        tabla.add_row("Extractos", "[dim]saltado (--no-extractos)[/dim]")
    elif err_ext:
        tabla.add_row("Extractos", f"[red]ERROR: {err_ext}[/red]")
    elif res_ext is not None:
        tabla.add_row(
            "Extractos",
            f"nuevos=[green]{res_ext.nuevos}[/green] "
            f"saltados=[yellow]{res_ext.saltados}[/yellow] "
            f"fallidos=[red]{res_ext.fallidos}[/red]",
        )
    else:
        tabla.add_row("Extractos", "[red]ERROR: sin resultado[/red]")

    if not plan.do_cartera:
        tabla.add_row("Cartera", "[dim]saltado (--no-cartera)[/dim]")
    elif err_cart:
        tabla.add_row("Cartera", f"[red]ERROR: {err_cart}[/red]")
    elif res_cart is not None and res_cart.ok and res_cart.destino is not None:
        try:
            rel = res_cart.destino.relative_to(BASE)
        except ValueError:
            rel = res_cart.destino
        tabla.add_row("Cartera", f"[green]{rel}[/green] ({res_cart.size_kb:.0f} KB)")
    elif res_cart is not None and res_cart.error:
        tabla.add_row("Cartera", f"[red]ERROR: {res_cart.error}[/red]")
    else:
        tabla.add_row("Cartera", "[red]ERROR: sin resultado[/red]")

    console.print(tabla)

    # Sub-seccion: motivos de fallos de verificacion (solo si los hay).
    motivos_docs = (
        list(res_docs.detalle_fallidos)
        if res_docs is not None and res_docs.detalle_fallidos else []
    )
    motivos_ext = (
        list(res_ext.detalle_fallidos)
        if res_ext is not None and res_ext.detalle_fallidos else []
    )
    motivo_cart = (
        res_cart.motivo_verificacion
        if res_cart is not None and res_cart.motivo_verificacion else None
    )

    if motivos_docs or motivos_ext or motivo_cart:
        console.print("[bold]Detalle fallidos:[/bold]")
        for clave, motivo in motivos_docs:
            console.print(
                f"  Documentos -> Fallo verificacion: {clave} ({_motivo_visible(motivo)})"
            )
        for clave, motivo in motivos_ext:
            console.print(
                f"  Extractos  -> Fallo verificacion: {clave} ({_motivo_visible(motivo)})"
            )
        if motivo_cart:
            console.print(
                f"  Cartera    -> Fallo verificacion: {_motivo_visible(motivo_cart)}"
            )


@app.command()
def sync(
    no_docs: bool = typer.Option(False, "--no-docs", help="Saltarse documentos contables."),
    no_extractos: bool = typer.Option(False, "--no-extractos", help="Saltarse extractos PDF."),
    no_cartera: bool = typer.Option(False, "--no-cartera", help="Saltarse snapshot de cartera."),
    types: str = typer.Option(
        "", "--types",
        help="Tipos a consultar separados por coma (RC,NC,CE; FB/PB opt-in). "
             "Si vacio, usa el default del config. Solo afecta a la etapa de docs.",
    ),
    backfill: bool = typer.Option(False, "--backfill", help="Docs: consulta historica desde 2024-01-01."),
    desde: Optional[str] = typer.Option(None, "--from", help="Docs: fecha desde YYYY-MM-DD."),
    hasta: Optional[str] = typer.Option(None, "--to", help="Docs: fecha hasta YYYY-MM-DD."),
    smoke_test: bool = typer.Option(False, "--smoke-test", help="Docs: solo ultimos 30 dias."),
    max_docs: int = typer.Option(0, "--max-docs", help="Docs: limite de descargas (0 = sin limite)."),
) -> None:
    """Sincroniza TODO en una sola sesion: docs + extractos + snapshot de cartera.

    Una sola corrida de Playwright + un solo login manual. Si una etapa falla
    (sesion expira, error de red), las demas siguen y el resumen final lo
    refleja. Es el comando default cuando se invoca `uv run suvalor` sin args.
    """
    plan = _plan_desde_flags(
        no_docs=no_docs, no_extractos=no_extractos, no_cartera=no_cartera,
    )
    if plan.nada_que_hacer():
        console.print(
            "[red]ERROR:[/red] todas las etapas estan deshabilitadas. Quita "
            "alguno de los --no-docs / --no-extractos / --no-cartera."
        )
        raise typer.Exit(code=2)

    cfg = Config.cargar()
    estado = cargar_estado()
    inventario = cargar_inventario()
    inv_ext = cargar_inventario_extractos()
    mem = MemoriaTimings()

    opciones_docs: Optional[OpcionesCorrida] = None
    if plan.do_docs:
        opciones_docs = _construir_opciones_docs(
            cfg=cfg, estado=estado,
            backfill=backfill, desde=desde, hasta=hasta,
            types=types, smoke_test=smoke_test, max_docs=max_docs,
        )

    console.print(
        Panel(
            f"[bold]suvalor sync[/bold] v{__version__}\n"
            f"Etapas: "
            f"[{'cyan' if plan.do_docs else 'dim'}]docs[/{'cyan' if plan.do_docs else 'dim'}] "
            f"[{'cyan' if plan.do_extractos else 'dim'}]extractos[/{'cyan' if plan.do_extractos else 'dim'}] "
            f"[{'cyan' if plan.do_cartera else 'dim'}]cartera[/{'cyan' if plan.do_cartera else 'dim'}]",
            title="Iniciando sync",
            border_style="cyan",
        )
    )

    res_docs: Optional[ResumenCorrida] = None
    err_docs: Optional[str] = None
    res_ext: Optional[ResumenExtractos] = None
    err_ext: Optional[str] = None
    res_cart: Optional[ResumenCartera] = None
    err_cart: Optional[str] = None

    try:
        with abrir_navegador() as (context, page):
            login_manual(page, console)

            if plan.do_docs and opciones_docs is not None:
                console.rule("[bold cyan]Etapa 1/3: documentos[/bold cyan]")
                try:
                    res_docs = sincronizar_documentos(
                        context=context, page=page, opciones=opciones_docs,
                        inventario=inventario, estado=estado, mem=mem, console=console,
                    )
                except SessionExpired as e:
                    err_docs = f"sesion expirada: {e}"
                    logger.error(f"sync.docs SessionExpired: {e}")
                    console.print(f"[red]Etapa docs fallo: {err_docs}[/red]")
                except Exception as e:
                    err_docs = f"{type(e).__name__}: {e}"
                    logger.exception(f"sync.docs error inesperado: {e}")
                    console.print(f"[red]Etapa docs fallo: {err_docs}[/red]")

            if plan.do_extractos:
                console.rule("[bold cyan]Etapa 2/3: extractos[/bold cyan]")
                try:
                    res_ext = sincronizar_extractos(
                        page=page, inv_ext=inv_ext, mem=mem, console=console,
                        retry_doc=cfg.retry_doc,
                    )
                except SessionExpired as e:
                    err_ext = f"sesion expirada: {e}"
                    logger.error(f"sync.extractos SessionExpired: {e}")
                    console.print(f"[red]Etapa extractos fallo: {err_ext}[/red]")
                except Exception as e:
                    err_ext = f"{type(e).__name__}: {e}"
                    logger.exception(f"sync.extractos error inesperado: {e}")
                    console.print(f"[red]Etapa extractos fallo: {err_ext}[/red]")

            if plan.do_cartera:
                console.rule("[bold cyan]Etapa 3/3: cartera[/bold cyan]")
                try:
                    res_cart = sincronizar_cartera(
                        page=page, mem=mem, console=console,
                        retry_doc=cfg.retry_doc,
                    )
                    if not res_cart.ok and res_cart.error:
                        err_cart = res_cart.error
                except SessionExpired as e:
                    err_cart = f"sesion expirada: {e}"
                    logger.error(f"sync.cartera SessionExpired: {e}")
                    console.print(f"[red]Etapa cartera fallo: {err_cart}[/red]")
                except Exception as e:
                    err_cart = f"{type(e).__name__}: {e}"
                    logger.exception(f"sync.cartera error inesperado: {e}")
                    console.print(f"[red]Etapa cartera fallo: {err_cart}[/red]")
    finally:
        try:
            mem.guardar()
        except Exception as e:
            logger.warning(f"No pude guardar timings: {e}")
        if plan.do_extractos:
            try:
                guardar_inventario_extractos(inv_ext)
            except Exception as e:
                logger.warning(f"No pude guardar inventario_extractos: {e}")
        if plan.do_docs and res_docs is not None:
            try:
                persistir_estado(estado=estado, inventario=inventario, resumen=res_docs)
            except Exception as e:
                logger.warning(f"No pude persistir estado de docs: {e}")

    _renderear_resumen_sync(
        plan=plan,
        res_docs=res_docs, err_docs=err_docs,
        res_ext=res_ext, err_ext=err_ext,
        res_cart=res_cart, err_cart=err_cart,
    )

    # Exit code: 0 si todo OK; 3 si hubo errores parciales (excepciones por etapa
    # o fallidos > 0 en docs/extractos, o cartera no quedo ok).
    hubo_error = bool(err_docs or err_ext or err_cart)
    if plan.do_docs and res_docs is not None and res_docs.fallidos > 0:
        hubo_error = True
    if plan.do_extractos and res_ext is not None and res_ext.fallidos > 0:
        hubo_error = True
    if plan.do_cartera and res_cart is not None and not res_cart.ok:
        hubo_error = True

    raise typer.Exit(code=3 if hubo_error else 0)


def main() -> None:
    """Entry point del CLI suvalor."""
    app()


if __name__ == "__main__":
    main()
