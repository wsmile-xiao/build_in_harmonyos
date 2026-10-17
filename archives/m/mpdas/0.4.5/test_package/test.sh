#!/bin/sh
# test_package consumer test for mpdas 0.4.5 (HarmonyOS PC).
# Every assertion executes the installed mpdas binary through /usr/bin/timeout
# (rc=124 is a FAIL) and checks observable stdout/stderr plus the exit code.
# The strings grepped here come from the upstream sources:
#   main.cpp printversion() -> "mpdas-" VERSION / "Global config path is set to"
#   main.cpp printhelp()    -> "usage: mpdas [-h] [-v] [-c config]"
#   main.cpp main()         -> "AudioScrobbler username or password not set."
#   main.cpp + mpd.cpp      -> "Could not connect to MPD."
set -u
export PATH="$PATH:/system/bin"

TOUT=/usr/bin/timeout
if [ ! -x "$TOUT" ]; then
    TOUT="$(command -v timeout)"
fi
[ -n "$TOUT" ] || { echo "FAIL 0: no timeout(1) available"; exit 1; }

pass=0

# 1. -v exits 0 and prints the compiled-in version (VERSION macro)
out=$("$TOUT" 30 mpdas -v 2>&1); rc=$?
[ "$rc" = "0" ] || { echo "FAIL 1: mpdas -v exit=$rc out=[$out]"; exit 1; }
echo "$out" | grep -qF "mpdas-0.4.5" || { echo "FAIL 1: version string missing in [$out]"; exit 1; }
pass=$((pass+1)); echo "PASS 1: mpdas -v -> [$out]"

# 2. -h exits 0 and prints the usage line
out=$("$TOUT" 30 mpdas -h 2>&1); rc=$?
[ "$rc" = "0" ] || { echo "FAIL 2: mpdas -h exit=$rc out=[$out]"; exit 1; }
echo "$out" | grep -qF "usage: mpdas [-h] [-v] [-c config]" || { echo "FAIL 2: usage line missing in [$out]"; exit 1; }
pass=$((pass+1)); echo "PASS 2: mpdas -h prints usage"

# 3. CONFDIR macro is compiled in (global config path reported)
out=$("$TOUT" 30 mpdas -v 2>&1); rc=$?
[ "$rc" = "0" ] || { echo "FAIL 3: mpdas -v exit=$rc out=[$out]"; exit 1; }
echo "$out" | grep -qF "Global config path is set to" || { echo "FAIL 3: CONFDIR missing in [$out]"; exit 1; }
pass=$((pass+1)); echo "PASS 3: CONFDIR compiled in -> [$out]"

# 4. -c with a config without credentials: parsed, then rejected with rc=1
printf '[Last.fm]\n' > nopasswd.cfg
out=$("$TOUT" 30 mpdas -c nopasswd.cfg 2>&1); rc=$?
[ "$rc" = "1" ] || { echo "FAIL 4: expected exit 1, got $rc out=[$out]"; exit 1; }
echo "$out" | grep -qF "AudioScrobbler username or password not set." || { echo "FAIL 4: rejection message missing in [$out]"; exit 1; }
pass=$((pass+1)); echo "PASS 4: credential check -> [$out]"

# 5. -c with credentials: the binary reaches the MPD protocol layer, which
#    proves libmpdclient is really loaded and its symbols resolved. No MPD
#    server runs on the build host, so the expected outcome is a clean
#    connection failure with rc=1 (scrobbler/HTTP path stays unexecuted).
printf '[Last.fm]\nusername=testuser\npassword=testpass\nhost=localhost\nport=6600\n' > scrobble.cfg
out=$("$TOUT" 30 mpdas -c scrobble.cfg 2>&1); rc=$?
[ "$rc" = "124" ] && { echo "FAIL 5: mpdas hung past the 30s timeout"; exit 1; }
[ "$rc" = "1" ] || { echo "FAIL 5: expected exit 1, got $rc out=[$out]"; exit 1; }
echo "$out" | grep -qF "Could not connect to MPD." || { echo "FAIL 5: MPD layer not reached in [$out]"; exit 1; }
pass=$((pass+1)); echo "PASS 5: libmpdclient runtime path -> [$out]"

echo "test mpdas 0.4.5: $pass/5 checks PASS"
[ "$pass" = "5" ] || exit 1
exit 0
