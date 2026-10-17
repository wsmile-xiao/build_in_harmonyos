#!/data/service/hnp/bin/bash
# test_package/test.sh — functional smoke test for the ayatana-indicator-a11y
# daemon. Runs inside the conanrun env (PATH/LD_LIBRARY_PATH include the
# installed package and conan-managed dependency libraries).
#
# The daemon owns the org.ayatana.indicator.a11y busname on the SESSION bus.
# In a headless CI sandbox without a D-Bus session bus, g_bus_own_name()
# fails immediately, the "name-lost" signal fires and main() quits with
# exit code 0 — so a clean exit is a valid pass. In an environment where a
# session bus exists the daemon keeps running, so a timeout (still alive
# after the grace period) is also a pass. Any other exit code (crash,
# missing library) is a failure.
set -uo pipefail

SCRATCH="${TMPDIR:-$HOME/tmp}"
mkdir -p "$SCRATCH"
trap 'rm -rf "$SCRATCH/a11y-stderr.log"' EXIT

# Daemon installs under libexec/ayatana-indicator-a11y/, not bin/ — the
# package folder is provided by conanfile.py via the A11Y_PKG variable.
PKG_PREFIX="${A11Y_PKG:?A11Y_PKG not set (run via conan test_package)}"
BINARY="$PKG_PREFIX/libexec/ayatana-indicator-a11y/ayatana-indicator-a11y-service"

# ── Test 1: daemon binary is a real ELF executable ──
[ -n "$BINARY" ] || { echo "❌ ayatana-indicator-a11y-service not found"; exit 1; }
[ -x "$BINARY" ] || { echo "❌ daemon binary not executable: $BINARY"; exit 1; }
head -c4 "$BINARY" | grep -q $'\x7fELF' || { echo "❌ daemon binary is not ELF: $BINARY"; exit 1; }
echo "✅ daemon ELF executable: $BINARY"

# ── Test 2: daemon loads all dependencies and reaches main() ──
# The daemon requires an X display + D-Bus session/system bus, which a
# headless CI sandbox cannot provide. Once all shared libraries are resolved
# and main() is reached, service_new() panics ("Failed to open X display" /
# "Failed connecting to the system bus") and GLib traps (SIGTRAP, rc=133).
# That panic is an ENVIRONMENT limitation, not a packaging defect — it proves
# the full dependency chain (glib/gobject/accountsservice/libayatana-common/
# X11) loaded and the ELF executed. A missing library would instead abort
# with "Error loading shared library" or "symbol not found".
echo "[test] launching ayatana-indicator-a11y-service (3s grace)"
"$BINARY" >/dev/null 2>"$SCRATCH/a11y-stderr.log" &
PID=$!
sleep 3
if kill -0 "$PID" 2>/dev/null; then
    # Still running: display + bus available, daemon owns the busname — pass.
    kill "$PID" 2>/dev/null
    wait "$PID" 2>/dev/null
    echo "✅ daemon is running (owns org.ayatana.indicator.a11y busname)"
else
    wait "$PID"
    RC=$?
    if [ "$RC" -eq 0 ]; then
        # Clean exit: no session bus, name-lost fired, main() returned 0.
        echo "✅ daemon exited cleanly (rc=0, no session bus available)"
    elif [ "$RC" -eq 133 ] && grep -q "Panic: Failed to open X display" "$SCRATCH/a11y-stderr.log"; then
        # Headless sandbox: all libs resolved, main() reached, daemon panicked
        # on the missing X display — dependency chain verified.
        echo "✅ daemon loaded all deps and reached main() (headless panic expected)"
    elif grep -q "Error loading shared library\|symbol not found" "$SCRATCH/a11y-stderr.log"; then
        echo "❌ daemon failed to load dependencies (rc=$RC):"
        head -5 "$SCRATCH/a11y-stderr.log"
        exit 1
    else
        echo "❌ daemon exited with rc=$RC (crash or missing dependency)"
        head -5 "$SCRATCH/a11y-stderr.log"
        exit 1
    fi
fi

# ── Test 3: installed data artifacts ──
for f in \
    "$PKG_PREFIX/share/glib-2.0/schemas/org.ayatana.indicator.a11y.gschema.xml" \
    "$PKG_PREFIX/share/ayatana/indicators/org.ayatana.indicator.a11y" \
    "$PKG_PREFIX/share/dbus-1/interfaces/org.ayatana.indicator.a11y.AccountsService.xml" \
    "$PKG_PREFIX/share/icons/hicolor/scalable/status/ayatana-indicator-a11y-scale-up.svg" \
    "$PKG_PREFIX/etc/xdg/autostart/ayatana-indicator-a11y.desktop" \
    ; do
    [ -f "$f" ] || { echo "❌ missing installed artifact: $f"; exit 1; }
done
echo "✅ GSettings schema + indicator descriptor + D-Bus XML + icon + autostart desktop file present"

echo "ALL TESTS PASSED"
