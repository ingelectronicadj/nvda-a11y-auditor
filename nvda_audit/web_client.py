"""Cliente Web / Chrome CDP + Motor de Buffer Virtual NVDA (Browse Mode & Focus Mode)."""

import json
import os
import subprocess
import tempfile
from .cdp import DOM_EXTRACT_JS
from .config import SCRIPT_DIR


NVDA_RUNNER_JS = r"""
const fs = require('fs');
const path = require('path');

function loadPuppeteer() {
  const candidates = [
    path.join(process.env.HOME || '', '.npm-global/lib/node_modules/pa11y/node_modules/puppeteer'),
    '/usr/local/lib/node_modules/pa11y/node_modules/puppeteer',
    'puppeteer'
  ];
  for (const c of candidates) {
    try { return require(c); } catch (e) {}
  }
  throw new Error('No se encontró puppeteer instalado.');
}

const puppeteer = loadPuppeteer();
const jobFile = process.argv[2];
const job = JSON.parse(fs.readFileSync(jobFile, 'utf8'));

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function applyKeepAlive(page) {
  await page.evaluate(() => {
    try {
      sessionStorage.removeItem('isExpired');
      const raw = sessionStorage.getItem('dev_tools_frame-config');
      const cfg = raw ? JSON.parse(raw) : {};
      cfg.sec_session_inactivity_duration = 86400;
      cfg.sec_session_inactivity_threshold_percent = 95;
      cfg.sec_refresh_token_percent = 0.15;
      sessionStorage.setItem('dev_tools_frame-config', JSON.stringify(cfg));
    } catch (e) {}
  }).catch(() => {});
}

async function performLogin(page, cfg) {
  const loginUrl = cfg.login_url;
  const auth = cfg.auth || {};
  if (!loginUrl || !auth.username || !auth.password) return;

  console.log('      [NVDA Web] iniciando sesión en ' + loginUrl + ' ...');
  for (let att = 0; att < 3; att++) {
    await page.goto(loginUrl, { waitUntil: 'domcontentloaded', timeout: 40000 }).catch(() => {});
    await page.waitForSelector('button#input-dropdown0, input#email', { timeout: 18000 }).catch(() => {});
    const hasDropNow = await page.$('button#input-dropdown0');
    if (hasDropNow) break;
    await sleep(2000);
  }
  await sleep(1500);

  if (auth.doc_type) {
    const hasDrop = await page.$('button#input-dropdown0');
    if (hasDrop) {
      await page.click('button#input-dropdown0').catch(() => {});
      await sleep(900);
      await page.evaluate((dtype) => {
        const items = Array.from(document.querySelectorAll('li, [role="option"], button, span, p'));
        const opt = items.find(el => (el.innerText || '').trim().toLowerCase() === dtype.toLowerCase());
        if (opt) opt.click();
      }, auth.doc_type).catch(() => {});
      await sleep(900);
    }
  }

  const userSel = await page.evaluate(() => {
    const inp = document.querySelector('input:not([type="checkbox"])');
    return inp && inp.id ? ('#' + inp.id) : 'input:not([type="checkbox"])';
  }).catch(() => 'input');
  await page.click(userSel).catch(() => {});
  await page.type(userSel, auth.username, { delay: 12 }).catch(() => {});
  await sleep(600);

  await page.click('[data-testid="document-footer-submit-button"] button').catch(() => {});
  await page.waitForSelector('input[type="password"], input#password', { timeout: 20000 }).catch(() => {});
  await sleep(900);

  await page.click('input#password').catch(() => {});
  await page.type('input#password', auth.password, { delay: 12 }).catch(() => {});
  await sleep(600);
  await page.evaluate(() => {
    const sub = Array.from(document.querySelectorAll('button')).find(b => /log in|continue|entrar/i.test(b.innerText || ''));
    if (sub) sub.click();
  }).catch(() => {});

  const quickAction = auth.entry_quick_action || 'Crypto';
  for (let i = 0; i < 18; i++) {
    await sleep(1500);
    await applyKeepAlive(page);
    const clicked = await page.evaluate((qa) => {
      const els = Array.from(document.querySelectorAll('button, a, [role="button"]'));
      const btn = els.find(el => (el.innerText || '').trim() === qa || (el.getAttribute('aria-label') || '').includes(qa));
      if (btn) {
        btn.click();
        return true;
      }
      return false;
    }, quickAction).catch(() => false);
    if (clicked) {
      console.log('      [NVDA Web] quick action "' + quickAction + '" activada en Global Position');
      break;
    }
  }

  for (let i = 0; i < 14; i++) {
    await sleep(1500);
    const ready = await page.evaluate(() => {
      const h = document.querySelector('main h1, h1');
      return h ? h.innerText.trim() : '';
    }).catch(() => '');
    if (ready && ready.toLowerCase() !== 'overview' && !page.url().includes('/login')) {
      console.log('      [NVDA Web] módulo cargado -> H1: "' + ready + '" (' + page.url() + ')');
      break;
    }
  }
}

async function runViewSteps(page, steps) {
  let lastTransitionFocusIssue = '';
  for (const st of (steps || [])) {
    if (st.spa_path) {
      await page.evaluate((p) => {
        const closeBtn = document.querySelector('[role="dialog"] button[aria-label="Close"], [role="dialog"] button[data-testid="close-button"]');
        if (closeBtn) closeBtn.click();
        window.history.pushState({}, '', p);
        window.dispatchEvent(new PopStateEvent('popstate'));
      }, st.spa_path).catch(() => {});
      for (let w = 0; w < 12; w++) {
        await sleep(800);
        const hasBrokerH1 = await page.evaluate(() => {
          const h1 = document.querySelector('[data-testid="microfrontend-broker"] h1, main h1');
          return h1 && h1.innerText && h1.innerText.trim().toLowerCase() !== 'cryptocurrencies';
        }).catch(() => false);
        if (hasBrokerH1) break;
      }
    }
    if (st.click || st.click_selector) {
      const sel = st.click || st.click_selector;
      await page.evaluate((s) => {
        const el = document.querySelector(s);
        if (el) el.click();
      }, sel).catch(() => {});
    }
    if (st.click_text) {
      await page.evaluate((txt) => {
        const needle = txt.toLowerCase();
        const openDlg = Array.from(document.querySelectorAll('[role="dialog"]')).find(d => d.getBoundingClientRect().width > 50);
        const searchRoot = openDlg || document.querySelector('main') || document.body;
        const cands = Array.from(searchRoot.querySelectorAll('a, button, [role="tab"], [role="button"], label, [data-testid="selector-row"], p, span'));
        for (const el of cands) {
          const t = ((el.innerText || '') + ' ' + (el.getAttribute('aria-label') || '')).trim().toLowerCase();
          if (t === needle || t.includes(needle)) {
            const target = el.closest('a, button, [role="button"], [role="tab"], label, [data-testid="selector-row"]') || el;
            target.click();
            return true;
          }
        }
        return false;
      }, st.click_text).catch(() => {});
    }
    if (st.type_selector) {
      await page.click(st.type_selector, { clickCount: 3 }).catch(() => {});
      await page.keyboard.press('Backspace').catch(() => {});
      await page.evaluate((sel) => {
        const el = document.querySelector(sel);
        if (el && el.value && el.value !== '0') {
          const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
          if (setter) setter.call(el, '');
          el.dispatchEvent(new Event('input', { bubbles: true }));
        }
      }, st.type_selector).catch(() => {});
      await page.type(st.type_selector, String(st.text || ''), { delay: 18 }).catch(() => {});
    }
    if (st.eval) {
      await page.evaluate(st.eval).catch(() => {});
    }
    const prevH2 = await page.evaluate(() => (document.querySelector('main h2, main h1')?.innerText || '').trim()).catch(() => '');
    await sleep(Math.round((st.wait_sec || 2.0) * 1000));
    if (st.click_text && /^(next|confirm|back|continue|read documentation)$/i.test(st.click_text.trim())) {
      const fCheck = await page.evaluate(() => {
        const ae = document.activeElement;
        const h = document.querySelector('main h2, main h1');
        const hTxt = h ? (h.innerText || '').trim() : '';
        if (!ae || ae === document.body) {
          return { bad: false, hTxt, aeTxt: 'BODY' };
        }
        const tag = ae.tagName.toLowerCase();
        const aeTxt = (ae.getAttribute('aria-label') || ae.innerText || '').replace(/\s+/g, ' ').trim();
        const r = ae.getBoundingClientRect();
        const hr = h ? h.getBoundingClientRect() : { bottom: 200 };
        const stayedOnFooterBtn = (tag === 'button' && r.top > hr.bottom + 120);
        return { bad: stayedOnFooterBtn, hTxt, aeTxt: tag + ' "' + aeTxt.slice(0, 45) + '"' };
      }).catch(() => ({ bad: false }));
      if (fCheck.bad) {
        lastTransitionFocusIssue = 'Orden del foco en transición SPA (WCAG 2.4.3): tras avanzar a «' + (fCheck.hTxt || 'nueva vista') + '», el foco permaneció en el botón inferior (' + fCheck.aeTxt + ') en lugar de moverse al inicio de la nueva vista';
      }
    }
  }
  return lastTransitionFocusIssue;
}

const COLLECT_NVDA_ITEMS_JS = `(() => {
  const openDlg = Array.from(document.querySelectorAll('[role="dialog"]')).find(d => {
    const r = d.getBoundingClientRect();
    return r.width > 50 && r.height > 50;
  });
  const scope = openDlg || document.querySelector('main') || document.body;
  const items = [];
  const visitedEls = new Set();

  function resolveAriaLabelledBy(el) {
    const ids = (el.getAttribute('aria-labelledby') || '').trim().split(/\\s+/).filter(Boolean);
    if (!ids.length) return '';
    return ids.map(id => {
      const ref = document.getElementById(id);
      return ref ? (ref.getAttribute('aria-label') || ref.innerText || ref.textContent || '').trim() : '';
    }).filter(Boolean).join(' ');
  }

  function isHidden(el) {
    let cur = el;
    while (cur && cur !== document.body) {
      if (cur.getAttribute?.('aria-hidden') === 'true' || cur.hasAttribute?.('inert')) return true;
      if (cur.getAttribute?.('data-testid')?.startsWith('DevTools')) return true;
      const st = window.getComputedStyle(cur);
      if (st.display === 'none' || st.visibility === 'hidden') return true;
      cur = cur.parentElement;
    }
    return false;
  }

  function buildSelector(el) {
    const tag = el.tagName.toLowerCase();
    const tid = el.getAttribute('data-testid') || '';
    const id = el.id || '';
    const role = el.getAttribute('role') || '';
    let s = tag;
    if (id && !/\\s/.test(id)) s += '#' + id;
    if (tid) s += '[data-testid="' + tid + '"]';
    if (role) s += '[role="' + role + '"]';
    return s;
  }

  const all = Array.from(scope.querySelectorAll('*'));
  let chartCount = 0;

  for (const el of all) {
    if (visitedEls.has(el) || isHidden(el)) continue;
    const tag = el.tagName.toLowerCase();
    const role = (el.getAttribute('role') || '').toLowerCase();
    const tid = el.getAttribute('data-testid') || '';
    const ariaLbl = (el.getAttribute('aria-label') || '').trim();
    const ariaLblBy = resolveAriaLabelledBy(el);

    // 1. Headings (h1..h6 or role="heading")
    if (/^h[1-6]$/.test(tag) || role === 'heading') {
      const lvl = /^h[1-6]$/.test(tag) ? tag.slice(1) : (el.getAttribute('aria-level') || '2');
      const txt = (ariaLblBy || ariaLbl || el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
      if (!txt) continue;
      el.querySelectorAll('*').forEach(c => visitedEls.add(c));
      items.push({
        el,
        label: txt,
        role: 'Heading ' + lvl,
        utterance: 'heading level ' + lvl + ' ' + txt,
        selector: buildSelector(el)
      });
      continue;
    }

    // 2. Tabs (role="tab")
    if (role === 'tab') {
      const txt = (ariaLblBy || ariaLbl || el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
      const sel = el.getAttribute('aria-selected') === 'true';
      const parentList = el.closest('[role="tablist"]');
      const tabs = parentList ? Array.from(parentList.querySelectorAll('[role="tab"]')) : [el];
      const idx = tabs.indexOf(el) + 1;
      el.querySelectorAll('*').forEach(c => visitedEls.add(c));
      items.push({
        el,
        label: txt,
        role: 'Tab',
        utterance: txt + ' tab ' + (sel ? 'selected ' : '') + idx + ' of ' + tabs.length,
        selector: buildSelector(el)
      });
      continue;
    }

    // 3. Links (a[href] or role="link")
    if (tag === 'a' || role === 'link') {
      const txt = (ariaLblBy || ariaLbl || el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
      el.querySelectorAll('*').forEach(c => visitedEls.add(c));
      items.push({
        el,
        label: txt || '(empty link)',
        role: 'Link',
        utterance: (txt ? (txt + ' ') : '') + 'link',
        selector: buildSelector(el)
      });
      continue;
    }

    // 4. Buttons (button or role="button")
    if (tag === 'button' || role === 'button') {
      const txt = (ariaLblBy || ariaLbl || el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
      const nestedAria = !txt ? (el.querySelector('span[aria-label]:not([role]), div[aria-label]:not([role])')?.getAttribute('aria-label') || '').trim() : '';
      const dis = el.hasAttribute('disabled') || el.getAttribute('aria-disabled') === 'true';
      const exp = el.getAttribute('aria-expanded');
      el.querySelectorAll('*').forEach(c => visitedEls.add(c));
      const uttLbl = txt ? txt : ('Unlabelled' + (nestedAria ? (' [span child aria-label="' + nestedAria + '"]') : ''));
      items.push({
        el,
        label: txt || ('Unlabelled button' + (nestedAria ? (' (span aria-label: ' + nestedAria + ')') : '')),
        role: 'Button',
        utterance: uttLbl + ' button' + (dis ? ' unavailable' : '') + (exp === 'true' ? ' expanded' : (exp === 'false' ? ' collapsed' : '')),
        selector: buildSelector(el)
      });
      continue;
    }

    // 5. Text / Currency inputs
    if (tag === 'input' && (el.type || 'text').toLowerCase() !== 'radio' && (el.type || 'text').toLowerCase() !== 'checkbox') {
      const txt = (ariaLblBy || ariaLbl || el.getAttribute('placeholder') || '').replace(/\\s+/g, ' ').trim();
      const val = (el.value || '').trim();
      items.push({
        el,
        label: txt,
        role: 'Edit',
        utterance: txt + ' edit' + (val ? (' ' + val) : ''),
        selector: buildSelector(el)
      });
      continue;
    }

    // 5b. Custom selector rows (role="radio" or data-testid="selector-row" in Account Drawer)
    if (role === 'radio' || tid === 'selector-row') {
      const txt = (ariaLblBy || ariaLbl || el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
      const chk = (el.getAttribute('aria-checked') === 'true' || el.getAttribute('data-selected') === 'true') ? 'checked' : 'not checked';
      el.querySelectorAll('*').forEach(c => visitedEls.add(c));
      items.push({
        el,
        label: txt,
        role: role === 'radio' ? 'RadioButton' : 'SelectorRow',
        utterance: txt + (role === 'radio' ? (' radio button ' + chk) : ''),
        selector: buildSelector(el)
      });
      continue;
    }

    // 6. Radio inputs (e.g. quick-amount pills)
    if (tag === 'input' && (el.type || '').toLowerCase() === 'radio') {
      const txt = (ariaLblBy || ariaLbl || '').replace(/\\s+/g, ' ').trim();
      const chk = el.checked ? 'checked' : 'not checked';
      const group = el.name ? Array.from(scope.querySelectorAll('input[type="radio"][name="' + el.name + '"]')) : [el];
      const idx = group.indexOf(el) + 1;
      items.push({
        el,
        label: txt,
        role: 'RadioButton',
        utterance: txt + ' radio button ' + chk + ' ' + idx + ' of ' + group.length,
        selector: buildSelector(el)
      });
      continue;
    }

    // 6b. Checkbox inputs
    if (tag === 'input' && (el.type || '').toLowerCase() === 'checkbox') {
      const lblEl = el.id ? document.querySelector('label[for="' + el.id + '"]') : el.closest('label');
      const txt = (ariaLblBy || ariaLbl || (lblEl ? lblEl.innerText : '') || '').replace(/\\s+/g, ' ').trim();
      const chk = el.checked ? 'checked' : 'not checked';
      items.push({
        el,
        label: txt || 'Unlabelled checkbox',
        role: 'CheckBox',
        utterance: (txt || 'Unlabelled') + ' check box ' + chk,
        selector: buildSelector(el)
      });
      continue;
    }

    // 7. SVG charts and circle data points
    if (tag === 'svg' && tid.startsWith('line-chart')) {
      const txt = (ariaLblBy || ariaLbl || '').replace(/\\s+/g, ' ').trim();
      items.push({
        el,
        label: txt || 'Unlabelled',
        role: 'Graphic',
        utterance: (txt ? ('graphic ' + txt) : 'Unlabelled graphic'),
        selector: buildSelector(el)
      });
      continue;
    }

    if (tag === 'circle' && (tid === 'node-circle' || role === 'img' || ariaLbl)) {
      chartCount += 1;
      if (chartCount <= 5) {
        items.push({
          el,
          label: ariaLbl,
          role: 'Graphic',
          utterance: 'Date: ' + ariaLbl.replace(/^Date:\\s*/i, '') + ' graphic',
          selector: buildSelector(el),
          isChartPoint: true
        });
      }
      continue;
    }

    // 8. Images (img)
    if (tag === 'img') {
      const alt = el.getAttribute('alt');
      if (alt === '') continue;
      items.push({
        el,
        label: alt || 'Unlabelled image',
        role: 'Graphic',
        utterance: (alt ? (alt + ' graphic') : 'Unlabelled graphic'),
        selector: buildSelector(el)
      });
      continue;
    }

    // 9. Live region role="status"
    if (role === 'status') {
      const rawTxt = el.textContent || '';
      const cleanTxt = rawTxt.replace(/\\u200b/g, '').trim();
      if (rawTxt.length > 0 && !cleanTxt) {
        items.push({
          el,
          label: rawTxt,
          role: 'Status',
          utterance: 'status',
          selector: buildSelector(el)
        });
      }
      continue;
    }

    // 10. Leaf text nodes (p, dt, dd, legend, span[data-testid="screen-reader"], label)
    if (['p', 'dt', 'dd', 'legend', 'span', 'label'].includes(tag)) {
      if (tag === 'span' && tid !== 'screen-reader' && tid !== 'text') continue;
      const hasInteractiveChild = el.querySelector('a, button, input, select, textarea');
      if (tag !== 'label' && hasInteractiveChild) continue;
      const directTxt = (tag === 'label')
        ? Array.from(el.querySelectorAll('[data-testid="text"]')).map(s => s.innerText || s.textContent || '').join(' ').trim()
        : (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
      if (!directTxt) continue;
      if (tag === 'label') {
        el.querySelectorAll('[data-testid="text"], [data-pill-content] *').forEach(c => visitedEls.add(c));
      } else {
        el.querySelectorAll('*').forEach(c => visitedEls.add(c));
      }
      const roleSuffix = (tag === 'dt' || role === 'term') ? ' term' : '';
      items.push({
        el,
        label: directTxt,
        role: tag === 'dt' ? 'Term' : 'Text',
        utterance: directTxt + roleSuffix,
        selector: buildSelector(el)
      });
    }
  }

  return items.map((it, idx) => {
    it.el.setAttribute('data-nvda-step-idx', String(idx));
    return {
      idx,
      label: it.label,
      role: it.role,
      utterance: it.utterance,
      selector: it.selector,
      isChartPoint: !!it.isChartPoint
    };
  });
})()`;

(async () => {
  const browser = await puppeteer.launch({
    headless: job.headless ? 'new' : false,
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    defaultViewport: { width: job.viewport_width || 1440, height: job.viewport_height || 900 },
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--lang=' + (job.locale || 'en-US')]
  });

  const page = await browser.newPage();
  const netOverrides = (job.cfg && job.cfg.network_overrides) || {};
  if (Object.keys(netOverrides).length > 0) {
    await page.setRequestInterception(true);
    page.on('request', req => {
      const u = req.url();
      for (const [pat, mockBody] of Object.entries(netOverrides)) {
        if (u.includes(pat)) {
          const corsHeaders = {
            'Access-Control-Allow-Origin': req.headers()['origin'] || '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': req.headers()['access-control-request-headers'] || '*',
            'Access-Control-Allow-Credentials': 'true'
          };
          if (req.method() === 'OPTIONS') {
            req.respond({ status: 204, headers: corsHeaders, body: '' });
            return;
          }
          const bodyStr = (typeof mockBody === 'string') ? mockBody : JSON.stringify(mockBody);
          req.respond({
            status: 200,
            contentType: 'application/json',
            headers: corsHeaders,
            body: bodyStr
          });
          return;
        }
      }
      req.continue();
    });
  }

  await performLogin(page, job.cfg);

  const results = {};
  for (const v of job.views) {
    console.log('      [NVDA Web] preparando vista "' + v.title + '" ...');
    const spaFocusIssue = await runViewSteps(page, v.cdp_steps || []);
    await applyKeepAlive(page);
    for (let sk = 0; sk < 6; sk++) {
      const hasSkel = await page.evaluate(() => !!document.querySelector('[aria-busy="true"], [data-testid*="skeleton"]')).catch(() => false);
      if (!hasSkel) break;
      await sleep(900);
    }

    const rawDom = await page.evaluate(job.dom_extract_js).catch(() => null);
    const domSnapshot = (typeof rawDom === 'string') ? JSON.parse(rawDom) : rawDom;
    let rawItems = await page.evaluate(COLLECT_NVDA_ITEMS_JS).catch(() => []);
    if (job.mode === 'tab' || job.mode === 'both') {
      const tabStops = [];
      await page.evaluate(() => { if (document.activeElement) document.activeElement.blur(); });
      for (let t = 0; t < 25; t++) {
        await page.keyboard.press('Tab');
        await sleep(60);
        const cur = await page.evaluate(() => {
          const ae = document.activeElement;
          if (!ae || ae === document.body) return null;
          const tag = ae.tagName.toLowerCase();
          const tid = ae.getAttribute('data-testid') || '';
          if (tid.startsWith('DevTools')) return null;
          const lbl = (ae.getAttribute('aria-label') || ae.innerText || ae.getAttribute('placeholder') || '').replace(/\s+/g, ' ').trim();
          const r = ae.getBoundingClientRect();
          return { tag, tid, lbl: lbl.slice(0, 80), x: Math.round(r.left), y: Math.round(r.top) };
        }).catch(() => null);
        if (cur) {
          const key = cur.tag + ':' + cur.lbl + ':' + cur.x + ':' + cur.y;
          if (tabStops.some(s => s.key === key)) break;
          tabStops.push({ ...cur, key });
        }
      }
      if (domSnapshot && typeof domSnapshot === 'object') {
        domSnapshot.tabStops = tabStops;
      }
    }
    const maxSteps = Math.min(rawItems.length, v.max_steps || 70);

    const steps = [];
    const treeNodes = [];
    const visited = [];

    for (let i = 0; i < maxSteps; i++) {
      const it = rawItems[i];
      const stepNum = i + 1;
      const box = await page.evaluate((stepIdx, utt, stepN, totalN) => {
        const el = document.querySelector('[data-nvda-step-idx="' + stepIdx + '"]');
        let rect = { x: 40, y: 120, width: 220, height: 32 };
        if (el) {
          el.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' });
          const r = el.getBoundingClientRect();
          if (r.width > 1 && r.height > 1) {
            rect = { x: Math.round(r.left), y: Math.round(r.top), width: Math.round(r.width), height: Math.round(r.height) };
          }
        }
        let hl = document.getElementById('__nvda_focus_ring__');
        if (!hl) {
          hl = document.createElement('div');
          hl.id = '__nvda_focus_ring__';
          document.body.appendChild(hl);
        }
        hl.style.cssText = [
          'position:fixed',
          'left:' + Math.max(2, rect.x - 3) + 'px',
          'top:' + Math.max(2, rect.y - 3) + 'px',
          'width:' + Math.max(18, rect.width + 6) + 'px',
          'height:' + Math.max(18, rect.height + 6) + 'px',
          'border:3px solid #22c55e',
          'box-shadow:0 0 0 2px rgba(15,23,42,0.85)',
          'border-radius:6px',
          'pointer-events:none',
          'z-index:2147483646'
        ].join(';');

        let bar = document.getElementById('__nvda_speech_viewer__');
        if (!bar) {
          bar = document.createElement('div');
          bar.id = '__nvda_speech_viewer__';
          document.body.appendChild(bar);
        }
        bar.style.cssText = [
          'position:fixed',
          'left:50%',
          'bottom:18px',
          'transform:translateX(-50%)',
          'min-width:520px',
          'max-width:88vw',
          'background:rgba(15,23,42,0.94)',
          'color:#f8fafc',
          'padding:11px 18px',
          'border-radius:8px',
          'border:1px solid #334155',
          'border-left:5px solid #22c55e',
          'font:600 14px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif',
          'box-shadow:0 10px 25px rgba(0,0,0,0.35)',
          'pointer-events:none',
          'z-index:2147483647'
        ].join(';');
        bar.textContent = '[NVDA Speech Viewer #' + stepN + '/' + totalN + ']  ' + utt;

        return [rect.x, rect.y, rect.x + rect.width, rect.y + rect.height];
      }, it.idx, it.utterance, stepNum, maxSteps);

      const pngPath = path.join(v.out_dir, 'img', 'step_' + String(stepNum).padStart(3, '0') + '.png');
      await page.screenshot({ path: pngPath });

      const nodeObj = {
        cls: it.role,
        text: it.label,
        desc: it.label,
        rid: it.selector,
        pkg: 'web',
        bounds: box,
        focusable: true,
        clickable: ['Button', 'Link', 'Tab', 'RadioButton', 'Edit'].includes(it.role)
      };
      treeNodes.push(nodeObj);
      visited.push(it.selector + '|' + it.label);
      steps.push({
        i: stepNum,
        png: pngPath,
        node: nodeObj,
        utterance: it.utterance,
        raw_caption: it.utterance,
        page_title: (domSnapshot && domSnapshot.viewHeading) || v.title,
        is_skeleton: false,
        box: box,
        in_overlay: false,
        label: it.label,
        screen_change: stepNum === 1
      });
      console.log('      ' + String(stepNum).padStart(3, ' ') + '. ' + (it.label || '?').slice(0, 50).padEnd(52, ' ') + ' | NVDA: ' + it.utterance.slice(0, 65));
    }

    if (job.test_modals) {
      const modalTrigger = await page.evaluate(() => {
        const btns = Array.from((document.querySelector('main') || document.body).querySelectorAll('button, [role="button"]'));
        const b = btns.find(el => /change .*order|more information|más información|order type|tipo de orden/i.test((el.getAttribute('aria-label') || el.innerText || '')));
        if (!b) return null;
        const lbl = (b.getAttribute('aria-label') || b.innerText || '').trim();
        b.focus();
        b.click();
        return lbl;
      }).catch(() => null);
      if (modalTrigger) {
        await sleep(1600);
        const modalInfo = await page.evaluate(() => {
          const dlg = document.querySelector('[role="dialog"]');
          if (!dlg) return null;
          const h = dlg.querySelector('h1, h2, h3');
          const title = h ? (h.innerText || '').trim() : 'Dialog';
          const badBtn = dlg.querySelector('button:not([aria-label]) > span[aria-label]:not([role])');
          const nestedAria = badBtn ? badBtn.getAttribute('aria-label') : '';
          const r = dlg.getBoundingClientRect();
          return {
            title,
            nestedAria,
            box: [Math.round(r.left), Math.round(r.top), Math.round(r.right), Math.round(r.bottom)]
          };
        }).catch(() => null);
        if (modalInfo) {
          const mStepNum = steps.length + 1;
          const mPng = path.join(v.out_dir, 'img', 'step_' + String(mStepNum).padStart(3, '0') + '.png');
          await page.screenshot({ path: mPng });
          const mUtt = 'dialog ' + modalInfo.title + (modalInfo.nestedAria ? (' · Unlabelled button (nested span aria-label="' + modalInfo.nestedAria + '")') : '');
          steps.push({
            i: mStepNum,
            png: mPng,
            node: { cls: 'Dialog', text: modalInfo.title, desc: modalInfo.title, rid: 'div[role="dialog"]', pkg: 'web', bounds: modalInfo.box, focusable: true, clickable: false },
            utterance: mUtt,
            raw_caption: mUtt,
            page_title: modalInfo.title,
            is_skeleton: false,
            box: modalInfo.box,
            in_overlay: false,
            label: modalInfo.title,
            screen_change: true,
            is_modal: true
          });
          if (modalInfo.nestedAria && domSnapshot && Array.isArray(domSnapshot.elements)) {
            domSnapshot.elements.push({
              tag: 'button',
              selector: 'button[data-testid="tooltip-trigger"]',
              testId: 'tooltip-trigger',
              role: '',
              ariaLabel: '',
              label: '',
              nestedSpanAria: modalInfo.nestedAria,
              poeditorOrigin: 'Origen: Componente de Librería UI (Design System)',
              html: '<button data-testid="tooltip-trigger" type="button"><span aria-label="' + modalInfo.nestedAria + '" data-testid="icon-button"><svg aria-hidden="true"></svg></span></button>'
            });
          }
          await page.evaluate(() => {
            const c = document.querySelector('[role="dialog"] button[aria-label="Close"], [role="dialog"] button[data-testid="close-button"]');
            if (c) c.click();
          }).catch(() => {});
          await sleep(1000);
        }
      }
    }

    await page.evaluate(() => {
      document.getElementById('__nvda_focus_ring__')?.remove();
      document.getElementById('__nvda_speech_viewer__')?.remove();
    }).catch(() => {});

    results[v.id] = {
      dom_snapshot: domSnapshot,
      steps,
      tree_nodes: treeNodes,
      visited
    };
  }

  fs.writeFileSync(job.out_json, JSON.stringify(results));
  await browser.close();
})();
"""


class WebClient:
    """Ejecuta el motor de inspección Web + NVDA Browse Mode sobre Google Chrome vía CDP."""

    def __init__(self, cfg):
        self.cfg = cfg

    def run_views(self, views_payload, mode="browse", test_modals=False):
        with tempfile.TemporaryDirectory() as tmpdir:
            runner_js = os.path.join(tmpdir, "nvda_runner.js")
            job_json = os.path.join(tmpdir, "nvda_job.json")
            out_json = os.path.join(tmpdir, "nvda_out.json")
            with open(runner_js, "w", encoding="utf-8") as f:
                f.write(NVDA_RUNNER_JS)
            job = {
                "cfg": self.cfg,
                "locale": self.cfg.get("locale") or "en-US",
                "headless": bool(self.cfg.get("headless", True)),
                "viewport_width": int(self.cfg.get("viewport_width", 1440)),
                "viewport_height": int(self.cfg.get("viewport_height", 900)),
                "dom_extract_js": DOM_EXTRACT_JS,
                "views": views_payload,
                "mode": mode,
                "test_modals": bool(test_modals),
                "out_json": out_json,
            }
            with open(job_json, "w", encoding="utf-8") as f:
                json.dump(job, f)
            subprocess.run(["node", runner_js, job_json], check=True)
            return json.loads(open(out_json, encoding="utf-8").read())
