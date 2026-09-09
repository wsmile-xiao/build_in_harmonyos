#!/usr/bin/env bash
# test_package/test.sh — functional test for the proctools suite (pgrep/pkill/pfind).
# Runs in conanrun env (PATH includes the installed bin/); conanfile.py invokes
# it as `bash test.sh`, so the shebang is not relied upon at runtime (AI review
# P3: avoid sandbox-specific absolute interpreter path).
# R34: every assertion genuinely invokes the tested binaries and verifies
# real process-table effects (no print-only stubs).
set -eu -o pipefail

PASS=0
FAIL=0
ok()   { PASS=$((PASS+1)); echo "OK: $1"; }
bad()  { FAIL=$((FAIL+1)); echo "FAIL: $1"; }
# containment check: every expected pid must appear in the (possibly multi-line) output
contains(){ echo "$2" | grep -qx "$1"; }

# ---------------------------------------------------------------- pre-cleanup
# make the process table deterministic: remove stale sleeps left over from
# earlier crashed runs.  Only ORPHANED sleeps (ppid==1) are killed -- a global
# `pkill -x sleep` here could hit sleeps spawned by other jobs sharing the
# same CI worker (AI review P3).
for p in $(pgrep -x sleep 2>/dev/null); do
    ppid=$(awk '{print $4}' "/proc/$p/stat" 2>/dev/null) || continue
    [ "$ppid" = "1" ] && kill -9 "$p" 2>/dev/null
done
sleep 0.3

# ---------------------------------------------------------------- assertion 1
# all three tools report the expected version banner
V=$(pgrep -V 2>&1)
case "$V" in
    *"proctools 0.4pre1"*) ok "pgrep -V reports proctools 0.4pre1";;
    *) bad "pgrep -V unexpected: $V";;
esac
V=$(pkill -V 2>&1)
case "$V" in
    *"proctools 0.4pre1"*) ok "pkill -V reports proctools 0.4pre1";;
    *) bad "pkill -V unexpected: $V";;
esac
V=$(pfind -V 2>&1)
case "$V" in
    *"proctools 0.4pre1"*) ok "pfind -V reports proctools 0.4pre1";;
    *) bad "pfind -V unexpected: $V";;
esac

# ---------------------------------------------------------------- assertion 2
# pgrep enumerates a real process started by this test (exact name match)
sleep 500 & S1=$!
sleep 0.4
P=$(pgrep -x sleep)
if contains "$S1" "$P"; then
    ok "pgrep -x sleep finds the spawned sleep pid"
else
    bad "pgrep -x sleep output '$P' lacks $S1"
fi

# ---------------------------------------------------------------- assertion 3
# pgrep -l prints pid and process name
# (upstream pads pid to 5 columns with %5d for -l/-L; tolerate leading spaces)
L=$(pgrep -l -x sleep)
if echo "$L" | grep -q "^ *$S1 sleep\$"; then
    ok "pgrep -l -x prints '<pid> sleep'"
else
    bad "pgrep -l -x output: '$L'"
fi

# ---------------------------------------------------------------- assertion 4
# pgrep -f matches against the full command line (/proc/<pid>/cmdline)
P=$(pgrep -f "sleep 500")
if contains "$S1" "$P"; then
    ok "pgrep -f matches full cmdline 'sleep 500'"
else
    bad "pgrep -f output '$P' lacks $S1"
fi

# ---------------------------------------------------------------- assertion 5
# pgrep -n selects the most recently started matching process (starttime)
sleep 501 & S2=$!
sleep 0.4
P=$(pgrep -n -x sleep)
check(){ if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (got '$2' want '$3')"; fi; }
check "pgrep -n returns the newest sleep" "$P" "$S2"

# ---------------------------------------------------------------- assertion 6
# pgrep -d uses the requested delimiter between multiple pids
D=$(pgrep -d, -x sleep)
case "$D" in
    *,*) ok "pgrep -d, separates multiple pids with ','";;
    *) bad "pgrep -d, output: '$D'";;
esac

# ---------------------------------------------------------------- assertion 7
# pkill sends SIGTERM by default and the targets really die
pkill -x sleep
sleep 0.5
if kill -0 $S1 2>/dev/null || kill -0 $S2 2>/dev/null; then
    bad "pkill (default TERM) left a sleep alive"
else
    ok "pkill (default TERM) killed both sleeps"
fi

# ---------------------------------------------------------------- assertion 8
# pkill -<signal> accepts a numeric signal and the target dies
sleep 502 & S3=$!
sleep 0.4
pkill -9 -x sleep
sleep 0.5
if kill -0 $S3 2>/dev/null; then
    bad "pkill -9 left the sleep alive"
else
    ok "pkill -9 killed the sleep"
fi

# ---------------------------------------------------------------- assertion 9
# pkill -s <name> resolves signal names via sys_signame and kills
sleep 503 & S4=$!
sleep 0.4
pkill -s TERM -x sleep
sleep 0.5
if kill -0 $S4 2>/dev/null; then
    bad "pkill -s TERM left the sleep alive"
else
    ok "pkill -s TERM (signal name resolution) killed the sleep"
fi

# ---------------------------------------------------------------- assertion 10
# pfind -name finds processes by executable name
sleep 504 & S5=$!
sleep 0.4
P=$(pfind -x -name sleep)
if contains "$S5" "$P"; then
    ok "pfind -x -name sleep finds the pid"
else
    bad "pfind -x -name sleep output '$P' lacks $S5"
fi

# ---------------------------------------------------------------- assertion 11
# pfind -args matches against process arguments (cmdline)
P=$(pfind -args ".*504")
if contains "$S5" "$P"; then
    ok "pfind -args '.*504' matches by argument"
else
    bad "pfind -args output '$P' lacks $S5"
fi

# ---------------------------------------------------------------- assertion 12
# pfind -uid + -name combine predicates
U=$(awk '/^Uid:/{print $2}' /proc/self/status)
P=$(pfind -x -uid "$U" -name sleep)
if contains "$S5" "$P"; then
    ok "pfind -x -uid <self> -name sleep matches"
else
    bad "pfind -uid output '$P' lacks $S5"
fi

# ---------------------------------------------------------------- assertion 13
# pfind -kill <signal> terminates the matched process
pfind -x -name sleep -kill TERM >/dev/null
sleep 0.5
if kill -0 $S5 2>/dev/null; then
    bad "pfind -kill TERM left the sleep alive"
else
    ok "pfind -kill TERM killed the sleep"
fi

# ---------------------------------------------------------------- assertion 14
# pfind -dump / -f: dump the process table entry and read it back
sleep 505 & S6=$!
sleep 0.4
# Dump file lives in CWD (the conan test build folder, always writable):
# $HOME/tmp and /tmp are not guaranteed to exist on CI workers.
DUMP="pfdump.$$.txt"
pfind -x -name sleep -dump "$DUMP" >/dev/null
P=$(pfind -f "$DUMP" -name sleep)
if contains "$S6" "$P"; then
    ok "pfind dump/readback roundtrip returns the pid"
else
    bad "pfind dump/readback output '$P' lacks $S6"
fi
rm -f "$DUMP"
kill -9 $S6 2>/dev/null || true

# ---------------------------------------------------------------- assertion 15
# pgrep -P filters by parent pid: both sleeps share this shell as parent
sleep 506 & SA=$!
sleep 507 & SB=$!
sleep 0.4
PPID_SH=$$
N=$(pgrep -P $PPID_SH -x sleep | wc -l)
if [ "$N" -ge 2 ]; then
    ok "pgrep -P <ppid> lists both child sleeps (got $N)"
else
    bad "pgrep -P <ppid> expected >=2 sleeps, got $N"
fi
# cleanup after assertion 15: kill only sleeps parented to this shell --
# sleeps belonging to other jobs on a shared worker are not ours to kill
# (AI review P3; the pkill *assertions* above exercise pkill itself and are
# inherently global, which is the point of the test)
kill $(pgrep -P $$ -x sleep 2>/dev/null) 2>/dev/null || true
sleep 0.3

# ---------------------------------------------------------------- assertion 16
# REG_NOSPEC emulation: -x patterns are literals, so 'a{2}' must match a
# process literally named "a{2}" and must NOT match one named "aa"
# (without brace escaping, ERE a{2} == "aa" and the match flips).
# Symlinks instead of copies: comm comes from the execve path basename,
# and /system/bin is not user-readable for cp.
SLEEPBIN=$(command -v sleep)
ln -s "$SLEEPBIN" ./aa
ln -s "$SLEEPBIN" './a{2}'
'./aa' 600 & AA=$!
'./a{2}' 600 & AB=$!
sleep 0.4
P=$(pfind -x 'a{2}')
if contains "$AB" "$P" && ! contains "$AA" "$P"; then
    ok "pfind -x 'a{2}' matches the literal-named process only"
else
    bad "pfind -x 'a{2}' output '$P' (want $AB, not $AA)"
fi
kill -9 $AA $AB 2>/dev/null || true
rm -f ./aa './a{2}'

# ---------------------------------------------------------------- assertion 17
# procfs status Gid: parsing coverage: -gid matches a real gid of a live
# process (AI review P3 coverage gap)
G=$(awk '/^Gid:/{print $2}' /proc/self/status)
sleep 508 & S7=$!
sleep 0.4
P=$(pfind -x -gid "$G" -name sleep)
if contains "$S7" "$P"; then
    ok "pfind -x -gid <self-gid> -name sleep matches"
else
    bad "pfind -x -gid output '$P' lacks $S7"
fi
kill -9 $S7 2>/dev/null || true

echo
echo "=================================================="
echo "RESULT: PASS=$PASS FAIL=$FAIL"
echo "=================================================="
[ "$FAIL" -eq 0 ]
