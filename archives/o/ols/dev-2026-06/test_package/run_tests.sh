#!/usr/bin/env bash
# test_package/run_tests.sh — ols 包端到端测试驱动（6 项）
#
# 用法: run_tests.sh <ols_bin> <pkg_dir> <work_dir>
#   ols_bin  : 包内 bin/ols 的绝对路径
#   pkg_dir  : ols 包根（供诊断使用）
#   work_dir : 测试产物输出目录（测试结束不清理，便于 CI 取证）
#
# 由 test_package/conanfile.py 的 test() 调用；也可脱离 conan 手工复现。
#
# 设计依据（无头环境，上游源码为准）：
#   * `ols version` 是 src/main.odin 中服务端启动之前的纯 IO 退出路径
#     （判 os.args[1] == "version" 即打印并 os.exit(0)），与显示/终端无关。
#   * ols 是 LSP 服务器：无参数启动后进入 request 循环，只在收到 exit 通知
#     （notification_exit → config.running = false）后才退出。上游 reader 在
#     stdin 提前 EOF 时仅让 request 线程退出、主循环仍 sema_wait —— 即 stdin
#     提前关闭会导致进程永久阻塞。故本驱动必须显式走
#     initialize → initialized → … → shutdown → exit 的完整 LSP 生命周期。
#   * 上游 initialize 响应只有 result.capabilities，不含 serverInfo
#     （src/server/types.odin: ResponseInitializeParams :: struct { capabilities }），
#     故能力断言落在 capabilities 字段上。

set -uo pipefail

OLS_BIN="$1"
PKG_DIR="$2"
WORK_DIR="$3"

HERE="$(cd "$(dirname "$0")" && pwd)"
LSP="$HERE/lsp"
WS="$WORK_DIR/ws"
RESP="$WORK_DIR/resp.txt"
ERRLOG="$WORK_DIR/stderr.txt"

rm -rf "$WORK_DIR"
mkdir -p "$WS"
cp "$HERE/sample/main.odin" "$WS/main.odin"
# 测试产物不留在仓库内：退出即清理；失败时把响应原文打到 stdout 供 CI 取证
trap 'rm -rf "$WORK_DIR"' EXIT

dump() {
    [ -f "$RESP" ] && { echo '-------- resp.txt --------'; cat "$RESP"; }
    [ -f "$ERRLOG" ] && { echo '-------- stderr.txt --------'; cat "$ERRLOG"; }
}
fail() { printf '[test] FAIL: %s\n' "$*" >&2; dump >&2; exit 1; }

# ── 1/6 `ols version`（纯 IO 路径，服务端未启动）────────────────────────────
echo "[test] 1/6 ols version：纯 IO 退出路径，输出含登记版本且 rc=0"
VER_RAW="$("$OLS_BIN" version 2>&1)"; VER_RC=$?
printf '        rc=%s out=%s\n' "$VER_RC" "$VER_RAW"
[ "$VER_RC" -eq 0 ] || fail "ols version 退出码非 0（rc=$VER_RC）"
case "$VER_RAW" in
    *"ols version dev-2026-06"*) ;;
    *) fail "ols version 输出不含 'ols version dev-2026-06'（实际：$VER_RAW）" ;;
esac

# ── 2/6 运行期资产 builtin/ 必须与 ols 二进制同级（上游 README 要求）──────────
echo "[test] 2/6 builtin/ 运行期资产与 ols 二进制同级且完整"
BIN_DIR="$(cd "$(dirname "$OLS_BIN")" && pwd)"
[ -x "$BIN_DIR/ols" ] || fail "包内 $BIN_DIR/ols 不可执行"
for f in builtin.odin intrinsics.odin; do
    [ -f "$BIN_DIR/builtin/$f" ] || fail "缺少运行期资产 $BIN_DIR/builtin/$f"
done
printf '        %s/builtin/{builtin.odin,intrinsics.odin} OK\n' "$BIN_DIR"

# ── 3~6/6 LSP 无头会话（stdin/stdout JSON-RPC，Content-Length 分帧）─────────
echo "[test] 3/6 LSP initialize 握手 + 4/6 能力协商 + 5/6 documentSymbol + 6/6 优雅退出"

frame() { printf 'Content-Length: %d\r\n\r\n%s' "${#1}" "$1"; }
msg() { local t; t="$(cat "$LSP/$1")"; printf '%s' "${t//__WS__/$WS}"; }

RUNNER=( "$OLS_BIN" )
TIMEOUT_BIN="$(command -v timeout || true)"
[ -n "$TIMEOUT_BIN" ] && RUNNER=( "$TIMEOUT_BIN" 120 "$OLS_BIN" )
[ -n "$TIMEOUT_BIN" ] || echo "        [warn] timeout 不可用，本项无外层超时保护"

{
    frame "$(msg init.json)";            sleep 6
    frame "$(msg initialized.json)";     sleep 1
    frame "$(msg did_open.json)";        sleep 2
    frame "$(msg document_symbol.json)"; sleep 3
    frame "$(msg shutdown.json)";        sleep 1
    frame "$(msg exit.json)";            sleep 2
} | "${RUNNER[@]}" > "$WORK_DIR/resp.framed" 2> "$ERRLOG"
PIPE_RC=${PIPESTATUS[1]}
tr -d '\r' < "$WORK_DIR/resp.framed" > "$RESP"
printf '        ols rc=%s（0 = 收到 exit 通知后优雅退出；124 = 超时未退出）\n' "$PIPE_RC"

grep -qF '"id": 1, "result": {"capabilities": {' "$RESP" \
    || fail "initialize 响应缺 result.capabilities（见 $RESP）"
for cap in \
    '"definitionProvider": true' \
    '"typeDefinitionProvider": true' \
    '"hoverProvider": true' \
    '"documentSymbolProvider": true' \
    '"documentFormattingProvider": true' \
    '"referencesProvider": true' \
    '"workspaceSymbolProvider": true' \
    '"renameProvider": {"prepareProvider": true}' \
    '"completionProvider": {"resolveProvider": false, "triggerCharacters": [".", ">", "#"' ; do
    grep -qF "$cap" "$RESP" || fail "initialize 能力缺失：$cap"
done
echo "        initialize：result.capabilities + 8 项能力字段断言通过"

grep -qF '"id": 3, "result": [' "$RESP" \
    || fail "documentSymbol 未返回符号数组（见 $RESP）"
grep -qF '{"name": "add", "kind": 12, "range": {"start": {"line": 4, "character": 0}, "end": {"line": 6, "character": 1}}' "$RESP" \
    || fail "documentSymbol 未返回函数符号 add（kind=12, line 4）"
grep -qF '{"name": "main", "kind": 12, "range": {"start": {"line": 8, "character": 0}, "end": {"line": 10, "character": 1}}' "$RESP" \
    || fail "documentSymbol 未返回函数符号 main（kind=12, line 8）"
# 注：符号数组顺序由上游 collector/索引顺序决定，非确定（实测两次运行顺序相反），
#     故两个符号各自独立断言，不断言相对次序。
echo "        documentSymbol：add(line 4) / main(line 8) 两个函数符号断言通过"

grep -qF '{"jsonrpc": "2.0", "id": 2, "result": null}' "$RESP" \
    || fail "shutdown 未返回 {\"id\": 2, \"result\": null}"
if grep -qF 'Failed to find the builtin folder' "$ERRLOG"; then
    fail "运行期未找到 builtin/ 目录（见 $ERRLOG）"
fi
[ "$PIPE_RC" -eq 0 ] || fail "进程未在 exit 通知后优雅退出（rc=$PIPE_RC，124 = 超时）"
echo "        shutdown → {\"id\": 2, \"result\": null}；exit 后 rc=0 优雅退出"

printf '[test] 6/6 全部通过（ols 包根: %s）\n' "$PKG_DIR"
