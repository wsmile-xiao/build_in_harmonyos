#!/bin/sh
# Consumer test driver for unace on OHOS.
# usage: test_unace.sh <unace_bin> <archive> <workdir>
#
# 7 consumer assertions (A1..A7). unace returns unreliable exit codes (main()
# has no explicit return), so every assertion judges printed output/content.
UNACE="$1"; ARC="$2"; WORK="$3"
pass=0; fail=0

ok()  { pass=$((pass+1)); echo "PASS: $1"; }
bad() { fail=$((fail+1)); echo "FAIL: $1"; }

# A1 version self-report (printf(version) runs on every invocation)
v="$("$UNACE" 2>&1 | head -1)"
case "$v" in
  *UNACE*v1.2*) ok "A1 version self-report ($v)" ;;
  *) bad "A1 version self-report, got: $v" ;;
esac

mkdir -p "$WORK/l" "$WORK/e" "$WORK/x" || exit 1

# A2/A3 list mode shows both entries
out="$("$UNACE" l "$ARC" 2>&1)"
echo "$out" | grep -q "hello.txt" && ok "A2 l lists hello.txt" || bad "A2 l lists hello.txt"
echo "$out" | grep -q "deep.txt" && ok "A3 l lists deep.txt" || bad "A3 l lists deep.txt"

# A4 integrity test: the tool's own CRC check must say OK for both files
n="$("$UNACE" t "$ARC" 2>&1 | grep -c 'CRC OK')"
[ "$n" = "2" ] && ok "A4 t reports 2x CRC OK" || bad "A4 t CRC OK count=$n (want 2)"

# A5/A6 flat extraction (e) — both files land in cwd, path stripped
(cd "$WORK/e" && "$UNACE" e -y "$ARC" >/dev/null 2>&1)
[ "$(cat "$WORK/e/hello.txt" 2>/dev/null)" = "Hello from unace test package!" ] \
  && ok "A5 e hello.txt content" || bad "A5 e hello.txt content"
[ "$(cat "$WORK/e/deep.txt" 2>/dev/null)" = "nested content for unace on OHOS" ] \
  && ok "A6 e flattens sub/deep.txt" || bad "A6 e flattens sub/deep.txt"

# A7 path extraction (x) — backslash separator becomes DIRSEP
(cd "$WORK/x" && "$UNACE" x -y "$ARC" >/dev/null 2>&1)
[ "$(cat "$WORK/x/sub/deep.txt" 2>/dev/null)" = "nested content for unace on OHOS" ] \
  && ok "A7 x extracts sub/deep.txt" || bad "A7 x extracts sub/deep.txt"

echo "SUMMARY pass=$pass fail=$fail total=$((pass+fail))"
[ "$fail" -eq 0 ]
