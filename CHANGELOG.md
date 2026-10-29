# Changelog - NVDA Audit

Todos los cambios relevantes de este proyecto se documentan en este archivo siguiendo el formato Keep a Changelog y Semantic Versioning.

## [0.4.0] - 2026-10-29

### Añadido
- **Recorrido real de teclado `--mode {tab,both}` (`nvda_audit/web_client.py`)**:
  - Ejecuta pulsaciones reales de `Tab` y registra la secuencia de `document.activeElement` en `domSnapshot.tabStops`.
- **Generador desplegable de plantilla de bug A11Y de 6 secciones en `report.html` y limpieza de atributos efímeros (`data-nvda-step-idx`, `name="_r_N_"`) en snippets DOM (`nvda_audit/report.py`)**.

## [0.3.0] - 2026-10-28

### Añadido
- **Detección de `<input>` huérfanos que exponen únicamente su `placeholder` (`inputPlaceholderOnly` - WCAG 1.3.1 / 3.3.2)**:
  - Identifica campos `<input>` sin `<label for>`, `aria-label` ni `aria-labelledby` cuyo nombre accesible recae en una máscara de formato o placeholder (por ejemplo `MM/DD/YYYY`, `DD/MM/YYYY`, `0,0000`).
- **Detección de selectores `role="combobox"` cuyo `aria-labelledby` omite el valor seleccionado (`comboboxMissingValue` - WCAG 4.1.2)**:
  - Alerta cuando un control `role="combobox"` muestra en pantalla una opción seleccionada que no forma parte de su nombre accesible calculado.
- **Detección de ilustraciones decorativas con `alt` genérico y `aria-hidden="false"` en banners informativos o de error (WCAG 1.1.1)**:
  - Detecta paradas redundantes como `Informative message graphic` o `Error graphic` dentro de contenedores de aviso.
- **Verificación automática de orden de foco en transiciones entre pasos SPA (`spaFocusIssue` - WCAG 2.4.3)**:
  - Al avanzar o retroceder de paso mediante `click_text` (`Next`, `Confirm`, `Back`, `Continue`), comprueba si `document.activeElement` permaneció en el botón inferior en lugar de trasladarse al inicio de la nueva vista.
- **Aislamiento de estado de inputs en flujos multi-paso y reintento automático de carga inicial (`nvda_audit/web_client.py`)**:
  - Limpia el valor previo de los campos `<input>` antes de ejecutar `type_selector` y añade soporte de `click_selector` e inspección automática de diálogos abiertos (`[role="dialog"]`).

### Corregido
- **Escapado de expresiones regulares dentro del template literal `COLLECT_NVDA_ITEMS_JS` (`nvda_audit/web_client.py`)**:
  - Se corrigió el escape de `/\\s+/g` y `/\\u200b/g` para preservar intactos todos los caracteres al normalizar espacios en blanco.
- **Manejo completo de preflights CORS `OPTIONS` en `network_overrides` (`nvda_audit/web_client.py`)**:
  - Responde automáticamente con `204 No Content` y cabeceras `Access-Control-Allow-*` en peticiones `OPTIONS` asociadas a rutas interceptadas.

## [0.2.0] - 2026-10-28

### Añadido
- **Modos de navegación `--mode {browse,tab,both}` e inspección profunda de diálogos `--test-modals` (`nvda_audit.py`, `nvda_audit/web_client.py`)**:
  - Permite alternar entre el cursor virtual de NVDA (`browse`) y navegación por teclado (`tab`), y audita automáticamente el contenido de modales y drawers (`[role="dialog"]`).
- **Mocks / overrides declarativos de red (`network_overrides`) y espera automática de fin de skeletons (`nvda_audit/web_client.py`)**:
  - Permite interceptar y simular respuestas HTTP desde `profiles/*.local.json` y aguarda a que desaparezcan los indicadores `[aria-busy="true"]` o `skeleton` antes de capturar el árbol accesible.
- **Reglas W3C ACCNAME 1.2 para `aria-label` anidado en `<span>` sin `role`, detector de sufijos duplicados en `aria-label`, clasificador agnóstico de capa de origen y comparador tripartito multiplataforma (`Web Desktop NVDA` vs `Android TalkBack` vs `iOS VoiceOver`)**.

## [0.1.0] - 2026-10-28

### Añadido
- **Motor de Buffer Virtual NVDA (Browse Mode y Focus Mode) sobre Chrome CDP (`nvda_audit/web_client.py`)**:
  - Recorrido lineal en orden documental sobre el árbol accesible de Chromium con formato de salida idéntico a **NVDA Speech Viewer** (`heading level 1..6`, `button`, `button unavailable`, `link`, `tab selected M of N`, `edit`, `radio button not checked M of N`, `check box`, `graphic`, `term`, `status`).
  - Renderizado en vivo del anillo de foco y barra inferior **NVDA Speech Viewer** en cada captura `step_NNN.png`.
- **Soporte declarativo de autenticación pre-auditoría, navegación SPA (`history.pushState`) y preservación de sesión en aplicaciones web**.
- **Catálogo de 16 reglas `NVDA-*` sobre los 86 criterios oficiales WCAG 2.2 y empaquetador de suites HTML + `.zip` (`--pack`)**.
