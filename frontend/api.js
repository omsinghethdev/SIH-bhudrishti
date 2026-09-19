/* ==========================================================================
   BhuDrishti 3D — backend API client, auth gate, and data hydration.
   Loads before app.js. Populates the globals app.js renders from, so every
   view is backed by real FastAPI data instead of hardcoded demo objects.
   ========================================================================== */

const API_BASE = (window.BHUDRISHTI_API_BASE || 'http://127.0.0.1:8000') + '/api';
const TOKEN_KEY = 'bhudrishti.token';

const Auth = {
  get token() { try { return localStorage.getItem(TOKEN_KEY); } catch (e) { return null; } },
  set token(v) {
    try { v ? localStorage.setItem(TOKEN_KEY, v) : localStorage.removeItem(TOKEN_KEY); } catch (e) {}
  },
  user: null,
};

/* ---------------------------------------------------------------- transport */

class ApiError extends Error {
  constructor(status, detail, errors) {
    super(detail || ('Request failed with status ' + status));
    this.status = status;
    this.errors = errors || [];
  }
}

async function request(path, options) {
  const opts = options || {};
  const headers = Object.assign({}, opts.headers);
  if (Auth.token) headers['Authorization'] = 'Bearer ' + Auth.token;

  let body = opts.body;
  if (body !== undefined && !(body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(API_BASE + path, { method: opts.method || 'GET', headers, body });
  } catch (e) {
    throw new ApiError(0, 'Cannot reach the backend at ' + API_BASE + '. Is uvicorn running?');
  }

  if (res.status === 401 && Auth.token) {
    // Token expired or revoked — drop it and send the user back to sign-in.
    Auth.token = null;
    Auth.user = null;
    showLogin('Your session expired. Please sign in again.');
    throw new ApiError(401, 'Session expired');
  }

  if (res.status === 204) return null;

  const text = await res.text();
  const payload = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const detail = payload && payload.detail ? payload.detail : 'Request failed';
    throw new ApiError(res.status, detail, payload && payload.errors);
  }
  return payload;
}

function qs(params) {
  const clean = {};
  Object.keys(params || {}).forEach(k => {
    if (params[k] !== undefined && params[k] !== null && params[k] !== '') clean[k] = params[k];
  });
  const s = new URLSearchParams(clean).toString();
  return s ? '?' + s : '';
}

/* ---------------------------------------------------------------- endpoints */

const API = {
  // auth
  register: (data) => request('/auth/register', { method: 'POST', body: data }),
  login: (email, password) => request('/auth/login', { method: 'POST', body: { email, password } }),
  me: () => request('/auth/me'),
  logout: () => request('/auth/logout', { method: 'POST' }),

  // reference / cadastre
  permissions: () => request('/users/permissions'),
  locality: () => request('/locality'),
  buildings: () => request('/buildings'),
  building: (slug) => request('/buildings/' + slug),
  verticalStack: (slug) => request('/buildings/' + slug + '/vertical-stack'),
  infraProfiles: () => request('/infra-profiles'),
  infraAssets: (kind) => request('/infra-assets' + qs({ kind })),
  depthReference: () => request('/depth-reference'),

  // search / passport
  search: (params) => request('/search' + qs(params)),
  spatialQuery: (building, radius_m) => request('/spatial-query' + qs({ building, radius_m })),
  passport: (id3d) => request('/passport/' + encodeURIComponent(id3d)),

  // conflicts
  conflicts: (params) => request('/conflicts' + qs(params)),
  conflictStats: () => request('/conflicts/stats'),
  runValidation: () => request('/conflicts/validate', { method: 'POST' }),
  resolveConflict: (id, note) => request('/conflicts/' + id + '/resolve' + qs({ note }), { method: 'POST' }),

  // approvals
  approvalBoard: (params) => request('/approvals/board' + qs(params)),
  approvalCase: (id) => request('/approvals/' + id),
  decideCase: (id, action, note) =>
    request('/approvals/' + id + '/decision', { method: 'POST', body: { action, note } }),

  // intake
  datasets: (params) => request('/datasets' + qs(params)),
  uploadDataset: (file, buildingSlug, crs) => {
    const form = new FormData();
    form.append('file', file);
    if (buildingSlug) form.append('building_slug', buildingSlug);
    if (crs) form.append('crs', crs);
    return request('/datasets', { method: 'POST', body: form });
  },
  pipeline: (datasetId) => request('/datasets/' + datasetId + '/pipeline'),
  floorSegments: (params) => request('/floor-segments' + qs(params)),
  submitSegmentation: (params) => request('/floor-segments/submit' + qs(params), { method: 'POST' }),

  // planning
  proposals: () => request('/proposals'),
  createProposal: (data) => request('/proposals', { method: 'POST', body: data }),
  utilityAssets: () => request('/utility/assets'),
  digSafe: (data) => request('/utility/dig-safe', { method: 'POST', body: data }),
  wizardConfig: () => request('/ulpin/wizard-config'),
  ulpinPreview: (params) => request('/ulpin/preview' + qs(params)),
  validateGeometry: (params) => request('/ulpin/validate-geometry' + qs(params)),
  generateUlpin: (data) => request('/ulpin/generate', { method: 'POST', body: data }),

  // insights / settings
  overview: () => request('/overview'),
  analytics: () => request('/analytics'),
  reports: () => request('/reports'),
  activity: (limit) => request('/activity' + qs({ limit })),
  users: (params) => request('/users' + qs(params)),
  createUser: (data) => request('/users', { method: 'POST', body: data }),
  settings: () => request('/settings'),
  ladmMapping: () => request('/settings/ladm-mapping'),
  legacyMapping: () => request('/settings/legacy-mapping'),
};

window.API = API;
window.ApiError = ApiError;
window.Auth = Auth;

/* ---------------------------------------------------------------- mapping
   The backend returns one canonical shape per entity; app.js was written
   against slightly different local shapes. These adapters bridge the two so
   none of the existing render code has to change.
   ------------------------------------------------------------------------- */

const FLAGSHIP = 'lakeview'; // app.js treats this building as the primary record

function toLevelRow(lvl) {
  const c = lvl.colors || {};
  return {
    id: lvl.code,
    label: lvl.label,
    tag: lvl.tag,
    h: lvl.h || 34,
    type: lvl.type,
    below: !!lvl.below,
    top: c.top || '#9fc3d8',
    left: c.left || '#7fa8c9',
    right: c.right || '#6c93b3',
    hasConflict: !!lvl.conflict,
  };
}

function toLevelDetail(lvl) {
  return {
    id3d: lvl.id3d,
    type: lvl.type,
    elevation: lvl.elevation,
    area: lvl.area,
    volume: lvl.volume,
    owner: lvl.owner,
    source: lvl.source,
    confidence: lvl.confidence,
    conflict: !!lvl.conflict,
    airspace: !!lvl.airspace,
    rights: lvl.rights || {},
  };
}

function toBuildingMeta(meta) {
  return {
    name: meta.name, parent: meta.parent, floors: meta.floors, basements: meta.basements,
    address: meta.address, ward: meta.ward, zone: meta.zone, surveyNo: meta.surveyNo,
    lat: meta.lat, lng: meta.lng, landUse: meta.landUse, ownershipType: meta.ownershipType,
    boundaryDims: meta.boundaryDims, status: meta.status, validationStatus: meta.validationStatus,
    surveyAccuracy: meta.surveyAccuracy, gnss: meta.gnss, lidarAvailability: meta.lidarAvailability,
    infra: meta.infra || {}, slug: meta.slug,
  };
}

/* ---------------------------------------------------------------- hydration */

const HYDRATED = { buildings: {}, conflictById: {}, caseIdByUlpin: {}, permissions: null };
window.HYDRATED = HYDRATED;

async function hydrateCadastre() {
  const [locality, profiles] = await Promise.all([API.locality(), API.infraProfiles()]);

  INFRA_PROFILES = {};
  profiles.forEach(p => { INFRA_PROFILES[p.value] = { label: p.label, color: p.color }; });

  LOCALITY = {
    buildings: locality.buildings.map(b => ({
      id: b.slug, name: b.name, use: b.use, conflict: b.conflict,
      x: (b.geometry || {}).x, y: (b.geometry || {}).y,
      w: (b.geometry || {}).w, h: (b.geometry || {}).h,
    })),
    genericBuildings: locality.genericBuildings || [],
    metro: {
      path: locality.metro.path,
      stations: locality.metro.stations || [],
      status: locality.metro.status,
      name: locality.metro.name,
      slug: locality.metro.slug,
    },
    rail: { path: locality.rail.path, label: locality.rail.label, name: locality.rail.name },
    parks: locality.parks || [],
  };

  // Pull every building's levels so the explorer, vstack and underground views
  // can switch between them without another round trip.
  const details = await Promise.all(LOCALITY.buildings.map(b => API.building(b.id)));
  BUILDINGS_EXTRA = {};
  details.forEach(d => {
    const slug = d.meta.slug;
    const levels = d.levels.map(toLevelRow);
    const detail = {};
    d.levels.forEach(l => { detail[l.code] = toLevelDetail(l); });
    const meta = toBuildingMeta(d.meta);
    HYDRATED.buildings[slug] = { meta, levels, detail, raw: d };

    if (slug === FLAGSHIP) {
      LEVELS = levels;
      LEVEL_DETAIL = detail;
      LAKEVIEW_META = meta;
      const flagshipUnit = d.levels.find(l => (l.rights || {}).unit_name);
      if (flagshipUnit) {
        UNIT_402 = Object.assign(toLevelDetail(flagshipUnit), {
          name: flagshipUnit.rights.unit_name,
          id3d: flagshipUnit.id3d,
          parent: d.meta.parent,
          building: d.meta.name + ', Bldg 01',
          floor: flagshipUnit.label,
          ownerFull: flagshipUnit.owner,
          lastVerified: flagshipUnit.verified_on,
        });
      }
    } else {
      BUILDINGS_EXTRA[slug] = { meta, levels, detail };
    }
  });

  VSTACK_ROAD_INFO = {};
  details.forEach(d => { VSTACK_ROAD_INFO[d.meta.slug] = d.meta.roadInfo || ''; });
}

async function hydrateConflicts() {
  const [body, stats] = await Promise.all([
    API.conflicts({ page_size: 200 }),
    API.conflictStats(),
  ]);
  HYDRATED.conflictStats = stats;
  CONFLICTS = body.items.map(c => ({
    id: c.id, sev: c.sev, type: c.type, prop: c.prop, bldg: c.bldg, vol: c.vol,
    status: c.status, officer: c.officer, explain: c.explain, rule: c.rule,
    buildingId: c.buildingId,
  }));
  HYDRATED.conflictById = {};
  CONFLICTS.forEach(c => { HYDRATED.conflictById[c.id] = c; });
}

async function hydrateApprovals() {
  const board = await API.approvalBoard();
  APPROVAL_COLUMNS = board.columns.map(col => ({
    id: col.id,
    label: col.label,
    cases: col.cases.map(c => ({
      id: c.ulpin_3d, caseId: c.id, title: c.title, conf: c.conf,
      sla: c.sla || '—', conflict: c.conflict,
    })),
  }));
  HYDRATED.caseIdByUlpin = {};
  APPROVAL_COLUMNS.forEach(col => col.cases.forEach(c => { HYDRATED.caseIdByUlpin[c.id] = c.caseId; }));
}

async function hydrateIntake() {
  const [datasets, segments] = await Promise.all([
    API.datasets({ page_size: 50 }),
    API.floorSegments({ building: FLAGSHIP }),
  ]);
  // app.js picks the icon from `kind` — api.js stays free of render concerns.
  DATASETS = datasets.items.map(d => ({
    id: d.id, name: d.name, meta: d.meta, state: d.state, kind: d.kind,
  }));
  FLOOR_REVIEW = segments.map(s => ({ id: s.id, label: s.label, conf: s.conf, note: s.note }));
}

async function hydrateSearch() {
  const body = await API.search({ page_size: 50 });
  SEARCH_RESULTS = body.items.map(r => ({
    addr: r.addr, parent: r.parent, buildingId: r.buildingId, id3d: r.id3d,
    fullId3d: r.full_id3d, status: r.status, conf: r.conf, conflict: r.conflict, date: r.date,
  }));
}

async function hydrateInsights() {
  const [overview, analytics, reports, utilityAssets] = await Promise.all([
    API.overview(), API.analytics(), API.reports(), API.utilityAssets(),
  ]);
  ACTIVITY = overview.activity.map(a => ({ c: a.c, t: a.t, time: a.time }));
  REPORTS = reports.map(r => ({ name: r.name, desc: r.desc, formats: r.formats }));
  HYDRATED.overview = overview;
  HYDRATED.analytics = analytics;
  HYDRATED.utilityAssets = utilityAssets;
}

async function hydrateAdmin() {
  const [perms, users, ladm, legacy] = await Promise.all([
    API.permissions(), API.users({ page_size: 100 }), API.ladmMapping(), API.legacyMapping(),
  ]);
  HYDRATED.permissions = perms;
  PERMISSION_MATRIX = perms.matrix.map(row => [
    row.module, row.planner, row.constructor, row.surveyor, row.public,
  ]);
  DEMO_USERS = users.items.map(u => ({
    name: u.name, role: u.role_label, org: u.org, active: u.active, status: u.status,
  }));
  LADM_MAPPING = ladm;
  LEGACY_MAPPING = legacy;
}

async function hydrateAll() {
  // Admin data is planner-only; the rest is available to every signed-in role.
  await Promise.all([
    hydrateCadastre(),
    hydrateConflicts().catch(() => {}),
    hydrateApprovals().catch(() => {}),
    hydrateIntake().catch(() => {}),
    hydrateSearch(),
    hydrateInsights().catch(() => {}),
    hydrateAdmin().catch(() => {
      HYDRATED.permissions = { my_role: Auth.user && Auth.user.role, my_nav_access: null };
    }),
  ]);
}

/* Refresh just the per-building levels and conflict flags (after a resolve,
   a new 3D ULPIN, or an approval decision) without re-fetching everything. */
async function hydrateCadastreLevels() {
  const slugs = LOCALITY.buildings.map(b => b.id);
  const details = await Promise.all(slugs.map(s => API.building(s)));
  details.forEach(d => {
    const slug = d.meta.slug;
    const levels = d.levels.map(toLevelRow);
    const detail = {};
    d.levels.forEach(l => { detail[l.code] = toLevelDetail(l); });
    const meta = toBuildingMeta(d.meta);
    HYDRATED.buildings[slug] = { meta, levels, detail, raw: d };
    const summary = LOCALITY.buildings.find(b => b.id === slug);
    if (summary) summary.conflict = !!(d.conflict_summary && d.conflict_summary.count);
    if (slug === FLAGSHIP) {
      LEVELS = levels;
      LEVEL_DETAIL = detail;
      LAKEVIEW_META = meta;
    } else {
      BUILDINGS_EXTRA[slug] = { meta, levels, detail };
    }
  });
}

async function hydrateAdminUsers() {
  const users = await API.users({ page_size: 100 });
  DEMO_USERS = users.items.map(u => ({
    name: u.name, role: u.role_label, org: u.org, active: u.active, status: u.status,
  }));
}

window.hydrateCadastreLevels = hydrateCadastreLevels;
window.hydrateAdminUsers = hydrateAdminUsers;
window.hydrateAll = hydrateAll;
window.hydrateConflicts = hydrateConflicts;
window.hydrateApprovals = hydrateApprovals;
window.hydrateIntake = hydrateIntake;
window.hydrateSearch = hydrateSearch;

/* ---------------------------------------------------------------- login gate */

function loginMarkup() {
  return `
    <div class="auth-card">
      <div class="auth-brand">
        <div class="mark"><svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8"><path d="M3 20h18M5 20V9l7-5 7 5v11M9 20v-6h6v6"/></svg></div>
        <div><strong>BhuDrishti 3D</strong><small>3D Cadastre &amp; Vertical Property Mapping</small></div>
      </div>
      <div class="auth-tabs">
        <button class="active" data-auth-tab="login">Sign in</button>
        <button data-auth-tab="register">Create account</button>
      </div>
      <form id="authForm" autocomplete="on">
        <div class="auth-field" id="authNameField" style="display:none">
          <label for="authName">Full name</label>
          <input type="text" id="authName" placeholder="R. Mehta" autocomplete="name">
        </div>
        <div class="auth-field">
          <label for="authEmail">Email</label>
          <input type="email" id="authEmail" placeholder="officer@bmc.gov.in" autocomplete="username" required>
        </div>
        <div class="auth-field">
          <label for="authPassword">Password</label>
          <input type="password" id="authPassword" placeholder="••••••••" autocomplete="current-password" required>
        </div>
        <div class="auth-field" id="authRoleField" style="display:none">
          <label for="authRole">Role</label>
          <select id="authRole">
            <option value="public">Public User</option>
            <option value="surveyor">Architect / Surveyor</option>
            <option value="constructor">Constructor / Engineer</option>
            <option value="planner">Government / Planner</option>
          </select>
        </div>
        <div class="auth-field" id="authOrgField" style="display:none">
          <label for="authOrg">Organization</label>
          <input type="text" id="authOrg" placeholder="Bhopal Municipal Corporation">
        </div>
        <div class="auth-error" id="authError"></div>
        <button type="submit" class="auth-submit" id="authSubmit">Sign in</button>
      </form>
      <div class="auth-hint">
        Demo accounts (password <code>Bhudrishti@2026</code>):<br>
        <code>r.mehta@bmc.gov.in</code> — Government / Planner<br>
        <code>n.iqbal@geosurv.in</code> — Architect / Surveyor<br>
        <code>k.nair@bmrc.co.in</code> — Constructor / Engineer<br>
        <code>a.sharma@example.com</code> — Public User
      </div>
    </div>`;
}

let authMode = 'login';

function showLogin(message) {
  const overlay = document.getElementById('authOverlay');
  overlay.innerHTML = loginMarkup();
  overlay.classList.add('open');
  document.getElementById('appShell').style.display = 'none';
  if (message) setAuthError(message);
  wireAuthForm();
}

function hideLogin() {
  const overlay = document.getElementById('authOverlay');
  overlay.classList.remove('open');
  overlay.innerHTML = '';
  document.getElementById('appShell').style.display = '';
}

function setAuthError(msg) {
  const el = document.getElementById('authError');
  if (el) { el.textContent = msg || ''; el.style.display = msg ? 'block' : 'none'; }
}

function wireAuthForm() {
  const tabs = Array.from(document.querySelectorAll('[data-auth-tab]'));
  tabs.forEach(tab => tab.addEventListener('click', () => {
    tabs.forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    authMode = tab.dataset.authTab;
    const isRegister = authMode === 'register';
    document.getElementById('authNameField').style.display = isRegister ? 'block' : 'none';
    document.getElementById('authRoleField').style.display = isRegister ? 'block' : 'none';
    document.getElementById('authOrgField').style.display = isRegister ? 'block' : 'none';
    document.getElementById('authSubmit').textContent = isRegister ? 'Create account' : 'Sign in';
    document.getElementById('authPassword').autocomplete = isRegister ? 'new-password' : 'current-password';
    setAuthError('');
  }));

  document.getElementById('authForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('authSubmit');
    const email = document.getElementById('authEmail').value.trim();
    const password = document.getElementById('authPassword').value;
    btn.disabled = true;
    btn.textContent = authMode === 'register' ? 'Creating…' : 'Signing in…';
    setAuthError('');
    try {
      let result;
      if (authMode === 'register') {
        result = await API.register({
          name: document.getElementById('authName').value.trim(),
          email,
          password,
          role: document.getElementById('authRole').value,
          organization: document.getElementById('authOrg').value.trim() || null,
        });
      } else {
        result = await API.login(email, password);
      }
      Auth.token = result.access_token;
      Auth.user = result.user;
      hideLogin();
      await bootApp();
    } catch (err) {
      const detail = err.errors && err.errors.length
        ? err.errors.map(x => x.field + ': ' + x.message).join('; ')
        : err.message;
      setAuthError(detail);
      btn.disabled = false;
      btn.textContent = authMode === 'register' ? 'Create account' : 'Sign in';
    }
  });
}

window.showLogin = showLogin;

async function doLogout() {
  try { await API.logout(); } catch (e) { /* token may already be gone */ }
  Auth.token = null;
  Auth.user = null;
  location.reload();
}
window.doLogout = doLogout;

/* ---------------------------------------------------------------- boot */

let appStarted = false;

async function bootApp() {
  const overlay = document.getElementById('authOverlay');
  overlay.innerHTML = '<div class="auth-loading">Loading MP Nagar dataset…</div>';
  overlay.classList.add('open');
  try {
    await hydrateAll();
  } catch (err) {
    overlay.innerHTML = '';
    showLogin('Could not load data: ' + err.message);
    return;
  }
  hideLogin();

  if (appStarted) {
    // Re-hydration after a role switch: just repaint.
    if (typeof startApp === 'function') startApp();
    return;
  }
  appStarted = true;
  if (typeof startApp === 'function') startApp();
}

document.addEventListener('DOMContentLoaded', async () => {
  if (!Auth.token) { showLogin(); return; }
  try {
    Auth.user = await API.me();
  } catch (err) {
    if (err.status !== 401) showLogin('Could not reach the backend: ' + err.message);
    return;
  }
  await bootApp();
});
