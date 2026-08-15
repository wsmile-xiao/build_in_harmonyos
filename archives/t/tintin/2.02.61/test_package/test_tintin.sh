#!/bin/sh
set -eu

BIN="$1"
TTPP="$BIN/tt++"

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

# 独立临时目录：test_package 源目录在 CI 上可能只读，输出与 HOME
# （tt++ 启动时会创建 $HOME/.tintin）全部落在 TMPDIR 下
OUT_DIR=$(mktemp -d "${TMPDIR:-/tmp}/tintin-test-XXXXXX")
trap 'rm -rf "$OUT_DIR"' EXIT
export HOME="$OUT_DIR"

# 上游 src/validate 自校验脚本（原样拷贝，未修改）：
# 113 个 error 断言点（112 个独立编号），覆盖 math/line/buffer/switch/
# class/loop/parse/path/script/regex/list/format/map/hash/cursor/tab 等
# 脚本引擎核心命令，通过判据为输出 "End of validation with 0 errors"。
VALIDATE="$SCRIPT_DIR/validate"

# 断言 1：tt++ 二进制存在且可执行
if [ ! -x "$TTPP" ]; then
    echo "FAIL: tt++ binary not found or not executable: $TTPP" >&2
    exit 1
fi

# 断言 2：-V 输出 TinTin++ 2.02.61
# tt++ -V 按上游行为打印版本后 exit(1)（main.c -V 分支），退出码
# 不参与断言，只校验输出内容
"$TTPP" -V > "$OUT_DIR/version.out" 2>&1 || true
grep -F "TinTin++ 2.02.61" "$OUT_DIR/version.out"

# 断言 3：上游 validate 套件整体退出码为 0
# -H（nohup）：CI 无 TTY，跳过终端初始化（tcsetattr 在非终端上致命）
TERM=xterm "$TTPP" -H -G "$VALIDATE" > "$OUT_DIR/validate.out" 2>&1

# 断言 4：validate 报告 0 errors（上游通过判据，113/113 断言点通过）
grep -F "End of validation with 0 errors" "$OUT_DIR/validate.out"

# 负向断言 5：非法 -l 参数必须被拒绝（上游 main.c：exit 1）
if TERM=xterm "$TTPP" -H -l bogus > "$OUT_DIR/neg.out" 2>&1; then
    echo "FAIL: tt++ accepted invalid -l option value" >&2
    exit 1
fi

# 负向断言 6：拒绝时输出用法提示
grep -F "Option arguments are: -l <rain|regex>." "$OUT_DIR/neg.out"

echo "tintin test_package: all assertions passed"
