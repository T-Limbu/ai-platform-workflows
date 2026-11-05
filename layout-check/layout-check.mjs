#!/usr/bin/env node
// Responsive layout check: loads each configured page at six widths and fails on
// sideways overflow, off-screen content, overlapping tap targets, clipped text and
// missing must-be-reachable elements. Usage: node layout-check.mjs <config.json> [--report-only]
import { readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

export const WIDTHS = [320, 360, 414, 768, 1024, 1440];

// Runs inside the page (must stay self-contained). Returns [{check, severity, detail}].
export function pageAudit({ mustBeReachable = [], ignoreSelector = '' }) {
  const out = [];
  const add = (check, severity, detail) => out.push({ check, severity, detail });
  const vw = document.documentElement.clientWidth;
  const label = (el) => {
    const t = (el.getAttribute('aria-label') || el.innerText || el.getAttribute('title') || el.getAttribute('placeholder') || '').trim().replace(/\s+/g, ' ').slice(0, 30);
    const cls = typeof el.className === 'string' ? el.className.trim().split(/\s+/).slice(0, 2).join('.') : '';
    return '<' + el.tagName.toLowerCase() + (cls ? '.' + cls : '') + '>' + (t ? ' "' + t + '"' : '');
  };
  const isIgnored = (el) => !!(el.closest('[data-layout-ignore]') || (ignoreSelector && el.closest(ignoreSelector)));
  const visible = (el) => {
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || Number(s.opacity) === 0) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  // an ancestor (below body) that scrolls or clips sideways makes overflow inside it intentional
  const inScrollBox = (el) => {
    for (let p = el.parentElement; p && p !== document.body && p !== document.documentElement; p = p.parentElement) {
      const s = getComputedStyle(p);
      if (/(auto|scroll|hidden|clip)/.test(s.overflowX) && p.scrollWidth > p.clientWidth) return true;
    }
    return false;
  };

  // 1. sideways scroll
  const sw = Math.max(document.documentElement.scrollWidth, document.body.scrollWidth);
  if (sw > vw + 1) add('sideways-scroll', 'error', 'page is ' + sw + 'px wide in a ' + vw + 'px viewport');

  const all = [...document.body.querySelectorAll('*')].filter((e) => visible(e) && !isIgnored(e));

  // 2. off-screen content (elements with their own text, or controls and images)
  const offScreen = [];
  for (const el of all) {
    if (/^(script|style|svg|path)$/i.test(el.tagName) || el.closest('svg')) continue;
    if (getComputedStyle(el).position === 'fixed') continue;
    const r = el.getBoundingClientRect();
    if (r.right > vw + 1 || r.left < -1) {
      const own = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim()) || /^(A|BUTTON|INPUT|SELECT|TEXTAREA|IMG)$/.test(el.tagName);
      if (own && !inScrollBox(el)) offScreen.push(label(el) + ' spans ' + Math.round(r.left) + '..' + Math.round(r.right));
    }
  }
  offScreen.slice(0, 8).forEach((d) => add('off-screen', 'error', d));

  // 3. overlapping interactive elements, 5. small tap targets
  const sel = 'a[href],button,input:not([type=hidden]),select,textarea,[role=button],[role=tab],summary';
  const ctrls = all.filter((e) => e.matches(sel) && !e.closest('svg'));
  const rects = ctrls.map((e) => e.getBoundingClientRect());
  const seen = new Set();
  for (let i = 0; i < ctrls.length; i++) {
    for (let j = i + 1; j < ctrls.length; j++) {
      if (ctrls[i].contains(ctrls[j]) || ctrls[j].contains(ctrls[i])) continue;
      const a = rects[i], b = rects[j];
      const w = Math.min(a.right, b.right) - Math.max(a.left, b.left);
      const h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (w > 4 && h > 4) {
        const key = label(ctrls[i]) + '|' + label(ctrls[j]);
        if (!seen.has(key)) { seen.add(key); add('overlap', 'error', label(ctrls[i]) + ' overlaps ' + label(ctrls[j]) + ' by ' + Math.round(w) + 'x' + Math.round(h) + 'px'); }
      }
    }
  }
  const small = ctrls.filter((e, i) => (rects[i].width < 24 || rects[i].height < 24) && getComputedStyle(e).display !== 'inline');
  if (small.length) add('small-tap-target', 'warning', small.length + ' control(s) under 24px, e.g. ' + small.slice(0, 3).map(label).join(', '));

  // 4. clipped text (overflow hidden, no ellipsis, content wider than its box)
  const clipped = [];
  for (const el of all) {
    if (![...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) continue;
    const s = getComputedStyle(el);
    if (/(hidden|clip)/.test(s.overflowX) && el.scrollWidth > el.clientWidth + 1 && s.textOverflow !== 'ellipsis') {
      clipped.push(label(el) + ' content ' + el.scrollWidth + 'px in ' + el.clientWidth + 'px');
    }
  }
  clipped.slice(0, 8).forEach((d) => add('clipped-text', 'error', d));

  // 6. must-be-reachable: visible, on screen, not covered by something else
  for (const m of mustBeReachable) {
    const els = [...document.querySelectorAll(m.selector)];
    const ok = els.find((e) => {
      if (!visible(e)) return false;
      const r = e.getBoundingClientRect();
      if (r.right <= 0 || r.left >= vw || r.bottom <= 0) return false;
      if (r.top >= innerHeight) return true; // below the fold: reachable by scrolling
      const cx = Math.min(Math.max(r.left + r.width / 2, 0), vw - 1);
      const cy = Math.min(Math.max(r.top + r.height / 2, 0), innerHeight - 1);
      const top = document.elementFromPoint(cx, cy);
      return !top || e.contains(top) || top.contains(e);
    });
    if (!ok) add('unreachable', 'error', (m.name || m.selector) + ' (' + m.selector + ') is ' + (els.length ? 'hidden, off-screen or covered' : 'missing'));
  }
  return out;
}

export async function run(configPath, { reportOnly = false } = {}) {
  const cfg = JSON.parse(readFileSync(configPath, 'utf8'));
  const base = process.env.LAYOUT_BASE_URL || cfg.baseUrl;
  const req = createRequire(resolve(process.cwd(), 'package.json'));
  const { chromium } = req('playwright');
  const browser = await chromium.launch();
  const results = [];
  try {
    // sign in once through the API with a seeded local account (no accounts are created)
    const storage = {};
    if (cfg.login) {
      const user = process.env[cfg.login.userEnv];
      const pass = process.env[cfg.login.passEnv];
      if (!user || !pass) throw new Error('set ' + cfg.login.userEnv + ' and ' + cfg.login.passEnv + ' for the layout check login');
      const res = await fetch(new URL(cfg.login.apiPath, base), {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ [cfg.login.userField || 'identifier']: user, [cfg.login.passField || 'password']: pass }),
      });
      const body = await res.json();
      if (!res.ok || !body.token) throw new Error('layout check login failed (' + res.status + '): ' + (body.error || 'no token'));
      for (const [key, from] of Object.entries(cfg.login.storage)) storage[key] = JSON.stringify(from === 'token' ? body.token : { ...body.user, ...(cfg.login.userExtra || {}) });
    }
    for (const page of cfg.pages) {
      for (const width of cfg.widths || WIDTHS) {
        const ctx = await browser.newContext({ viewport: { width, height: 800 }, hasTouch: width < 768, isMobile: width < 768 });
        if (cfg.login && !page.anonymous) await ctx.addInitScript((s) => { for (const [k, v] of Object.entries(s)) localStorage.setItem(k, v); }, storage);
        const p = await ctx.newPage();
        await p.goto(new URL(page.path, base).href, { waitUntil: 'networkidle' });
        if (page.waitFor) await p.waitForSelector(page.waitFor, { timeout: 15000 });
        await p.waitForTimeout(300);
        const landed = new URL(p.url()).pathname;
        if (landed !== new URL(page.path, base).pathname) throw new Error('layout check: ' + page.path + ' redirected to ' + landed + ' at ' + width + 'px (login not accepted by the app?)');
        const must = [...(cfg.mustBeReachable || []), ...(page.mustBeReachable || [])];
        const findings = await p.evaluate(pageAudit, { mustBeReachable: must, ignoreSelector: cfg.ignoreSelector || '' });
        // a page marked reportOnly (known, ticketed problems) reports its errors as warnings so it does not block
        if (page.reportOnly) for (const f of findings) if (f.severity === 'error') { f.severity = 'warning'; f.check += ' (known)'; }
        results.push({ page: page.path, width, findings });
        await ctx.close();
      }
    }
  } finally {
    await browser.close();
  }
  const all = results.flatMap((r) => r.findings);
  const errors = all.filter((f) => f.severity === 'error');
  const lines = [];
  for (const r of results) for (const f of r.findings) lines.push(f.severity.toUpperCase().padEnd(7) + ' ' + r.page + ' @' + r.width + 'px  ' + f.check + ': ' + f.detail);
  console.log(lines.join('\n') || 'no findings');
  console.log('\n' + results.length + ' page/width runs, ' + errors.length + ' error(s), ' + (all.length - errors.length) + ' warning(s)' + (reportOnly ? ' (report-only)' : ''));
  if (process.env.GITHUB_STEP_SUMMARY) writeFileSync(process.env.GITHUB_STEP_SUMMARY, '### Layout check\n```\n' + lines.join('\n') + '\n```\n', { flag: 'a' });
  return reportOnly ? 0 : errors.length ? 1 : 0;
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  const args = process.argv.slice(2);
  const cfgPath = args.find((a) => !a.startsWith('--'));
  if (!cfgPath) { console.error('usage: layout-check.mjs <config.json> [--report-only]'); process.exit(2); }
  run(cfgPath, { reportOnly: args.includes('--report-only') || process.env.LAYOUT_REPORT_ONLY === 'true' })
    .then((c) => process.exit(c))
    .catch((e) => { console.error(e.message); process.exit(2); });
}
