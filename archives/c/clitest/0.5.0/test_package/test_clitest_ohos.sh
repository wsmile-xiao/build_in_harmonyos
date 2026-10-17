#!/bin/sh
# test_clitest_ohos.sh — HarmonyOS-specific runtime assertions for clitest.
#
# Covers exactly the two things patches/0001-clitest.patch changes, plus the
# HMDFS/exec-bit and encoding constraints of the platform. Assertions whose
# precondition does not hold on the current host print SKIP instead of
# silently passing. Fixtures are written with printf, never with
# here-documents (see test_clitest.sh for why).
#
# Usage: test_clitest_ohos.sh <path-to-clitest> [interpreter]
set -u

CLITEST="${1:?usage: test_clitest_ohos.sh <path-to-clitest> [interpreter]}"
SH="${2:-sh}"

pass=0
fail=0
skip=0
ok() { echo "PASS: $1"; pass=$((pass + 1)); }
no() { echo "FAIL: $1 -- $2"; fail=$((fail + 1)); }
sk() { echo "SKIP: $1 -- $2"; skip=$((skip + 1)); }

WORK="$(pwd)/clitest-tp-ohos"
rm -rf "$WORK"
mkdir -p "$WORK" || { echo "FAIL: cannot create work dir $WORK"; exit 1; }

printf '%s\n' "\$ echo ok" "ok" > "$WORK/basic.txt"
printf '%s\n' \
    "\$ echo \"鸿蒙 PC — clitest ✓\"" \
    "鸿蒙 PC — clitest ✓" \
    > "$WORK/utf8.txt"
for f in "$WORK/basic.txt" "$WORK/utf8.txt"; do
    [ -s "$f" ] || { echo "FAIL: fixture $f is empty (shell could not write it)"; exit 1; }
done

# ── OHOS-1: packaged shebang points at the HarmonyOS sh (E165) ──────────────
head1=$(head -n 1 "$CLITEST")
if [ "$head1" = "#!/system/bin/sh" ]; then
    ok "packaged shebang is #!/system/bin/sh"
else
    no "packaged shebang is #!/system/bin/sh" "got '$head1'"
fi

# ── OHOS-2: the shebang interpreter really runs the packaged script ─────────
# Direct execution is tried first. Conan's cache may sit on HMDFS, where exec
# bits are not honoured; then the shebang interpreter itself must still run
# the script, and the PASS line says which path was taken.
if [ -x /system/bin/sh ]; then
    out=$("$CLITEST" --version 2>&1)
    if [ "$out" = "clitest 0.5.0" ]; then
        ok "direct execution through the #!/system/bin/sh shebang works"
    else
        out2=$(/system/bin/sh "$CLITEST" --version 2>&1)
        if [ "$out2" = "clitest 0.5.0" ]; then
            ok "/system/bin/sh runs the packaged clitest (direct exec unavailable here: '$out')"
        else
            no "/system/bin/sh runs the packaged clitest" "direct='$out' explicit='$out2'"
        fi
    fi
else
    sk "/system/bin/sh runs the packaged clitest" "/system/bin/sh not present on this host"
fi

# ── OHOS-3: $TMPDIR unset must still work when /tmp is read-only (E002) ─────
# This is the behaviour patches/0001 adds: fall back to $HOME instead of
# aborting with "cannot create temporary dir".
if [ -d /tmp ] && [ -w /tmp ]; then
    sk "read-only /tmp fallback" "/tmp is writable on this host, precondition absent"
else
    out=$(unset TMPDIR; "$SH" "$CLITEST" --progress none "$WORK/basic.txt" 2>&1)
    rc=$?
    if [ $rc -eq 0 ] && echo "$out" | grep -q '^OK: 1 of 1 test passed$'; then
        ok "runs with \$TMPDIR unset while /tmp is read-only (HOME fallback)"
    else
        no "runs with \$TMPDIR unset while /tmp is read-only" "rc=$rc out='$(echo "$out" | tail -n 1)'"
    fi
fi

# ── OHOS-4: an explicitly set but invalid $TMPDIR still fails loudly ────────
# Upstream semantics preserved by the patch (upstream test.md asserts this).
out=$(TMPDIR=/nonexistent-clitest-dir "$SH" "$CLITEST" --progress none "$WORK/basic.txt" 2>&1)
rc=$?
if [ $rc -ne 0 ] && echo "$out" | grep -q 'cannot create temporary dir'; then
    ok "explicit invalid \$TMPDIR still fails loudly (upstream semantics kept)"
else
    no "explicit invalid \$TMPDIR still fails loudly" "rc=$rc out='$(echo "$out" | tail -n 1)'"
fi

# ── OHOS-5: an explicitly set writable $TMPDIR is honoured and cleaned up ───
mkdir -p "$WORK/mytmp"
out=$(TMPDIR="$WORK/mytmp" "$SH" "$CLITEST" --progress none "$WORK/basic.txt" 2>&1)
rc=$?
leftover=$(find "$WORK/mytmp" -maxdepth 1 -name 'clitest.*' 2>/dev/null | wc -l | tr -d ' ')
if [ $rc -eq 0 ] && [ "$leftover" -eq 0 ]; then
    ok "explicit writable \$TMPDIR is used and the temp dir is cleaned up"
else
    no "explicit writable \$TMPDIR is used and cleaned up" "rc=$rc leftover=$leftover"
fi

# ── OHOS-6: exec bit independence (HMDFS normalises chmod) ──────────────────
cp "$CLITEST" "$WORK/clitest-copy"
chmod 0644 "$WORK/clitest-copy" 2>/dev/null
out=$(TMPDIR="$WORK/mytmp" "$SH" "$WORK/clitest-copy" --progress none "$WORK/basic.txt" 2>&1)
rc=$?
if [ $rc -eq 0 ] && echo "$out" | grep -q '^OK: 1 of 1 test passed$'; then
    ok "works through an explicit interpreter without the exec bit"
else
    no "works through an explicit interpreter without the exec bit" "rc=$rc out='$(echo "$out" | tail -n 1)'"
fi

# ── OHOS-7: UTF-8 payloads compare byte-exactly ─────────────────────────────
out=$(TMPDIR="$WORK/mytmp" "$SH" "$CLITEST" --progress none "$WORK/utf8.txt" 2>&1)
rc=$?
if [ $rc -eq 0 ] && echo "$out" | grep -q '^OK: 1 of 1 test passed$'; then
    ok "UTF-8 expected output compares byte-exactly"
else
    no "UTF-8 expected output compares byte-exactly" "rc=$rc out='$(echo "$out" | tail -n 1)'"
fi

# ── OHOS-8: a $TMPDIR path containing spaces never passes silently ──────────
mkdir -p "$WORK/my tmp dir"
out=$(TMPDIR="$WORK/my tmp dir" "$SH" "$CLITEST" --progress none "$WORK/basic.txt" 2>&1)
rc=$?
if [ $rc -eq 0 ] && echo "$out" | grep -q '^OK: 1 of 1 test passed$'; then
    ok "\$TMPDIR containing spaces is handled correctly"
else
    no "\$TMPDIR containing spaces is handled correctly" "rc=$rc out='$(echo "$out" | tail -n 1)'"
fi

# ── OHOS-9: the packaged tool is self-contained (single file, no helpers) ───
lines=$(wc -l < "$CLITEST" | tr -d ' ')
if [ -f "$CLITEST" ] && [ "$lines" -gt 500 ]; then
    ok "packaged clitest is the complete single-file script ($lines lines)"
else
    no "packaged clitest is the complete single-file script" "lines=$lines"
fi

rm -rf "$WORK"

echo "----------------------------------------"
echo "harmonyos: $pass passed, $fail failed, $skip skipped"
test "$fail" -eq 0
