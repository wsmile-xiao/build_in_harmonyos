#!/data/service/hnp/bin/bash
# test_package/test.sh — verify asahi-audio DSP configuration data files
set -euo pipefail

PKG_ROOT="$1"
SHARE_DIR="${PKG_ROOT}/share"

echo "[step] Verifying asahi-audio data files..."

# Verify asahi-audio data directory exists
if [ ! -d "${SHARE_DIR}/asahi-audio" ]; then
    echo "        [fail] asahi-audio data directory missing"
    exit 1
fi

# Count installed data files (wav/json/lua/conf)
FIR_COUNT=$(find "${SHARE_DIR}/asahi-audio" -type f | wc -l)
if [ "${FIR_COUNT}" -lt 60 ]; then
    echo "        [fail] Expected >=60 FIR data files, got ${FIR_COUNT}"
    exit 1
fi

# Verify WirePlumber config
if [ ! -f "${SHARE_DIR}/wireplumber/wireplumber.conf.d/99-asahi.conf" ]; then
    echo "        [fail] WirePlumber config missing"
    exit 1
fi

# Verify PipeWire config
if [ ! -f "${SHARE_DIR}/pipewire/pipewire.conf.d/99-asahi.conf" ]; then
    echo "        [fail] PipeWire config missing"
    exit 1
fi

# Verify Lua script
if [ ! -f "${SHARE_DIR}/wireplumber/scripts/device/asahi-limit-volume.lua" ]; then
    echo "        [fail] WirePlumber Lua script missing"
    exit 1
fi

# Verify alias JSON files were generated (sed-processed)
ALIAS_COUNT=$(find "${SHARE_DIR}/asahi-audio" -name "graph-j*.json" -o -name "mic-j*.json" | wc -l)
if [ "${ALIAS_COUNT}" -lt 5 ]; then
    echo "        [fail] Expected >=5 alias JSON files, got ${ALIAS_COUNT}"
    exit 1
fi

echo "        [ok] asahi-audio verified (${FIR_COUNT} data files, ${ALIAS_COUNT} alias JSONs)"
