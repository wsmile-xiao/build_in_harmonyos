#!/usr/bin/env bash
set -euo pipefail

CONF_DIR=${UNRTF_CONF_DIR:?UNRTF_CONF_DIR is required}
SAMPLE=${1:-sample.rtf}

unrtf --version

if [[ ! -f "$SAMPLE" ]]; then
  cat > "$SAMPLE" <<'RTF'
{\rtf1\ansi Hello HarmonyOS\par}
RTF
fi

output=$(unrtf -P "$CONF_DIR" --text "$SAMPLE")
printf '%s\n' "$output"

grep -q "Hello HarmonyOS" <<< "$output"
