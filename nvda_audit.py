#!/usr/bin/env python3
"""
nvda_audit.py - CLI principal de auditoría lineal de accesibilidad Web con NVDA y Chrome CDP.

Arquitectura modular en nvda_audit/:
  - nvda_audit.config       : configuración centralizada (perfiles JSON / CLI)
  - nvda_audit.web_client   : motor Chrome CDP + NVDA Browse Mode (Virtual Buffer) y Speech Viewer visual
  - nvda_audit.cdp          : inspector DOM / ARIA e IndexedDB en memoria
  - nvda_audit.wcag_catalog : taxonomía oficial WCAG 2.2 (86 criterios) y catálogo de 16 reglas NVDA-*
  - nvda_audit.rules        : motor de heurísticas sobre nodos, textos, skeletons, encabezados y omitidos
  - nvda_audit.report       : persistencia steps.json, generador de report.html e index.html / ZIP
  - nvda_audit.compare      : comparador multiplataforma Web NVDA vs Android TalkBack / iOS VoiceOver
"""

import argparse
import datetime
import os
import tempfile

from nvda_audit import VERSION
from nvda_audit.cdp import match_dom_element
from nvda_audit.compare import build_comparison_suite
from nvda_audit.config import load_config
from nvda_audit.report import build_report, build_suite_index, rebuild_report
from nvda_audit.rules import is_a11y_relevant, text_a11y_issues
from nvda_audit.wcag_catalog import WCAG_CATALOG, WCAG_CRITERIA, WCAG_ORDER, resolve_wcag_meta
from nvda_audit.web_client import WebClient


def run_self_test():
    """Autocomprobación rápida sin navegador: valida catálogo WCAG 2.2, reglas NVDA-* y generador HTML."""
    assert len(WCAG_CRITERIA) == 86, "Se esperaban 86 criterios WCAG 2.2"
    for rk in WCAG_ORDER:
        cat = WCAG_CATALOG[rk]
        meta = resolve_wcag_meta(cat["criterion"])
        assert meta["level"] in ("A", "AA", "AAA")
        assert meta["w3c_url"].startswith("https://www.w3.org/WAI/WCAG22/Understanding/")
    assert any("Moneda" in x for x in text_a11y_issues("$ 11.415.305,40"))
    assert not any("Moneda" in x for x in text_a11y_issues("US$ 82.119,30"))
    sample_steps = [
        {
            "i": 1, "png": "img/step_001.png", "node": None,
            "utterance": "Siguiente", "raw_caption": "Siguiente",
            "page_title": "Transferencias", "is_skeleton": False,
            "box": (100, 200, 300, 260), "in_overlay": False, "label": "Siguiente",
            "screen_change": False,
        },
        {
            "i": 2, "png": "img/step_002.png", "node": None,
            "utterance": "", "raw_caption": "NVDA menu",
            "page_title": "Elegí con qué cuenta querés operar",
            "is_skeleton": True, "box": None, "in_overlay": True, "label": "",
            "screen_change": True,
        },
        {
            "i": 3, "png": "img/step_003.png", "node": None,
            "utterance": "1 replaced 0 · Siguiente", "raw_caption": "1 replaced 0 · Siguiente",
            "page_title": "Transferencias", "is_skeleton": False,
            "box": None, "in_overlay": False, "label": "", "screen_change": True,
        },
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "img"), exist_ok=True)
        out_html = build_report(sample_steps, [], set(), tmpdir, "self-test")
        content = open(out_html, encoding="utf-8").read()
        assert "NVDA-SKEL-001" in content, "Falta detección NVDA-SKEL-001 en self-test"
        assert "NVDA-FOCUS-001" in content, "Falta detección NVDA-FOCUS-001 en self-test"
    print(
        "Self-test OK (v%s): 86 criterios WCAG 2.2, %d reglas NVDA-* y generador HTML verificados."
        % (VERSION, len(WCAG_CATALOG))
    )


def main():
    ap = argparse.ArgumentParser(description="Auditoría Web con NVDA Speech Viewer y reporte visual (v%s)" % VERSION)
    ap.add_argument("--version", action="version", version="nvda_audit %s" % VERSION)
    ap.add_argument(
        "--profile",
        "-p",
        metavar="NAME",
        help="nombre del perfil en profiles/<NAME>.local.json (ej. app_staging, app_qa)",
    )
    ap.add_argument("--config", metavar="FILE", help="archivo JSON de configuración opcional")
    ap.add_argument("--self-test", action="store_true", help="ejecuta autovalidación interna y sale")
    ap.add_argument(
        "--view",
        metavar="VIEW_ID",
        help="ID de vista declarada en config['views'] (ej. landing, product_bitcoin, buy_bitcoin_step1, o 'all')",
    )
    ap.add_argument("--view-title", metavar="TITLE", help="título descriptivo de la vista para el reporte")
    ap.add_argument("--steps", type=int, default=None, help="máx. de avances de cursor virtual NVDA (default 75)")
    ap.add_argument("--mode", choices=["browse", "tab", "both"], default="browse", help="modo NVDA: browse (cursor virtual flecha abajo), tab (Focus Mode Tab) o both")
    ap.add_argument("--test-modals", action="store_true", help="abre y audita drawers/modales detectados y valida Focus Return")
    ap.add_argument("--url", default=None, help="URL objetivo a auditar")
    ap.add_argument("--locale", default=None, metavar="BCP47", help="idioma objetivo del navegador y NVDA (ej. en-US, es-AR)")
    ap.add_argument("--headed", action="store_true", help="mostrar ventana visible de Google Chrome durante la auditoría")
    ap.add_argument("--out", default=None, help="directorio del reporte")
    ap.add_argument(
        "--pack",
        nargs="?",
        const="auto",
        default=None,
        metavar="ZIP_FILE",
        help="genera index.html maestro y empaqueta los reportes de la suite en un archivo .zip autocontenido",
    )
    ap.add_argument("--rebuild", metavar="DIR", help="regenera report.html desde un directorio previo")
    ap.add_argument(
        "--compare",
        nargs=2,
        metavar=("OTHER_DIR", "NVDA_DIR"),
        help="genera reporte comparativo lado a lado entre otra plataforma (iOS/Android) y Web NVDA",
    )
    args = ap.parse_args()

    if args.self_test:
        run_self_test()
        return

    cfg = load_config(args.config, target_url=args.url, profile=args.profile)
    if args.locale:
        cfg["locale"] = args.locale
    if args.headed:
        cfg["headless"] = False

    if args.compare:
        other_dir, nvda_dir = args.compare
        res = build_comparison_suite(other_dir, nvda_dir)
        print("Reporte comparativo: %s" % res)
        return

    if args.rebuild:
        v_info = {"title": args.view_title} if args.view_title else None
        print("Reporte: %s" % rebuild_report(None, args.rebuild, view_info=v_info, cfg=cfg))
        return

    views_cfg = cfg.get("views") or {}
    if args.view and args.view.lower() == "all":
        view_queue = list(views_cfg.keys())
    elif args.view:
        if args.view not in views_cfg:
            raise SystemExit(
                "Vista '%s' no encontrada en config['views'] (disponibles: %s)"
                % (args.view, ", ".join(views_cfg.keys()) or "ninguna")
            )
        view_queue = [args.view]
    else:
        view_queue = [None]

    views_payload = []
    for v_id in view_queue:
        v_spec = views_cfg.get(v_id, {}) if v_id else {}
        cur_out = (
            args.out
            if (args.out and len(view_queue) == 1)
            else v_spec.get("out")
            or os.path.join(
                os.getcwd(),
                "reportes",
                "adhoc",
                "nvda_report_%s" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
            )
        )
        img_dir = os.path.join(cur_out, "img")
        os.makedirs(img_dir, exist_ok=True)
        for old_png in os.listdir(img_dir):
            if old_png.startswith("step_") and old_png.endswith(".png"):
                try:
                    os.remove(os.path.join(img_dir, old_png))
                except OSError:
                    pass
        views_payload.append({
            "id": v_id or "default",
            "title": args.view_title or v_spec.get("title") or "Vista Web NVDA",
            "short_title": v_spec.get("short_title") or args.view_title or v_spec.get("title") or "Vista Web",
            "scope_tag": v_spec.get("scope_tag") or "",
            "out_dir": cur_out,
            "max_steps": int(args.steps or v_spec.get("steps") or 75),
            "cdp_steps": v_spec.get("cdp_steps") or [],
        })

    client = WebClient(cfg)
    results = client.run_views(views_payload, mode=args.mode, test_modals=args.test_modals)

    completed_dirs = []
    for vp in views_payload:
        res = results.get(vp["id"]) or {}
        steps = res.get("steps") or []
        tree_nodes = res.get("tree_nodes") or []
        visited = set(res.get("visited") or [])
        dom_snapshot = res.get("dom_snapshot")
        if isinstance(dom_snapshot, str):
            import json as _json
            dom_snapshot = _json.loads(dom_snapshot)

        for s in steps:
            if dom_snapshot and not s.get("dom"):
                s["dom"] = match_dom_element(s.get("utterance"), s.get("label"), dom_snapshot, box=s.get("box"))

        extra_ver = ""
        if dom_snapshot:
            if dom_snapshot.get("bundleVersion"):
                extra_ver += " · bundle=v%s" % dom_snapshot["bundleVersion"]
            po = dom_snapshot.get("poeditor") or {}
            if po.get("version"):
                db_lbl = po.get("dbName") or "i18n"
                extra_ver += " · POEditor=%s v%s (%s, %d keys)" % (
                    db_lbl,
                    po["version"],
                    po.get("language", ""),
                    po.get("totalKeys", 0),
                )
        user_lbl = (cfg.get("auth") or {}).get("username") or "n/d"
        meta = "navegador=Chrome Desktop (%dx%d, locale %s) · user=%s · lector=NVDA Browse Mode%s · pasos=%d · %s" % (
            int(cfg.get("viewport_width", 1440)),
            int(cfg.get("viewport_height", 900)),
            cfg.get("locale") or "en-US",
            user_lbl,
            extra_ver,
            len(steps),
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        view_info = {
            "title": vp["title"],
            "short_title": vp["short_title"],
            "scope_tag": vp["scope_tag"],
        }
        tree = [n for n in tree_nodes if is_a11y_relevant(n)]
        path = build_report(
            steps, tree, visited, vp["out_dir"], meta, dom_snapshot=dom_snapshot, view_info=view_info, cfg=cfg
        )
        completed_dirs.append(vp["out_dir"])
        print("Reporte: %s" % path)

    if len(completed_dirs) > 1 or args.pack:
        suite_dirs = completed_dirs
        if len(suite_dirs) <= 1 and views_cfg:
            suite_dirs = [
                v.get("out")
                for v in views_cfg.values()
                if v.get("out") and os.path.exists(os.path.join(v["out"], "report.html"))
            ] or completed_dirs
        zip_target = None
        if args.pack:
            zip_target = (
                os.path.join("reportes", "reportes_nvda_suite_v%s.zip" % VERSION)
                if args.pack == "auto"
                else args.pack
            )
        idx_p, zip_p = build_suite_index(
            suite_dirs,
            zip_path=zip_target,
            suite_title="Auditoría Web NVDA A11Y (v%s)" % VERSION,
        )
        if idx_p:
            print("Portada maestra: %s" % idx_p)
        if zip_p:
            print("Paquete ZIP:     %s" % zip_p)


if __name__ == "__main__":
    main()
