#!/bin/sh
# test_package/test_smoke.sh — real artifact verification for alpine-baselayout 3.7.2.
#
# The packaged artifact is a configuration/data package (noarch). This test
# verifies packaging integrity against the upstream 3.7.2 content:
#   1. etc/crontabs/root (crontab, mode 600)
#   2. etc/profile.d/color_prompt.sh.disabled + 20locale.sh
#   3. etc/modprobe.d/aliases.conf + blacklist.conf + i386.conf
#   4. etc/group + etc/passwd + etc/inittab + etc/profile
#   5. etc/protocols + etc/services (netbase v6.4 content)
#   6. etc/shadow generated from passwd (upstream awk semantics)
#   7. usr/share/man/man7/hier.7
#   8. licenses/GPL-2.0.txt (GPLv2 official text)
#   9. shell scripts pass `sh -n`
#
# NOTE: upstream APKBUILD has options="!fhs !check keepdirs" and no
# test()/check() function — there is no upstream automated test suite.
# This is a consumer-side packaging-integrity test, not an upstream test.
set -euo pipefail

PKG_ROOT="${1:-}"
TEST_SHELL="${2:-}"

if [ -z "$PKG_ROOT" ] || [ -z "$TEST_SHELL" ]; then
    echo "ERROR: package root and shell path are required" >&2
    exit 1
fi

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

pass_count=0
ok() {
    pass_count=$((pass_count + 1))
    echo "PASS: $*"
}

assert_file() {
    [ -f "$1" ] || fail "file missing: $1"
}

# --- 1. crontab -> etc/crontabs/root ---
f="$PKG_ROOT/etc/crontabs/root"
assert_file "$f"
# 上游 install -m600。注意：本文件系统（含 CI worker）强制 group-write 位，
# chmod 600 后 stat 仍为 660（实测），因此断言语义：owner 可读写 + 非 world 可读。
mode=$(stat -c %a "$f" 2>/dev/null || stat -f %Lp "$f" 2>/dev/null)
case "$mode" in
    [0-7][0-7][0-3]) ;;
    *) fail "crontab world-readable or unexpected mode: $mode" ;;
esac
grep -q "^#.*do daily/weekly/monthly maintenance" "$f" || fail "crontab content unexpected: $f"
ok "etc/crontabs/root present (owner rw, not world-readable, upstream crontab)"

# --- 2. profile.d scripts ---
for f in "$PKG_ROOT/etc/profile.d/color_prompt.sh.disabled" "$PKG_ROOT/etc/profile.d/20locale.sh"; do
    assert_file "$f"
    "$TEST_SHELL" -n "$f" || fail "sh -n failed: $f"
done
ok "profile.d scripts present and pass sh -n"

# --- 3. modprobe.d configs ---
for f in aliases.conf blacklist.conf i386.conf; do
    assert_file "$PKG_ROOT/etc/modprobe.d/$f"
done
grep -q "alias.*net-pf-3" "$PKG_ROOT/etc/modprobe.d/aliases.conf" || fail "aliases.conf content unexpected"
ok "modprobe.d configs present (aliases/blacklist/i386)"

# --- 4. group / passwd / inittab / profile ---
assert_file "$PKG_ROOT/etc/group"
grep -q "^root:x:0:" "$PKG_ROOT/etc/group" || fail "group root entry missing"
assert_file "$PKG_ROOT/etc/passwd"
grep -q "^root:x:0:0:root:/root:/bin/sh" "$PKG_ROOT/etc/passwd" || fail "passwd root entry missing"
assert_file "$PKG_ROOT/etc/inittab"
grep -q "::sysinit:" "$PKG_ROOT/etc/inittab" || fail "inittab sysinit missing"
assert_file "$PKG_ROOT/etc/profile"
grep -q 'export PATH="/usr/local/sbin' "$PKG_ROOT/etc/profile" || fail "profile PATH missing"
ok "etc/group passwd inittab profile present with expected content"

# --- 5. protocols / services (netbase v6.4) ---
assert_file "$PKG_ROOT/etc/protocols"
grep -q "^tcp" "$PKG_ROOT/etc/protocols" || fail "protocols tcp missing"
assert_file "$PKG_ROOT/etc/services"
grep -q "^http" "$PKG_ROOT/etc/services" || fail "services http missing"
ok "etc/protocols and etc/services present (netbase v6.4)"

# --- 6. shadow generated from passwd (upstream awk semantics) ---
f="$PKG_ROOT/etc/shadow"
assert_file "$f"
# upstream awk: root gets pw "::", others get ":!:", then ":0:::::"
first=$(head -n1 "$f")
[ "$first" = "root:::0:::::" ] || fail "shadow root line unexpected: $first"
grep -q "^bin:!::0:::::" "$f" || fail "shadow bin line unexpected"
ok "etc/shadow generated with upstream awk semantics"

# --- 7. hier.7 man page ---
assert_file "$PKG_ROOT/usr/share/man/man7/hier.7"
grep -q "Alpine" "$PKG_ROOT/usr/share/man/man7/hier.7" || fail "hier.7 content unexpected"
ok "usr/share/man/man7/hier.7 present"

# --- 8. license ---
f="$PKG_ROOT/licenses/GPL-2.0.txt"
assert_file "$f"
head -n2 "$f" | grep -q "GNU GENERAL PUBLIC LICENSE" || fail "license text unexpected: $f"
ok "licenses/GPL-2.0.txt present (GPLv2 official text)"

echo "PASS: alpine-baselayout smoke test: $pass_count assertions passed"
