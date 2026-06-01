"""Constantes, enums y rutas globales del proyecto suvalor.

Aprendizajes preservados del script monolitico:
- El sitio limita las consultas a 89 dias (no 90 como sugiere el formulario).
- FB (Facturas de Bolsa) y PB (Papeletas de Bolsa) tienden a fallar con 504
  cuando el rango es amplio. Por eso por default solo se procesan RC y NC.
- La sesion expira a los ~7 minutos de inactividad. El sitio entonces redirige
  a `terminarSesion.aspx` o vuelve a mostrar el form de login.
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path


# --- Rutas ---
# BASE: directorio donde el script lee/escribe inventarios, perfil de Chrome,
# logs y carpetas de salida (`2024/`, `Extractos/`, `Cartera/`, ...).
#
# Resolucion (en orden):
#   1. Variable de entorno SUVALOR_HOME, si esta definida y es no-vacia.
#   2. cwd del proceso (el directorio activo al invocar el comando).
#
# Recomendado: configurar SUVALOR_HOME a una carpeta dedicada a los datos
# del portal, separada del repo del codigo. Ver README.
class SuvalorHomeInvalido(RuntimeError):
    """SUVALOR_HOME (o cwd) apunta al codigo fuente del paquete, no a una
    carpeta de datos. Configurar SUVALOR_HOME en una carpeta dedicada."""


def _es_codigo_fuente(path: Path) -> bool:
    """Heuristica: este `path` parece ser el repo del codigo de suvalor?"""
    if not path.is_dir():
        return False
    # Marcadores fuertes: existe `suvalor/cli.py` Y `pyproject.toml` con
    # `name = "suvalor"`.
    if not (path / "suvalor" / "cli.py").is_file():
        return False
    pyproject = path / "pyproject.toml"
    if not pyproject.is_file():
        return False
    try:
        contenido = pyproject.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return 'name = "suvalor"' in contenido


def _resolver_base() -> Path:
    home = os.environ.get("SUVALOR_HOME", "").strip()
    base = Path(home).resolve() if home else Path.cwd().resolve()
    if _es_codigo_fuente(base):
        raise SuvalorHomeInvalido(
            f"SUVALOR_HOME={base} parece ser el repo del codigo fuente.\n"
            "Configure SUVALOR_HOME en una carpeta DEDICADA a los datos del\n"
            "portal (separada del repo). Ej: SUVALOR_HOME=$HOME/Documents/suvalor-data"
        )
    return base


BASE: Path = _resolver_base()
STATE_DIR: Path = BASE / "_state"
PROFILE_DIR: Path = BASE / "_chrome_profile"
FALLIDOS_DIR: Path = BASE / "_Fallidos"

# --- Archivos de estado ---
# IMPORTANTE: nombres preservados del monolito para compatibilidad de datos.
STATE_FILE: Path = STATE_DIR / "ultima_corrida.json"
INVENTORY_FILE: Path = STATE_DIR / "inventario.json"
INVENTORY_EXTRACTOS_FILE: Path = STATE_DIR / "inventario_extractos.json"
TIMINGS_FILE: Path = STATE_DIR / "timings.json"
CONFIG_FILE: Path = STATE_DIR / "config.toml"
LOG_FILE: Path = STATE_DIR / "run.log"
FALLOS_TSV: Path = FALLIDOS_DIR / "fallos.tsv"

# --- Carpetas de salida (subcomandos extractos / cartera / fondos / tesoreria) ---
EXTRACTOS_DIR: Path = BASE / "Extractos"
CARTERA_DIR: Path = BASE / "Cartera"
FONDOS_DIR: Path = BASE / "Fondos"
TESORERIA_DIR: Path = BASE / "Tesoreria"

# --- URLs ---
LOGIN_URL = "https://www.suvalor.com/operaciones/login.aspx"
CONSULTA_URL = (
    "https://www.suvalor.com/documentosElectronicos/"
    "consultarDocumentosElectronicos.aspx"
)
SESSION_TERMINATED_HINT = "terminarSesion.aspx"

# --- URLs (subcomandos extractos / cartera) ---
EXTRACTOS_URL = "https://www.suvalor.com/consultas/extractoInfoGeneral.aspx"
EXTRACTO_PDF_URL = (
    "https://www.suvalor.com/consultas/pdfExtractoConsolidado.aspx?id={id}"
)
CARTERA_URL = "https://www.suvalor.com/consultas/portafolioConsolidado.aspx"
FONDOS_URL = "https://www.suvalor.com/consultas/InformeFondos.aspx"
TESORERIA_URL = "https://www.suvalor.com/consultas/consultarMovimientoTesoreria.aspx"

# --- Nombre del archivo temporal que escribe el visor (descargas docs) ---
# El sitio descarga siempre con este nombre fijo en la carpeta `BASE`.
DOWNLOAD_FILENAME = "VerDocumentoElectronico.pdf"

# --- Nombres de archivo que escribe el sitio (subcomandos nuevos) ---
EXTRACTO_TMP_PATTERN = "extracto-{id}.pdf"
CARTERA_TMP_FILENAME = "Portafolio.xls"

# --- IDs ASP.NET (no cambiar) ---
ID_TIPO_DOC = "ctl00_Contenedor_ucConsultarDocumentosElectronicos_ddlTipoDocumento"
ID_FECHA_INI = "ctl00_Contenedor_ucConsultarDocumentosElectronicos_wcFechaInicial"
ID_FECHA_FIN = "ctl00_Contenedor_ucConsultarDocumentosElectronicos_wcFechaFinal"
ID_BTN_CONSULTAR = "ctl00_Contenedor_ucConsultarDocumentosElectronicos_btnConsultar"
POSTBACK_TARGET_GV = "ctl00$Contenedor$ucConsultarDocumentosElectronicos$gvDocumentos"

# --- IDs ASP.NET extra (extractos / cartera) ---
ID_DDL_PERIODO = "ddlPeriodo"
ID_DDL_CUENTA = "uscSitioTopConsultas_mddlCuentasMultiproducto"
ID_BTN_EXCEL = "btnExcel"

# --- IDs ASP.NET tesoreria (evidencia redacted en docs/SITE_NOTES.md) ---
ID_TESORERIA_CUENTA = "ctl00_Contenedor_mddlCuentasMultiproducto"
ID_TESORERIA_FECHA_INI = "ctl00_Contenedor_wcFechaInicial"
ID_TESORERIA_FECHA_FIN = "ctl00_Contenedor_wcFechaFinal"
ID_TESORERIA_BTN_PDF = "ctl00_Contenedor_btnMovTesoreriaPDF"
ID_TESORERIA_BTN_EXCEL = "ctl00_Contenedor_btnMovTesoreriaExcel"


class TipoDoc(str, Enum):
    """Codigos de tipo de documento aceptados por el formulario suvalor.

    El str-value coincide con lo que espera el `<select>` del filtro en el sitio.
    """

    RC = "RC"
    NC = "NC"
    FB = "FB"
    PB = "PB"
    CE = "CE"
    CC = "CC"


# Mapeo a nombre legible para usar como nombre de carpeta destino.
NOMBRES_TIPOS: dict[str, str] = {
    "RC": "RecibosDeCaja",
    "NC": "NotasContables",
    "FB": "FacturasDeBolsa",
    "PB": "PapeletasDeBolsa",
    "CE": "ComprobantesDeEgreso",
    "CC": "CertificadosDeCustodia",
}

# Tipos que existen actualmente en el selector del portal para consultas nuevas.
# CC se conserva como metadata legacy, pero no debe planear consultas nuevas.
TIPOS_SELECTOR_ACTUALES = {"CE", "FB", "NC", "PB", "RC"}
TIPOS_LEGACY_NO_DISPONIBLES = {"CC"}

# Tipos por defecto para la corrida normal.
# RC, NC y CE son seguros para el flujo default. FB y PB son opt-in; CC es
# legacy local porque ya no aparece en el selector actual del portal.
TIPOS_DEFAULT = ["RC", "NC", "CE"]

# Limite duro del sitio: 89 dias por consulta. NO subir a 90.
MAX_DIAS_POR_RANGO = 89
