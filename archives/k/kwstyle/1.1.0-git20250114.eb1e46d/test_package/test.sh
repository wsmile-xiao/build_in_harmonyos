#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer verification for the kwstyle CLI.
#
# 以「库的使用者」身份调用已安装的 KWStyle 命令，验证它被拿过去能否正常跑通。
#
# 选项风格（源码 eb1e46d57db0 实测）：
#   MetaCommand 只识别单横线选项，因此是 `-version`（不是 `--version`）、
#   `-xml`、`-exportxml`、`-h`。
# 退出码语义（kwsStyle.cxx）：
#   - 帮助/版本分支：MetaCommand::Parse() 返回 false → main `return 1`
#     （上游既有行为，故版本检查不断言退出码，只断言输出内容）
#   - 正常检查分支：`if(nerrors > 0) return EXIT_FAILURE;` 否则 EXIT_SUCCESS
#     → 风格错误文件非 0，干净文件 0
#   - 选项解析失败（如误用 `--version`）同样 return 1
#
# 所有产物写到临时目录，避免污染 test_package/ 归档目录
# （OHOS 上 /tmp 只读，故用 $TMPDIR 或 $HOME/tmp，与 archives/a/aaphoto 同范式）。
#
# 由 test_package/conanfile.py 的 test() 以 `bash test.sh` 调用
# （OHOS /system/bin/sh 无法执行 ELF 二进制）。

set -euo pipefail

fail() {
    echo "FAIL: $1"
    exit 1
}

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

SCRATCH="${TMPDIR:-$HOME/tmp}"
[ -d "$SCRATCH" ] || mkdir -p "$SCRATCH"
TESTDIR="$SCRATCH/kwstyle-consumer-$$"
mkdir -p "$TESTDIR"
trap 'rm -rf "$TESTDIR"' EXIT

echo "=== KWStyle consumer verification ==="

KWSTYLE_BIN=KWStyle
command -v "$KWSTYLE_BIN" >/dev/null 2>&1 || fail "kwstyle 不在 PATH 上（cpp_info.bindirs 未生效）"

# ---------------------------------------------------------------
# 1. 可执行且能打印版本串
#    注意：上游版本分支返回 1（见文件头说明），故只看输出、不断言退出码。
#    `|| true` 用于让 set -e 放行这个预期的非零退出。
# ---------------------------------------------------------------
ver=$("$KWSTYLE_BIN" -version 2>&1) || true
echo "$ver" | grep -qi "version" || fail "-version 输出异常: $ver"
echo "$ver" | grep -q "1\.1\.0" || fail "-version 未包含上游版本号 1.1.0: $ver"
echo "PASS 1/3: -version -> $(echo "$ver" | tr '\n' ' ')"

# ---------------------------------------------------------------
# 2. 有风格错误的文件 → 必须检出并返回非 0，且导出 XML 含 <Error>
#    bad.cpp: 1 个制表符（Tabs 规则）+ 1 行超 120 列（LineLength 规则）
#    非零退出是预期结果，故用 `|| rc=$?` 捕获而不让 set -e 中断。
# ---------------------------------------------------------------
rc=0
"$KWSTYLE_BIN" -xml "$SCRIPT_DIR/kwstyle-config.kws.xml" \
    -exportxml "$TESTDIR/bad-output.xml" "$SCRIPT_DIR/bad.cpp" \
    >"$TESTDIR/bad.log" 2>&1 || rc=$?
if [ "$rc" -eq 0 ]; then
    echo "--- bad.log ---"
    cat "$TESTDIR/bad.log"
    fail "风格错误文件竟返回 0（未检出问题）"
fi
[ -f "$TESTDIR/bad-output.xml" ] || fail "未生成 bad-output.xml"
if ! grep -q "<Error>" "$TESTDIR/bad-output.xml"; then
    echo "--- bad-output.xml ---"
    cat "$TESTDIR/bad-output.xml"
    fail "bad-output.xml 中没有 <Error> 条目"
fi
errs=$(grep -c "<Error>" "$TESTDIR/bad-output.xml")
[ "$errs" -ge 2 ] || fail "预期 >=2 个错误（Tab + 超长行），实际 $errs"
echo "PASS 2/3: 错误检出 -> exit=$rc, $errs 个 <Error>"

# ---------------------------------------------------------------
# 3. 风格干净的文件 → 必须通过并返回 0
# ---------------------------------------------------------------
rc=0
"$KWSTYLE_BIN" -xml "$SCRIPT_DIR/kwstyle-config.kws.xml" \
    "$SCRIPT_DIR/good.cpp" >"$TESTDIR/good.log" 2>&1 || rc=$?
if [ "$rc" -ne 0 ]; then
    echo "--- good.log ---"
    cat "$TESTDIR/good.log"
    fail "干净文件返回 $rc（应为 0）"
fi
echo "PASS 3/3: 干净文件通过 -> exit=0"

echo ""
echo "test kwstyle 1.1.0-git20250114.eb1e46d: 3/3 checks PASS"
exit 0
