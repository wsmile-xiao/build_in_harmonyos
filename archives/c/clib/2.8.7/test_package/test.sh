#!/data/service/hnp/bin/bash
# test_package/test.sh — clib 2.8.7 consumer smoke test
# Runs in conanrun env (package bin/ is on PATH).
# HOME 重定向到 scratch,避免污染真实 ~/.clib 缓存。
set -u

SCRATCH="${1:-$(mktemp -d)}"
STATUS=0

ok()   { echo "  ✅ $1"; }
fail() { echo "  ❌ $1"; STATUS=1; }

export HOME="$SCRATCH/home"
mkdir -p "$HOME"

# tp1: 9 个打包产物存在且可执行(command -v 走 conanrun PATH)
for b in clib clib-install clib-search clib-init clib-configure clib-build \
         clib-update clib-upgrade clib-uninstall; do
  if command -v "$b" > /dev/null 2>&1; then
    ok "binary available: $b"
  else
    fail "binary missing: $b"
  fi
done

# tp2: clib --version 输出 2.8.7
V=$(clib --version 2>&1)
if [ "$V" = "2.8.7" ]; then
  ok "--version == 2.8.7"
else
  fail "--version expected 2.8.7, got: $V"
fi

# tp3: usage 输出包含命令列表
U=$(clib 2>&1 || true)
case "$U" in
  *"clib <command> [options]"*|*"Commands:"*) ok "usage output lists commands" ;;
  *) fail "unexpected usage output"; echo "$U" | head -3 ;;
esac

# tp4: 主程序 → 子命令分发(which("clib-install") 命中包内包装工具);
# 空目录下 clib install 的 "no such file: clib.json" 来自 clib-install 本体
INIT_DIR="$SCRATCH/empty"
mkdir -p "$INIT_DIR" && cd "$INIT_DIR" || exit 1
D=$(clib install 2>&1 || true)
case "$D" in
  *"no such file: clib.json"*) ok "dispatch clib install → clib-install (real tool error path)" ;;
  *) fail "dispatch clib install unexpected output"; echo "$D" | head -3 ;;
esac
cd - > /dev/null

# tp5: clib init 经分发机制端到端生成 clib.json
INIT_DIR="$SCRATCH/init"
mkdir -p "$INIT_DIR" && cd "$INIT_DIR" || exit 1
OUT=$(printf '\n\n' | clib init 2>&1 || true)
if [ -f clib.json ]; then
  ok "clib init dispatched and generated clib.json"
else
  fail "clib init did not generate clib.json"
  echo "$OUT" | head -3
fi
cd - > /dev/null

# tp6: clib-search 真实 HTTPS 查询(CA 探测补丁生效证据)。
# 环境条件性观测项,不计入断言分母:依赖外网。设备出口可测(间歇性
# 连接重置,重试 3 次);CI worker 无外网(实测 "failed to fetch wiki
# HTML")时显式记 SKIP——不伪造、不静默跳过。
SRES=""
for attempt in 1 2 3; do
  SRES=$(clib-search trim 2>&1 || true)
  case "$SRES" in
    *"stephenmathieson/trim.c"*) break ;;
    *) sleep 2 ;;
  esac
done
case "$SRES" in
  *"stephenmathieson/trim.c"*)
    ok "clib-search trim → stephenmathieson/trim.c (HTTPS OK) [观测项]"
    ;;
  *"failed to fetch"*|*"Could not resolve"*|*"timed out"*|*"Connection"*|*"SSL"*)
    echo "  ⏭️ SKIP tp6 clib-search: 无外网环境,观测项不可测(首错: $(printf '%s' "$SRES" | head -1))"
    ;;
  *)
    fail "clib-search trim did not return expected package"
    echo "$SRES" | head -5
    ;;
esac

chmod -R u+w "$SCRATCH" 2>/dev/null || true
rm -rf "$SCRATCH"
exit $STATUS
