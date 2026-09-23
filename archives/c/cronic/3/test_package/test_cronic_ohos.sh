#!/usr/bin/env bash
# test_cronic_ohos.sh — HarmonyOS-specific tests for the packaged cronic wrapper.
#
# Usage: bash test_cronic_ohos.sh <path-to-installed-cronic>
#
# Complements test_cronic.sh (generic behaviour) with assertions about the
# HarmonyOS runtime constraints this recipe actually has to satisfy:
#   OHOS-1 runtime tools + "#!/bin/bash" baseline (HarmonyOS has no /bin/bash)
#   OHOS-2 exec-bit independence (HMDFS normalises chmod)
#   OHOS-3 writable TMPDIR requirement (HarmonyOS /tmp is read-only) + cleanup
#   OHOS-4 UTF-8 payload; space-in-TMPDIR must never pass silently
#   OHOS-5 HNP bash compatibility (conditional: /data/service/hnp/bin/bash)
#   OHOS-6 read-only /tmp trap: TMPDIR unset must fail (conditional on host)
#
# Every executed check is a real assertion; any failure exits non-zero.
# Platform-conditional checks print SKIP (never counted as a pass) when the
# host does not expose the HarmonyOS condition they exercise.

set -u

CRONIC="${1:-}"
if [ -z "$CRONIC" ] || [ ! -f "$CRONIC" ]; then
    echo "ERROR: cronic script not found: '${CRONIC}'"
    exit 1
fi
CRONIC="$(cd "$(dirname "$CRONIC")" && pwd)/$(basename "$CRONIC")"

pass=0; fail=0; skip=0
ok()  { echo "PASS: $1"; pass=$((pass + 1)); }
bad() { echo "FAIL: $1"; fail=$((fail + 1)); }
skp() { echo "SKIP: $1"; skip=$((skip + 1)); }

# ── scratch directory (must be writable; never assume /tmp) ─────────────────
SCRATCH=""
for cand in "${TMPDIR:-}" "${HOME:-}/tmp" "/tmp"; do
    [ -n "$cand" ] || continue
    mkdir -p "$cand" 2>/dev/null || continue
    ( : > "$cand/.cronic-wtest" ) 2>/dev/null || continue
    rm -f "$cand/.cronic-wtest"
    SCRATCH="$(mktemp -d "$cand/cronic-ohos.XXXXXX" 2>/dev/null)" || SCRATCH=""
    [ -n "$SCRATCH" ] && break
done
if [ -z "$SCRATCH" ]; then
    echo "ERROR: no writable scratch directory available"
    exit 1
fi
cleanup() { rm -rf "$SCRATCH"; }
trap cleanup EXIT

echo "# cronic      = $CRONIC"
echo "# scratch     = $SCRATCH"
echo "# TMPDIR(env) = ${TMPDIR:-<unset>}"
echo "# bash        = $(command -v bash 2>/dev/null || echo '<missing>')"
echo "# /bin/bash   = $([ -e /bin/bash ] && echo present || echo absent)"
echo "# /tmp        = $( ( : > /tmp/.cronic-wtest ) 2>/dev/null && { rm -f /tmp/.cronic-wtest; echo writable; } || echo read-only)"
echo

# ── OHOS-1: runtime tools + shebang baseline ───────────────────────────────
missing=""
for tool in bash grep mktemp; do
    command -v "$tool" >/dev/null 2>&1 || missing="$missing $tool"
done
if [ -z "$missing" ]; then
    ok "OHOS-1 runtime tools available (bash/grep/mktemp)"
else
    bad "OHOS-1 missing runtime tool(s):$missing"
fi

shebang="$(head -1 "$CRONIC")"
if [ "$shebang" = "#!/bin/bash" ]; then
    ok "OHOS-1 packaged script keeps upstream shebang '#!/bin/bash'"
else
    bad "OHOS-1 unexpected shebang: '$shebang'"
fi

out="$(bash "$CRONIC" true 2>&1)"; rc=$?
if [ "$rc" -eq 0 ] && [ -z "$out" ]; then
    ok "OHOS-1 'bash <script>' invocation works from PATH bash (silent on success)"
else
    bad "OHOS-1 'bash <script>' invocation failed (rc=$rc, out='$out')"
fi

if [ ! -e /bin/bash ]; then
    direct_rc=0
    "$CRONIC" true >/dev/null 2>&1 || direct_rc=$?
    if [ "$direct_rc" -ne 0 ]; then
        ok "OHOS-1 no /bin/bash -> direct execution fails (rc=$direct_rc): shebang unresolvable, must call 'bash <script>'"
    else
        bad "OHOS-1 direct execution unexpectedly succeeded without /bin/bash"
    fi
else
    skp "OHOS-1 host has /bin/bash - 'shebang unresolvable' not exercised"
fi

# ── OHOS-2: exec-bit independence (HMDFS normalises chmod) ─────────────────
copy="$SCRATCH/cronic-mode0644"
cp "$CRONIC" "$copy"
chmod 0644 "$copy" 2>/dev/null || true
echo "  (OHOS-2 copy mode after chmod 0644: $(ls -l "$copy" | awk '{print $1}') - HMDFS may ignore chmod)"

orig="$(bash "$CRONIC" false 2>&1)"
copied="$(bash "$copy" false 2>&1)"
if printf '%s' "$copied" | grep -qF "Cronic detected failure" && printf '%s' "$copied" | grep -qF "RESULT CODE: 1"; then
    ok "OHOS-2 report reproduced from a 0644-mode copy via 'bash <script>' (exec bit not required)"
else
    bad "OHOS-2 0644-mode copy did not produce the expected report"
    printf '%s\n' "$copied"
fi
if [ "$copied" = "$orig" ]; then
    ok "OHOS-2 0644-mode copy output is byte-identical to the packaged script's"
else
    bad "OHOS-2 0644-mode copy output differs from the packaged script's"
fi

# ── OHOS-3: writable TMPDIR requirement + mktemp cleanup ───────────────────
wt="$SCRATCH/writable-tmp"; mkdir -p "$wt"
out="$(TMPDIR="$wt" bash "$CRONIC" false 2>&1)"; rc=$?
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -qF "RESULT CODE: 1"; then
    ok "OHOS-3 writable TMPDIR: cronic runs and reports correctly"
else
    bad "OHOS-3 writable TMPDIR run failed (rc=$rc)"
    printf '%s\n' "$out"
fi
residue="$(ls -A "$wt" 2>/dev/null)"
if [ -z "$residue" ]; then
    ok "OHOS-3 no temporary residue left in TMPDIR (mktemp -d cleaned up)"
else
    bad "OHOS-3 temporary residue left in TMPDIR: $residue"
fi
out="$(TMPDIR="$SCRATCH/does-not-exist" bash "$CRONIC" false 2>&1)"; rc=$?
if [ "$rc" -ne 0 ] && [ -n "$out" ]; then
    ok "OHOS-3 missing TMPDIR rejected loudly (rc=$rc, non-empty diagnostic)"
else
    bad "OHOS-3 missing TMPDIR not rejected (rc=$rc, out='$out')"
fi

# ── OHOS-4: UTF-8 payload; space-in-path must never pass silently ──────────
utf="$SCRATCH/中文目录"; mkdir -p "$utf"
out="$(TMPDIR="$utf" bash "$CRONIC" bash -c 'printf "%s\n" "中文输出-测试"; printf "%s\n" "中文错误-测试" >&2' 2>&1)"
if printf '%s' "$out" | grep -qF "中文错误-测试" && printf '%s' "$out" | grep -qF "中文输出-测试"; then
    ok "OHOS-4 UTF-8 stdout/stderr echoed verbatim in the report (UTF-8 TMPDIR)"
else
    bad "OHOS-4 UTF-8 payload not echoed correctly"
    printf '%s\n' "$out"
fi
sp="$SCRATCH/含空格 目录"; mkdir -p "$sp"
out="$(TMPDIR="$sp" bash "$CRONIC" false 2>&1)"; rc=$?
if [ "$rc" -ne 0 ] && [ -n "$out" ]; then
    ok "OHOS-4 space-in-TMPDIR fails loudly (rc=$rc) instead of a silent wrong pass - upstream limitation (unquoted \$OUT/\$TRACE at cronic:15), documented in notes.md"
elif [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -qF "RESULT CODE: 1"; then
    ok "OHOS-4 space-in-TMPDIR handled correctly (failure report produced)"
else
    bad "OHOS-4 space-in-TMPDIR neither failed loudly nor produced a correct report (rc=$rc)"
fi

# ── OHOS-5: HNP bash compatibility (conditional) ───────────────────────────
HNP_BASH="/data/service/hnp/bin/bash"
if [ -x "$HNP_BASH" ]; then
    d_sil="$(bash "$CRONIC" true 2>&1)"
    h_sil="$("$HNP_BASH" "$CRONIC" true 2>&1)"
    if [ -z "$d_sil" ] && [ -z "$h_sil" ]; then
        ok "OHOS-5 HNP bash: silent-on-success identical to default bash"
    else
        bad "OHOS-5 HNP bash silent case differs (default='$d_sil' hnp='$h_sil')"
    fi
    d_fail="$(bash "$CRONIC" false 2>&1)"
    h_fail="$("$HNP_BASH" "$CRONIC" false 2>&1)"
    if [ "$d_fail" = "$h_fail" ] && printf '%s' "$h_fail" | grep -qF "RESULT CODE: 1"; then
        ok "OHOS-5 HNP bash: failure report byte-identical to default bash"
    else
        bad "OHOS-5 HNP bash failure report mismatch"
    fi
else
    skp "OHOS-5 $HNP_BASH absent - HNP bash compatibility not exercised on this host"
fi

# ── OHOS-6: read-only /tmp trap (conditional on host) ─────────────────────
if ( : > /tmp/.cronic-wtest ) 2>/dev/null; then
    rm -f /tmp/.cronic-wtest
    skp "OHOS-6 /tmp is writable on this host - read-only-/tmp trap not exercised"
else
    out="$( unset TMPDIR; bash "$CRONIC" false 2>&1 )"; rc=$?
    if [ "$rc" -ne 0 ] && [ -n "$out" ]; then
        ok "OHOS-6 read-only /tmp: TMPDIR unset fails as expected (rc=$rc) -> TMPDIR must point to a user-writable dir"
    else
        bad "OHOS-6 read-only /tmp did not fail with TMPDIR unset (rc=$rc)"
    fi
fi

echo
echo "SUMMARY: pass=$pass fail=$fail skip=$skip"
[ "$fail" -eq 0 ]
