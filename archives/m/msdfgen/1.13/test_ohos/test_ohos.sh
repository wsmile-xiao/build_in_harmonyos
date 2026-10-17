#!/usr/bin/env bash
# HarmonyOS-specific test — msdfgen 1.13
#
# Runs on OpenHarmony PC against the FINAL Conan package. Independently
# verifies platform delivery aspects the consumer test does not cover:
#   H1 ELF64 Little-Endian AArch64 class/data/machine for libmsdfgen-core,
#      libmsdfgen-ext and the CLI (a readelf failure fails the check)
#   H2 dynamic section: versioned SONAME present, no host RPATH/RUNPATH
#   H3 .codesign section present on every shipped dynamic ELF
#   H4 no host build paths leaked into binaries (strings scan)
#   H5 the CLI really generates MSDF output on OpenHarmony PC
#      (-defineshape text input — no font/image files involved)
#   H6 output structure: 64x64, 192 hex tokens per row in 00..FF, center
#      pixel decodes inside (FF-ish), corner pixels decode outside (00-ish)
#
# Usage: bash test_ohos.sh <package_folder> [readelf_path]
# The caller (test_ohos/conanfile.py) stages the runtime dependency libs
# and exports LD_LIBRARY_PATH before launching this script; the script
# itself takes no environment-directory argument.
#
# All check output is TAP (ok/not ok lines + trailing plan line) and is
# always fully emitted, including when individual checks fail. Test
# artifacts (MSDF text output, CLI stderr) go to a private temp directory
# that is removed on success, failure, Ctrl-C and timeout (SIGTERM) —
# never into the package folder.

set -euo pipefail

PKG="${1:?usage: test_ohos.sh <package_folder> [readelf_path]}"
RE="${2:-readelf}"

fail=0
checks=0
check() {
    checks=$((checks + 1))
    if [ "$2" = "ok" ]; then
        echo "ok $checks - $1"
    else
        echo "not ok $checks - $1 ($2)"
        fail=$((fail + 1))
    fi
}

# ── Private temp directory + guaranteed cleanup ────────────────────────
# Created before any check runs; removed on normal exit, on unexpected
# error (EXIT), on Ctrl-C (INT) and on timeout kills (TERM).
TMPD=""
cleanup() {
    if [ -n "$TMPD" ]; then
        rm -rf "$TMPD"
    fi
}
trap cleanup EXIT
trap 'trap - INT; cleanup; exit 130' INT
trap 'trap - TERM; cleanup; exit 143' TERM
if ! TMPD="$(mktemp -d "${TMPDIR:-/tmp}/msdfgen-test-ohos.XXXXXX" 2>/dev/null)"; then
    # /tmp may be read-only on OHOS images — try $TMPDIR, /tmp, then $HOME
    # (never ".": cwd may be inside the package folder). If no location
    # works, bail out explicitly instead of writing test output anywhere.
    if ! TMPD="$(mktemp -d "/tmp/msdfgen-test-ohos.XXXXXX" 2>/dev/null)" \
        && ! TMPD="$(mktemp -d "${HOME:?HOME not set}/msdfgen-test-ohos.XXXXXX" 2>/dev/null)"; then
        echo "Bail out! cannot create private temp directory"
        exit 1
    fi
fi

# Strict two-uppercase-hex-digit token check. Prints the decimal value and
# returns 0, or returns 1 for anything else (empty / wrong length / non
# hex) so callers record an explicit FAIL instead of letting $((16#...))
# blow up the script on garbage input.
hexval() {
    case "$1" in
        [0-9A-F][0-9A-F]) printf '%s\n' "$((16#$1))" ;;
        *) return 1 ;;
    esac
}

CORE="$PKG/lib/libmsdfgen-core.so.1.13"
EXT="$PKG/lib/libmsdfgen-ext.so.1.13"
CLI="$PKG/bin/msdfgen"

# ── H1: ELF64 / Little-Endian / AArch64, verified per artifact ────────
# readelf failing (missing file, non-ELF, broken tool) must produce a
# "not ok" check — never abort the run.
for f in "$CORE" "$EXT" "$CLI"; do
    name="$(basename "$f")"
    if hdr="$($RE -h "$f" 2>&1)"; then
        class="$(printf '%s\n' "$hdr" | sed -n 's/^ *Class: *//p')"
        data="$(printf '%s\n' "$hdr" | sed -n 's/^ *Data: *//p')"
        mach="$(printf '%s\n' "$hdr" | sed -n 's/^ *Machine: *//p')"
        if [ "$class" = "ELF64" ] \
            && [ "$data" = "2's complement, little endian" ] \
            && [ "$mach" = "AArch64" ]; then
            check "H1 $name is ELF64 Little-Endian AArch64 (machine: $mach)" ok
        else
            check "H1 $name is ELF64 Little-Endian AArch64" \
                "class=$class data=$data machine=$mach"
        fi
    else
        err="${hdr%%$'\n'*}"
        check "H1 $name is ELF64 Little-Endian AArch64" "readelf failed: $err"
    fi
done

# ── H2: SONAME + no host RPATH ────────────────────────────────────────
# Each readelf failure degrades to an empty/garbage-free parse and the
# corresponding check records "not ok" (fail closed), so the TAP stream
# and the plan line below always complete.
dyn_core="$($RE -d "$CORE" 2>&1 || true)"
dyn_ext="$($RE -d "$EXT" 2>&1 || true)"
dyn_cli="$($RE -d "$CLI" 2>&1 || true)"

son="$(printf '%s\n' "$dyn_core" | grep 'SONAME' | sed 's/.*\[\(.*\)\]/\1/' || true)"
[ "$son" = "libmsdfgen-core.so.1" ] && check "H2 core SONAME is libmsdfgen-core.so.1" ok \
    || check "H2 core SONAME is libmsdfgen-core.so.1" "got: $son"
son="$(printf '%s\n' "$dyn_ext" | grep 'SONAME' | sed 's/.*\[\(.*\)\]/\1/' || true)"
[ "$son" = "libmsdfgen-ext.so.1" ] && check "H2 ext SONAME is libmsdfgen-ext.so.1" ok \
    || check "H2 ext SONAME is libmsdfgen-ext.so.1" "got: $son"

files=("$CORE" "$EXT" "$CLI")
dyns=("$dyn_core" "$dyn_ext" "$dyn_cli")
for idx in 0 1 2; do
    f="${files[$idx]}"
    dyn="${dyns[$idx]}"
    name="$(basename "$f")"
    rp="$(printf '%s\n' "$dyn" | grep -E 'RPATH|RUNPATH' || true)"
    [ -z "$rp" ] && check "H2 $name has no RPATH/RUNPATH" ok \
        || check "H2 $name has no RPATH/RUNPATH" "$rp"
done

# ext must depend on the core via its SONAME and the CLI on both
printf '%s\n' "$dyn_ext" | grep 'NEEDED.*libmsdfgen-core\.so\.1' >/dev/null \
    && check "H2 ext NEEDED includes libmsdfgen-core.so.1" ok \
    || check "H2 ext NEEDED includes libmsdfgen-core.so.1" "missing"
printf '%s\n' "$dyn_cli" | grep 'NEEDED.*libmsdfgen-core\.so\.1' >/dev/null \
    && check "H2 CLI NEEDED includes libmsdfgen-core.so.1" ok \
    || check "H2 CLI NEEDED includes libmsdfgen-core.so.1" "missing"
printf '%s\n' "$dyn_cli" | grep 'NEEDED.*libmsdfgen-ext\.so\.1' >/dev/null \
    && check "H2 CLI NEEDED includes libmsdfgen-ext.so.1" ok \
    || check "H2 CLI NEEDED includes libmsdfgen-ext.so.1" "missing"

# ── H3: .codesign section ─────────────────────────────────────────────
for f in "$CORE" "$EXT" "$CLI"; do
    name="$(basename "$f")"
    n="$($RE -SW "$f" 2>/dev/null | grep -c 'codesign' || true)"
    [ "$n" -ge 1 ] && check "H3 $name carries .codesign section" ok \
        || check "H3 $name carries .codesign section" "count=$n"
done

# ── H4: no host build paths ───────────────────────────────────────────
for f in "$CORE" "$EXT" "$CLI"; do
    name="$(basename "$f")"
    # clang records source paths in debug info only when -g is used; the
    # release build has none, but scan anyway to keep the guarantee
    n="$(strings "$f" 2>/dev/null | grep -cE '/home/|/tmp/|storage/Users/' || true)"
    [ "$n" = "0" ] && check "H4 $name has no host paths" ok \
        || check "H4 $name has no host paths" "count=$n"
done

# ── H5: real MSDF generation on OpenHarmony PC ─────────────────────────
# Shape: an 8..56 square centered in the 64x64 viewport (the CLI fits the
# shape description to the canvas by default). Geometrically guaranteed
# sampling points: center (32,32) is deep inside; the four bitmap corners
# are outside. All input is the auditable -defineshape text vector — no
# fonts or images are involved.
OUT="$TMPD/msdf.txt"
ERRF="$TMPD/msdf.err"
rc=0
if [ -x "$CLI" ]; then
    "$CLI" msdf -defineshape "{ 8,8; 56,8; 56,56; 8,56; # }" \
        -size 64 64 -format text -stdout > "$OUT" 2> "$ERRF" || rc=$?
else
    rc=127
fi
[ "$rc" = "0" ] && check "H5 CLI generated MSDF on OHOS (exit 0)" ok \
    || check "H5 CLI generated MSDF on OHOS" "exit=$rc"
if [ "$rc" != "0" ] && [ -s "$ERRF" ]; then
    # surface the CLI's own error message for diagnosis (TAP comments)
    sed -n '1,5p' "$ERRF" | sed 's/^/# CLI stderr: /'
fi

# ── H6: output structure & pixel-level relations ──────────────────────
if [ -s "$OUT" ]; then
    rows="$(wc -l < "$OUT")"
    [ "$rows" = "64" ] && check "H6 output has 64 rows (height)" ok \
        || check "H6 output has 64 rows (height)" "rows=$rows"
    cols="$(sed -n '1p' "$OUT" | wc -w)"
    # MSDF: 3 channels per pixel -> 64 px * 3 = 192 hex tokens per row
    [ "$cols" = "192" ] && check "H6 row has 192 hex tokens (64 px x 3 ch)" ok \
        || check "H6 row has 192 hex tokens (64 px x 3 ch)" "cols=$cols"
    # all tokens valid hex bytes
    bad="$(grep -cvE '^([0-9A-F]{2} )*[0-9A-F]{2}$' "$OUT" || true)"
    [ "$bad" = "0" ] && check "H6 all tokens are 2-digit hex" ok \
        || check "H6 all tokens are 2-digit hex" "badlines=$bad"
    # center pixel (row 33 = y32, token 97 = x32 ch1) decodes inside (FF),
    # the three bitmap corners decode outside (00). Every token is
    # strictly validated as two hex characters before any 16# conversion;
    # empty or malformed tokens become explicit FAIL checks.
    ctr="$(sed -n '33p' "$OUT" | awk '{print $97}')"
    cor_tl="$(sed -n '1p' "$OUT" | awk '{print $1}')"
    cor_tr="$(sed -n '1p' "$OUT" | awk '{print $192}')"
    cor_bl="$(sed -n '64p' "$OUT" | awk '{print $1}')"

    if cval="$(hexval "$ctr")"; then
        [ "$cval" -ge 160 ] && check "H6 center pixel channel high ($ctr=inside)" ok \
            || check "H6 center pixel channel high (inside)" "got=$ctr"
    else
        check "H6 center pixel channel high (inside)" "invalid hex token: '$ctr'"
    fi

    if tl="$(hexval "$cor_tl")" && tr="$(hexval "$cor_tr")" \
        && bl="$(hexval "$cor_bl")"; then
        [ "$tl" -le 63 ] && [ "$tr" -le 63 ] && [ "$bl" -le 63 ] \
            && check "H6 corner pixels low ($cor_tl/$cor_tr/$cor_bl=outside)" ok \
            || check "H6 corner pixels low (outside)" "got=$cor_tl/$cor_tr/$cor_bl"
    else
        check "H6 corner pixels low (outside)" \
            "invalid hex token: '$cor_tl'/'$cor_tr'/'$cor_bl'"
    fi

    # structural: value domain [0,255] with meaningful spread
    mn="$(awk '{for (i = 1; i <= NF; ++i) print $i}' "$OUT" | sort | sed -n '1p')"
    mx="$(awk '{for (i = 1; i <= NF; ++i) print $i}' "$OUT" | sort | sed -n '$p')"
    if mnv="$(hexval "$mn")" && mxv="$(hexval "$mx")"; then
        [ "$mxv" -gt "$mnv" ] \
            && check "H6 field spread is non-flat (min=$mn max=$mx)" ok \
            || check "H6 field spread is non-flat" "min=$mn max=$mx"
    else
        check "H6 field spread is non-flat" "invalid hex token: '$mn'/'$mx'"
    fi
else
    check "H6 output file is non-empty" "empty"
fi

echo "1..$checks"
if [ "$fail" -gt 0 ]; then
    echo "# FAILED $fail/$checks"
    exit 1
fi
echo "# passed $checks/$checks"
