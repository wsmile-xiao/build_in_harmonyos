#!/data/service/hnp/bin/bash
# test_package/test_authbind.sh — real smoke test for the packaged authbind.
#
#  1. Executes the packaged `authbind --help` and asserts rc=0 + "usage:" output.
#  2. Compiles test_dlopen.c against the packaged libauthbind.so and dlopen()s it,
#     asserting the interposition symbol "bind" resolves (libc/libdl closure).
#  3. Runs the probe with LD_PRELOAD to verify the library loads cleanly.
set -eu

binary="${AUTHBIND_BIN:-}"
libauthbind="${LIBAUTHBIND:-}"
cc="${CC:-clang}"
src_dir="${SRC_DIR:-.}"

if [ ! -x "$binary" ]; then
    echo "❌ authbind binary not executable: $binary" >&2
    exit 1
fi
if [ ! -f "$libauthbind" ]; then
    echo "❌ libauthbind not found: $libauthbind" >&2
    exit 1
fi
echo "[test] binary=$binary"
echo "[test] libauthbind=$libauthbind"

# --- 1. authbind --help smoke -------------------------------------------------
out_help="$( "$binary" --help 2>&1 )" || {
    echo "❌ authbind --help failed (rc=$?)" >&2
    echo "output: $out_help" >&2
    exit 1
}
echo "[test] authbind --help rc=0"
echo "$out_help" | grep -q "usage:" || {
    echo "❌ --help output missing 'usage:'" >&2
    echo "output: $out_help" >&2
    exit 1
}
echo "✅ AUTHBIND_HELP_OK"

# --- 2. dlopen probe against packaged libauthbind.so -------------------------
probe="$src_dir/test_dlopen.c"
if [ ! -f "$probe" ]; then
    echo "❌ probe source missing: $probe" >&2
    exit 1
fi
probe_bin="$(mktemp "$HOME/tmp/authbind-dlopen.XXXXXX")" || probe_bin="$(mktemp)"
"$cc" -o "$probe_bin" "$probe" -ldl || {
    echo "❌ probe compile failed" >&2
    exit 1
}
out_probe="$( "$probe_bin" "$libauthbind" 2>&1 )" || {
    echo "❌ dlopen probe failed (rc=$?)" >&2
    echo "output: $out_probe" >&2
    rm -f "$probe_bin"
    exit 1
}
echo "$out_probe" | grep -q "AUTHBIND_DLOPEN_BIND_SYMBOL_OK" || {
    echo "❌ probe did not confirm bind symbol" >&2
    echo "output: $out_probe" >&2
    rm -f "$probe_bin"
    exit 1
}
echo "✅ AUTHBIND_DLOPEN_BIND_SYMBOL_OK"

# --- 3. LD_PRELOAD closure load ----------------------------------------------
# Load libauthbind.so via LD_PRELOAD into a trivial process (bash) and require
# the dynamic loader to succeed — any unresolved symbol / bad DT_NEEDED in
# libauthbind.so would abort process startup with a loader error.
out_pre="$( LD_PRELOAD="$libauthbind" /data/service/hnp/bin/bash -c 'true' 2>&1 )" || {
    echo "❌ LD_PRELOAD load failed (rc=$?)" >&2
    echo "output: $out_pre" >&2
    rm -f "$probe_bin"
    exit 1
}
echo "✅ AUTHBIND_LD_PRELOAD_LOAD_OK"

rm -f "$probe_bin"
echo "✅ ALL_AUTHBIND_SMOKE_OK"
