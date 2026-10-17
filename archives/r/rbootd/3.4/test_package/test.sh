#!/data/service/hnp/bin/bash
# test_package/test.sh — functional smoke test for the packaged rbootd binary.
# Runs inside the conanrun env (PATH includes the installed bin/).
#
# rbootd is a privileged network daemon: a bare run daemonizes and needs a
# live capture interface plus root, so the smoke test only exercises the
# deterministic startup path (getopt option handling) and the OHOS
# cross-build properties of the packaged artifact.
#
# Only bash, od, tr and grep are used.  On OHOS the PATH picks up the toybox
# tools in /system/bin, and toybox grep refuses to search binary files (it
# ignores -a), so the ELF string checks render the bytes as text with
# `od -An -t c | tr -d ' \n'` and match the resulting stream.
set -u

BIN="$(command -v rbootd || true)"
if [ -z "$BIN" ] || [ ! -x "$BIN" ]; then
    echo "FAIL: rbootd not found on PATH"
    exit 1
fi

# Test 1 (functional): the binary executes on OHOS and getopt parses options.
# `-d` keeps it in the foreground (no daemon fork) and `-Z` is an invalid
# option, so getopt writes "unrecognized option: Z" to stderr before rbootd
# reaches its capture loop.  rbootd may then block waiting for packets, so the
# child is bounded with a short timeout and killed afterwards.
tmp="${TMPDIR:-$HOME/tmp}"
mkdir -p "$tmp" 2>/dev/null
outfile="$tmp/rbootd-getopt-$$.out"
rbootd -d -Z > "$outfile" 2>&1 < /dev/null &
child=$!
for _ in 1 2 3 4 5; do
    sleep 1
    kill -0 "$child" 2>/dev/null || break
done
kill "$child" 2>/dev/null
wait "$child" 2>/dev/null
out="$(< "$outfile")"
rm -f "$outfile"
case "$out" in
    *"unrecognized option: Z"*)
        echo "PASS: rbootd executes and getopt rejects -Z" ;;
    *)
        echo "FAIL: rbootd did not report the invalid option; output was: [$out]"
        exit 1 ;;
esac

# Test 2 (OHOS-specific): the packaged binary is an aarch64 / HarmonyOS(musl)
# ELF — i.e. it was really cross-built for the OHOS target.
# e_machine at ELF offset 18 (2 bytes, little-endian) must be 0xB7 = AArch64.
machine="$(od -An -t x1 -j 18 -N 2 "$BIN" | tr -d ' \n')"
if [ "$machine" != "b700" ]; then
    echo "FAIL: unexpected ELF e_machine: $machine (want b700 = AArch64)"
    exit 1
fi
# The dynamic loader string is unique to the OHOS/musl target.
if ! od -An -t c "$BIN" | tr -d ' \n' | grep -qF "ld-musl-aarch64.so.1"; then
    echo "FAIL: rbootd is not linked against the OHOS/musl loader"
    exit 1
fi
echo "PASS: OHOS aarch64 ELF (musl loader + e_machine AArch64)"

# Test 3 (OHOS-specific / dependency): libpcap is linked statically, so the
# binary has no dynamic dependency on libpcap.so (system-name lib isolation).
if od -An -t c "$BIN" | tr -d ' \n' | grep -qF "libpcap.so"; then
    echo "FAIL: rbootd has a dynamic libpcap.so dependency (expected static)"
    exit 1
fi
echo "PASS: libpcap linked statically (no libpcap.so dependency)"
