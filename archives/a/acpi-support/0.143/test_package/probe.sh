#!/data/service/hnp/bin/bash
# test_package/probe.sh — real probes for the installed acpi-support layout.
# $1 = acpi-support package folder. Every check is a real filesystem/script
# assertion (no dlopen-style stub possible for a shell package).
set -u
PKG="${1:?usage: probe.sh <package-folder>}"
failures=0
ok()   { printf '[ok] %s\n' "$1"; }
fail() { printf '[FAIL] %s\n' "$1"; failures=$((failures+1)); }
bash_bin="${CONFIG_SHELL:-bash}"
command -v "$bash_bin" >/dev/null 2>&1 || bash_bin=/data/service/hnp/bin/bash

# 1. Main config installed at /etc/acpi/acpi-support with the method section.
cfg="$PKG/etc/acpi/acpi-support"
if [ -f "$cfg" ] && grep -q "Suspend/hibernate method" "$cfg"; then
    ok "main config present with suspend/hibernate section"
else
    fail "main config missing or truncated ($cfg)"
fi

# 2. All 8 acpid event configs installed, each defining action=.
evdir="$PKG/etc/acpi/events"
evcount=$(ls "$evdir" 2>/dev/null | wc -l)
if [ "$evcount" -eq 8 ]; then
    ok "8 event configs installed"
else
    fail "expected 8 event configs, found $evcount"
fi
bad=0
for ev in "$evdir"/*; do
    grep -q "^action=" "$ev" || bad=$((bad+1))
done
if [ "$bad" -eq 0 ]; then
    ok "every event config defines action="
else
    fail "$bad event configs missing action="
fi

# 3. Handler scripts installed with exec bit.
allx=1
for s in asus-keyboard-backlight.sh asus-wireless.sh ibm-wireless.sh tosh-wireless.sh undock.sh; do
    f="$PKG/etc/acpi/$s"
    [ -f "$f" ] && [ -x "$f" ] || allx=0
done
if [ "$allx" -eq 1 ]; then
    ok "5 handler scripts installed with exec bit"
else
    fail "handler scripts missing or non-executable"
fi

# 4. Syntax of installed scripts validates (bash -n).
syn=0
for s in asus-keyboard-backlight.sh asus-wireless.sh ibm-wireless.sh tosh-wireless.sh undock.sh; do
    "$bash_bin" -n "$PKG/etc/acpi/$s" || syn=$((syn+1))
done
"$bash_bin" -n "$PKG/usr/share/acpi-support/state-funcs" || syn=$((syn+1))
if [ "$syn" -eq 0 ]; then
    ok "bash -n syntax validation of 6 installed scripts"
else
    fail "$syn installed scripts fail bash -n"
fi

# 5. state-funcs library actually loads and runs: isAnyWirelessPoweredOn
#    walks /sys/class/net; exit status 0 (something powered on) or 1
#    (nothing) both prove the function executed; anything else is broken.
probe_rc=$("$bash_bin" -c '. "$1/usr/share/acpi-support/state-funcs"; isAnyWirelessPoweredOn >/dev/null 2>&1; echo $?' _ "$PKG")
if [ "$probe_rc" = "0" ] || [ "$probe_rc" = "1" ]; then
    ok "state-funcs: isAnyWirelessPoweredOn executed (rc=$probe_rc)"
else
    fail "state-funcs function call broken (rc=$probe_rc)"
fi

# 6. key-constants table installed with KEY_ entries.
kc="$PKG/usr/share/acpi-support/key-constants"
if [ -f "$kc" ] && grep -q "^KEY_" "$kc"; then
    ok "key-constants table with KEY_ entries"
else
    fail "key-constants missing or empty ($kc)"
fi

printf '%s: acpi-support probe (%d failures)\n' "$([ "$failures" -eq 0 ] && echo PASS || echo FAIL)" "$failures"
exit $([ "$failures" -eq 0 ] && echo 0 || echo 1)
