#!/bin/sh
# Consumer-side end-to-end check for the ksystemstats package.
#
# This exercises the packaged deliverables the way a real consumer does:
# it starts the packaged org.kde.ksystemstats daemon against a private
# session bus, then queries it through the packaged kstatsviewer CLI and
# asserts that the sensor plugins really loaded and published sensors with
# live values. Removing the package's bin/ or lib/plugins/ directory makes
# this fail, so it cannot pass against a stub.
#
# Usage: consumer_check.sh <package_folder> <dbus-daemon> <work_dir>
# Exit:  0 = the daemon answered with real sensors, non-zero = failure.

set -eu
set -o pipefail

PKG_DIR="$1"
DBUS_DAEMON="$2"
WORK_DIR="$3"

# Absolute path of this script: step 1 re-executes it from another directory.
SELF="$0"
case "$SELF" in
    /*) ;;
    *) SELF="$(pwd)/$SELF" ;;
esac

BIN_DIR="$PKG_DIR/bin"

export LD_LIBRARY_PATH="$PKG_DIR/lib:${LD_LIBRARY_PATH:-}"
export QT_PLUGIN_PATH="$PKG_DIR/lib/plugins:${QT_PLUGIN_PATH:-}"
export QT_QPA_PLATFORM=offscreen
export HOME="$WORK_DIR/home"
export XDG_RUNTIME_DIR="$WORK_DIR/runtime"
export XDG_CACHE_HOME="$HOME/.cache"
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_DATA_HOME="$HOME/.local/share"
mkdir -p "$HOME" "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"

# The published libKSysGuardSystemStats.so records libKSysGuardFormatter.so as
# "../bin/libKSysGuardFormatter.so", which the loader resolves against the
# process CWD. The caller materializes that bridge in the parent of this
# directory, so anchor the CWD here.
cd "$WORK_DIR"

if [ ! -x "$DBUS_DAEMON" ]; then
    echo "FAIL: dbus-daemon is not executable at '$DBUS_DAEMON'"
    exit 1
fi
if [ ! -x "$BIN_DIR/ksystemstats" ]; then
    echo "FAIL: $BIN_DIR/ksystemstats is missing from the package"
    exit 1
fi
if [ ! -x "$BIN_DIR/kstatsviewer" ]; then
    echo "FAIL: $BIN_DIR/kstatsviewer is missing from the package"
    exit 1
fi

# 1. Private session bus.
#
# TCP + ANONYMOUS: the sandbox denies AF_UNIX binds and the runtime has no
# passwd record for the running UID. dbus-run-session starts the daemon, waits
# until it is usable and exports DBUS_SESSION_BUS_ADDRESS, so this script
# re-executes itself inside it and everything below runs against that bus.
if [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ]; then
    CONF="$WORK_DIR/session-tcp.conf"
    cat > "$CONF" <<'BUSCONF'
<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-BUS Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <type>session</type>
  <keep_umask/>
  <listen>tcp:host=127.0.0.1,port=0,bind=127.0.0.1</listen>
  <auth>ANONYMOUS</auth>
  <allow_anonymous/>
  <policy context="default">
    <allow send_destination="*" eavesdrop="true"/>
    <allow eavesdrop="true"/>
    <allow own="*"/>
  </policy>
</busconfig>
BUSCONF

    DBUS_RUN_SESSION="$(dirname "$DBUS_DAEMON")/dbus-run-session"
    if [ ! -x "$DBUS_RUN_SESSION" ]; then
        echo "FAIL: dbus-run-session is not available next to $DBUS_DAEMON"
        exit 1
    fi
    exec "$DBUS_RUN_SESSION" --dbus-daemon="$DBUS_DAEMON" \
        --config-file="$CONF" -- sh "$SELF" "$@"
fi

echo "session bus: $DBUS_SESSION_BUS_ADDRESS"

# 2. The packaged daemon.
DAEMON_PID=""
cleanup() {
    if [ -n "$DAEMON_PID" ]; then
        kill "$DAEMON_PID" 2> /dev/null || true
    fi
}
trap cleanup EXIT INT TERM

"$BIN_DIR/ksystemstats" --remain > "$WORK_DIR/ksystemstats.log" 2>&1 &
DAEMON_PID=$!

# 3. The packaged CLI, retried until the daemon has published its sensors.
LIST_OUTPUT=""
attempt=0
while [ "$attempt" -lt 60 ]; do
    LIST_OUTPUT=$("$BIN_DIR/kstatsviewer" --list 2>> "$WORK_DIR/kstatsviewer.err" || true)
    if [ -n "$LIST_OUTPUT" ] && [ "$LIST_OUTPUT" != "No sensors available." ]; then
        break
    fi
    attempt=$((attempt + 1))
    sleep 1
done

echo "--- kstatsviewer --list ---"
echo "$LIST_OUTPUT"
echo "---------------------------"

if [ -z "$LIST_OUTPUT" ]; then
    echo "FAIL: kstatsviewer --list produced no output"
    cat "$WORK_DIR/ksystemstats.log" 2> /dev/null || true
    exit 1
fi
if [ "$LIST_OUTPUT" = "No sensors available." ]; then
    echo "FAIL: the packaged daemon published no sensors (plugins did not load)"
    cat "$WORK_DIR/ksystemstats.log" 2> /dev/null || true
    exit 1
fi

# 4. Assert the sensor containers the packaged plugins must provide. These are
# created unconditionally by their plugins (the container ids come from the
# plugin sources: osinfo registers "os", disks registers "disk"), so the check
# does not depend on the hardware present on the machine. A container without
# child objects is listed as "<id> <name>", with them as "<id>/...".
MISSING=""
for container in cpu memory disk network os power pressure gpu; do
    if ! printf '%s\n' "$LIST_OUTPUT" | grep -qE "^$container(/| |$)"; then
        MISSING="$MISSING $container"
    fi
done
if [ -n "$MISSING" ]; then
    echo "FAIL: no sensors published for container(s):$MISSING"
    exit 1
fi

# 5. Assert a concrete sensor value round-trips through D-Bus.
VALUE_OUTPUT=$("$BIN_DIR/kstatsviewer" cpu/all/usage 2>> "$WORK_DIR/kstatsviewer.err" || true)
echo "--- kstatsviewer cpu/all/usage ---"
echo "$VALUE_OUTPUT"
echo "---------------------------------"
if ! printf '%s\n' "$VALUE_OUTPUT" | grep -q "^cpu/all/usage "; then
    echo "FAIL: cpu/all/usage did not report a value through the D-Bus service"
    exit 1
fi

SENSOR_COUNT=$(printf '%s\n' "$LIST_OUTPUT" | grep -c "/")
echo "PASS: packaged daemon published $SENSOR_COUNT sensors; cpu/all/usage reported a live value"
exit 0
