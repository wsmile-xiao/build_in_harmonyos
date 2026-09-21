#!/bin/sh
# test_package/test_uucp_ohos.sh — consumer test for the packaged Taylor UUCP
# binaries, executed on the HarmonyOS PC device itself (aarch64).
# Runs in the conanrun environment (PATH includes the installed bin/ dir).
# Real assertions on CLI output and on the real configuration parser; any
# failure makes `conan test` fail (CI L1e verifies the test really needs the
# package).
#
# NOTE: deliberately not `set -e`: assertions run commands that may legally
# return non-zero; the check() helper evaluates them as conditions.
set -u

DIR="uucp-test.$$"
mkdir -p "$DIR"
cd "$DIR" || exit 1

n_ok=0
n_fail=0
check() {
  msg="$1"
  shift
  if eval "$@" >/dev/null 2>&1; then
    echo "ok - $msg"
    n_ok=$((n_ok + 1))
  else
    echo "not ok - $msg"
    n_fail=$((n_fail + 1))
  fi
}

echo "1..18"

# --- 1..13: every packaged artifact exists, is executable and answers -v ---

for prog in uucico uuxqt uuchk uuconv uux uucp uustat uuname uulog uupick cu; do
  check "$prog is installed, executable and reports the 1.07 banner" \
    "rc=0; out=\$($prog -v 2>&1) || rc=\$?; [ \$rc -eq 0 ] && echo \"\$out\" | grep -q 'Taylor UUCP) 1.07'"
done

# uusched and uuto are POSIX sh scripts (not -v style binaries); assert they
# exist, are executable and are syntactically valid shell.
check "uusched is installed, executable and valid shell" \
  "command -v uusched >/dev/null && test -x \$(command -v uusched) && sh -n \$(command -v uusched)"
check "uuto is installed, executable and valid shell" \
  "command -v uuto >/dev/null && test -x \$(command -v uuto) && sh -n \$(command -v uuto)"

# --- 14: OHOS platform assertion (consumer case runs on the target device) ---

check "consumer case runs on an aarch64 HarmonyOS PC host" \
  "test \"\$(uname -m)\" = aarch64"

# --- 15..18: OHOS consumer functional case — the real configuration parser ---

# Build a minimal but complete Taylor UUCP configuration chain in a temporary
# directory: main `config` pointing at a `sys` file and a TCP `port` file, then
# let uuchk walk the whole chain.  This exercises uuconf's parser, the sysfile
# and portfile indirection, and the system/printer code paths — the same code
# uucico uses at startup — with no serial hardware or spool privileges needed.

CONF="$PWD/ohos-uucp-conf"
mkdir -p "$CONF"
cat > "$CONF/config" <<EOF
# Minimal OHOS consumer test configuration
nodename ohos-test
sysfile $CONF/sys
portfile $CONF/port
EOF
cat > "$CONF/sys" <<'EOF'
system uunet
time any
port tcp
address 127.0.0.1
EOF
cat > "$CONF/port" <<'EOF'
port tcp
type tcp
EOF

# 15) uuchk parses the chain and prints the remote system definition.
check "uuchk -I resolves the config/sysfile/portfile chain and prints system uunet" \
  "rc=0; out=\$(uuchk -I $CONF/config 2>&1) || rc=\$?; [ \$rc -eq 0 ] && echo \"\$out\" | grep -q 'uunet'"

# 16) uuchk -s examines exactly the named system.
check "uuchk -I -s uunet prints the full definition for the named system" \
  "rc=0; out=\$(uuchk -I $CONF/config -s uunet 2>&1) || rc=\$?; [ \$rc -eq 0 ] && echo \"\$out\" | grep -q 'uunet' && echo \"\$out\" | grep -q 'port'"

# 17) uuchk rejects a bogus system name with a non-zero status (parser really
#     validates, not just prints).
check "uuchk -I -s no-such-system exits non-zero" \
  "uuchk -I $CONF/config -s no-such-system 2>/dev/null; test \$? -ne 0"

# 18) uuname -l lists the nodename declared in the consumer configuration.
check "uuname -I reports the configured nodename ohos-test" \
  "rc=0; out=\$(uuname -I $CONF/config -l 2>&1) || rc=\$?; [ \$rc -eq 0 ] && echo \"\$out\" | grep -q 'ohos-test'"

echo "# ok=$n_ok fail=$n_fail"
# Clean up the whole scratch directory regardless of the outcome.
cd ..
rm -rf "$DIR"
if [ "$n_fail" -ne 0 ]; then
  echo "$n_fail check(s) FAILED"
  exit 1
fi
echo "all checks passed"
exit 0
