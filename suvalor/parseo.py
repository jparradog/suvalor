"""Parseo de fechas y otros strings que aparecen en la UI del sitio."""
from __future__ import annotations

import datetime as dt
import re
import unicodedata

# Mapeo de meses cortos en castellano (como aparecen en la grilla de docs).
_MESES = {
    "ene": "01", "feb": "02", "mar": "03", "abr": "04",
    "may": "05", "jun": "06", "jul": "07", "ago": "08",
    "sep": "09", "set": "09",  # algunos sitios usan "set"
    "oct": "10", "nov": "11", "dic": "12",
}

# Forma larga -> 3 letras (lo que mapea _MESES). Tolerante a acentos.
_MESES_LARGOS = {
    "enero": "ene",
    "febrero": "feb",
    "marzo": "mar",
    "abril": "abr",
    "mayo": "may",
    "junio": "jun",
    "julio": "jul",
    "agosto": "ago",
    "septiembre": "sep", "setiembre": "sep",
    "octubre": "oct",
    "noviembre": "nov",
    "diciembre": "dic",
}


def _quitar_acentos(s: str) -> str:
    """Normaliza removiendo acentos para que 'Diciembre' / 'diciembre' colisionen."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def parsear_fecha_grilla(s: str) -> str:
    """Convierte fechas de grilla a ISO `YYYY-MM-DD`.

    Soporta `12/abr/2025`, `12/abr./2025` y `12/04/2025`. Si el texto
    tiene forma de fecha de grilla pero el mes/dia no es valido, levanta
    `ValueError` en vez de producir fechas imposibles como `YYYY-00-DD`.

    Si no matchea el patron esperado, retorna una version "limpia" del string
    (replace `/` -> `-` y elimina puntos), que es lo que hacia el monolito.
    """
    if not s:
        return s
    m = re.match(r"^\s*(\d{1,2})/([^/]+)/?(\d{4})\s*$", s.lower())
    if not m:
        return s.replace("/", "-").replace(".", "")

    d_raw, mes_raw, a_raw = m.groups()
    mes_norm = _quitar_acentos(mes_raw).strip().strip(".").lower()
    if mes_norm.isdigit():
        mes_num = int(mes_norm)
    else:
        prefijo = mes_norm[:3]
        if prefijo not in _MESES:
            raise ValueError(f"mes no reconocido en {s!r}")
        mes_num = int(_MESES[prefijo])

    fecha = dt.date(int(a_raw), mes_num, int(d_raw))
    return fecha.isoformat()


def fecha_iso_a_dmy(iso: str) -> str:
    """Convierte `YYYY-MM-DD` a `DD/MM/YYYY` (formato que pide el sitio)."""
    d = dt.date.fromisoformat(iso)
    return d.strftime("%d/%m/%Y")


def fecha_dmy_a_iso(dmy: str) -> str:
    """Convierte `DD/MM/YYYY` a `YYYY-MM-DD`."""
    d = dt.datetime.strptime(dmy, "%d/%m/%Y").date()
    return d.isoformat()


def extraer_anio_de_dmy(dmy: str) -> str:
    """Devuelve el componente del anio (`YYYY`) de un string `DD/MM/YYYY`."""
    return dmy.split("/")[-1]


def mes_es_a_iso(text: str) -> str:
    """Convierte un periodo en castellano "marzo 2026" / "ene 2026" a `YYYY-MM`.

    Tolerante a:
      - capitalizacion arbitraria ("Marzo", "MARZO", "marzo")
      - acentos (no son comunes en estos meses, pero los toleramos)
      - abreviado de 3 letras o nombre completo ("ene", "enero", "ene.")
      - palabras intermedias tipo "marzo de 2026"
      - separadores varios ("ene-2026", "ene/2026", "ene 2026")

    Levanta `ValueError` si no puede identificar mes y/o anio.
    """
    if not text or not text.strip():
        raise ValueError("texto vacio")
    raw = _quitar_acentos(text).lower().strip()
    # normalizamos puntos y separadores no alfanumericos a espacios
    norm = re.sub(r"[^a-z0-9]+", " ", raw).strip()
    if not norm:
        raise ValueError(f"sin tokens utiles en {text!r}")

    tokens = norm.split()
    # buscamos el anio (4 digitos) y el mes (alguna palabra que matchee)
    anio: str | None = None
    mes_num: str | None = None

    for tok in tokens:
        if anio is None and re.fullmatch(r"\d{4}", tok):
            anio = tok
            continue
        if mes_num is not None:
            continue
        # nombre completo
        if tok in _MESES_LARGOS:
            mes_num = _MESES[_MESES_LARGOS[tok]]
            continue
        # abreviado de 3 letras
        prefijo = tok[:3]
        if prefijo in _MESES:
            mes_num = _MESES[prefijo]
            continue

    if mes_num is None:
        raise ValueError(f"no pude reconocer mes en {text!r}")
    if anio is None:
        raise ValueError(f"no pude reconocer anio en {text!r}")
    return f"{anio}-{mes_num}"
