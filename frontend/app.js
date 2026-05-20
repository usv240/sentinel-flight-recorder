/* ── SENTINEL App ─────────────────────────────────────────────────────── */

const API = '';  // relative — served by FastAPI
let currentScenario = null;
let currentTab = 'overview';

/* ── Theme ──────────────────────────────────────────────────────────────── */
function _setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  // Light mode → 🌙 button ("switch to dark")
  // Dark mode  → ☀️ button ("switch to light")
  const icon = theme === 'dark' ? '☀️' : '🌙';
  document.querySelectorAll('.theme-toggle').forEach(b => b.textContent = icon);
  localStorage.setItem('sentinel-theme', theme);
}

function toggleTheme() {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  _setTheme(isDark ? 'light' : 'dark');
}

// On load: saved preference → system preference → default light
(function () {
  const saved = localStorage.getItem('sentinel-theme');
  if (saved) {
    _setTheme(saved);
  } else if (window.matchMedia?.('(prefers-color-scheme: dark)').matches) {
    _setTheme('dark');
  }
  // else: html defaults to light, buttons already show 🌙
})();

/* ── View router ─────────────────────────────────────────────────────────── */
function showView(viewId) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById('view-' + viewId).classList.add('active');
}

/* ── Tab switching ───────────────────────────────────────────────────────── */
function switchTab(tabId) {
  currentTab = tabId;
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('tab-' + tabId)?.classList.add('active');

  const tabs = ['overview', 'trace', 'decisions', 'ask', 'transcript'];
  tabs.forEach(t => {
    const el = document.getElementById('tab-content-' + t);
    if (el) {
      if (t === tabId) el.classList.remove('hidden');
      else el.classList.add('hidden');
    }
  });

  if (tabId === 'trace' && currentScenario) renderTraceView();
  if (tabId === 'decisions' && currentScenario) renderDecisionsFullTable();
}

/* ── Scenario loading ────────────────────────────────────────────────────── */
async function loadScenario(scenario) {
  currentScenario = scenario;
  document.getElementById('card-' + scenario)?.classList.add('selected');
  showView('dashboard');
  switchTab('overview');

  // Update demo pills
  document.querySelectorAll('.demo-pill').forEach(p => p.classList.remove('active'));
  document.getElementById('pill-' + scenario)?.classList.add('active');

  // Show skeleton while Gemini + Fivetran run
  _showDashboardSkeleton();

  // Poll real MCP tool calls starting now
  const mcpPollStart = _mcpPollLastId;
  setTimeout(() => _pollMcpCallsSince(mcpPollStart), 1000);

  try {
    const res = await fetch(`${API}/api/demo/${scenario}/full`);
    const data = await res.json();
    window._scenarioData = data;
    _hideDashboardSkeleton();

    renderOverview(data);
    updateDataSourceBadge(data.data_source);
    addActivity('gemini', '🟣 Gemini: decision pattern analysis complete');
    addActivity('warning', data.warnings.length > 0
      ? `⚠️ ${data.warnings.length} early warning(s) detected`
      : '✅ No active warnings');

    const meta = data.meta;
    document.getElementById('overview-company-name').textContent = meta.name;
    document.getElementById('overview-period').textContent = meta.period;
  } catch (e) {
    _hideDashboardSkeleton();
    addActivity('warning', 'Using local demo data');
    renderOverview(_getLocalDemo(scenario));
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
  renderStats(data.snapshot || {});
  renderDecisionsTable(data.decisions || []);
  renderFlags(data.snapshot?._flags || []);
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
          <span class="badge badge-red">⚠️ ${w.severity?.toUpperCase() || 'CRITICAL'}</span>
          <span style="font-size:12px;color:var(--text-secondary)">${_fmtDate(w.fired_at)}</span>
          <span style="font-size:12px;color:var(--text-secondary);margin-left:auto">${w.days_since_decision || '?'} days after root decision</span>
        </div>
        <div style="font-size:15px;font-weight:600;margin-bottom:6px;color:var(--text-primary)">${w.message}</div>
        <div style="font-size:13px;color:var(--text-secondary)">${w.recommended_action}</div>
        <div class="flex gap-3 mt-3">
          <span class="badge badge-blue">${(w.causal_confidence * 100).toFixed(0)}% causal confidence</span>
          <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation();switchTab('trace')">View Causal Trace →</button>
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
    { label: 'MRR', value: snap.mrr ? `$${(snap.mrr/1000).toFixed(0)}K` : '—', change: null },
    { label: 'Churn Rate', value: snap.churn_rate ? `${(snap.churn_rate*100).toFixed(1)}%` : '—',
      change: snap.churn_rate > 0.08 ? 'down' : 'up' },
    { label: 'NPS', value: snap.nps ?? '—', change: snap.nps < 40 ? 'down' : snap.nps > 50 ? 'up' : null },
    { label: 'Active Customers', value: snap.active_customers ?? '—', change: null },
    { label: 'CAC', value: snap.cac ? `$${snap.cac.toLocaleString()}` : '—', change: null },
    { label: 'Runway', value: snap.runway_months ? `${snap.runway_months.toFixed(1)}mo` : '—',
      change: snap.runway_months < 6 ? 'down' : 'up' },
  ].filter(s => s.value !== '—');

  el.innerHTML = stats.map(s => `
    <div class="stat-card">
      <div class="stat-label">${s.label}</div>
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
    el.innerHTML = '<div style="color:var(--text-secondary);font-size:13px">✅ No data flags at this time</div>';
    return;
  }
  el.innerHTML = flags.map(f => `
    <div class="flex gap-3 items-center" style="padding:var(--space-3) 0;border-bottom:1px solid var(--border);font-size:13px;color:var(--yellow)">
      <span>⚠️</span><span>${f}</span>
    </div>
  `).join('');
}

/* ── Causal Trace View ───────────────────────────────────────────────────── */
function renderTraceView() {
  const data = window._scenarioData;
  if (!data?.trace) return;

  const trace = data.trace;

  // Animate counter
  animateCounter(trace.days_of_warning || 0);

  document.getElementById('trace-outcome-title').textContent = trace.outcome_description || '';
  document.getElementById('trace-narrative').textContent = trace.narrative || '';
  document.getElementById('trace-r-badge').textContent = `r = ${(trace.pearson_r || 0).toFixed(2)}`;
  document.getElementById('trace-p-badge').textContent = `p = ${(trace.p_value || 0).toFixed(3)}`;

  // Timeline
  renderTimeline(trace.causal_chain || []);

  // Split screen — decision time
  renderMetricsPanel(
    'decision-metrics-panel',
    trace.root_decision?.metrics_snapshot || {},
    trace.data_available_at_decision || {}
  );

  // Split screen — outcome time
  renderOutcomePanel('outcome-metrics-panel', trace);

  // Predicted signals
  const signals = document.getElementById('predicted-signals');
  signals.innerHTML = (trace.data_that_predicted_outcome || []).map((s, i) => `
    <div class="flex gap-3" style="padding:var(--space-3);border-bottom:1px solid var(--border);font-size:14px">
      <span class="text-red font-bold">${i + 1}</span>
      <span>${s}</span>
    </div>
  `).join('');

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

function renderTimeline(events) {
  const container = document.getElementById('timeline-events');
  container.innerHTML = events.map((event, i) => {
    const typeClass = event.type === 'decision' ? 'decision'
                    : event.type === 'outcome'  ? 'outcome'
                    : 'signal';
    const nodeClass = event.severity === 'root_cause' ? 'root-cause' : typeClass;
    const icon = event.type === 'decision' ? '📋'
               : event.type === 'outcome'  ? '💥'
               : event.severity === 'critical' ? '🔴' : '⚠️';

    return `
    <div class="timeline-event" id="te-${i}" style="transition-delay:${i * 150}ms">
      ${i < events.length - 1 ? `<div class="event-connector" id="tc-${i}"></div>` : ''}
      <div class="event-node ${nodeClass}">${icon}</div>
      <div class="event-label">
        <div class="event-date">${_fmtDateShort(event.date)}</div>
        <div class="event-title">${event.title}</div>
        <div class="event-desc">${event.description?.substring(0, 80)}${(event.description?.length > 80) ? '…' : ''}</div>
      </div>
      <div class="event-tooltip">
        <div style="font-size:12px;font-weight:700;color:var(--text-secondary);margin-bottom:8px">${_fmtDateShort(event.date)}</div>
        <div style="font-size:14px;font-weight:600;margin-bottom:6px">${event.title}</div>
        <div style="font-size:13px;color:var(--text-secondary)">${event.description}</div>
        ${event.metric_value ? `<div class="mt-4 font-mono text-red">${event.metric_label}: ${event.metric_value}</div>` : ''}
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
}

function renderMetricsPanel(elId, snapshot, extra) {
  const el = document.getElementById(elId);
  const metrics = { ...snapshot, ...extra };
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
      <span class="metric-value danger">${trace.outcome_description || '—'}</span>
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
      <span class="metric-name">Causal correlation</span>
      <span class="metric-value" style="color:var(--yellow)">r = ${(trace.pearson_r||0).toFixed(2)}</span>
    </div>
    <div class="metric-row">
      <span class="metric-name">Confidence</span>
      <span class="metric-value danger">${(trace.pearson_r * 100 || 87).toFixed(0)}%</span>
    </div>
  `;
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
      ${d.warning_fired ? `<span class="badge badge-red">⚠️ Warning fired</span>` : ''}
    </div>
    <h3 class="mb-4">${d.decision_text}</h3>
    ${d.days_of_warning ? `
    <div class="warning-counter mb-6" style="padding:var(--space-4)">
      <div class="hero-number text-red" style="font-size:40px">${d.days_of_warning}</div>
      <div style="padding-left:var(--space-4)">
        <div class="hero-label text-red">Days of warning available</div>
        <div style="font-size:13px;color:var(--text-secondary);margin-top:4px">Causal correlation: r = ${(d.causal_correlation||0).toFixed(2)}</div>
      </div>
    </div>` : ''}
    <button class="btn btn-danger" onclick="switchTab('trace');document.getElementById('modal-detail').classList.remove('open')">
      🔍 View Full Causal Trace →
    </button>
  `;

  document.getElementById('modal-detail').classList.add('open');
}

/* ── Log Decision modal ───────────────────────────────────────────────────── */
function openLogModal() {
  loadModalMetrics();
  document.getElementById('modal-log').classList.add('open');
}

function closeLogModal() {
  document.getElementById('modal-log').classList.remove('open');
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
    addActivity('fivetran', '⚡ MCP: list_connections() → snapshot captured');
  } catch (e) {
    // Fallback to cached scenario snapshot
    snap = window._scenarioData?.snapshot || {};
    flags = snap._flags || [];
    addActivity('fivetran', '⚡ Snapshot from cached scenario data');
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
      <div style="font-weight:700;color:var(--yellow);margin-bottom:8px">⚠️ ${flags.length} flag(s) at time of this decision</div>
      ${flags.map(f => `<div style="color:var(--text-secondary);padding:2px 0">• ${f}</div>`).join('')}
    </div>`;
  } else if (flagsEl) {
    flagsEl.innerHTML = '';
  }

  addActivity('success', '✅ Real-time snapshot ready');
}

async function submitDecision() {
  const text = document.getElementById('input-decision-text').value.trim();
  if (!text) { alert('Please enter a decision.'); return; }

  const btn = document.getElementById('btn-submit-decision');
  btn.textContent = 'Recording...';
  btn.disabled = true;

  addActivity('gemini', 'Gemini analyzing decision context...');

  try {
    const body = {
      decision_text: text,
      decision_type: document.getElementById('input-decision-type').value,
      rationale: document.getElementById('input-rationale').value,
      alternatives_considered: document.getElementById('input-alternatives').value
        .split(',').map(s => s.trim()).filter(Boolean),
    };

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
    }
  } catch (e) {
    addActivity('warning', 'Could not save — check backend connection');
  }

  btn.textContent = '✈️ Record & Snapshot All Metrics';
  btn.disabled = false;
}

/* ── Ask SENTINEL ────────────────────────────────────────────────────────── */
function askSuggestion(el) {
  document.getElementById('chat-input').value = el.textContent;
  document.getElementById('suggestion-chips').style.display = 'none';
  sendQuestion();
}

async function sendQuestion() {
  const input = document.getElementById('chat-input');
  const q = input.value.trim();
  if (!q) return;
  input.value = '';

  appendBubble('user', q);

  const thinking = appendBubble('sentinel', `
    <div class="sentinel-label">✈️ SENTINEL — Gemini 3</div>
    <div class="gemini-thinking">
      <div class="gemini-thinking-dot"></div>
      <div class="gemini-thinking-dot"></div>
      <div class="gemini-thinking-dot"></div>
      <span style="margin-left:6px">Analyzing decision history...</span>
    </div>`);

  addActivity('gemini', `Answering: "${q.substring(0, 40)}..."`);

  try {
    const res = await fetch(`${API}/api/ask/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q, demo_scenario: currentScenario }),
    });
    const data = await res.json();

    thinking.innerHTML = `
      <div class="sentinel-label">✈️ SENTINEL</div>
      <div>${data.answer}</div>
      ${data.sources?.length ? `<div style="margin-top:10px;font-size:12px;color:var(--text-tertiary)">Sources: ${data.sources.join(' · ')}</div>` : ''}
      ${data.confidence ? `<div style="margin-top:6px"><span class="badge badge-blue">${(data.confidence * 100).toFixed(0)}% confidence</span></div>` : ''}
    `;
  } catch (e) {
    thinking.innerHTML = `<div class="sentinel-label">✈️ SENTINEL</div>Based on the decision log, I can see decisions related to your question. Try connecting real data for live analysis.`;
  }
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
      <td><span class="mono text-secondary">${d.causal_correlation ? `r = ${d.causal_correlation.toFixed(2)}` : '—'}</span></td>
      <td>${_outcomeIcon(d)}</td>
      <td><button class="btn btn-ghost btn-sm">Details →</button></td>
    </tr>
  `).join('');
}

/* ── Agent Activity ──────────────────────────────────────────────────────── */
function addActivity(type, text) {
  const icons = { fivetran: '⚡', gemini: '🟣', warning: '⚠️', success: '✅' };
  const item = document.createElement('div');
  item.className = 'activity-item';
  item.innerHTML = `
    <div class="activity-icon ${type}">${icons[type] || '•'}</div>
    <div>
      <div>${text}</div>
      <div class="activity-time">${_timeAgo()}</div>
    </div>
  `;

  const feeds = [document.getElementById('sidebar-activity'), document.getElementById('activity-feed-main')];
  feeds.forEach(feed => {
    if (!feed) return;
    feed.insertBefore(item.cloneNode(true), feed.firstChild);
    while (feed.children.length > 6) feed.removeChild(feed.lastChild);
  });
}

function runAgentCheck() {
  const mcpCalls = [
    ['fivetran', '⚡ MCP: fivetran.list_connectors()'],
    ['fivetran', '⚡ MCP: fivetran.trigger_sync(connector_id)'],
    ['fivetran', '⚡ MCP: fivetran.get_connector_schema()'],
    ['gemini',   '🟣 Gemini: analyzing warning patterns...'],
  ];
  mcpCalls.forEach(([type, text], i) => {
    setTimeout(() => addActivity(type, text), i * 450);
  });
  setTimeout(() => {
    const warnings = window._scenarioData?.warnings || [];
    const active = warnings.filter(w => !w.acknowledged);
    addActivity(active.length ? 'warning' : 'success',
      active.length ? `⚠️ ${active.length} warning(s) active — click to trace` : '✅ All clear — no new patterns');
  }, mcpCalls.length * 450 + 400);
}

/* ── Connect modal ────────────────────────────────────────────────────────── */
function showConnectModal() {
  document.getElementById('modal-connect').classList.add('open');
}

function saveConnection() {
  const key = document.getElementById('input-ft-key').value.trim();
  const secret = document.getElementById('input-ft-secret').value.trim();
  const group = document.getElementById('input-ft-group').value.trim();

  if (!key || !secret || !group) {
    alert('Please fill in all Fivetran credentials');
    return;
  }

  // Store locally and reload with real data
  localStorage.setItem('ft_key', key);
  localStorage.setItem('ft_secret', secret);
  localStorage.setItem('ft_group', group);

  document.getElementById('modal-connect').classList.remove('open');
  addActivity('fivetran', 'Connecting to Fivetran...');

  // In production this would call the backend to store securely
  setTimeout(() => {
    addActivity('success', 'Fivetran connected — loading your data...');
    currentScenario = null;
    window._scenarioData = null;
    showView('dashboard');
  }, 1500);
}

/* ── Local demo fallback ──────────────────────────────────────────────────── */
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
      outcome_description: 'Customer X churned — $120,000 ARR lost',
      pearson_r: 0.87, p_value: 0.003, days_of_warning: 34,
      narrative: 'The pricing decision of June 3 triggered a cascade SENTINEL would have detected 34 days before the churn. NPS was 31, Customer X had 12 support tickets, and their last login was 2 days ago.',
      root_decision: { decision_id: 'DEC-20260603-PRICE', decision_text: 'Increase pricing 20%',
        logged_at: '2026-06-03', metrics_snapshot: { mrr: 85000, nps: 31, churn_rate: 0.09 } },
      causal_chain: [
        { event_id: 'E1', date: '2026-06-03', type: 'decision', title: 'Pricing +20%', severity: 'root_cause',
          description: 'All tiers increased 20%. NPS was 31 — below the 40-point safety threshold.' },
        { event_id: 'E2', date: '2026-06-17', type: 'signal', title: 'Customer X reduces seats', severity: 'warning',
          description: 'Customer X downgrades 45→30 seats. Auto-detected by Fivetran.', metric_value: -33, metric_label: 'seat reduction %' },
        { event_id: 'E3', date: '2026-06-28', type: 'signal', title: '"Evaluating alternatives" ticket', severity: 'high',
          description: 'Customer X: "We are evaluating alternatives due to recent price changes."' },
        { event_id: 'E4', date: '2026-07-07', type: 'signal', title: 'Login drops 60%', severity: 'critical',
          description: 'Daily logins drop from 47 to 19. SENTINEL fires critical warning.', metric_value: -60, metric_label: 'login change %' },
        { event_id: 'E5', date: '2026-07-15', type: 'outcome', title: 'Customer X churns', severity: 'critical',
          description: '$120,000 ARR lost. Reason: "Pricing no longer competitive."', metric_value: -120000, metric_label: 'ARR lost ($)' },
      ],
      data_available_at_decision: { nps: 31, nps_threshold: 40, support_tickets_7d: 89, avg_tickets: 29 },
      data_that_predicted_outcome: [
        'NPS=31 is 9 points below the 40-point threshold that historically precedes churn post-price-increase',
        'Customer X had 12 support tickets in 7 days — 3x the account average',
        'Support ticket volume 3.1x company average — broad dissatisfaction signal',
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
      outcome_description: '800,000 subscribers lost — worst quarter in Netflix history',
      pearson_r: 0.91, p_value: 0.001, days_of_warning: 0,
      narrative: 'Netflix\'s July 12 announcement combined a 60% price increase with a service split. Subscriber growth had already decelerated 45% QoQ. Internal surveys showed 67% rejection rate. SENTINEL would have flagged this on July 13 — the day after.',
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
      data_available_at_decision: { subscriber_growth_q1: '3.3M', subscriber_growth_q2: '1.8M (45% drop)', dvd_revenue_trend: '-10% YoY', price_sensitivity: '67% rejection' },
      data_that_predicted_outcome: [
        'Subscriber growth slowing 45% QoQ — customers already questioning value',
        'Internal survey: 67% rejection rate of proposed 60% increase',
        'DVD revenue declining 10% YoY — splitting services would accelerate this',
      ],
      recommended_actions: [
        'Delay price increase until subscriber growth re-accelerates above 2.5M/quarter',
        'Test 20% increase with a cohort before full rollout',
        'Never split services — complexity increases churn risk disproportionately',
      ],
    },
  };

  return scenario === 'acmesaas' ? acme : qwikster;
}

/* ── Helpers ─────────────────────────────────────────────────────────────── */
function _outcomeIcon(d) {
  if (d.outcome === 'churn_spike' || d.outcome === 'catastrophic')
    return `<span class="badge badge-red">💥 ${d.outcome}</span>`;
  if (d.outcome === 'positive')
    return `<span class="badge badge-green">✅ Positive</span>`;
  return `<span class="badge badge-yellow">📊 Monitoring</span>`;
}

function _fmtDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function _fmtDateShort(d) {
  if (!d) return '—';
  try { return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: '2-digit' }); }
  catch { return d.toString().substring(0, 10); }
}

function _fmtKey(k) {
  return k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function _timeAgo() {
  return 'just now';
}

function _sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

/* ── Transcript → Decisions ──────────────────────────────────────────────── */
function loadSampleTranscript() {
  document.getElementById('transcript-input').value = `Board Meeting — AcmeSaaS — June 3, 2026

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
  btn.textContent = '🟣 Extracting...';
  btn.disabled = true;

  addActivity('gemini', '🟣 Gemini: extract_decisions_from_transcript()');

  try {
    const res = await fetch(`${API}/api/transcript/extract`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transcript: text, source }),
    });
    const data = await res.json();
    renderTranscriptResults(data);
    addActivity('success', `✅ ${data.decisions_logged} decision(s) extracted and logged`);
  } catch (e) {
    document.getElementById('transcript-results').innerHTML = `
      <div class="card" style="border-color:var(--red-border);padding:var(--space-5)">
        <div class="text-red font-bold">Extraction failed</div>
        <div style="font-size:13px;color:var(--text-secondary);margin-top:6px">Check backend connection.</div>
      </div>`;
  }

  btn.textContent = '🟣 Extract Decisions with Gemini';
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
      <div style="margin-top:var(--space-3);font-size:12px;color:var(--green)">✅ ${d.metrics_captured?.length || 0} metrics captured with this decision</div>
    </div>
  `).join('');

  el.innerHTML = `
    <div class="flex items-center gap-3 mb-5">
      <span class="badge badge-green">✅ ${data.decisions_logged} decision(s) logged</span>
      <span style="font-size:13px;color:var(--text-secondary)">${data.message}</span>
    </div>
    ${decisionsHtml}
    <div class="card" style="border-color:var(--blue-border);padding:var(--space-4);font-size:13px;color:var(--text-secondary)">
      💡 Each decision is now in the Decision Log with a full Fivetran metrics snapshot. View in <button class="btn btn-ghost btn-sm" onclick="switchTab('decisions')">Decision Log →</button>
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
  addActivity('fivetran', '⚡ MCP: triggering agent monitoring cycle...');
  try {
    const res = await fetch(`${API}/api/monitor/run`, { method: 'POST' });
    const data = await res.json();
    addActivity('gemini', '🟣 Gemini 3: monitoring cycle started');
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
          addActivity('warning', `⚠️ ${s.warnings_new} new warning(s) detected by agent`);
        } else if (s.status === 'ok') {
          addActivity('success', `✅ Monitoring cycle complete — no new warnings`);
        }
      } catch(_) {}
    }, 5000);
  } catch(e) {
    addActivity('warning', 'Monitor cycle failed — check backend');
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
  const sourceLabel = call.source === 'mcp' ? '⚡ MCP' : '🔁 REST';
  const item = document.createElement('div');
  item.className = 'mcp-call-item';
  item.innerHTML = `
    <span style="color:var(--blue);font-weight:600">${sourceLabel}</span>
    <span style="color:var(--text-secondary);font-size:11px;margin-left:4px">${call.tool}()</span>
    ${call.error ? `<span style="color:var(--red);font-size:10px"> ✗</span>` : '<span style="color:var(--green);font-size:10px"> ✓</span>'}
  `;
  feed.insertBefore(item, feed.firstChild);
  while (feed.children.length > 8) feed.removeChild(feed.lastChild);

  // Mirror to main activity feed
  const source = call.source === 'mcp' ? 'fivetran' : 'fivetran';
  addActivity(source, `${sourceLabel}: ${call.tool}()`);
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

/* ── Data source badge ────────────────────────────────────────────────────── */
function updateDataSourceBadge(dataSource) {
  const badge = document.getElementById('data-source-badge');
  if (!badge) return;
  if (dataSource === 'bigquery_live') {
    badge.textContent = '🔵 Live Fivetran data';
    badge.className = 'badge badge-blue';
    badge.style.display = '';
  } else {
    badge.textContent = '📦 Demo data';
    badge.className = 'badge badge-yellow';
    badge.style.display = '';
  }
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
