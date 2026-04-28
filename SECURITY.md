# Politica de seguridad

## Versiones soportadas

Solo la **rama `main`** y la ultima release publicada reciben actualizaciones de
seguridad. Los tags anteriores (incluso `v0.x`) **no** se parchean
retroactivamente.

| Version | Soporte de seguridad |
|---|---|
| `main` (HEAD) | ✅ |
| Ultima release etiquetada | ✅ |
| Releases anteriores | ❌ |

## Reportar una vulnerabilidad

> **No abrir un issue publico ni un PR para reportar una vulnerabilidad.**
> Eso expone el problema antes de que exista un fix.

Si se encuentra:

- Una vulnerabilidad que pueda **exponer credenciales** del usuario (cookies
  de sesion, configuracion local, perfil de Chrome).
- Un vector que permita **escalar privilegios** o ejecutar codigo arbitrario
  via input del portal.
- Cualquier comportamiento del cliente que **filtre datos personales** a
  terceros (telemetria oculta, paths inseguros, race conditions en escritura
  de archivos sensibles).
- Un cambio del portal que **rompa silenciosamente** la verificacion
  post-descarga (PDFs invalidos pasando como validos).

**Procedimiento:**

1. Enviar un **GitHub private vulnerability report**:
   <https://github.com/jparradog/suvalor/security/advisories/new>
2. Si por alguna razon no es posible usar advisories, contactar
   directamente a `@jparradog` por GitHub (DM) o por el email asociado a
   su perfil.

Incluir en el reporte:

- Descripcion del problema y por que se considera una vulnerabilidad.
- Pasos para reproducir (lo mas reducidos posible — idealmente con
  `--smoke-test --max-docs 1`).
- Impacto estimado.
- Parche propuesto, si se tiene uno.
- **No incluir datos personales reales** (numeros de cliente, COYDs,
  numeros de cuenta, nombres). Si se necesita mostrar estructura, usar
  placeholders (`<CLIENTE_ID>`, `<NUMERO_DOC>`).

## Tiempo de respuesta

- **Acuse de recibo**: dentro de 72 horas.
- **Evaluacion inicial**: dentro de 7 dias.
- **Fix + advisory**: depende de la severidad. Las criticas se priorizan.

## Que NO es una vulnerabilidad de este proyecto

- **Bugs del portal del banco.** Si el portal cambia y rompe el cliente,
  eso es un bug que se atiende por issue normal — no es una
  vulnerabilidad.
- **El portal bloquea la cuenta del usuario por usar el cliente.** Eso es
  un riesgo documentado en [`DISCLAIMER.md`](DISCLAIMER.md). No es una
  vulnerabilidad; es la realidad del scraping no autorizado.
- **El reCAPTCHA no se puede automatizar.** Eso es **intencional**. No
  se aceptan bypasses.

## Disclosure responsable

Una vez aplicado el fix, se publica un GitHub Security Advisory con:

- CVE id (si aplica).
- Versiones afectadas.
- Workaround temporal y version con el fix.
- Credito al reportador (salvo que solicite anonimato).

Gracias por contribuir a mantener este proyecto seguro.
