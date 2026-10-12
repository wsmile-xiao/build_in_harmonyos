#!/bin/bash
# rtags 2.44 L1 功能测试（消费者视角 E2E）
# 1) smoke：rc 可执行并报版本；
# 2) 功能：启动 rdm → rc -J 装载 compile_commands.json → libclang 真实索引 → rc -R 引用查询断言。
# 平台说明：OHOS SELinux 禁止 AF_UNIX bind，统一走 TCP 回环（rdm --tcp-port / rc --socket-address）。
set -euo pipefail

BINDIR="${TEST_BINDIR:?TEST_BINDIR not set}"
PROJDIR="${TEST_PROJDIR:?TEST_PROJDIR not set}"
RC="$BINDIR/rc"
RDM="$BINDIR/rdm"

fail() { echo "rtags test FAILED: $*" >&2; exit 1; }

PORT=$((25447 + ($$ % 1000)))
ADDR="127.0.0.1:$PORT"

# 优先用设备签名工具链 clang（conan 缓存内 clang 未签名，OHOS XPM 禁止 exec）
if [ -x /data/service/hnp/bin/clang ]; then
    CLANG=/data/service/hnp/bin/clang
else
    CLANG="$(command -v clang)" || fail "clang not found"
fi

# 0) 准备测试工程与 compile_commands.json（rc -J 依赖）
mkdir -p "$PROJDIR"
cat > "$PROJDIR/test_project.c" <<'EOF'
int rtags_test_add(int a, int b) { return a + b; }
int main(void) { return rtags_test_add(1, 2) == 3 ? 0 : 1; }
EOF
printf '[{"directory": "%s", "arguments": ["%s", "-c", "test_project.c"], "file": "test_project.c"}]\n' \
    "$PROJDIR" "$CLANG" > "$PROJDIR/compile_commands.json"

# 1) smoke：版本输出
"$RC" --version || fail "rc --version failed"

# 2) 启动 rdm（TCP 回环）
"$RDM" --tcp-port "$PORT" --data-dir="$PROJDIR/.rtags" --silent -L "$PROJDIR/rdm.log" -vvvv &
RDM_PID=$!
cleanup() { kill "$RDM_PID" 2>/dev/null || true; wait "$RDM_PID" 2>/dev/null || true; }
trap cleanup EXIT

# 3) 等待 rdm 可达
READY=0
for _ in $(seq 1 30); do
    if "$RC" --socket-address "$ADDR" --current-project >/dev/null 2>&1; then READY=1; break; fi
    sleep 1
done
[ "$READY" = 1 ] || fail "rdm did not become reachable within 30s"

# 4) 设置当前工程并装载 compile_commands.json（libclang 真实解析索引）
"$RC" --socket-address "$ADDR" -w "$PROJDIR" || fail "rc -w failed"
"$RC" --socket-address "$ADDR" -J "$PROJDIR" || fail "rc -J failed"

# 5) 等待索引完成
for _ in $(seq 1 60); do
    "$RC" --socket-address "$ADDR" -T "$PROJDIR/test_project.c" >/dev/null 2>&1 && break
    sleep 1
done
"$RC" --socket-address "$ADDR" -T "$PROJDIR/test_project.c" >/dev/null 2>&1 \
    || fail "indexing did not finish"

# 6) 查询符号引用（libclang 解析结果入库验证）
OUT=""
# rdm 索引入库是异步的：-T 通过后偶发出现 -R 查询过早返回空/非零的竞态，
# 重试最多 10 次消除偶发失败
for _ in $(seq 1 10); do
    if OUT="$("$RC" --socket-address "$ADDR" -R rtags_test_add 2>&1)" \
        && echo "$OUT" | grep -q "test_project.c"; then
        break
    fi
    OUT=""
    sleep 1
done
echo "$OUT" | grep -q "test_project.c" || fail "no references found: ${OUT:-<empty>}"

echo "rtags functional test passed: index + reference query OK"
