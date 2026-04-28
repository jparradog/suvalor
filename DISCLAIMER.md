# Disclaimer / Aviso legal

> **TL;DR — Lea esto antes de usar el cliente.**
> Esto es software no oficial. **No estoy afiliado a Bancolombia S.A.,
> Valores Bancolombia, Cibest Capital ni Suvalor.** Lo uso bajo mi propia
> sesion autenticada para descargar **mi propia documentacion** de un portal
> al que ya tengo acceso. Si lo usa, **lo hace bajo su propio riesgo y
> responsabilidad**, y acepta todo lo que dice este documento.

---

## 1. Naturaleza del proyecto

`suvalor` es una herramienta de automatizacion **personal y no oficial** que
controla un navegador real (Google Chrome via Playwright) para automatizar la
descarga de **documentacion contable propia** desde el portal Suvalor /
Cibest Capital (Valores Bancolombia), en `suvalor.com`.

- **No** es un producto de Bancolombia S.A., de Valores Bancolombia S.A.
  Comisionista de Bolsa, ni de ninguna entidad del Grupo Bancolombia.
- **No** es un producto de Cibest Capital ni de Suvalor.
- **No** ha sido revisado, autorizado, certificado, ni respaldado por dichas
  entidades.
- Las marcas "Suvalor", "Cibest Capital", "Valores Bancolombia" y
  "Bancolombia" pertenecen a sus respectivos titulares y se mencionan aqui
  unica y exclusivamente con fines descriptivos / identificatorios
  (nominative fair use), para indicar **a que portal apunta el cliente**.

## 2. Alcance funcional

`suvalor` actua **siempre dentro de una sesion que el usuario humano abrio
manualmente con sus propias credenciales**. Especificamente:

- El cliente **no** intenta evadir el reCAPTCHA, el teclado virtual, ni
  ningun otro control de seguridad.
- El cliente **no** almacena, transmite, ni envia la contrasena, el OTP,
  el nombre de usuario, ni ningun token de autenticacion a ningun servidor
  de terceros. El proyecto no opera servidores ni telemetria.
- El login lo realiza **el usuario**, manualmente, en el navegador. El
  cliente recien toma el control **despues** de que la sesion esta
  autenticada.
- Las cookies de sesion quedan en el perfil persistente de Chrome
  (`_chrome_profile/`, en la maquina local del usuario). **Nunca abandonan
  el equipo por causa de este cliente.**

### 2.1 Sobre las medidas anti-deteccion del navegador

El paquete incluye un `add_init_script` en `suvalor/navegador.py` que ajusta
propiedades cosmeticas del navegador (entre otras: oculta el flag
`navigator.webdriver`, normaliza `plugins`, `languages` y user-agent
client hints) **para evitar que scripts antifraude del propio sitio
detecten que el navegador esta siendo controlado por Playwright**.

Estas modificaciones:

- **NO** evaden, descifran ni rompen ningun control criptografico de
  seguridad.
- **NO** evaden el reCAPTCHA (lo resuelve el usuario humano durante el
  login manual).
- **NO** rompen el teclado virtual ni capturan credenciales.
- **NO** inyectan codigo en otros origenes ni interceptan trafico.

Su unico proposito es que Chrome (con el perfil propio del usuario y sus
propias cookies de sesion) se comporte como un navegador "normal" frente
al fingerprinting del sitio. Es funcionalmente equivalente a usar una
extension comercial de browser-fingerprint-protection.

Aun asi, **legalmente** podria interpretarse como "circumvention" en
ciertas jurisdicciones bajo legislacion de delitos informaticos (en
Colombia, Ley 1273 de 2009 art. 269A). El usuario es el unico responsable
de evaluar si su uso es licito en su jurisdiccion. Ver §3 mas abajo.

## 3. Uso aceptable — responsabilidad del usuario

Antes de usar este cliente, el usuario es responsable de **leer y cumplir**:

- Los **Terminos y Condiciones** del portal Suvalor / Cibest Capital y de
  cualquier entidad del Grupo Bancolombia que aplique a su cuenta.
- Las **politicas de uso aceptable**, incluyendo (pero no limitado a)
  restricciones sobre automatizacion, scraping, robots.txt y rate limiting.
- La **legislacion aplicable** en su jurisdiccion sobre proteccion de
  datos personales, secreto bancario, fraude informatico, acceso no
  autorizado a sistemas, y similares (en Colombia, la Ley 1273 de 2009
  entre otras).

> **Si los terminos del portal prohiben la automatizacion del acceso, NO
> SE DEBE USAR ESTE CLIENTE.** Solo debe usarse si y solo si la entidad
> explicitamente lo permite, o si se ha obtenido autorizacion previa.

Es responsabilidad **exclusiva del usuario** determinar si su uso del
cliente cumple con dichos terminos. Los autores y contribuidores **no
auditan ni vigilan** el uso que terceros hacen del codigo.

## 4. Sin garantia (Apache-2.0 §7)

El software se entrega **"AS IS" — TAL CUAL ESTA**, sin garantia de ningun
tipo, ni expresa ni implicita, incluyendo pero no limitado a garantias de
comerciabilidad, idoneidad para un proposito particular, exactitud, o
no infraccion. Sin garantia de:

- Que el cliente funcione en cualquier momento dado.
- Que el portal del banco no cambie y rompa el cliente (de hecho, **es
  muy probable** que cambie y que el cliente deje de funcionar).
- Que los archivos descargados sean correctos, completos o equivalentes a
  los que ofrece el portal por canales oficiales.
- Que el cliente no tenga bugs que provoquen perdida de datos en el
  filesystem local del usuario.
- Que el uso del cliente no sea detectado, registrado o sancionado por la
  entidad operadora del portal.

## 5. Limitacion de responsabilidad (Apache-2.0 §8)

**En ningun caso** los autores, contribuidores o titulares del copyright
seran responsables ante el usuario o ante terceros por daño alguno,
directo, indirecto, incidental, especial, ejemplar o consecuente, derivado
del uso o la imposibilidad de usar este software, incluyendo (pero no
limitado a):

- **Sanciones, bloqueos, suspensiones, cierres de cuenta** o cualquier otra
  accion disciplinaria que la entidad operadora del portal aplique sobre
  la cuenta del usuario como consecuencia (directa o indirecta) del uso
  del cliente.
- **Acciones legales o regulatorias** (civiles, administrativas o penales)
  iniciadas contra el usuario por el uso del cliente.
- **Perdidas financieras** derivadas de decisiones tomadas a partir de la
  informacion obtenida con el cliente.
- **Perdida o corrupcion** de archivos locales del usuario (PDFs, XLS,
  JSON de estado).
- **Brechas de seguridad** en el equipo del usuario derivadas de tener un
  perfil persistente de Chrome con cookies de sesion bancaria activa.
- **Filtracion accidental** de datos personales si el usuario sube a un
  repositorio publico archivos generados por el cliente (de ahi el
  `.gitignore` exhaustivo y esta advertencia).

Si el usuario no acepta esta limitacion de responsabilidad **en su
totalidad**, **no debe usar el cliente**.

## 6. Datos personales y financieros

Este repositorio (codigo fuente) **no contiene** ni esta diseñado para
contener datos personales o financieros del usuario. El cliente genera
todos los archivos sensibles en `SUVALOR_HOME` (o cwd), una carpeta que
elige el usuario y que es **independiente del repositorio del codigo**.

**Nunca** se debe hacer commit de:

- Inventarios JSON (`_state/`)
- Perfiles de Chrome (`_chrome_profile/`) — contienen cookies de sesion
  bancaria activa.
- Archivos descargados (`*.pdf`, `*.xls`, carpetas de año, `Extractos/`,
  `Cartera/`).
- Archivos de configuracion con datos personales (`config.toml`).
- Logs (`run.log`, `_LOG.md`).

El `.gitignore` del proyecto cubre todos estos patrones, pero **la
responsabilidad final de no filtrar datos sigue siendo del usuario**.

## 7. Marcas registradas

"Suvalor", "Cibest Capital", "Valores Bancolombia", "Bancolombia" y los
logos asociados son marcas registradas de sus respectivos titulares. Su
mencion en este proyecto es exclusivamente nominativa (para identificar a
que portal apunta el cliente) y **no implica afiliacion, endoso, patrocinio,
ni asociacion alguna**.

## 8. Cambios en este documento

Los terminos de este disclaimer pueden actualizarse en futuras versiones
del proyecto. La version vigente es siempre la incluida en el commit que
se este utilizando.

---

**Al clonar, instalar, ejecutar o redistribuir este software, el usuario
acepta en su totalidad los terminos de este DISCLAIMER y de la Apache
License 2.0 incluida en el archivo LICENSE.**

Si tiene dudas legales, consulte a un profesional de derecho informatico
o financiero **antes de usar el cliente**, no despues.
