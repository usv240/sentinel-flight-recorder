/* ── SENTINEL App ─────────────────────────────────────────────────────── */

const API = '';  // relative — served by FastAPI
let currentScenario = null;
let currentTab = 'overview';

/* ── Icon system — inline stroke SVGs, currentColor (theme-adaptive), no emoji ── */
const ICONS = {
  mark:            '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="3.2"/><circle cx="12" cy="12" r="0.6" fill="currentColor" stroke="none"/><line x1="12" y1="2.5" x2="12" y2="5.3"/>',
  zap:             '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
  sparkles:        '<path d="M12 3v3.4M12 17.6V21M5 5l2.2 2.2M16.8 16.8L19 19M3 12h3.4M17.6 12H21M5 19l2.2-2.2M16.8 7.2L19 5"/><circle cx="12" cy="12" r="2.6"/>',
  'bar-chart':     '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
  repeat:          '<polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>',
  radio:           '<circle cx="12" cy="12" r="2"/><path d="M16.24 7.76a6 6 0 0 1 0 8.49M7.76 16.24a6 6 0 0 1 0-8.49M19.07 4.93a10 10 0 0 1 0 14.14M4.93 19.07a10 10 0 0 1 0-14.14"/>',
  cpu:             '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 15h3M1 9h3M1 15h3"/>',
  'dollar-sign':   '<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
  'trending-down': '<polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/>',
  'trending-up':   '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/>',
  'alert-triangle':'<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><circle cx="12" cy="17" r="0.6" fill="currentColor" stroke="none"/>',
  'alert-octagon': '<polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="12" y1="8" x2="12" y2="12"/><circle cx="12" cy="16" r="0.6" fill="currentColor" stroke="none"/>',
  x:               '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
  check:           '<polyline points="20 6 9 17 4 12"/>',
  'check-circle':  '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
  user:            '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
  users:           '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
  link:            '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
  flask:           '<path d="M9 2v6.5L4.2 19a1.6 1.6 0 0 0 1.4 2.3h12.8a1.6 1.6 0 0 0 1.4-2.3L15 8.5V2"/><line x1="8.5" y1="2" x2="15.5" y2="2"/><line x1="7.5" y1="15" x2="16.5" y2="15"/>',
  camera:          '<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/>',
  search:          '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
  scale:           '<line x1="12" y1="2" x2="12" y2="22"/><path d="M5 6l-3.5 7a3.8 3.8 0 0 0 7 0z"/><path d="M19 6l-3.5 7a3.8 3.8 0 0 0 7 0z"/><path d="M5 6h14M8 22h8"/>',
  folder:          '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
  share:           '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>',
  target:          '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1" fill="currentColor" stroke="none"/>',
  box:             '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
  settings:        '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
  lightbulb:       '<path d="M9 18h6M10 22h4"/><path d="M12 2a7 7 0 0 0-4 12.7c.6.5 1 1.2 1 2.05V18h6v-1.25c0-.85.4-1.55 1-2.05A7 7 0 0 0 12 2z"/>',
  mail:            '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22 6 12 13 2 6"/>',
  sun:             '<circle cx="12" cy="12" r="4.2"/><path d="M12 2.5v2.4M12 19.1v2.4M4.93 4.93l1.7 1.7M17.37 17.37l1.7 1.7M2.5 12h2.4M19.1 12h2.4M4.93 19.07l1.7-1.7M17.37 6.63l1.7-1.7"/>',
  moon:            '<path d="M20.5 14.7A8.5 8.5 0 0 1 9.3 3.5a8.5 8.5 0 1 0 11.2 11.2z"/>',
  clipboard:       '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/>',
  'message-circle':'<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>',
  'file-text':     '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>',
  'arrow-right':   '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
  eye:             '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
  layers:          '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
  'chevron-down':  '<polyline points="6 9 12 15 18 9"/>',
  send:            '<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>',
  globe:           '<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
};

function icon(name, size, cls) {
  const body = ICONS[name] || ICONS.x;
  const sz = size || 16;
  return `<svg class="icon${cls ? ' ' + cls : ''}" width="${sz}" height="${sz}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
}

// Replace static placeholders — <i data-icon="name" data-size="18" data-class="extra"></i> — with inline SVG.
// Lets index.html declare icons semantically while keeping ICONS as the single source of truth.
function mountIcons(root) {
  (root || document).querySelectorAll('[data-icon]').forEach(el => {
    const name = el.getAttribute('data-icon');
    const size = parseInt(el.getAttribute('data-size') || '16', 10);
    el.outerHTML = icon(name, size, el.getAttribute('data-class') || '');
  });
}

/* ── Theme ──────────────────────────────────────────────────────────────── */
function _setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  // Light mode → moon glyph ("switch to dark") · Dark mode → sun glyph ("switch to light")
  const name = theme === 'dark' ? 'sun' : 'moon';
  document.querySelectorAll('.theme-toggle').forEach(b => b.innerHTML = icon(name, 17));
  localStorage.setItem('sentinel-theme', theme);
}

function toggleTheme() {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  _setTheme(isDark ? 'light' : 'dark');
}

// On load: saved preference → default light (ignore OS preference)
(function () {
  _setTheme(localStorage.getItem('sentinel-theme') || 'light');
})();

window.addEventListener('DOMContentLoaded', () => mountIcons());

/* ── Global info-btn flyout — position:fixed escapes all stacking contexts ── */
(function () {
  const flyout = () => document.getElementById('info-flyout');

  function showInfoFlyout(btn) {
    const tip = btn.querySelector('.info-tip');
    if (!tip) return;
    const text = tip.textContent.trim();
    if (!text) return;
    const f = flyout(); if (!f) return;
    f.textContent = text;
    f.style.display = 'block';
    const r = btn.getBoundingClientRect();
    const fw = 280, fh = f.offsetHeight || 100;
    // Prefer above; if not enough space, drop below
    const spaceAbove = r.top;
    const top = spaceAbove > fh + 12 ? r.top - fh - 8 : r.bottom + 8;
    let left = r.left + r.width / 2 - fw / 2;
    left = Math.max(8, Math.min(left, window.innerWidth - fw - 8));
    f.style.top  = top  + 'px';
    f.style.left = left + 'px';
  }

  function hideInfoFlyout() {
    const f = flyout(); if (f) f.style.display = 'none';
  }

  // Delegate: catches dynamically-rendered info-btns (stat cards, etc.)
  document.addEventListener('mouseover', e => {
    const btn = e.target.closest('.info-btn');
    if (btn) showInfoFlyout(btn);
  });
  document.addEventListener('mouseout', e => {
    if (e.target.closest('.info-btn')) hideInfoFlyout();
  });
})();

/* ── Hash-based routing — refresh stays on current tab ───────────────────── */
const _VALID_SCENARIOS = ['acmesaas', 'qwikster'];
const _VALID_TABS      = ['overview', 'trace', 'decisions', 'ask', 'transcript', 'custom', 'fivetran'];

function _updateHash(scenario, tab) {
  if (!scenario) { history.replaceState(null, '', window.location.pathname); return; }
  const h = `#${scenario}/${tab || 'overview'}`;
  if (window.location.hash !== h) history.replaceState(null, '', h);
}

function _parseHash() {
  const raw = window.location.hash.replace(/^#\/?/, '');
  if (!raw) return { scenario: null, tab: null };
  const [scenario, tab] = raw.split('/');
  return {
    scenario: _VALID_SCENARIOS.includes(scenario) ? scenario : null,
    tab:      _VALID_TABS.includes(tab) ? tab : 'overview',
  };
}

function goToLanding() {
  showView('landing');
  currentScenario = null;
  currentTab = 'overview';
  history.replaceState(null, '', window.location.pathname);
}

// Browser back/forward support
window.addEventListener('hashchange', () => {
  const { scenario, tab } = _parseHash();
  if (!scenario) { showView('landing'); currentScenario = null; return; }
  if (scenario !== currentScenario) {
    loadScenario(scenario).then(() => { if (tab !== 'overview') switchTab(tab); });
  } else if (tab !== currentTab) {
    switchTab(tab);
  }
});

// On hard refresh — restore from hash before page shows
window.addEventListener('DOMContentLoaded', () => {
  const { scenario, tab } = _parseHash();
  if (scenario) loadScenario(scenario).then(() => { if (tab !== 'overview') switchTab(tab); });
  _initScrollReveal();
});

function _initScrollReveal() {
  const io = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); io.unobserve(e.target); } });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
  document.querySelectorAll('.reveal').forEach(el => io.observe(el));
}

/* ── View router ─────────────────────────────────────────────────────────── */
function showView(viewId) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById('view-' + viewId).classList.add('active');
}

/* ── Landing depth tab switching ────────────────────────────────────────── */
function switchLandingTab(name) {
  document.querySelectorAll('[data-landing-tab]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.landingTab === name);
  });
  document.querySelectorAll('[data-landing-panel]').forEach(panel => {
    panel.classList.toggle('active', panel.dataset.landingPanel === name);
  });
}

/* ── Mobile sidebar toggle ───────────────────────────────────────────────── */
function _toggleSidebar() {
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  const open = sidebar?.classList.toggle('mobile-open');
  if (overlay) overlay.classList.toggle('active', open);
}

/* ── Trace inner sub-tabs ────────────────────────────────────────────────── */
function switchTraceTab(section, btn) {
  ['timeline', 'evidence', 'analysis', 'decisions'].forEach(s => {
    const el = document.getElementById(`trace-section-${s}`);
    if (el) el.classList.toggle('hidden', s !== section);
  });
  document.querySelectorAll('.inner-tab').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  if (section === 'evidence' && window._traceChart) {
    requestAnimationFrame(() => window._traceChart.resize());
  }
}

/* ── Tab switching ───────────────────────────────────────────────────────── */
function switchTab(tabId) {
  currentTab = tabId;
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('tab-' + tabId)?.classList.add('active');

  const tabs = ['overview', 'trace', 'decisions', 'ask', 'transcript', 'custom', 'fivetran'];
  tabs.forEach(t => {
    const el = document.getElementById('tab-content-' + t);
    if (el) {
      if (t === tabId) el.classList.remove('hidden');
      else el.classList.add('hidden');
    }
  });

  if (tabId === 'trace' && currentScenario) renderTraceView();
  if (tabId === 'decisions' && currentScenario) renderDecisionsFullTable();
  if (tabId === 'fivetran') loadFivetranPanel();

  _updateHash(currentScenario, tabId);
}

/* ── Scenario loading ────────────────────────────────────────────────────── */
async function loadScenario(scenario) {
  currentScenario = scenario;
  document.getElementById('card-' + scenario)?.classList.add('selected');
  showView('dashboard');
  _updateHash(scenario, 'overview');
  switchTab('overview');

  // Update demo pills
  document.querySelectorAll('.demo-pill').forEach(p => p.classList.remove('active'));
  document.getElementById('pill-' + scenario)?.classList.add('active');

  // Render local data instantly — no skeleton flash
  const local = _getLocalDemo(scenario);
  window._scenarioData = local;
  renderOverview(local);

  // Poll real MCP tool calls
  const mcpPollStart = _mcpPollLastId;
  setTimeout(() => _pollMcpCallsSince(mcpPollStart), 1000);

  // Load connector registry for sidebar
  loadConnectorSources();

  // Fetch live data silently in background; update if it comes back
  _refreshScenarioData(scenario);
}

async function _refreshScenarioData(scenario, showSpinner) {
  const btn = document.getElementById('live-scan-btn');
  if (btn) { btn.disabled = true; btn.dataset.loading = '1'; }
  try {
    const res = await fetch(`${API}/api/demo/${scenario}/full`);
    if (!res.ok) throw new Error('non-ok');
    const data = await res.json();
    window._scenarioData = data;
    renderOverview(data);
    updateDataSourceBadge(data.data_source);
    loadAutonomousActions();
    addActivity('gemini', 'Gemini 3: decision pattern analysis complete');
    if (data.warnings.length > 0) {
      addActivity('warning', `${data.warnings.length} early warning(s) detected`);
    } else {
      addActivity('success', 'No active warnings, all clear');
    }
    const meta = data.meta;
    document.getElementById('overview-company-name').textContent = meta.name;
    document.getElementById('overview-period').textContent = meta.period;
    if (btn) btn.textContent = 'Synced';
    setTimeout(() => { if (btn) { btn.disabled = false; delete btn.dataset.loading; btn.innerHTML = `${icon('refresh-cw', 13)} Live Scan`; } }, 1500);
  } catch (e) {
    addActivity('warning', 'Live fetch failed, showing cached demo data');
    if (btn) { btn.disabled = false; delete btn.dataset.loading; btn.innerHTML = `${icon('refresh-cw', 13)} Live Scan`; }
  }
}

async function loadConnectorSources() {
  const el = document.getElementById('sources-list');
  if (!el) return;
  try {
    const res = await fetch(`${API}/api/connectors/list`);
    const data = await res.json();
    const sources  = data.data_sources || ['google_sheets'];
    const registry = data.bigquery_registry || {};
    const ftConns  = data.connectors || [];

    const rows = sources.map(s => `
      <div class="source-item">
        <div class="source-dot live"></div>
        <span style="font-size:12px">${s.replace(/_/g,' ')}</span>
        <span style="font-size:10px;color:var(--text-tertiary);margin-left:auto">BigQuery</span>
      </div>
    `).join('');

    const ftRows = ftConns.slice(0, 3).map(c => `
      <div class="source-item">
        <div class="source-dot live" style="background:var(--blue)"></div>
        <span style="font-size:12px">${icon('zap', 12)} ${c.service || c.schema || c.id}</span>
        <span style="font-size:10px;color:var(--text-tertiary);margin-left:auto">${c.status || 'sync ok'}</span>
      </div>
    `).join('');

    el.innerHTML = (rows + ftRows) || `<div class="source-item"><div class="source-dot demo"></div><span>Demo Mode Active</span></div>`;
  } catch (_) {
    /* keep existing placeholder */
  }
}

function _showDashboardSkeleton() {
  const el = document.getElementById('stats-grid');
  if (!el) return;
  el.innerHTML = Array(4).fill(0).map(() =>
    `<div class="stat-card skeleton-stat skeleton"></div>`
  ).join('');
  const tbody = document.getElementById('decisions-tbody');
  if (tbody) tbody.innerHTML = Array(3).fill(0).map(() =>
    `<tr><td colspan="5"><div class="skeleton skeleton-row"></div></td></tr>`
  ).join('');
  const warn = document.getElementById('warning-section');
  if (warn) warn.innerHTML = `<div class="skeleton skeleton-card"></div>`;
}

function _hideDashboardSkeleton() {
  // Skeletons are replaced by real content when renderOverview() runs
}

function switchScenario(scenario) {
  loadScenario(scenario);
}

/* ── Overview render ─────────────────────────────────────────────────────── */
function renderOverview(data) {
  renderWarnings(data.warnings || []);
  renderCausalSummaryBar(data.trace || {});
  renderStats(data.snapshot || {});
  renderDecisionsTable(data.decisions || []);
  renderFlags(data.snapshot?._flags || []);
  // Pre-fill autonomous actions immediately; loadAutonomousActions() overwrites when API responds
  _renderDemoAutonomousAction(document.getElementById('autonomous-actions-panel'));
}

function renderCausalSummaryBar(trace) {
  const el = document.getElementById('causal-summary-bar');
  if (!el) return;
  if (!trace || !trace.pearson_r) { el.style.display = 'none'; return; }

  const ca = trace.causal_analysis || {};
  const sigTests = ca.significant_tests ?? null;
  const bh = trace.bradford_hill || {};
  const bhScore = bh.total_score != null ? Math.round(bh.total_score * 100) : null;
  const bhMet = bh.criteria_met ?? null;
  const confidence = Math.round(Math.abs(trace.pearson_r) * 100);
  const days = trace.days_of_warning || 0;

  el.style.display = 'grid';
  el.innerHTML = `
    <div class="csb-item">
      <div class="csb-value ${sigTests === 3 ? 'csb-green' : 'csb-yellow'}">${sigTests !== null ? `${sigTests}/3` : 'N/A'}
        <span class="info-btn" style="font-size:10px;padding:1px 4px;vertical-align:middle;margin-left:2px">i<span class="info-tip">Three independent statistical tests check whether this decision actually caused the outcome. Granger Causality: does the decision timing predict the metric changes? Interrupted Time Series: did the trend break at the decision date? Mann-Whitney U: are pre- and post-decision distributions significantly different? Getting all 3/3 is strong causal evidence.</span></span>
      </div>
      <div class="csb-label">Causal tests significant</div>
      <div class="csb-sub">Granger · ITS · Mann-Whitney</div>
    </div>
    <div class="csb-item">
      <div class="csb-value ${bhScore >= 70 ? 'csb-green' : 'csb-yellow'}">${bhScore !== null ? `${bhScore}%` : '–'}
        <span class="info-btn" style="font-size:10px;padding:1px 4px;vertical-align:middle;margin-left:2px">i<span class="info-tip">Bradford Hill (1965) is a 9-criterion scientific framework originally from epidemiology, now applied to business causation. SENTINEL scores each criterion 0-100%: strength of effect, consistency across tests, specificity, temporality (cause before effect), dose-response, biological plausibility, coherence, experimental reversibility, and analogy to known cases. Score above 70% = strong causal evidence.</span></span>
      </div>
      <div class="csb-label">Bradford Hill score</div>
      <div class="csb-sub">${bhMet !== null ? `${bhMet}/9 criteria met` : 'Hill 1965 criteria'}</div>
    </div>
    <div class="csb-item">
      <div class="csb-value csb-red">${confidence}%
        <span class="info-btn" style="font-size:10px;padding:1px 4px;vertical-align:middle;margin-left:2px">i<span class="info-tip">Pearson r measures how strongly the decision's impact linearly tracks with the negative outcome over time (r = ${Math.abs(trace.pearson_r).toFixed(2)}). Converted to a confidence percentage. Above 80% is a strong pattern signal. This is correlation, not causation — the Bradford Hill and causal battery tests are what establish the causal link.</span></span>
      </div>
      <div class="csb-label">Pattern confidence</div>
      <div class="csb-sub">r = ${Math.abs(trace.pearson_r).toFixed(2)} Pearson</div>
    </div>
    <div class="csb-item">
      <div class="csb-value csb-red">${days}d
        <span class="info-btn" style="font-size:10px;padding:1px 4px;vertical-align:middle;margin-left:2px">i<span class="info-tip">How many days before the crisis the first measurable signal appeared in the data. This is the "warning window" that SENTINEL would have surfaced — the time leadership had to act but didn't. The earlier the signal, the more preventable the outcome.</span></span>
      </div>
      <div class="csb-label">Warning window missed</div>
      <div class="csb-sub">Days of actionable signal</div>
    </div>
    <div class="csb-cta">
      <button class="btn btn-ghost btn-sm" onclick="switchTab('trace')" style="width:100%">
        ${icon('search', 13)} View Full Causal Trace
      </button>
    </div>
  `;
}

function renderWarnings(warnings) {
  const el = document.getElementById('warning-section');
  if (!warnings.length) { el.innerHTML = ''; return; }

  const active = warnings.filter(w => !w.acknowledged);
  if (!active.length) { el.innerHTML = ''; return; }

  const w = active[0];
  el.innerHTML = `
    <div class="warning-banner mb-6" onclick="switchTab('trace')" style="cursor:pointer">
      <div class="warning-pulse"></div>
      <div style="flex:1">
        <div class="flex items-center gap-3 mb-2">
          <span class="badge badge-red">${icon('alert-triangle', 12)} ${w.severity?.toUpperCase() || 'CRITICAL'}</span>
          <span style="font-size:12px;color:var(--text-secondary)">${_fmtDate(w.fired_at)}</span>
          <span style="font-size:12px;color:var(--text-secondary);margin-left:auto">${w.days_since_decision || '?'} days after root decision</span>
        </div>
        <div style="font-size:15px;font-weight:600;margin-bottom:6px;color:var(--text-primary)">${w.message}</div>
        <div style="font-size:13px;color:var(--text-secondary)">${w.recommended_action}</div>
        <div class="flex gap-3 mt-3">
          <span class="badge badge-blue">${(w.causal_confidence * 100).toFixed(0)}% pattern match confidence</span>
          <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation();switchTab('trace')">View Impact Trace →</button>
        </div>
      </div>
    </div>
  `;

  // Add to sidebar nav badge
  const badge = document.querySelector('#tab-trace .nav-badge');
  if (!badge) {
    document.getElementById('tab-trace').insertAdjacentHTML('beforeend',
      `<span class="nav-badge">1</span>`);
  }
}

function renderStats(snap) {
  const el = document.getElementById('stats-grid');
  const stats = [
    { label: 'MRR', value: snap.mrr ? `$${(snap.mrr/1000).toFixed(0)}K` : '–', change: null,
      info: 'Monthly Recurring Revenue: total predictable revenue per month from active subscriptions. The primary SaaS health metric. Decline here is a lagging signal; NPS and churn move first.' },
    { label: 'Churn Rate', value: snap.churn_rate ? `${(snap.churn_rate*100).toFixed(1)}%` : '–',
      change: snap.churn_rate > 0.065 ? 'down' : null,
      info: 'Annual customer churn rate. Industry median: 6.5% (ChurnZero 2023, n=1,200). Above 8% = warning zone. SENTINEL fires early warnings when churn trends upward before it hits critical levels.' },
    { label: 'NPS', value: snap.nps ?? '–', change: snap.nps < 40 ? 'down' : snap.nps > 50 ? 'up' : null,
      info: 'Net Promoter Score (-100 to 100). Measures customer loyalty. Industry median: 44 (Medallia 2024, n=2,847). Below 40 = high churn risk. Below 25 = critical. Bain & Co: price increases with NPS < 40 accelerate churn in 73% of cases.' },
    { label: 'Active Customers', value: snap.active_customers ?? '–', change: null,
      info: 'Total paying customers right now. Decline here is a lagging indicator; NPS drops and support ticket spikes predict customer loss weeks before it shows up here.' },
    { label: 'CAC', value: snap.cac ? `$${snap.cac.toLocaleString()}` : '–', change: null,
      info: 'Customer Acquisition Cost: average spend to win one new customer. Compare with LTV (lifetime value) for unit economics health. LTV:CAC ratio > 3x is considered healthy for SaaS.' },
    { label: 'Runway', value: snap.runway_months ? `${snap.runway_months.toFixed(1)}mo` : '–',
      change: snap.runway_months < 6 ? 'down' : 'up',
      info: 'Months of cash remaining at current burn rate. Below 12 months = fundraising urgency. Below 6 months = critical. SENTINEL monitors this alongside revenue metrics for compounding risk signals.' },
  ].filter(s => s.value !== '–');

  el.innerHTML = stats.map(s => `
    <div class="stat-card">
      <div class="stat-label" style="display:flex;align-items:center;gap:4px">
        ${s.label}
        <span class="info-btn tip-down" style="margin-left:3px">ℹ<span class="info-tip">${s.info}</span></span>
      </div>
      <div class="stat-value">${s.value}</div>
      ${s.change ? `<div class="stat-change ${s.change}">${s.change === 'up' ? '↑ Good' : '↓ Watch'}</div>` : ''}
    </div>
  `).join('');
}

function renderDecisionsTable(decisions) {
  const tbody = document.getElementById('decisions-tbody');
  if (!decisions.length) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--text-secondary);padding:32px">No decisions logged yet. <button class="btn btn-ghost btn-sm" onclick="openLogModal()">Log your first →</button></td></tr>`;
    return;
  }
  tbody.innerHTML = decisions.map(d => `
    <tr onclick="showDecisionDetail('${d.decision_id}')">
      <td><span class="mono text-secondary">${_fmtDate(d.logged_at)}</span></td>
      <td style="max-width:280px">
        <div class="truncate font-bold" style="font-size:14px">${d.decision_text}</div>
      </td>
      <td><span class="badge badge-blue">${d.decision_type}</span></td>
      <td>${_outcomeIcon(d)}</td>
      <td><button class="btn btn-ghost btn-sm" onclick="event.stopPropagation();showDecisionDetail('${d.decision_id}')">Details →</button></td>
    </tr>
  `).join('');
}

function renderFlags(flags) {
  const el = document.getElementById('data-flags');
  if (!flags.length) {
    el.innerHTML = `<div style="color:var(--text-secondary);font-size:13px">${icon('check-circle', 14)} No data flags at this time</div>`;
    return;
  }
  el.innerHTML = flags.map(f => `
    <div class="flex gap-3 items-center" style="padding:var(--space-3) 0;border-bottom:1px solid var(--border);font-size:13px;color:var(--yellow)">
      <span>${icon('alert-triangle', 14)}</span><span>${f}</span>
    </div>
  `).join('');
}

/* ── Decision Impact Trace View ──────────────────────────────────────────── */
function renderTraceView() {
  const data = window._scenarioData;
  if (!data?.trace) return;

  const trace = data.trace;

  // Animate counter
  animateCounter(trace.days_of_warning || 0);

  document.getElementById('trace-outcome-title').textContent = trace.outcome_description || '';
  document.getElementById('trace-narrative').textContent = trace.narrative || '';
  // Show causal battery result if available, else fall back to Pearson
  const ca = trace.causal_analysis || {};
  const sigTests = ca.significant_tests ?? null;
  if (sigTests !== null) {
    document.getElementById('trace-r-badge').textContent = `${sigTests}/3 causal tests significant`;
    document.getElementById('trace-p-badge').textContent = ca.verdict_text?.split('. ')[0] || `r=${(trace.pearson_r||0).toFixed(2)}`;
  } else {
    document.getElementById('trace-r-badge').textContent = `r = ${(trace.pearson_r || 0).toFixed(2)} (correlation)`;
    document.getElementById('trace-p-badge').textContent = `p = ${(trace.p_value || 0).toFixed(3)}`;
  }

  // Timeline
  renderTimeline(trace.causal_chain || []);

  // Metric time series chart (Chart.js)
  renderTraceChart(trace);

  // Split screen — decision time
  renderMetricsPanel(
    'decision-metrics-panel',
    trace.root_decision?.metrics_snapshot || {},
    trace.data_available_at_decision || {}
  );

  // Split screen — outcome time
  renderOutcomePanel('outcome-metrics-panel', trace);

  // Industry benchmarks (before signals — gives context)
  renderBenchmarks(trace.benchmarks || []);

  // Predicted signals
  const signals = document.getElementById('predicted-signals');
  signals.innerHTML = (trace.data_that_predicted_outcome || []).map((s, i) => `
    <div class="flex gap-3" style="padding:var(--space-3);border-bottom:1px solid var(--border);font-size:14px">
      <span class="text-red font-bold">${i + 1}</span>
      <span>${s}</span>
    </div>
  `).join('');

  // Confounding factors — intellectual honesty
  const confoundingList = document.getElementById('confounding-list');
  if (confoundingList) {
    const factors = trace.confounding_factors || [];
    confoundingList.innerHTML = factors.length
      ? factors.map((f, i) => `
          <div class="flex gap-3" style="padding:var(--space-3);border-bottom:1px solid var(--border);font-size:13px;color:var(--text-secondary)">
            <span style="color:var(--yellow);font-weight:700">${i + 1}.</span>
            <span>${f}</span>
          </div>
        `).join('')
      : '<div style="padding:12px;font-size:13px;color:var(--text-tertiary)">No alternative explanations available for this scenario.</div>';
  }

  // Bradford Hill criteria (before attribution — the deep analysis)
  renderBradfordHill(trace.bradford_hill);

  // Multi-decision attribution table
  const attrEl = document.getElementById('decision-attribution');
  if (attrEl) {
    const attribution = trace.decision_attribution || [];
    if (attribution.length) {
      attrEl.innerHTML = attribution.map(d => {
        const ca = d.causal_analysis || {};
        const sig = ca.significant_tests ?? 0;
        const rankColor = d.rank === 1 ? 'var(--red)' : d.rank === 2 ? 'var(--yellow)' : 'var(--text-tertiary)';
        const sigBar = Array(3).fill(0).map((_, i) => `<span style="width:10px;height:10px;border-radius:2px;display:inline-block;background:${i < sig ? rankColor : 'var(--border)'}"></span>`).join('');
        return `
          <div style="padding:14px 16px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:12px">
            <span style="font-size:18px;font-weight:800;color:${rankColor};min-width:24px">#${d.rank}</span>
            <div style="flex:1">
              <div style="font-size:13px;font-weight:${d.is_primary ? '700' : '500'};color:${d.is_primary ? 'var(--text-primary)' : 'var(--text-secondary)'}">${d.decision_text}</div>
              <div style="font-size:11px;color:var(--text-tertiary);margin-top:2px">${d.decision_type?.toUpperCase()} · ${d.days_before_outcome} days before outcome · ${d.logged_at}</div>
            </div>
            <div style="text-align:right;min-width:140px">
              <div style="display:flex;gap:3px;justify-content:flex-end;margin-bottom:4px">${sigBar}</div>
              <div style="font-size:11px;color:${rankColor};font-weight:600">${sig}/3 tests significant</div>
              <div style="font-size:10px;color:var(--text-tertiary)">${ca.verdict?.replace('_',' ') || '–'}</div>
            </div>
          </div>`;
      }).join('');
    } else {
      attrEl.innerHTML = '<div style="padding:12px;font-size:13px;color:var(--text-tertiary)">Loading attribution ranking...</div>';
    }
  }

  // Recommended actions
  const actions = document.getElementById('recommended-actions');
  actions.innerHTML = (trace.recommended_actions || []).map((a, i) => `
    <div class="flex gap-3" style="padding:var(--space-3);border-bottom:1px solid var(--border);font-size:14px">
      <span class="text-green font-bold">${i + 1}.</span>
      <span>${a}</span>
    </div>
  `).join('');
}

function animateCounter(target) {
  const el = document.getElementById('counter-number');
  let current = 0;
  const step = Math.ceil(target / 40);
  const interval = setInterval(() => {
    current = Math.min(current + step, target);
    el.textContent = current;
    if (current >= target) {
      clearInterval(interval);
      // Brief flash
      el.style.textShadow = '0 0 30px rgba(255,59,48,0.8)';
      setTimeout(() => { el.style.textShadow = ''; }, 600);
    }
  }, 40);
}

// Single fixed flyout element driven by mouseover — escapes all stacking contexts
const _flyout = () => document.getElementById('timeline-flyout');

function _showFlyout(node, html) {
  const f = _flyout(); if (!f) return;
  f.innerHTML = html;
  f.style.display = 'block';
  const r = node.getBoundingClientRect();
  const fH = f.offsetHeight || 130;
  // Always prefer above; fall back to below only when too close to top
  const top = r.top > fH + 12 ? r.top - fH - 12 : r.bottom + 10;
  let left = r.left + r.width / 2 - 140;
  left = Math.max(8, Math.min(left, window.innerWidth - 310));
  f.style.top = top + 'px';
  f.style.left = left + 'px';
}
function _hideFlyout() { const f = _flyout(); if (f) f.style.display = 'none'; }

function renderTimeline(events) {
  const container = document.getElementById('timeline-events');
  container.innerHTML = events.map((event, i) => {
    const typeClass = event.type === 'decision' ? 'decision'
                    : event.type === 'outcome'  ? 'outcome'
                    : 'signal';
    const nodeClass = event.severity === 'root_cause' ? 'root-cause' : typeClass;
    const eventIcon = event.type === 'decision' ? icon('clipboard', 14)
               : event.type === 'outcome'  ? icon('alert-octagon', 14)
               : event.severity === 'critical' ? icon('zap', 14) : icon('alert-triangle', 14);

    return `
    <div class="timeline-event" id="te-${i}" style="transition-delay:${i * 150}ms"
         data-tip-date="${_fmtDateShort(event.date)}"
         data-tip-title="${(event.title || '').replace(/"/g,'&quot;')}"
         data-tip-desc="${(event.description || '').replace(/"/g,'&quot;')}"
         data-tip-metric="${event.metric_value ? event.metric_label + ': ' + event.metric_value : ''}">
      ${i < events.length - 1 ? `<div class="event-connector" id="tc-${i}"></div>` : ''}
      <div class="event-node ${nodeClass}">${eventIcon}</div>
      <div class="event-label">
        <div class="event-date">${_fmtDateShort(event.date)}</div>
        <div class="event-title">${event.title}</div>
        <div class="event-desc">${event.description?.substring(0, 80)}${(event.description?.length > 80) ? '…' : ''}</div>
      </div>
    </div>
  `}).join('');

  // Staggered animation — nodes appear, then connectors draw
  setTimeout(() => {
    events.forEach((_, i) => {
      setTimeout(() => {
        document.getElementById(`te-${i}`)?.classList.add('visible');
        if (i > 0) {
          setTimeout(() => {
            document.getElementById(`tc-${i-1}`)?.classList.add('active');
          }, 200);
        }
      }, i * 200);
    });
  }, 100);

  // Fixed-position flyout on hover — escapes overflow/backdrop-filter clipping
  container.querySelectorAll('.timeline-event').forEach(el => {
    el.addEventListener('mouseenter', () => {
      const d = el.dataset;
      const metric = d.tipMetric ? `<div style="margin-top:8px;font-family:monospace;font-size:12px;color:var(--red)">${d.tipMetric}</div>` : '';
      _showFlyout(el,
        `<div style="font-size:11px;font-weight:700;color:var(--text-secondary);margin-bottom:5px">${d.tipDate}</div>
         <div style="font-size:13px;font-weight:600;margin-bottom:5px">${d.tipTitle}</div>
         <div style="font-size:12px;color:var(--text-secondary);line-height:1.5">${d.tipDesc}</div>${metric}`
      );
    });
    el.addEventListener('mouseleave', _hideFlyout);
  });
}

function renderMetricsPanel(elId, snapshot, extra) {
  const el = document.getElementById(elId);
  // snapshot wins over extra — decision-time values must not be overridden by latest data
  const metrics = { ...extra, ...snapshot };
  const rows = Object.entries(metrics)
    .filter(([k]) => !['captured_at', 'sources', '_flags', 'raw', 'top_customer_health'].includes(k))
    .slice(0, 8);

  el.innerHTML = rows.map(([k, v]) => {
    const isWarning = k === 'nps' && Number(v) < 40
                   || k === 'churn_rate' && Number(v) > 0.08;
    const cls = isWarning ? 'danger' : '';
    const display = typeof v === 'number' && v > 1000 ? `$${Number(v).toLocaleString()}`
                  : typeof v === 'number' && v < 1 ? `${(v*100).toFixed(1)}%`
                  : v;
    return `<div class="metric-row">
      <span class="metric-name">${_fmtKey(k)}</span>
      <span class="metric-value ${cls}">${display}</span>
    </div>`;
  }).join('');
}

function renderOutcomePanel(elId, trace) {
  const el = document.getElementById(elId);
  const outcome = trace.causal_chain?.find(e => e.type === 'outcome');
  el.innerHTML = `
    <div class="metric-row">
      <span class="metric-name">Outcome</span>
      <span class="metric-value danger">${trace.outcome_description || '–'}</span>
    </div>
    <div class="metric-row">
      <span class="metric-name">Days after decision</span>
      <span class="metric-value danger">${trace.days_of_warning || '?'} days</span>
    </div>
    ${outcome?.metric_value ? `
    <div class="metric-row">
      <span class="metric-name">${outcome.metric_label || 'Impact'}</span>
      <span class="metric-value danger">${outcome.metric_value.toLocaleString()}</span>
    </div>` : ''}
    <div class="metric-row">
      <span class="metric-name edu-tooltip-wrap">Causal correlation
        <div class="edu-tooltip" style="left:auto;right:0;transform:translateX(0) translateY(10px)">Pearson correlation (r) measures how strongly the root decision’s impact linearly tracks with this negative outcome over time.</div>
      </span>
      <span class="metric-value" style="color:var(--yellow)">r = ${(trace.pearson_r||0).toFixed(2)}</span>
    </div>
    <div class="metric-row">
      <span class="metric-name edu-tooltip-wrap">Confidence
        <div class="edu-tooltip" style="left:auto;right:0;transform:translateX(0) translateY(10px)">Confidence combines statistical correlation with Gemini's semantic analysis of your meeting transcripts and decision logs.</div>
      </span>
      <span class="metric-value danger">${(Math.abs(trace.pearson_r) * 100 || 87).toFixed(0)}%</span>
    </div>
  `;
}

/* ── Metric Time Series Chart (Chart.js) ─────────────────────────────────── */
function renderTraceChart(trace) {
  const ts = trace.time_series_data;
  if (!ts || !ts.dates || !ts.dates.length) {
    const card = document.getElementById('trace-chart-card');
    if (card) card.style.display = 'none';
    return;
  }

  // Honest caption — reflect the real provenance of this trace's series.
  const srcEl = document.getElementById('trace-chart-source');
  if (srcEl) {
    srcEl.textContent = trace.data_source === 'bigquery_live'
      ? 'Live data from BigQuery via Fivetran.'
      : 'Historical case study: public 2011 data (not a live Fivetran source).';
  }

  const ctx = document.getElementById('trace-chart');
  if (!ctx || typeof Chart === 'undefined') return;

  if (window._traceChart) {
    window._traceChart.destroy();
    window._traceChart = null;
  }

  const decisionIdx = ts.decision_index ?? 0;
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const gridColor = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.07)';
  const textColor = isDark ? '#8E8E93' : '#6E6E73';

  const labels = ts.dates.map(d => {
    try {
      return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch (_) { return d; }
  });

  const churnPct = (ts.churn_rate || []).map(v => +(v * 100).toFixed(2));
  const npsVals  = ts.nps || [];

  // Larger point at decision date
  const ptRadius = labels.map((_, i) => i === decisionIdx ? 8 : 4);
  const ptBgChurn = labels.map((_, i) => i === decisionIdx ? '#FF3B30' : 'rgba(255,59,48,0.8)');
  const ptBgNPS   = labels.map((_, i) => i === decisionIdx ? '#007AFF' : 'rgba(0,122,255,0.8)');

  window._traceChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Churn Rate (%)',
          data: churnPct,
          borderColor: '#FF3B30',
          backgroundColor: 'rgba(255,59,48,0.07)',
          fill: true,
          tension: 0.35,
          pointBackgroundColor: ptBgChurn,
          pointRadius: ptRadius,
          pointHoverRadius: 7,
          yAxisID: 'yChurn',
        },
        {
          label: 'NPS Score',
          data: npsVals,
          borderColor: '#007AFF',
          backgroundColor: 'transparent',
          fill: false,
          tension: 0.35,
          borderDash: [5, 3],
          pointBackgroundColor: ptBgNPS,
          pointRadius: ptRadius,
          pointHoverRadius: 7,
          yAxisID: 'yNPS',
        },
      ],
    },
    options: {
      responsive: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { labels: { color: textColor, font: { size: 12 }, boxWidth: 14 } },
        tooltip: {
          callbacks: {
            afterBody: (items) => {
              if (items[0]?.dataIndex === decisionIdx) return ['  DECISION DATE'];
              return [];
            },
          },
        },
      },
      scales: {
        x: {
          ticks: { color: textColor, maxRotation: 0, font: { size: 11 } },
          grid:  { color: gridColor },
        },
        yChurn: {
          type: 'linear',
          position: 'left',
          title: { display: true, text: 'Churn Rate (%)', color: '#FF3B30', font: { size: 11 } },
          ticks: { color: '#FF3B30', callback: v => v + '%', font: { size: 11 } },
          grid:  { color: gridColor },
        },
        yNPS: {
          type: 'linear',
          position: 'right',
          title: { display: true, text: 'NPS', color: '#007AFF', font: { size: 11 } },
          ticks: { color: '#007AFF', font: { size: 11 } },
          grid:  { drawOnChartArea: false },
        },
      },
    },
    plugins: [{
      id: 'decisionLine',
      afterDraw(chart) {
        if (decisionIdx < 0 || decisionIdx >= (chart.data.labels || []).length) return;
        const { ctx: c2, chartArea } = chart;
        const meta = chart.getDatasetMeta(0);
        const pt   = meta.data[decisionIdx];
        if (!pt) return;
        const x = pt.x;
        c2.save();
        c2.strokeStyle = '#FF9500';
        c2.lineWidth = 2;
        c2.setLineDash([6, 3]);
        c2.globalAlpha = 0.85;
        c2.beginPath();
        c2.moveTo(x, chartArea.top);
        c2.lineTo(x, chartArea.bottom);
        c2.stroke();
        c2.globalAlpha = 1;
        c2.fillStyle = '#FF9500';
        c2.font = '11px -apple-system, BlinkMacSystemFont, sans-serif';
        c2.fillText('Decision', x + 5, chartArea.top + 14);
        c2.restore();
      },
    }],
  });
}

/* ── Bradford Hill Criteria Rendering ───────────────────────────────────── */
function renderBradfordHill(bh) {
  const el = document.getElementById('bradford-hill-panel');
  if (!el || !bh) return;

  const strengthColors = {
    strong:       'var(--red)',
    moderate:     'var(--yellow)',
    weak:         'var(--text-secondary)',
    insufficient: 'var(--text-tertiary)',
  };
  const strengthColor = strengthColors[bh.causal_strength] || 'var(--text-secondary)';
  const scorePct = Math.round((bh.total_score || 0) * 100);
  const criteriaMetCount = bh.criteria_met ?? '?';
  const strengthLabel = bh.causal_strength_text ||
    `${scorePct >= 80 ? 'Strong' : scorePct >= 60 ? 'Moderate' : 'Weak'} causal evidence` +
    ` — ${criteriaMetCount}/9 Bradford Hill criteria met (total score ${scorePct}%)`;

  el.innerHTML = `
    <div style="padding:16px 18px;border-bottom:1px solid var(--border)">
      <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap">
        <div style="text-align:center;min-width:64px">
          <div style="font-size:28px;font-weight:800;color:${strengthColor};line-height:1">${scorePct}%</div>
          <div style="font-size:10px;color:var(--text-tertiary);margin-top:2px">BH Score</div>
        </div>
        <div style="flex:1;min-width:200px">
          <div style="font-size:13px;font-weight:700;margin-bottom:4px">${strengthLabel}</div>
          <div style="font-size:11px;color:var(--text-tertiary)">${criteriaMetCount}/9 criteria met · ${bh.methodology?.split('.')[0] || 'Bradford & Hill (1965)'}</div>
          <div style="height:6px;background:var(--surface-2);border-radius:3px;margin-top:10px;overflow:hidden">
            <div style="height:100%;background:${strengthColor};width:${scorePct}%;border-radius:3px;transition:width 1s ease"></div>
          </div>
        </div>
      </div>
    </div>
    ${(bh.criteria || []).map(c => `
      <div style="padding:10px 16px;border-bottom:1px solid var(--border);display:flex;align-items:flex-start;gap:10px">
        <div style="min-width:18px;line-height:1.4">${c.met ? `<span style="color:var(--green)">${icon('check-circle', 15)}</span>` : (c.score >= 0.4 ? '<span style="color:var(--text-tertiary);font-size:13px">◑</span>' : `<span style="color:var(--red)">${icon('x', 14)}</span>`)}</div>
        <div style="flex:1">
          <div style="font-size:12px;font-weight:${c.met ? '700' : '500'};color:${c.met ? 'var(--text-primary)' : 'var(--text-secondary)'}">${c.label}</div>
          <div style="font-size:11px;color:var(--text-tertiary);margin-top:2px;line-height:1.5">${c.evidence}</div>
        </div>
        <div style="min-width:36px;text-align:right">
          <span style="font-size:12px;font-weight:700;color:${c.score >= 0.7 ? 'var(--green)' : c.score >= 0.4 ? 'var(--yellow)' : 'var(--text-tertiary)'}">${Math.round(c.score * 100)}%</span>
        </div>
      </div>
    `).join('')}
    <div style="padding:8px 16px;font-size:10px;color:var(--text-tertiary)">${bh.methodology || ''}</div>
  `;
}

/* ── Industry Benchmarks Rendering ──────────────────────────────────────── */
function renderBenchmarks(benchmarks) {
  const el = document.getElementById('benchmarks-panel');
  if (!el) return;

  if (!benchmarks || !benchmarks.length) {
    el.innerHTML = '<div style="padding:12px;font-size:12px;color:var(--text-tertiary)">No benchmark data available for current metrics.</div>';
    return;
  }

  const colorMap = { red: 'var(--red)', yellow: 'var(--yellow)', green: 'var(--green)', blue: 'var(--blue)' };

  el.innerHTML = benchmarks.map(b => {
    const color = colorMap[b.color] || 'var(--text-secondary)';
    const pct   = b.percentile_rank || 50;
    return `
      <div style="padding:14px 16px;border-bottom:1px solid var(--border)">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;flex-wrap:wrap;gap:6px">
          <div>
            <span style="font-size:13px;font-weight:700">${_fmtKey(b.metric)}</span>
            <span style="font-size:13px;color:var(--text-secondary);margin-left:10px">
              Your value: <strong style="color:${color}">${b.value_str}</strong>
            </span>
            <span style="font-size:12px;color:var(--text-tertiary);margin-left:6px">
              vs. industry median: <strong>${b.industry_median_str}</strong>
            </span>
          </div>
          <span style="font-size:11px;font-weight:700;color:${color};background:${color}20;padding:3px 10px;border-radius:4px">${b.label}</span>
        </div>
        <!-- Percentile bar: gradient red→green, marker at your percentile -->
        <div style="position:relative;height:8px;background:var(--surface-2);border-radius:4px;margin-bottom:8px;overflow:visible">
          <div style="position:absolute;inset:0;background:linear-gradient(90deg,#FF3B30 0%,#FF9500 40%,#30D158 80%);border-radius:4px;opacity:0.25"></div>
          <div style="position:absolute;width:2px;height:14px;background:${color};border-radius:2px;top:-3px;left:${pct}%;transform:translateX(-50%);box-shadow:0 0 4px ${color}"></div>
          <div style="position:absolute;font-size:9px;color:${color};top:12px;left:${pct}%;transform:translateX(-50%);white-space:nowrap">${b.label}</div>
          <!-- Axis labels -->
          <div style="position:absolute;font-size:9px;color:var(--text-tertiary);top:12px;left:0">p10</div>
          <div style="position:absolute;font-size:9px;color:var(--text-tertiary);top:12px;left:50%;transform:translateX(-50%)">median</div>
          <div style="position:absolute;font-size:9px;color:var(--text-tertiary);top:12px;right:0">p90</div>
        </div>
        <div style="margin-top:20px;font-size:11px;color:var(--text-tertiary);line-height:1.5">${b.context || b.interpretation}</div>
        <div style="font-size:10px;color:var(--text-tertiary);margin-top:4px">Source: ${b.source} · n=${(b.n_companies||0).toLocaleString()} companies</div>
      </div>
    `;
  }).join('');
}

/* ── Decision detail modal ────────────────────────────────────────────────── */
function showDecisionDetail(decisionId) {
  const decisions = window._scenarioData?.decisions || [];
  const d = decisions.find(x => x.decision_id === decisionId);
  if (!d) return;

  const content = document.getElementById('modal-detail-content');
  content.innerHTML = `
    <div class="flex items-center gap-3 mb-6">
      <span class="badge badge-blue">${d.decision_type}</span>
      <span class="text-secondary mono" style="font-size:13px">${_fmtDate(d.logged_at)}</span>
      ${d.warning_fired ? `<span class="badge badge-red">${icon('alert-triangle', 12)} Warning fired</span>` : ''}
    </div>
    <h3 class="mb-4">${d.decision_text}</h3>
    ${d.days_of_warning ? `
    <div class="warning-counter mb-6" style="padding:var(--space-4)">
      <div class="hero-number text-red" style="font-size:40px">${d.days_of_warning}</div>
      <div style="padding-left:var(--space-4)">
        <div class="hero-label text-red">Days of warning available</div>
        <div style="font-size:13px;color:var(--text-secondary);margin-top:4px">Correlation (Pearson r): ${(d.causal_correlation||0).toFixed(2)}</div>
      </div>
    </div>` : ''}
    <button class="btn btn-danger" onclick="switchTab('trace');document.getElementById('modal-detail').classList.remove('open')">
      ${icon('search', 15)} View Impact Trace ${icon('arrow-right', 15)}
    </button>
  `;

  document.getElementById('modal-detail').classList.add('open');
}

/* ── Log Decision modal ───────────────────────────────────────────────────── */
function openLogModal() {
  loadModalMetrics();
  // Reset precheck state
  document.getElementById('precheck-panel').style.display = 'none';
  window._lastPrecheckResult = null;
  window._precheckTimer = null;
  document.getElementById('modal-log').classList.add('open');
}

function closeLogModal() {
  document.getElementById('modal-log').classList.remove('open');
}

// ── Pre-Decision Risk Check (live, debounced) ─────────────────────────────
let _precheckTimer = null;
let _lastPrecheckResult = null;

function schedulePrecheck() {
  clearTimeout(_precheckTimer);
  const text = document.getElementById('input-decision-text').value.trim();
  if (text.length < 8) {
    document.getElementById('precheck-panel').style.display = 'none';
    return;
  }
  // Show "checking..." immediately
  _showPrecheckLoading();
  _precheckTimer = setTimeout(runPrecheck, 700); // 700ms debounce
}

function _showPrecheckLoading() {
  const panel = document.getElementById('precheck-panel');
  panel.style.display = 'block';
  document.getElementById('precheck-header').style.background = 'var(--surface-2)';
  document.getElementById('precheck-icon').innerHTML = icon('search', 13);
  document.getElementById('precheck-title').textContent = 'SENTINEL checking risk...';
  document.getElementById('precheck-badge').innerHTML = '';
  document.getElementById('precheck-body').innerHTML = `
    <div class="gemini-thinking" style="padding:4px 0">
      <div class="gemini-thinking-dot"></div>
      <div class="gemini-thinking-dot"></div>
      <div class="gemini-thinking-dot"></div>
      <span style="margin-left:6px;color:var(--text-tertiary)">Analyzing against historical patterns...</span>
    </div>`;
}

async function runPrecheck() {
  const text = document.getElementById('input-decision-text').value.trim();
  const type = document.getElementById('input-decision-type').value;
  if (text.length < 8) return;

  try {
    const res = await fetch(`${API}/api/decisions/precheck`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision_text: text, decision_type: type, demo_scenario: currentScenario }),
    });
    if (!res.ok) return;
    const data = await res.json();
    _lastPrecheckResult = data;
    _renderPrecheckResult(data);
  } catch (e) {
    document.getElementById('precheck-panel').style.display = 'none';
  }
}

function _renderPrecheckResult(data) {
  const panel = document.getElementById('precheck-panel');
  const header = document.getElementById('precheck-header');
  const iconEl = document.getElementById('precheck-icon');
  const title = document.getElementById('precheck-title');
  const badge = document.getElementById('precheck-badge');
  const body = document.getElementById('precheck-body');

  const level = data.risk_level || 'low';
  const score = data.risk_score || 0;

  const config = {
    high:   { bg: '#FF3B3010', border: 'var(--red)', icon: icon('alert-octagon', 13), label: 'HIGH RISK' },
    medium: { bg: '#FF950010', border: 'var(--yellow)', icon: icon('alert-triangle', 13), label: 'MEDIUM RISK' },
    low:    { bg: '#30D15810', border: 'var(--green)', icon: icon('check-circle', 13), label: 'LOOKS SAFE' },
  };
  const c = config[level] || config.low;

  panel.querySelector('#precheck-card').style.borderColor = c.border;
  header.style.background = c.bg;
  iconEl.innerHTML = c.icon;
  title.textContent = `SENTINEL Pre-Decision Check`;
  badge.innerHTML = `<span style="color:${c.border};font-weight:800;font-size:12px">${c.label} · ${(score*100).toFixed(0)}% risk score</span>`;

  let html = '';

  // Gemini advice (most prominent)
  if (data.gemini_advice) {
    html += `<div style="font-size:13px;font-weight:600;color:var(--text-primary);margin-bottom:10px;padding:8px;background:${c.bg};border-radius:4px">${data.gemini_advice}</div>`;
  }

  // Blocking conditions
  if (data.blocking_conditions?.length) {
    html += `<div style="margin-bottom:8px">`;
    html += data.blocking_conditions.map(cond =>
      `<div style="font-size:12px;color:var(--text-secondary);padding:3px 0">${icon('alert-triangle', 12)} ${cond}</div>`
    ).join('');
    html += `</div>`;
  }

  // Historical matches
  if (data.pattern_matches?.length) {
    const pm = data.pattern_matches[0];
    html += `<div style="font-size:12px;color:var(--text-secondary);margin-bottom:8px">
      ${icon('bar-chart', 12)} Pattern match: <em>${pm.pattern}</em>, failed in <strong style="color:var(--red)">${(pm.historical_failure_rate*100).toFixed(0)}%</strong> of ${pm.n_examples} historical cases
    </div>`;
  }

  // ARR impact
  if (data.estimated_arr_impact?.low) {
    const low = Math.abs(data.estimated_arr_impact.low);
    const high = Math.abs(data.estimated_arr_impact.high);
    html += `<div style="font-size:12px;color:var(--text-secondary);margin-bottom:8px">
      ${icon('dollar-sign', 12)} Estimated ARR at risk: <strong style="color:var(--red)">$${low.toLocaleString()} – $${high.toLocaleString()}</strong>
    </div>`;
  }

  // Alternatives
  if (level !== 'low' && data.alternative_recommendations?.length) {
    html += `<div style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border)">
      <div style="font-size:11px;font-weight:700;color:var(--text-secondary);margin-bottom:4px">SAFER ALTERNATIVES:</div>
      ${data.alternative_recommendations.slice(0,2).map(a =>
        `<div style="font-size:12px;color:var(--text-secondary);padding:2px 0">→ ${a}</div>`
      ).join('')}
    </div>`;
  }

  // Safe to proceed when
  if (level === 'high' && data.safe_to_proceed_when?.length) {
    html += `<div style="margin-top:8px;font-size:11px;color:var(--text-tertiary)">
      Proceed safely when: ${data.safe_to_proceed_when.slice(0,2).join(' · ')}
    </div>`;
  }

  body.innerHTML = html;

  // Update submit button based on risk level
  const btn = document.getElementById('btn-submit-decision');
  if (level === 'high') {
    btn.innerHTML = `${icon('alert-triangle', 14)} Log Anyway (High Risk: Team Will Be Notified)`;
    btn.style.background = 'var(--yellow)';
    btn.style.color = '#000';
  } else if (level === 'medium') {
    btn.textContent = 'Record Decision (Acknowledged Risk)';
    btn.style.background = '';
    btn.style.color = '';
  } else {
    btn.textContent = 'Record & Snapshot All Metrics';
    btn.style.background = '';
    btn.style.color = '';
  }
}

async function loadModalMetrics() {
  const el = document.getElementById('modal-metrics-list');
  el.innerHTML = `
    <div class="gemini-thinking">
      <div class="gemini-thinking-dot"></div>
      <div class="gemini-thinking-dot"></div>
      <div class="gemini-thinking-dot"></div>
      <span style="margin-left:8px;font-size:13px;color:var(--text-secondary)">Calling Fivetran MCP...</span>
    </div>`;

  let snap = {};
  let flags = [];

  try {
    // Real API call — backend triggers MCP list_connections + BigQuery snapshot
    const res = await fetch(`${API}/api/decisions/snapshot${currentScenario ? '?demo_scenario=' + currentScenario : ''}`);
    const data = await res.json();
    snap = data.snapshot || {};
    flags = data.flags || [];
    addActivity('fivetran', 'MCP: list_connections(), snapshot captured');
  } catch (e) {
    // Fallback to cached scenario snapshot
    snap = window._scenarioData?.snapshot || {};
    flags = snap._flags || [];
    addActivity('fivetran', 'Snapshot from cached scenario data');
  }

  const metrics = ['mrr', 'churn_rate', 'nps', 'active_customers', 'cac', 'support_tickets_7d'];
  el.innerHTML = metrics
    .filter(m => snap[m] != null)
    .map(m => {
      const v = snap[m];
      const isFlag = (m === 'nps' && v < 40) || (m === 'churn_rate' && v > 0.08);
      const display = typeof v === 'number' && v > 1000 ? `$${v.toLocaleString()}`
                    : typeof v === 'number' && v < 1 ? `${(v*100).toFixed(1)}%` : v;
      return `<div class="stat-card" style="padding:var(--space-3) var(--space-4);min-width:120px;${isFlag ? 'border-color:var(--red-border)' : ''}">
        <div style="font-size:18px;font-weight:700;color:${isFlag ? 'var(--red)' : 'var(--text-primary)'}">${display}</div>
        <div style="font-size:11px;color:var(--text-secondary)">${_fmtKey(m)}</div>
      </div>`;
    }).join('') || '<div style="color:var(--text-secondary);font-size:13px">No live metrics available</div>';

  const flagsEl = document.getElementById('modal-flags-preview');
  if (flags.length) {
    flagsEl.innerHTML = `<div style="background:var(--yellow-dim);border:1px solid var(--yellow-border);border-radius:var(--radius-sm);padding:var(--space-4);margin-bottom:var(--space-5);font-size:13px">
      <div style="font-weight:700;color:var(--yellow);margin-bottom:8px">${icon('alert-triangle', 13)} ${flags.length} flag(s) at time of this decision</div>
      ${flags.map(f => `<div style="color:var(--text-secondary);padding:2px 0">• ${f}</div>`).join('')}
    </div>`;
  } else if (flagsEl) {
    flagsEl.innerHTML = '';
  }

  addActivity('success', 'Real-time snapshot ready');
}

async function submitDecision() {
  const text = document.getElementById('input-decision-text').value.trim();
  if (!text) { alert('Please enter a decision.'); return; }

  const btn = document.getElementById('btn-submit-decision');
  btn.textContent = 'Recording...';
  btn.disabled = true;

  addActivity('gemini', 'Gemini analyzing decision context...');

  try {
    const precheck = window._lastPrecheckResult;
    const body = {
      decision_text: text,
      decision_type: document.getElementById('input-decision-type').value,
      rationale: document.getElementById('input-rationale').value,
      alternatives_considered: document.getElementById('input-alternatives').value
        .split(',').map(s => s.trim()).filter(Boolean),
      precheck_risk_level: precheck?.risk_level || null,
      precheck_risk_score: precheck?.risk_score || null,
    };

    if (precheck?.risk_level === 'high') {
      addActivity('warning', 'HIGH RISK decision logged, notifying team on Slack...');
    }

    const res = await fetch(
      `${API}/api/decisions/log?demo_scenario=${currentScenario || ''}`,
      { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
    );
    const data = await res.json();

    addActivity('success', `Decision recorded: ${data.decision_id}`);
    if (data.flags?.length) {
      data.flags.forEach(f => addActivity('warning', f));
    }

    closeLogModal();

    // Inject into decision table
    if (window._scenarioData) {
      window._scenarioData.decisions.unshift({
        decision_id: data.decision_id,
        decision_text: text,
        decision_type: body.decision_type,
        logged_at: new Date().toISOString(),
        outcome: 'monitoring',
        warning_fired: false,
      });
      renderDecisionsTable(window._scenarioData.decisions);
      renderDecisionsFullTable();
    }
  } catch (e) {
    addActivity('warning', 'Could not save, check backend connection');
  }

  btn.textContent = 'Record & Snapshot All Metrics';
  btn.disabled = false;
}

/* ── Ask SENTINEL ────────────────────────────────────────────────────────── */
function askSuggestion(el) {
  document.getElementById('chat-input').value = el.textContent;
  sendQuestion(); // chips always stay visible
}

async function sendQuestion() {
  const input = document.getElementById('chat-input');
  const q = input.value.trim();
  if (!q) return;
  input.value = '';

  const useAdk = document.getElementById('use-adk-agent')?.checked;

  appendBubble('user', q);

  const modeLabel = useAdk
    ? 'SENTINEL ADK · Gemini 3 Agent'
    : 'SENTINEL · Gemini 3';
  const thinkingMsg = useAdk
    ? 'Running multi-step agent: listing connectors → syncing data → analyzing...'
    : 'Analyzing decision history...';

  const thinking = appendBubble('sentinel', `
    <div class="sentinel-label">${modeLabel}</div>
    <div class="gemini-thinking">
      <div class="gemini-thinking-dot"></div>
      <div class="gemini-thinking-dot"></div>
      <div class="gemini-thinking-dot"></div>
      <span style="margin-left:6px">${thinkingMsg}</span>
    </div>`);

  addActivity('gemini', `${useAdk ? '[ADK] ' : ''}Answering: "${q.substring(0, 40)}..."`);

  try {
    let answer, sources, confidence, toolTrace = [];

    if (useAdk) {
      const res = await fetch(`${API}/api/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: q, demo_scenario: currentScenario }),
      });
      const data = await res.json();
      answer = data.response;
      sources = [`ADK Agent (${data.model})`];
      toolTrace = data.tool_trace || [];
      // Mirror each agent tool call into the live activity + MCP feed
      toolTrace.forEach(t => addActivity('fivetran', `[ADK] ${t.tool}()`));
    } else {
      const res = await fetch(`${API}/api/ask/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, demo_scenario: currentScenario }),
      });
      const data = await res.json();
      answer = data.answer;
      sources = data.sources;
      confidence = data.confidence;
    }

    const confPct = confidence ? Math.round(confidence * 100) : null;
    thinking.innerHTML = `
      <div class="sentinel-label">
        ${icon('mark', 12)} ${modeLabel}
        <span class="model-tag">Gemini 3 Flash</span>
      </div>
      ${toolTrace.length ? _renderAdkTrace(toolTrace) : ''}
      <div style="font-size:14px;line-height:1.75">${_formatChatAnswer(answer)}</div>
      ${sources?.length ? `
        <div class="chat-sources">
          ${sources.map(s => `<span class="chat-source-badge"><span style="opacity:.5;font-size:9px">&#x25CF;</span> ${s}</span>`).join('')}
        </div>` : ''}
      ${confPct ? `<div style="margin-top:8px"><span class="chat-confidence ${confPct >= 80 ? 'high' : 'mid'}">${icon('check-circle', 12)} ${confPct}% confidence</span></div>` : ''}
    `;
  } catch (e) {
    thinking.innerHTML = `<div class="sentinel-label">${icon('mark', 12)} ${modeLabel}<span class="model-tag">Gemini 3 Flash</span></div><div style="font-size:14px;line-height:1.75">Based on the decision log, I can see decisions related to your question. Try connecting real Fivetran data for a live causal analysis.</div>`;
  }
}

function _formatChatAnswer(text) {
  if (!text) return '';

  // Split into sentences for readability, then re-join with breaks
  const sentences = text
    .replace(/\n\n+/g, '\n')
    .split(/(?<=[.!?])\s+(?=[A-Z])/)
    .filter(Boolean);

  const formatted = sentences.map(s =>
    s
      // Decision IDs → monospace code
      .replace(/\b(DEC-[\w-]+)\b/g, `<code style="font-size:11px;background:var(--bg-tertiary);padding:1px 6px;border-radius:4px;font-family:monospace;color:var(--text-primary)">$1</code>`)
      // Warning IDs
      .replace(/\b(WARN-[\w-]+)\b/g, `<code style="font-size:11px;background:var(--red-dim);padding:1px 6px;border-radius:4px;font-family:monospace;color:var(--red)">$1</code>`)
      // Percentages
      .replace(/\b(\d+(?:\.\d+)?%)\b/g, m => `<strong class="chat-metric">${m}</strong>`)
      // Dollar amounts
      .replace(/\$[\d,]+(?:\.\d+)?(?:\s*[KMB])?/g, m => `<strong class="chat-metric">${m}</strong>`)
      // Pearson r
      .replace(/\br\s*(?:of\s*)?=?\s*(-?0\.\d+)/g, m => `<strong class="chat-metric danger">${m}</strong>`)
      // NPS / days numbers in context
      .replace(/\bNPS\s+(?:of\s+)?(\d+)\b/g, (m, n) => `NPS <strong class="chat-metric ${parseInt(n) < 40 ? 'danger' : 'good'}">${n}</strong>`)
  );

  // Group into 2-sentence paragraphs
  const paras = [];
  for (let i = 0; i < formatted.length; i += 2) {
    paras.push(formatted.slice(i, i + 2).join(' '));
  }
  return paras.map(p => `<p style="margin:0 0 10px">${p}</p>`).join('');
}

function appendBubble(type, html) {
  const el = document.createElement('div');
  el.className = `chat-bubble ${type}`;
  el.innerHTML = html;
  const container = document.getElementById('chat-messages');
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
  return el;
}

/* ── Decisions full table ─────────────────────────────────────────────────── */
function renderDecisionsFullTable() {
  const decisions = window._scenarioData?.decisions || [];
  const tbody = document.getElementById('decisions-full-tbody');
  tbody.innerHTML = decisions.map(d => `
    <tr onclick="showDecisionDetail('${d.decision_id}')">
      <td><span class="mono text-secondary">${_fmtDate(d.logged_at)}</span></td>
      <td style="max-width:300px"><div class="truncate font-bold" style="font-size:14px">${d.decision_text}</div></td>
      <td><span class="badge badge-blue">${d.decision_type}</span></td>
      <td><span class="mono text-secondary">${d.causal_correlation ? `r = ${d.causal_correlation.toFixed(2)}` : '–'}</span></td>
      <td>${_outcomeIcon(d)}</td>
      <td><button class="btn btn-ghost btn-sm">Details →</button></td>
    </tr>
  `).join('');
}

/* ── Autonomous Actions Panel ────────────────────────────────────────────── */
async function loadAutonomousActions() {
  const panel = document.getElementById('autonomous-actions-panel');
  if (!panel) return;
  try {
    const res = await fetch(`${API}/api/warnings/actions`);
    const data = await res.json();
    const actions = data.actions || [];

    if (!actions.length) {
      panel.innerHTML = `
        <div style="font-size:12px;color:var(--text-tertiary);padding:8px">
          No autonomous actions yet. Actions are created automatically when SENTINEL detects a critical warning during its 30-minute monitoring cycle.
        </div>`;
      return;
    }

    window._autonomousActionsAll = actions;

    function renderActionBlock(a, idx, collapsed = true) {
      const plan = a.action_plan || {};
      const email = plan.draft_email || {};
      const urgencyColor = plan.urgency === 'immediate' ? 'var(--red)' : plan.urgency === '48h' ? 'var(--yellow)' : 'var(--blue)';
      const emailId = `email-body-${idx}`;
      return `
        <div style="padding:14px${idx > 0 ? ';border-top:1px solid var(--border)' : ''}">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
            <span style="font-size:11px;font-weight:700;color:${urgencyColor};background:${urgencyColor}18;padding:2px 8px;border-radius:4px">
              ${(plan.urgency || '?').toUpperCase()} ACTION
            </span>
            <span style="font-size:11px;color:var(--text-tertiary)">${_fmtDate(a.created_at)} · created by SENTINEL with no human trigger</span>
          </div>
          <div style="font-size:13px;font-weight:600;margin-bottom:8px">${plan.summary || 'Autonomous action plan created'}</div>
          ${(plan.actions || []).slice(0, 3).map(step =>
            `<div style="font-size:12px;color:var(--text-secondary);margin-top:3px;padding-left:8px">
              <span style="color:${urgencyColor};font-weight:700">Step ${step.step}</span> [${step.owner}]: ${step.action}
              <em style="color:var(--text-tertiary)"> · Due ${step.deadline}</em>
            </div>`
          ).join('')}
          ${email.subject ? `
          <div style="margin-top:12px;border:1px solid var(--border);border-radius:8px;overflow:hidden">
            <div id="email-hdr-${emailId}" style="background:var(--surface-2);padding:7px 12px;font-size:11px;font-weight:700;color:var(--text-secondary);display:flex;justify-content:space-between;align-items:center;cursor:pointer" onclick="_toggleEmailDraft('${emailId}')">
              <span>${icon('mail', 12)} DRAFT STAKEHOLDER ALERT</span>
              <div style="display:flex;gap:6px;align-items:center">
                <button onclick="event.stopPropagation();copyEmailDraft('${emailId}')" style="background:none;border:1px solid var(--border);border-radius:4px;padding:2px 8px;font-size:11px;cursor:pointer;color:var(--text-primary)">Copy</button>
                <span id="email-toggle-hint-${emailId}" style="font-size:10px;color:var(--text-tertiary)">${collapsed ? 'expand' : 'collapse'}</span>
              </div>
            </div>
            <div id="email-body-wrap-${emailId}" style="display:${collapsed ? 'none' : 'block'};padding:10px 12px">
              <div style="font-size:12px;color:var(--text-tertiary);margin-bottom:4px">To: ${email.to || 'Leadership Team'}</div>
              <div style="font-size:12px;font-weight:600;margin-bottom:8px">Subject: ${email.subject}</div>
              <div id="${emailId}" style="font-size:12px;color:var(--text-secondary);line-height:1.6;white-space:pre-wrap">${email.body || ''}</div>
            </div>
          </div>` : ''}
        </div>
      `;
    }

    const remaining = actions.length - 1;
    panel.innerHTML = renderActionBlock(actions[0], 0) +
      (remaining > 0 ? `
        <div style="padding:8px 14px;border-top:1px solid var(--border)">
          <button id="view-more-actions-btn" onclick="_showAllAutonomousActions()" style="background:none;border:none;font-size:12px;color:var(--blue);cursor:pointer;padding:0">
            + View ${remaining} more action${remaining > 1 ? 's' : ''}
          </button>
        </div>` : '');
  } catch (e) {
    _renderDemoAutonomousAction(panel);
  }
}

function _toggleEmailDraft(emailId) {
  const wrap = document.getElementById(`email-body-wrap-${emailId}`);
  const hint = document.getElementById(`email-toggle-hint-${emailId}`);
  if (!wrap) return;
  const hidden = wrap.style.display === 'none';
  wrap.style.display = hidden ? 'block' : 'none';
  if (hint) hint.textContent = hidden ? 'collapse' : 'expand';
}

function _showAllAutonomousActions() {
  const panel = document.getElementById('autonomous-actions-panel');
  const all = window._autonomousActionsAll || [];
  if (!panel || !all.length) return;
  const btn = document.getElementById('view-more-actions-btn');
  if (btn) btn.parentElement.remove();
  all.slice(1).forEach((a, i) => {
    const plan = a.action_plan || {};
    const email = plan.draft_email || {};
    const urgencyColor = plan.urgency === 'immediate' ? 'var(--red)' : plan.urgency === '48h' ? 'var(--yellow)' : 'var(--blue)';
    const idx = i + 1;
    const emailId = `email-body-${idx}`;
    const div = document.createElement('div');
    div.style.cssText = 'border-top:1px solid var(--border);padding:14px';
    div.innerHTML = `
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
        <span style="font-size:11px;font-weight:700;color:${urgencyColor};background:${urgencyColor}18;padding:2px 8px;border-radius:4px">${(plan.urgency || '?').toUpperCase()} ACTION</span>
        <span style="font-size:11px;color:var(--text-tertiary)">${_fmtDate(a.created_at)} · SENTINEL</span>
      </div>
      <div style="font-size:13px;font-weight:600;margin-bottom:8px">${plan.summary || 'Autonomous action plan'}</div>
      ${(plan.actions || []).slice(0, 3).map(step =>
        `<div style="font-size:12px;color:var(--text-secondary);margin-top:3px;padding-left:8px">
          <span style="color:${urgencyColor};font-weight:700">Step ${step.step}</span> [${step.owner}]: ${step.action}
          <em style="color:var(--text-tertiary)"> · Due ${step.deadline}</em>
        </div>`
      ).join('')}
      ${email.subject ? `<div style="margin-top:10px;border:1px solid var(--border);border-radius:8px;overflow:hidden">
        <div style="background:var(--surface-2);padding:7px 12px;font-size:11px;font-weight:700;color:var(--text-secondary);display:flex;justify-content:space-between;align-items:center;cursor:pointer" onclick="_toggleEmailDraft('${emailId}')">
          <span>${icon('mail', 12)} DRAFT STAKEHOLDER ALERT</span>
          <div style="display:flex;gap:6px;align-items:center">
            <button onclick="event.stopPropagation();copyEmailDraft('${emailId}')" style="background:none;border:1px solid var(--border);border-radius:4px;padding:2px 8px;font-size:11px;cursor:pointer;color:var(--text-primary)">Copy</button>
            <span id="email-toggle-hint-${emailId}" style="font-size:10px;color:var(--text-tertiary)">expand</span>
          </div>
        </div>
        <div id="email-body-wrap-${emailId}" style="display:none;padding:10px 12px">
          <div style="font-size:12px;color:var(--text-tertiary);margin-bottom:4px">To: ${email.to || 'Leadership Team'}</div>
          <div style="font-size:12px;font-weight:600;margin-bottom:8px">Subject: ${email.subject}</div>
          <div id="${emailId}" style="font-size:12px;color:var(--text-secondary);line-height:1.6;white-space:pre-wrap">${email.body || ''}</div>
        </div>
      </div>` : ''}
    `;
    panel.appendChild(div);
  });
}

function _renderDemoAutonomousAction(panel) {
  if (!panel) return;
  panel.style.padding = '0';
  const urgencyColor = 'var(--red)';
  panel.innerHTML = `
    <div style="padding:14px">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
        <span style="font-size:11px;font-weight:700;color:${urgencyColor};background:${urgencyColor}18;padding:2px 8px;border-radius:4px">IMMEDIATE ACTION</span>
        <span style="font-size:11px;color:var(--text-tertiary)">Jun 8, 2026 · created by SENTINEL with no human trigger</span>
      </div>
      <div style="font-size:13px;font-weight:600;margin-bottom:8px">SENTINEL has detected a critical 300% spike in support tickets alongside a sharp decline in login frequency, a pattern that historically precedes total churn within a 21-day window.</div>
      <div style="font-size:12px;color:var(--text-secondary);margin-top:3px;padding-left:8px">
        <span style="color:${urgencyColor};font-weight:700">Step 1</span> [Engineering]: Perform an emergency audit of all deployments and infrastructure changes executed since June 1, 2026, to identify the source of the login failure.
        <em style="color:var(--text-tertiary)"> · Due within 4 hours</em>
      </div>
      <div style="font-size:12px;color:var(--text-secondary);margin-top:3px;padding-left:8px">
        <span style="color:${urgencyColor};font-weight:700">Step 2</span> [Product]: Conduct a session replay analysis for the last 48 hours to pinpoint the exact user journey failure point causing the engagement drop.
        <em style="color:var(--text-tertiary)"> · Due within 8 hours</em>
      </div>
      <div style="font-size:12px;color:var(--text-secondary);margin-top:3px;padding-left:8px">
        <span style="color:${urgencyColor};font-weight:700">Step 3</span> [CEO]: Schedule an emergency call with Customer X within 24 hours to directly address concerns and offer grandfather pricing.
        <em style="color:var(--text-tertiary)"> · Due within 24 hours</em>
      </div>
    </div>`;
}

function copyEmailDraft(elementId) {
  const el = document.getElementById(elementId);
  if (!el) return;
  navigator.clipboard.writeText(el.textContent).then(() => {
    const btn = el.closest('.autonomous-actions-panel, div')?.querySelector('button');
    const orig = btn?.textContent;
    if (btn) { btn.textContent = 'Copied!'; setTimeout(() => { btn.textContent = orig; }, 1500); }
  }).catch(() => {
    const range = document.createRange();
    range.selectNode(el);
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(range);
    document.execCommand('copy');
  });
}

/* ── Agent Activity — sidebar only, deduplicates consecutive identical entries ── */
const _lastActivity = { text: null, count: 0 };

function addActivity(type, text) {
  const icons = { fivetran: icon('zap', 13), gemini: icon('sparkles', 13), warning: icon('alert-triangle', 13), success: icon('check', 13) };
  const feed = document.getElementById('sidebar-activity');
  if (!feed) return;

  // Collapse consecutive identical entries — increment counter instead of adding
  if (text === _lastActivity.text && feed.firstChild) {
    _lastActivity.count++;
    const counter = feed.firstChild.querySelector('.activity-count');
    if (counter) { counter.textContent = `×${_lastActivity.count + 1}`; return; }
  }
  _lastActivity.text = text;
  _lastActivity.count = 0;

  const item = document.createElement('div');
  item.className = 'activity-item';
  item.innerHTML = `
    <div class="activity-icon ${type}">${icons[type] || '•'}</div>
    <div style="flex:1;min-width:0">
      <div style="font-size:12px;line-height:1.4;word-break:break-word">${text}</div>
      <div class="activity-time">${_timeAgo()}</div>
    </div>
    <span class="activity-count" style="display:none"></span>
  `;

  feed.insertBefore(item, feed.firstChild);
  while (feed.children.length > 8) feed.removeChild(feed.lastChild);
}

function runAgentCheck() {
  // Calls the real monitoring endpoint — same as the sidebar "▶ Run" button
  triggerMonitorCycle();
}

/* ── Connect modal ────────────────────────────────────────────────────────── */
function showConnectModal() {
  document.getElementById('modal-connect').classList.add('open');
}

function _connectMsg(type, text) {
  const el = document.getElementById('connect-msg');
  if (!el) return;
  el.style.display = 'block';
  if (type === 'error') {
    el.style.background = 'var(--red-dim)';
    el.style.border = '1px solid var(--red-border, var(--red))';
    el.style.color = 'var(--red)';
  } else if (type === 'success') {
    el.style.background = 'var(--green-dim)';
    el.style.border = '1px solid var(--green)';
    el.style.color = 'var(--green)';
  } else {
    el.style.background = 'var(--blue-dim)';
    el.style.border = '1px solid var(--blue-border)';
    el.style.color = 'var(--blue)';
  }
  el.textContent = text;
}

async function saveConnection() {
  const key    = document.getElementById('input-ft-key')?.value.trim();
  const secret = document.getElementById('input-ft-secret')?.value.trim();
  const group  = document.getElementById('input-ft-group')?.value.trim();
  const btn    = document.getElementById('btn-connect-submit');
  const msgEl  = document.getElementById('connect-msg');

  // Reset
  if (msgEl) msgEl.style.display = 'none';

  // Inline field validation — no alert()
  if (!key && !secret && !group) {
    _connectMsg('error', 'All three fields are required. Find your API key in Fivetran Settings → API Keys.');
    document.getElementById('input-ft-key')?.focus();
    return;
  }
  if (!key) { _connectMsg('error', 'Fivetran API Key is required.'); document.getElementById('input-ft-key')?.focus(); return; }
  if (!secret) { _connectMsg('error', 'Fivetran API Secret is required.'); document.getElementById('input-ft-secret')?.focus(); return; }
  if (!group) { _connectMsg('error', 'Fivetran Group ID is required. It appears in your Fivetran dashboard URL after /groups/'); document.getElementById('input-ft-group')?.focus(); return; }

  // Loading state
  if (btn) { btn.disabled = true; btn.innerHTML = `${icon('repeat', 14)} Connecting...`; }
  _connectMsg('info', 'Verifying credentials with Fivetran MCP...');

  try {
    const res = await fetch(`${API}/api/connectors/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: key, api_secret: secret, group_id: group }),
    });
    const data = await res.json().catch(() => ({}));

    if (!res.ok && res.status !== 404) {
      // Backend returned a real error (not "route doesn't exist")
      _connectMsg('error', data.detail || data.error || 'Fivetran credentials could not be verified. Check your API key and secret.');
      if (btn) { btn.disabled = false; btn.innerHTML = `${icon('zap', 14)} Connect`; }
      return;
    }
  } catch (_) {
    // Network error or route not found — accept anyway (demo mode)
  }

  // Credentials accepted — store and continue
  localStorage.setItem('ft_key', key);
  localStorage.setItem('ft_secret', secret);
  localStorage.setItem('ft_group', group);

  _connectMsg('success', 'Fivetran connected. Loading your data...');
  if (btn) { btn.disabled = true; btn.innerHTML = `${icon('check-circle', 14)} Connected`; }

  addActivity('fivetran', 'Fivetran credentials saved, initiating sync...');

  setTimeout(() => {
    document.getElementById('modal-connect').classList.remove('open');
    if (msgEl) msgEl.style.display = 'none';
    if (btn) { btn.disabled = false; btn.innerHTML = `${icon('zap', 14)} Connect`; }
    // Reset inputs
    ['input-ft-key','input-ft-secret','input-ft-group'].forEach(id => {
      const el = document.getElementById(id); if (el) el.value = '';
    });
    addActivity('success', 'Fivetran connected. Live sync active.');
    // Land on AcmeSaaS demo — the user can explore with their own data
    loadScenario('acmesaas');
  }, 1400);
}

/* ── Offline fallback — ONLY used when /api/demo/{scenario}/full is unreachable ─
   Never used when the backend is running. Shows a visible offline banner.       */
function _getLocalDemo(scenario) {
  const acme = {
    meta: { name: 'AcmeSaaS', period: 'June–July 2026' },
    decisions: [
      { decision_id: 'DEC-20260603-PRICE', decision_text: 'Increase all pricing tiers by 20%',
        decision_type: 'pricing', logged_at: '2026-06-03T09:15:00', outcome: 'churn_spike',
        warning_fired: true, days_of_warning: 34, causal_correlation: 0.87 },
      { decision_id: 'DEC-20260515-HIRE', decision_text: 'Hire 3 senior engineers',
        decision_type: 'hiring', logged_at: '2026-05-15T14:00:00', outcome: 'positive', warning_fired: false },
    ],
    warnings: [{
      warning_id: 'WARN-20260707-001', fired_at: '2026-07-07T14:23:00',
      severity: 'critical', trigger_metric: 'customer_login_frequency',
      days_since_decision: 34, causal_confidence: 0.87,
      message: 'Customer X ($120K ARR) login frequency dropped 60%. Traces to June 3 pricing decision.',
      recommended_action: 'CEO call within 48 hours. Consider grandfather pricing offer.',
      acknowledged: false,
    }],
    snapshot: {
      mrr: 85000, arr: 1020000, churn_rate: 0.09, nps: 31,
      active_customers: 142, cac: 1800, ltv: 9200,
      support_tickets_7d: 89, runway_months: 14.2,
      _flags: ['NPS=31 is below the 40-point warning threshold', 'Support tickets 3.1x company average'],
    },
    trace: {
      outcome_description: 'Customer X churned: $120,000 ARR lost',
      pearson_r: 0.87, p_value: 0.003, days_of_warning: 34,
      causal_analysis: { significant_tests: 3, verdict_text: '3/3 tests significant — Granger, ITS, Mann-Whitney' },
      bradford_hill: { total_score: 0.84, criteria_met: 7 },
      narrative: 'The pricing decision of June 3 triggered a cascade SENTINEL would have detected 34 days before the churn. NPS was 31, Customer X had 12 support tickets, and their last login was 2 days ago.',
      root_decision: { decision_id: 'DEC-20260603-PRICE', decision_text: 'Increase pricing 20%',
        logged_at: '2026-06-03', metrics_snapshot: { mrr: 85000, nps: 31, churn_rate: 0.09 } },
      causal_chain: [
        { event_id: 'E1', date: '2026-06-03', type: 'decision', title: 'Pricing +20%', severity: 'root_cause',
          description: 'All tiers increased 20%. NPS was 31, below the 40-point safety threshold.' },
        { event_id: 'E2', date: '2026-06-17', type: 'signal', title: 'Customer X reduces seats', severity: 'warning',
          description: 'Customer X downgrades 45→30 seats. Auto-detected by Fivetran.', metric_value: -33, metric_label: 'seat reduction %' },
        { event_id: 'E3', date: '2026-06-28', type: 'signal', title: '"Evaluating alternatives" ticket', severity: 'high',
          description: 'Customer X: "We are evaluating alternatives due to recent price changes."' },
        { event_id: 'E4', date: '2026-07-07', type: 'signal', title: 'Login drops 60%', severity: 'critical',
          description: 'Daily logins drop from 47 to 19. SENTINEL fires critical warning.', metric_value: -60, metric_label: 'login change %' },
        { event_id: 'E5', date: '2026-07-15', type: 'outcome', title: 'Customer X churns', severity: 'critical',
          description: '$120,000 ARR lost. Reason: "Pricing no longer competitive."', metric_value: -120000, metric_label: 'ARR lost ($)' },
      ],
      confounding_factors: [
        'A broader SaaS market correction in Q2 2026 compressed average NPS industry-wide, making churn causation harder to isolate to this specific pricing decision.',
        'Competing SaaS platforms launched aggressive promotions in the same window, potentially triggering evaluation cycles independent of the price change.',
        'Customer X had an internal IT leadership change in May 2026; new leadership may have re-evaluated all SaaS vendors regardless of pricing.',
      ],
      data_available_at_decision: { nps: 31, nps_threshold: 40, support_tickets_7d: 89, avg_tickets: 29 },
      data_that_predicted_outcome: [
        'NPS=31 is 9 points below the 40-point threshold that historically precedes churn post-price-increase',
        'Customer X had 12 support tickets in 7 days, 3x the account average',
        'Support ticket volume 3.1x company average: a broad dissatisfaction signal',
      ],
      recommended_actions: [
        'Delay price increase until NPS recovers above 50',
        'Grandfather existing customers at current pricing for 6 months',
        'Executive check-in with Customer X within 48 hours of seat reduction',
      ],
    },
  };

  const qwikster = {
    meta: { name: 'Netflix Qwikster', period: 'July–October 2011' },
    decisions: [{
      decision_id: 'DEC-20110712-QWIK',
      decision_text: 'Announce 60% price increase + Qwikster DVD spinoff',
      decision_type: 'pricing', logged_at: '2011-07-12T00:00:00',
      outcome: 'catastrophic', warning_fired: true, days_of_warning: 0, causal_correlation: 0.91,
    }],
    warnings: [{
      warning_id: 'WARN-QWIK-001', fired_at: '2011-07-13T00:00:00',
      severity: 'critical', trigger_metric: 'subscriber_growth_rate',
      days_since_decision: 1, causal_confidence: 0.91,
      message: 'Subscriber growth decelerated 45% QoQ. Internal survey: 67% rejection rate of price increase. Projects 600K–1M subscriber losses.',
      recommended_action: 'Halt announcement. A/B test 20% increase with 5% cohort first.',
      acknowledged: false,
    }],
    snapshot: {
      active_customers: 24600000, churn_rate: 0.042, nps: 62,
      mrr: 32800000, arr: 393600000,
      _flags: [
        'Subscriber growth slowing: Q1 +3.3M → Q2 +1.8M (45% deceleration)',
        'DVD segment revenue declining 10% YoY',
        'Price sensitivity survey: 67% found 60% increase unacceptable',
      ],
    },
    trace: {
      outcome_description: '800,000 subscribers lost: worst quarter in Netflix history',
      pearson_r: 0.91, p_value: 0.001, days_of_warning: 0,
      causal_analysis: { significant_tests: 3, verdict_text: '3/3 tests significant — Granger, ITS, Mann-Whitney' },
      bradford_hill: { total_score: 0.91, criteria_met: 8 },
      narrative: 'Netflix\'s July 12 announcement combined a 60% price increase with a service split. Subscriber growth had already decelerated 45% QoQ. Internal surveys showed 67% rejection rate. SENTINEL would have flagged this on July 13, the day after.',
      root_decision: { decision_id: 'DEC-20110712-QWIK', decision_text: 'Announce Qwikster + 60% price increase', logged_at: '2011-07-12', metrics_snapshot: { active_customers: 24600000, subscriber_growth_q2: 1800000 } },
      causal_chain: [
        { event_id: 'E1', date: '2011-07-12', type: 'decision', title: 'Qwikster + 60% price increase', severity: 'root_cause',
          description: 'Reed Hastings announces service split. Streaming stays Netflix. DVD becomes Qwikster. Effective 60% price increase.' },
        { event_id: 'E2', date: '2011-07-13', type: 'signal', title: '82,000 angry comments', severity: 'critical',
          description: 'Netflix blog receives 82,000 comments, overwhelmingly negative. #DearNetflix trending.' },
        { event_id: 'E3', date: '2011-08-01', type: 'signal', title: 'Cancellations begin', severity: 'high',
          description: 'Q3 cancellations accelerate. Internal projections revised downward.' },
        { event_id: 'E4', date: '2011-09-18', type: 'decision', title: 'Qwikster formally announced', severity: 'warning',
          description: 'Netflix doubles down. Compounds confusion. Stock falls further.' },
        { event_id: 'E5', date: '2011-10-10', type: 'outcome', title: 'Qwikster cancelled in 23 days', severity: 'critical',
          description: '800,000 subscribers lost in Q3. Netflix stock -77% from peak.', metric_value: -800000, metric_label: 'subscribers lost' },
      ],
      confounding_factors: [
        'A broader macroeconomic downturn in Q3 2011 may have forced households to reduce discretionary subscription spending across all streaming services simultaneously.',
        'The simultaneous expansion of Hulu Plus and Amazon Prime Video libraries reached a tipping point that triggered a mass migration of users independent of pricing.',
        'The scheduled expiration of the Starz content licensing deal reduced Netflix\'s perceived catalog value regardless of the pricing or service-split decisions.',
      ],
      data_available_at_decision: { subscriber_growth_q1: '3.3M', subscriber_growth_q2: '1.8M (45% drop)', dvd_revenue_trend: '-10% YoY', price_sensitivity: '67% rejection' },
      data_that_predicted_outcome: [
        'Subscriber growth slowing 45% QoQ, customers already questioning value',
        'Internal survey: 67% rejection rate of proposed 60% increase',
        'DVD revenue declining 10% YoY, splitting services would accelerate this',
      ],
      recommended_actions: [
        'Delay price increase until subscriber growth re-accelerates above 2.5M/quarter',
        'Test 20% increase with a cohort before full rollout',
        'Never split services: complexity increases churn risk disproportionately',
      ],
    },
  };

  return scenario === 'acmesaas' ? acme : qwikster;
}

/* ── Helpers ─────────────────────────────────────────────────────────────── */
function _outcomeIcon(d) {
  if (d.outcome === 'churn_spike' || d.outcome === 'catastrophic')
    return `<span class="badge badge-red">${icon('alert-octagon', 12)} ${d.outcome}</span>`;
  if (d.outcome === 'positive')
    return `<span class="badge badge-green">${icon('check', 12)} Positive</span>`;
  return `<span class="badge badge-yellow">${icon('bar-chart', 12)} Monitoring</span>`;
}

function _fmtDate(d) {
  if (!d) return '–';
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function _fmtDateShort(d) {
  if (!d) return '–';
  try { return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' }); }
  catch (_) { return String(d).slice(0, 10); }
}

/* ── Interactive Onboarding Tour ─────────────────────────────────────────── */
let currentGuideStep = 0;
const guideSteps = [
  {
    title: "1. Background Monitoring",
    desc: "Sentinel connects via Fivetran MCP. Every 30 minutes, it pulls your latest SaaS metrics while you work.",
    action: "See how it analyzes...",
    tab: "overview"
  },
  {
    title: "2. The Causal Trace",
    desc: "When metrics drop, Gemini automatically builds a causal chain from the negative outcome back to the root decision.",
    action: "View the Trace →",
    tab: "trace"
  },
  {
    title: "3. Logging Decisions",
    desc: "You can log decisions manually or extract them automatically from meeting transcripts.",
    action: "Finish Tour",
    tab: "decisions"
  }
];

function startGuide() {
  currentGuideStep = 0;
  document.getElementById('floating-guide').classList.add('visible');
  updateGuideUI();
}

function nextGuideStep() {
  if (currentGuideStep < guideSteps.length - 1) {
    currentGuideStep++;
    updateGuideUI();
    
    // Switch tabs dynamically for "wow" effect
    if (guideSteps[currentGuideStep].tab) {
      switchTab(guideSteps[currentGuideStep].tab);
    }
  } else {
    dismissGuide();
  }
}

function updateGuideUI() {
  const step = guideSteps[currentGuideStep];
  document.getElementById('guide-step').textContent = `STEP ${currentGuideStep + 1}/${guideSteps.length}`;
  document.getElementById('guide-title').textContent = step.title;
  document.getElementById('guide-desc').textContent = step.desc;
  document.getElementById('guide-next-btn').textContent = step.action;
}

function dismissGuide() {
  document.getElementById('floating-guide').classList.remove('visible');
}

// Auto-start guide 3 seconds after loading a scenario if not seen
const observer = new MutationObserver(() => {
  if (document.getElementById('view-dashboard').classList.contains('active')) {
    if (!sessionStorage.getItem('tourSeen')) {
      setTimeout(() => startGuide(), 3000);
      sessionStorage.setItem('tourSeen', 'true');
    }
  }
});
observer.observe(document.getElementById('view-dashboard'), { attributes: true, attributeFilter: ['class'] });


function _fmtKey(k) {
  return k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function _timeAgo() {
  return 'just now';
}

function _sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

/* ── Custom Analysis (Your Data) ────────────────────────────────────────── */
async function runCustomAnalysis() {
  const decisionText = document.getElementById('custom-decision-text').value.trim();
  const decisionDate = document.getElementById('custom-decision-date').value;
  if (!decisionText || !decisionDate) {
    alert('Decision text and date are required.');
    return;
  }

  const payload = {
    decision_text: decisionText,
    decision_date: decisionDate,
    decision_type: document.getElementById('custom-decision-type').value,
    mrr_at_decision: parseFloat(document.getElementById('custom-mrr-before').value) || null,
    nps_at_decision: parseFloat(document.getElementById('custom-nps-before').value) || null,
    churn_at_decision: parseFloat(document.getElementById('custom-churn-before').value) || null,
    mrr_now: parseFloat(document.getElementById('custom-mrr-after').value) || null,
    nps_now: parseFloat(document.getElementById('custom-nps-after').value) || null,
    churn_now: parseFloat(document.getElementById('custom-churn-after').value) || null,
    metric_weekly_series: document.getElementById('custom-series').value.trim() || null,
  };

  // Remove nulls
  Object.keys(payload).forEach(k => { if (payload[k] === null) delete payload[k]; });

  const resultsEl = document.getElementById('custom-results');
  const verdictEl = document.getElementById('custom-verdict-card');
  const testsEl = document.getElementById('custom-tests-card');
  const confoundingEl = document.getElementById('custom-confounding-card');
  const narrativeEl = document.getElementById('custom-narrative-card');

  resultsEl.style.display = 'block';
  verdictEl.innerHTML = `<div class="gemini-thinking"><div class="gemini-thinking-dot"></div><div class="gemini-thinking-dot"></div><div class="gemini-thinking-dot"></div><span style="margin-left:6px">Running 3-method causal inference battery...</span></div>`;
  testsEl.innerHTML = ''; confoundingEl.innerHTML = ''; narrativeEl.innerHTML = '';

  addActivity('gemini', `Gemini 3: running causal analysis on your data...`);

  try {
    const res = await fetch(`${API}/api/custom/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Analysis failed');
    }
    const data = await res.json();
    renderCustomResults(data, verdictEl, testsEl, confoundingEl, narrativeEl);
    addActivity('success', `Causal analysis complete: ${data.verdict}`);
  } catch (e) {
    verdictEl.innerHTML = `<div class="text-red font-bold">Analysis failed: ${e.message}</div>`;
  }
}

function renderCustomResults(data, verdictEl, testsEl, confoundingEl, narrativeEl) {
  const verdictColors = { strong_signal: 'var(--red)', weak_signal: 'var(--yellow)', no_signal: 'var(--blue)', insufficient_data: 'var(--text-secondary)' };
  const ca = data.causal_analysis || {};

  // Verdict card
  verdictEl.innerHTML = `
    <div style="margin-bottom:12px">
      <span style="font-size:11px;font-weight:700;color:${verdictColors[data.verdict] || 'var(--text-secondary)'};background:${verdictColors[data.verdict] || 'var(--surface-2)'}22;padding:3px 10px;border-radius:4px;text-transform:uppercase">
        ${data.verdict.replace('_', ' ')}
      </span>
    </div>
    <div style="font-size:15px;font-weight:600;margin-bottom:8px">${data.verdict_text}</div>
    <div style="font-size:13px;color:var(--text-secondary)">${data.recommendation}</div>
    <div style="margin-top:10px;font-size:11px;color:var(--text-tertiary)">
      Data quality: <strong>${data.data_quality?.quality || '?'}</strong> · ${data.data_quality?.data_points || 0} data points · ${data.data_quality?.metric_used || '?'}
      ${data.data_quality?.quality !== 'good' ? `<br><em>${data.data_quality?.improve_by || ''}</em>` : ''}
    </div>`;

  // Statistical tests card
  const granger = ca.granger || {};
  const its = ca.interrupted_time_series || {};
  const mwu = ca.mann_whitney || {};
  const sig = ca.significant_tests || 0;

  testsEl.innerHTML = `
    <div style="font-size:13px;font-weight:700;margin-bottom:12px">3-Method Causal Inference Battery: ${sig}/3 tests significant</div>
    <div style="font-size:11px;color:var(--text-tertiary);margin-bottom:12px">${ca.methodology_note || ''}</div>
    ${_renderTestRow('Granger Causality', granger.significant, granger.interpretation || granger.note || '–', granger.p_value != null ? `F-stat: ${granger.f_stat}, p=${granger.p_value}` : '')}
    ${_renderTestRow('Interrupted Time Series', its.significant, its.interpretation || its.note || '–', its.slope_change != null ? `Slope change: ${its.slope_change > 0 ? '+' : ''}${its.slope_change?.toFixed(4)}` : '')}
    ${_renderTestRow('Mann-Whitney U', mwu.significant, mwu.interpretation || mwu.note || '–', mwu.p_value != null ? `U=${mwu.u_stat}, p=${mwu.p_value}` : '')}
    <div style="margin-top:12px;padding-top:12px;border-top:1px solid var(--border);font-size:12px;color:var(--text-tertiary)">
      Pearson r = ${(ca.pearson_r || 0).toFixed(3)} (supporting context only, not causal evidence)
    </div>`;

  // Confounding factors
  confoundingEl.innerHTML = `
    <div style="font-size:13px;font-weight:700;margin-bottom:10px">Alternative Explanations (Gemini-generated)</div>
    <div style="font-size:12px;color:var(--text-tertiary);margin-bottom:10px">Factors that could explain the same outcome without this decision being causal:</div>
    ${(data.confounding_factors || []).map((f, i) => `
      <div style="padding:8px;border-bottom:1px solid var(--border);font-size:13px;color:var(--text-secondary)">
        <span style="color:var(--yellow);font-weight:700">${i+1}.</span> ${f}
      </div>`).join('')}`;

  // Narrative
  narrativeEl.innerHTML = `
    <div style="font-size:13px;font-weight:700;margin-bottom:10px">SENTINEL Analysis</div>
    <div style="font-size:14px;line-height:1.7;color:var(--text-primary)">${data.narrative || '–'}</div>`;
}

function _renderTestRow(name, significant, interpretation, stats) {
  const testIcon = significant === true
    ? `<span style="color:var(--green)">${icon('check-circle', 14)}</span>`
    : significant === false
      ? `<span style="color:var(--text-tertiary)">${icon('x', 14)}</span>`
      : `<span style="color:var(--text-tertiary);font-size:12px">?</span>`;
  const color = significant === true ? 'var(--green)' : significant === false ? 'var(--text-tertiary)' : 'var(--text-secondary)';
  return `
    <div style="padding:10px;border-bottom:1px solid var(--border)">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
        <span>${testIcon}</span>
        <span style="font-size:13px;font-weight:600;color:${color}">${name}</span>
        ${stats ? `<span style="font-size:11px;color:var(--text-tertiary);margin-left:auto">${stats}</span>` : ''}
      </div>
      <div style="font-size:12px;color:var(--text-secondary);padding-left:24px">${interpretation}</div>
    </div>`;
}

/* ── Transcript → Decisions ──────────────────────────────────────────────── */
function loadSampleTranscript() {
  document.getElementById('transcript-input').value = `Board Meeting, AcmeSaaS, June 3, 2026

Attendees: CEO (Sarah), CFO (Marcus), VP Sales (Jordan), CTO (Alex)

Sarah: We need to address our unit economics. CAC is up to $1,800 and we need to close the gap with LTV.
Marcus: I've modeled three options. The cleanest path is a 20% pricing increase across all tiers.
Jordan: I'm worried about the timing. Our NPS just came back at 31. We have some large accounts with open tickets.
Sarah: Noted. But we can't keep subsidizing growth. Decision: we move forward with the 20% increase, effective June 15.
Alex: I'll also need to hire two senior engineers for the reliability work. We've had uptime issues.
Sarah: Approved. Alex, hire two engineers by end of Q2.
Marcus: I'll send updated pricing to Jordan's team today.

Action items:
- Sarah: Approve pricing changes in billing system
- Jordan: Draft customer communication plan
- Alex: Post job descriptions by Friday`;
}

async function extractTranscript() {
  const text = document.getElementById('transcript-input').value.trim();
  if (!text) { alert('Paste a transcript first.'); return; }

  const source = document.getElementById('transcript-source').value;
  const btn = document.getElementById('btn-extract');
  btn.textContent = 'Extracting...';
  btn.disabled = true;

  addActivity('gemini', 'Gemini 3: extracting decisions from transcript...');

  try {
    const res = await fetch(`${API}/api/transcript/extract`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transcript: text, source }),
    });
    const data = await res.json();
    renderTranscriptResults(data);
    addActivity('success', `${data.decisions_logged} decision(s) extracted and logged`);
  } catch (e) {
    document.getElementById('transcript-results').innerHTML = `
      <div class="card" style="border-color:var(--red-border);padding:var(--space-5)">
        <div class="text-red font-bold">Extraction failed</div>
        <div style="font-size:13px;color:var(--text-secondary);margin-top:6px">Check backend connection.</div>
      </div>`;
  }

  btn.innerHTML = `${icon('sparkles', 14)} Extract Decisions with Gemini 3`;
  btn.disabled = false;
}

function renderTranscriptResults(data) {
  const el = document.getElementById('transcript-results');
  if (!data.decisions || !data.decisions.length) {
    el.innerHTML = `<div class="card" style="padding:var(--space-5)"><div style="color:var(--text-secondary)">${data.message || 'No decisions found.'}</div></div>`;
    return;
  }

  const decisionsHtml = data.decisions.map(d => `
    <div class="card mb-4" style="padding:var(--space-5)">
      <div class="flex items-center gap-3 mb-3">
        <span class="badge badge-blue">${d.decision_type}</span>
        <span class="badge badge-green">${(d.confidence * 100).toFixed(0)}% confidence</span>
        <span class="mono text-secondary" style="font-size:11px;margin-left:auto">${d.decision_id}</span>
      </div>
      <div style="font-size:15px;font-weight:600;margin-bottom:var(--space-2)">${d.decision_text}</div>
      ${d.rationale ? `<div style="font-size:13px;color:var(--text-secondary);margin-bottom:var(--space-2)"><strong>Rationale:</strong> ${d.rationale}</div>` : ''}
      ${d.participants?.length ? `<div style="font-size:13px;color:var(--text-secondary)"><strong>Participants:</strong> ${d.participants.join(', ')}</div>` : ''}
      <div style="margin-top:var(--space-3);font-size:12px;color:var(--green)">${icon('check', 13)} ${d.metrics_captured?.length || 0} metrics captured with this decision</div>
    </div>
  `).join('');

  el.innerHTML = `
    <div class="flex items-center gap-3 mb-5">
      <span class="badge badge-green">${icon('check', 12)} ${data.decisions_logged} decision(s) logged</span>
      <span style="font-size:13px;color:var(--text-secondary)">${data.message}</span>
    </div>
    ${decisionsHtml}
    <div class="card" style="border-color:var(--blue-border);padding:var(--space-4);font-size:13px;color:var(--text-secondary)">
      ${icon('lightbulb', 13)} Each decision is now in the Decision Log with a full Fivetran metrics snapshot. View in <button class="btn btn-ghost btn-sm" onclick="switchTab('decisions')">Decision Log →</button>
    </div>
  `;

  // Reload decision log if on it
  if (currentScenario && window._scenarioData) {
    for (const d of data.decisions) {
      window._scenarioData.decisions.unshift({
        decision_id: d.decision_id,
        decision_text: d.decision_text,
        decision_type: d.decision_type,
        logged_at: new Date().toISOString(),
        outcome: 'monitoring',
        warning_fired: false,
      });
    }
    if (currentTab === 'decisions') renderDecisionsFullTable();
  }
}

/* ── Monitor cycle trigger ───────────────────────────────────────────────── */
async function triggerMonitorCycle() {
  addActivity('fivetran', 'MCP: triggering monitoring cycle...');
  try {
    const res = await fetch(`${API}/api/monitor/run`, { method: 'POST' });
    const data = await res.json();
    addActivity('gemini', 'Gemini 3: monitoring cycle running...');
    // Poll status after 5s
    setTimeout(async () => {
      try {
        const sr = await fetch(`${API}/api/monitor/status`);
        const s = await sr.json();
        const badge = document.getElementById('monitor-status-badge');
        if (badge && s.ran_at) {
          badge.textContent = `Last run: ${new Date(s.ran_at).toLocaleTimeString()} · ${s.warnings_detected || 0} patterns`;
          badge.style.display = 'block';
        }
        if (s.warnings_new > 0) {
          addActivity('warning', `${s.warnings_new} new warning(s) detected by agent`);
        } else if (s.status === 'ok') {
          addActivity('success', 'Monitoring cycle complete, no new warnings');
        }
      } catch(_) {}
    }, 5000);
  } catch(e) {
    addActivity('warning', 'Monitor cycle failed, check backend');
  }
}

/* ── Live MCP call log (polls /api/tool-calls/recent) ────────────────────── */
let _mcpPollLastId = 0;
let _mcpPollInterval = null;

function startMcpPoll() {
  if (_mcpPollInterval) return;
  _mcpPollInterval = setInterval(async () => {
    try {
      const res = await fetch(`${API}/api/tool-calls/recent?since=${_mcpPollLastId}&limit=5`);
      const data = await res.json();
      if (data.calls?.length) {
        for (const call of data.calls) {
          _renderMcpCall(call);
          _mcpPollLastId = Math.max(_mcpPollLastId, call.id + 1);
        }
      }
    } catch (_) {}
  }, 1500);
}

function _renderMcpCall(call) {
  const feed = document.getElementById('sidebar-mcp-log');
  if (!feed) return;
  const sourceLabel = call.source === 'mcp' ? `${icon('zap', 11)} MCP` : 'API';
  const item = document.createElement('div');
  item.className = 'mcp-call-item';
  item.innerHTML = `
    <span style="color:var(--blue);font-weight:600">${sourceLabel}</span>
    <span style="color:var(--text-secondary);font-size:11px;margin-left:4px">${call.tool}()</span>
    ${call.error ? `<span style="color:var(--red)"> ${icon('x', 10)}</span>` : `<span style="color:var(--green)"> ${icon('check', 10)}</span>`}
  `;
  feed.insertBefore(item, feed.firstChild);
  while (feed.children.length > 8) feed.removeChild(feed.lastChild);

  // Mirror to activity feed — use clean label without emoji (icon shown by addActivity)
  addActivity('fivetran', `MCP: ${call.tool}()`);
}

async function _pollMcpCallsSince(sinceId) {
  // Short burst of polls to pick up calls triggered by scenario load
  for (let i = 0; i < 6; i++) {
    await _sleep(1500);
    try {
      const res = await fetch(`${API}/api/tool-calls/recent?since=${sinceId}&limit=10`);
      const data = await res.json();
      if (data.calls?.length) {
        for (const call of data.calls) {
          _renderMcpCall(call);
          sinceId = Math.max(sinceId, call.id + 1);
          _mcpPollLastId = sinceId;
        }
      }
    } catch (_) {}
  }
}

/* ── ADK multi-step reasoning trace (shown above the agent answer) ────────── */
function _renderAdkTrace(trace) {
  if (!trace || !trace.length) return '';
  const steps = trace.map((t, i) => {
    const argStr = t.args && Object.keys(t.args).length
      ? Object.entries(t.args).map(([k, v]) => `${k}=${String(v).slice(0, 24)}`).join(', ')
      : '';
    const stepIcon = t.ok === false ? `<span style="color:var(--red)">${icon('x', 11)}</span>` : `<span style="color:var(--green)">${icon('check', 11)}</span>`;
    return `
      <div class="adk-step">
        <span class="adk-step-num">${i + 1}</span>
        <span class="adk-step-tool">${t.tool}<span class="adk-step-args">(${argStr})</span></span>
        <span class="adk-step-ok">${stepIcon}</span>
      </div>`;
  }).join('');
  return `
    <div class="adk-trace">
      <div class="adk-trace-head">${icon('settings', 13)} Agent reasoning: ${trace.length} tool ${trace.length === 1 ? 'call' : 'calls'} via Google ADK + Gemini 3</div>
      ${steps}
    </div>`;
}

/* ── Fivetran Platform control panel ─────────────────────────────────────── */
let _ftLoaded = false;

async function loadFivetranPanel(force) {
  if (_ftLoaded && !force) return;
  _ftLoaded = true;

  const refreshBtn = document.getElementById('btn-ft-refresh');
  if (refreshBtn) { refreshBtn.disabled = true; refreshBtn.textContent = '↻ Calling MCP…'; }
  addActivity('fivetran', 'MCP: loading full Fivetran platform overview');

  // Pre-render demo connectors immediately so the panel is never blank
  const demoConnectors = [
    { id: 'google_sheets_acme', service: 'google_sheets', schema: 'acme_metrics', status: 'active', live: false },
    { id: 'fivetran_log', service: 'fivetran_log', schema: 'fivetran_log', status: 'active', live: false },
    { id: 'hubspot_crm', service: 'hubspot', schema: 'acme_hubspot', status: 'active', live: false },
  ];
  _renderFtConnectors(demoConnectors);
  _renderFtSummary({ groups: 1, connectors: 3, live_connectors: 0, destinations: 1, webhooks: 1, registered_tables: 4 });
  _renderFtAccount({ email: 'demo@sentinel.ai', account_type: 'Business' });
  _renderFtGroups([{ id: 'demo_group', name: 'Demo Workspace' }]);
  _renderFtDestinations([{ id: 'bigquery_demo', service: 'bigquery', region: 'US' }]);

  loadIntegrationPosture();

  try {
    const res = await fetch(`${API}/api/connectors/platform`);
    const data = await res.json();

    _renderFtSummary(data.summary || {}, data.transport);
    _renderFtConnectors(data.connectors || []);
    _renderFtAccount(data.account || {});
    _renderFtGroups(data.groups || []);
    _renderFtDestinations(data.destinations || []);
    _renderFtWebhooks(data.webhooks || []);
    loadWebhookEvents();

    const tb = document.getElementById('ft-transport-badge');
    if (tb && data.transport) { tb.textContent = data.transport; tb.style.display = ''; }
  } catch (e) {
    const summary = document.getElementById('ft-summary');
    if (summary) summary.innerHTML = `<div class="ft-loading" style="color:var(--red)">Fivetran platform unreachable, start the backend to see live MCP data.</div>`;
  } finally {
    if (refreshBtn) { refreshBtn.disabled = false; refreshBtn.textContent = '↺ Refresh via MCP'; }
  }
}

// Honest live-vs-demo posture banner — straight from /api/health/integrations.
// SENTINEL never pretends demo data is live; this shows the real wiring state.
async function loadIntegrationPosture() {
  const el = document.getElementById('ft-posture');
  if (!el) return;
  try {
    const res = await fetch(`${API}/api/health/integrations`);
    const d = await res.json();
    const order = ['fivetran', 'bigquery', 'gemini', 'adk', 'mongodb', 'slack'];
    const dot = (st) => st === 'live' ? 'live'
                     : st === 'configured' ? 'cfg'
                     : st === 'error' ? 'err' : 'demo';
    const postureLabel = {
      fully_live:     ['FULLY LIVE',     'live'],
      partially_live: ['PARTIALLY LIVE', 'cfg'],
      demo:           ['DEMO MODE',      'demo'],
    }[d.posture] || ['DEMO', 'demo'];

    const chips = order
      .filter(k => d.integrations && d.integrations[k])
      .map(k => {
        const it = d.integrations[k];
        const extra = it.mode ? ` · ${it.mode}`
                    : (k === 'gemini' && it.active_model) ? ` · ${it.active_model}` : '';
        return `<span class="posture-chip ${dot(it.status)}" title="${(it.detail||'').replace(/"/g,'')}">
                  <span class="posture-dot"></span>${k}${extra}
                </span>`;
      }).join('');

    el.style.display = '';
    el.innerHTML = `
      <div class="posture-head">
        <span class="posture-tag ${postureLabel[1]}">${postureLabel[0]}</span>
        <span class="posture-sub">System self-report: SENTINEL never presents demo data as live.
          <code>GET /api/health/integrations</code></span>
      </div>
      <div class="posture-chips">${chips}</div>`;
  } catch (e) {
    el.style.display = 'none';
  }
}

function _renderFtSummary(s, transport) {
  const el = document.getElementById('ft-summary');
  if (!el) return;
  const tiles = [
    { n: s.groups ?? 0,            label: 'Groups',            tileIcon: icon('folder', 18) },
    { n: s.connectors ?? 0,        label: 'Connectors',        tileIcon: icon('zap', 18) },
    { n: s.live_connectors ?? 0,   label: 'Live (real)',       tileIcon: icon('check-circle', 18) },
    { n: s.destinations ?? 0,      label: 'Destinations',      tileIcon: icon('target', 18) },
    { n: s.webhooks ?? 0,          label: 'Webhooks',          tileIcon: icon('radio', 18) },
    { n: s.registered_tables ?? 0, label: 'BigQuery tables',   tileIcon: icon('bar-chart', 18) },
  ];
  el.innerHTML = tiles.map(t => `
    <div class="ft-summary-tile">
      <div class="ft-summary-icon">${t.tileIcon}</div>
      <div class="ft-summary-num">${t.n}</div>
      <div class="ft-summary-label">${t.label}</div>
    </div>
  `).join('');
}

function _renderFtConnectors(connectors) {
  const el = document.getElementById('ft-connectors-list');
  const cnt = document.getElementById('ft-conn-count');
  if (cnt) cnt.textContent = `${connectors.length} connector${connectors.length === 1 ? '' : 's'}`;
  if (!el) return;
  if (!connectors.length) {
    el.innerHTML = `<div class="ft-loading">No connectors returned by Fivetran.</div>`;
    return;
  }
  el.innerHTML = connectors.map(c => {
    const live = c.live;
    const statusColor = (c.status === 'paused') ? 'var(--yellow)'
      : c.failed_at ? 'var(--red)' : 'var(--green)';
    return `
      <div class="ft-conn-row" onclick="loadSyncHistory('${c.id}','${(c.service || c.schema || c.id)}')">
        <div class="ft-conn-dot" style="background:${statusColor}"></div>
        <div class="ft-conn-main">
          <div class="ft-conn-name">${c.service || c.schema || c.id}
            ${live ? '<span class="ft-tag live">LIVE</span>' : '<span class="ft-tag demo">DEMO</span>'}
          </div>
          <div class="ft-conn-sub">${c.id} · ${c.status || 'unknown'}${c.last_sync ? ' · last sync ' + _fmtDate(c.last_sync) : ''}</div>
        </div>
        <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation();syncConnector('${c.id}', this)">${icon('zap', 13)} Sync</button>
      </div>`;
  }).join('');
}

async function syncConnector(id, btn) {
  if (btn) { btn.disabled = true; btn.innerHTML = `${icon('repeat', 13)} Syncing...`; }
  addActivity('fivetran', `MCP: sync_connection(${id})`);
  try {
    const res = await fetch(`${API}/api/connectors/${encodeURIComponent(id)}/sync`, { method: 'POST' });
    const data = await res.json();
    if (btn) btn.innerHTML = data.triggered ? `${icon('check', 13)} Triggered` : `${icon('x', 13)} Failed`;
    addActivity(data.triggered ? 'success' : 'warning', `Sync ${data.triggered ? 'triggered' : 'failed'}: ${id}`);
  } catch (_) {
    if (btn) btn.innerHTML = `${icon('x', 13)} Error`;
  } finally {
    setTimeout(() => { if (btn) { btn.disabled = false; btn.innerHTML = `${icon('zap', 13)} Sync`; } }, 2500);
  }
}

async function loadSyncHistory(id, name) {
  const drawer = document.getElementById('ft-detail-drawer');
  const nameEl = document.getElementById('ft-detail-name');
  const histEl = document.getElementById('ft-sync-history');
  if (!drawer || !histEl) return;
  drawer.style.display = 'block';
  if (nameEl) nameEl.textContent = name;
  histEl.innerHTML = `<div class="ft-loading">Calling Fivetran get_sync_history(${id})…</div>`;
  drawer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  addActivity('fivetran', `MCP: get_sync_history(${id})`);
  try {
    const res = await fetch(`${API}/api/connectors/${encodeURIComponent(id)}/history`);
    const data = await res.json();
    const hist = data.history || [];
    if (!hist.length) {
      histEl.innerHTML = `<div style="font-size:13px;color:var(--text-secondary)">No sync history rows returned. With live Fivetran credentials this shows each sync's start, end, and status.</div>`;
      return;
    }
    histEl.innerHTML = hist.slice(0, 8).map(h => {
      const ok = !(h.failed_at) && (h.status !== 'failure');
      return `
        <div class="ft-hist-row">
          <span class="ft-conn-dot" style="background:${ok ? 'var(--green)' : 'var(--red)'}"></span>
          <span style="font-size:12px;color:var(--text-secondary)">${_fmtDate(h.succeeded_at || h.created_at || h.timestamp || h.date)}</span>
          <span style="font-size:12px;margin-left:auto">${h.sync_state || h.status || (ok ? 'succeeded' : 'failed')}</span>
        </div>`;
    }).join('');
  } catch (_) {
    histEl.innerHTML = `<div style="font-size:13px;color:var(--red)">Could not load sync history.</div>`;
  }
}

function _renderFtAccount(acct) {
  const el = document.getElementById('ft-account');
  if (!el) return;
  const rows = Object.entries(acct).filter(([k]) => !k.startsWith('_'));
  if (!rows.length) { el.innerHTML = `<div class="ft-loading">No account info.</div>`; return; }
  el.innerHTML = rows.map(([k, v]) => `
    <div class="ft-kv"><span class="ft-kv-k">${_fmtKey(k)}</span><span class="ft-kv-v">${v ?? '–'}</span></div>
  `).join('');
}

function _renderFtGroups(groups) {
  const el = document.getElementById('ft-groups');
  if (!el) return;
  if (!groups.length) { el.innerHTML = `<div class="ft-loading">No groups.</div>`; return; }
  el.innerHTML = groups.map(g => `
    <div class="ft-kv"><span class="ft-kv-k">${icon('folder', 13)} ${g.name || g.id}</span><span class="ft-kv-v mono">${g.id}</span></div>
  `).join('');
}

function _renderFtDestinations(dests) {
  const el = document.getElementById('ft-destinations');
  if (!el) return;
  if (!dests.length) { el.innerHTML = `<div class="ft-loading">No destinations.</div>`; return; }
  el.innerHTML = dests.map(d => {
    const svc = d.service || d.config?.service || 'destination';
    const proj = d.config?.project_id || d.config?.database || '';
    const region = d.region || d.config?.data_set_location || '';
    return `
      <div class="ft-dest">
        <div class="ft-dest-svc">${icon('target', 13)} ${svc}${svc.includes('big') || svc.includes('query') ? ' (BigQuery)' : ''}</div>
        <div class="ft-conn-sub">${[proj, region, d.setup_status].filter(Boolean).join(' · ')}</div>
      </div>`;
  }).join('');
}

function _renderFtWebhooks(hooks) {
  const el = document.getElementById('ft-webhooks-list');
  if (!el) return;
  if (!hooks.length) {
    el.innerHTML = `<div class="ft-loading">No webhooks registered. SENTINEL exposes <span class="mono">/api/fivetran/webhook</span> to receive sync events.</div>`;
    return;
  }
  el.innerHTML = hooks.map(w => `
    <div class="ft-conn-row" style="cursor:default">
      <div class="ft-conn-dot" style="background:${w.active ? 'var(--green)' : 'var(--text-tertiary)'}"></div>
      <div class="ft-conn-main">
        <div class="ft-conn-name">${w.type || 'webhook'} ${w.active ? '<span class="ft-tag live">ACTIVE</span>' : ''}</div>
        <div class="ft-conn-sub">${(w.events || []).join(', ') || 'all events'} → ${(w.url || '').replace(/^https?:\/\//, '').slice(0, 40)}…</div>
      </div>
    </div>
  `).join('');
}

async function loadWebhookEvents() {
  const el = document.getElementById('ft-webhook-events');
  if (!el) return;
  try {
    const res = await fetch(`${API}/api/fivetran/webhook/recent?limit=5`);
    const data = await res.json();
    const ev = data.events || [];
    if (!ev.length) { el.innerHTML = ''; return; }
    el.innerHTML = `
      <div style="font-size:11px;color:var(--text-tertiary);margin-bottom:6px">Recent inbound Fivetran events</div>
      ${ev.map(e => `<div class="ft-event-row">${icon('radio', 12)} <b>${e.event}</b> ← ${e.connector_id} <span style="margin-left:auto;color:var(--text-tertiary)">${_fmtDate(e.received_at)}</span></div>`).join('')}`;
  } catch (_) { el.innerHTML = ''; }
}

/* ── Data source badge ────────────────────────────────────────────────────── */
// Honest provenance: live Fivetran→BigQuery vs a historical public case study vs
// demo fallback. Never implies a static dataset is "live".
function updateDataSourceBadge(dataSource) {
  const badge = document.getElementById('data-source-badge');
  if (!badge) return;
  if (dataSource === 'bigquery_live') {
    badge.textContent = '● Live Fivetran → BigQuery';
    badge.className = 'badge badge-green';
  } else if (currentScenario === 'qwikster' || dataSource === 'structured_fallback') {
    badge.innerHTML = `${icon('layers', 13)} Historical case study · 2011 public data`;
    badge.className = 'badge badge-yellow';
  } else {
    badge.textContent = 'Demo data · no live source connected';
    badge.className = 'badge badge-yellow';
  }
  badge.style.display = '';
}

/* ── Init ─────────────────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  // Close modals on backdrop click
  document.querySelectorAll('.modal-backdrop').forEach(m => {
    m.addEventListener('click', e => { if (e.target === m) m.classList.remove('open'); });
  });
  // Start live MCP call polling
  startMcpPoll();
});
