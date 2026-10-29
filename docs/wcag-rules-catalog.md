# Catálogo de reglas `NVDA-*` y taxonomía WCAG 2.2

**NVDA Audit** incluye los **86 criterios oficiales de conformidad de WCAG 2.2 (Niveles A, AA y AAA)** en `nvda_audit/wcag_catalog.py` y evalúa automáticamente **16 reglas especializadas (`NVDA-*`)** más heurísticas de cálculo de nombre accesible (**W3C ACCNAME 1.2**) en `nvda_audit/rules.py` y `nvda_audit/report.py`.

---

## Resumen de las 16 reglas automatizadas (`NVDA-*`)

| ID regla | Criterio WCAG 2.2 | Nivel | Severidad | Qué detecta |
|---|---|---|---|---|
| `NVDA-I18N-001` | `3.1.2` Idioma de las partes / `2.4.6` | AA | Alta | Keys de traducción crudas sin resolver (`a11y_*`, `i18n_*`), textos en idioma distinto al `locale` de la vista, placeholders sin interpolar (`{variable}`) o erratas ortográficas que alteran la pronunciación TTS. |
| `NVDA-LINK-001` | `2.4.4` Propósito de los enlaces | A | Alta | Enlaces vacíos o genéricos (`(empty link)`, `More info` sin contexto) o que duplican su etiqueta por autorreferencia en `aria-labelledby`. |
| `NVDA-SKEL-001` | `4.1.3` Mensajes de estado / `2.4.3` | AA | Alta | Vistas o drawers en carga con *skeletons* sin anuncio `aria-live`, o regiones `<span role="status">\u200b</span>` que permanecen en el DOM con espacios de ancho cero tras finalizar la carga. |
| `NVDA-CHART-001` | `2.4.1` Evitar bloques | A | Alta | Gráficas `<svg>` cuyos puntos individuales (`<circle>`) quedan expuestos al cursor virtual o al tabulador sin mecanismo para saltar la serie de datos. |
| `NVDA-FOCUS-001` | `2.4.3` Orden del foco | A | Alta | Pérdida de retorno de foco (*Focus Return*) al cerrar modales/drawers, orden de foco invertido respecto al layout visual, o foco que no se traslada al inicio de la nueva vista tras una transición de paso en flujos SPA. |
| `NVDA-CURR-001` | `1.3.1` Información y relaciones | A | Alta | Importes monetarios o valores numéricos que omiten la divisa/unidad en su etiqueta accesible (ej. anunciar `10` sin unidad bajo `Approximate amount` o `0.0337` sin el ticker del activo). |
| `NVDA-UNREACH-001` | `1.3.1` Información y relaciones / `2.1.1` | A | Alta | Elementos interactivos o informativos visibles en el DOM que carecen de semántica o quedan fuera del recorrido del lector. |
| `NVDA-HEAD-002` | `1.3.1` Información y relaciones / `2.4.6` | A | Media | Saltos en la jerarquía de encabezados (`H1 -> H3` sin `H2`), ausencia de `H1` o encabezados ocultos que envuelven párrafos extensos (`> 120` caracteres). |
| `NVDA-NAME-001` | `4.1.2` Nombre, función, valor | A | Alta | Botones o controles sin nombre accesible (`Unlabelled button`), incluyendo botones `<button>` que anidan su `aria-label` dentro de un `<span>` hijo sin `role` (ignorado por W3C ACCNAME 1.2) y selectores `role="combobox"` cuyo `aria-labelledby` omite el valor seleccionado. |
| `NVDA-IMG-001` | `1.1.1` Contenido no textual | A | Alta | Imágenes o `<svg>` informativos sin nombre accesible (`Unlabelled graphic`) o ilustraciones decorativas de banners/alertas con `aria-hidden="false"` y `alt` genérico (`Informative message graphic`, `Error graphic`). |
| `NVDA-MERGE-001` | `1.3.2` Secuencia significativa | A | Media | Paradas duplicadas en controles compuestos (como píldoras de radio `<Pill>` o filas `<SelectorRow>` donde se lee primero el `<span>` de texto sin `aria-hidden="true"` y luego el `<input type="radio">`). |
| `NVDA-LABEL-001` | `2.5.3` Etiqueta en el nombre / `3.3.2` | A | Media | Campos `<input>` huérfanos sin `<label for>`, `aria-label` ni `aria-labelledby` que anuncian únicamente su `placeholder` de formato (`MM/DD/YYYY edit`), o controles cuyo `aria-label` contradice el texto visible. |
| `NVDA-TARGET-001` | `2.5.8` Tamaño del objetivo (mínimo) | AA | Media | Controles interactivos con área de clic inferior a `24x24 px` (o `44x44 px` en diseño adaptable). |
| `NVDA-STATUS-001` | `4.1.3` Mensajes de estado | AA | Media | Pantallas o mensajes de error (`Something went wrong`) que se renderizan dinámicamente sin `role="alert"` ni `aria-live="assertive"`. |
| `NVDA-HEAD-001` | `2.4.6` Encabezados y etiquetas | AA | Baja | Etiquetas `aria-label` que incluyen manualmente el nombre del rol (`button`, `link`) o que concatenan al final un importe/unidad duplicado que ya fue enunciado al inicio de la misma etiqueta. |
| `NVDA-LANG-001` | `3.1.2` Idioma de las partes | AA | Baja | Mezcla de cadenas en distintos idiomas sin atributo `lang` en el sub-árbol correspondiente. |

---

## Patrones de remediación en aplicaciones Web (HTML / React / Design Systems)

### 1. Botones de Tooltip (`NVDA-NAME-001` - W3C ACCNAME 1.2)
- **Problema**: un componente `<Tooltip>` envuelve un icono dentro de `<button data-testid="tooltip-trigger">` sin `aria-label`, dejando el `aria-label="Information about Order type"` en un `<span>` hijo sin `role`.
- **Remediación**:
  ```html
  <!-- Correcto: el aria-label vive en el elemento interactivo <button> -->
  <button type="button" data-testid="tooltip-trigger" aria-label="Information about Order type">
    <svg aria-hidden="true" focusable="false"></svg>
  </button>
  ```

### 2. Píldoras de selección rápida y filas de radio (`NVDA-MERGE-001`)
- **Problema**: el texto visible `<span id="pill0-content">10%</span>` no tiene `aria-hidden="true"`, por lo que el cursor virtual de NVDA se detiene primero en el `<span>` y luego en el `<input type="radio" aria-labelledby="pill0-content">`.
- **Remediación**:
  ```html
  <!-- Ocultar el span al cursor virtual; aria-labelledby sigue resolviendo el texto en el input -->
  <span id="pill0-content" aria-hidden="true">10%</span>
  <input type="radio" name="amountPreset" aria-labelledby="pill0-content" />
  ```

### 3. Campos de fecha e inputs con etiqueta visual externa (`NVDA-LABEL-001`)
- **Problema**: el texto `"Start date"` se renderiza en un `<span>` sin asociación programática con `<input id="input-date0" placeholder="MM/DD/YYYY">`.
- **Remediación**:
  ```html
  <label id="input-date0-label" for="input-date0">Start date</label>
  <input id="input-date0" type="text" placeholder="MM/DD/YYYY" aria-describedby="input-date0-help" />
  <span id="input-date0-help">Format: MM/DD/YYYY</span>
  ```

### 4. Selectores personalizados `role="combobox"` (`NVDA-NAME-001`)
- **Problema**: `<button id="freq-btn" role="combobox" aria-labelledby="freq-label"><span id="freq-val">Monthly</span></button>` anuncia solo `"Frequency button collapsed"` porque `aria-labelledby` pisa el contenido interno del botón.
- **Remediación**:
  ```html
  <label id="freq-label">Frequency</label>
  <button id="freq-btn" type="button" role="combobox" aria-expanded="false" aria-labelledby="freq-label freq-val">
    <span id="freq-val">Monthly</span>
  </button>
  ```
