#!/usr/bin/env bash
# test_package/test_qastools.sh — qastools 1.4.0 消费者测试
#
# 真实 exec 被测包安装的三个 Qt6/ALSA GUI 可执行文件（L0c 测试源 / L0d self.run /
# R34 实质依赖被测包），断言落在被测二进制的真实进程输出上。
#
# 上游命令行契约（源码级核对，v1.4.0）：
#   * 三个程序都在 main() 进入 Qt 事件循环之前处理 --version / --help
#     （各程序 src/desktop_items.cpp::parse_cmd_options），故 headless 下可安全断言。
#   * qasmixer --version 打印 "qasmixer 1.4.0" 后 parse_cmd_options `return -1`，
#     main.cpp:34-37 `if (res < 0) return res;` → 进程以 255 退出，**不进入事件循环**
#     → 退出码可硬断言。
#   * qashctl / qasconfig 同样打印版本号，但上游 main.cpp:27-30 / 24-27 写的是
#     `if (res < ditems.init_settings (argc, argv))` —— 二次调用 init_settings 后比较
#     `-1 < -1` 为假，条件落空，程序继续进入 app.exec()。故这两个进程打印版本号后
#     由 timeout 杀掉（rc=124）→ 只能对 stdout 的版本串断言，不能约束退出码。
#     （上游缺陷，本 PR 不改源码，如实记录。）
#
# 无头环境：QT_QPA_PLATFORM=offscreen（conducteo/acetoneiso/diffpdf/marknote 先例）。
# libc++_shared.so 位于 OHOS SDK 的**按架构分层** llvm lib 目录，而 CI profile 的
# buildenv 只前置了 llvm/lib（不含架构层），故此处补齐（conducteo 同款处置）。
# SDK 版本用通配符发现，避免 worker 升 SDK 后静默跳过。
#
# 用法: test_qastools.sh <bin-dir>      （由 test_package/conanfile.py 调用）
set -euo pipefail

BIN_DIR="${1:-}"
if [ -z "$BIN_DIR" ] || [ ! -d "$BIN_DIR" ]; then
    echo "[fail] usage: $0 <bin-dir>   (got: '${1:-}')" >&2
    exit 2
fi

# ── 运行环境准备 ────────────────────────────────────────────────────
# D15：OHOS aarch64 的 /tmp 只读，临时文件一律落 $HOME/tmp 并先建目录。
if [ -z "${TMPDIR:-}" ]; then
    export TMPDIR="${HOME}/tmp"
    mkdir -p "$TMPDIR"
fi

# libc++_shared.so：按架构分层的 SDK llvm lib 目录（可用 OHOS_SDK_LLVM_LIB 覆盖）。
if [ -z "${OHOS_SDK_LLVM_LIB:-}" ]; then
    for _d in /data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib/aarch64-linux-ohos; do
        if [ -d "$_d" ]; then
            OHOS_SDK_LLVM_LIB="$_d"
        fi
    done
fi
if [ -n "${OHOS_SDK_LLVM_LIB:-}" ] && [ -d "$OHOS_SDK_LLVM_LIB" ]; then
    export LD_LIBRARY_PATH="$OHOS_SDK_LLVM_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
    echo "[ok]   SDK per-arch llvm lib prepended: $OHOS_SDK_LLVM_LIB"
else
    echo "[warn] SDK per-arch llvm lib not discovered; libc++_shared.so may be unresolvable"
fi

export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
echo "[ok]   QT_QPA_PLATFORM=$QT_QPA_PLATFORM"
echo "[ok]   TMPDIR=$TMPDIR"

RUN_TIMEOUT="${QASTOOLS_TEST_TIMEOUT:-15}"
PASS=0
FAIL=0
OUT=""
RC=0

ok()   { echo "[ok]   $*"; PASS=$((PASS + 1)); }
bad()  { echo "[fail] $*"; FAIL=$((FAIL + 1)); }

# 期望非零退出的调用统一走这里：set -e 会因命令替换非零而中止，故显式关/开。
run_cli() {
    set +e
    OUT=$(timeout "$RUN_TIMEOUT" "$@" 2>&1)
    RC=$?
    set -e
}

# 纯 bash 读 ELF 魔数（不依赖 file/od/dd —— OHOS CI 的 coreutils 覆盖不稳定）
elf_magic() {
    local magic=""
    if ! IFS= read -r -n 4 magic < "$1"; then
        magic=""
    fi
    [ "$magic" = $'\177ELF' ]
}

# 失败时给出可定位的诊断，避免下一轮只能看到"红"
diagnose() {
    case "$1" in
        *"Error loading shared library"*|*"cannot open shared object file"*)
            echo "       hint: 动态链接闭包不完整——核对 conanrun 的 LD_LIBRARY_PATH 是否覆盖 Qt6 各 .so" ;;
        *"failed to start because no Qt platform plugin"*|*"could not load the Qt platform plugin"*)
            echo "       hint: Qt 平台插件缺失——确认制品仓 qtbase-sql-dbus 变体带 offscreen 插件" ;;
        *"Permission denied"*)
            echo "       hint: HMDFS 上 exec 权限受限——参考 archives/f/fceux/2.6.6 配方：拷到可写 TMPDIR 后自签再 exec" ;;
    esac
}

# ── 1. 三个可执行文件存在、可执行、是 ELF ──────────────────────────
echo "[step] installed executables"
for name in qasmixer qashctl qasconfig; do
    bin="$BIN_DIR/$name"
    if [ ! -f "$bin" ]; then
        bad "$name missing: $bin"
        continue
    fi
    ok "$name installed"
    if [ -x "$bin" ]; then
        ok "$name executable bit"
    else
        bad "$name not executable"
    fi
    if elf_magic "$bin"; then
        ok "$name ELF magic"
    else
        bad "$name not an ELF object"
    fi
done

# ── 2. qasmixer --version：打印版本号后以 255 退出，不进事件循环 ─────
echo "[step] qasmixer --version (expect 'qasmixer 1.4.0' + exit 255)"
if [ -x "$BIN_DIR/qasmixer" ]; then
    run_cli "$BIN_DIR/qasmixer" --version
    echo "$OUT"
    echo "[info] qasmixer --version rc=$RC"
    case "$OUT" in
        *"qasmixer 1.4.0"*)
            if [ "$RC" -eq 255 ]; then
                ok "qasmixer --version reports 1.4.0 and exits 255 (no event loop)"
            elif [ "$RC" -eq 124 ]; then
                bad "qasmixer --version printed the banner but never terminated (timeout ${RUN_TIMEOUT}s)"
            else
                bad "qasmixer --version reported 1.4.0 but unexpected rc=$RC"
            fi
            ;;
        *)
            bad "qasmixer --version output does not contain 'qasmixer 1.4.0'"
            diagnose "$OUT"
            ;;
    esac
fi

# ── 3. qasmixer --help：Usage 横幅后同样 return -1 ──────────────────
echo "[step] qasmixer --help (expect 'Usage:' + exit 255)"
if [ -x "$BIN_DIR/qasmixer" ]; then
    run_cli "$BIN_DIR/qasmixer" --help
    echo "$OUT" | head -n 20
    echo "[info] qasmixer --help rc=$RC"
    case "$OUT" in
        *"Usage:"*)
            if [ "$RC" -eq 255 ]; then
                ok "qasmixer --help prints Usage and exits 255"
            elif [ "$RC" -eq 124 ]; then
                bad "qasmixer --help printed Usage but never terminated"
            else
                bad "qasmixer --help printed Usage but unexpected rc=$RC"
            fi
            ;;
        *)
            bad "qasmixer --help output does not contain 'Usage:'"
            diagnose "$OUT"
            ;;
    esac
fi

# ── 4. qashctl / qasconfig --version：上游条件落空进事件循环，rc=124 属预期，
#       断言只落在 stdout 的版本串上（见文件头契约说明）────────────────
for name in qashctl qasconfig; do
    echo "[step] $name --version (expect '$name 1.4.0' on stdout; rc=124 tolerated)"
    bin="$BIN_DIR/$name"
    if [ -x "$bin" ]; then
        run_cli "$bin" --version
        echo "$OUT" | head -n 20
        echo "[info] $name --version rc=$RC (124 = 事件循环被 timeout 杀掉，上游预期)"
        case "$OUT" in
            *"$name 1.4.0"*) ok "$name --version reports 1.4.0" ;;
            *)
                bad "$name --version output does not contain '$name 1.4.0'"
                diagnose "$OUT"
                ;;
        esac
    fi
done

TOTAL=$((PASS + FAIL))
echo ""
echo "RESULT: $PASS passed, $FAIL failed"
if [ "$TOTAL" -eq 0 ]; then
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"test_qastools.sh\",\"discovered\":0,\"passedCount\":0}"
    echo "test_qastools.sh: no case executed — harness broken" >&2
    exit 1
fi
if [ "$FAIL" -eq 0 ]; then
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"test_qastools.sh\",\"discovered\":$TOTAL,\"passedCount\":$PASS}"
    exit 0
fi
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"test_qastools.sh\",\"discovered\":$TOTAL,\"passedCount\":$PASS}"
exit 1
