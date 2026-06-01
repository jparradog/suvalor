# Hallazgos tecnicos del portal

> **Ultima verificacion**: 2026-04-28 — los IDs ASP.NET, URLs y
> restricciones documentadas reflejan el estado del portal a esa fecha.
> Si encontras divergencias, abrir un PR con el cambio + fecha nueva.

Documentacion del comportamiento del portal Suvalor / Cibest Capital
relevante para el funcionamiento del cliente. Util para mantenimiento
cuando el portal cambie y rompa el script.

> Esta informacion se obtuvo navegando manualmente el portal con sesion
> propia autenticada. **No** incluye datos personales, numeros de cuenta,
> IDs de cliente, ni cualquier otro identificador. Antes de actualizar
> este documento, **redactar cualquier dato sensible** antes de commitear.

---

## Stack del sitio

- ASP.NET WebForms.
- ComponentArt Menu (en algunas vistas la version demo muestra un banner
  que el script descarta automaticamente).
- Login con teclado virtual numerico (4 digitos en posiciones aleatorias)
  + reCAPTCHA. **No automatizable.**
- Cookies de sesion estandar; expiran tras ~7 minutos sin actividad y
  redirigen a `terminarSesion.aspx` o vuelven al form de login.

## Endpoints principales

| Funcionalidad | URL |
|---|---|
| Login | `https://www.suvalor.com/operaciones/login.aspx` |
| Documentos contables | `https://www.suvalor.com/documentosElectronicos/consultarDocumentosElectronicos.aspx` |
| Extractos (lista de meses) | `https://www.suvalor.com/consultas/extractoInfoGeneral.aspx` |
| Extracto PDF directo | `https://www.suvalor.com/consultas/pdfExtractoConsolidado.aspx?id=<extractoId>` |
| Cartera (Excel) | `https://www.suvalor.com/consultas/portafolioConsolidado.aspx` (submit `btnExcel`) |
| Termino de sesion | `https://www.suvalor.com/operaciones/terminarSesion.aspx` |

## Restricciones observadas

- **Documentos contables**: rango maximo de **89 dias por consulta**.
  El sitio sugiere 90 pero al pasarlos da error. NO subir.
- **Extractos**: solo los **ultimos 12 meses** estan disponibles. Para
  historico anterior hay que pedirlo por canales del banco.
- **Sesion**: expira a los **~7 minutos sin actividad**.
- **Selector actual de documentos**: evidencia manual redacted de issue #1
  muestra `CE`, `FB`, `NC`, `PB` y `RC`; no muestra `CC`.
- **Defaults seguros**: el cliente consulta por default solo `RC`, `NC`,
  `CE`. `FB` y `PB` son opt-in con `--types`.
- **CC (Certificados de Custodia)**: tipo legacy local. Debe seguir siendo
  legible en `_state/`, inventarios y `fallos.tsv`, pero no se debe planear
  como consulta nueva porque no aparece en el selector actual.
- **recuperar-fallidos**: las filas legacy `CC` se saltan antes de cargar
  config/timings o abrir navegador. Si hay mezcla con tipos actuales, solo
  se reintentan los actuales.

## Documentos contables — flujo de descarga

### IDs ASP.NET clave

```
ctl00_Contenedor_ucConsultarDocumentosElectronicos_ddlTipoDocumento
ctl00_Contenedor_ucConsultarDocumentosElectronicos_wcFechaInicial
ctl00_Contenedor_ucConsultarDocumentosElectronicos_wcFechaFinal
ctl00_Contenedor_ucConsultarDocumentosElectronicos_btnConsultar
ctl00$Contenedor$ucConsultarDocumentosElectronicos$gvDocumentos  (postback de la grilla)
```

### Flujo

1. Configurar `ddlTipoDocumento` (selector actual: CE, FB, NC, PB, RC).
2. Configurar `wcFechaInicial` y `wcFechaFinal` (rango ≤ 89 dias).
3. Click `btnConsultar`.
4. La grilla `gvDocumentos` se rellena. Cada fila tiene un link `Select$N`
   en la primera columna que dispara `__doPostBack` y abre el visor PDF.
5. Click en `Select$N` → el sitio descarga `VerDocumentoElectronico.pdf`
   en la carpeta de descargas del navegador (apuntada a `BASE`).
6. Renombrar a `BASE/<año>/<carpeta-tipo>/<YYYY-MM-DD>_<TIPO>_<NUMERO>.pdf`.

### Patron de nombres

| Tipo | Patron del archivo final |
|---|---|
| Documento contable | `YYYY-MM-DD_TIPO_NUMERO.pdf` |
| Extracto consolidado | `YYYY-MM_extracto.pdf` |
| Snapshot cartera | `YYYY-MM-DD_portafolio.xls` (sufijo `_HHMMSS` si hay varios el mismo dia) |

### Carpetas de salida

```
BASE/
├── YYYY/
│   ├── RecibosDeCaja/
│   ├── NotasContables/
│   ├── ComprobantesDeEgreso/
│   ├── CertificadosDeCustodia/
│   ├── FacturasDeBolsa/
│   └── PapeletasDeBolsa/
├── Extractos/YYYY/
└── Cartera/
```

### Adobe Acrobat extension — gotcha

Si Chrome tiene la extension de Adobe Acrobat, los PDFs **NO disparan
download event**: se abren en visor inline en una pestaña popup.

Mitigacion implementada en `descargador.py`:

1. Detectar el popup tab que abre el visor.
2. Extraer la URL del PDF.
3. Llamar `context.request.get(url)` con las cookies de sesion ya
   establecidas → bytes del PDF en memoria.
4. Escribir manualmente al filesystem.
5. Cerrar la pestaña popup.

---

## Extractos consolidados — flujo de descarga

### IDs

- `ddlPeriodo` — dropdown con los **ultimos 12 meses** disponibles. Cada
  `<option>` tiene `value` = `extractoId` numerico, `text` = "marzo 2026"
  (mes en español + año).
- `uscSitioTopConsultas_mddlCuentasMultiproducto` — selector de cuenta.
  Por defecto trae la cuenta del usuario; no tocar a menos que tenga
  varias cuentas.
- `lnkPDF` — link "Descargar en PDF" en la UI (no se necesita: la URL
  directa funciona).

### Flujo simplificado

1. Navegar a `extractoInfoGeneral.aspx`.
2. Leer `ddlPeriodo` → lista de `(extractoId, "mes año")`.
3. Convertir cada `text` a `YYYY-MM` via `parseo.mes_es_a_iso()`.
4. Para cada `(extractoId, YYYY-MM)`:
   - Target = `Extractos/YYYY/YYYY-MM_extracto.pdf`.
   - Si existe en disco o en `inventario_extractos.json`, skip.
   - Si no, navegar a
     `pdfExtractoConsolidado.aspx?id=<extractoId>`.
   - Esperar `extracto-<id>.pdf` en `BASE` (polling).
   - Mover y renombrar a target.

Es **GET directo, sin postback**. Solo requiere cookie de sesion.

---

## Cartera (portafolio consolidado) — flujo de descarga

### IDs

- `uscSitioTopConsultas_mddlCuentasMultiproducto` — selector de cuenta
  (opciones: las del cliente + "TODAS LAS CUENTAS").
- `btnExcel` — `<input type="submit">` que dispara la exportacion.

### Flujo

1. Navegar a `portafolioConsolidado.aspx`.
2. (Opcional) Seleccionar cuenta especifica via dropdown.
3. Click `btnExcel` → submit normal del form `Form1`.
4. Servidor responde con `Portafolio.xls` (~88 KB).
5. Mover/renombrar a `Cartera/YYYY-MM-DD_portafolio.xls`.

### Formato del archivo

- Extension `.xls` pero internamente es **HTML con `<table>` tags** en
  ISO-8859-1, ~700 tablas anidadas.
- Excel lo abre nativamente.
- Contiene la lista de instrumentos, valor de mercado, saldos por moneda,
  fondos, operaciones pendientes.

### No hay historico de cartera

`/consultaEventos/ConsultaPortafolio.aspx` es solo un **audit log de
cuando se consulto** la cartera, NO un historico de snapshots. Por eso
el script siempre baja un snapshot nuevo (idempotencia por dia + sufijo
`_HHMMSS` si hay multiple corridas el mismo dia).

---

## Verificacion post-descarga

### PDFs

Tras `save_as`, validar:

- Empieza con bytes `%PDF-`.
- Termina con `%%EOF` (con whitespace tolerante despues).
- Tamaño > 2 KB.

Si falla → el server probablemente respondio HTML de login en vez del PDF.
Borrar archivo basura y reintentar.

### XLS-HTML (cartera)

Validar:

- Contiene tag `<table` (case-insensitive).
- **NO** contiene `login` ni `iniciar sesion`.

Misma logica de retry si falla.

---

## Endpoints relacionados (no implementados aun)

| Funcion | URL | Notas |
|---|---|---|
| Movimientos de Tesoreria | `/consultas/consultarMovimientoTesoreria.aspx` | Form con FechaInicial/FechaFinal + selector cuenta + botones PDF (`btnMovTesoreriaPDF`) y Excel (`btnMovTesoreriaExcel`). Util para flujo de caja. |
| Movimientos Wompi | `/consultas/MovimientosWompi.aspx` | No explorado. |
| Informe movimientos fondos | `/consultas/InformeFondos.aspx` | No explorado. |
| Suscripcion a documentos | `/operaciones/suscripcionDocumentos.aspx` | Form de suscripcion (no descarga). |

Si ves valor en agregar alguno de estos, abre un issue antes de empezar.

### ReteFuente certificate investigation

- Estado: **investigacion solamente / deshabilitado / no soportado**.
  No existe comando `suvalor retefuente`, flag experimental, integracion en
  `sync`, ni flujo de descarga runtime.
- Endpoint observado: `/operaciones/reteFuente.aspx`.
- Controles observados: `ddlAnioRetencion` y `btnDescargarPDF`.
- Resultado del probe manual redacted: hacer click en `btnDescargarPDF`
  produjo **sin descarga / no download** y **sin popup / no popup**. Este
  resultado es inconcluso; no debe reportarse como certificado descargado.
- Gate de evidencia antes de automatizar: documentar selectores redacted,
  DevTools/Network o red equivalente, request URL sin query sensible,
  metodo, status, `content-type`, `content-disposition`, tamano, redirect
  chain, y bytes `%PDF-` con `%%EOF` o un estado clasificado de
  `sin certificado` / no-certificate.
- Expiracion de sesion: login redirect, expired-session o sesion expirada es
  un resultado separado. No debe disparar reautenticacion automatica ni
  manejo de credenciales, OTP, captcha o teclado virtual.
- Privacidad/redaccion obligatoria: no incluir IDs de cliente, COYD,
  numeros de cuenta, nombres, screenshots, paths personales, credenciales,
  OTP, captcha, teclado virtual, cookies, tokens ni datos de sesion.
- GMF: fuera de alcance. Evidencia manual indica redirect/unavailable hacia
  `mensajes.aspx?id=000-01`; no es un flujo de certificado soportado.

---

## Anti-deteccion (Playwright)

El script usa Chrome real (no Chromium) con perfil persistente y un
`add_init_script` que oculta los flags tipicos de automatizacion
(`navigator.webdriver`, etc.). Esto es necesario porque reCAPTCHA bloquea
Chromium controlado de forma muy agresiva.

**Esto no evade el reCAPTCHA**: el reCAPTCHA lo resuelve el humano durante
el login manual. Lo unico que hace el `init_script` es evitar que Chromium
sea detectado como bot por scripts antifraude del propio sitio.

---

## Cuando el sitio cambie

1. Reproducir el flujo manualmente en un navegador limpio.
2. Inspeccionar los IDs ASP.NET con devtools.
3. Capturar las URLs de cada postback.
4. Actualizar `tipos.py` y `pagina.py` con los nuevos IDs/URLs.
5. Actualizar este documento.
6. Agregar / ajustar tests.
