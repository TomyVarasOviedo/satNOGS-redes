#!/usr/bin/env bash
# Prepara la demo del TFI. Correr EL MISMO DÍA de la demo, con buena conexión, desde cualquier carpeta:
#   ./backend/scripts/preparar_demo.sh            # tests, precarga de caché, endpoints de la demo y notebook
#   ./backend/scripts/preparar_demo.sh --offline  # con el wifi cortado: verifica que todo sale de la caché
# La caché de la validación se renueva por día (clave con fecha UTC): por eso no sirve prepararla días antes.
set -euo pipefail

cd "$(dirname "$0")/.."
PORT="${PORT:-8000}"
API="http://127.0.0.1:${PORT}"
LUSAT="ZDPY-4221-9426-0630-5344"
ISS="XSKZ-5603-1870-9019-3066"
MODE="${1:-}"

ENDPOINTS=(
  "/orbits/classify?sat_id=${LUSAT}"
  "/predictions/passes?sat_id=${LUSAT}&days=2"
  "/predictions/doppler?sat_id=${LUSAT}&step=5"
  "/predictions/groundtrack?sat_id=${LUSAT}"
  "/satelites/lusat"
  "/validation/satellite?sat_id=${ISS}&days=7"
  "/validation/satellite?sat_id=${LUSAT}&days=7"
)

if [ "${MODE}" != "--offline" ]; then
  echo "==> Dependencias y tests"
  uv sync --group notebook
  uv run pytest -q
  echo "==> Precarga de satélites monitoreados"
  uv run python scripts/prefetch.py
fi

echo "==> Levantando el backend en ${API}"
REFRESH_INTERVAL=86400 uv run uvicorn main:app --port "${PORT}" >/tmp/noc-demo-backend.log 2>&1 &
BACKEND_PID=$!
trap 'kill ${BACKEND_PID} 2>/dev/null || true' EXIT
for _ in $(seq 60); do
  curl -sf "${API}/" >/dev/null && break
  sleep 0.5
done

echo "==> Endpoints de la demo (X-Source: live = SatNOGS, cache/stale = caché local)"
failed=0
for path in "${ENDPOINTS[@]}"; do
  headers=$(curl -s -D - -o /dev/null --max-time 300 "${API}${path}" || true)
  status=$(printf '%s' "${headers}" | head -1 | awk '{print $2}')
  source=$(printf '%s' "${headers}" | tr -d '\r' | awk -F': ' 'tolower($1)=="x-source"{print $2}')
  printf '  %-4s %-7s %s\n' "${status:-ERR}" "${source:--}" "${path}"
  [ "${status}" = "200" ] || failed=1
done

if [ "${MODE}" != "--offline" ]; then
  echo "==> Ejecutando el notebook (gráficos actualizados)"
  NOC_API="${API}" uv run --group notebook jupyter nbconvert --to notebook --execute --inplace \
    --ExecutePreprocessor.timeout=600 notebooks/analisis.ipynb
fi

if [ "${failed}" = "1" ]; then
  echo "!! Algún endpoint no respondió 200. Ver /tmp/noc-demo-backend.log"
  exit 1
fi
echo "==> Listo. Para la demo: uv run uvicorn main:app  ->  ${API}/docs"
