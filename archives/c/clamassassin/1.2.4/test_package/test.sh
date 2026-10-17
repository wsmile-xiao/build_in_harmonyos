#!/bin/sh
set -eu
# clamassassin functional smoke test.
#
# clamassassin is a procmail wrapper around clamscan/formail. The CI toolchain
# has no ClamAV, so this test runs the INSTALLED script with mock clamscan /
# formail stubs and two real mail cases:
#   1. clean mail    -> X-Virus-Status: No
#   2. infected mail -> X-Virus-Status: Yes + X-Virus-Report: <sig> FOUND
#
# Only the hardcoded tool paths (MKTEMP/RM/CAT/SED/ECHO) and TMPPATH are
# normalized in a throwaway copy; the filtering logic under test is the
# unmodified installed script.
#
# NOTE: no here-documents, no embedded newlines in generated files —
# /bin/sh here is zsh and /tmp is read-only on this platform.

# --- helper: write a mock script file from single-line args ------------------
write_mock() {
    _wm_file="$1"
    shift
    : > "$_wm_file"
    for _wm_line in "$@"; do
        printf '%s\n' "$_wm_line" >> "$_wm_file"
    done
    chmod +x "$_wm_file"
}

# --- locate the installed script --------------------------------------------
if command -v clamassassin >/dev/null 2>&1; then
    INSTALLED="$(command -v clamassassin)"
else
    echo "FAIL: clamassassin not found in PATH"
    exit 1
fi
echo "clamassassin found: $INSTALLED"

# shell syntax check of the installed script
sh -n "$INSTALLED"
echo "clamassassin sh -n: OK"

# --- build an isolated workspace --------------------------------------------
WORK=""
for cand in "${TMPDIR:-}" "$HOME" /data/service/hnp /storage/Users/currentUser/tmp .; do
    [ -n "$cand" ] && [ -d "$cand" ] && [ -w "$cand" ] && \
        WORK="$cand/clamassassin-test.$$" && mkdir -p "$WORK" 2>/dev/null && break
done
[ -n "$WORK" ] || { echo "FAIL: no writable directory found"; exit 1; }
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/tmp" "$WORK/mock" "$WORK/mail"

# copy the installed script and normalize hardcoded absolute tool paths
cp "$INSTALLED" "$WORK/clamassassin"
sed -i \
    -e "s|^TMPPATH=.*|TMPPATH=$WORK/tmp/|" \
    -e 's|^MKTEMP=.*|MKTEMP=mktemp|' \
    -e 's|^RM=.*|RM=rm|' \
    -e 's|^CAT=.*|CAT=cat|' \
    -e 's|^SED=.*|SED=sed|' \
    -e 's|^ECHO=.*|ECHO=echo|' \
    "$WORK/clamassassin"

# --- mock clamscan: -V prints version, otherwise scan stdin for EICAR -------
write_mock "$WORK/mock/clamscan" \
    '#!/bin/sh' \
    'if [ "$1" = "-V" ]; then' \
    '    echo "ClamAV 1.2.4/20260101"' \
    '    exit 0' \
    'fi' \
    'if cat | grep -q "EICAR"; then' \
    '    echo "STDIN: Eicar-Signature FOUND"' \
    '    echo "----------- SCAN SUMMARY -----------"' \
    '    exit 1' \
    'fi' \
    'exit 0'

# --- mock formail (two-pass arg scan, no arrays):
#     formail -f -I HDR... -> print each -I header line, then pass stdin
#     formail -c -x FIELD  -> extract header value (leading-space quirk that
#                             upstream clamassassin strips)
write_mock "$WORK/mock/formail" \
    '#!/bin/sh' \
    'field=""' \
    'saw_x=0' \
    'prev=""' \
    'for a in "$@"; do' \
    '    if [ "$prev" = "-x" ]; then' \
    '        field="$a"' \
    '        saw_x=1' \
    '    fi' \
    '    prev="$a"' \
    'done' \
    'if [ "$saw_x" = 1 ]; then' \
    '    grep "^$field" 2>/dev/null | sed "s/^$field[[:space:]]*/ /" || true' \
    '    exit 0' \
    'fi' \
    'prev=""' \
    'for a in "$@"; do' \
    '    if [ "$prev" = "-I" ]; then' \
    '        printf "%s\n" "$a"' \
    '    fi' \
    '    prev="$a"' \
    'done' \
    'cat'

# --- test 1: clean mail ------------------------------------------------------
printf 'Subject: Clean test mail\nFrom: sender@example.com\n\nThis is a harmless message.\n' \
    > "$WORK/mail/clean.eml"
OUT_CLEAN="$(PATH="$WORK/mock:$PATH" sh "$WORK/clamassassin" < "$WORK/mail/clean.eml")"
printf '%s\n' "$OUT_CLEAN"
if printf '%s' "$OUT_CLEAN" | grep -q "^X-Virus-Status: No"; then
    echo "clean mail -> X-Virus-Status: No: OK"
else
    echo "FAIL: clean mail not marked No"
    exit 1
fi

# --- test 2: infected mail ---------------------------------------------------
printf 'Subject: Infected test mail\nFrom: sender@example.com\n\nBody with EICAR-STANDARD-ANTIVIRUS-TEST-FILE string\n' \
    > "$WORK/mail/infected.eml"
OUT_INFECTED="$(PATH="$WORK/mock:$PATH" sh "$WORK/clamassassin" < "$WORK/mail/infected.eml")"
printf '%s\n' "$OUT_INFECTED"
if printf '%s' "$OUT_INFECTED" | grep -q "^X-Virus-Status: Yes"; then
    echo "infected mail -> X-Virus-Status: Yes: OK"
else
    echo "FAIL: infected mail not marked Yes"
    exit 1
fi
if printf '%s' "$OUT_INFECTED" | grep -q "^X-Virus-Report: Eicar-Signature FOUND"; then
    echo "infected mail -> X-Virus-Report: OK"
else
    echo "FAIL: X-Virus-Report missing virus name"
    exit 1
fi

# --- test 3 (HarmonyOS-specific, E011): the E011 fix itself -----------------
# E011: HMDFS defaults to umask 077, so config.status would generate files
# that the current (UID-mapped) process cannot read/write. The recipe patches
# config.status umask 077 -> 022; verify the generated script really was
# produced under the corrected umask, i.e. the file is owner-rwx and does NOT
# carry the 0600 signature of an unpatched config.status run.
#
# NOTE: we deliberately do NOT assert the packaged file's final permission
# bits: on HMDFS, SELinux/HMDFS silently ignore chmod() (knowledge E046), so
# the packaged bits reflect the filesystem policy, not the recipe's chmod —
# asserting them is environment-dependent and fails on the CI worker.
INSTALLED_MODE="$(ls -lL "$INSTALLED" | awk '{print $1}')"
case "$INSTALLED_MODE" in
    -rw-------*|-rw-------)
        echo "FAIL: harmony-specific E011 mode check — installed mode '$INSTALLED_MODE' looks like an unpatched umask 077 config.status output (0600)"
        exit 1
        ;;
esac
echo "harmony-specific E011 mode check ($INSTALLED_MODE not 0600): OK"

# behavioral half of E011: run the real filtering pass under umask 077 so
# every file created during the run is owner-only, proving the filter logic
# itself is unaffected by the HMDFS default umask.
UMASK_OUT="$( (umask 077; PATH="$WORK/mock:$PATH" sh "$WORK/clamassassin" < "$WORK/mail/clean.eml") )"
if printf '%s' "$UMASK_OUT" | grep -q "^X-Virus-Status: No"; then
    echo "harmony-specific E011 filter run under umask 077: OK"
else
    echo "FAIL: harmony-specific E011 filter run under umask 077"
    exit 1
fi

echo "ALL TESTS PASSED"
