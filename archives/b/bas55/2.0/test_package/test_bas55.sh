#!/bin/sh
set -eu

BIN="$1"
BAS55="$BIN/bas55"

OUT_DIR=$(mktemp -d "${TMPDIR:-$HOME/tmp}/bas55-test-XXXXXX")
trap 'rm -rf "$OUT_DIR"' EXIT

# 断言 1：bas55 二进制存在且可执行
if [ ! -x "$BAS55" ]; then
    echo "FAIL: bas55 binary not found or not executable: $BAS55" >&2
    exit 1
fi

# 断言 2：-v 输出版本信息（bas55 2.0）
"$BAS55" -v > "$OUT_DIR/version.out" 2>&1
grep -F "bas55 2.0" "$OUT_DIR/version.out"

# 断言 3：-h 输出 Usage
"$BAS55" -h > "$OUT_DIR/help.out" 2>&1
grep -F "Usage:" "$OUT_DIR/help.out"

# 断言 4（正向）：运行一个简单 BASIC 程序并校验输出
cat > "$OUT_DIR/hello.bas" <<'EOF'
10 PRINT "HELLO FROM BAS55"
20 END
EOF
"$BAS55" "$OUT_DIR/hello.bas" > "$OUT_DIR/hello.out" 2>&1
grep -F "HELLO FROM BAS55" "$OUT_DIR/hello.out"

# 断言 5（负向）：非法 BASIC 程序必须在 stderr 报告错误
# 注：bas55 对程序内错误是容错语义——stderr 报错后继续执行、
# 退出码仍为 0（上游行为，.eok 校验错误输出而非退出码），
# 因此负向断言校验错误输出而非退出码。
cat > "$OUT_DIR/bad.bas" <<'EOF'
10 PRINT "UNCLOSED
20 END
EOF
"$BAS55" "$OUT_DIR/bad.bas" > "$OUT_DIR/bad.out" 2>&1 || true
grep -iE "error|string not terminated" "$OUT_DIR/bad.out" >/dev/null

# 断言 6（负向）：非法 -g 参数必须被拒绝（退出码非 0 + 错误信息）
if "$BAS55" -g bogus "$OUT_DIR/hello.bas" > "$OUT_DIR/neg.out" 2>&1; then
    echo "FAIL: bas55 accepted invalid -g option value" >&2
    exit 1
fi
grep -F "bad GOSUB stack size" "$OUT_DIR/neg.out" >/dev/null

echo "bas55 test_package: all assertions passed"
