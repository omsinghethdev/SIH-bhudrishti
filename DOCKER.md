# BhuDrishti 3D — Docker & AWS deployment

Three containers, one origin:

```
            :80
  browser ──────► frontend (nginx)  ── /            static Index/app/styles
                        │            ── /api/*      proxy ─┐
                        │            ── /uploads/*  proxy ─┤
                        │            ── /docs       proxy ─┤
                                                           ▼
                                              backend (uvicorn + FastAPI)
                                                           │
                                                           ▼
                                                  db (PostgreSQL 16)
```

Only the frontend publishes a port. The API and the database stay on the internal
Compose network, so there is exactly one thing to expose in an AWS security group.

---

## 1. Run it

```bash
cp .env.example .env

# fill in the two required secrets
python3 -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(48))"
python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(24))"

docker compose up -d --build
docker compose logs -f backend      # wait for "seeding database" then "Uvicorn running"
```

Open <http://localhost> and sign in with `r.mehta@bmc.gov.in` / `Bhudrishti@2026`.
API docs are at <http://localhost/docs>.

```bash
docker compose ps           # health of each service
docker compose down         # stop, keep data
docker compose down -v      # stop and wipe database + uploads
```

## 2. Environment variables

Everything lives in the root `.env` (see `.env.example`).

| Variable | Default | Notes |
|---|---|---|
| `JWT_SECRET` | — | **Required.** Compose refuses to start without it. |
| `POSTGRES_PASSWORD` | — | **Required.** |
| `POSTGRES_DB` / `POSTGRES_USER` | `bhudrishti` | |
| `HTTP_PORT` | `80` | Host port nginx binds. |
| `FRONTEND_URL` | `http://localhost,http://127.0.0.1` | Backend CORS allow-list. Add your EC2 DNS or domain. |
| `API_BASE_URL` | *(empty)* | Empty = browser calls its own origin through the nginx proxy. Set only if the API is on a different domain. |
| `MAX_UPLOAD_MB` | `200` | Applied to both FastAPI and `client_max_body_size`. |
| `WEB_CONCURRENCY` | `2` | uvicorn workers. |
| `SEED_ON_START` | `true` | Loads the MP Nagar demo dataset on first boot. Idempotent — it skips when parcels already exist. Set `false` once you have real data. |

## 3. What the images do

**`backend/Dockerfile`** — two-stage `python:3.11-slim`. The builder compiles wheels
(including `psycopg[binary]`, which the repo's SQLite-only `requirements.txt` omits);
the runtime stage installs from those wheels, runs as the non-root user `bhudrishti`,
and exposes `/api/health` as its `HEALTHCHECK`. `docker-entrypoint.sh` waits for
PostgreSQL to accept connections, runs `python -m app.seed`, and then execs uvicorn.

**`frontend/Dockerfile`** — a busybox stage normalises the assets, then `nginx:1.27-alpine`
serves them. Two things happen at build time:

- `Index.html` / `Styles.css` / `App.js` are renamed to lowercase. The HTML requests
  `styles.css` and `app.js`, which resolves on macOS and Windows but 404s on a
  case-sensitive Linux filesystem. (The repo files are left untouched.)
- A `<script src="config.js">` tag is injected ahead of `api.js`.

At container start, `/docker-entrypoint.d/40-bhudrishti-config.sh` writes `config.js`
with `window.BHUDRISHTI_API_BASE`, so the same image works on localhost, an EC2 public
DNS name, or a custom domain without a rebuild.

## 4. Using SQLite instead of PostgreSQL

The backend image defaults to `sqlite:////data/bhudrishti.db`. For a single-container
demo with no database service:

```bash
docker build -t bhudrishti-api ./backend
docker run -d -p 8000:8000 -v bhudrishti_data:/data \
  -e JWT_SECRET="$(python3 -c 'import secrets;print(secrets.token_urlsafe(48))')" \
  bhudrishti-api
```

The entrypoint forces `WEB_CONCURRENCY=1` on SQLite, since SQLite cannot take
concurrent writers. Use PostgreSQL for anything multi-user.

## 5. Deploying on AWS

### 5a. Single EC2 instance (fastest route for the SIH demo)

1. Launch **Amazon Linux 2023**, `t3.small` or larger (the build needs ~2 GB RAM).
2. Security group inbound: **80** from `0.0.0.0/0`, **22** from your IP. Nothing else —
   the API and database are not published.
3. On the instance:

   ```bash
   sudo dnf install -y docker git
   sudo systemctl enable --now docker
   sudo usermod -aG docker ec2-user && newgrp docker

   DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
   mkdir -p $DOCKER_CONFIG/cli-plugins
   curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
     -o $DOCKER_CONFIG/cli-plugins/docker-compose
   chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose

   git clone <your-repo-url> bhudrishti && cd bhudrishti
   cp .env.example .env && nano .env     # secrets + FRONTEND_URL=http://<public-dns>
   docker compose up -d --build
   ```

4. Visit `http://<public-dns>`. `restart: unless-stopped` brings the stack back after
   an instance reboot.

### 5b. Managed AWS (production shape)

- **Database** — delete the `db` service and point `DATABASE_URL` at RDS PostgreSQL:
  `postgresql+psycopg://user:pass@<rds-endpoint>:5432/bhudrishti`. Store the password in
  Secrets Manager and inject it as a task secret.
- **Images** — `docker build` + push both to ECR, then run them as two containers in one
  **ECS Fargate** task definition. Keep `BACKEND_HOST=localhost` for the frontend
  container, because containers in a Fargate task share a network namespace.
- **Uploads** — `/data/uploads` must be an **EFS** volume, otherwise survey files vanish
  when a task is replaced. (Moving uploads to S3 would be the better long-term fix; the
  code currently writes to local disk.)
- **TLS** — terminate on an ALB with an ACM certificate, target group → port 80 of the
  frontend container, health check path `/healthz`. Uvicorn already runs with
  `--proxy-headers`, so it honours `X-Forwarded-Proto`.
- **Seeding** — set `SEED_ON_START=false` once the real dataset is loaded.

## 6. Before this is genuinely production-ready

Carried over from `backend/README.md`, and still true after containerising:

- No Alembic migrations — tables come from `Base.metadata.create_all`, so a schema change
  needs a reseed.
- Logout does not invalidate the JWT; it stays valid until it expires.
- No rate limiting on `/api/auth/login`.
- Uploaded files are validated for extension and size only.
