#!/bin/bash
set -euo pipefail

# LV2 plugin validation script for dragonfly-reverb
# Usage: test.sh <package_folder> [nm_path]

PACKAGE_FOLDER="${1:?Usage: test.sh <package_folder> [nm_path]}"
NM="${2:-nm}"

LV2_DIR="${PACKAGE_FOLDER}/lib/lv2"

PLUGINS="DragonflyEarlyReflections DragonflyHallReverb DragonflyPlateReverb DragonflyRoomReverb"

for name in ${PLUGINS}; do
    BUNDLE="${LV2_DIR}/${name}.lv2"
    PLUGIN="${BUNDLE}/${name}.so"
    MANIFEST="${BUNDLE}/manifest.ttl"
    METADATA="${BUNDLE}/${name}_dsp.ttl"

    # Check plugin binary exists
    if [ ! -f "${PLUGIN}" ]; then
        echo "FAIL: Missing LV2 plugin: ${PLUGIN}" >&2
        exit 1
    fi

    # Check manifest exists
    if [ ! -f "${MANIFEST}" ]; then
        echo "FAIL: Missing manifest: ${MANIFEST}" >&2
        exit 1
    fi

    # Check DSP metadata exists
    if [ ! -f "${METADATA}" ]; then
        echo "FAIL: Missing DSP metadata: ${METADATA}" >&2
        exit 1
    fi

    # Check manifest references binary and TTL
    if ! grep -q "<${name}.so>" "${MANIFEST}"; then
        echo "FAIL: manifest missing binary reference: ${MANIFEST}" >&2
        exit 1
    fi
    if ! grep -q "<${name}_dsp.ttl>" "${MANIFEST}"; then
        echo "FAIL: manifest missing TTL reference: ${MANIFEST}" >&2
        exit 1
    fi

    # Check no UI references (ui:UI / ui:binary catch actual UI usage;
    # @prefix ui: namespace declarations are intentionally not matched)
    if grep -q "ui:UI\|ui:binary\|_ui\.so\|_ui\.ttl" "${MANIFEST}" "${METADATA}"; then
        echo "FAIL: UI reference found in metadata: ${BUNDLE}" >&2
        exit 1
    fi

    # Check lv2_descriptor symbol.
    # Capture nm output into a variable first so the NM process exit status
    # cannot leak into the pipe's exit status under `set -o pipefail`. llvm-nm
    # may return non-zero (warnings on certain ELF sections, or SIGPIPE when
    # `grep -q` exits early on large symbol tables) even when stdout correctly
    # lists the symbol — that previously caused false "missing lv2_descriptor"
    # verdicts on DragonflyPlateReverb.so (125 symbols). Only grep's exit
    # status decides whether the symbol is present.
    nm_out="$("${NM}" -D "${PLUGIN}" 2>/dev/null || true)"
    if ! grep -q "lv2_descriptor" <<<"${nm_out}"; then
        echo "FAIL: Missing lv2_descriptor export: ${PLUGIN}" >&2
        echo "  --- diagnostics ---" >&2
        echo "  file: $(file "${PLUGIN}" 2>/dev/null || echo n/a)" >&2
        echo "  size: $(stat -c%s "${PLUGIN}" 2>/dev/null || echo n/a) bytes" >&2
        echo "  nm -D defined symbols (T/B/D/W):" >&2
        grep -E ' [TBDW] ' <<<"${nm_out}" | head -30 | sed 's/^/    /' >&2
        echo "  nm -D total: $(wc -l <<<"${nm_out}") symbols" >&2
        NM_DIR="$(dirname "${NM}")"
        for _re in llvm-readelf readelf; do
            if [ -x "${NM_DIR}/${_re}" ]; then
                echo "  ${_re} --dyn-syms (lv2 lines):" >&2
                "${NM_DIR}/${_re}" --dyn-syms "${PLUGIN}" 2>/dev/null | grep -i lv2 | head -10 | sed 's/^/    /' >&2 || true
                break
            fi
        done
        exit 1
    fi

    echo "OK: Verified ${name}"
done

echo "All 4 LV2 plugins verified successfully"
