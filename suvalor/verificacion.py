"""Verificacion post-descarga de archivos para evitar falsos positivos.

El sitio de Suvalor a veces responde con HTML de error, redirige a login con
cookie expirada, o entrega el archivo truncado. Si solo confiamos en que
`download.save_as()` no levante excepcion vamos a marcar como `[ok]` cosas
que en disco son basura.

Estas funciones son puras (no tocan Playwright), reciben un `Path` y
devuelven `(ok: bool, motivo: str)`. `motivo` queda vacio si `ok=True`;
si `ok=False`, describe en pocas palabras el problema (apto para log y
para mostrar en el resumen del CLI).

Idea: NO somos un validador forense de PDFs. Solo atajamos los casos
mas frecuentes de falso positivo:
    - archivo de 0 bytes / muy chico
    - HTML de login camuflado de PDF (cookie vencida)
    - PDF truncado (sin marker `%%EOF` al final)
    - HTML de Portafolio.xls que en realidad es la pagina de login
"""

from __future__ import annotations

from pathlib import Path

from .diagnosticos import clasificar_fallo_portal

# Cuanto del final del PDF leemos para buscar el marker `%%EOF`.
# El marker normalmente aparece en los ultimos ~50 bytes, pero algunos
# generadores agregan basura adicional; 1KB es margen mas que suficiente
# y mantiene la lectura barata.
_PDF_TAIL_BYTES = 1024
_PDF_HEADER = b"%PDF-"
_PDF_EOF_MARKER = b"%%EOF"

# Para HTML camuflado de XLS: si aparece alguna de estas senales en el
# contenido, es casi seguro que el server redirigio a login.
_HTML_LOGIN_HINTS = (
    "iniciar sesion",
    "iniciar sesi&oacute;n",
    "iniciar sesión",
    "login",
)


def sanitizar_pdf_bytes(data: bytes) -> bytes:
    """Trunca bytes posteriores al ultimo marker `%%EOF` de un PDF.

    Solo sanitiza contenido que ya parece PDF y contiene EOF. Para HTML,
    respuestas sin header o PDFs truncados devuelve los bytes originales para
    que la validacion conservadora falle con su motivo normal.
    """
    if not data.startswith(_PDF_HEADER):
        return data
    idx = data.rfind(_PDF_EOF_MARKER)
    if idx < 0:
        return data
    return data[: idx + len(_PDF_EOF_MARKER)]


def sanitizar_pdf_en_archivo(path: Path) -> None:
    """Aplica `sanitizar_pdf_bytes` in-place si hay bytes trailing."""
    try:
        data = path.read_bytes()
    except OSError:
        return
    limpio = sanitizar_pdf_bytes(data)
    if limpio != data:
        path.write_bytes(limpio)


def es_pdf_valido(path: Path, min_bytes: int = 2048) -> tuple[bool, str]:
    """Chequea heuristicamente que `path` sea un PDF no-corrupto.

    Considera valido si:
        - el archivo existe y `size >= min_bytes`
        - los primeros 5 bytes son `%PDF-`
        - el marker `%%EOF` aparece en los ultimos 1KB
    """
    if not path.exists():
        return False, "archivo no existe"

    try:
        size = path.stat().st_size
    except OSError as e:
        return False, f"no pude leer stat: {e}"

    if size == 0:
        return False, "size=0 bytes"

    try:
        with path.open("rb") as f:
            muestra_inicial = f.read(512)
    except OSError as e:
        return False, f"error leyendo: {e}"
    motivo_portal = clasificar_fallo_portal(contenido=muestra_inicial)
    if motivo_portal:
        return False, motivo_portal

    if size < min_bytes:
        return False, f"size={size} bytes < min={min_bytes}"

    try:
        with path.open("rb") as f:
            head = f.read(len(_PDF_HEADER))
            if head != _PDF_HEADER:
                # diagnostico mas util: si parece HTML, decirlo
                resto = head + f.read(256 - len(_PDF_HEADER))
                muestra = resto.lower()
                if b"<html" in muestra or b"<!doctype" in muestra:
                    motivo = clasificar_fallo_portal(contenido=resto)
                    return False, motivo or "es HTML (probable redirect a login)"
                return False, f"header no es %PDF- (head={head!r})"

            # leemos los ultimos `_PDF_TAIL_BYTES` para buscar el marker EOF
            tail_offset = max(0, size - _PDF_TAIL_BYTES)
            f.seek(tail_offset)
            tail = f.read()
            if _PDF_EOF_MARKER not in tail:
                return False, "no encontre marker %%EOF (PDF truncado?)"
    except OSError as e:
        return False, f"error leyendo: {e}"

    return True, ""


def es_xls_html_valido(path: Path, min_bytes: int = 2048) -> tuple[bool, str]:
    """Chequea que `path` sea el HTML camuflado de Portafolio.xls real.

    El sitio entrega el portafolio como un .xls que en realidad es HTML con
    una `<table>`. Si la cookie expiro, en vez del portafolio el server
    devuelve la pagina de login (tambien HTML, pero sin tabla y con
    `iniciar sesion`).

    Considera valido si:
        - el archivo existe y `size >= min_bytes`
        - contiene `<table` en algun lugar (case-insensitive)
        - NO contiene `login` ni `iniciar sesion` (textos del redirect)
    """
    if not path.exists():
        return False, "archivo no existe"

    try:
        size = path.stat().st_size
    except OSError as e:
        return False, f"no pude leer stat: {e}"

    if size == 0:
        return False, "size=0 bytes"
    if size < min_bytes:
        return False, f"size={size} bytes < min={min_bytes}"

    try:
        # Decodificamos best-effort. El portafolio real suele ser latin-1 /
        # cp1252; los errores los ignoramos porque solo buscamos substrings
        # ASCII.
        raw = path.read_bytes()
    except OSError as e:
        return False, f"error leyendo: {e}"

    texto = raw.decode("utf-8", errors="ignore").lower()

    if "<table" not in texto:
        return False, "no encontre <table> (formato inesperado)"

    for hint in _HTML_LOGIN_HINTS:
        if hint in texto:
            return False, f"contiene '{hint}' (probable redirect a login)"

    return True, ""


def verificar_descarga(path: Path, tipo: str) -> tuple[bool, str]:
    """Despachador segun el `tipo` esperado del archivo.

    `tipo` admitido:
        - `'pdf'`      -> usa `es_pdf_valido`
        - `'xls_html'` -> usa `es_xls_html_valido` (el `.xls` que es HTML)
    """
    if tipo == "pdf":
        sanitizar_pdf_en_archivo(path)
        return es_pdf_valido(path)
    if tipo == "xls_html":
        return es_xls_html_valido(path)
    return False, f"tipo de verificacion desconocido: {tipo!r}"
