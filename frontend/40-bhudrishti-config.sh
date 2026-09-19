#!/bin/sh
# Writes the runtime config the browser reads before api.js loads.
#
# api.js does:  (window.BHUDRISHTI_API_BASE || 'http://127.0.0.1:8000') + '/api'
# Leaving API_BASE_URL empty makes the app call its own origin, which is what
# you want when nginx proxies /api to the backend (single ALB / single domain).
# Set it only when the API lives on a different host, e.g. https://api.example.com
set -eu

: "${API_BASE_URL:=}"

cat > /usr/share/nginx/html/config.js <<JS
// Generated at container start — do not edit, do not commit.
window.BHUDRISHTI_API_BASE = "${API_BASE_URL}" || window.location.origin;
JS

echo "[bhudrishti] API base = ${API_BASE_URL:-<same origin>}"
