# Guía de resolución de problemas en auditorías Web y SPAs

Esta guía reúne soluciones a los problemas más comunes al auditar Single-Page Applications (`React`, `Angular`, `Vue`) con **NVDA Audit** sobre Google Chrome.

---

## 1. Los servicios de traducción o API responden `404` al iniciar la sesión

- **Síntoma**: la pantalla de login queda en estado *skeleton* y las llamadas a servicios de internacionalización fallan en modo headless.
- **Causa**: algunos gateways validan de forma estricta la cabecera `Accept-Language` enviada por `fetch` (por ejemplo esperando `en_US` o `es_ES`) y rechazan cabeceras compuestas con pesos de calidad (`en-US,en;q=0.9`) si se sobreescriben globalmente con `setExtraHTTPHeaders`.
- **Solución**: **NVDA Audit** configura el idioma mediante el flag nativo de lanzamiento de Chromium (`--lang=<locale>`), permitiendo que el cliente HTTP de la aplicación envíe su cabecera `Accept-Language` en el formato exacto que espera su backend.

---

## 2. Al abrir un drawer o modal (`[role="dialog"]`), el barrido lee la página de fondo

- **Síntoma**: después de hacer clic en un botón que abre un drawer lateral o un modal, el reporte captura los elementos de `<main>` en lugar del contenido del diálogo.
- **Causa**: en librerías de componentes basadas en portales (`React Portal`), el contenedor `[role="dialog"]` se monta al final de `<body>`, fuera de la etiqueta `<main>`.
- **Solución**: desde la versión `v0.2.0`, `COLLECT_NVDA_ITEMS_JS` detecta automáticamente cualquier `[role="dialog"]` visible (`width > 50` y `height > 50`) y cambia el ámbito de recorrido al diálogo activo, tal como hace NVDA cuando un diálogo tiene `aria-modal="true"`. Asegúrate de dar un `wait_sec` de al menos `1.5` a `2.0` segundos tras el `click_text` que abre el drawer para permitir que termine su animación de entrada.

---

## 3. El valor escrito en un `<input>` se concatena con el de la vista anterior (`100` -> `100100`)

- **Síntoma**: al auditar varias vistas consecutivas que comparten la misma ruta SPA (por ejemplo Paso 1, Paso 2 y Paso 3 de un formulario), el store en memoria (`MobX` / `Redux` / `Zustand`) conserva el valor escrito en la vista previa.
- **Solución**: usa siempre la acción declarativa `type_selector` en `cdp_steps`. Desde `v0.3.0`, `type_selector` selecciona todo el contenido previo, invoca el setter nativo de `HTMLInputElement.prototype.value` y despacha el evento `input` antes de escribir el nuevo valor.

---

## 4. Peticiones interceptadas con `network_overrides` son bloqueadas por CORS

- **Síntoma**: la consola de Chrome muestra `has been blocked by CORS policy` cuando el frontend vive en `https://app.example.com` y las llamadas API van a `https://api.example.com`.
- **Solución**: al tratarse de orígenes cruzados con cabeceras personalizadas (`Authorization`, `Content-Type`), el navegador envía primero una petición preflight `OPTIONS`. `nvda_audit` (`v0.3.0`) responde automáticamente a las peticiones `OPTIONS` de cualquier ruta incluida en `network_overrides` con estado `204` y las cabeceras `Access-Control-Allow-Origin` y `Access-Control-Allow-Credentials: true`.
