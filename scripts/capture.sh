#!/usr/bin/env bash
# Run from the project root in DragonOS. Reception only.
set -euo pipefail
frequency_mhz="${1:-1970}"
duration="${2:-120}"
point="${3:-P01}"
command -v FalconEye >/dev/null || { printf 'FalconEye no esta en PATH.\n' >&2; exit 1; }
command -v timeout >/dev/null || { printf 'Se necesita GNU timeout.\n' >&2; exit 1; }
python3 - "$frequency_mhz" "$duration" "$point" <<'PY'
import math, re, sys
f, d = map(float, sys.argv[1:3])
if not (math.isfinite(f) and 0 < f < 10000 and math.isfinite(d) and 5 <= d <= 3600):
    sys.exit('Frecuencia o duracion fuera del rango admitido (5..3600 s).')
if not re.fullmatch(r'[A-Za-z0-9_-]{1,40}', sys.argv[3]):
    sys.exit('Punto: solo letras, numeros, guion y guion bajo.')
PY
if pgrep -x FalconGUI >/dev/null || pgrep -x FalconEye >/dev/null; then
    printf 'Cierra las otras instancias de FalconGUI/FalconEye antes de capturar.\n' >&2
    exit 1
fi
session="capture_$(date +%Y%m%d_%H%M%S)_${point}"
session_dir="$PWD/data/raw/$session"
mkdir -p "$session_dir"
frequency_hz=$(python3 -c 'import sys; print(round(float(sys.argv[1])*1e6))' "$frequency_mhz")
{
    printf 'session=%s\n' "$session"
    printf 'frequency_hz=%s\n' "$frequency_hz"
    printf 'receiver_label=LibreSDR Mini B220; UHD detection may report B210\n'
    printf 'location_label=%s\n' "$point"
    printf 'wall_time_limit_seconds=%s\n' "$duration"
    printf 'started=%s\n' "$(date --iso-8601=seconds)"
    printf 'requested_subframes=0 (unlimited; externally time bounded)\n'
    printf 'gain=AGC default\n'
    printf 'antenna_and_host_conditions=complete notes.md manually\n'
} > "$session_dir/metadata.txt"
printf 'Sesion: %s\nLimite de tiempo TOTAL, incluye busqueda de celda: %s s\n' "$session_dir" "$duration"
set +e
timeout --signal=INT --kill-after=15s "${duration}s" \
    FalconEye -f "$frequency_hz" -n 0 -r \
    -D "$session_dir/dci.tsv" -E "$session_dir/stats.txt" \
    2>&1 | tee "$session_dir/console.log"
capture_status=${PIPESTATUS[0]}
set -e
{
    printf 'finished=%s\n' "$(date --iso-8601=seconds)"
    printf 'capture_exit_code=%s\n' "$capture_status"
} >> "$session_dir/metadata.txt"
cat > "$session_dir/notes.md" <<'EOF'
# Bitacora
- Antena y orientacion:
- Interior/exterior:
- Ejecucion nativa o VM:
- Aplicaciones abiertas:
- PCI y PRB confirmados por adquisicion (no valores predeterminados de GUI):
- Cambios durante la sesion:
- Advertencias y limitaciones:
EOF
printf '\nArchivos guardados en %s\n' "$session_dir"
if [[ "$capture_status" == 124 ]]; then
    printf '124: se alcanzo el limite de tiempo; revisar cierre y estadisticas en console.log.\n'
elif [[ "$capture_status" != 0 ]]; then
    printf 'Captura con codigo %s; revisar console.log antes de interpretar datos.\n' "$capture_status" >&2
    exit "$capture_status"
fi
if [[ ! -s "$session_dir/dci.tsv" ]]; then
    printf 'No hay registros DCI. Esta sesion no sirve para analizar actividad.\n' >&2
    exit 2
fi
printf 'Siguiente paso: python3 scripts/analyze.py --input "%s/dci.tsv" --console "%s/console.log" --session-label "%s" --frequency-mhz "%s"\n' "$session_dir" "$session_dir" "$session" "$frequency_mhz"
