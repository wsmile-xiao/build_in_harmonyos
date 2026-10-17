#!/bin/bash
# nmh test_package runner (run under the conanrun environment).
#
# Case inventory (must stay in sync with MANIFEST.yml / manifest.yaml):
#   1-44 : every installed ELF command answers -version with "nmh-1.8"
#          (the sendfiles and mhmail shell wrappers are excluded: they
#          spawn compile-time /libexec/nmh helper paths)
#   45-53: functional mail-folder workflows (mhparam, scan, pick,
#          folder, mark, flist, packf, rmm)
#   54-58: negative paths (missing MH profile, no MH/no home profile,
#          missing mts.conf, unknown folder, malformed MH profile)
#
# The runner prints one PASS/FAIL line per case plus a final
# "NMH_TEST_SUMMARY total=.. pass=.. fail=.." line.

set -u

export LC_ALL=C
export LANG=C

PKG="$1"
WORK="$2"

BIN="$PKG/bin"
ETC="$PKG/etc/nmh"
MHMTSCONF_DEFAULT="$ETC/mts.conf"

HOME_DIR="$WORK/home"
MAIL_DIR="$WORK/mail"
PROFILE_DIR="$WORK/profile"
PROFILE="$PROFILE_DIR/.mh_profile"

rm -rf "$WORK"
mkdir -p "$HOME_DIR" "$MAIL_DIR" "$PROFILE_DIR"
printf 'path: %s\nUnseen-Sequence: unseen\n' "$MAIL_DIR" > "$PROFILE"

PASS=0
FAIL=0

note_pass() {
    PASS=$((PASS + 1))
    echo "PASS $1"
}

note_fail() {
    FAIL=$((FAIL + 1))
    echo "FAIL $1 :: $2"
}

# run_capture <outfile> <errfile> <rcfile> -- cmd args...
run_capture() {
    local out="$1" err="$2" rc="$3"
    shift 3
    "$@" >"$out" 2>"$err"
    echo "$?" > "$rc"
}

expect_ok() {
    local name="$1" out="$2" err="$3" rc="$4" needle="$5"
    if [ "$(cat "$rc")" -ne 0 ]; then
        note_fail "$name" "rc=$(cat "$rc") stderr=$(head -c 140 "$err")"
    elif [ -n "$needle" ] && ! grep -q "$needle" "$out" "$err" 2>/dev/null; then
        note_fail "$name" "needle '$needle' not found"
    else
        note_pass "$name"
    fi
}

export HOME="$HOME_DIR"
export MH="$PROFILE"
export MHMTSCONF="$MHMTSCONF_DEFAULT"
export TERMINFO="${TERMINFO:-/nonexistent}"
unset TERMINFO_DIRS

i=0
for b in "$BIN"/*; do
    i=$((i + 1))
    name="smoke-$i-$(basename "$b")"
    magic=$(head -c 4 "$b")
    if [ "$magic" != "$(printf '\177ELF')" ]; then
        # shell wrappers (e.g. sendfiles) spawn compile-time libexec
        # paths that do not exist in the sandbox
        echo "SKIP $name (non-ELF script)"
        continue
    fi
    run_capture "$WORK/o" "$WORK/e" "$WORK/r" "$b" -version
    if [ "$(cat "$WORK/r")" -eq 0 ] && grep -q 'nmh-1.8' "$WORK/o"; then
        note_pass "$name"
    else
        note_fail "$name" "rc=$(cat "$WORK/r") out=$(head -c 100 "$WORK/o") err=$(head -c 100 "$WORK/e")"
    fi
done

mkdir -p "$MAIL_DIR/inbox"
printf 'From: sender@example.com\nTo: you@example.com\nSubject: hello nmh test\nDate: Thu, 1 Jan 2026 10:00:00 +0000\n\nBody line one.\n' > "$MAIL_DIR/inbox/1"

run_capture "$WORK/o" "$WORK/e" "$WORK/r" "$BIN/mhparam" version
expect_ok "f-mhparam-version" "$WORK/o" "$WORK/e" "$WORK/r" '^nmh-1.8'

run_capture "$WORK/o" "$WORK/e" "$WORK/r" "$BIN/mhparam" path
expect_ok "f-mhparam-path" "$WORK/o" "$WORK/e" "$WORK/r" "^$MAIL_DIR"

run_capture "$WORK/o" "$WORK/e" "$WORK/r" "$BIN/scan" +inbox
expect_ok "f-scan-inbox" "$WORK/o" "$WORK/e" "$WORK/r" 'hello nmh test'

run_capture "$WORK/o" "$WORK/e" "$WORK/r" "$BIN/pick" -subject hello -list +inbox
expect_ok "f-pick-subject" "$WORK/o" "$WORK/e" "$WORK/r" '^1'

run_capture "$WORK/o" "$WORK/e" "$WORK/r" "$BIN/folder" +inbox
expect_ok "f-folder-count" "$WORK/o" "$WORK/e" "$WORK/r" 'has 1 message'

run_capture "$WORK/o" "$WORK/e" "$WORK/r" "$BIN/mark" +inbox 1 -sequence seen
if [ "$(cat "$WORK/r")" -ne 0 ]; then
    note_fail "f-mark-sequence" "rc=$(cat "$WORK/r") $(head -c 140 "$WORK/e")"
else
    run_capture "$WORK/o" "$WORK/e" "$WORK/r" "$BIN/pick" +inbox -sequence seen -list
    if [ "$(cat "$WORK/r")" -ne 0 ]; then
        note_fail "f-mark-sequence-verify" "rc=$(cat "$WORK/r")"
    elif grep -q '^1' "$WORK/o"; then
        note_pass "f-mark-sequence"
    else
        note_fail "f-mark-sequence-verify" "no message listed: $(head -c 100 "$WORK/o")"
    fi
fi

run_capture "$WORK/o" "$WORK/e" "$WORK/r" "$BIN/flist" +inbox
expect_ok "f-flist" "$WORK/o" "$WORK/e" "$WORK/r" 'inbox+'

run_capture "$WORK/o" "$WORK/e" "$WORK/r" "$BIN/packf" +inbox -file "$WORK/mbox.out"
if [ "$(cat "$WORK/r")" -ne 0 ]; then
    note_fail "f-packf" "rc=$(cat "$WORK/r") $(head -c 140 "$WORK/e")"
elif grep -q 'hello nmh test' "$WORK/mbox.out"; then
    note_pass "f-packf"
else
    note_fail "f-packf" "mbox lacks message"
fi

run_capture "$WORK/o" "$WORK/e" "$WORK/r" "$BIN/rmm" +inbox 1
if [ "$(cat "$WORK/r")" -ne 0 ]; then
    note_fail "f-rmm" "rc=$(cat "$WORK/r") $(head -c 140 "$WORK/e")"
else
    run_capture "$WORK/o" "$WORK/e" "$WORK/r" "$BIN/folder" +inbox
    if grep -qe 'has no messages' -e 'has 0 messages' "$WORK/o"; then
        note_pass "f-rmm"
    else
        note_fail "f-rmm-verify" "folder=$(head -c 100 "$WORK/o")"
    fi
fi

# --- negative paths ---------------------------------------------------

export MH="$PROFILE_DIR/does-not-exist"
run_capture "$WORK/o" "$WORK/e" "$WORK/r" "$BIN/mhparam" version
if [ "$(cat "$WORK/r")" -ne 0 ] && grep -q 'unable to read the.*profile specified by your MH' "$WORK/e"; then
    note_pass "n-missing-mh-profile"
else
    note_fail "n-missing-mh-profile" "rc=$(cat "$WORK/r") out=$(head -c 120 "$WORK/o") err=$(head -c 120 "$WORK/e")"
fi

mkdir -p "$WORK/home-no-profile"
export MH=
export HOME="$WORK/home-no-profile"
run_capture "$WORK/o" "$WORK/e" "$WORK/r" "$BIN/mhparam" version
if [ "$(cat "$WORK/r")" -ne 0 ] && grep -q "Doesn't look like nmh is installed" "$WORK/e"; then
    note_pass "n-no-mh-home-profile"
else
    note_fail "n-no-mh-home-profile" "rc=$(cat "$WORK/r") out=$(head -c 120 "$WORK/o") err=$(head -c 120 "$WORK/e")"
fi

export MH="$PROFILE"
export HOME="$HOME_DIR"
export MHMTSCONF="$WORK/nonexistent-mts.conf"
run_capture "$WORK/o" "$WORK/e" "$WORK/r" "$BIN/scan" +inbox
if [ "$(cat "$WORK/r")" -ne 0 ] && grep -q 'error opening mts.conf' "$WORK/e"; then
    note_pass "n-missing-mtsconf"
else
    note_fail "n-missing-mtsconf" "rc=$(cat "$WORK/r") err=$(head -c 120 "$WORK/e")"
fi

export MHMTSCONF="$MHMTSCONF_DEFAULT"
run_capture "$WORK/o" "$WORK/e" "$WORK/r" "$BIN/pick" -subject x -list +folder-that-does-not-exist
if [ "$(cat "$WORK/r")" -ne 0 ]; then
    note_pass "n-unknown-folder"
else
    note_fail "n-unknown-folder" "unexpected rc=0"
fi

mkdir -p "$PROFILE_DIR/badprof"
export MH="$PROFILE_DIR/badprof"
run_capture "$WORK/o" "$WORK/e" "$WORK/r" "$BIN/mhparam" version
if [ "$(cat "$WORK/r")" -ne 0 ] && grep -q 'not a normal file' "$WORK/e"; then
    note_pass "n-profile-is-directory"
else
    note_fail "n-profile-is-directory" "rc=$(cat "$WORK/r") err=$(head -c 120 "$WORK/e")"
fi

echo "NMH_TEST_SUMMARY total=$((PASS + FAIL)) pass=$PASS fail=$FAIL"
[ "$FAIL" -eq 0 ]
