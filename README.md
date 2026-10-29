# NVDA Audit (`v0.4.0`)

Herramienta de auditoría lineal de accesibilidad para **Web Desktop con NVDA y Google Chrome** mediante **Chrome DevTools Protocol (CDP)**. Permite auditar aplicaciones web tradicionales y Single-Page Applications (`React`, `Angular`, `Vue`, `Web Components`) reproduciendo el recorrido del cursor virtual de NVDA (*Browse Mode*) y del foco de teclado (*Focus Mode*).

Automatiza el recorrido lineal paso a paso sobre cada vista, modal o drawer, dibuja en vivo el anillo de foco y la barra inferior **NVDA Speech Viewer** en cada captura, inspecciona el árbol DOM / ARIA e `IndexedDB`, evalúa **16 reglas de accesibilidad (`NVDA-*`) mapeadas a los 86 criterios oficiales de WCAG 2.2 (A / AA / AAA)** y genera reportes ejecutivos interactivos (`report.html` + `steps.json` + portada maestra `index.html` + comparador tripartito **Web NVDA vs Android TalkBack vs iOS VoiceOver**).

---

## Características principales

- **Agnóstico de framework y arquitectura web**: funciona sobre cualquier sitio web o aplicación SPA (`React`, `Angular`, `Vue`, `Svelte`, `Shadow DOM`) sin requerir instrumentación en el código fuente.
- **Doble modo de navegación de NVDA (`--mode {browse,tab,both}`)**:
  - **Modo `browse` (cursor virtual `↓`)**: recorre en orden documental encabezados (`heading level 1..6`), enlaces (`link`), botones (`button` / `button unavailable` / `expanded` / `collapsed`), pestañas (`tab selected M of N`), campos de texto (`edit`), botones de radio (`radio button checked/not checked M of N`), casillas (`check box`), imágenes (`graphic`), términos (`term`) y regiones vivas (`status`).
  - **Modo `tab` (*Focus Mode*)**: avanza con la tecla `Tab` capturando `document.activeElement` en cada parada para detectar trampas de teclado, elementos interactivos sin `tabindex` y órdenes de tabulación invertidos.
- **Auditoría de flujos multi-paso, drawers y diálogos (`cdp_steps` y `--test-modals`)**:
  - Ejecuta pasos declarativos (`spa_path`, `click_text`, `click_selector`, `type_selector`) para recorrer embudos completos (Paso 1 -> Drawers -> Paso 2 Revisión -> Modales -> Paso 3 Confirmación).
  - Cuando se abre un diálogo modal (`[role="dialog"]`), restringe automáticamente el ámbito del cursor virtual al interior del diálogo y verifica el retorno del foco (*Focus Return*) al cerrarlo y el traslado del foco al inicio de cada nueva vista en transiciones SPA (`NVDA-FOCUS-002`).
- **Inspector profundo de DOM, W3C ACCNAME 1.2 e internacionalización (`nvda_audit/cdp.py`)**:
  - Extrae selectores HTML, atributos ARIA, cálculo de nombre accesible según **W3C ACCNAME 1.2** (detectando `aria-label` anidados en `<span>` sin `role`, `<input>` huérfanos que caen en `placeholder` y `role="combobox"` que omiten el valor seleccionado) y clasifica de forma agnóstica la capa de origen de cada nodo (`Origen: Diccionario i18n`, `Origen: Componente de Librería UI (Design System)` u `Origen: Código Front-End de la Vista`).
- **Interceptación declarativa de red (`network_overrides`)**:
  - Permite definir mocks HTTP locales en `profiles/*.local.json` (incluyendo manejo automático de preflights `OPTIONS` CORS) para auditar pasos posteriores de un flujo aunque algún servicio de entorno de pruebas no esté disponible.
- **Comparador tripartito multiplataforma (`--compare`)**:
  - Cruza automáticamente los resultados de **Web Desktop NVDA (Google Chrome)** contra **Android TalkBack (WebView)** e **iOS VoiceOver (WKWebView)** en una matriz lado a lado con miniaturas sincronizadas.

---

## Requisitos

- **macOS, Linux o Windows** con **Google Chrome** instalado.
- **Python 3.9+** (usa únicamente la biblioteca estándar de Python; cero dependencias `pip` externas).
- **Node.js 18+** con `puppeteer` o `puppeteer-core` disponible para la conexión Chrome CDP.

---

## Instalación y uso rápido

```bash
# 1. Clonar el repositorio y entrar al directorio
git clone https://github.com/ingelectronicadj/nvda-a11y-auditor.git
cd nvda-a11y-auditor

# 2. Verificar versión y ejecutar el autodiagnóstico interno
python3 nvda_audit.py --version
python3 nvda_audit.py --self-test

# 3. Crear un perfil local a partir de la plantilla
mkdir -p profiles
cp config.example.json profiles/mi_app.local.json
```

### Auditar una aplicación web o comparar entre plataformas

```bash
# Opción A: Auditar una URL directa con el cursor virtual de NVDA
python3 nvda_audit.py --url https://example.com --view-title "Home - Mi Web" --out reportes/mi_web/01_home

# Opción B: Ejecutar todas las vistas multi-paso definidas en un perfil y generar paquete .zip
python3 nvda_audit.py --profile mi_app --view all --pack reportes/mi_app/reportes_nvda_mi_app.zip

# Opción C: Auditar abriendo e inspeccionando automáticamente modales y drawers
python3 nvda_audit.py --profile mi_app --view all --test-modals

# Opción D: Regenerar el reporte HTML de una corrida previa sin volver a abrir el navegador
python3 nvda_audit.py --profile mi_app --rebuild reportes/mi_app/01_home

# Opción E: Generar comparativa tripartita (Web Desktop NVDA vs Android TalkBack vs iOS VoiceOver)
python3 nvda_audit.py --compare reportes/mi_app ../talkback_audit/reportes/mi_app
```

---

## Opciones de línea de comandos (CLI)

| Opción | Descripción | Valor por defecto |
|---|---|---|
| `--version` | Muestra la versión instalada y termina | - |
| `--self-test` | Valida los 86 criterios WCAG 2.2, las 16 reglas `NVDA-*` y el generador HTML | - |
| `--profile NAME`, `-p` | Carga el perfil `profiles/<NAME>.local.json` | Auto |
| `--config FILE` | Ruta a un archivo JSON de configuración personalizada | `profiles/*.local.json` |
| `--url URL` | URL directa a auditar cuando no se usa el mapa `views` del perfil | `target_url` del perfil |
| `--locale BCP47` | Idioma esperado de la interfaz y del navegador (ej. `en-US`, `es-ES`, `es-AR`) | `en-US` |
| `--view VIEW_ID` | Ejecuta una vista declarativa del perfil o `all` para correr todas en secuencia | `all` |
| `--view-title TITLE` | Título descriptivo de la vista para el reporte HTML | Auto (`<h1>`) |
| `--steps N` | Número máximo de avances del cursor virtual de NVDA por vista | `75` |
| `--mode {browse,tab,both}` | Modo de barrido: `browse` (cursor virtual `↓`), `tab` (tecla `Tab`) o `both` | `browse` |
| `--test-modals` | Abre y audita automáticamente diálogos/drawers (`[role="dialog"]`) y valida `Focus Return` | `False` |
| `--headed` | Ejecuta Google Chrome con ventana visible en lugar de modo headless | `False` |
| `--out DIR` | Carpeta de salida cuando se audita una vista individual | `reportes/nvda_run` |
| `--pack [ZIP_FILE]` | Genera portada maestra `index.html` y empaqueta la suite en un archivo `.zip` autocontenido | - |
| `--rebuild DIR` | Reconstruye `report.html` desde `steps.json` y `DIR/img/` | - |
| `--compare DIR_A DIR_B` | Genera matriz comparativa multiplataforma entre carpetas de reportes | - |

---

## Arquitectura del proyecto

```text
.
├── nvda_audit.py              # Entrypoint CLI, orquestador de vistas y modo --self-test
├── config.example.json        # Plantilla de configuración (copiar a profiles/<app>.local.json)
├── profiles/                  # Perfiles locales por aplicación/entorno (*.local.json ignorados en git)
├── reportes/                  # Reportes HTML, capturas y paquetes .zip (ignorados en git)
├── CHANGELOG.md               # Historial de cambios por versión
├── nvda_audit/
│   ├── __init__.py            # Versión del paquete (VERSION = "0.4.0")
│   ├── config.py              # Carga de configuración jerárquica y resolución de perfiles
│   ├── web_client.py          # Motor Chrome CDP, Buffer Virtual NVDA, Speech Viewer y network_overrides
│   ├── cdp.py                 # Extractor DOM / ARIA, W3C ACCNAME 1.2, IndexedDB i18n y capa de origen
│   ├── wcag_catalog.py        # Taxonomía oficial WCAG 2.2 (86 criterios) y catálogo de 16 reglas NVDA-*
│   ├── rules.py               # Motor de heurísticas por nodo, texto, secuencia, formularios y encabezados
│   ├── report.py              # Generador de steps.json, reporte HTML interactivo e índice/ZIP de suite
│   └── compare.py             # Comparador tripartito (Web NVDA vs Android TalkBack vs iOS VoiceOver)
└── docs/
    ├── architecture.md                # Arquitectura interna del Buffer Virtual NVDA y Chrome CDP
    ├── wcag-rules-catalog.md          # Catálogo detallado de las 16 reglas NVDA-* y criterios WCAG 2.2
    ├── configuration-and-profiles.md  # Configuración de vistas multi-paso, login SPA y network_overrides
    └── troubleshooting-nvda-web.md    # Guía de resolución de problemas en auditorías Web y SPAs
```

---

## Documentación adicional (`docs/`)

1. **[Arquitectura y funcionamiento interno](docs/architecture.md)**: cómo emula `web_client.py` el Buffer Virtual de NVDA (*Browse Mode*) sobre Chromium, cómo gestiona el ámbito de diálogos `aria-modal="true"` y cómo clasifica el origen de cada hallazgo.
2. **[Catálogo de reglas `NVDA-*` y taxonomía WCAG 2.2](docs/wcag-rules-catalog.md)**: detalle de las 16 reglas automatizadas (`NVDA-SKEL-001` a `NVDA-LANG-001`), heurísticas de formularios/tooltips y ejemplos de remediación HTML / React / ARIA.
3. **[Configuración, flujos multi-paso y perfiles](docs/configuration-and-profiles.md)**: cómo definir `cdp_steps` para navegar embudos multi-paso, interceptar respuestas HTTP con `network_overrides`, auditar `IndexedDB` y vincular tickets de Jira.
4. **[Guía de resolución de problemas en Web y SPAs](docs/troubleshooting-nvda-web.md)**: manejo de cabeceras `Accept-Language`, preflights CORS en mocks, tiempos de hidratación de microfrontends y aislamiento de estado entre vistas.
