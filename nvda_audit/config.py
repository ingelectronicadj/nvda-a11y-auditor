"""Configuración centralizada para auditoría Web con NVDA (profiles/*.local.json / --profile / --config)."""

import json
import os

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROFILES_DIR = os.path.join(SCRIPT_DIR, "profiles")
LOCAL_CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.local.json")

ROLE_MAP = {
    "button": "Botón",
    "link": "Enlace",
    "heading": "Encabezado",
    "textbox": "Campo de edición",
    "radio": "Botón de opción",
    "checkbox": "Casilla de verificación",
    "tab": "Pestaña",
    "tablist": "Lista de pestañas",
    "img": "Gráfico / Imagen",
    "image": "Gráfico / Imagen",
    "status": "Región de estado",
    "term": "Término",
    "StaticText": "Texto",
}

INTERESTING_CLS = ("Button", "Link", "Heading", "Edit", "RadioButton", "CheckBox", "Tab", "Graphic", "Status", "Term")
SKIP_CLS = ("ViewGroup", "Container")

CURRENCY_NOTES = {
    "$": "el símbolo $ sin desambiguar se anuncia como 'dólares' en síntesis TTS en español aunque represente pesos u otra moneda local",
    "€": "el símbolo € se anuncia como 'euros'",
    "£": "el símbolo £ se anuncia como 'libras'",
}

DEFAULT_CONFIG = {
    "browser": "Chrome CDP (NVDA Browse Mode)",
    "locale": os.environ.get("NVDA_LOCALE", "en-US"),
    "viewport_width": 1440,
    "viewport_height": 900,
    "headless": True,
    "login_url": os.environ.get("NVDA_LOGIN_URL", ""),
    "target_url": os.environ.get("NVDA_TARGET_URL", ""),
    "scope_selector": "main",
    "auth": {
        "doc_type": "Email",
        "username": os.environ.get("NVDA_USER", ""),
        "password": os.environ.get("NVDA_PASSWORD", ""),
        "entry_quick_action": "Crypto",
    },
    "i18n_db_name": os.environ.get("NVDA_I18N_DB", ""),
    "jira_base_url": os.environ.get("NVDA_JIRA_BASE_URL", ""),
    "jira_bugs": [],
    "views": {},
}


def _deep_merge(base, override):
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base


def resolve_profile_path(profile_or_path=None):
    if profile_or_path:
        if os.path.exists(profile_or_path):
            return profile_or_path
        cand1 = os.path.join(PROFILES_DIR, "%s.local.json" % profile_or_path)
        if os.path.exists(cand1):
            return cand1
        cand2 = os.path.join(PROFILES_DIR, "%s.json" % profile_or_path)
        if os.path.exists(cand2):
            return cand2
        return profile_or_path
    if os.path.exists(LOCAL_CONFIG_PATH):
        return LOCAL_CONFIG_PATH
    if os.path.isdir(PROFILES_DIR):
        locals_found = sorted(
            os.path.join(PROFILES_DIR, fn)
            for fn in os.listdir(PROFILES_DIR)
            if fn.endswith(".local.json")
        )
        if locals_found:
            return locals_found[0]
    return None


def load_config(config_path=None, user_id=None, password=None, target_url=None, profile=None):
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    target_cfg = resolve_profile_path(profile or config_path)
    if target_cfg and os.path.exists(target_cfg):
        try:
            with open(target_cfg, "r", encoding="utf-8") as f:
                _deep_merge(cfg, json.load(f))
        except Exception:
            pass
    if user_id:
        cfg.setdefault("auth", {})["username"] = str(user_id).strip()
    if password:
        cfg.setdefault("auth", {})["password"] = str(password).strip()
    if target_url:
        cfg["target_url"] = str(target_url).strip()
    return cfg


def role_of(cls):
    short = (cls or "").split(".")[-1]
    for k, v in ROLE_MAP.items():
        if k.lower() == short.lower() or k.lower() in short.lower():
            return v
    return short or "Elemento"
