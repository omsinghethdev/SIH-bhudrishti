# BhuDrishti 3D — Backend

FastAPI + SQLAlchemy backend for the BhuDrishti 3D cadastre frontend. Every view in the
existing frontend is served from this API — there is no mock data left in the browser.

- **Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic v2, PyJWT, bcrypt, Uvicorn
- **Database:** SQLite for now (`backend/bhudrishti.db`), written so the only change needed
  for PostgreSQL is `DATABASE_URL`
- **Docs:** http://127.0.0.1:8000/docs

---

## 1. Quick start

```bash
cd backend

# create the virtualenv and install dependencies
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt     # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # macOS / Linux

# configure
cp .env.example .env        # then set JWT_SECRET to a real random value

# create the tables and load the MP Nagar demo dataset
.venv/Scripts/python -m app.seed

# run
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

Then serve the frontend from its own directory on a **different** port:

```bash
cd ../frontend
python -m http.server 5500
# open http://localhost:5500/Index.html
```

`python -m app.seed --reset` drops and rebuilds every table — use it when you want a clean slate.

### Demo accounts

All use the password `Bhudrishti@2026`:

| Email | Role |
|---|---|
| `r.mehta@bmc.gov.in` | Government / Planner (full access) |
| `k.nair@bmrc.co.in` | Constructor / Engineer |
| `n.iqbal@geosurv.in` | Architect / Surveyor |
| `a.sharma@example.com` | Public User (masked data) |

You can also create a new account from the sign-in screen's **Create account** tab.

---

## 2. Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `JWT_SECRET` | `change-me-in-production` | HMAC key for signing access tokens. **Set this.** |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `720` | Access-token lifetime |
| `DATABASE_URL` | `sqlite:///backend/bhudrishti.db` | SQLAlchemy connection URL |
| `FRONTEND_URL` | localhost on ports 8000/5500/3000/5173 | Comma-separated CORS origins |
| `UPLOAD_DIR` | `backend/uploads` | Where survey files are stored |
| `MAX_UPLOAD_MB` | `200` | Per-file upload ceiling |

---

## 3. Database models

| Model | Table | Notes |
|---|---|---|
| `User` | `users` | name, unique email, bcrypt hash, role enum, organization, active flag, last-active |
| `Parcel` | `parcels` | parent ULPIN (unique), address, ward/zone, registered area, Khasra no., migration status |
| `Building` | `buildings` | `slug` (the id the frontend uses), FK → parcel, survey metadata, lat/lng, JSON `infra` + `map_geometry`, conflict flag |
| `Level` | `levels` | one 3D volume: 3D ULPIN, elevation range (text + numeric min/max), area, volume, owner (+ unmasked `owner_full`), confidence, below-grade / airspace / conflict flags, JSON `rights` and render `colors`. Unique per (building, code) |
| `InfraAsset` | `infra_assets` | metro corridor, railway, parks, and the underground utility lines with depths |
| `Conflict` | `conflicts` | severity, type, affected property, overlap volume, status, officer, plain explanation, violated rule, FKs → building/level |
| `ApprovalCase` | `approval_cases` | 3D ULPIN, title, workflow stage, confidence, SLA, ward, surveyor |
| `CaseEvent` | `case_events` | append-only audit trail per case |
| `Dataset` | `datasets` | uploaded survey file: stored path, served URL, size, kind, CRS, pipeline state |
| `FloorSegment` | `floor_segments` | AI-detected floor band awaiting human verification |
| `Activity` | `activities` | recent-activity feed, written by real actions |
| `InfraProposal` | `infra_proposals` | proposed route + its stored conflict analysis, owned by a user |

Deletes cascade where it makes sense (parcel → buildings → levels → floor segments; case → events)
and null out where the record should survive (`Conflict.building_id`, `Dataset.uploaded_by_id`).

### Roles

Four roles, matching the frontend's role selector: `planner` (admin), `constructor`, `surveyor`,
`public`. `planner` passes every role guard.

| Action | Required role |
|---|---|
| Read cadastre, search, passport, analytics | any signed-in user |
| Unmasked owner names | any role except `public` |
| Survey upload, floor-segment review, create building/level | `surveyor` or `planner` |
| Conflicts (create/update/resolve), validation runs, proposals, dig-safe | `constructor` or `planner` |
| User management, delete building/level, approval decisions | `planner` only |

---

## 4. Authentication flow

1. `POST /api/auth/register` → creates the user (bcrypt hash) and returns a token, so the
   user is signed in immediately. Duplicate email → **409**.
2. `POST /api/auth/login` → verifies the password and returns
   `{access_token, token_type, expires_in, user}`. Wrong password *and* unknown email both
   return the same **401** so the endpoint doesn't reveal which emails exist.
   A deactivated account gets **403**.
3. The frontend stores the token in `localStorage` and sends
   `Authorization: Bearer <token>` on every request.
4. `GET /api/auth/me` returns the current user. Protected endpoints resolve the user through a
   FastAPI dependency; a missing, malformed or expired token is **401** (expired tokens say so),
   and a role that isn't permitted is **403**.
5. `POST /api/auth/logout` records the sign-out. JWTs are stateless, so the client discards the
   token — there is no server-side blocklist (see Assumptions).

Password hashes are never serialized: every user response goes through `UserOut`.

---

## 5. Major endpoints

Full interactive reference at `/docs`.

**Auth** — `POST /api/auth/register` · `POST /api/auth/login` · `GET /api/auth/me` ·
`PATCH /api/auth/me` · `POST /api/auth/logout`

**Users & roles** — `GET /api/users/permissions` (matrix + the caller's own nav access) ·
`GET|POST /api/users` · `GET|PATCH|DELETE /api/users/{id}`

**Cadastre** — `GET /api/locality` (whole locality map) · `GET /api/buildings` ·
`GET|POST /api/buildings` · `GET|PATCH|DELETE /api/buildings/{slug}` ·
`GET|POST /api/buildings/{slug}/levels` · `GET|PATCH|DELETE /api/buildings/{slug}/levels/{code}` ·
`GET /api/buildings/{slug}/vertical-stack` · `GET /api/parcels` · `GET /api/parcels/{ulpin}` ·
`GET /api/infra-assets` · `GET /api/depth-reference`

**Search & passport** — `GET /api/search` (text + property type, verification status, conflict,
survey year, paginated) · `GET /api/spatial-query` (radius search) ·
`GET /api/passport/{ulpin_3d}`

**Conflicts** — `GET /api/conflicts` (filter by severity/status/building, paginated) ·
`GET /api/conflicts/stats` · `POST /api/conflicts/validate` ·
`POST /api/conflicts` · `GET|PATCH|DELETE /api/conflicts/{id}` · `POST /api/conflicts/{id}/resolve`

**Approvals** — `GET /api/approvals/board` (kanban + filter options) · `GET|POST /api/approvals` ·
`GET /api/approvals/{id}` · `POST /api/approvals/{id}/decision`
(`approve` / `reject` / `return_for_correction` / `request_resurvey` / `publish`)

**Survey intake** — `GET|POST /api/datasets` (multipart upload) ·
`GET|DELETE /api/datasets/{id}` · `GET /api/datasets/{id}/pipeline` ·
`GET /api/floor-segments` · `PATCH /api/floor-segments/{id}` ·
`POST /api/floor-segments/submit` · `POST /api/floor-segments/reject`

**Planning** — `GET /api/infra-profiles` · `GET|POST /api/proposals` ·
`POST /api/proposals/{id}/analyze` · `GET /api/utility/assets` · `POST /api/utility/dig-safe` ·
`GET /api/ulpin/wizard-config` · `GET /api/ulpin/preview` · `GET /api/ulpin/validate-geometry` ·
`POST /api/ulpin/generate`

**Insights & settings** — `GET /api/overview` · `GET /api/analytics` · `GET /api/reports` ·
`GET /api/reports/{name}/export` · `GET /api/activity` · `GET /api/settings` ·
`GET /api/settings/ladm-mapping` · `GET /api/settings/legacy-mapping` · `GET /api/health`

### Error shape

`{"detail": "..."}` for 400/401/403/404/409/413. Validation failures add a field list:

```json
{ "detail": "Validation failed",
  "errors": [{ "field": "email", "message": "value is not a valid email address" }] }
```

---

## 6. How the frontend connects

The frontend gained one new file, `frontend/api.js`, loaded before `app.js`. It:

1. **Points at the backend** — `http://127.0.0.1:8000/api` by default. Override by setting
   `window.BHUDRISHTI_API_BASE` before the script tag.
2. **Gates the app behind sign-in** — renders a sign-in / create-account card over the shell,
   stores the token in `localStorage`, and clears it on a 401 so the user is asked to sign in again.
3. **Hydrates the globals `app.js` already renders from** — `LOCALITY`, `LEVELS`, `LEVEL_DETAIL`,
   `BUILDINGS_EXTRA`, `CONFLICTS`, `APPROVAL_COLUMNS`, `DATASETS`, `SEARCH_RESULTS`,
   `PERMISSION_MATRIX` and the rest were hardcoded demo objects; they are now filled from the API
   before the first render. The rendering code itself is unchanged.
4. **Calls `startApp()`** once the data is in place (`app.js`'s old `DOMContentLoaded` body).

Actions that previously only raised a toast now hit the API: sign in/out, run validation, resolve a
conflict, approve/return/re-survey/reject a case, dig-safe clearance, the 3D route conflict
analysis, spatial query, survey upload (drag-and-drop and Browse), floor-segmentation submit,
3D ULPIN generation, search, and Add User.

The role dropdown now shows the signed-in account's role and is read-only — the role comes from the
JWT and the server decides what the session may see, so the client can't grant itself access.
To view the app as another role, sign in with that account.

**CORS** is restricted to the origins in `FRONTEND_URL`. If you serve the frontend on a different
port, add it there — a blocked origin shows up as a failed fetch in the browser console.

---

## 7. What was tested

`41` backend tests plus `75` browser-level integration checks, all passing.

```bash
cd backend
.venv/Scripts/python -m pytest tests -q        # 41 passed
```

The pytest suite (`tests/test_api.py`) runs against a temporary seeded SQLite database and covers:

- server boots, database initializes, `/api/health` responds
- registration; duplicate email → 409; invalid email and short password → 422 with field errors
- login; wrong password and unknown email → identical 401; deactivated account → 403
- `/auth/me`, profile update, password change then re-login, logout
- protected endpoints reject anonymous requests, malformed tokens, and expired tokens
- authorization: public user blocked from user admin and from creating proposals/uploads (403);
  surveyor blocked from officer decisions; users can't delete another user's proposal or
  deactivate/delete their own account
- owner masking: public role gets `A. Sharma (masked)`, officials get `Anil Sharma`
- response shapes match what the frontend reads (building meta keys, level keys, conflict keys)
- locality map, building detail, levels, vertical stack bands, depth reference, infra assets
- search: text, ULPIN, property type, verification status, conflict, survey year, pagination
  (no overlap between pages), bad filter → 400; passport masking and 404
- conflicts: list/filter/stats, validation run reports real failures, full CRUD, resolve clears the
  level and building flags, double-resolve → 409
- approvals: board columns and counts, case detail with audit trail, every decision transition,
  already-decided → 409, unknown action → 422
- uploads: real multipart upload stored and served, rejected extension → 400, LiDAR upload
  generates floor segments, pipeline stages, segment edit and submit, second submit → 404
- planning: route analysis finds the basement intersection and the metro pier rule, a deep route
  clears, same-from-and-to → 400, out-of-range depth → 422; dig-safe clear/review/prohibited
  thresholds; spatial query distances
- ULPIN wizard: preview, geometry validation, duplicate 3D ULPIN → 409, generation persists the
  volume and creates the approval case, parcel/building mismatch → 400
- building and level CRUD including slug pattern and confidence-range validation
- overview, analytics, reports catalogue and export guard, settings, LADM and legacy mapping
- activity feed records real actions
- CORS preflight returns the frontend origin

Frontend integration was verified by loading the actual `Index.html`, `api.js` and `app.js` in a
jsdom browser environment against the running server, signing in through the real form, and
asserting the DOM: **61 read/render checks** (every view renders server data — overview KPIs,
locality map, both buildings' 3D levels, conflict radar and drawer, kanban and case drawer,
server-side search filtering, vertical stack, underground, proposal analysis, dig-safe verdicts,
intake, wizard validation, analytics, permission matrix, settings) and **14 write-path checks**
(upload from the dropzone persists and the file is downloadable; Resolve persists, records the
officer from the JWT, clears the level flag and repaints; Approve moves the case and writes the
audit entry; requests fail with 401 after logout). No uncaught page errors.

That round caught three real defects, all fixed: the hydrated globals were declared with `let`
(which doesn't reliably share a binding across script tags — now `var`), several KPI blocks were
still rendering hardcoded numbers from inside the render functions, and `api.js` depended on a
`const` declared in `app.js`.

---

## 8. Assumptions and remaining gaps

**Assumptions**

- `lakeview` is the primary building record. The frontend hardcodes that id in several places
  (the "flagship" unit, default level selection), so the hydration keeps the same convention:
  `lakeview` fills `LEVELS`/`LEVEL_DETAIL`, other buildings fill `BUILDINGS_EXTRA`.
- Elevations are stored both as the display string the UI shows (`"-6.2 m – -3.0 m"`) and as
  numeric `elevation_min`/`elevation_max`, which is what the depth-conflict maths uses. Both are
  written by the seed; the API keeps them in sync on create.
- Dig-safe thresholds are derived from the registered utility assets rather than hardcoded, and
  land on the same 2.4 m / 3.6 m boundaries the prototype used. Changing an asset's depth moves
  the thresholds.
- The metro pier rule (GEO-02) fires when a building's `infra.metro` note mentions piers, which is
  how the seeded DB Trade Centre case is expressed — not a hardcoded building id.
- Seed counts are real (3 parcels, 3 buildings, 23 volumes, 9 conflicts), so the dashboards show
  small numbers rather than the prototype's invented 2,184 parcels. That is deliberate: the KPIs
  now count rows.
- Confidence scores and survey dates come from the seed. Nothing recomputes a confidence score —
  there is no scoring model, so the API returns what was recorded.

**Gaps**

- **Report export returns data, not files.** `GET /api/reports/{name}/export` returns the row
  counts that would be included. Writing actual PDF/CityGML/Shapefile output needs a rendering
  library and was out of scope; the frontend's format buttons are still display-only.
- **Logout doesn't invalidate the token.** With stateless JWTs the token stays valid until it
  expires. For real deployment add a short access-token lifetime plus refresh tokens, or a
  server-side revocation list.
- **No geometry engine.** Conflict detection compares stored depth ranges and elevation bands; it
  does not do true solid intersection. `overlap_volume` is a recorded value, not a computed one.
  Real volumetric checks would need PostGIS or a 3D geometry library.
- **Uploaded files are parsed for type and size only.** Nothing reads the LAS/GeoJSON contents,
  and the AI floor segmentation is derived from the building's existing levels rather than from the
  point cloud. The pipeline stages reflect the dataset's recorded state.
- **No rate limiting** on login, and no password-reset or email-verification flow.
- **`Index.html` requests `styles.css` and `app.js` in lowercase** while the files on disk are
  `Styles.css` and `App.js`. This works on Windows and macOS but will 404 on a case-sensitive
  Linux host — rename the files or the references before deploying there.
- **`SQLite` concurrency.** Fine for development; switch `DATABASE_URL` to PostgreSQL before any
  multi-user deployment. No Alembic migrations yet — tables are created with
  `Base.metadata.create_all`, so schema changes currently need a `--reset` reseed.

`backend/scripts/wire_frontend.py` is the one-off script that converted the frontend's hardcoded
demo constants into hydrated globals. It is idempotent and kept for reference;
`frontend/App.js.bak` is the original file before that change.
