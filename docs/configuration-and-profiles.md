# Configuración, flujos multi-paso y perfiles

**NVDA Audit** funciona sobre cualquier URL pública sin configuración previa (`--url https://...`), y permite definir perfiles locales en `profiles/<nombre>.local.json` (ignorados por `.gitignore`) para automatizar inicios de sesión, navegar flujos multi-paso, abrir drawers y modales, interceptar peticiones HTTP (`network_overrides`) y cruzar resultados con tickets de Jira.

---

## 1. Estructura de un perfil (`profiles/<app>.local.json`)

```json
{
  "locale": "en-US",
  "viewport_width": 1440,
  "viewport_height": 900,
  "headless": true,
  "login_url": "https://app.staging.example.com/login",
  "target_url": "https://app.staging.example.com/dashboard",
  "auth": {
    "doc_type": "Email",
    "username": "qa.user@example.com",
    "password": "<TU_PASSWORD_LOCAL>",
    "entry_quick_action": "Investments"
  },
  "i18n_db_name": "APP_I18N_DB",
  "jira_base_url": "https://org.atlassian.net",
  "jira_bugs": [
    {
      "key": "PROJ-101",
      "epic": "PROJ-10",
      "rule_id": "NVDA-NAME-001",
      "fix_type": "UI Component Library (Tooltip)",
      "summary": "Tooltip trigger button lacks aria-label on button element",
      "views": "Step 1 & Step 2 Review"
    }
  ],
  "network_overrides": {
    "/api/v1/accounts": [
      {
        "id": "ACC-01",
        "name": "Main Account",
        "balance": { "currency": "EUR", "value": 25000.0 }
      }
    ]
  },
  "views": {
    "01_step1_drawer": {
      "title": "Checkout - 1. Account Selector Drawer",
      "short_title": "1. Account Drawer",
      "scope_tag": "Account Drawer",
      "steps": 45,
      "out": "reportes/mi_app/01_step1_drawer",
      "cdp_steps": [
        { "spa_path": "/checkout/buy", "wait_sec": 4.0 },
        { "click_text": "Select account", "wait_sec": 2.0 }
      ]
    },
    "02_step2_review": {
      "title": "Checkout - 2. Review and Verify Details",
      "short_title": "2. Step 2 Review",
      "scope_tag": "Step 2 Review",
      "steps": 55,
      "out": "reportes/mi_app/02_step2_review",
      "cdp_steps": [
        { "spa_path": "/checkout/buy", "wait_sec": 3.5 },
        { "click_text": "Select account", "wait_sec": 1.5 },
        { "click_selector": "[role=\"dialog\"] [data-testid=\"selector-row\"]", "wait_sec": 0.8 },
        { "click_text": "Select", "wait_sec": 1.2 },
        { "type_selector": "input[name=\"amount\"]", "text": "100", "wait_sec": 1.0 },
        { "click_text": "Next", "wait_sec": 2.5 }
      ]
    }
  }
}
```

---

## 2. Acciones soportadas en `cdp_steps`

Cada vista dentro de `"views"` puede definir una lista ordenada de pasos `cdp_steps` que se ejecutan antes de iniciar el barrido de NVDA:

| Acción | Ejemplo | Comportamiento |
|---|---|---|
| `spa_path` | `{"spa_path": "/checkout/buy", "wait_sec": 3.5}` | Cierra cualquier diálogo abierto del paso anterior, navega dentro de la SPA mediante `history.pushState` + evento `popstate` sin perder la sesión en memoria y aguarda a que se monte el `<h1>` de la vista. |
| `click_text` | `{"click_text": "Change order", "wait_sec": 1.8}` | Busca en el diálogo activo (si hay uno abierto) o en `<main>` un enlace, botón, pestaña o fila cuyo texto visible o `aria-label` coincida y ejecuta `.click()`. Si el botón es de transición de paso (`Next`, `Confirm`, `Back`), verifica además si el foco se trasladó al inicio de la nueva vista. |
| `click_selector` | `{"click_selector": "[role=\"dialog\"] button.primary", "wait_sec": 1.0}` | Ejecuta `.click()` sobre el primer elemento que coincida con el selector CSS. |
| `type_selector` | `{"type_selector": "input#amount", "text": "100", "wait_sec": 1.0}` | Limpia cualquier valor previo del `<input>` (evitando concatenaciones entre vistas consecutivas de una misma SPA) y escribe el texto carácter por carácter. |
| `eval` | `{"eval": "window.scrollTo(0, 0)", "wait_sec": 0.5}` | Evalúa una expresión JavaScript arbitraria en el contexto de la página. |

---

## 3. Uso de `network_overrides` para desbloquear flujos en entornos de prueba

En entornos de QA o Staging es frecuente que un usuario de prueba no tenga cuentas asociadas para un producto específico (`204 No Content`) o que un servicio intermedio de simulación devuelva error `400`/`500`, impidiendo llegar al Paso 2 (Revisión) o Paso 3 (Confirmación).

Al declarar entradas en `"network_overrides"`:
- `nvda_audit` activa `page.setRequestInterception(true)` en Chrome CDP.
- Cuando la URL de una petición contiene la clave configurada:
  - Si el método es `OPTIONS` (preflight CORS), responde automáticamente `204 No Content` con las cabeceras `Access-Control-Allow-Origin`, `Access-Control-Allow-Methods`, `Access-Control-Allow-Headers` y `Access-Control-Allow-Credentials: true`.
  - Si es `GET` o `POST`, responde `200 OK` con `Content-Type: application/json` y el cuerpo configurado en el perfil, permitiendo auditar todas las pantallas del flujo de punta a punta.
