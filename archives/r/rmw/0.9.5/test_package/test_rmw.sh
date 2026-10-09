#!/bin/sh
# End-to-end consumer test for rmw (OHOS aarch64).
# Exercises: version banner, config parsing, move-to-waste (+ trashinfo),
# orphaned check, and restore.  Prints one "ok"/"FAIL" line per assertion and
# exits non-zero on any failure.

RMW_BINDIR="${RMW_BINDIR:-.}"
RMW="$RMW_BINDIR/rmw"

PASS=0
FAIL=0

ok() { PASS=$((PASS + 1)); echo "ok   - $1"; }
bad() { FAIL=$((FAIL + 1)); echo "FAIL - $1"; }
assert() { # assert <desc> <cmd...>
    desc=$1; shift
    if "$@" >/dev/null 2>&1; then ok "$desc"; else bad "$desc"; fi
}

# Locate a usable mktemp
TMPBASE=$(mktemp -d "${TMPDIR:-/data/storage/el2/base/cache}/rmw-test.XXXXXX") || exit 2
trap 'rm -rf "$TMPBASE"' EXIT

WORK=$TMPBASE/work
WASTE=$TMPBASE/waste
mkdir -p "$WORK" "$WASTE"

CFG=$TMPBASE/rmwrc
cat > "$CFG" <<EOF
WASTE = $WASTE
expire_age = 0
EOF

# 1. version banner (consumer invocation of the installed binary)
"$RMW" --version > "$TMPBASE/version.out" 2>&1
if grep -q "0\.9\.5" "$TMPBASE/version.out"; then
    ok "rmw --version reports 0.9.5"
else
    bad "rmw --version reports 0.9.5"
    cat "$TMPBASE/version.out"
fi

# 2. help banner
assert "rmw --help exits 0" "$RMW" --help

# 3. config file is parsed without errors (-c consumer config, -o orphaned check)
assert "rmw -o (orphaned check) accepts consumer config" \
    env HOME="$TMPBASE" "$RMW" -c "$CFG" -o

# 4. move a file into the waste directory
echo "hello rmw" > "$WORK/hello.txt"
assert "rmw moves hello.txt into waste" \
    env HOME="$TMPBASE" "$RMW" -c "$CFG" "$WORK/hello.txt"

# 5. the original is gone
assert "original file no longer present" test ! -e "$WORK/hello.txt"

# 6. the file landed in the waste/files directory (FreeDesktop layout)
assert "wasted copy exists in waste/files" test -e "$WASTE/files/hello.txt"

# 7. a trashinfo sidecar was generated in waste/info
assert "trashinfo sidecar exists in waste/info" \
    test -e "$WASTE/info/hello.txt.trashinfo"

# 8. trashinfo references the original path
if grep -q "Path=$WORK/hello.txt" "$WASTE/info/hello.txt.trashinfo" 2>/dev/null; then
    ok "trashinfo records the original path"
else
    bad "trashinfo records the original path"
fi

# 9. restore via -z
assert "rmw -z restores the file" \
    env HOME="$TMPBASE" "$RMW" -c "$CFG" -z "$WASTE/files/hello.txt"

# 10. restored content matches
if [ "$(cat "$WORK/hello.txt" 2>/dev/null)" = "hello rmw" ]; then
    ok "restored file content matches"
else
    bad "restored file content matches"
fi

# 11. trashinfo consumed on restore
assert "trashinfo removed after restore" \
    test ! -e "$WASTE/info/hello.txt.trashinfo"

echo "passed=$PASS failed=$FAIL"
if [ "$FAIL" -ne 0 ]; then
    exit 1
fi
exit 0
