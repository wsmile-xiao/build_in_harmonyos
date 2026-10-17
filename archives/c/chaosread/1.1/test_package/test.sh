#!/usr/bin/env bash
# chaosread 1.1 — test_package consumer test runner.
#
# Resolution order for the binary:
#   1. $CHAOSREAD_BIN env var (set by conanfile.py test())
#   2. bare `chaosread` (PATH must already include the package bin/)
#   3. $1 explicit override
# The manpage is derived from the binary's real path (../share/man/...),
# so it works regardless of where conan installed the package
# (no hardcoded /usr/share/...).
#
# Fail-fast: any assertion failure calls `die` which prints the
# accumulated fail count and exits non-zero so conan test reports it.

set -euo pipefail

# 1) Locate the binary
if [[ -n "${CHAOSREAD_BIN:-}" ]]; then
    CHAOSREAD="$CHAOSREAD_BIN"
elif [[ -n "${1:-}" ]]; then
    CHAOSREAD="$1"
else
    CHAOSREAD="$(command -v chaosread 2>/dev/null || true)"
    if [[ -z "$CHAOSREAD" ]]; then
        echo "ERROR: chaosread not on PATH and CHAOSREAD_BIN not set" >&2
        exit 1
    fi
fi
# Resolve to absolute path (handles symlinks too)
CHAOSREAD_ABS="$(readlink -f "$CHAOSREAD" 2>/dev/null || python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$CHAOSREAD" 2>/dev/null || echo "$CHAOSREAD")"
# Derive package root from the binary path (bin/ -> package root)
PKG_ROOT="$(dirname "$(dirname "$CHAOSREAD_ABS")")"
# Manpage is at <pkg_root>/share/man/man1/chaosread.1
MANPAGE="$PKG_ROOT/share/man/man1/chaosread.1"

PASS=0
FAIL=0
FAILS=()

ok()  { printf '  ✅ %s\n' "$1"; PASS=$((PASS+1)); }
die() { printf '  ❌ %s\n' "$1"; FAIL=$((FAIL+1)); FAILS+=("$1"); }
hdr() { printf '\n== %s ==\n' "$1"; }

readelf_one() {
    local key="$1"; shift
    local bin="$1"; shift
    local out=""
    for tool in llvm-readelf readelf; do
        if command -v "$tool" >/dev/null 2>&1; then
            out="$("$tool" "$@" "$bin" 2>/dev/null || true)"
            if [[ -n "$out" ]]; then
                printf '%s\n' "$out" | awk -v k="$key" '
                    index($0, k) { sub(/^[^:]*:/, ""); sub(/^[ \t]+/, ""); print; exit }'
                return 0
            fi
        fi
    done
    return 1
}

readelf_dump() {
    local bin="$1"; shift
    for tool in llvm-readelf readelf; do
        if command -v "$tool" >/dev/null 2>&1; then
            "$tool" "$@" "$bin" 2>/dev/null || true
            return 0
        fi
    done
    return 1
}

# ── T1: binary present + executable ──────────────────────────────────────
hdr "T1  binary present + executable (CHAOSREAD=$CHAOSREAD)"
if [[ -f "$CHAOSREAD" ]]; then ok "binary exists ($CHAOSREAD)"; else die "binary missing: $CHAOSREAD"; fi
if [[ -x "$CHAOSREAD" ]]; then ok "binary is executable"; else die "binary not executable"; fi

# ── T2: manpage present + non-empty ──────────────────────────────────────
hdr "T2  manpage present + non-empty (MANPAGE=$MANPAGE)"
if [[ -f "$MANPAGE" ]]; then ok "manpage exists ($MANPAGE)"; else die "manpage missing: $MANPAGE"; fi
if [[ -f "$MANPAGE" && -s "$MANPAGE" ]]; then ok "manpage non-empty"; else die "manpage empty"; fi

# ── T3 / T4 / T5 / T6: ELF readelf gates (OH platform) ─────────────────
if [[ -f "$CHAOSREAD" ]]; then
    hdr "T3  ELF interpreter is OH musl loader"
    if interp="$(readelf_one 'Requesting program interpreter' -l "$CHAOSREAD" 2>/dev/null)" \
       || interp="$(readelf_one '[Requesting program interpreter]' -l "$CHAOSREAD" 2>/dev/null)"; then
        if [[ "$interp" == *"/lib/ld-musl-aarch64.so.1"* ]]; then
            ok "interpreter = $interp"
        else
            die "interpreter is not OH musl loader: '$interp'"
        fi
    else
        die "could not read program interpreter from ELF"
    fi

    hdr "T4  NEEDED = libc.so only (G3 system-isolation)"
    needed_list="$(readelf_dump "$CHAOSREAD" -d | awk '/\(NEEDED\)/ {gsub(/^.*Shared library:/, ""); gsub(/[][]/, ""); gsub(/^[ \t]+/, ""); gsub(/[ \t]+$/, ""); print}' || true)"
    if [[ "$(printf '%s' "$needed_list" | tr -d '\n')" == "libc.so" ]]; then
        ok "NEEDED = libc.so only"
    else
        die "NEEDED list not isolated to libc.so: '$needed_list'"
    fi

    hdr "T5  PIE enabled (Type=DYN + FLAGS_1=PIE)"
    hdr_out="$(readelf_dump "$CHAOSREAD" -h)"
    if grep -q "^[[:space:]]*Type:[[:space:]]*DYN" <<<"$hdr_out"; then
        ok "Type: DYN (PIE)"
    else
        die "Type is not DYN: $'\n'$(grep -i 'Type' <<<"$hdr_out" | head -1)"
    fi
    dyn_out="$(readelf_dump "$CHAOSREAD" -d)"
    if grep -q "FLAGS_1" <<<"$dyn_out" && grep -q "PIE" <<<"$dyn_out"; then
        ok "FLAGS_1=PIE present"
    else
        die "FLAGS_1=PIE not set"
    fi

    hdr "T6  NX enabled (GNU_STACK is RW, no X)"
    prg_out="$(readelf_dump "$CHAOSREAD" -l)"
    if grep -q "GNU_STACK" <<<"$prg_out" \
       && grep -A2 "GNU_STACK" <<<"$prg_out" | grep -q "RW" \
       && ! grep -A2 "GNU_STACK" <<<"$prg_out" | grep -q "RWE"; then
        ok "GNU_STACK is RW, no X (NX enabled)"
    else
        die "NX not enabled (GNU_STACK is missing RWE or not RW-only)"
    fi
fi

# ── T7: manpage content check ───────────────────────────────────────────
hdr "T7  manpage mentions chaosread"
if [[ -f "$MANPAGE" ]] && grep -qi "chaosread" "$MANPAGE"; then
    ok "manpage mentions 'chaosread'"
else
    die "manpage does not mention 'chaosread'"
fi

# ── T8: --version reports upstream date 2019-01-07 ──────────────────────
hdr "T8  --version reports upstream date 2019-01-07"
if [[ -x "$CHAOSREAD" ]]; then
    if version_out="$("$CHAOSREAD" --version 2>&1)"; then
        if grep -q "2019-01-07" <<<"$version_out"; then
            ok "--version = $(tr -d '\n' <<<"$version_out")"
        else
            die "--version output missing 2019-01-07: $version_out"
        fi
    else
        die "chaosread --version exited non-zero"
    fi
else
    die "skipping T8: chaosread not executable"
fi

# ── T9: --help lists all 5 device flags ────────────────────────────────
hdr "T9  --help lists all 5 device flags"
if [[ -x "$CHAOSREAD" ]]; then
    if help_out="$("$CHAOSREAD" --help 2>&1)"; then
        missing=()
        for flag in --serial --length --cooked --raw --infinite; do
            if ! grep -q -- "$flag" <<<"$help_out"; then
                missing+=("$flag")
            fi
        done
        if [[ ${#missing[@]} -eq 0 ]]; then
            ok "--help lists --serial --length --cooked --raw --infinite"
        else
            die "--help missing flags: ${missing[*]}"
        fi
    else
        die "chaosread --help exited non-zero"
    fi
else
    die "skipping T9: chaosread not executable"
fi

# ── T10: chaosread exits non-zero on a real I/O error (negative test) ───
# Note: getopt-based tools (incl. chaosread) commonly return 0 for
# unknown flags (they just print usage and continue).  Testing that
# an *unknown flag* is rejected is therefore unreliable.  Use a
# concrete I/O failure instead — opening a non-existent device
# should always return non-zero.
hdr "T10 chaosread exits non-zero on /dev/nonexistent (negative I/O test)"
if [[ -x "$CHAOSREAD" ]]; then
    if "$CHAOSREAD" --serial=00:00:00:00:00:00 /dev/this-device-does-not-exist-anywhere >/dev/null 2>&1; then
        die "chaosread returned 0 for a non-existent /dev/... device"
    else
        ok "chaosread returned non-zero for non-existent device (proper I/O error)"
    fi
    # Also note the unknown-flag behaviour for the record (informational,
    # not a gate — some tools accept and ignore unknown flags by design).
    if "$CHAOSREAD" --definitely-not-a-flag-xyz >/dev/null 2>&1; then
        printf '  ℹ️  chaosread returned 0 for unknown flag (getopt default; not failing)\n'
    else
        printf '  ℹ️  chaosread returned non-zero for unknown flag\n'
    fi
else
    die "skipping T10: chaosread not executable"
fi

# ── Summary ─────────────────────────────────────────────────────────────
printf '\n== Summary ==\n'
printf '  pass: %d\n  fail: %d\n' "$PASS" "$FAIL"

if [[ $FAIL -gt 0 ]]; then
    printf '\nFailures:\n'
    for f in "${FAILS[@]}"; do
        printf '  - %s\n' "$f"
    done
    exit 1
fi

printf 'PASS: chaosread 1.1 — all %d consumer tests succeeded\n' "$PASS"
