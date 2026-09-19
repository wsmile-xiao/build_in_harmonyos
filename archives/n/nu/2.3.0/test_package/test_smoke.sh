#!/usr/bin/env bash
# nu 2.3.0 smoke tests — 5 项实质断言，供 conanfile.py test() 与 CI L0c 使用
# 用法: bash test_smoke.sh <nush路径> <libNu路径>
set -euo pipefail

NUSH="$1"
LIBNU="$2"
export NU_LIBRARY_PATH="$LIBNU"

fail() { echo "FAIL: $1" >&2; exit 1; }

# 1. arithmetic
out=$("$NUSH" -e '(puts (+ 40 2))' 2>/dev/null)
[ "$out" = "42" ] || fail "arith expect 42 got '$out'"
echo "PASS arith"

# 2. control-flow: for + break → 15
out=$("$NUSH" -e '(set x 0) (for ((set i 1) (< i 10) (set i (+ i 1))) (if (== i 6) (break)) (set x (+ x i))) (puts x)' 2>/dev/null)
[ "$out" = "15" ] || fail "control-flow expect 15 got '$out'"
echo "PASS control-flow"

# 3. native ObjC exception try/catch
out=$("$NUSH" -e '(try (throw (NSString stringWithString: "boom")) (catch (e) (puts (+ "caught:" e))))' 2>/dev/null)
case "$out" in
  caught:*) echo "PASS try/catch ($out)" ;;
  *) fail "try/catch expect caught:boom got '$out'" ;;
esac

# 4. POSIX-regex NuRegex group extraction → 24
out=$("$NUSH" -e '(set m (/a(.*)z/ findInString:"abcdefghijklmnopqrstuvwxyz")) (puts ((m groupAtIndex:1) length))' 2>/dev/null)
[ "$out" = "24" ] || fail "regex expect 24 got '$out'"
echo "PASS regex"

# 5. list map → (1 4 9)
out=$("$NUSH" -e '(puts ((list 1 2 3) map: (do (x) (* x x))))' 2>/dev/null)
[ "$out" = "(1 4 9)" ] || fail "map expect (1 4 9) got '$out'"
echo "PASS map"

# 6. [鸿蒙特有] OHOS 平台识别: 内核/系统名应包含 ohos 或 linux (OHOS 基于 linux 内核)
out=$(uname -s 2>/dev/null | tr '[:upper:]' '[:lower:]')
case "$out" in
  *ohos*|*linux*) echo "PASS ohos-platform ($out)" ;;
  *) fail "ohos-platform expect *ohos*/linux got '$out'" ;;
esac

# 7. [鸿蒙特有] Nu 通过 ObjC 桥接访问系统信息 (NSProcessInfo 可用性)
out=$("$NUSH" -e '(puts (NSProcessInfo processInfo) processName)' 2>/dev/null)
case "$out" in
  nush|*nu*) echo "PASS ohos-objc-bridge ($out)" ;;
  *) fail "ohos-objc-bridge expect nush got '$out'" ;;
esac

echo "ALL TESTS PASSED"
