#!/bin/sh
# test_package consumer smoke test for nagios 4.5.14 (OHOS aarch64).
#
# Exercises the installed package end-to-end:
#   1. nagios --version          — binary loads, reports the right version
#   2. nagios -v <empty cfg>     — validator must FAIL (error reporting path)
#   3. nagios -v <minimal cfg>   — validator must PASS: real config parsing,
#                                  object registration, pre-flight check —
#                                  the core startup path of the daemon
#   4. nagiostats --version      — statistics utility works
#
# Usage: test_nagios.sh <package_folder> <workdir>
set -eu

PKG="$1"
WORKDIR="$2"

NAGIOS="$PKG/bin/nagios"
NAGIOSTATS="$PKG/bin/nagiostats"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

# --- 1. version ---------------------------------------------------------
out=$("$NAGIOS" --version 2>&1) || fail "nagios --version returned non-zero"
echo "$out" | grep -q "Nagios Core 4.5.14" || fail "version string mismatch: $out"
echo "ok 1 - nagios --version reports 4.5.14"

# --- 2/3. configuration validation -------------------------------------
CFG_DIR="$WORKDIR/etc"
VAR_DIR="$WORKDIR/var"
mkdir -p "$CFG_DIR/objects" "$VAR_DIR/spool/checkresults" "$VAR_DIR/rw" "$WORKDIR/tmp"

cat > "$CFG_DIR/nagios.cfg" <<EOF
log_file=$VAR_DIR/nagios.log
temp_path=$WORKDIR/tmp
check_result_path=$VAR_DIR/spool/checkresults
status_file=$VAR_DIR/status.dat
command_file=$VAR_DIR/rw/nagios.cmd
cfg_dir=$CFG_DIR/objects
use_syslog=0
EOF

# 2. empty objects dir → validation must fail with config errors
if "$NAGIOS" -v "$CFG_DIR/nagios.cfg" > "$WORKDIR/v-empty.log" 2>&1; then
    fail "empty config should fail validation but returned 0"
fi
echo "--- nagios -v (empty config) output ---"
sed -n '1,20p' "$WORKDIR/v-empty.log"
echo "----------------------------------------"
# any "Error:" diagnostic line proves the validator parsed the config and
# reported problems (the specific error depends on which object check
# fires first, which varies with locale/directory iteration order)
grep -q "^Error" "$WORKDIR/v-empty.log" \
    || fail "expected 'Error:' diagnostics in validation output"
echo "ok 2 - nagios -v reports errors for empty config"

# 3. minimal but complete object set → validation must pass
cat > "$CFG_DIR/objects/hosts.cfg" <<'EOF'
define timeperiod {
    timeperiod_name     24x7
    alias               24 Hours A Day, 7 Days A Week
    sunday              00:00-24:00
    monday              00:00-24:00
    tuesday             00:00-24:00
    wednesday           00:00-24:00
    thursday            00:00-24:00
    friday              00:00-24:00
    saturday            00:00-24:00
}
define command {
    command_name        check_dummy
    command_line        /bin/true
}
define command {
    command_name        notify-service
    command_line        /bin/true
}
define command {
    command_name        notify-host
    command_line        /bin/true
}
define contact {
    contact_name        testcontact
    alias               Test Contact
    service_notification_period   24x7
    host_notification_period      24x7
    service_notification_commands notify-service
    host_notification_commands    notify-host
}
define host {
    host_name           testhost
    alias               Test Host
    address             127.0.0.1
    max_check_attempts  1
    check_period        24x7
    notification_period 24x7
    contacts            testcontact
}
define service {
    host_name           testhost
    service_description Test Service
    check_command       check_dummy
    max_check_attempts  1
    check_interval      5
    retry_interval      1
    check_period        24x7
    notification_interval 60
    notification_period 24x7
    contacts            testcontact
}
EOF

out=$("$NAGIOS" -v "$CFG_DIR/nagios.cfg" 2>&1) \
    || fail "full config validation failed: $out"
echo "$out" | grep -q "Things look okay" \
    || fail "expected 'Things look okay' in validation output: $out"
echo "ok 3 - nagios -v passes for minimal complete config"

# --- 4. nagiostats --------------------------------------------------------
out=$("$NAGIOSTATS" --version 2>&1) || fail "nagiostats --version returned non-zero"
echo "$out" | grep -q "Nagios Stats 4.5.14" || fail "nagiostats version mismatch: $out"
echo "ok 4 - nagiostats --version reports 4.5.14"

echo "1..4"
echo "All 4 consumer tests passed."
