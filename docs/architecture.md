# Arquitectura y funcionamiento interno

Este documento describe las decisiones técnicas de diseño de **NVDA Audit** para emular con precisión el recorrido lineal del lector de pantalla **NVDA** (*NonVisual Desktop Access*) sobre **Google Chrome** mediante **Chrome DevTools Protocol (CDP)**.

---

## 1. Modelo de navegación de NVDA en navegadores de escritorio

A diferencia de los lectores de pantalla móviles (como TalkBack o iOS VoiceOver, que operan mediante gestos de swipe sobre la pantalla táctil), **NVDA en escritorio** opera bajo dos modos complementarios sobre el árbol accesible de Chromium (`IAccessible2` / `Chrome AXTree`):

1. **Modo exploración (*Browse Mode* / Buffer Virtual)**:
   - El usuario avanza nodo por nodo en orden documental con la flecha abajo (`↓`) o salta por tipo de elemento con atajos de una letra (`H` para encabezados, `B` para botones, `K` para enlaces, `E` para campos de edición, `F` para controles de formulario, `G` para gráficos).
   - El cursor virtual visita tanto elementos interactivos como elementos estáticos semánticos (`<h1>..<h6>`, `<p>`, `<dt>`, `<dd>`, `<legend>`, `<img alt="...">`, regiones `role="status"`).
2. **Modo foco (*Focus Mode* / Tecla `Tab`)**:
   - El usuario avanza únicamente por elementos enfocables por teclado (`a[href]`, `button`, `input`, `select`, `textarea`, `[tabindex="0"]`), revelando si existen controles interactivos que carecen de soporte de teclado o si el orden de tabulación contradice el orden visual.

---

## 2. Componentes de la arquitectura

### A. Emulador de Buffer Virtual y Speech Viewer (`nvda_audit/web_client.py`)

`WebNvdaClient` lanza o conecta una instancia de **Google Chrome** vía CDP y ejecuta `COLLECT_NVDA_ITEMS_JS` sobre el contenedor activo de la vista:

- **Ámbito automático de modales (`aria-modal="true"` / `role="dialog"`)**:
  Si en la pantalla hay un diálogo o drawer abierto (`[role="dialog"]` con dimensiones visibles), el motor restringe automáticamente el ámbito del recorrido al interior del diálogo, reproduciendo el atrapamiento de cursor virtual que aplica NVDA sobre diálogos modales. Si no hay diálogo abierto, recorre `<main>` (o `<body>`).
- **Formato de salida de NVDA Speech Viewer**:
  Construye la cadena verbalizada siguiendo las convenciones de NVDA en Chrome:
  - Encabezados: `heading level <1..6> <texto>`
  - Pestañas: `<texto> tab [selected] <M> of <N>`
  - Enlaces: `<texto> link`
  - Botones: `<texto> button [unavailable] [expanded|collapsed]`
  - Campos de texto: `<etiqueta> edit [<valor>]`
  - Botones de radio: `<etiqueta> radio button <checked|not checked> <M> of <N>`
  - Casillas de verificación: `<etiqueta> check box <checked|not checked>`
  - Imágenes y SVGs: `<alt> graphic` o `Unlabelled graphic`
  - Listas de definición: `<texto> term`
  - Regiones vivas expuestas: `status`
- **Renderizado visual en vivo**:
  En cada paso `i`, desplaza el elemento al centro del viewport (`scrollIntoView`), dibuja el recuadro de foco (`#__nvda_focus_ring__`) y la barra inferior `#__nvda_speech_viewer__` con el número de paso y la frase exacta verbalizada, y captura `img/step_NNN.png`.

### B. Orquestador de flujos multi-paso y `network_overrides` (`runViewSteps`)

Para auditar flujos completos (por ejemplo: Paso 1 Formulario -> Drawer de Selección -> Paso 2 Revisión -> Modal de Detalle -> Paso 3 Confirmación) sin intervención manual:

- **`cdp_steps` declarativos**:
  Soporta navegación SPA sin recarga (`spa_path` mediante `history.pushState` + evento `popstate`), espera automática de montaje del encabezado `<h1>` del microfrontend, espera de desaparición de skeletons (`[aria-busy="true"], [data-testid*="skeleton"]`), clics por texto visible o `aria-label` (`click_text`), clics por selector CSS (`click_selector`) y escritura limpia en campos (`type_selector` con vaciado previo del valor).
- **Verificación de foco en transiciones SPA (`spaFocusIssue`)**:
  Tras cada clic de avance o retroceso entre pasos (`Next`, `Confirm`, `Back`, `Continue`), comprueba dónde quedó `document.activeElement`. Si el foco permaneció en el botón del pie de página en lugar de trasladarse al encabezado o inicio de la nueva vista, registra automáticamente una alerta `WCAG 2.4.3`.
- **Interceptación HTTP con soporte CORS (`network_overrides`)**:
  Permite definir en el perfil local respuestas JSON simuladas por patrón de URL, respondiendo automáticamente tanto a las peticiones `GET`/`POST` como a los preflights `OPTIONS` con cabeceras `Access-Control-Allow-*`.

### C. Inspector DOM, W3C ACCNAME 1.2 e `IndexedDB` (`nvda_audit/cdp.py`)

En cada vista, `DOM_EXTRACT_JS` inspecciona el DOM en vivo y extrae:

1. **Atributos ARIA y anomalías de nombre accesible (W3C ACCNAME 1.2)**:
   - Controles `<button>` o `<a>` sin `aria-label` propio que anidan un `<span aria-label="...">` o `<div aria-label="...">` sin atributo `role` (`nestedSpanAria`).
   - Campos `<input>` sin `<label for>`, `aria-label` ni `aria-labelledby` que caen únicamente en su atributo `placeholder` (`inputPlaceholderOnly`).
   - Selectores `role="combobox"` cuyo `aria-labelledby` apunta solo a la etiqueta del campo y omite el valor seleccionado (`comboboxMissingValue`).
2. **Auditoría del diccionario i18n en `IndexedDB`**:
   Localiza automáticamente almacenes de traducciones en `IndexedDB`, detecta keys vacías (`""`), placeholders sin interpolar (`{variable}`) o textos en idioma distinto al configurado, y cruza cada nodo DOM con la key exacta que lo generó.
3. **Clasificador agnóstico de capa de origen**:
   Etiqueta cada nodo con su capa de responsabilidad (`Origen: Diccionario i18n`, `Origen: Componente de Librería UI (Design System)` u `Origen: Código Front-End de la Vista`).
