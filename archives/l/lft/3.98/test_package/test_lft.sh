#!/bin/sh
# lft-3.98 packaged-tool behavioural smoke test (OHOS: /bin/sh is toybox ash).
#
# lft is a raw-socket traceroute; the device is unprivileged and headless, so
# "actually trace a route" is NOT a reachable pass condition.  Assertions are
# therefore placed on the code paths that really execute before that stage, and
# everything unreachable is declared SKIP with its reason, never as a pass:
#
#   LOAD/BEHAVIOUR (asserted):
#     1  lft --version  -> upstream banner "Layer Four Traceroute (LFT) -
#        version 3.98" on stderr (lft.c show_version(): one big fprintf).
#        Reaching it proves the loader accepted the ELF *and* that libpcap is
#        linked in: show_version() also prints the pcap/c-ares/ncurses option
#        block, and -DVERSION substitution is what produced "3.98".
#     2  lft --version  -> exit 0 (upstream exit after the banner)
#     3  lft (no args)  -> exit 1 + usage text   (measured on the build host)
#     4  lft (no args)  -> usage output non-empty
#     5  lft --nonsuch  -> exit 1 (default: usage branch)
#     6  lft 127.0.0.1  -> exit 1 with the privilege diagnostic: main() parses
#        options, then lft_check_permissions() (lft.c ~634) fails as non-root;
#        the failure is therefore "needs privileges", NOT a loader rejection.
#     7  whob -v        -> exit 1 and its usage banner carries "3.98"
#     8  negative control: with the Conan run-lib path stripped the binary must
#        NOT become 127/126 (libpcap is static here, closure is self-contained)
#
#   CAPABILITY (declared skipped, with reasons):
#     9  real traceroute round (raw socket / CAP_NET_RAW unavailable to this uid)
#     10 interactive ncurses mode (build-time --disable-ncurses)
#     11 asynchronous DNS via c-ares (build-time --disable-async-dns)

set -u

BIN_DIR="$1"
WORK_DIR="$2"
LFT="$BIN_DIR/lft"
WHOB="$BIN_DIR/whob"
PASS=0
SKIP=0
FAIL=0

say() { printf '%s\n' "$*"; }
ok() { PASS=$((PASS + 1)); say "LFT_TEST_PASS case=$1"; }
bad() { FAIL=$((FAIL + 1)); say "LFT_TEST_FAIL case=$1 reason=$2"; say "LFT_SMOKE_FAILED"; exit 1; }
sk() { SKIP=$((SKIP + 1)); say "LFT_TEST_SKIP case=$1 reason=$2"; }

[ -x "$LFT" ] || bad missing-binary "no executable $LFT"
[ -x "$WHOB" ] || bad missing-binary "no executable $WHOB"
mkdir -p "$WORK_DIR" 2>/dev/null

# --- 1/2: version banner (also proves libpcap linkage) ----------------------
"$LFT" --version > "$WORK_DIR/v.out" 2>"$WORK_DIR/v.err"
rc=$?
cat "$WORK_DIR/v.out" "$WORK_DIR/v.err" > "$WORK_DIR/v.all" 2>/dev/null
if grep -q "Layer Four Traceroute (LFT) - version 3.98" "$WORK_DIR/v.all"; then
    ok version-banner
else
    bad version-banner "banner not found; first lines: $(sed -n 1,2p "$WORK_DIR/v.all" | tr "\n" "|")"
fi
if [ "$rc" -eq 0 ]; then ok version-exit-zero; else bad version-exit-zero "exit=$rc expected=0"; fi

# --- 3/4: no-argument usage path -------------------------------------------
"$LFT" > "$WORK_DIR/n.out" 2>"$WORK_DIR/n.err"
rc=$?
if [ "$rc" -eq 1 ]; then ok no-args-exit-1; else bad no-args-exit-1 "exit=$rc expected=1"; fi
if [ -s "$WORK_DIR/n.out" ] || [ -s "$WORK_DIR/n.err" ]; then
    ok no-args-usage-nonempty
else
    bad no-args-usage-nonempty "both streams empty"
fi

# --- 5: unknown option ------------------------------------------------------
"$LFT" --certainly-not-an-option > "$WORK_DIR/b.out" 2>"$WORK_DIR/b.err"
rc=$?
if [ "$rc" -eq 1 ]; then ok bad-option-exit-1; else bad bad-option-exit-1 "exit=$rc expected=1"; fi

# --- 6: privilege gate (real behaviour, not an environment excuse) ---------
"$LFT" 127.0.0.1 > "$WORK_DIR/p.out" 2>"$WORK_DIR/p.err"
rc=$?
cat "$WORK_DIR/p.out" "$WORK_DIR/p.err" > "$WORK_DIR/p.all" 2>/dev/null
if [ "$rc" -eq 126 ] || [ "$rc" -eq 127 ]; then
    bad privilege-gate "exit=$rc means the loader refused, not the permission gate"
fi
if grep -qi "privilege" "$WORK_DIR/p.all"; then
    ok privilege-gate
else
    bad privilege-gate "no privilege diagnostic; exit=$rc first line: $(sed -n 1p "$WORK_DIR/p.all")"
fi

# --- 7: whob usage carries the version -------------------------------------
"$WHOB" -v > "$WORK_DIR/w.out" 2>"$WORK_DIR/w.err"
rc=$?
cat "$WORK_DIR/w.out" "$WORK_DIR/w.err" > "$WORK_DIR/w.all" 2>/dev/null
if grep -q "3.98" "$WORK_DIR/w.all" && [ "$rc" -eq 1 ]; then
    ok whob-version-in-usage
else
    bad whob-version-in-usage "exit=$rc first line: $(sed -n 1p "$WORK_DIR/w.all")"
fi

# --- 8: negative control (self-contained closure) ---------------------------
env -i "$LFT" --version > "$WORK_DIR/s.out" 2>"$WORK_DIR/s.err"
rc=$?
if [ "$rc" -eq 126 ] || [ "$rc" -eq 127 ]; then
    bad stripped-env-control "exit=$rc: binary is not self-contained after all"
else
    ok stripped-env-control
fi

# --- 9..11: capability-dependent, honestly skipped -------------------------
sk raw-socket-traceroute "unprivileged uid; no CAP_NET_RAW / raw socket on this device"
sk interactive-ncurses-mode "built with --disable-ncurses (no display/terminal UI on build host)"
sk async-dns-cares-path "built with --disable-async-dns (c-ares not linked)"

say "LFT_SMOKE_PASS behavioural=$PASS skipped=$SKIP failed=$FAIL"
say "behavioural=$PASS skipped=$SKIP failed=$FAIL" > "$WORK_DIR/summary.txt"
exit 0
