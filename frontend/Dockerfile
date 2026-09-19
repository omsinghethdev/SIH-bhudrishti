# syntax=docker/dockerfile:1

############################
# Stage 1 — normalise the static assets
############################
# Index.html asks for "styles.css" / "app.js" in lowercase while the files on
# disk are "Styles.css" / "App.js". That works on macOS and Windows but 404s on
# a case-sensitive Linux container, so the build materialises lowercase names.
FROM busybox:1.36 AS assets

WORKDIR /site
COPY Index.html Styles.css App.js api.js ./

RUN mv Index.html index.html \
 && mv Styles.css styles.css \
 && mv App.js     app.js \
 # load the generated runtime config before api.js reads window.BHUDRISHTI_API_BASE
 && sed -i 's|<script src="api.js"></script>|<script src="config.js"></script><script src="api.js"></script>|' index.html \
 && grep -q 'config.js' index.html

############################
# Stage 2 — nginx
############################
FROM nginx:1.27-alpine AS runtime

ENV BACKEND_HOST=backend \
    BACKEND_PORT=8000 \
    MAX_UPLOAD_MB=200 \
    API_BASE_URL= \
    NGINX_ENVSUBST_FILTER="^(BACKEND_HOST|BACKEND_PORT|MAX_UPLOAD_MB)$"

COPY --from=assets /site/ /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/templates/default.conf.template
COPY 40-bhudrishti-config.sh /docker-entrypoint.d/40-bhudrishti-config.sh
RUN chmod +x /docker-entrypoint.d/40-bhudrishti-config.sh

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1/healthz >/dev/null || exit 1
