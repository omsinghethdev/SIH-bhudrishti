/* ==========================================================================
   BhuDrishti 3D — prototype application logic
   All data below is fictional demo data for MP Nagar, Bhopal Municipal Area.
   ========================================================================== */

const ICONS = {
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M20 6L9 17l-5-5"/></svg>',
  alert: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>',
  clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>',
  file: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6"/></svg>',
  layers: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l9 5-9 5-9-5 9-5z"/><path d="M3 12l9 5 9-5"/><path d="M3 17l9 5 9-5"/></svg>',
  shield: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6z"/></svg>',
  drone: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="2.4"/><path d="M4 4l5.5 5.5M20 4l-5.5 5.5M4 20l5.5-5.5M20 20l-5.5-5.5"/><circle cx="4" cy="4" r="1.6" fill="currentColor"/><circle cx="20" cy="4" r="1.6" fill="currentColor"/><circle cx="4" cy="20" r="1.6" fill="currentColor"/><circle cx="20" cy="20" r="1.6" fill="currentColor"/></svg>',
  plane: '<svg viewBox="0 0 24 24" fill="currentColor" stroke="none"><path d="M2 16l8-2.5V6l3-4 3 4v7.5L24 16v2l-8-2v3.5l2.5 2V23l-3.5-1-3.5 1v-1.5L13 20v-3.5L2 18v-2z"/></svg>',
  train: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="5" y="3" width="14" height="14" rx="3"/><path d="M5 11h14M9 17l-2 4M15 17l2 4"/><circle cx="8.5" cy="7.5" r="1"/><circle cx="15.5" cy="7.5" r="1"/></svg>',
};

/* ---------------------------------------------------------------- DEMO DATA */

const STATE = {
  role: 'planner',
  view: 'overview',
  explorer: { mode: '3d', exploded: false, xray: false, underground: false, selectedLevel: 'floor4',
    pointCloud: false, lidar: false, floorplan: false, gnss: false, drone: false, plane: false, metro: false, rail: false,
    water: false, gas: false, electricity: false, telecom: false, showRoads: true, showTerrain: false, showProposed: false,
    scope: 'locality', buildingId: null, localityViewMode: 'schematic',
    locLayers: { buildings: true, metro: true, rail: true, parks: true, roads: true } },
  wizard: { step: 0, unitType: null, parcel: '1450A9B7C23456' },
  conflicts: { scanning: false },
  approvalView: 'kanban',
};

var LEVELS = []; /* hydrated by api.js */

var UNIT_402 = {}; /* hydrated by api.js */

var LEVEL_DETAIL = {}; /* hydrated by api.js */

var BUILDINGS_EXTRA = {}; /* hydrated by api.js */

var LAKEVIEW_META = { infra: {} }; /* hydrated by api.js */

var INFRA_PROFILES = {}; /* hydrated by api.js */

STATE.proposedInfra = { type: 'metro', from: 'lakeview', to: 'dbtrade', depth: 18, analyzed: false, conflicts: [], route: null, inspecting: null };

function parseDepthRange(elevStr) {
  const nums = [...elevStr.matchAll(/-([\d.]+)/g)].map(m => parseFloat(m[1]));
  if (!nums.length) return null;
  return [Math.min(...nums), Math.max(...nums)];
}

/* The 3D (X, Y, Z) conflict analysis runs on the backend against the stored
   volumes and utility assets; this only records the result for rendering. */
async function analyzeProposedInfra() {
  const p = STATE.proposedInfra;
  const res = await API.createProposal({
    infra_type: p.type,
    from_building: p.from,
    to_building: p.to,
    width_m: p.width || 3,
    depth_m: p.depth,
  });
  p.id = res.id;
  p.route = res.route;
  p.conflicts = res.conflicts.map(c => ({
    severity: c.severity, building: c.building, buildingId: c.buildingId,
    level: c.level, id3d: c.id3d, explain: c.explain, rule: c.rule,
    recommended: c.recommended,
  }));
  p.analyzed = true;
  p.inspecting = null;
}

function getLevels(bidOverride) {
  const id = bidOverride !== undefined ? bidOverride : STATE.explorer.buildingId;
  return (id && BUILDINGS_EXTRA[id]) ? BUILDINGS_EXTRA[id].levels : LEVELS;
}
function getLevelDetail(bidOverride) {
  const id = bidOverride !== undefined ? bidOverride : STATE.explorer.buildingId;
  return (id && BUILDINGS_EXTRA[id]) ? BUILDINGS_EXTRA[id].detail : LEVEL_DETAIL;
}
function getBuildingMeta() {
  const id = STATE.explorer.buildingId;
  return (id && BUILDINGS_EXTRA[id]) ? BUILDINGS_EXTRA[id].meta : LAKEVIEW_META;
}

/* ---- MP Nagar locality map data (fictional demo layout) ---- */

var LOCALITY = { buildings: [], genericBuildings: [], metro: { stations: [] }, rail: {}, parks: [] }; /* hydrated by api.js */
var CONFLICTS = []; /* hydrated by api.js */

var APPROVAL_COLUMNS = []; /* hydrated by api.js */

var DATASETS = []; /* hydrated by api.js */

var FLOOR_REVIEW = []; /* hydrated by api.js */

var REPORTS = []; /* hydrated by api.js */

var ACTIVITY = []; /* hydrated by api.js */

/* ---------------------------------------------------------------- UTILITIES */

function $(sel, root) { return (root || document).querySelector(sel); }
function $all(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

function toast(msg, icon) {
  const stack = $('#toastStack');
  const el = document.createElement('div');
  el.className = 'toast';
  el.innerHTML = (icon || ICONS.check) + '<span>' + msg + '</span>';
  stack.appendChild(el);
  setTimeout(() => { el.style.transition = 'opacity .3s'; el.style.opacity = '0'; setTimeout(() => el.remove(), 300); }, 3200);
}

function confidenceLabel(score) {
  if (score >= 90) return { label: 'Verified', color: 'var(--success)' };
  if (score >= 70) return { label: 'High Confidence', color: 'var(--success)' };
  if (score >= 50) return { label: 'Review Required', color: 'var(--warning)' };
  return { label: 'Low Confidence', color: 'var(--error)' };
}

/* ---------------------------------------------------------------- ROUTING */

const VIEW_ON_ENTER = {
  vstack: () => renderVerticalStackPage(),
  underground: () => renderUndergroundPage(),
  proposed: () => initProposedInfraPage(),
  users: () => renderUsersPage(),
};

function goToView(name) {
  STATE.view = name;
  $all('.view').forEach(v => v.classList.remove('active'));
  const target = $('#view-' + name);
  if (target) target.classList.add('active');
  $all('.nav-item').forEach(n => n.classList.toggle('active', n.dataset.view === name));
  $all('.bottom-nav button').forEach(n => n.classList.toggle('active', n.dataset.view === name));
  $('#mainArea').scrollTop = 0;
  if (VIEW_ON_ENTER[name]) VIEW_ON_ENTER[name]();
}

function initRouting() {
  $all('[data-view]').forEach(el => {
    el.addEventListener('click', () => goToView(el.dataset.view));
  });
}

/* ---------------------------------------------------------------- SHELL */

function initShell() {
  $('#collapseBtn').addEventListener('click', () => {
    $('#appShell').classList.toggle('sidebar-collapsed');
  });

  // The signed-in account's role is authoritative — the server enforces it and
  // decides what data (e.g. unmasked owners) this session is allowed to see.
  const account = window.Auth && Auth.user;
  if (account) {
    STATE.role = account.role;
    const select = $('#roleSelect');
    select.value = account.role;
    select.disabled = true;
    select.title = 'Signed in as ' + account.name + ' (' + account.role_label + ')';
  }

  const logoutBtn = $('#logoutBtn');
  if (logoutBtn) logoutBtn.addEventListener('click', () => doLogout());

  $('#notifBtn').addEventListener('click', async () => {
    try {
      const stats = await API.conflictStats();
      toast(stats.active + ' open conflicts · ' + stats.critical + ' critical', ICONS.alert);
    } catch (err) {
      toast('Could not load notifications: ' + err.message, ICONS.alert);
    }
  });

  applyRole();
}

const ROLE_NAV_ACCESS = {
  planner: 'all',
  constructor: ['overview', 'explorer', 'proposed', 'conflicts', 'analytics', 'search', 'passport'],
  surveyor: ['explorer', 'vstack', 'underground', 'intake', 'search', 'passport'],
  public: ['explorer', 'search', 'passport'],
};
const ROLE_DEFAULT_VIEW = { planner: 'overview', constructor: 'explorer', surveyor: 'explorer', public: 'explorer' };

function applyRole() {
  const initialsMap = { planner: 'GP', constructor: 'CE', surveyor: 'AS', public: 'PU' };
  $('#roleAvatar').textContent = initialsMap[STATE.role];
  const isPublic = STATE.role === 'public';
  const ownerEl = $('#passportOwner');
  if (ownerEl) ownerEl.textContent = isPublic ? 'A. Sharma (masked)' : (UNIT_402.ownerFull + ' (verified owner)');
  updateNavAccess();
  if ($('#buildingSvgHost')) refreshExplorerDetail();
}

function updateNavAccess() {
  const access = ROLE_NAV_ACCESS[STATE.role];
  const allowed = (view) => access === 'all' || access.includes(view);
  $all('.nav-item[data-view]').forEach(el => {
    el.style.display = allowed(el.dataset.view) ? 'flex' : 'none';
  });
  $all('.bottom-nav button[data-view]').forEach(el => {
    el.style.display = allowed(el.dataset.view) ? 'flex' : 'none';
  });
  $all('.nav-group-label').forEach(label => {
    let sib = label.nextElementSibling;
    let anyVisible = false;
    while (sib && sib.classList.contains('nav-item')) {
      if (sib.style.display !== 'none') anyVisible = true;
      sib = sib.nextElementSibling;
    }
    label.style.display = anyVisible ? 'block' : 'none';
  });
  if (!allowed(STATE.view)) {
    goToView(ROLE_DEFAULT_VIEW[STATE.role]);
    toast('That section isn\'t available for the ' + $('#roleSelect option:checked').textContent.trim() + ' role');
  }
}

/* ---------------------------------------------------------------- OVERVIEW */

function renderOverview() {
  const overview = (window.HYDRATED && HYDRATED.overview) || {};

  const heroName = window.Auth && Auth.user ? Auth.user.name : '';
  const hero = $('.hero-band h1');
  if (hero && heroName) hero.textContent = 'Welcome back, ' + heroName;

  const kpis = overview.kpis || [];
  $('#overviewKpis').innerHTML = kpis.map(k => `
    <div class="kpi-card"><div class="label">${k.label}</div><div class="value">${k.value}</div>${k.cls ? `<div class="delta ${k.cls}">${k.delta || 'Needs attention'}</div>` : ''}</div>`).join('');

  $('#recentConflicts').innerHTML = CONFLICTS.slice(0, 3).map((c, i) => {
    const m = severityMeta(c.sev);
    return `<div class="detail-row clickable-row" data-conflict-idx="${i}">
      <span class="k"><span class="severity-dot sev-${c.sev}"></span> ${c.type}</span>
      <span class="v badge ${m.badge}">${m.label}</span>
    </div>`;
  }).join('');
  $all('[data-conflict-idx]', $('#recentConflicts')).forEach(el => el.addEventListener('click', () => {
    goToView('conflicts');
    openConflictDrawer(CONFLICTS[+el.dataset.conflictIdx]);
  }));

  $('#recentSurveys').innerHTML = DATASETS.slice(0, 3).map(d => `
    <div class="detail-row"><span class="k">${d.name}</span><span class="v badge badge-info" style="font-weight:600">${d.state}</span></div>`).join('');

  const inspected = overview.recent_properties || [];
  $('#recentProperties').innerHTML = inspected.map((p, i) => `
    <div class="detail-row clickable-row" data-inspect-idx="${i}">
      <span class="k">${p.name}<br><span style="color:var(--text-faint);font-size:11px">${p.when}</span></span>
      <span class="v badge ${p.conf >= 90 ? 'badge-success' : 'badge-warning'}">${p.conf}/100</span>
    </div>`).join('');
  $all('[data-inspect-idx]', $('#recentProperties')).forEach(el => el.addEventListener('click', () => {
    const p = inspected[+el.dataset.inspectIdx];
    goToView('explorer');
    selectBuilding(p.bid);
  }));

  const projects = overview.active_projects || [];
  $('#activeProjects').innerHTML = projects.map(p => `
    <div style="margin-bottom:12px">
      <div style="display:flex;justify-content:space-between;font-size:12.5px;margin-bottom:5px"><strong>${p.name}</strong><span style="color:var(--text-secondary)">${p.status}</span></div>
      <div class="progress-track"><div class="progress-fill" style="width:${p.pct}%;background:${p.pct > 55 ? 'var(--success)' : 'var(--info)'}"></div></div>
    </div>`).join('');

  const feed = $('#activityFeed');
  feed.innerHTML = ACTIVITY.map((a, i) => `
    <div class="activity-item">
      <div class="dot-line"><span class="adot" style="background:${a.c}"></span>${i < ACTIVITY.length - 1 ? '<span class="aline"></span>' : ''}</div>
      <div><div class="atxt">${a.t}</div><div class="atime">${a.time}</div></div>
    </div>`).join('');

  const map = $('#miniMap');
  map.innerHTML = `
    <div class="ward-blob" style="width:70px;height:70px;left:40px;top:30px;background:rgba(182,66,66,0.35)"></div>
    <div class="ward-blob" style="width:50px;height:50px;left:150px;top:90px;background:rgba(200,131,26,0.3)"></div>
    <div class="parcel-outline" style="width:26px;height:20px;left:60px;top:50px"></div>
    <div class="parcel-outline" style="width:20px;height:16px;left:120px;top:75px"></div>
    <div class="parcel-outline" style="width:30px;height:22px;left:170px;top:110px"></div>
    <div class="parcel-outline" style="width:18px;height:18px;left:210px;top:40px"></div>`;

  const runBtn = $('#qaRunConflict');
  if (runBtn) runBtn.addEventListener('click', () => { goToView('conflicts'); setTimeout(() => $('#runValidationBtn') && $('#runValidationBtn').click(), 150); });
  const repBtn = $('#qaGenReport');
  if (repBtn) repBtn.addEventListener('click', () => goToReportsTab());
}

/* ---------------------------------------------------------------- ISO 3D EXPLORER */

function isoFaces(cx, yTop, yBottom, w, d) {
  const rx = 0.87, ry = 0.5, lx = -0.87, ly = 0.5;
  const B = { x: cx, y: yBottom }, T = { x: cx, y: yTop };
  const BR = { x: cx + d * rx, y: yBottom + d * ry }, TR = { x: cx + d * rx, y: yTop + d * ry };
  const BL = { x: cx + w * lx, y: yBottom + w * ly }, TL = { x: cx + w * lx, y: yTop + w * ly };
  const BB = { x: BR.x + w * lx, y: BR.y + w * ly }, TB = { x: TR.x + w * lx, y: TR.y + w * ly };
  const pts = (arr) => arr.map(p => p.x.toFixed(1) + ',' + p.y.toFixed(1)).join(' ');
  return {
    top: pts([T, TR, TB, TL]),
    right: pts([B, BR, TR, T]),
    left: pts([B, BL, TL, T]),
    frontTopX: T.x, frontTopY: T.y, rightTopX: TR.x, rightTopY: TR.y,
  };
}

function reducedMotionOK() {
  return !window.matchMedia || !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function buildExplorerSvg(ctxOverride) {
  const ctx = ctxOverride || STATE.explorer;
  const heightScale = ctx.mode === '2.5d' ? 0.55 : 1;
  const W = 120, D = 100, cx = 260;
  const groundY = 300;
  const gap = ctx.exploded ? 14 : 1;
  const levels = getLevels(ctx.buildingId);

  const above = levels.filter(l => !l.below).slice().reverse();
  const below = levels.filter(l => l.below);

  let svg = '';
  let overlays = '';
  let terrainLayer = '';
  let cursorY = groundY;
  const levelBoxes = {};

  above.forEach(level => {
    const h = level.h * heightScale;
    const yBottom = cursorY;
    const yTop = yBottom - h;
    const f = isoFaces(cx, yTop, yBottom, W, D);
    levelBoxes[level.id] = { yTop, yBottom, f, h };
    cursorY = yTop - gap;
  });

  cursorY = groundY;
  below.forEach(level => {
    const h = level.h * heightScale;
    const yTop = cursorY;
    const yBottom = yTop + h;
    const f = isoFaces(cx, yTop, yBottom, W, D);
    levelBoxes[level.id] = { yTop, yBottom, f, h };
    cursorY = yBottom + gap;
  });

  const isSelected = (id) => ctx.selectedLevel === id;
  const anySelected = !!ctx.selectedLevel;

  function levelGroup(level) {
    const box = levelBoxes[level.id];
    const sel = isSelected(level.id);
    const dim = anySelected && !sel;
    const dimOpacity = ctx.xray ? 0.22 : 0.6;
    const conflictOnLevel = level.hasConflict && isSelected(level.id);
    return `
      <g class="building-level ${dim ? 'dimmed' : ''}" data-level="${level.id}" style="opacity:${dim ? dimOpacity : (ctx.forceFade ? 0.4 : 1)}" ${sel ? 'filter="url(#selGlow)"' : ''}>
        <polygon points="${box.f.right}" fill="${level.right}" stroke="${sel ? '#163A5F' : '#4a5c68'}" stroke-width="${sel ? 1.6 : 0.6}"/>
        <polygon points="${box.f.right}" fill="url(#windowGrid)"/>
        <polygon points="${box.f.left}" fill="${level.left}" stroke="#4a5c68" stroke-width="0.6"/>
        <polygon points="${box.f.left}" fill="url(#windowGrid)"/>
        <polygon points="${box.f.top}" fill="${conflictOnLevel ? '#e3a1a1' : level.top}" stroke="#4a5c68" stroke-width="0.6" class="${conflictOnLevel ? 'unit-cell conflict-pulse' : ''}"/>
        <text x="${cx - 96}" y="${(box.yTop + box.yBottom) / 2 + 4}" font-size="10" font-family="IBM Plex Mono, monospace" fill="${level.below ? '#7d8b95' : '#425867'}" text-anchor="end">${level.tag}</text>
      </g>`;
  }

  svg += below.slice().reverse().map(levelGroup).join('');
  svg += above.map(levelGroup).join('');

  const deepestBelow = below.length ? levelBoxes[below[below.length - 1].id] : { yTop: groundY, yBottom: groundY };

  // ---- underground utilities: colored, labeled, depth-tagged (matches reference cross-section style) ----
  const pipeDefs = [
    { key: 'electricity', name: 'Electricity', depth: '-10 m', color: '#c8831a', y: deepestBelow.yBottom + 26, x1: cx - 150, x2: cx + 60 },
    { key: 'telecom', name: 'Telecom / Fiber', depth: '-8 m', color: '#3f8f5b', y: deepestBelow.yBottom + 48, x1: cx - 130, x2: cx + 90 },
    { key: 'water', name: 'Water', depth: '-15 m', color: '#2563a9', y: deepestBelow.yBottom + 72, x1: cx - 170, x2: cx + 140 },
    { key: 'gas', name: 'Gas', depth: '-12 m', color: '#d9702e', y: deepestBelow.yBottom + 4, x1: cx - 40, x2: cx + 220 },
  ];
  const activePipes = pipeDefs.filter(p => ctx.underground || ctx[p.key]);
  if (ctx.underground || activePipes.length) {
    activePipes.push({ key: 'sewer', name: 'Sewer', depth: '-5 m', color: '#2e7d5b', y: deepestBelow.yBottom + 4, x1: cx - 40, x2: cx + 220 });
  }
  if (activePipes.length) {
    overlays += '<g class="underground-group">' + activePipes.map(p => `
      <line x1="${p.x1}" y1="${p.y}" x2="${p.x2}" y2="${p.y}" stroke="${p.color}" stroke-width="5" stroke-linecap="round" opacity="0.88"/>
      <circle cx="${(p.x1 + p.x2) / 2}" cy="${p.y}" r="4.5" fill="${p.color}" stroke="#fff" stroke-width="1.5"/>
      <text x="${(p.x1 + p.x2) / 2 + 9}" y="${p.y - 7}" font-size="9.5" font-weight="700" fill="${p.color}">${p.name} ${p.depth}</text>`).join('') + '</g>';
  }
  if (ctx.metro) {
    const mY = deepestBelow.yBottom + 70;
    const mx1 = cx - 40, mx2 = cx + 220;
    overlays += `<g class="underground-group">
      <line x1="${mx1}" y1="${mY}" x2="${mx2}" y2="${mY}" stroke="#5b5f97" stroke-width="7" stroke-linecap="round" opacity="0.9"/>
      <circle cx="${(mx1 + mx2) / 2}" cy="${mY}" r="5" fill="#5b5f97" stroke="#fff" stroke-width="1.5"/>
      <text x="${(mx1 + mx2) / 2 + 10}" y="${mY - 8}" font-size="9.5" font-weight="700" fill="#3c3f66">Metro Tunnel -30 m (under construction)</text>
    </g>`;
  }
  // ---- roads, terrain, proposed infrastructure ----
  if (ctx.showRoads) {
    overlays += `<g><line x1="20" y1="${groundY + 12}" x2="${cx - 40}" y2="${groundY + 12}" stroke="#b9c2c9" stroke-width="6" stroke-linecap="round"/>
      <text x="20" y="${groundY + 26}" font-size="9" fill="#667085">Main Road</text></g>`;
  }
  if (ctx.showTerrain) {
    terrainLayer = `<ellipse cx="${cx}" cy="${groundY + 4}" rx="260" ry="16" fill="#dce8d6" opacity="0.55"/>`;
  }
  if (ctx.showProposed && STATE.proposedInfra && STATE.proposedInfra.analyzed && [STATE.proposedInfra.from, STATE.proposedInfra.to].includes(ctx.buildingId)) {
    const pi = STATE.proposedInfra;
    const profile = INFRA_PROFILES[pi.type];
    const conflictHere = pi.conflicts.some(c => c.buildingId === ctx.buildingId);
    overlays += `<g><line x1="${cx + 40}" y1="${groundY - 20}" x2="${cx + 260}" y2="${groundY - 40}" stroke="${conflictHere ? '#b64242' : profile.color}" stroke-width="3" stroke-dasharray="6 4" class="${conflictHere ? 'conflict-pulse' : ''}"/>
      <text x="${cx + 44}" y="${groundY - 26}" font-size="9" font-weight="700" fill="${conflictHere ? '#b64242' : profile.color}">Proposed ${profile.label} (${pi.depth} m)${conflictHere ? ' — conflict' : ''}</text></g>`;
  }

  // ---- survey data overlays ----
  if (ctx.pointCloud) {
    let dots = '';
    for (let i = 0; i < 90; i++) {
      const px = cx - 90 + Math.random() * 260;
      const py = 60 + Math.random() * 220;
      dots += `<circle cx="${px.toFixed(1)}" cy="${py.toFixed(1)}" r="1.1" fill="#5b7d99" opacity="0.55"/>`;
    }
    overlays += `<g class="path-icon-group">${dots}</g>`;
  }
  if (ctx.lidar) {
    let mesh = '';
    for (let i = 0; i < 8; i++) {
      const y = 60 + i * 30;
      mesh += `<line x1="${cx - 90}" y1="${y}" x2="${cx + 150}" y2="${y + 40}" stroke="#5b7d99" stroke-width="0.5" opacity="0.5"/>`;
    }
    overlays += `<g class="path-icon-group">${mesh}<text x="${cx - 90}" y="52" font-size="9" fill="#5b7d99">LiDAR mesh (sample density)</text></g>`;
  }
  if (ctx.floorplan && levelBoxes[ctx.selectedLevel]) {
    const b = levelBoxes[ctx.selectedLevel].f;
    overlays += `<g class="path-icon-group" stroke="#425867" stroke-width="0.5" stroke-dasharray="2 2" fill="none">
      <polygon points="${b.top}"/>
      <line x1="${b.frontTopX}" y1="${b.frontTopY}" x2="${b.rightTopX}" y2="${b.rightTopY}"/>
      <text x="${b.frontTopX - 6}" y="${b.frontTopY - 6}" font-size="8" fill="#425867" stroke="none">Floor plan overlay</text>
    </g>`;
  }
  if (ctx.gnss) {
    const pts = [[cx - 60, 90], [cx + 40, 70], [cx - 20, 260], [cx + 90, 230]];
    overlays += '<g class="path-icon-group" stroke="#c8831a" stroke-width="1.4">' +
      pts.map(([x, y]) => `<path d="M${x - 5} ${y} L${x + 5} ${y} M${x} ${y - 5} L${x} ${y + 5}"/>`).join('') +
      `<text x="${cx - 60}" y="82" font-size="8" fill="#c8831a" stroke="none">GNSS checkpoints</text></g>`;
  }

  // ---- drone flight path ----
  if (ctx.drone) {
    const pathId = 'dronePath';
    overlays += `<g>
      <path id="${pathId}" d="M 60 340 C 160 60, 380 40, 560 130" fill="none" stroke="#2563a9" stroke-width="1.4" stroke-dasharray="5 4" opacity="0.8"/>
      <text x="60" y="352" font-size="9" fill="#2563a9">Drone survey path — +45 m altitude</text>
      <g class="path-icon-group" fill="#2563a9">
        <circle r="4"/>
        ${reducedMotionOK() ? `<animateMotion dur="6s" repeatCount="indefinite"><mpath href="#${pathId}"/></animateMotion>` : ''}
      </g>
    </g>`;
  }

  // ---- aeroplane air corridor (air-rights clearance) ----
  if (ctx.plane) {
    const pathId = 'planePath';
    overlays += `<g>
      <line x1="10" y1="30" x2="640" y2="30" stroke="#667085" stroke-width="1" stroke-dasharray="6 4" opacity="0.7"/>
      <text x="10" y="22" font-size="9" fill="#667085">Aeroplane air corridor — +150 m clearance plane</text>
      <path id="${pathId}" d="M 0 30 L 660 30" fill="none" stroke="none"/>
      <g class="path-icon-group" fill="#667085" transform="scale(0.8)">
        <path d="M2 16l8-2.5V6l3-4 3 4v7.5L24 16v2l-8-2v3.5l2.5 2V23l-3.5-1-3.5 1v-1.5L13 20v-3.5L2 18v-2z" transform="translate(-12,-12)"/>
        ${reducedMotionOK() ? `<animateMotion dur="7s" repeatCount="indefinite"><mpath href="#${pathId}"/></animateMotion>` : ''}
      </g>
    </g>`;
  }

  // ---- railway track (at grade, surface level — distinct from the underground metro tunnel) ----
  if (ctx.rail) {
    const pathId = 'railPath';
    const ry = groundY + 46;
    overlays += `<g>
      <line x1="${cx + 60}" y1="${ry}" x2="${cx + 320}" y2="${ry}" stroke="#6b4f2a" stroke-width="4" stroke-linecap="round" opacity="0.85"/>
      <line x1="${cx + 60}" y1="${ry}" x2="${cx + 320}" y2="${ry}" stroke="#fff" stroke-width="1" stroke-dasharray="5 5"/>
      <text x="${cx + 66}" y="${ry - 8}" font-size="9.5" font-weight="700" fill="#6b4f2a">Railway Track — 0.0 m (at grade)</text>
      <path id="${pathId}" d="M ${cx + 60} ${ry} L ${cx + 320} ${ry}" fill="none" stroke="none"/>
      <g class="path-icon-group" fill="#6b4f2a">
        <rect x="-7" y="-5" width="14" height="10" rx="2"/>
        ${reducedMotionOK() ? `<animateMotion dur="5.5s" repeatCount="indefinite"><mpath href="#${pathId}"/></animateMotion>` : ''}
      </g>
    </g>`;
  }

  const groundLine = `<line x1="40" y1="${groundY + 2}" x2="620" y2="${groundY + 2}" stroke="#a9bcc7" stroke-width="1" stroke-dasharray="3 3"/>
    <text x="40" y="${groundY - 6}" font-size="9.5" fill="#8b98a5" font-family="IBM Plex Mono, monospace">GROUND LEVEL — 0.0 m</text>`;

  const minY = Math.min(...Object.values(levelBoxes).map(b => b.yTop), 20) - 40;
  let maxY = Math.max(...Object.values(levelBoxes).map(b => b.yBottom), groundY) + 60;
  if (ctx.underground || ctx.water || ctx.gas || ctx.electricity || ctx.telecom) maxY += 90;
  if (ctx.metro) maxY += 40;
  if (ctx.rail) maxY += 20;

  return `<svg viewBox="0 10 660 ${maxY - minY + 40}" width="620" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <filter id="selGlow" x="-40%" y="-40%" width="180%" height="180%">
        <feDropShadow dx="0" dy="0" stdDeviation="3.2" flood-color="#2563a9" flood-opacity="0.55"/>
      </filter>
      <pattern id="windowGrid" width="9" height="9" patternUnits="userSpaceOnUse">
        <rect width="9" height="9" fill="none"/>
        <rect x="1" y="1" width="6" height="6" fill="#ffffff" opacity="0.14"/>
      </pattern>
    </defs>
    ${terrainLayer}
    ${groundLine}
    ${svg}
    ${overlays}
  </svg>`;
}

function build2DPlanSvg() {
  const meta = getBuildingMeta();
  const isFlagship = STATE.explorer.buildingId === 'lakeview';
  const conflictOnUnit = isFlagship && STATE.explorer.selectedLevel === 'floor4';
  let overlays = '';
  if (STATE.explorer.underground) {
    overlays += `<line x1="60" y1="210" x2="500" y2="210" stroke="#2F6F73" stroke-width="4" stroke-dasharray="8 3" opacity="0.75"/>
      <text x="60" y="224" font-size="9" fill="#2F6F73">Water / fibre / sewer corridor (plan)</text>`;
  }
  if (STATE.explorer.metro) {
    overlays += `<line x1="40" y1="235" x2="520" y2="250" stroke="#5b5f97" stroke-width="5" stroke-dasharray="2 2" opacity="0.8"/>
      <text x="40" y="248" font-size="9" fill="#3c3f66">Metro tunnel — Line 2 (plan)</text>`;
  }
  if (STATE.explorer.drone) {
    overlays += `<path d="M 30 40 C 150 90, 380 10, 540 60" fill="none" stroke="#2563a9" stroke-width="1.4" stroke-dasharray="5 4"/>
      <text x="30" y="32" font-size="9" fill="#2563a9">Drone survey path (plan)</text>`;
  }
  if (STATE.explorer.plane) {
    overlays += `<line x1="10" y1="18" x2="560" y2="18" stroke="#667085" stroke-width="1" stroke-dasharray="6 4"/>
      <text x="10" y="12" font-size="8" fill="#667085">Air corridor overhead</text>`;
  }
  return `<svg viewBox="0 0 560 300" width="560" xmlns="http://www.w3.org/2000/svg">
    <rect x="60" y="60" width="440" height="210" fill="none" stroke="#1F4E79" stroke-width="2"/>
    <text x="64" y="54" font-size="10" fill="#1F4E79" font-family="IBM Plex Mono, monospace">Parent parcel ${meta.parent}</text>
    <rect x="120" y="100" width="300" height="140" fill="#9fc3d8" stroke="#6c93b3" stroke-width="1.5"/>
    <text x="132" y="120" font-size="10" fill="#163A5F" font-weight="700">${meta.name} — footprint</text>
    ${isFlagship ? `<rect x="260" y="150" width="70" height="46" fill="${conflictOnUnit ? '#e3a1a1' : '#7fa8c9'}" stroke="#b64242" stroke-width="1.2" class="${conflictOnUnit ? 'unit-cell conflict-pulse' : 'unit-cell'}" data-level="floor4"/>
    <text x="264" y="172" font-size="8" fill="#1f2933">Unit 402 (L4)</text>` : ''}
    ${overlays}
    <text x="64" y="292" font-size="9" fill="#667085">2D plan view — switch to 3D or 2.5D to inspect other levels individually</text>
  </svg>`;
}

/* ---------------------------------------------------------------- MP NAGAR LOCALITY MAP */

function buildLiveMapOverlayPins() {
  let html = '';
  LOCALITY.buildings.forEach(b => {
    const cx = ((b.x + b.w / 2) / 700 * 100).toFixed(1);
    const cy = ((b.y + b.h / 2) / 420 * 100).toFixed(1);
    html += `<div class="map-pin" data-asset="${b.id}" style="left:${cx}%;top:${cy}%" title="${b.name}">
      <div class="dot" style="background:${b.conflict ? '#b64242' : '#1F4E79'}"></div>
      <div class="lbl">${b.name}</div>
    </div>`;
  });
  const m = LOCALITY.metro.stations[0];
  html += `<div class="map-pin" data-infra="metro" style="left:${(m.x / 700 * 100).toFixed(1)}%;top:${(m.y / 420 * 100).toFixed(1)}%" title="Metro corridor">
    <div class="dot" style="background:#5b5f97"></div><div class="lbl">Metro corridor</div></div>`;
  html += `<div class="map-pin" data-infra="rail" style="left:18%;top:87%" title="Railway track">
    <div class="dot" style="background:#6b4f2a"></div><div class="lbl">Railway track</div></div>`;
  LOCALITY.parks.forEach((p, i) => {
    const cx = ((p.x + p.w / 2) / 700 * 100).toFixed(1);
    const cy = ((p.y + p.h / 2) / 420 * 100).toFixed(1);
    html += `<div class="map-pin" data-infra="park:${i}" style="left:${cx}%;top:${cy}%" title="${p.name}">
      <div class="dot" style="background:#3f8f5b"></div><div class="lbl">${p.name}</div></div>`;
  });
  return html;
}

function buildLiveMapHtml() {
  const q = encodeURIComponent('MP Nagar, Bhopal, Madhya Pradesh, India');
  const t = STATE.explorer.localityViewMode === 'satellite' ? '&t=k' : '';
  const src = `https://www.google.com/maps?q=${q}&z=16&output=embed${t}`;
  return `<iframe class="live-map-frame" src="${src}" loading="lazy" referrerpolicy="no-referrer-when-downgrade" title="Live map of MP Nagar, Bhopal"></iframe>
    <div class="map-pin-layer">${buildLiveMapOverlayPins()}</div>
    <div class="live-map-note">Pins mark the demo dataset's buildings and infrastructure — click one to open it. Positions are illustrative and won't track if you pan or zoom the live map.</div>`;
}

function wireLocalityAssetHandlers(host) {
  $all('[data-asset]', host).forEach(g => g.addEventListener('click', () => selectBuilding(g.dataset.asset)));
  $all('[data-infra]', host).forEach(g => g.addEventListener('click', () => openInfraDrawer(g.dataset.infra)));
  $all('[data-generic]', host).forEach(g => g.addEventListener('click', () => toast('This block has not been digitized yet — add it via Survey & Data Intake.')));
}

function buildLocalitySvg() {
  const L = STATE.explorer.locLayers;
  let svg = '';

  if (L.roads) {
    svg += `<g stroke="#c9ceb8" stroke-width="4" fill="none" opacity="0.85">
      <path d="M 0 260 H 700"/><path d="M 250 0 V 420"/><path d="M 470 0 V 420"/><path d="M 0 130 H 700"/>
    </g>`;
  }
  if (L.rail) {
    svg += `<g data-infra="rail" class="locality-asset" style="cursor:pointer">
      <path d="${LOCALITY.rail.path}" fill="none" stroke="#6b4f2a" stroke-width="4"/>
      <path d="${LOCALITY.rail.path}" fill="none" stroke="#fff" stroke-width="1" stroke-dasharray="6 6"/>
      <text x="20" y="368" font-size="10" fill="#6b4f2a" font-weight="700">Railway track (demo alignment)</text>
    </g>`;
  }
  if (L.metro) {
    svg += `<g data-infra="metro" class="locality-asset" style="cursor:pointer">
      <path d="${LOCALITY.metro.path}" fill="none" stroke="#5b5f97" stroke-width="5" stroke-dasharray="10 6" opacity="0.85"/>
      <text x="230" y="158" font-size="10" fill="#3c3f66" font-weight="700">Metro corridor — under construction</text>
      ${LOCALITY.metro.stations.map(s => `<circle cx="${s.x}" cy="${s.y}" r="7" fill="#5b5f97" stroke="#fff" stroke-width="2"/>`).join('')}
    </g>`;
  }
  if (L.parks) {
    svg += LOCALITY.parks.map((p, i) => `
      <g data-infra="park:${i}" class="locality-asset" style="cursor:pointer">
        <rect x="${p.x}" y="${p.y}" width="${p.w}" height="${p.h}" rx="10" fill="#cfe8d6" stroke="#3f8f5b" stroke-width="1.5"/>
        <text x="${p.x + 8}" y="${p.y + 16}" font-size="9" fill="#2e6b45" font-weight="700">${p.name}</text>
      </g>`).join('');
  }
  if (L.buildings) {
    svg += LOCALITY.genericBuildings.map(b => `
      <g data-generic="1" class="locality-asset" style="cursor:pointer" opacity="0.55">
        <rect x="${b.x}" y="${b.y}" width="${b.w}" height="${b.h}" fill="#dfe4e8" stroke="#b9c2c9" stroke-dasharray="4 3"/>
        <text x="${b.x + 4}" y="${b.y + b.h / 2}" font-size="8" fill="#8b98a5">${b.name}</text>
      </g>`).join('');
    svg += LOCALITY.buildings.map(b => {
      const useColor = { residential: '#6fa3cc', commercial: '#8ec3dd', mixed: '#7ecbb0' }[b.use] || '#9fc3d8';
      return `
      <g data-asset="${b.id}" class="locality-asset" style="cursor:pointer" filter="url(#bldgGlow)">
        <rect x="${b.x}" y="${b.y}" width="${b.w}" height="${b.h}" fill="${useColor}" stroke="${b.conflict ? '#b64242' : '#1F4E79'}" stroke-width="${b.conflict ? 2.4 : 1.6}" rx="3" class="${b.conflict ? 'conflict-pulse' : ''}"/>
        <rect x="${b.x}" y="${b.y}" width="${b.w}" height="${b.h}" fill="url(#windowGrid)" rx="3"/>
        <text x="${b.x + 6}" y="${b.y + 18}" font-size="10" font-weight="700" fill="#163A5F">${b.name}</text>
        <text x="${b.x + 6}" y="${b.y + 32}" font-size="8.5" fill="${b.conflict ? '#b64242' : '#2e7d5b'}">${b.conflict ? 'Active conflict' : 'Verified'}</text>
      </g>`;
    }).join('');
  }

  const p = STATE.proposedInfra;
  if (p && p.analyzed && p.route) {
    const hasConflict = p.conflicts.length > 0;
    const profile = INFRA_PROFILES[p.type];
    svg += `<g class="path-icon-group">
      <path d="M ${p.route.x1} ${p.route.y1} L ${p.route.x2} ${p.route.y2}" fill="none" stroke="${hasConflict ? '#b64242' : profile.color}" stroke-width="4" stroke-dasharray="10 6" opacity="0.9" class="${hasConflict ? 'conflict-pulse' : ''}"/>
      <text x="${(p.route.x1 + p.route.x2) / 2 - 60}" y="${(p.route.y1 + p.route.y2) / 2 - 10}" font-size="9.5" font-weight="700" fill="${hasConflict ? '#b64242' : '#1f2933'}">Proposed ${profile.label} (${p.depth} m)${hasConflict ? ' — conflict' : ''}</text>
    </g>`;
  }

  return `<svg viewBox="0 0 700 420" width="680" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="aerialBg" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#eef2df"/>
        <stop offset="55%" stop-color="#e4ecda"/>
        <stop offset="100%" stop-color="#dce8e0"/>
      </linearGradient>
      <filter id="bldgGlow" x="-40%" y="-40%" width="180%" height="180%">
        <feDropShadow dx="0" dy="1" stdDeviation="2.6" flood-color="#163A5F" flood-opacity="0.35"/>
      </filter>
      <pattern id="windowGrid" width="9" height="9" patternUnits="userSpaceOnUse">
        <rect width="9" height="9" fill="none"/>
        <rect x="1" y="1" width="6" height="6" fill="#ffffff" opacity="0.12"/>
      </pattern>
    </defs>
    <rect width="700" height="420" fill="url(#aerialBg)"/>
    ${svg}
  </svg>`;
}

function selectBuilding(id) {
  STATE.explorer.scope = 'building';
  STATE.explorer.buildingId = id;
  const defaultLevel = { lakeview: 'floor4', dbtrade: 'f2', mpplaza: 'gf' };
  STATE.explorer.selectedLevel = defaultLevel[id] || null;
  STATE.explorer.mode = '3d';
  STATE.explorer.exploded = false;
  STATE.explorer.xray = false;
  STATE.explorer.underground = false;
  // Show the surrounding infrastructure context automatically on selection
  STATE.explorer.metro = true;
  STATE.explorer.rail = true;
  STATE.explorer.drone = true;
  STATE.explorer.plane = true;
  STATE.explorer.water = true;
  STATE.explorer.gas = true;
  STATE.explorer.electricity = true;
  STATE.explorer.telecom = true;
  STATE.explorer.showRoads = true;
  $all('#viewModeToggle button').forEach(b => b.classList.toggle('active', b.dataset.mode === '3d'));
  $('#explodeBtn').classList.remove('btn-primary');
  $('#xrayBtn').classList.remove('btn-primary');
  $('#undergroundBtn').classList.remove('btn-primary');
  syncLayerCheckboxes();
  renderExplorer();
  toast('Opened ' + getBuildingMeta().name + ' — 3D volume view with surrounding infrastructure');
}

function syncLayerCheckboxes() {
  const map = {
    layerMetro: 'metro', layerRail: 'rail', layerDrone: 'drone', layerPlane: 'plane',
    layerWater: 'water', layerGas: 'gas', layerElectricity: 'electricity', layerTelecom: 'telecom',
    layerRoads: 'showRoads', layerTerrain: 'showTerrain', layerProposed: 'showProposed', layerUtility: 'underground',
  };
  Object.keys(map).forEach(elId => {
    const el = $('#' + elId);
    if (el) el.checked = !!STATE.explorer[map[elId]];
  });
}

function backToLocality() {
  STATE.explorer.scope = 'locality';
  STATE.explorer.buildingId = null;
  STATE.explorer.selectedLevel = null;
  renderExplorer();
}

function renderLocalityEmptyDetail() {
  const host = $('#explorerDetail');
  host.innerHTML = `<div class="detail-empty">${ICONS.layers}<p>Click a building for its full 3D volume view, or click the metro corridor, railway track, or a park for infrastructure details.</p></div>
    <div class="divider"></div>
    <h4 style="font-size:12px;color:var(--text-secondary);margin-bottom:8px">Digitized buildings</h4>
    ${LOCALITY.buildings.map(b => `<div class="detail-row clickable-row" data-asset="${b.id}"><span class="k">${b.name}</span><span class="v">${b.conflict ? '<span class="badge badge-error">Conflict</span>' : '<span class="badge badge-success">Verified</span>'}</span></div>`).join('')}`;
  $all('[data-asset]', host).forEach(el => el.addEventListener('click', () => selectBuilding(el.dataset.asset)));
}

function openInfraDrawer(kind) {
  const overlay = $('#infraDrawer');
  let html = '';
  if (kind === 'metro') {
    html = `
      <div class="drawer-head">
        <div><span class="badge badge-warning">${ICONS.alert}Under construction</span><h3 style="margin-top:8px">MP Nagar Metro Corridor</h3></div>
        <button class="drawer-close" id="closeInfraDrawer"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg></button>
      </div>
      <div class="detail-row"><span class="k">Implementing agency</span><span class="v">Bhopal Metro Rail Corporation (demo)</span></div>
      <div class="detail-row"><span class="k">Alignment</span><span class="v">Elevated viaduct, Phase 2</span></div>
      <div class="detail-row"><span class="k">Stations on this segment</span><span class="v">${LOCALITY.metro.stations.length}</span></div>
      <div class="detail-row"><span class="k">Completion</span><span class="v">61%</span></div>
      <div class="detail-row"><span class="k">Impacted parcels</span><span class="v">3 flagged for clearance review</span></div>
      <div class="plain-explain">Piers along this corridor fall within 4.5 m of DB Trade Centre's registered parcel boundary — flagged for coordination between BMRC and the Municipal Officer.</div>
      <div class="detail-actions"><button class="btn btn-sm" onclick="selectBuilding('dbtrade')">Inspect DB Trade Centre</button></div>`;
  } else if (kind === 'rail') {
    html = `
      <div class="drawer-head">
        <div><span class="badge badge-info">Operational</span><h3 style="margin-top:8px">Railway Track — MP Nagar Approach</h3></div>
        <button class="drawer-close" id="closeInfraDrawer"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg></button>
      </div>
      <div class="detail-row"><span class="k">Managing agency</span><span class="v">Indian Railways (demo)</span></div>
      <div class="detail-row"><span class="k">Alignment</span><span class="v">${LOCALITY.rail.label}</span></div>
      <div class="detail-row"><span class="k">Safety buffer</span><span class="v">15 m from track centreline</span></div>
      <div class="detail-row"><span class="k">Nearby station</span><span class="v">Rani Kamlapati (Habibganj)</span></div>`;
  } else if (kind.startsWith('park:')) {
    const p = LOCALITY.parks[+kind.split(':')[1]];
    html = `
      <div class="drawer-head">
        <div><span class="badge badge-success">Public space</span><h3 style="margin-top:8px">${p.name}</h3></div>
        <button class="drawer-close" id="closeInfraDrawer"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg></button>
      </div>
      <div class="detail-row"><span class="k">Maintained by</span><span class="v">Bhopal Municipal Corporation</span></div>
      <div class="detail-row"><span class="k">Classification</span><span class="v">Public green space — no-build zone</span></div>
      <div class="detail-row"><span class="k">Amenities</span><span class="v">Walking track, seating, play area</span></div>`;
  }
  $('#infraDrawerPanel').innerHTML = html;
  overlay.classList.add('open');
  const closeBtn = $('#closeInfraDrawer');
  if (closeBtn) closeBtn.addEventListener('click', () => overlay.classList.remove('open'));
}

function buildingOptionsHtml(selectedId) {
  return LOCALITY.buildings.map(b => `<option value="${b.id}" ${selectedId === b.id ? 'selected' : ''}>${b.name}</option>`).join('');
}

function renderProposedInfraForm() {
  const p = STATE.proposedInfra;
  $('#proposedFormHost').innerHTML = `
    <div class="field"><label>Infrastructure type</label>
      <select id="proposeType">${Object.keys(INFRA_PROFILES).map(k => `<option value="${k}" ${p.type === k ? 'selected' : ''}>${INFRA_PROFILES[k].label}</option>`).join('')}</select>
    </div>
    <div class="field"><label>From</label><select id="proposeFrom">${buildingOptionsHtml(p.from)}</select></div>
    <div class="field"><label>To</label><select id="proposeTo">${buildingOptionsHtml(p.to)}</select></div>
    <div class="field">
      <label>Width (m)</label>
      <input type="range" min="1" max="12" value="${p.width || 3}" id="proposeWidth">
      <div class="hint" id="proposeWidthVal">${p.width || 3} m</div>
    </div>
    <div class="field">
      <label>Depth below ground (m)</label>
      <input type="range" min="1" max="35" value="${p.depth}" id="proposeDepth">
      <div class="hint" id="proposeDepthVal">${p.depth} m — X, Y position from the From/To route, Z from this depth</div>
    </div>
    <button class="btn btn-primary btn-block" id="runProposeAnalysisBtn">Run 3D Conflict Analysis</button>`;

  $('#proposeType').addEventListener('change', (e) => { p.type = e.target.value; });
  $('#proposeFrom').addEventListener('change', (e) => { p.from = e.target.value; });
  $('#proposeTo').addEventListener('change', (e) => { p.to = e.target.value; });
  $('#proposeWidth').addEventListener('input', (e) => { p.width = +e.target.value; $('#proposeWidthVal').textContent = p.width + ' m'; });
  $('#proposeDepth').addEventListener('input', (e) => { p.depth = +e.target.value; $('#proposeDepthVal').textContent = p.depth + ' m — X, Y position from the From/To route, Z from this depth'; });
  $('#runProposeAnalysisBtn').addEventListener('click', async () => {
    const btn = $('#runProposeAnalysisBtn');
    btn.disabled = true;
    btn.textContent = 'Running analysis…';
    try {
      await analyzeProposedInfra();
      renderProposedMapPreview();
      renderProposedInfraResults();
      toast(p.conflicts.length ? p.conflicts.length + ' conflict(s) detected along the proposed route' : 'No conflicts detected — route is clear');
    } catch (err) {
      toast('Analysis failed: ' + err.message, ICONS.alert);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Run 3D Conflict Analysis';
    }
  });
}

function renderProposedMapPreview() {
  const host = $('#proposedMapHost');
  if (!host) return;
  host.innerHTML = buildLocalitySvg();
}

function renderProposedInfraResults() {
  const p = STATE.proposedInfra;
  const host = $('#proposedResultsHost');
  if (!host) return;
  if (!p.analyzed) {
    host.innerHTML = `<div class="detail-empty">${ICONS.layers}<p>Define a route and depth, then run the analysis to see affected properties, infrastructure, and conflict severity here.</p></div>`;
    return;
  }
  if (p.inspecting !== null) {
    const c = p.conflicts[p.inspecting];
    const m = severityMeta(c.severity);
    host.innerHTML = `
      <button class="btn btn-sm" id="backToProposeResults" style="margin-bottom:12px"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>Back to results</button>
      <span class="badge ${m.badge}"><span class="severity-dot sev-${c.severity}"></span>${m.label}</span>
      <div class="plain-explain">${c.explain}</div>
      <div class="detail-row"><span class="k">Rule violated</span><span class="v" style="text-align:right;max-width:220px">${c.rule}</span></div>
      <div class="detail-row"><span class="k">Affected property</span><span class="v">${c.building}</span></div>
      <div class="detail-row"><span class="k">Level / feature</span><span class="v">${c.level}</span></div>
      <div class="detail-row"><span class="k">ID</span><span class="v mono" style="font-size:11px">${c.id3d}</span></div>
      <div class="detail-row"><span class="k">Recommended action</span><span class="v" style="text-align:right;max-width:220px">${c.severity === 'critical' ? 'Reroute or increase clearance depth before submission' : 'Coordinate with affected property owner before proceeding'}</span></div>
      <div class="detail-actions">
        <button class="btn btn-primary btn-sm" id="openPassportFromConflict">Open Property Passport</button>
        <button class="btn btn-sm" id="viewOnMapFromConflict">View on Map</button>
        <button class="btn btn-sm" id="returnToMapFromConflict">Return to Map</button>
      </div>`;
    $('#backToProposeResults').addEventListener('click', () => { p.inspecting = null; renderProposedInfraResults(); });
    $('#openPassportFromConflict').addEventListener('click', () => { toast('Opening Property Passport for ' + c.building); goToView('passport'); });
    $('#viewOnMapFromConflict').addEventListener('click', () => { goToView('explorer'); selectBuilding(c.buildingId); });
    $('#returnToMapFromConflict').addEventListener('click', () => goToView('explorer'));
    return;
  }

  const hasConflict = p.conflicts.length > 0;
  host.innerHTML = `
    <div class="digsafe-result ${hasConflict ? 'digsafe-prohibited' : 'digsafe-clear'}">
      ${hasConflict ? ICONS.alert : ICONS.check}
      <span>${hasConflict ? p.conflicts.length + ' conflict' + (p.conflicts.length > 1 ? 's' : '') + ' detected along this route' : 'No conflict detected with current infrastructure'}</span>
    </div>
    ${hasConflict ? `<div style="margin-top:12px">${p.conflicts.map((c, i) => {
      const m = severityMeta(c.severity);
      return `
      <div class="result-card" style="padding:11px" data-idx="${i}">
        <div class="result-thumb" style="background:${c.severity === 'critical' ? 'var(--error)' : 'var(--warning)'}">${ICONS.alert}</div>
        <div class="result-body"><div class="addr" style="font-size:12.5px">${c.building}</div><div class="ids" style="font-size:11px">${c.level}</div></div>
        <span class="badge ${m.badge}">${m.label}</span>
      </div>`;
    }).join('')}</div>` : ''}
    <button class="btn btn-sm btn-block" id="returnToMapClear" style="margin-top:12px">Return to Map</button>`;

  $all('.result-card', host).forEach(el => el.addEventListener('click', () => { p.inspecting = +el.dataset.idx; renderProposedInfraResults(); }));
  $('#returnToMapClear').addEventListener('click', () => goToView('explorer'));
}

function initProposedInfraPage() {
  renderProposedInfraForm();
  renderProposedMapPreview();
  renderProposedInfraResults();
}

/* ---------------------------------------------------------------- UNDERGROUND / X-RAY PAGE */

STATE.underground = { buildingId: 'lakeview', mode: 'surface', selectedLevel: 'floor4' };

function renderUndergroundPage() {
  const u = STATE.underground;
  $('#undergroundBuildingSwitch').innerHTML = LOCALITY.buildings.map(b => `
    <button class="btn btn-sm ${b.id === u.buildingId ? 'btn-primary' : ''}" data-uswitch="${b.id}">${b.name}</button>`).join('');
  $all('[data-uswitch]', $('#undergroundBuildingSwitch')).forEach(btn => btn.addEventListener('click', () => {
    u.buildingId = btn.dataset.uswitch;
    const defaults = { lakeview: 'floor4', dbtrade: 'f2', mpplaza: 'gf' };
    u.selectedLevel = defaults[u.buildingId] || null;
    renderUndergroundPage();
  }));

  const ctx = {
    buildingId: u.buildingId, selectedLevel: u.selectedLevel, mode: '3d', exploded: false,
    xray: u.mode === 'xray', underground: u.mode === 'underground', metro: u.mode === 'underground',
    forceFade: u.mode !== 'surface',
    pointCloud: false, lidar: false, floorplan: false, gnss: false, drone: false, plane: false,
  };
  $('#undergroundViewport').innerHTML = `<div style="display:flex;justify-content:center">${buildExplorerSvg(ctx)}</div>`;
  $all('[data-level]', $('#undergroundViewport')).forEach(g => g.addEventListener('click', () => {
    u.selectedLevel = g.dataset.level;
    renderUndergroundPage();
  }));

  const levels = getLevels(u.buildingId);
  const detail = getLevelDetail(u.buildingId);
  const meta = u.buildingId === 'lakeview' ? LAKEVIEW_META : BUILDINGS_EXTRA[u.buildingId].meta;
  const d = u.selectedLevel ? detail[u.selectedLevel] : null;
  const level = u.selectedLevel ? levels.find(l => l.id === u.selectedLevel) : null;
  const dHost = $('#undergroundDetail');
  dHost.innerHTML = `
    <div class="detail-head">
      <h3>${meta.name}</h3>
      <div class="idline">Mode: ${u.mode === 'surface' ? 'Surface' : u.mode === 'xray' ? 'X-Ray' : 'Underground'}</div>
    </div>
    ${level && d ? `
      <div class="detail-row"><span class="k">Selected level</span><span class="v">${level.label}</span></div>
      <div class="detail-row"><span class="k">Elevation</span><span class="v">${d.elevation}</span></div>
      <div class="detail-row"><span class="k">Confidence</span><span class="v">${d.confidence}/100</span></div>` : ''}
    <div class="divider"></div>
    <h4 style="font-size:12px;color:var(--text-secondary);margin-bottom:8px">Depth reference</h4>
    <div class="detail-row"><span class="k"><span class="severity-dot" style="background:#2e7d5b"></span> Sewer Line</span><span class="v">-5 m</span></div>
    <div class="detail-row"><span class="k"><span class="severity-dot" style="background:#c8831a"></span> Electric Cable</span><span class="v">-10 m</span></div>
    <div class="detail-row"><span class="k"><span class="severity-dot" style="background:#2563a9"></span> Water Pipeline</span><span class="v">-15 m</span></div>
    <div class="detail-row"><span class="k"><span class="severity-dot" style="background:#5b5f97"></span> Metro Tunnel</span><span class="v">-30 m${u.mode === 'underground' ? ' (visible)' : ''}</span></div>
    <div class="detail-actions" style="margin-top:14px">
      <button class="btn btn-sm" data-view="vstack">Open Vertical Stack</button>
      <button class="btn btn-sm" data-view="conflicts">Check Conflicts</button>
    </div>`;
  $all('[data-view]', dHost).forEach(el => el.addEventListener('click', () => {
    if (el.dataset.view === 'vstack') STATE.vstackBuildingId = u.buildingId;
    goToView(el.dataset.view);
  }));
}

function initUndergroundPage() {
  $('#undergroundModeToggle').addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    $all('button', e.currentTarget).forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    STATE.underground.mode = btn.dataset.umode;
    renderUndergroundPage();
  });
}

/* ---------------------------------------------------------------- USER & ROLE MANAGEMENT */

var PERMISSION_MATRIX = []; /* hydrated by api.js */

var DEMO_USERS = []; /* hydrated by api.js */

function renderUsersPage() {
  $('#permissionMatrixBody').innerHTML = PERMISSION_MATRIX.map(row => `
    <tr>
      <td data-label="Module">${row[0]}</td>
      ${row.slice(1).map((v, i) => `<td data-label="${['Government / Planner', 'Constructor / Engineer', 'Architect / Surveyor', 'Public User'][i]}">${v === true ? '<span class="badge badge-success">' + ICONS.check + 'Full</span>' : v === false ? '<span class="badge badge-neutral">—</span>' : '<span class="badge badge-info">' + v + '</span>'}</td>`).join('')}
    </tr>`).join('');

  const addBtn = $('#addUserBtn');
  if (addBtn && !addBtn.dataset.wired) {
    addBtn.dataset.wired = '1';
    addBtn.addEventListener('click', async () => {
      const name = prompt('Full name');
      if (!name) return;
      const email = prompt('Email address');
      if (!email) return;
      const role = prompt('Role — one of: planner, constructor, surveyor, public', 'public');
      if (!role) return;
      const password = prompt('Temporary password (min 8 characters)');
      if (!password) return;
      const organization = prompt('Organization (optional)') || null;
      try {
        await API.createUser({ name, email, password, role: role.trim(), organization });
        await hydrateAdminUsers();
        renderUsersPage();
        toast(name + ' added as ' + role);
      } catch (err) {
        const detail = err.errors && err.errors.length
          ? err.errors.map(x => x.field + ': ' + x.message).join('; ')
          : err.message;
        toast('Could not add user: ' + detail, ICONS.alert);
      }
    });
  }

  $('#usersTableBody').innerHTML = DEMO_USERS.map(u => `
    <tr>
      <td data-label="Name">${u.name}</td>
      <td data-label="Role">${u.role}</td>
      <td data-label="Organization">${u.org}</td>
      <td data-label="Last active">${u.active}</td>
      <td data-label="Status"><span class="badge ${u.status === 'Active' ? 'badge-success' : 'badge-neutral'}">${u.status}</span></td>
    </tr>`).join('');
}

function updateExplorerChrome() {
  const inBuilding = STATE.explorer.scope === 'building';
  $('#localityLayerGroup').style.display = inBuilding ? 'none' : 'block';
  $('#buildingLayerGroup').style.display = inBuilding ? 'block' : 'none';
  $('#localityBackBtn').style.display = inBuilding ? 'inline-flex' : 'none';
  $('#viewModeToggle').style.display = inBuilding ? 'flex' : 'none';
  $('#localityViewToggle').style.display = inBuilding ? 'none' : 'flex';
  $('#explodeBtn').style.display = inBuilding ? 'inline-flex' : 'none';
  $('#xrayBtn').style.display = inBuilding ? 'inline-flex' : 'none';
  $('#undergroundBtn').style.display = inBuilding ? 'inline-flex' : 'none';
  $('#vstackBtn').style.display = inBuilding ? 'inline-flex' : 'none';
  $('#proposeInfraBtn').style.display = inBuilding ? 'none' : 'inline-flex';

  if (inBuilding) {
    const meta = getBuildingMeta();
    $('#explorerBreadcrumb').textContent = meta.name;
    $('#viewportCaption').textContent = meta.name + ', ' + meta.address + ' — isometric sample geometry';
    $('#viewportHint').textContent = 'Click any level or unit to inspect it. Use Explode / X-ray / Underground to change the view.';
    $('#buildingSummary').innerHTML = `<strong style="color:var(--navy-900)">${meta.name}</strong><br>${meta.floors} floors · ${meta.basements} basement${meta.basements === 1 ? '' : 's'}<br>Parent ULPIN <span class="mono">${meta.parent}</span>`;
  } else {
    $('#explorerBreadcrumb').textContent = 'MP Nagar Locality';
    if (STATE.explorer.localityViewMode === 'schematic') {
      $('#viewportCaption').textContent = 'MP Nagar, Bhopal — locality map, demo dataset';
      $('#viewportHint').textContent = 'Click a building to open its 3D volume view. Click the metro corridor, railway track, or a park for infrastructure details.';
    } else {
      $('#viewportCaption').textContent = 'MP Nagar, Bhopal — live ' + (STATE.explorer.localityViewMode === 'satellite' ? 'satellite' : 'road') + ' map';
      $('#viewportHint').textContent = 'This is a live map for real-world orientation. Use the building list on the right, or switch to Schematic, to select a property.';
    }
  }
}

function refreshExplorerDetail() {
  if (STATE.explorer.scope === 'locality') renderLocalityEmptyDetail();
  else renderExplorerDetail();
}

/* ---------------------------------------------------------------- SYNCHRONIZED BOTTOM PANELS */

function buildFloorPlanSvg(bid, level, detail, meta) {
  if (!level) {
    return `<div class="empty-state" style="padding:20px 6px"><p>Select a building and floor to see its floor plan.</p></div>`;
  }
  const isResidentialFloor = /apartment/i.test(detail.type) && !level.below;
  const numPrefix = (level.tag || '').replace(/[^0-9]/g, '') || '0';
  const isFlagship = bid === 'lakeview' && level.id === 'floor4';
  if (isResidentialFloor) {
    const units = [numPrefix + '01', numPrefix + '02', numPrefix + '03', numPrefix + '04'];
    const selUnit = isFlagship ? numPrefix + '02' : units[0];
    return `<svg viewBox="0 0 240 150" width="100%" height="140" xmlns="http://www.w3.org/2000/svg">
      <rect x="4" y="4" width="232" height="142" fill="none" stroke="#d7e0e7"/>
      <rect x="4" y="4" width="112" height="70" fill="${units[0] === selUnit ? '#bcd4e6' : '#eef2f5'}" stroke="#8b98a5"/>
      <rect x="120" y="4" width="116" height="70" fill="${units[1] === selUnit ? '#bcd4e6' : '#eef2f5'}" stroke="#8b98a5"/>
      <rect x="4" y="78" width="112" height="68" fill="${units[2] === selUnit ? '#bcd4e6' : '#eef2f5'}" stroke="#8b98a5"/>
      <rect x="120" y="78" width="116" height="68" fill="${units[3] === selUnit ? '#bcd4e6' : '#eef2f5'}" stroke="#8b98a5"/>
      <rect x="108" y="4" width="20" height="142" fill="#c7ced4" stroke="#8b98a5"/>
      <text x="118" y="76" font-size="7" fill="#425867" text-anchor="middle" transform="rotate(-90 118,76)">Lift / Stair</text>
      <text x="60" y="42" font-size="11" font-weight="700" fill="#163A5F" text-anchor="middle">${units[0]}</text>
      <text x="178" y="42" font-size="11" font-weight="700" fill="#163A5F" text-anchor="middle">${units[1]}</text>
      <text x="60" y="115" font-size="11" font-weight="700" fill="#163A5F" text-anchor="middle">${units[2]}</text>
      <text x="178" y="115" font-size="11" font-weight="700" fill="#163A5F" text-anchor="middle">${units[3]}</text>
    </svg>
    <div style="font-size:11.5px;color:var(--text-secondary);margin-top:4px">
      <strong style="color:var(--navy-900)">Unit ${selUnit}</strong> — ${isFlagship ? UNIT_402.area : '~90 m²'} · ${level.label} · ${detail.id3d}
    </div>`;
  }
  return `<svg viewBox="0 0 240 150" width="100%" height="140" xmlns="http://www.w3.org/2000/svg">
    <rect x="4" y="4" width="232" height="142" fill="#eef2f5" stroke="#d7e0e7"/>
    <text x="120" y="78" font-size="11" fill="#425867" text-anchor="middle">${detail.type}</text>
    <text x="120" y="94" font-size="9" fill="#8b98a5" text-anchor="middle">Open-plan — not individually subdivided</text>
  </svg>
  <div style="font-size:11.5px;color:var(--text-secondary);margin-top:4px">${level.label} · ${detail.area} · ${detail.id3d}</div>`;
}

function renderFloorPlanPanel() {
  const host = $('#floorPlanPanel');
  const sub = $('#floorPlanSubtitle');
  if (!host) return;
  if (STATE.explorer.scope !== 'building' || !STATE.explorer.selectedLevel) {
    sub.textContent = '';
    host.innerHTML = `<div class="empty-state" style="padding:20px 6px"><p>Select a building and floor in the 3D view to see its floor plan here.</p></div>`;
    return;
  }
  const meta = getBuildingMeta();
  const levels = getLevels();
  const detail = getLevelDetail();
  const level = levels.find(l => l.id === STATE.explorer.selectedLevel);
  const d = detail[STATE.explorer.selectedLevel];
  sub.textContent = `(${meta.name} — ${level ? level.label : ''})`;
  host.innerHTML = buildFloorPlanSvg(STATE.explorer.buildingId, level, d, meta);
}

function buildUndergroundCrossSvg() {
  const rows = [
    { label: 'Ground Level', depth: '0 m', color: '#a9c19a' },
    { label: 'Sewer Line', depth: '-5 m', color: '#2e7d5b' },
    { label: 'Telecom / Fiber', depth: '-8 m', color: '#3f8f5b' },
    { label: 'Electricity', depth: '-10 m', color: '#c8831a' },
    { label: 'Gas', depth: '-12 m', color: '#d9702e' },
    { label: 'Water Pipeline', depth: '-15 m', color: '#2563a9' },
    { label: 'Metro Tunnel', depth: '-30 m', color: '#5b5f97' },
  ];
  const rowH = 20;
  const top = 30;
  let rowsSvg = rows.map((r, i) => `
    <line x1="70" y1="${top + i * rowH}" x2="230" y2="${top + i * rowH}" stroke="${r.color}" stroke-width="4" stroke-linecap="round"/>
    <circle cx="70" cy="${top + i * rowH}" r="3.4" fill="${r.color}" stroke="#fff" stroke-width="1"/>
    <text x="4" y="${top + i * rowH + 3}" font-size="8" fill="#425867">${r.label}</text>
    <text x="236" y="${top + i * rowH + 3}" font-size="8" font-weight="700" fill="${r.color}">${r.depth}</text>`).join('');
  return `<svg viewBox="0 0 300 ${top + rows.length * rowH + 6}" width="100%" xmlns="http://www.w3.org/2000/svg">
    <rect x="120" y="2" width="30" height="20" fill="#9fc3d8" stroke="#6c93b3"/>
    <text x="135" y="15" font-size="7" fill="#163A5F" text-anchor="middle">Bldg</text>
    <line x1="135" y1="22" x2="135" y2="${top}" stroke="#8b98a5" stroke-width="1" stroke-dasharray="2 2"/>
    ${rowsSvg}
  </svg>`;
}

function renderUndergroundCrossPanel() {
  const host = $('#undergroundCrossPanel');
  if (!host) return;
  host.innerHTML = buildUndergroundCrossSvg();
}

function renderConflictDetectPanel() {
  const host = $('#conflictDetectPanel');
  if (!host) return;
  if (STATE.explorer.scope !== 'building' || !STATE.explorer.selectedLevel) {
    host.innerHTML = `<div class="empty-state" style="padding:16px 6px"><p>Select a building and floor to run conflict detection for that specific level.</p></div>`;
    return;
  }
  const meta = getBuildingMeta();
  const levels = getLevels();
  const detail = getLevelDetail();
  const level = levels.find(l => l.id === STATE.explorer.selectedLevel);
  const d = detail[STATE.explorer.selectedLevel];
  if (!d || !d.conflict) {
    host.innerHTML = `
      <div class="digsafe-result digsafe-clear" style="margin-bottom:10px">${ICONS.check}<span>No Conflict Detected</span></div>
      <div style="font-size:11.5px;color:var(--text-secondary)">${level ? level.label : ''} at ${meta.name} has no recorded intersections with existing or proposed infrastructure.</div>`;
    return;
  }
  const relatedConflict = CONFLICTS.find(c => c.prop.toLowerCase().includes((level.label || '').toLowerCase()) || (STATE.explorer.buildingId === 'lakeview' && level.id === 'floor4' && c.prop === 'Apartment 402'));
  const existing = relatedConflict ? relatedConflict.type : 'Basement / utility overlap';
  const depthNote = STATE.explorer.buildingId === 'lakeview' && level.id === 'b2' ? 'Sewer Line -5 m' : STATE.explorer.buildingId === 'lakeview' && level.id === 'floor4' ? 'Fire-escape volume, Level 4' : 'Adjacent utility volume';
  host.innerHTML = `
    <div class="digsafe-result digsafe-prohibited" style="margin-bottom:10px">${ICONS.alert}<span>Potential Conflict Detected</span></div>
    <div class="detail-row"><span class="k">Conflict type</span><span class="v" style="text-align:right;max-width:150px">${existing}</span></div>
    <div class="detail-row"><span class="k">Existing</span><span class="v" style="text-align:right;max-width:150px">${depthNote}</span></div>
    <div class="detail-row"><span class="k">Level</span><span class="v">${level.label}</span></div>
    <button class="btn btn-sm btn-danger btn-block" id="conflictDetectViewBtn" style="margin-top:8px">View Details</button>`;
  const btn = $('#conflictDetectViewBtn');
  if (btn) btn.addEventListener('click', () => {
    goToView('conflicts');
    if (relatedConflict) openConflictDrawer(relatedConflict);
  });
}

function renderBottomPanels() {
  renderFloorPlanPanel();
  renderUndergroundCrossPanel();
  renderConflictDetectPanel();
}

function renderExplorer() {
  const host = $('#buildingSvgHost');
  if (STATE.explorer.scope === 'locality') {
    if (STATE.explorer.localityViewMode === 'schematic') {
      host.classList.remove('map-embed-host');
      host.innerHTML = buildLocalitySvg();
    } else {
      host.classList.add('map-embed-host');
      host.innerHTML = buildLiveMapHtml();
    }
    wireLocalityAssetHandlers(host);
  } else {
    host.classList.remove('map-embed-host');
    host.innerHTML = STATE.explorer.mode === '2d' ? build2DPlanSvg() : buildExplorerSvg();
    $all('[data-level]', host).forEach(g => {
      g.addEventListener('click', () => {
        STATE.explorer.selectedLevel = g.dataset.level;
        renderExplorer();
      });
    });
  }
  updateExplorerChrome();
  refreshExplorerDetail();
  renderBottomPanels();
}

function buildingConflictSummary(bid) {
  const { levels, detail } = buildingLevelSet(bid);
  const flagged = levels.filter(l => detail[l.id] && detail[l.id].conflict);
  if (!flagged.length) return null;
  const relevant = bid === 'lakeview' ? CONFLICTS.filter(c => !c.buildingId || c.buildingId === 'lakeview') : [];
  const worst = relevant.length ? relevant.reduce((a, c) => (severityRank(c.sev) > severityRank(a.sev) ? c : a), relevant[0]) : null;
  return {
    count: flagged.length,
    severity: worst ? worst.sev : (bid === 'lakeview' ? 'critical' : 'medium'),
    type: worst ? worst.type : 'Basement / utility overlap',
    overlap: worst ? worst.vol : '—',
    affectedLevels: flagged.map(l => l.label).join(', '),
    recommended: worst && severityMeta(worst.sev).label === 'Critical' ? 'Reroute or resurvey before approval' : 'Coordinate with affected party before proceeding',
  };
}

function severityRank(sev) {
  return { critical: 4, high: 3, medium: 2, low: 1, clear: 0 }[sev] || 0;
}

function renderExplorerDetail() {
  const host = $('#explorerDetail');
  const meta = getBuildingMeta();
  const levels = getLevels();
  const levelDetail = getLevelDetail();
  const isPublic = STATE.role === 'public';
  const conflictSummary = buildingConflictSummary(STATE.explorer.buildingId || 'lakeview');

  const overviewHtml = `
    <div class="detail-head">
      <div class="verified-row">
        <span class="badge ${meta.validationStatus === 'Verified' ? 'badge-success' : 'badge-warning'}">${meta.validationStatus === 'Verified' ? ICONS.check : ICONS.alert}${meta.validationStatus}</span>
        ${conflictSummary ? `<span class="badge ${severityMeta(conflictSummary.severity).badge}"><span class="severity-dot sev-${conflictSummary.severity}"></span>${conflictSummary.count} conflict${conflictSummary.count > 1 ? 's' : ''}</span>` : '<span class="badge badge-success">' + ICONS.check + 'No conflicts</span>'}
      </div>
      <h3>${meta.name}</h3>
      <div class="idline">${meta.parent}</div>
    </div>
    <h4 style="font-size:11px;text-transform:uppercase;letter-spacing:.03em;color:var(--text-secondary);margin:10px 0 4px">Identification</h4>
    <div class="detail-row"><span class="k">Survey number</span><span class="v">${meta.surveyNo}</span></div>
    <div class="detail-row"><span class="k">Ward / Zone</span><span class="v">${meta.ward} · ${meta.zone}</span></div>
    <div class="detail-row"><span class="k">Location</span><span class="v" style="text-align:right;max-width:170px">${meta.address}</span></div>
    <div class="detail-row"><span class="k">Coordinates</span><span class="v mono" style="font-size:11px">${typeof meta.lat === 'number' ? meta.lat.toFixed(4) + ', ' + meta.lng.toFixed(4) : 'Not surveyed'}</span></div>
    <h4 style="font-size:11px;text-transform:uppercase;letter-spacing:.03em;color:var(--text-secondary);margin:10px 0 4px">Land Information</h4>
    <div class="detail-row"><span class="k">Land use</span><span class="v">${meta.landUse}</span></div>
    <div class="detail-row"><span class="k">Boundary dimensions</span><span class="v">${meta.boundaryDims}</span></div>
    <div class="detail-row"><span class="k">Floors / basements</span><span class="v">${meta.floors} / ${meta.basements}</span></div>
    <div class="detail-row"><span class="k">Status</span><span class="v">${meta.status}</span></div>
    ${!isPublic ? `
    <h4 style="font-size:11px;text-transform:uppercase;letter-spacing:.03em;color:var(--text-secondary);margin:10px 0 4px">Ownership</h4>
    <div class="detail-row"><span class="k">Ownership type</span><span class="v">${meta.ownershipType}</span></div>
    <h4 style="font-size:11px;text-transform:uppercase;letter-spacing:.03em;color:var(--text-secondary);margin:10px 0 4px">Survey</h4>
    <div class="detail-row"><span class="k">Survey accuracy</span><span class="v">${meta.surveyAccuracy}</span></div>
    <div class="detail-row"><span class="k">GNSS</span><span class="v" style="text-align:right;max-width:170px">${meta.gnss}</span></div>
    <div class="detail-row"><span class="k">LiDAR</span><span class="v">${meta.lidarAvailability}</span></div>` : ''}
    <h4 style="font-size:11px;text-transform:uppercase;letter-spacing:.03em;color:var(--text-secondary);margin:10px 0 4px">Infrastructure</h4>
    <div class="detail-row"><span class="k">Roads</span><span class="v" style="text-align:right;max-width:170px">${meta.infra.roads}</span></div>
    <div class="detail-row"><span class="k">Metro</span><span class="v" style="text-align:right;max-width:170px">${meta.infra.metro}</span></div>
    <div class="detail-row"><span class="k">Water</span><span class="v">${meta.infra.water}</span></div>
    <div class="detail-row"><span class="k">Gas</span><span class="v">${meta.infra.gas}</span></div>
    <div class="detail-row"><span class="k">Electricity</span><span class="v">${meta.infra.electricity}</span></div>
    <div class="detail-row"><span class="k">Underground utilities</span><span class="v" style="text-align:right;max-width:170px">${meta.infra.underground}</span></div>
    ${conflictSummary ? `
    <h4 style="font-size:11px;text-transform:uppercase;letter-spacing:.03em;color:var(--text-secondary);margin:10px 0 4px">Conflicts</h4>
    <div class="detail-row"><span class="k">Severity</span><span class="v">${severityMeta(conflictSummary.severity).label}</span></div>
    <div class="detail-row"><span class="k">Type</span><span class="v" style="text-align:right;max-width:170px">${conflictSummary.type}</span></div>
    <div class="detail-row"><span class="k">Overlap</span><span class="v">${conflictSummary.overlap}</span></div>
    <div class="detail-row"><span class="k">Affected levels</span><span class="v" style="text-align:right;max-width:170px">${conflictSummary.affectedLevels}</span></div>
    <div class="detail-row"><span class="k">Recommended action</span><span class="v" style="text-align:right;max-width:170px">${conflictSummary.recommended}</span></div>` : ''}
    <div class="detail-actions" style="margin-top:12px">
      <button class="btn btn-primary btn-sm" data-view="passport">Open Property Passport</button>
      <button class="btn btn-sm" id="detailShowUnderground">Show Underground</button>
      <button class="btn btn-sm" id="detailMeasure">Measure</button>
      <button class="btn btn-sm" id="detailViewInfra">View Infrastructure</button>
      ${conflictSummary ? '<button class="btn btn-sm btn-danger" data-view="conflicts">Check Conflicts</button>' : ''}
      <button class="btn btn-teal btn-sm" id="detailGenReport">Generate Report</button>
    </div>
    <div class="divider"></div>`;

  const floorChipsHtml = `
    <h4 style="font-size:11px;text-transform:uppercase;letter-spacing:.03em;color:var(--text-secondary);margin-bottom:8px">Floors</h4>
    <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:14px">
      ${levels.map(l => `<button class="btn btn-sm ${l.id === STATE.explorer.selectedLevel ? 'btn-primary' : ''}" data-floorchip="${l.id}" style="position:relative">${l.label}${levelDetail[l.id] && levelDetail[l.id].conflict ? '<span class="severity-dot sev-critical" style="margin-left:5px"></span>' : ''}</button>`).join('')}
    </div>`;

  const levelId = STATE.explorer.selectedLevel;
  const d = levelId ? levelDetail[levelId] : null;
  const level = levelId ? levels.find(l => l.id === levelId) : null;
  let floorDetailHtml;
  if (!d || !level) {
    floorDetailHtml = `<div class="detail-empty">${ICONS.layers}<p>Select a floor above, or click a level in the 3D view.</p></div>`;
  } else {
    const conf = confidenceLabel(d.confidence);
    const isFlagshipUnit = STATE.explorer.buildingId === 'lakeview' && levelId === 'floor4';
    const ownerLine = isPublic ? (d.owner || 'Common') : (isFlagshipUnit ? UNIT_402.ownerFull + ' (verified)' : (d.owner || 'Common'));
    floorDetailHtml = `
      <div class="verified-row" style="margin-bottom:6px">
        <span class="badge ${d.confidence >= 90 ? 'badge-success' : d.confidence >= 70 ? 'badge-info' : 'badge-warning'}">${ICONS.check}${conf.label}</span>
        ${d.conflict ? '<span class="badge badge-error">' + ICONS.alert + 'Conflict</span>' : ''}
      </div>
      <h3 style="font-size:14.5px">${level.label}${isFlagshipUnit ? ' — Apartment 402' : ''}</h3>
      <div class="idline" style="margin-bottom:8px">${d.id3d}</div>
      <div class="detail-row"><span class="k">Property type</span><span class="v">${d.type}</span></div>
      <div class="detail-row"><span class="k">Elevation range</span><span class="v">${d.elevation}</span></div>
      <div class="detail-row"><span class="k">Area</span><span class="v">${d.area}</span></div>
      <div class="detail-row"><span class="k">Volume</span><span class="v">${d.volume}</span></div>
      <div class="detail-row"><span class="k">Ownership</span><span class="v">${ownerLine}</span></div>
      <div class="detail-row"><span class="k">Airspace / air-rights</span><span class="v">${d.airspace ? 'Air-rights zone applies' : 'Not applicable'}</span></div>
      <div class="detail-row"><span class="k">Survey source</span><span class="v">${d.source}</span></div>
      <div class="confidence-ring-row">
        <span class="num" style="color:${conf.color}">${d.confidence}</span>
        <span class="lab">/100 — ${conf.label}<br>Source 35% · Geometry 30% · Freshness 20% · Verification 15%</span>
      </div>
      <div class="detail-actions">
        <button class="btn btn-sm">Inspect Geometry</button>
        <button class="btn btn-sm">View Documents</button>
        ${d.conflict ? '<button class="btn btn-sm btn-danger" data-view="conflicts">View Conflict</button>' : ''}
        <button class="btn btn-teal btn-sm">Generate QR</button>
      </div>`;
  }

  host.innerHTML = overviewHtml + floorChipsHtml + '<div id="floorDetailHost">' + floorDetailHtml + '</div>';

  $all('[data-view]', host).forEach(el => el.addEventListener('click', () => goToView(el.dataset.view)));
  $all('[data-floorchip]', host).forEach(el => el.addEventListener('click', () => {
    STATE.explorer.selectedLevel = el.dataset.floorchip;
    renderExplorer();
  }));
  const showUgBtn = $('#detailShowUnderground');
  if (showUgBtn) showUgBtn.addEventListener('click', () => { STATE.underground.buildingId = STATE.explorer.buildingId || 'lakeview'; goToView('underground'); });
  const measureBtn = $('#detailMeasure');
  if (measureBtn) measureBtn.addEventListener('click', () => toast('Measurement tool: click two points in the 3D view to measure distance (prototype placeholder)'));
  const infraBtn = $('#detailViewInfra');
  if (infraBtn) infraBtn.addEventListener('click', () => goToView('utility'));
  const reportBtn = $('#detailGenReport');
  if (reportBtn) reportBtn.addEventListener('click', () => { toast('Generating property report for ' + meta.name); goToReportsTab(); });
}

var VSTACK_ROAD_INFO = {}; /* hydrated by api.js */

function buildingLevelSet(bid) {
  if (bid === 'lakeview') return { levels: LEVELS, detail: LEVEL_DETAIL, meta: LAKEVIEW_META };
  const b = BUILDINGS_EXTRA[bid];
  return { levels: b.levels, detail: b.detail, meta: b.meta };
}

function vcard(l, d, bid) {
  const isPublic = STATE.role === 'public';
  const isFlagshipUnit = bid === 'lakeview' && l.id === 'floor4';
  const owner = isPublic ? (d.owner || 'Common') : (isFlagshipUnit ? UNIT_402.ownerFull + ' (verified)' : (d.owner || 'Common'));
  return `<div class="vcard" data-level="${l.id}" data-building="${bid}">
    <div class="vc-lab">${l.label}${d.conflict ? '<span class="badge badge-error" style="padding:1px 6px">!</span>' : ''}</div>
    <div class="vc-row"><span>Type</span><span>${d.type}</span></div>
    <div class="vc-row"><span>Owner</span><span>${owner}</span></div>
    <div class="vc-row"><span>Confidence</span><span>${d.confidence}/100</span></div>
    <span class="vc-air ${d.airspace ? 'yes' : 'no'}">${d.airspace ? 'Airspace rights apply' : 'No airspace rights'}</span>
  </div>`;
}

function vstackBand(title, subtitle, innerHtml, tone) {
  return `<div class="card" style="margin-bottom:12px; border-left:4px solid ${tone}">
    <div class="card-title-row"><h3>${title}</h3></div>
    ${subtitle ? `<div style="font-size:12px;color:var(--text-secondary);margin-bottom:10px">${subtitle}</div>` : ''}
    ${innerHtml}
  </div>`;
}

function renderVerticalStackPage() {
  const bid = STATE.vstackBuildingId || STATE.explorer.buildingId || 'lakeview';
  STATE.vstackBuildingId = bid;
  const { levels, detail, meta } = buildingLevelSet(bid);

  $('#vstackBuildingSwitch').innerHTML = LOCALITY.buildings.map(b => `
    <button class="btn btn-sm ${b.id === bid ? 'btn-primary' : ''}" data-switch-building="${b.id}">${b.name}</button>`).join('');
  $all('[data-switch-building]', $('#vstackBuildingSwitch')).forEach(btn => btn.addEventListener('click', () => {
    STATE.vstackBuildingId = btn.dataset.switchBuilding;
    renderVerticalStackPage();
  }));

  const airspaceLevels = levels.filter(l => !l.below && detail[l.id] && detail[l.id].airspace);
  const floorLevels = levels.filter(l => !l.below && detail[l.id] && !detail[l.id].airspace && l.id !== 'ground' && l.id !== 'gf');
  const groundLevel = levels.find(l => l.id === 'ground' || l.id === 'gf');
  const belowLevels = levels.filter(l => l.below);

  const host = $('#vstackBands');
  host.innerHTML =
    vstackBand('Airspace', 'Terrace, roof, and upper amenity levels — air-rights zones.',
      `<div class="vcard-row">${airspaceLevels.map(l => vcard(l, detail[l.id], bid)).join('') || '<p style="font-size:12px;color:var(--text-faint)">No airspace-designated levels for this building.</p>'}</div>`, '#9fc3d8') +
    vstackBand('Building Floors', `${meta.name} — ${meta.floors} floors above ground.`,
      `<div class="vcard-row">${floorLevels.map(l => vcard(l, detail[l.id], bid)).join('')}</div>`, 'var(--navy-700)') +
    vstackBand('Ground', 'Grade level — where the building meets the parcel surface.',
      groundLevel ? `<div class="vcard-row">${vcard(groundLevel, detail[groundLevel.id], bid)}</div>` : '<p style="font-size:12px;color:var(--text-faint)">No ground-level record.</p>', 'var(--teal-700)') +
    vstackBand('Road / Surface Infrastructure', 'Adjacent roads and surface-level transit context.',
      `<p style="font-size:12.5px;color:var(--text-secondary)">${VSTACK_ROAD_INFO[bid] || 'No surface infrastructure notes.'}</p>`, '#b9c2c9') +
    vstackBand('Underground Utilities', 'Basements, parking, and shallow utility lines (0–6 m below grade).',
      `<div class="vcard-row">${belowLevels.map(l => vcard(l, detail[l.id], bid)).join('')}</div>
       <div class="divider"></div>
       <div class="detail-row"><span class="k"><span class="severity-dot" style="background:#2e7d5b"></span> Sewer Line</span><span class="v">-5 m</span></div>
       <div class="detail-row"><span class="k"><span class="severity-dot" style="background:#c8831a"></span> Electric Cable</span><span class="v">-10 m</span></div>
       <div class="detail-row"><span class="k"><span class="severity-dot" style="background:#2563a9"></span> Water Pipeline</span><span class="v">-15 m</span></div>`, 'var(--warning)') +
    vstackBand('Metro / Pipeline', 'Mid-depth transit and trunk infrastructure (15–30 m below grade).',
      `<div class="detail-row"><span class="k"><span class="severity-dot" style="background:#5b5f97"></span> Metro Tunnel — Line 2</span><span class="v">-30 m (under construction)</span></div>
       ${STATE.proposedInfra.analyzed && [STATE.proposedInfra.from, STATE.proposedInfra.to].includes(bid) ? `<div class="detail-row"><span class="k">Proposed ${INFRA_PROFILES[STATE.proposedInfra.type].label}</span><span class="v">${STATE.proposedInfra.depth} m${STATE.proposedInfra.conflicts.length ? ' — conflict' : ' — clear'}</span></div>` : ''}`, '#5b5f97') +
    vstackBand('Deep Underground Infrastructure', 'Reserved corridors below 30 m for future utility and transit expansion.',
      `<p style="font-size:12.5px;color:var(--text-secondary)">No active infrastructure recorded below 30 m for this parcel.</p>`, 'var(--navy-900)');

  $all('.vcard', host).forEach(card => card.addEventListener('click', () => {
    goToView('explorer');
    selectBuilding(card.dataset.building);
    STATE.explorer.selectedLevel = card.dataset.level;
    renderExplorer();
  }));
}

function initExplorer() {
  $('#viewModeToggle').addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    $all('button', e.currentTarget).forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    STATE.explorer.mode = btn.dataset.mode;
    toast('Switched to ' + btn.dataset.mode.toUpperCase() + ' view');
    renderExplorer();
  });

  $('#localityViewToggle').addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    $all('button', e.currentTarget).forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    STATE.explorer.localityViewMode = btn.dataset.mapmode;
    renderExplorer();
  });

  const overlayToggles = [
    ['layerPointCloud', 'pointCloud'], ['layerLidar', 'lidar'], ['layerFloorplan', 'floorplan'], ['layerGnss', 'gnss'],
    ['layerDrone', 'drone'], ['layerPlane', 'plane'], ['layerMetro', 'metro'], ['layerRail', 'rail'],
    ['layerWater', 'water'], ['layerGas', 'gas'], ['layerElectricity', 'electricity'], ['layerTelecom', 'telecom'],
    ['layerRoads', 'showRoads'], ['layerTerrain', 'showTerrain'], ['layerProposed', 'showProposed'],
  ];
  overlayToggles.forEach(([elId, key]) => {
    const el = $('#' + elId);
    if (!el) return;
    el.addEventListener('change', (e) => { STATE.explorer[key] = e.target.checked; renderExplorer(); });
  });

  $('#vstackBtn').addEventListener('click', () => {
    STATE.vstackBuildingId = STATE.explorer.buildingId;
    goToView('vstack');
  });

  $('#resetCameraBtn').addEventListener('click', () => {
    STATE.explorer.mode = '3d';
    STATE.explorer.exploded = false;
    STATE.explorer.xray = false;
    $all('#viewModeToggle button').forEach(b => b.classList.toggle('active', b.dataset.mode === '3d'));
    $('#explodeBtn').classList.remove('btn-primary');
    $('#xrayBtn').classList.remove('btn-primary');
    renderExplorer();
    toast('Camera reset');
  });

  $('#fullscreenBtn').addEventListener('click', () => {
    const el = $('#explorerViewportEl');
    if (!document.fullscreenElement) {
      (el.requestFullscreen ? el.requestFullscreen() : Promise.reject()).catch(() => toast('Full screen isn\'t available in this environment'));
    } else {
      document.exitFullscreen();
    }
  });

  const opacitySlider = $('#layerOpacitySlider');
  if (opacitySlider) opacitySlider.addEventListener('input', (e) => {
    $('#buildingSvgHost').style.opacity = (e.target.value / 100).toString();
  });

  $('#exportBtn').addEventListener('click', (e) => {
    e.stopPropagation();
    $('#exportMenu').classList.toggle('open');
  });
  document.addEventListener('click', () => $('#exportMenu').classList.remove('open'));
  $all('#exportMenu button').forEach(b => b.addEventListener('click', (e) => {
    e.stopPropagation();
    toast('Exported Lakeview Residency geometry as ' + b.dataset.fmt);
    $('#exportMenu').classList.remove('open');
  }));
  $('#explodeBtn').addEventListener('click', () => {
    STATE.explorer.exploded = !STATE.explorer.exploded;
    $('#explodeBtn').classList.toggle('btn-primary', STATE.explorer.exploded);
    renderExplorer();
  });
  $('#xrayBtn').addEventListener('click', () => {
    STATE.explorer.xray = !STATE.explorer.xray;
    $('#xrayBtn').classList.toggle('btn-primary', STATE.explorer.xray);
    renderExplorer();
  });
  $('#undergroundBtn').addEventListener('click', () => {
    STATE.explorer.underground = !STATE.explorer.underground;
    $('#undergroundBtn').classList.toggle('btn-primary', STATE.explorer.underground);
    $('#layerUtility').checked = STATE.explorer.underground;
    renderExplorer();
  });
  $('#layerUtility').addEventListener('change', (e) => {
    STATE.explorer.underground = e.target.checked;
    $('#undergroundBtn').classList.toggle('btn-primary', STATE.explorer.underground);
    renderExplorer();
  });

  $('#localityBackBtn').addEventListener('click', backToLocality);
  $('#explorerBreadcrumb').addEventListener('click', () => { if (STATE.explorer.scope === 'building') backToLocality(); });

  const locToggleMap = { locLayerBuildings: 'buildings', locLayerMetro: 'metro', locLayerRail: 'rail', locLayerParks: 'parks', locLayerRoads: 'roads' };
  Object.keys(locToggleMap).forEach(elId => {
    const el = $('#' + elId);
    if (!el) return;
    el.addEventListener('change', (e) => { STATE.explorer.locLayers[locToggleMap[elId]] = e.target.checked; renderExplorer(); });
  });

  $('#infraDrawer').addEventListener('click', (e) => { if (e.target.id === 'infraDrawer') e.currentTarget.classList.remove('open'); });

  $('#proposeInfraBtn').addEventListener('click', () => goToView('proposed'));

  renderExplorer();
}

/* ---------------------------------------------------------------- SEARCH */

var SEARCH_RESULTS = []; /* hydrated by api.js */

function initSpatialQuery() {
  $all('.search-method-chip').forEach(chip => chip.addEventListener('click', () => {
    $all('.search-method-chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    const isSpatial = chip.id === 'spatialChip';
    $('#spatialQueryPanel').style.display = isSpatial ? 'block' : 'none';
    if (isSpatial) renderSpatialMiniMap();
  }));

  $('#spatialRadius').addEventListener('input', renderSpatialMiniMap);
  $('#runSpatialBtn').addEventListener('click', async () => {
    const r = $('#spatialRadius').value;
    const center = STATE.explorer.buildingId || 'lakeview';
    $('#spatialResultCount').textContent = 'Running spatial query…';
    try {
      const res = await API.spatialQuery(center, r);
      $('#spatialResultCount').textContent =
        `Found ${res.count} property volume${res.count === 1 ? '' : 's'} within ${r} m of ${res.center.name}, including ${res.conflicts} active conflict${res.conflicts === 1 ? '' : 's'}.`;
      toast('Spatial query complete — ' + res.count + ' volumes found');
    } catch (err) {
      $('#spatialResultCount').textContent = 'Spatial query failed: ' + err.message;
    }
  });
}

function renderSpatialMiniMap() {
  const r = $('#spatialRadius').value;
  const map = $('#spatialMiniMap');
  const px = Math.min(70, Math.max(20, r / 6));
  map.innerHTML = `
    <div class="ward-blob" style="width:${px * 2}px;height:${px * 2}px;left:${100 - px}px;top:${75 - px}px;background:rgba(37,99,169,0.18);filter:blur(0px);border-radius:50%;border:1px dashed var(--info)"></div>
    <div class="parcel-outline" style="width:26px;height:20px;left:88px;top:65px;border-color:var(--navy-700)"></div>
    <div class="parcel-outline" style="width:16px;height:14px;left:140px;top:50px"></div>
    <div class="parcel-outline" style="width:18px;height:16px;left:150px;top:95px"></div>`;
}

function renderSearchResults() {
  const host = $('#searchResults');
  host.innerHTML = SEARCH_RESULTS.map((r, i) => {
    const conf = confidenceLabel(r.conf);
    return `
    <div class="result-card" data-idx="${i}">
      <div class="result-thumb">${ICONS.layers}</div>
      <div class="result-body">
        <div class="addr">${r.addr}</div>
        <div class="ids">${r.parent} · ${r.id3d}</div>
      </div>
      <div class="result-meta">
        <span class="badge ${r.conf >= 90 ? 'badge-success' : r.conf >= 70 ? 'badge-info' : 'badge-warning'}">${conf.label} · ${r.conf}</span>
        ${r.conflict ? '<span class="badge badge-error">' + ICONS.alert + 'Conflict</span>' : '<span class="badge badge-neutral">No conflict</span>'}
        <span style="font-size:11px;color:var(--text-faint)">Surveyed ${r.date}</span>
      </div>
    </div>`;
  }).join('');
  $all('.result-card', host).forEach(el => el.addEventListener('click', () => {
    const r = SEARCH_RESULTS[+el.dataset.idx];
    goToView('explorer');
    selectBuilding(r.buildingId);
  }));
}

/* ---------------------------------------------------------------- WIZARD */

const WIZARD_STEPS = [
  'Select Parent Parcel', 'Add Building / Asset', 'Define Vertical Levels', 'Subdivide Units',
  'Rights & Restrictions', 'Validate Geometry', 'Preview IDs', 'Submit for Approval',
];

const UNIT_TYPES = ['Apartment', 'Commercial unit', 'Parking bay', 'Common area', 'Basement', 'Utility corridor', 'Air-rights zone', 'Easement / restricted zone'];

function renderWizardSteps() {
  const host = $('#wizardSteps');
  host.innerHTML = WIZARD_STEPS.map((s, i) => {
    const cls = i < STATE.wizard.step ? 'done' : i === STATE.wizard.step ? 'current' : '';
    return `<div class="wizard-step ${cls}"><div class="circ">${i < STATE.wizard.step ? '✓' : i + 1}</div><div class="lab">${s}</div></div>${i < WIZARD_STEPS.length - 1 ? '<div class="wizard-connector"></div>' : ''}`;
  }).join('');
}

function renderWizardPanel() {
  const step = STATE.wizard.step;
  const panel = $('#wizardPanel');
  let html = '';
  if (step === 0) {
    html = `
      <h3 style="margin-bottom:6px">Select the parent parcel</h3>
      <p style="color:var(--text-secondary);font-size:13px;margin-bottom:16px">The parent ULPIN / Bhu-Aadhaar remains the immutable land-parcel identity — this wizard only extends it with a child 3D volume.</p>
      <div class="field"><label>Parent ULPIN</label><input type="text" value="1450A9B7C23456" readonly></div>
      <div class="field"><label>Address</label><input type="text" value="14 Lakeview Avenue, MP Nagar Zone II, Bhopal" readonly></div>
      <div class="field"><label>Registered area</label><input type="text" value="1,240 m²" readonly></div>`;
  } else if (step === 1) {
    html = `
      <h3 style="margin-bottom:6px">Add building or underground asset</h3>
      <p style="color:var(--text-secondary);font-size:13px;margin-bottom:16px">Choose what you are adding to this parent parcel.</p>
      <div class="option-grid">
        ${['Building', 'Underground utility asset', 'Standalone parking structure', 'Air-rights volume'].map((t, i) =>
          `<div class="option-tile ${i === 0 ? 'selected' : ''}">${ICONS.layers}<div>${t}</div></div>`).join('')}
      </div>
      <div class="field" style="margin-top:16px"><label>Building name</label><input type="text" value="Lakeview Residency, Building 01"></div>`;
  } else if (step === 2) {
    html = `
      <h3 style="margin-bottom:6px">Define vertical levels</h3>
      <p style="color:var(--text-secondary);font-size:13px;margin-bottom:14px">Set elevation ranges for each level, plus the precise centroid coordinates used to generate the 3D volume geometry.</p>
      <div class="coord-grid" style="margin-bottom:16px">
        <div class="field"><label>X (easting, m)</label><input type="text" value="682450.20"></div>
        <div class="field"><label>Y (northing, m)</label><input type="text" value="2607330.80"></div>
        <div class="field"><label>Z (elevation, m)</label><input type="text" value="12.0"></div>
        <div class="field"><label>Floor level</label><input type="text" value="4"></div>
        <div class="field"><label>Depth (below grade, m)</label><input type="text" value="0" placeholder="0 for above-grade"></div>
      </div>
      <div class="hint" style="margin-bottom:10px">Coordinates use the jurisdiction's projected CRS (UTM Zone 43N / EPSG:32643). Depth is measured from ground level for basements and utility volumes.</div>
      <div class="floor-stack-visual">
        ${LEVELS.slice().reverse().map(l => `<div class="fsv-row ${l.below ? 'below-grade' : ''}"><span class="tag">${l.tag}</span><span>${l.type}</span><span style="margin-left:auto;color:var(--text-secondary)">${LEVEL_DETAIL[l.id].elevation}</span></div>`).join('')}
      </div>`;
  } else if (step === 3) {
    html = `
      <h3 style="margin-bottom:6px">Subdivide units / volumes</h3>
      <p style="color:var(--text-secondary);font-size:13px;margin-bottom:16px">Select the unit type you are registering on Floor 4.</p>
      <div class="option-grid" id="unitTypeGrid">
        ${UNIT_TYPES.map(t => `<div class="option-tile ${STATE.wizard.unitType === t ? 'selected' : ''}" data-type="${t}">${ICONS.layers}<div>${t}</div></div>`).join('')}
      </div>
      <div class="field" style="margin-top:16px"><label>Unit number</label><input type="text" value="402" id="unitNumberInput"></div>`;
  } else if (step === 4) {
    html = `
      <h3 style="margin-bottom:6px">Add rights and restrictions</h3>
      <div class="field"><label>Ownership</label><select><option>Individual ownership</option><option>Joint ownership</option></select></div>
      <div class="field"><label>Parking entitlement</label><select><option>1 bay, Basement B1</option><option>None</option></select></div>
      <div class="field"><label>Common-area access</label><select><option>Lift, stair, terrace</option><option>Lift, stair only</option></select></div>
      <div class="field"><label>Easements / restrictions</label><textarea rows="2">Fire-escape clearance on Level 4 — flagged for geometry validation.</textarea></div>`;
  } else if (step === 5) {
    html = `
      <h3 style="margin-bottom:6px">Validate geometry</h3>
      <p style="color:var(--text-secondary);font-size:13px;margin-bottom:16px">Running topology checks against the parent parcel and neighbouring volumes.</p>
      <div id="wizardValidation"><div class="scan-stage-row active"><div class="stage-icon"></div>Running checks…</div></div>`;
  } else if (step === 6) {
    html = `
      <h3 style="margin-bottom:6px">Preview generated IDs</h3>
      <p style="color:var(--text-secondary);font-size:13px;margin-bottom:16px">Review the hierarchical relationship before submitting.</p>
      <div class="detail-row"><span class="k">Parent ULPIN</span><span class="v mono">1450A9B7C23456</span></div>
      <div class="detail-row"><span class="k">Building ID</span><span class="v mono">1450A9B7C23456-BLD-01</span></div>
      <div class="detail-row"><span class="k">Level ID</span><span class="v mono">1450A9B7C23456-BLD-01-LVL-04</span></div>
      <div class="detail-row"><span class="k">Generated 3D ID</span><span class="v mono">1450A9B7C23456-BLD-01-LVL-04-UNIT-402</span></div>`;
  } else if (step === 7) {
    html = `
      <div class="empty-state" style="padding:20px 10px">
        <div style="width:52px;height:52px;border-radius:50%;background:var(--success-bg);color:var(--success);display:flex;align-items:center;justify-content:center;margin:0 auto 14px">${ICONS.check}</div>
        <h4>Ready to submit for approval</h4>
        <p>1450A9B7C23456-BLD-01-LVL-04-UNIT-402 will be routed to Under Officer Review, with the fire-escape overlap flagged for the assigned officer.</p>
        <button class="btn btn-primary" style="margin-top:16px" id="wizardSubmitBtn">Submit for Approval</button>
      </div>`;
  }
  panel.innerHTML = html;

  if (step === 2) {
    const coords = $all('.coord-grid input', panel);
    const keys = ['x', 'y', 'z', 'levelNo', 'depth'];
    coords.forEach((input, i) => {
      input.addEventListener('input', () => {
        const v = parseFloat(input.value);
        STATE.wizard[keys[i]] = keys[i] === 'levelNo' ? input.value.trim() : (isNaN(v) ? null : v);
      });
    });
  }
  if (step === 3) {
    $all('#unitTypeGrid .option-tile').forEach(t => t.addEventListener('click', () => {
      STATE.wizard.unitType = t.dataset.type;
      renderWizardPanel();
    }));
    const unitInput = $('#unitNumberInput');
    if (unitInput) {
      STATE.wizard.unitNumber = STATE.wizard.unitNumber || unitInput.value;
      unitInput.addEventListener('input', () => { STATE.wizard.unitNumber = unitInput.value.trim(); });
    }
  }
  if (step === 4) {
    const selects = $all('.field select', panel);
    const area = $('textarea', panel);
    const keys = ['ownership', 'parking', 'commonAccess'];
    selects.forEach((sel, i) => {
      STATE.wizard[keys[i]] = STATE.wizard[keys[i]] || sel.options[sel.selectedIndex].text;
      sel.addEventListener('change', () => { STATE.wizard[keys[i]] = sel.options[sel.selectedIndex].text; });
    });
    if (area) {
      STATE.wizard.restrictions = STATE.wizard.restrictions || area.value;
      area.addEventListener('input', () => { STATE.wizard.restrictions = area.value; });
    }
  }
  if (step === 5) loadWizardValidation();
  if (step === 7) {
    $('#wizardSubmitBtn').addEventListener('click', async () => {
      const btn = $('#wizardSubmitBtn');
      btn.disabled = true;
      btn.textContent = 'Submitting…';
      try {
        const res = await API.generateUlpin({
          parent_ulpin: STATE.wizard.parcel,
          building_slug: 'lakeview',
          building_no: '01',
          level_code: STATE.wizard.levelCode || 'floor4',
          level_no: STATE.wizard.levelNo || '4',
          unit_type: STATE.wizard.unitType || 'Apartment',
          unit_number: STATE.wizard.unitNumber || '402',
          x: STATE.wizard.x, y: STATE.wizard.y, z: STATE.wizard.z,
          ownership: STATE.wizard.ownership,
          parking_entitlement: STATE.wizard.parking,
          common_area_access: STATE.wizard.commonAccess,
          restrictions: STATE.wizard.restrictions,
          submit_for_approval: true,
        });
        await Promise.all([hydrateCadastreLevels(), hydrateApprovals(), hydrateSearch()]);
        renderApprovalKanban();
        renderApprovalTable();
        toast('Registered ' + res.ids.generated_3d_id + ' and routed it for approval');
        goToView('approvals');
      } catch (err) {
        toast(err.status === 409
          ? 'That 3D ULPIN already exists — change the unit number (Rule ID-01)'
          : 'Submission failed: ' + err.message, ICONS.alert);
      } finally {
        btn.disabled = false;
        btn.textContent = 'Submit for Approval';
      }
    });
  }
  renderWizardNav();
}

/* Wizard step 6 — real topology checks from the backend. */
async function loadWizardValidation() {
  const host = $('#wizardValidation');
  if (!host) return;
  try {
    const res = await API.validateGeometry({
      building: 'lakeview',
      level_code: STATE.wizard.levelCode || 'floor4',
    });
    host.innerHTML = res.checks.map(c => {
      const cls = c.status === 'passed' ? 'done' : c.status === 'failed' ? 'active' : 'pending';
      const icon = c.status === 'passed' ? ICONS.check : c.status === 'failed' ? ICONS.alert : '';
      return `<div class="scan-stage-row ${cls}"><div class="stage-icon">${icon}</div>${c.name} — ${c.detail}</div>`;
    }).join('') + (res.notes.length
      ? `<div class="plain-explain" style="margin-top:14px">${res.notes.join(' ')} You can still submit — this will route the record to Conflict Radar for officer review.</div>`
      : `<div class="plain-explain" style="margin-top:14px">All checks passed. This record can be submitted for approval.</div>`);
  } catch (err) {
    host.innerHTML = `<div class="scan-stage-row active"><div class="stage-icon">${ICONS.alert}</div>Validation unavailable: ${err.message}</div>`;
  }
}

function renderWizardNav() {
  const panel = $('#wizardPanel');
  const nav = document.createElement('div');
  nav.className = 'wizard-nav';
  nav.innerHTML = `
    <button class="btn" id="wizPrev" ${STATE.wizard.step === 0 ? 'disabled' : ''}>Back</button>
    <button class="btn btn-primary" id="wizNext" ${STATE.wizard.step === WIZARD_STEPS.length - 1 ? 'style="display:none"' : ''}>Continue</button>`;
  panel.appendChild(nav);
  $('#wizPrev').addEventListener('click', () => { STATE.wizard.step = Math.max(0, STATE.wizard.step - 1); renderWizard(); });
  const nextBtn = $('#wizNext');
  if (nextBtn) nextBtn.addEventListener('click', () => { STATE.wizard.step = Math.min(WIZARD_STEPS.length - 1, STATE.wizard.step + 1); renderWizard(); });
}

function renderWizard() {
  renderWizardSteps();
  renderWizardPanel();
  $('#idPreview').innerHTML = `<span class="parent">1450A9B7C23456</span><br>-BLD-01<br>-LVL-04<br><span class="seg">-UNIT-402</span>`;
  const map = $('#wizardMiniMap');
  map.innerHTML = `<div class="parcel-outline" style="width:60px;height:44px;left:90px;top:60px;border-color:var(--teal-700);background:rgba(47,111,115,0.1)"></div>`;
}

/* ---------------------------------------------------------------- INTAKE */

function renderIntake() {
  const datasetIcon = (kind) => (kind === 'lidar' || kind === 'geojson' || kind === 'shapefile')
    ? ICONS.layers : ICONS.file;
  $('#datasetList').innerHTML = DATASETS.map(d => `
    <div class="dataset-card">
      <div class="dc-icon">${d.icon || datasetIcon(d.kind)}</div>
      <div class="dc-body"><div class="dc-name">${d.name}</div><div class="dc-meta">${d.meta}</div></div>
      <span class="badge badge-info">${d.state}</span>
    </div>`).join('');

  const stages = ['Upload complete', 'Coordinate reference detected', 'Point cloud classified', 'Building envelope extracted', 'Floor bands detected', 'AI segmentation ready for review'];
  $('#pipelineSteps').innerHTML = stages.map((s, i) => `
    <div class="scan-stage-row ${i < 5 ? 'done' : 'active'}"><div class="stage-icon">${i < 5 ? ICONS.check : ''}</div>${s}</div>`).join('');

  $('#fieldModeBtn').addEventListener('click', () => toast('Field Survey Mode: GPS capture, offline sync queue, and photo upload would open here on a mobile device.'));

  wireDatasetUpload();
}

/* Real uploads: the dropzone and the Browse button post to POST /api/datasets. */
function wireDatasetUpload() {
  const zone = $('.dropzone');
  if (!zone || zone.dataset.wired) return;
  zone.dataset.wired = '1';

  let picker = $('#datasetFileInput');
  if (!picker) {
    picker = document.createElement('input');
    picker.type = 'file';
    picker.id = 'datasetFileInput';
    picker.multiple = true;
    picker.style.display = 'none';
    picker.accept = '.geojson,.json,.shp,.zip,.dxf,.dwg,.las,.laz,.tif,.tiff,.pdf,.png,.jpg,.jpeg,.csv,.txt';
    zone.appendChild(picker);
  }

  const upload = async (files) => {
    const building = STATE.explorer.buildingId || 'lakeview';
    for (const file of Array.from(files)) {
      toast('Uploading ' + file.name + '…', ICONS.file);
      try {
        const ds = await API.uploadDataset(file, building, 'EPSG:4326');
        toast(ds.name + ' — ' + ds.state);
      } catch (err) {
        toast('Upload failed for ' + file.name + ': ' + err.message, ICONS.alert);
      }
    }
    await hydrateIntake();
    renderIntake();
    renderIntakeReview();
  };

  const browseBtn = $('button', zone);
  if (browseBtn) browseBtn.addEventListener('click', (e) => { e.preventDefault(); picker.click(); });
  picker.addEventListener('change', () => { if (picker.files.length) upload(picker.files); picker.value = ''; });

  ['dragenter', 'dragover'].forEach(evt => zone.addEventListener(evt, (e) => {
    e.preventDefault();
    zone.classList.add('dropzone-active');
  }));
  ['dragleave', 'drop'].forEach(evt => zone.addEventListener(evt, (e) => {
    e.preventDefault();
    zone.classList.remove('dropzone-active');
  }));
  zone.addEventListener('drop', (e) => {
    if (e.dataTransfer && e.dataTransfer.files.length) upload(e.dataTransfer.files);
  });
}

function renderIntakeReview() {
  $('#floorReviewList').innerHTML = FLOOR_REVIEW.map(f => {
    const conf = confidenceLabel(f.conf);
    return `
    <div style="padding:11px 0;border-bottom:1px solid var(--border)">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px">
        <strong style="font-size:13px">${f.label}</strong>
        <span class="badge ${f.conf >= 90 ? 'badge-success' : f.conf >= 70 ? 'badge-info' : 'badge-warning'}">${f.conf}/100</span>
      </div>
      <div class="progress-track" style="margin-bottom:6px"><div class="progress-fill" style="width:${f.conf}%;background:${conf.color}"></div></div>
      <div style="font-size:12px;color:var(--text-secondary)">${f.note}</div>
    </div>`;
  }).join('');
  const btn = $('#submitSegBtn');
  if (btn) btn.onclick = async () => {
    btn.disabled = true;
    try {
      const res = await API.submitSegmentation({ building: 'lakeview' });
      await hydrateIntake();
      renderIntakeReview();
      toast(res.submitted + ' floor bands submitted for surveyor verification');
      goToView('conflicts');
    } catch (err) {
      toast(err.status === 404
        ? 'No pending floor bands — all bands are already verified'
        : 'Submit failed: ' + err.message, ICONS.alert);
    } finally {
      btn.disabled = false;
    }
  };
}

/* ---------------------------------------------------------------- CONFLICT RADAR */

function severityMeta(sev) {
  const map = {
    critical: { label: 'Critical', badge: 'badge-error' },
    high: { label: 'High', badge: 'badge-error' },
    medium: { label: 'Medium', badge: 'badge-warning' },
    low: { label: 'Low', badge: 'badge-info' },
    clear: { label: 'Clear', badge: 'badge-success' },
  };
  return map[sev] || map.medium;
}

function renderConflictSeverityStrip() {
  const counts = { critical: 0, high: 0, medium: 0, low: 0, clear: 0 };
  CONFLICTS.forEach(c => { counts[c.sev] = (counts[c.sev] || 0) + 1; });
  const host = $('#conflictSeverityStrip');
  if (!host) return;
  host.innerHTML = ['critical', 'high', 'medium', 'low', 'clear'].map(sev => {
    const m = severityMeta(sev);
    return `<span class="badge ${m.badge}"><span class="severity-dot sev-${sev}"></span>${m.label} · ${counts[sev]}</span>`;
  }).join('');
}

function renderConflictKpis() {
  const s = (window.HYDRATED && HYDRATED.conflictStats) || {};
  const kpis = [
    { label: 'Total conflicts', value: String(s.total ?? '—'), delta: 'All recorded cases', cls: 'warn' },
    { label: 'Critical', value: String(s.critical ?? '—'), delta: 'Needs officer action', cls: 'down' },
    { label: 'Pending review', value: String(s.pending_review ?? '—'), delta: '', cls: '' },
    { label: 'Resolved this month', value: String(s.resolved_this_month ?? '—'), delta: '', cls: 'up' },
    { label: 'Volumes scanned', value: String(s.volumes_scanned ?? '—'), delta: 'Registered 3D volumes', cls: '' },
    { label: 'Topology validity', value: (s.topology_validity ?? '—') + '%', delta: '', cls: 'up' },
  ];
  $('#conflictKpis').innerHTML = kpis.map(k => `
    <div class="kpi-card"><div class="label">${k.label}</div><div class="value">${k.value}</div><div class="delta ${k.cls}">${k.delta}</div></div>`).join('');
  renderConflictSeverityStrip();
}

function renderConflictTable() {
  const body = $('#conflictTableBody');
  body.innerHTML = CONFLICTS.map((c, i) => {
    const m = severityMeta(c.sev);
    return `
    <tr class="clickable-row" data-idx="${i}">
      <td data-label="Severity"><span class="severity-dot sev-${c.sev}"></span> ${m.label}</td>
      <td data-label="Type">${c.type}</td>
      <td data-label="Property">${c.prop}</td>
      <td data-label="Building/floor">${c.bldg}</td>
      <td data-label="Volume">${c.vol}</td>
      <td data-label="Status"><span class="badge ${m.badge}">${c.status}</span></td>
      <td data-label="Officer">${c.officer}</td>
    </tr>`;
  }).join('');
  $all('tr', body).forEach(row => row.addEventListener('click', () => openConflictDrawer(CONFLICTS[+row.dataset.idx])));
}

function openConflictDrawer(c) {
  const overlay = $('#conflictDrawer');
  const m = severityMeta(c.sev);
  const buildingId = c.buildingId || 'lakeview';
  $('#conflictDrawerPanel').innerHTML = `
    <div class="drawer-head">
      <div><span class="badge ${m.badge}"><span class="severity-dot sev-${c.sev}"></span>${m.label}</span><h3 style="margin-top:8px">${c.type}</h3></div>
      <button class="drawer-close" id="closeConflictDrawer"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg></button>
    </div>
    <div class="plain-explain">${c.explain}</div>
    <div class="detail-row"><span class="k">Rule violated</span><span class="v" style="text-align:right;max-width:230px">${c.rule}</span></div>
    <div class="detail-row"><span class="k">Affected property</span><span class="v">${c.prop}</span></div>
    <div class="detail-row"><span class="k">Building / floor</span><span class="v">${c.bldg}</span></div>
    <div class="detail-row"><span class="k">Overlap volume</span><span class="v">${c.vol}</span></div>
    <div class="detail-row"><span class="k">Status</span><span class="v">${c.status}</span></div>
    <div class="detail-row"><span class="k">Assigned officer</span><span class="v">${c.officer}</span></div>
    <div style="margin:16px 0;border-radius:8px;overflow:hidden;border:1px solid var(--border)">
      <svg viewBox="0 0 200 90" width="100%"><rect width="200" height="90" fill="#eef2f5"/><polygon points="40,60 90,60 100,45 50,45" fill="#9fc3d8" stroke="#6c93b3"/><polygon points="70,52 110,52 118,40 78,40" fill="#e3a1a1" stroke="#b64242" class="conflict-pulse" style="animation:conflict-pulse 1.8s ease-in-out infinite"/><text x="10" y="14" font-size="8" fill="#667085">Intersecting volume shown in red</text></svg>
    </div>
    <div class="detail-actions">
      <button class="btn btn-sm" id="conflictViewMap">View on Map</button>
      <button class="btn btn-sm" id="conflictInspectProperty">Inspect Property</button>
      <button class="btn btn-sm" id="conflictInspectInfra">Inspect Infrastructure</button>
      <button class="btn btn-sm" id="conflictGenReport">Generate Report</button>
      <button class="btn btn-teal btn-sm" id="resolveConflictBtn">Resolve</button>
    </div>`;
  overlay.classList.add('open');
  $('#closeConflictDrawer').addEventListener('click', () => overlay.classList.remove('open'));
  $('#conflictViewMap').addEventListener('click', () => { overlay.classList.remove('open'); goToView('explorer'); selectBuilding(buildingId); });
  $('#conflictInspectProperty').addEventListener('click', () => { overlay.classList.remove('open'); goToView('passport'); });
  $('#conflictInspectInfra').addEventListener('click', () => { overlay.classList.remove('open'); goToView('utility'); });
  $('#conflictGenReport').addEventListener('click', () => { overlay.classList.remove('open'); toast('Generating conflict report for ' + c.prop); goToReportsTab(); });
  const resolveBtn = $('#resolveConflictBtn');
  if (resolveBtn) resolveBtn.addEventListener('click', async () => {
    if (c.sev === 'clear') { toast('This conflict is already resolved'); return; }
    resolveBtn.disabled = true;
    try {
      await API.resolveConflict(c.id, 'Resolved from the Conflict Radar drawer.');
      await hydrateConflicts();
      await hydrateCadastreLevels();
      renderConflictKpis();
      renderConflictTable();
      toast('Conflict resolved and recorded in the audit trail');
      overlay.classList.remove('open');
    } catch (err) {
      resolveBtn.disabled = false;
      toast('Could not resolve: ' + err.message, ICONS.alert);
    }
  });
}

function initConflicts() {
  renderConflictKpis();
  renderConflictTable();
  $('#conflictDrawer').addEventListener('click', (e) => { if (e.target.id === 'conflictDrawer') e.currentTarget.classList.remove('open'); });

  $('#runValidationBtn').addEventListener('click', async () => {
    if (STATE.conflicts.scanning) return;
    STATE.conflicts.scanning = true;
    const box = $('#scanBox');
    box.style.display = 'block';
    $('#scanProgress').style.width = '0%';
    $('#scanPct').textContent = '0%';

    let result;
    try {
      result = await API.runValidation();
    } catch (err) {
      STATE.conflicts.scanning = false;
      box.style.display = 'none';
      toast('Validation failed: ' + err.message, ICONS.alert);
      return;
    }

    // Reveal the real per-stage results progressively so the scan stays legible.
    $('#scanStages').innerHTML = result.stages.map(s =>
      `<div class="scan-stage-row pending" title="${s.detail}"><div class="stage-icon"></div>${s.name}</div>`).join('');
    const rows = $all('.scan-stage-row', box);
    let i = 0;
    const interval = setInterval(async () => {
      if (i > 0) {
        const prev = rows[i - 1];
        const stage = result.stages[i - 1];
        prev.classList.remove('active');
        prev.classList.add(stage.status === 'failed' ? 'failed' : 'done');
        prev.querySelector('.stage-icon').innerHTML = stage.status === 'failed' ? ICONS.alert : ICONS.check;
        prev.innerHTML += ` <span style="margin-left:auto;font-size:11px;color:var(--text-secondary)">${stage.detail}</span>`;
      }
      if (i < rows.length) {
        rows[i].classList.remove('pending');
        rows[i].classList.add('active');
        const pct = Math.round(((i + 1) / rows.length) * 100);
        $('#scanProgress').style.width = pct + '%';
        $('#scanPct').textContent = pct + '%';
        i++;
      } else {
        clearInterval(interval);
        STATE.conflicts.scanning = false;
        toast(`Validation complete — ${result.total_conflicts} conflicts, ${result.critical} critical, ${result.volumes_scanned} volumes scanned`);
        await hydrateConflicts();
        renderConflictKpis();
        renderConflictTable();
        setTimeout(() => { box.style.display = 'none'; }, 900);
      }
    }, 420);
  });
}

/* ---------------------------------------------------------------- APPROVALS */

function renderApprovalKanban() {
  const host = $('#approvalKanban');
  host.innerHTML = APPROVAL_COLUMNS.map(col => `
    <div class="kanban-col">
      <div class="kanban-col-head">${col.label}<span class="cnt">${col.cases.length}</span></div>
      ${col.cases.map(c => `
        <div class="kanban-card" data-id="${c.id}">
          <div class="kc-id">${c.id}</div>
          <div class="kc-title">${c.title}</div>
          <div class="kc-foot">
            <span class="badge ${c.conf >= 90 ? 'badge-success' : c.conf >= 70 ? 'badge-info' : 'badge-warning'}">${c.conf}</span>
            ${c.conflict ? '<span class="badge badge-error">' + ICONS.alert + '</span>' : ''}
          </div>
          <div class="kc-sla" style="margin-top:6px">${c.sla}</div>
        </div>`).join('')}
    </div>`).join('');
  $all('.kanban-card', host).forEach(card => card.addEventListener('click', () => openCaseDrawer(card.dataset.id)));
}

function renderApprovalTable() {
  const all = APPROVAL_COLUMNS.flatMap(col => col.cases.map(c => ({ ...c, status: col.label })));
  $('#approvalTableBody').innerHTML = all.map(c => `
    <tr class="clickable-row" data-id="${c.id}">
      <td data-label="3D ULPIN" class="mono" style="font-size:11px">${c.id}</td>
      <td data-label="Property">${c.title}</td>
      <td data-label="Status"><span class="badge badge-info">${c.status}</span></td>
      <td data-label="Confidence">${c.conf}</td>
      <td data-label="Conflict">${c.conflict ? '<span class="badge badge-error">Yes</span>' : '<span class="badge badge-neutral">No</span>'}</td>
      <td data-label="SLA">${c.sla}</td>
    </tr>`).join('');
  $all('tr', $('#approvalTableBody')).forEach(row => row.addEventListener('click', () => openCaseDrawer(row.dataset.id)));
}

function openCaseDrawer(id) {
  const all = APPROVAL_COLUMNS.flatMap(col => col.cases.map(c => ({ ...c, status: col.label })));
  const c = all.find(x => x.id === id);
  if (!c) return;
  const overlay = $('#caseDrawer');
  $('#caseDrawerPanel').innerHTML = `
    <div class="drawer-head">
      <div><span class="badge badge-info">${c.status}</span><h3 style="margin-top:8px">${c.title}</h3><div class="idline" style="font-size:11px;color:var(--text-secondary);word-break:break-all">${c.id}</div></div>
      <button class="drawer-close" id="closeCaseDrawer"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg></button>
    </div>
    <div class="detail-row"><span class="k">Confidence</span><span class="v">${c.conf}/100</span></div>
    <div class="detail-row"><span class="k">Conflict status</span><span class="v">${c.conflict ? 'Active conflict' : 'None'}</span></div>
    <div class="detail-row"><span class="k">SLA</span><span class="v">${c.sla}</span></div>
    <div class="detail-row"><span class="k">Surveyor notes</span><span class="v" style="text-align:right;max-width:230px">Geometry derived from LiDAR pass 03, verified against floor plan.</span></div>
    <div class="divider"></div>
    <h4 style="font-size:12px;color:var(--text-secondary);margin-bottom:8px">Audit trail</h4>
    <div class="timeline-mini">
      <div class="tmi"><span class="tdot"></span><div><div>Submitted by surveyor</div><div class="tdate">28 Jul 2026</div></div></div>
      <div class="tmi"><span class="tdot"></span><div><div>AI segmentation reviewed</div><div class="tdate">30 Jul 2026</div></div></div>
      <div class="tmi"><span class="tdot" style="background:var(--warning)"></span><div><div>Routed to officer review</div><div class="tdate">02 Aug 2026</div></div></div>
    </div>
    <div class="detail-actions" style="margin-top:16px">
      <button class="btn btn-primary btn-sm" id="approveCaseBtn">Approve</button>
      <button class="btn btn-sm" id="returnCaseBtn">Return for correction</button>
      <button class="btn btn-sm" id="resurveyCaseBtn">Request re-survey</button>
      <button class="btn btn-danger btn-sm" id="rejectCaseBtn">Reject</button>
    </div>`;
  overlay.classList.add('open');
  $('#closeCaseDrawer').addEventListener('click', () => overlay.classList.remove('open'));
  const decide = async (action, label) => {
    if (!c.caseId) { toast('This case has no backend record'); return; }
    if (!confirm(label + ' ' + c.title + '? This action will be recorded in the audit trail.')) return;
    try {
      await API.decideCase(c.caseId, action);
      await hydrateApprovals();
      renderApprovalKanban();
      renderApprovalTable();
      toast(c.title + ' — ' + label.toLowerCase() + 'd');
      overlay.classList.remove('open');
    } catch (err) {
      toast('Could not ' + label.toLowerCase() + ': ' + err.message, ICONS.alert);
    }
  };
  $('#approveCaseBtn').addEventListener('click', () => decide('approve', 'Approve'));
  $('#returnCaseBtn').addEventListener('click', () => decide('return_for_correction', 'Return'));
  $('#resurveyCaseBtn').addEventListener('click', () => decide('request_resurvey', 'Request re-survey for'));
  $('#rejectCaseBtn').addEventListener('click', () => decide('reject', 'Reject'));
}

function initApprovals() {
  renderApprovalKanban();
  renderApprovalTable();
  $('#caseDrawer').addEventListener('click', (e) => { if (e.target.id === 'caseDrawer') e.currentTarget.classList.remove('open'); });
  $('#approvalViewToggle').addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    $all('button', e.currentTarget).forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    STATE.approvalView = btn.dataset.v;
    $('#approvalKanban').style.display = btn.dataset.v === 'kanban' ? 'flex' : 'none';
    $('#approvalTable').style.display = btn.dataset.v === 'table' ? 'block' : 'none';
  });
}

/* ---------------------------------------------------------------- UTILITY PLANNER */

function renderUtilitySvg() {
  const layers = { water: $all('.util-layer').find(l => l.dataset.layer === 'water')?.checked ?? true,
    sewer: true, fibre: true, gas: false };
  $all('.util-layer').forEach(cb => layers[cb.dataset.layer] = cb.checked);
  // Depths, colours and agencies come from the registered utility assets.
  const assets = (window.HYDRATED && HYDRATED.utilityAssets) || [];
  const keyFor = (slug) => slug.split('-')[0].replace('fibre', 'fibre');
  const rows = assets.map(a => {
    const depth = Math.abs(a.depth_m);
    return {
      key: keyFor(a.slug),
      y: 60 + depth * 25,
      label: a.name.replace(/ (line|conduit)$/i, '') + ' — ' + depth + ' m',
      color: a.color || '#8b98a5',
    };
  });
  const depth = parseFloat($('#digDepth') ? $('#digDepth').value : 3.5);
  const digY = 40 + depth * 25;
  let svg = `<svg viewBox="0 0 420 230" width="100%" style="max-width:520px"><rect width="420" height="230" fill="#eef2f5"/>
    <rect x="0" y="0" width="420" height="40" fill="#dbe6ec"/>
    <text x="8" y="24" font-size="10" fill="#667085">Ground level</text>
    <rect x="140" y="10" width="90" height="30" fill="#b9c8d1" stroke="#8b98a5"/><text x="150" y="30" font-size="8" fill="#1f2933">Building footprint</text>
    <line x1="150" y1="40" x2="150" y2="230" stroke="#c3ccd3" stroke-dasharray="2 2"/>
    <line x1="220" y1="40" x2="220" y2="230" stroke="#c3ccd3" stroke-dasharray="2 2"/>
    <rect x="60" y="${digY - 14}" width="130" height="28" fill="rgba(182,66,66,0.18)" stroke="#b64242" stroke-dasharray="4 2"/>
    <text x="64" y="${digY - 18}" font-size="9" fill="#b64242">Proposed excavation zone (${depth.toFixed(1)} m)</text>`;
  rows.forEach(r => {
    if (!layers[r.key]) return;
    svg += `<rect x="20" y="${r.y}" width="380" height="10" rx="4" fill="${r.color}" opacity="0.85"/><text x="330" y="${r.y + 9}" font-size="9" fill="#1f2933">${r.label}</text>`;
  });
  svg += '</svg>';
  $('#utilitySvgHost').innerHTML = svg;
}

async function checkDigSafe() {
  const depth = parseFloat($('#digDepth').value);
  const footprintSelect = $('#view-utility .field select');
  const result = $('#digSafeResult');
  result.innerHTML = '<div class="digsafe-result digsafe-review">Checking clearance…</div>';
  try {
    const res = await API.digSafe({
      depth_m: depth,
      footprint: footprintSelect ? footprintSelect.options[footprintSelect.selectedIndex].text : undefined,
    });
    const cls = { clear: 'digsafe-clear', review: 'digsafe-review', prohibited: 'digsafe-prohibited' }[res.verdict];
    const icon = res.verdict === 'clear' ? ICONS.check : ICONS.alert;
    // Only list the assets in the way when the zone actually needs review.
    const assets = res.verdict === 'clear' ? '' : (res.conflicting_assets || []).map(a =>
      `<div class="detail-row"><span class="k">${a.name} (${a.depth_m} m)</span><span class="v">${a.clearance_m} m clearance · ${a.agency || '—'}</span></div>`).join('');
    result.innerHTML = `<div class="digsafe-result ${cls}">${icon}<span>${res.message}</span></div>${assets}`;
  } catch (err) {
    result.innerHTML = `<div class="digsafe-result digsafe-prohibited">${ICONS.alert}<span>Clearance check failed: ${err.message}</span></div>`;
  }
}

function initUtility() {
  renderUtilityRegistry();
  renderUtilitySvg();
  $all('.util-layer').forEach(cb => cb.addEventListener('change', renderUtilitySvg));
  $('#digDepth').addEventListener('input', renderUtilitySvg);
  $('#digSafeBtn').addEventListener('click', checkDigSafe);
}

/* Asset registry card + layer toggles, driven by the registered assets. */
function renderUtilityRegistry() {
  const assets = (window.HYDRATED && HYDRATED.utilityAssets) || [];
  if (!assets.length) return;

  const registry = $('#utilityAssetRegistry');
  if (registry) {
    registry.innerHTML = assets.map(a => `
      <div class="detail-row"><span class="k">${a.name}</span><span class="v">${a.agency || '—'} · ${a.condition || '—'}</span></div>`).join('') +
      `<div class="detail-row"><span class="k">Safety buffer</span><span class="v">1.5 m radial</span></div>`;
  }

  const toggleHost = $('#utilityLayerToggles');
  if (toggleHost) {
    toggleHost.innerHTML = assets.map((a, i) => {
      const key = a.slug.split('-')[0];
      return `<label style="display:flex;align-items:center;gap:6px"><input type="checkbox" ${i < 3 ? 'checked' : ''} class="util-layer" data-layer="${key}">${a.name.replace(/ (line|conduit)$/i, '')} (${a.depth_m}m)</label>`;
    }).join('');
  }
}

/* ---------------------------------------------------------------- PASSPORT */

function initPassport() {
  $all('.passport-toggle button').forEach(btn => btn.addEventListener('click', () => {
    $all('.passport-toggle button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const isPublic = btn.dataset.p === 'public';
    $('#passportOwner').textContent = isPublic ? 'A. Sharma (masked)' : UNIT_402.ownerFull + ' (verified owner)';
    toast(isPublic ? 'Showing public-safe view' : 'Showing official view (authorized roles only)');
  }));
}

/* ---------------------------------------------------------------- ANALYTICS */

function renderAnalytics() {
  const a = (window.HYDRATED && HYDRATED.analytics) || {};
  const kpis = a.kpis || [];
  $('#analyticsKpis').innerHTML = kpis.map(k => `<div class="kpi-card"><div class="label">${k.label}</div><div class="value">${k.value}</div></div>`).join('');

  // Scale the throughput bars against the busiest week so real counts stay readable.
  const rawTrend = a.trend || [];
  const peak = Math.max(1, ...rawTrend.map(t => t.surveyed));
  const trend = rawTrend.map(t => [t.label, Math.round(t.surveyed / peak * 100), Math.round(t.approved / peak * 100), t.surveyed]);
  $('#trendChart').innerHTML = trend.map(([label, surveyed, approved, rawCount]) => `
    <div class="bc-col">
      <div class="bc-val">${surveyed}</div>
      <div style="width:100%;display:flex;justify-content:center;gap:3px;height:100%;align-items:flex-end">
        <div class="bc-bar" style="height:${surveyed}%;background:var(--info);width:40%"></div>
        <div class="bc-bar" style="height:${approved}%;background:var(--teal-700);width:40%"></div>
      </div>
      <div class="bc-label">${label}</div>
    </div>`).join('');

  const donut = a.confidence_distribution || [];
  let acc = 0;
  const circles = donut.map(d => {
    const dash = `${d.pct} ${100 - d.pct}`;
    const el = `<circle r="15.9" cx="21" cy="21" fill="transparent" stroke="${d.color}" stroke-width="6" stroke-dasharray="${dash}" stroke-dashoffset="${25 - acc}"/>`;
    acc += d.pct;
    return el;
  }).join('');
  $('#donutChart').innerHTML = circles;
  $('#donutLegend').innerHTML = donut.map(d => `<div class="dl-item"><span class="dl-swatch" style="background:${d.color}"></span>${d.label} — ${d.pct}%</div>`).join('');

  const wards = (a.ward_conflicts || []).map(w => [w.ward, w.count]);
  const maxW = Math.max(1, ...wards.map(w => w[1]));
  $('#wardConflictChart').innerHTML = wards.map(([w, v]) => `
    <div class="hbar-row"><span class="hbl">${w}</span><div class="hbar-track"><div class="hbar-fill" style="width:${(v / maxW) * 100}%;background:var(--navy-700)"></div></div><span class="hbv">${v}</span></div>`).join('');

  const queue = a.priority_queue || [];
  $('#priorityQueue').innerHTML = queue.map((q, i) => `<div class="priority-item"><div class="num" style="background:var(--error-bg);color:var(--error)">${i + 1}</div><div class="txt">${q}</div></div>`).join('');

  const tax = (a.tax_realization || []).map(t => [t.period, t.demand, t.realized]);
  $('#taxChart').innerHTML = tax.map(([label, demand, realized]) => `
    <div class="hbar-row"><span class="hbl">${label} realized / demand</span><div class="hbar-track"><div class="hbar-fill" style="width:${(realized / demand) * 100}%;background:var(--teal-700)"></div></div><span class="hbv">${realized}%</span></div>`).join('') +
    `<div style="font-size:11px;color:var(--text-secondary);margin-top:6px">Tax realization is tied to verified 3D volumes — unresolved conflicts delay demand notices.</div>`;

  const litigation = (a.litigation || []).map(l => ({ t: l.title, s: l.status }));
  $('#litigationList').innerHTML = litigation.map(l => `
    <div class="detail-row"><span class="k" style="max-width:170px">${l.t}</span><span class="v badge badge-warning" style="display:inline-flex">${l.s}</span></div>`).join('') +
    `<div style="font-size:11px;color:var(--text-secondary);margin-top:10px">${litigation.length} open case${litigation.length === 1 ? '' : 's'} across MP Nagar — linked directly to Conflict Radar records.</div>`;

  const dilrmp = (a.dilrmp || []).map(d => [d.label, d.pct]);
  $('#dilrmpStatus').innerHTML = dilrmp.map(([label, pct]) => `
    <div class="confidence-bar-row"><span class="clabel" style="width:150px">${label}</span><div class="progress-track" style="flex:1"><div class="progress-fill" style="width:${pct}%;background:${pct > 85 ? 'var(--success)' : pct > 60 ? 'var(--info)' : 'var(--warning)'}"></div></div><span class="cval">${pct}%</span></div>`).join('') +
    `<div style="font-size:11px;color:var(--text-secondary);margin-top:6px">Tracks alignment with the Digital India Land Records Modernisation Programme.</div>`;
}

/* ---------------------------------------------------------------- SETTINGS EXTRAS */

var LADM_MAPPING = []; /* hydrated by api.js */

var LEGACY_MAPPING = []; /* hydrated by api.js */

function renderSettingsExtras() {
  $('#ladmMapping').innerHTML = LADM_MAPPING.map(m => `
    <div class="compliance-row"><span>${m.local}</span><span class="ladm-code">${m.ladm}</span></div>`).join('');

  $('#legacyMappingBody').innerHTML = LEGACY_MAPPING.map(l => `
    <tr><td data-label="Khasra / Survey No.">${l.khasra}</td><td data-label="Parent ULPIN" class="mono" style="font-size:11px">${l.parent}</td><td data-label="3D volumes">${l.volumes}</td><td data-label="Migration status"><span class="badge ${l.status === 'Migrated' ? 'badge-success' : 'badge-warning'}">${l.status}</span></td></tr>`).join('');
}

/* ---------------------------------------------------------------- REPORTS */

function goToReportsTab() {
  goToView('analytics');
  const btn = $('#analyticsTabToggle button[data-tab="reports"]');
  if (btn) btn.click();
}

function initAnalyticsTabs() {
  $('#analyticsTabToggle').addEventListener('click', (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    $all('button', e.currentTarget).forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    $('#analyticsDashboardsTab').style.display = btn.dataset.tab === 'dashboards' ? 'block' : 'none';
    $('#analyticsReportsTab').style.display = btn.dataset.tab === 'reports' ? 'block' : 'none';
  });
}

function renderReports() {
  $('#reportsGrid').innerHTML = REPORTS.map(r => `
    <div class="card">
      <div class="card-title-row"><h3>${r.name}</h3></div>
      <p style="font-size:12.5px;color:var(--text-secondary);margin-bottom:14px">${r.desc}</p>
      <div style="display:flex;gap:6px">${r.formats.map(f => `<button class="btn btn-sm">${f}</button>`).join('')}</div>
    </div>`).join('');
}

/* ---------------------------------------------------------------- INIT */

/* Called by api.js once the user is authenticated and the dataset is hydrated. */
function startApp() {
  initShell();
  initRouting();
  renderOverview();
  initExplorer();
  renderSearchResults();
  initSpatialQuery();
  renderWizard();
  renderIntake();
  renderIntakeReview();
  initConflicts();
  initApprovals();
  initUtility();
  initPassport();
  initUndergroundPage();
  renderAnalytics();
  renderReports();
  initAnalyticsTabs();
  renderSettingsExtras();

  $('#globalSearch').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { goToView('search'); runSearch(e.target.value); }
  });
  const searchInput = $('#searchInput');
  if (searchInput) searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') runSearch(e.target.value);
  });
  $all('.filter-row select', $('#view-search')).forEach(sel => sel.addEventListener('change', () => {
    runSearch($('#searchInput').value);
  }));
}

/* Server-side search — replaces the filtering the prototype did in memory. */
async function runSearch(query) {
  const selects = $all('.filter-row select', $('#view-search'));
  const pick = (i) => {
    const el = selects[i];
    if (!el || el.selectedIndex === 0) return undefined;
    return el.options[el.selectedIndex].text;
  };
  const conflictChoice = pick(2);
  const yearChoice = pick(3);
  try {
    const body = await API.search({
      q: query || undefined,
      property_type: pick(0),
      verification_status: pick(1),
      conflict: conflictChoice === undefined ? undefined : conflictChoice !== 'No conflict',
      survey_year: yearChoice ? Number(yearChoice) : undefined,
      page_size: 50,
    });
    SEARCH_RESULTS = body.items.map(r => ({
      addr: r.addr, parent: r.parent, buildingId: r.buildingId, id3d: r.id3d,
      fullId3d: r.full_id3d, status: r.status, conf: r.conf, conflict: r.conflict, date: r.date,
    }));
    renderSearchResults();
    toast(body.total + ' record' + (body.total === 1 ? '' : 's') + ' found');
  } catch (err) {
    toast('Search failed: ' + err.message, ICONS.alert);
  }
}