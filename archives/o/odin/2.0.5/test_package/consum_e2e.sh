#!/usr/bin/env bash
# test_package/consum_e2e.sh — rule12 鸿蒙消费者端到端用例（设备侧可复现）
#
# 用法: consum_e2e.sh <odin_bin> <odin_root> <work_dir>
#
# 与 run_tests.sh（3 项冒烟）互补：本脚本执行「消费者视角的完整闭环」，
# 每一步都真编译、真运行、真检查产物输出与退出码，非纯静态断言。
set -uo pipefail
ODIN_BIN="${1:?odin 二进制路径}"
ODIN_ROOT_DIR="${2:?ODIN_ROOT}"
WORK_DIR="${3:?工作目录}"

export ODIN_ROOT="$ODIN_ROOT_DIR"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR" || exit 1

PASS=0
FAIL=0
check() { # check <ok:0|1> <name>
    if [ "$1" -eq 0 ]; then
        echo "[PASS] $2"; PASS=$((PASS + 1))
    else
        echo "[FAIL] $2"; FAIL=$((FAIL + 1))
    fi
}

echo "=== odin 消费者端到端用例（rule12）==="

# ── C1 编译器自省：version 报出登记版本 ────────────────────────────────
V="$("$ODIN_BIN" version 2>&1)"
echo "     version = $V"
case "$V" in *dev-2026-08*) check 0 "C1 version contains dev-2026-08" ;;
               *)            check 1 "C1 version contains dev-2026-08" ;; esac

# ── C2 端到端：编译单文件 → 运行 → 检查输出 ──────────────────────────
cat > c2_hello.odin <<'EOF'
package main
import "core:fmt"
main :: proc() { fmt.println("E2E_OK_C2") }
EOF
if "$ODIN_BIN" build c2_hello.odin -file -out:c2_hello >c2_build.log 2>&1; then
    check 0 "C2a odin build single file"
    OUT="$(./c2_hello 2>&1)"
    echo "     output = $OUT"
    case "$OUT" in *E2E_OK_C2*) check 0 "C2b compiled binary runs and prints" ;;
                   *)           check 1 "C2b compiled binary runs and prints" ;; esac
else
    check 1 "C2a odin build single file"; echo "--- build log ---"; tail -20 c2_build.log
    check 1 "C2b compiled binary runs and prints"
fi

# ── C3 退出码契约：Odin exit(3) 须原样透传到宿主 ───────────────────────
cat > c3_exit.odin <<'EOF'
package main
import "core:os"
main :: proc() { os.exit(3) }
EOF
if "$ODIN_BIN" build c3_exit.odin -file -out:c3_exit >c3_build.log 2>&1; then
    check 0 "C3a odin build exit-code program"
    ./c3_exit >/dev/null 2>&1
    RC=$?
    echo "     exit code = $RC (expect 3)"
    [ "$RC" -eq 3 ]; check $? "C3b os.exit(3) propagates to host"
else
    check 1 "C3a odin build exit-code program"; echo "--- build log ---"; tail -20 c3_build.log
    check 1 "C3b os.exit(3) propagates to host"
fi

# ── C4 跨模块 import：编译期多包解析 + 运行结果 ───────────────────────
mkdir -p c4pkg
cat > c4pkg/lib.odin <<'EOF'
package c4pkg
LIB_VALUE :: 21
Double :: proc(x: int) -> int { return x * 2 }
EOF
cat > c4_main.odin <<'EOF'
package main
import "core:fmt"
import "c4pkg"
main :: proc() { fmt.printf("LIB=%v\n", c4pkg.Double(c4pkg.LIB_VALUE)) }
EOF
# Odin 要求 import 路径可解析：用 -collection 把工作目录挂成集合
if "$ODIN_BIN" build c4_main.odin -file -collection:c4pkg="$WORK_DIR/c4pkg" \
        -out:c4_app >c4_build.log 2>&1; then
    check 0 "C4a odin build multi-module import"
    OUT4="$(./c4_app 2>&1)"
    echo "     output = $OUT4"
    case "$OUT4" in *LIB=42*) check 0 "C4b cross-module call returns 42" ;;
                   *)         check 1 "C4b cross-module call returns 42" ;; esac
else
    check 1 "C4a odin build multi-module import"; echo "--- build log ---"; tail -20 c4_build.log
    check 1 "C4b cross-module call returns 42"
fi

# ── C5 运行时库完整性：base/core 目录须随包可用 ───────────────────────
[ -d "$ODIN_ROOT_DIR/core" ] && [ -d "$ODIN_ROOT_DIR/base" ]
check $? "C5 packaged runtime dirs base/ + core/ present"

echo
echo "=== E2E RESULT: pass=$PASS fail=$FAIL ==="
if [ "$FAIL" -ne 0 ]; then
    echo "E2E_VERDICT=FAIL"
    exit 1
fi
echo "E2E_VERDICT=PASS"
exit 0
