"""Preflight del entorno (--doctor) y diagnostico de red para login/target (Web NVDA)."""

import socket
import subprocess
import sys
from urllib.parse import urlparse

from . import VERSION


def probe_host(url, timeout=5):
    """TCP probe al host:puerto de `url`. Devuelve (ok, detalle)."""
    p = urlparse(url if "://" in url else "https://" + url)
    host = p.hostname or url
    port = p.port or (443 if p.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, "conecta"
    except socket.gaierror:
        return False, "%s no resuelve DNS" % host
    except (socket.timeout, TimeoutError):
        return False, "%s:%d timeout" % (host, port)
    except ConnectionRefusedError:
        return False, "%s:%d conexión rechazada" % (host, port)
    except OSError as e:
        return False, "%s: %s" % (host, e)


def net_hint(url):
    """Pista accionable según el dominio que falló."""
    host = urlparse(url if "://" in url else "https://" + url).hostname or ""
    if ".corp" in host or ".sar." in host or host.endswith(".internal"):
        return "dominio interno -> requiere VPN corporativa activa"
    return "revisa conectividad de red / VPN"


def check_sso_endpoints(cfg, timeout=5):
    """Sondea los endpoints del perfil y devuelve los inalcanzables como
    lista de (key, url, detalle_fallo)."""
    bad = []
    for key in ("login_url", "target_url", "hybrid_cdn_url"):
        url = (cfg or {}).get(key, "")
        if not url:
            continue
        ok, det = probe_host(url, timeout=timeout)
        if not ok:
            bad.append((key, url, det))
    return bad


def friendly_net_error(e, url):
    """Traduce errores urllib/socket a una causa accionable."""
    import urllib.error

    host = urlparse(url).hostname or url
    reason = getattr(e, "reason", e)
    if isinstance(reason, socket.gaierror):
        return "%s no resuelve DNS -> %s" % (host, net_hint(url))
    if isinstance(reason, (socket.timeout, TimeoutError)) or "timed out" in str(reason):
        return "timeout conectando a %s -> %s" % (host, net_hint(url))
    if isinstance(reason, ConnectionRefusedError):
        return "%s rechazó la conexión -> ¿servicio caído o puerto erróneo?" % host
    if isinstance(e, urllib.error.HTTPError):
        return "HTTP %s de %s -> revisa credenciales/token" % (e.code, host)
    return str(e)


_PUPPETEER_CHECK_JS = r"""
const path = require('path');
const cands = [
  path.join(process.env.HOME || '', '.npm-global/lib/node_modules/pa11y/node_modules/puppeteer'),
  '/usr/local/lib/node_modules/pa11y/node_modules/puppeteer',
  path.join(process.env.APPDATA || '', 'npm/node_modules/pa11y/node_modules/puppeteer'),
  path.join(process.env.APPDATA || '', 'npm/node_modules/puppeteer'),
  path.join(process.env.NPM_CONFIG_PREFIX || '', 'lib/node_modules/puppeteer'),
  'puppeteer'
];
for (const c of cands) {
  try { require(c); console.log('FOUND:' + c); process.exit(0); } catch (e) {}
}
console.log('MISS'); process.exit(1);
"""


def run_doctor(cfg):
    """Preflight completo del entorno Web/NVDA. Imprime [OK]/[WARN]/[FAIL]
    y devuelve el numero de fallos (0 = entorno listo)."""
    from .web_client import find_chrome_binary

    fails = [0]
    warns = [0]

    def ok(m):
        print("  [OK]   %s" % m)

    def warn(m):
        warns[0] += 1
        print("  [WARN] %s" % m)

    def fail(m):
        fails[0] += 1
        print("  [FAIL] %s" % m)

    print("=== Doctor NVDA Audit v%s ===\n" % VERSION)

    print("Anfitrión")
    vi = sys.version_info
    if vi >= (3, 9):
        ok("Python %d.%d.%d" % vi[:3])
    else:
        fail("Python %d.%d -> requiere >= 3.9" % vi[:2])

    node_ok = False
    try:
        v = subprocess.run(
            ["node", "--version"], capture_output=True, text=True, timeout=10
        )
        ok("Node.js %s" % v.stdout.strip())
        node_ok = True
    except Exception:
        fail("node no encontrado en PATH -> instala Node.js 18+")

    if node_ok:
        r = subprocess.run(
            ["node", "-e", _PUPPETEER_CHECK_JS],
            capture_output=True,
            text=True,
            timeout=20,
        )
        found = (r.stdout or "").strip()
        if found.startswith("FOUND:"):
            ok("puppeteer resoluble (%s)" % found[6:])
        else:
            fail(
                "puppeteer no resoluble -> npm i -g puppeteer (o pa11y) / revisa las rutas en loadPuppeteer()"
            )

    chrome = find_chrome_binary(cfg)
    if chrome:
        ok("Chrome: %s" % chrome)
    else:
        warn(
            "Chrome no encontrado en rutas por defecto -> puppeteer usará su Chrome for Testing, o fija chrome_path / $CHROME_PATH"
        )

    print("\nRed / endpoints del perfil")
    eps = [
        (k, cfg.get(k))
        for k in ("login_url", "target_url", "hybrid_cdn_url")
        if cfg.get(k)
    ]
    if not eps:
        warn("el perfil no define login_url/target_url/hybrid_cdn_url")
    for key, url in eps:
        okp, det = probe_host(url)
        host = urlparse(url).hostname or url
        if okp:
            ok("%s (%s): conecta" % (host, key))
        else:
            fail("%s (%s): %s -> %s" % (host, key, det, net_hint(url)))

    print("\nResultado: %d fallo(s), %d aviso(s)" % (fails[0], warns[0]))
    return fails[0]
