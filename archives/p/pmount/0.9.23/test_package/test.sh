#!/data/service/hnp/bin/bash
# test_package/test.sh - behavioural tests for the pmount/pumount executables.
# Runs in the conanrun env (PATH carries bin/).
#
# pmount is designed to be installed setuid root: src/pmount.c and
# src/pumount.c refuse every argument path unless geteuid()==0, and OHOS gives
# the packaged binaries no setuid bit.  So the suite asserts (a) the one
# unprivileged code path really works and (b) the privilege boundary really is
# enforced -- both are observable behaviour, not file existence checks.
set -u

fail=0
note() { echo "[test] $*"; }
bad()  { echo "[test] FAIL: $*"; fail=$((fail + 1)); }

# 1. the only pre-privilege code path: pmount with no arguments.  It must reach
#    print_mounted_removable_devices() (banner on stdout) and then stop at the
#    sysfs probe -- on OHOS the app-sandbox uid cannot even list /sys/block
#    (device: `ls /sys/block` => Permission denied), which policy.c:132 reports
#    as its own error and pmount.c turns into exit status 255.  Asserting this
#    triple proves the argc==1 branch really ran and did NOT reach the suid gate
#    or mount(8); the enumeration itself is a documented platform limitation.
out=$(pmount 2>pm.err); rc=$?
# Which outcome this path produces depends on the runner: policy.c:130-134 exits -1
# (status 255) as soon as opendir(/sys/block) is denied, while main() returns 0 after
# the enumeration when sysfs is listable (that is the CI worker).  Probe the premise
# and assert the matching behaviour on both machines; the group count is unchanged.
if ls /sys/block >/dev/null 2>&1; then
    if [ "$rc" -ne 0 ]; then
        bad "pmount (no args) exited $rc, expected 0 (sysfs is listable here)"
    elif ! printf '%s' "$out" | grep -q "Printing mounted removable devices"; then
        bad "pmount (no args) never printed the banner; got: $out"
    elif ! printf '%s' "$out" | grep -q "To get a short help"; then
        bad "pmount (no args) left the argc==1 branch early; got: $out"
    elif grep -q "suid root" pm.err; then
        bad "the argc==1 branch must be checked before the suid gate, but the gate fired"
    else
        note "pmount no-arg path enumerates sysfs and returns before the suid gate (0)"
    fi
elif [ "$rc" -ne 255 ]; then
    bad "pmount (no args) exited $rc, expected 255 (sysfs denial path)"
elif ! printf '%s' "$out" | grep -q "Printing mounted removable devices"; then
    bad "pmount (no args) never printed the banner; got: $out"
elif ! grep -q "could not open <sysfs dir>/block/" pm.err; then
    bad "pmount (no args) failed for another reason; got: $(cat pm.err)"
elif grep -q "suid root" pm.err; then
    bad "the argc==1 branch must be checked before the suid gate, but the gate fired"
else
    note "pmount no-arg path runs pre-gate and stops at the sysfs permission wall (255)"
fi

# 2. short option after the privilege gate: must be refused, usage must NOT run.
err=$(pmount -h 2>&1 >/dev/null); rc=$?
if [ $rc -eq 0 ]; then
    bad "pmount -h exited 0: the unprivileged build would expose mount(8) calls"
elif ! printf '%s' "$err" | grep -q "needs to be installed suid root"; then
    bad "pmount -h failed for another reason; got: $err"
else
    note "pmount -h privilege boundary enforced as documented"
fi

# 3. long option takes the same gate (getopt_long table is reached only after it).
err=$(pmount --version 2>&1 >/dev/null); rc=$?
if [ $rc -eq 0 ]; then
    bad "pmount --version exited 0, expected the suid refusal"
elif ! printf '%s' "$err" | grep -q "needs to be installed suid root"; then
    bad "pmount --version failed for another reason; got: $err"
else
    note "pmount --version privilege boundary enforced"
fi

# 4. pumount behaves the same way on its argument path.
err=$(pumount -h 2>&1 >/dev/null); rc=$?
if [ $rc -eq 0 ]; then
    bad "pumount -h exited 0, expected the suid refusal"
elif ! printf '%s' "$err" | grep -q "needs to be installed suid root"; then
    bad "pumount -h failed for another reason; got: $err"
else
    note "pumount -h privilege boundary enforced"
fi

# 5. a real device argument still stops at the gate rather than at name
#    resolution, i.e. no mount(8) is attempted for an unprivileged caller.
err=$(pmount /dev/definitely-not-a-device 2>&1 >/dev/null); rc=$?
if [ $rc -eq 0 ]; then
    bad "pmount accepted a bogus device without privileges"
elif printf '%s' "$err" | grep -qi "could not execute mount"; then
    bad "pmount reached mount(8) while unprivileged; got: $err"
elif ! printf '%s' "$err" | grep -q "needs to be installed suid root"; then
    bad "unexpected first error for a bogus device; got: $err"
else
    note "pmount device-argument path gated before mount(8)"
fi

# 6. ELF sanity for both installed programs.
for prog in pmount pumount; do
    path=$(command -v $prog || true)
    if [ -z "$path" ]; then
        bad "$prog is not on PATH"
    elif [ "$(head -c 4 "$path" | od -An -tx1 | tr -d ' \n')" != "7f454c46" ]; then
        bad "$prog is not an ELF binary ($path)"
    else
        note "$prog is a valid ELF ($path)"
    fi
done

if [ $fail -ne 0 ]; then
    echo "[test] $fail assertion(s) failed"
    exit 1
fi
echo "[test] all pmount consumer assertions passed"
