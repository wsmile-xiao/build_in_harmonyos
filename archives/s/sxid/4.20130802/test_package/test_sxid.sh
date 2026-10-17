#!/bin/sh
#--------------------------------------------------------------------
# Consumer test for sxid 4.20130802 (installed bin/sxid).
#
# Really runs the installed sxid against a controlled tree and checks its
# auditing contract: version/usage, first-run additions, the SHA-256 recorded
# in the log, the SHA-256/inode change detection on a second run, log rotation
# and mode 600, listall and spotcheck.
#
# The S_ISUID / S_ISGID capability of the host filesystem is probed first and
# sxid's result is then required to match the platform, so the test is
# deterministic on any filesystem.  On OHOS/HMDFS the probe shows regular files
# cannot keep S_ISUID while directories keep S_ISGID, so the "dropped" branches
# are exercised there; on a POSIX filesystem the "kept" branches run instead.
#
# Env: SXID_BIN = path to the installed sxid executable
# Exit: 0 = all checks passed, 1 = failure
#--------------------------------------------------------------------
set -eu

BIN="${SXID_BIN:-sxid}"
BASE="${HOME:-${TMPDIR:-.}}"
WORK="$BASE/sxid-consumer.$$"
rm -rf "$WORK"
mkdir -p "$WORK/scan/sgid_dir"
trap 'rm -rf "$WORK"' EXIT

# SHA-256 of the two file contents used below (independent constants, so the
# test does not depend on a sha256sum utility being installed).
SHA_HELLO="5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03"
SHA_HELLO_WORLD="a948904f2f0f479b8f8197694b30184b0d2ed1c1cd2a1ec0fb85d299a192a447"

checks=0
fails=0
check() { # check <name> <actual> <expected>
	checks=$((checks + 1))
	if [ "$2" = "$3" ]; then
		echo "PASS: $1"
	else
		echo "FAIL: $1 (got '$2', want '$3')"
		fails=$((fails + 1))
	fi
}
mode_of() { stat -c '%a' "$1" 2>/dev/null || echo 0; }
# has_special <mode> <bitmask>: mode like "4755" or "750"; bitmask 4=setuid, 2=setgid
has_special() {
	m="$1"
	while [ "${#m}" -lt 4 ]; do m="0$m"; done
	d=${m%???}
	[ $((d & $2)) -ne 0 ]
}

# 1. version
got=$("$BIN" -V | head -1)
check "sxid -V reports 4.20130802" "$got" "sXid 4.20130802"

# 2. usage documents the spotcheck option
got=$("$BIN" -h | grep -c -- '--spotcheck' || true)
check "sxid -h documents --spotcheck" "$got" "1"

# --- prepare a controlled tree ---
printf 'hello\n' > "$WORK/scan/tracked.txt"
printf '%s\n' "$WORK/scan/tracked.txt" > "$WORK/extra.lst"

# platform capability probes
: > "$WORK/scan/probe.bin"
chmod 4755 "$WORK/scan/probe.bin"
probe_mode=$(mode_of "$WORK/scan/probe.bin")
if has_special "$probe_mode" 4; then fs_suid=1; else fs_suid=0; fi
mkdir -p "$WORK/scan/sgid_dir"
chmod 2755 "$WORK/scan/sgid_dir"
dir_mode=$(mode_of "$WORK/scan/sgid_dir")
if has_special "$dir_mode" 2; then fs_sgid=1; else fs_sgid=0; fi
echo "platform: suid_file_mode=$probe_mode keeps_suid=$fs_suid sgid_dir_mode=$dir_mode keeps_sgid=$fs_sgid"

cat > "$WORK/sxid.conf" <<EOF
SEARCH "$WORK/scan"
EXCLUDE ""
IGNORE_DIRS ""
EMAIL "root"
LOG_FILE "$WORK/sxid.log"
MAIL_PROG "/usr/bin/mail"
EXTRA_LIST "$WORK/extra.lst"
FORBIDDEN ""
KEEP_LOGS "0"
EOF

# 3. first run reports the EXTRA_LIST tracked file as a new addition
out1=$("$BIN" -n -c "$WORK/sxid.conf")
got=$(printf '%s\n' "$out1" | grep -c "^ + $WORK/scan/tracked.txt" || true)
check "first run reports tracked.txt as addition" "$got" "1"

# 4. setuid regular file follows the platform capability
if [ "$fs_suid" = "1" ]; then
	got=$(printf '%s\n' "$out1" | grep -c "$WORK/scan/probe.bin" || true)
	check "setuid file listed when fs keeps S_ISUID" "$got" "1"
else
	got=$(printf '%s\n' "$out1" | grep -c "$WORK/scan/probe.bin" || true)
	check "setuid file omitted when fs drops S_ISUID" "$got" "0"
fi

# 5. setgid directory follows the platform capability
if [ "$fs_sgid" = "1" ]; then
	got=$(printf '%s\n' "$out1" | grep -c "^ + $WORK/scan/sgid_dir/" || true)
	check "setgid dir listed when fs keeps S_ISGID" "$got" "1"
else
	got=$(printf '%s\n' "$out1" | grep -c "$WORK/scan/sgid_dir" || true)
	check "setgid dir omitted when fs drops S_ISGID" "$got" "0"
fi

# 6. the interim log is created mode 600 (umask 077)
got=$(mode_of "$WORK/sxid.log")
check "sxid.log created mode 600" "$got" "600"

# 7. the log records the correct SHA-256 of tracked.txt
got=$(grep -c "$SHA_HELLO" "$WORK/sxid.log" || true)
check "log records tracked.txt SHA-256" "$got" "1"

# 8. second run detects the SHA-256 and inode change ("mi")
printf 'hello world\n' > "$WORK/scan/tracked.txt"
out2=$("$BIN" -n -c "$WORK/sxid.conf")
got=$(printf '%s\n' "$out2" | grep -c "^mi $WORK/scan/tracked.txt" || true)
check "second run reports checksum+inode change (mi)" "$got" "1"

# 9. the rotated log carries the new SHA-256
got=$(grep -c "$SHA_HELLO_WORLD" "$WORK/sxid.log" || true)
check "rotated log records new SHA-256" "$got" "1"

# 10. the old SHA-256 is gone after rotation
got=$(grep -c "$SHA_HELLO" "$WORK/sxid.log" || true)
check "rotated log no longer holds old SHA-256" "$got" "0"

# 11. listall (-l) shows the tracked entry
got=$("$BIN" -n -l -c "$WORK/sxid.conf" | grep -c "$WORK/scan/tracked.txt" || true)
[ "$got" -ge 1 ] && got=1 || got=0
check "listall includes tracked.txt" "$got" "1"

# 12. spotcheck (-k) reports the current working directory as the search root
out4=$(cd "$WORK/scan" && "$BIN" -n -k -c "$WORK/sxid.conf")
got=$(printf '%s\n' "$out4" | grep -c "^Spotcheck" || true)
check "spotcheck reports the cwd" "$got" "1"

echo "SXID_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
