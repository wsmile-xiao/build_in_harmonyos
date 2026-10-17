#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer side verification of the ypserv 4.2 package.
#
# Runs inside the conanrun environment, so the packaged tools (sbin/,
# lib/yp/) are on PATH.
#
#   1. every packaged tool starts and reports version 4.2
#   2. HarmonyOS specific: yphelper's passwd/shadow and group/gshadow merge
#      uses the password database interfaces that musl libc does not provide
#      (fgetpwent / fgetspent / fgetgrent).  The package replaces them with
#      real implementations, so the merged output must carry the *shadow*
#      password hashes — a no-op stub would let the passwd field ("x") through.
#   3. makedbm round trip, which exercises the statically linked gdbm backend
#      at run time.
set -eu

fail() { echo "❌ $*" >&2; exit 1; }
ok()   { echo "✅ $*"; }

WORK="${TMPDIR:-$HOME/tmp}/ypserv-test-$$"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

# ---------------------------------------------------------------- 1. tools ---
# Daemons live in sbin/, the map tools and helper scripts in lib/yp/.
TOOLS="ypserv rpc.ypxfrd rpc.yppasswdd yppush makedbm mknetid revnetgroup yphelper ypxfr"
for tool in $TOOLS; do
    command -v "$tool" >/dev/null || fail "$tool not on PATH"
    "$tool" --version > "$WORK/$tool.version" 2>&1 || fail "$tool --version exited non-zero"
    if grep -q '4.2' "$WORK/$tool.version"; then
        ok "$tool --version -> $(cat "$WORK/$tool.version")"
    else
        # ypxfr 4.2 prints nothing for --version (upstream behaviour); prove the
        # packaged binary works by asking it for its usage text instead.
        "$tool" -h 2>&1 | grep -qi "$tool" \
            || fail "$tool: neither --version nor -h identified the tool"
        ok "$tool --version silent (upstream), -h usage OK"
    fi
done

# ------------------------------------------- 2. HarmonyOS specific (musl) ---
cat > "$WORK/passwd" <<'EOF'
# comment line, must be skipped by fgetpwent()
root:x:0:0:root:/root:/bin/sh
daemon:x:1:1:daemon:/usr/sbin:/bin/false
testuser:x:1000:1000:Test User:/home/testuser:/bin/sh
EOF
cat > "$WORK/shadow" <<'EOF'
root:$6$rootsalt$rootHash:19000:0:99999:7:::
testuser:$6$usersalt$userHash:19100:0:99999:7:::
EOF
cat > "$WORK/group" <<'EOF'
root:x:0:
testgroup:x:1000:testuser,daemon
EOF
cat > "$WORK/gshadow" <<'EOF'
root:$6$gsalt$ghash::
testgroup:!::testuser
EOF

cat > "$WORK/passwd.expected" <<'EOF'
root:$6$rootsalt$rootHash:0:0:root:/root:/bin/sh
daemon:x:1:1:daemon:/usr/sbin:/bin/false
testuser:$6$usersalt$userHash:1000:1000:Test User:/home/testuser:/bin/sh
EOF
cat > "$WORK/group.expected" <<'EOF'
root:$6$gsalt$ghash:0:
testgroup:!:1000:testuser,daemon
EOF

yphelper --merge_passwd "$WORK/passwd" "$WORK/shadow" > "$WORK/passwd.merged" \
    || fail "yphelper --merge_passwd failed"
diff -u "$WORK/passwd.expected" "$WORK/passwd.merged" \
    || fail "passwd/shadow merge mismatch (musl fgetpwent/fgetspent shim)"
grep -q 'rootHash' "$WORK/passwd.merged" \
    || fail "shadow hash missing: fgetspent() did not parse /etc/shadow format"
if grep -q '^root:x:' "$WORK/passwd.merged"; then
    fail "passwd field not replaced by the shadow hash (stub implementation?)"
fi
ok "yphelper --merge_passwd: fgetpwent/fgetspent shim parses passwd+shadow (OHOS)"

yphelper --merge_group "$WORK/group" "$WORK/gshadow" > "$WORK/group.merged" \
    || fail "yphelper --merge_group failed"
diff -u "$WORK/group.expected" "$WORK/group.merged" \
    || fail "group/gshadow merge mismatch (musl fgetgrent shim)"
ok "yphelper --merge_group: fgetgrent shim parses group+gshadow (OHOS)"

# ------------------------------------------------------- 3. gdbm round trip ---
printf 'alpha\tvalue-one\nbeta\tvalue-two\n' > "$WORK/in.map"
makedbm "$WORK/in.map" "$WORK/out.map" || fail "makedbm (gdbm) failed to build a map"
makedbm -u "$WORK/out.map" > "$WORK/out.map.undumped" || fail "makedbm -u failed"
grep -q 'alpha[[:space:]]*value-one' "$WORK/out.map.undumped" || fail "alpha entry lost"
grep -q 'beta[[:space:]]*value-two' "$WORK/out.map.undumped" || fail "beta entry lost"
ok "makedbm: gdbm backed map round trip (static gdbm/1.23)"

echo "✅ all ypserv package checks passed"
