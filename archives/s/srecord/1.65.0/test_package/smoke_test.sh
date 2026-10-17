#!/bin/sh
# Consumer smoke test for srecord tools.
# Usage: smoke_test.sh <srec_cat> <srec_cmp> <srec_info> [qemu-wrapper...]
set -eu

SREC_CAT=$1
SREC_CMP=$2
SREC_INFO=$3
shift 3
WRAPPER="$@"

run() {
    if [ -n "$WRAPPER" ]; then
        # shellcheck disable=SC2086
        $WRAPPER "$@"
    else
        "$@"
    fi
}

run "$SREC_CAT" --version
run "$SREC_CMP" --version
run "$SREC_INFO" --version

# E002: OHOS /tmp is read-only; prefer an explicitly writable TMPDIR.
_pick_work_root() {
    for cand in \
        "${TMPDIR:-}" \
        "${SRECORD_SMOKE_TMP:-}" \
        "${HOME:+$HOME/tmp}" \
        "${HOME:+$HOME/.cache}" \
        "$(dirname "$SREC_CAT")/../_smoke_tmp" \
        "."
    do
        [ -n "$cand" ] || continue
        if mkdir -p "$cand" 2>/dev/null && [ -w "$cand" ]; then
            printf '%s\n' "$cand"
            return 0
        fi
    done
    return 1
}

WORK_ROOT=$(_pick_work_root) || {
    echo "srecord smoke_test: no writable temp dir" >&2
    exit 1
}
WORK="$WORK_ROOT/srecord-smoke-$$"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

cat >"$WORK/sample.srec" <<'EOF'
S00600004844521B
S1130000285F245F2212226A000424290008237C2A
S11300100002000800082629001853812341001813
S113002041E900084E42234300182342000824A952
S107003000144ED492
S5030004F8
EOF

run "$SREC_CAT" "$WORK/sample.srec" -o "$WORK/sample.hex" -intel
run "$SREC_CAT" "$WORK/sample.hex" -intel -o "$WORK/roundtrip.srec" -motorola
run "$SREC_CMP" "$WORK/sample.srec" "$WORK/roundtrip.srec"
run "$SREC_INFO" "$WORK/roundtrip.srec"

echo "srecord smoke_test: PASS"
