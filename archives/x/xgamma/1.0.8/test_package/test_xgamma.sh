#!/bin/sh
# test_xgamma.sh — verify xgamma binary works on HarmonyOS PC (headless, no X server)
# Called by test_package/conanfile.py test() with:
#   $1 = absolute path to the packaged xgamma binary
#   $2 = optional colon-joined LD_PRELOAD list of runtime .so paths
#        (xgamma links libXxf86vm + libX11 whose DT_NEEDED closure — libXext,
#         libxcb, libXau, libXdmcp — must resolve at load time;
#         HMBS [stale_runtime_library]: loader may ignore LD_LIBRARY_PATH, so
#         the recipe passes absolute paths to preload as a fallback).
#
# POSIX sh only (HMBS [shell_getcwd]: run with injected SHELL=/bin/sh; xev/xeyes
# already-passed tests use the same pattern). No set -e/-u/pipefail: toybox ash
# rejects them; every assertion captures its own rc and always prints output so
# loader errors hit the log.
#
# ── 安全红线（本包特有）────────────────────────────────────────────
# xgamma 会修改真机 X server 的 gamma。构建机就是用户在用的机器，绝不允许留下
# 被改掉的显示状态。因此本脚本 9 条断言逐条对照 xgamma.c 的行号保证不写 gamma：
#   1..2  -version/--version : 第 126-129 行 puts(PACKAGE_STRING); exit(EXIT_SUCCESS)
#   3     -help              : 第 130-132 行 Syntax(NULL, EXIT_SUCCESS) -> exit
#   4     非法选项           : 第 190-198 行 unrecognized argument -> Syntax(...,1)
#   5..6  gamma 取值域校验   : 第 144-149 行 GAMMA_MIN/GAMMA_MAX 越界 -> exit(1)
#   7     -gamma 与 -rgamma  : 第 154-155 行互斥 -> Syntax(...,1)
#   8     -gamma 缺参数      : 第 139-140 行 -> Syntax(...,1)
#   以上 8 条全部发生在第 202 行 XOpenDisplay() 之前：进程根本不连 X server。
#   9     裸 xgamma（无 gamma 选项）：走第 245-249 行
#       else { /* Not changing gamma, all done */ ret = EXIT_SUCCESS; goto finish; }
#       ——源码可证 **只 XF86VidModeGetGamma 读、永不调用 XF86VidModeSetGamma**。
#       本条仅在本机确认无可达 X server 时执行（断言上游错误串 + 非 0 退出）；
#       若存在可达 display 则记为 skipped（不猜服务端扩展状态），任何情况下都不会写 gamma。
# ──────────────────────────────────────────────────────────────────
# 无头环境可断言的正是 XOpenDisplay 失败分支（第 202-205 行）：
#   fprintf (stderr, "%s:  unable to open display '%s'\n", ProgramName, XDisplayName (displayname))

XGAMMA_BIN="$1"
LD_PRELOAD_EXTRA="${2:-}"

if [ -z "$XGAMMA_BIN" ]; then
    echo "FAIL: xgamma binary path not provided"
    exit 1
fi

if [ ! -x "$XGAMMA_BIN" ]; then
    echo "FAIL: $XGAMMA_BIN not found or not executable"
    exit 1
fi

BIN_DIR=$(dirname "$XGAMMA_BIN")
export LD_LIBRARY_PATH="${BIN_DIR}:${LD_LIBRARY_PATH:-}"

if [ -n "$LD_PRELOAD_EXTRA" ]; then
    export LD_PRELOAD="$LD_PRELOAD_EXTRA"
fi

echo "[shell] $0"
echo "[env] PATH=$PATH"
echo "[env] LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "[env] LD_PRELOAD=${LD_PRELOAD:-}"
echo "[env] DISPLAY=${DISPLAY-<unset>}"

# 可达 X server 探测（只为决定第 9 条跑还是 skip；跑的那 8 条与 display 无关）
X_REACHABLE=0
if [ -n "${DISPLAY-}" ]; then
    X_REACHABLE=1
fi
for _s in /tmp/.X11-unix/X*; do
    if [ -e "$_s" ]; then
        X_REACHABLE=1
    fi
done
if [ "$X_REACHABLE" -eq 1 ]; then
    echo "[note] reachable X server detected -> case 9 will be SKIPPED (never a gamma write)"
fi

discovered=9
passed=0
skipped=0

# 诊断：ldd 打印每个 DT_NEEDED 的解析结果，缺库一目了然
if command -v ldd >/dev/null 2>&1; then
    echo "[ldd]"
    ldd "$XGAMMA_BIN" 2>&1 || true
fi

# --- test 1: xgamma -version (xgamma.c:126-129 puts(PACKAGE_STRING); exit(0)) ---
echo "[test 1/$discovered] xgamma -version"
out=$("$XGAMMA_BIN" -version 2>&1)
rc=$?
echo "$out"
if [ $rc -ne 0 ]; then
    echo "FAIL: xgamma -version exit=$rc (expected 0)"
elif echo "$out" | grep -q "xgamma 1.0.8"; then
    echo "PASS: xgamma -version reports 'xgamma 1.0.8' (exit 0)"
    passed=$((passed + 1))
else
    echo "FAIL: xgamma -version unexpected output (no 'xgamma 1.0.8')"
fi

# --- test 2: xgamma --version (xgamma.c:127 explicit !strcmp("--version", arg)) ---
echo "[test 2/$discovered] xgamma --version"
out=$("$XGAMMA_BIN" --version 2>&1)
rc=$?
echo "$out"
if [ $rc -ne 0 ]; then
    echo "FAIL: xgamma --version exit=$rc (expected 0)"
elif echo "$out" | grep -q "xgamma 1.0.8"; then
    echo "PASS: xgamma --version reports 'xgamma 1.0.8' (exit 0)"
    passed=$((passed + 1))
else
    echo "FAIL: xgamma --version unexpected output (no 'xgamma 1.0.8')"
fi

# --- test 3: xgamma -help (xgamma.c:130-132 Syntax(NULL, EXIT_SUCCESS)) ---
# Syntax() 打印 "usage:  %s [-options]" 与选项表到 stderr，exit 0。
echo "[test 3/$discovered] xgamma -help"
out=$("$XGAMMA_BIN" -help 2>&1)
rc=$?
echo "$out" | head -20
if [ $rc -ne 0 ]; then
    echo "FAIL: xgamma -help exit=$rc (expected 0)"
elif echo "$out" | grep -qi "usage:"; then
    echo "PASS: xgamma -help prints usage banner (exit 0)"
    passed=$((passed + 1))
else
    echo "FAIL: xgamma -help missing usage banner"
fi

# --- test 4: 非法选项 (xgamma.c:190-193 unrecognized argument -> Syntax(NULL,1)) ---
echo "[test 4/$discovered] xgamma -nosuchopt (unrecognized argument -> nonzero)"
out=$("$XGAMMA_BIN" -nosuchopt 2>&1)
rc=$?
echo "$out" | head -20
if [ $rc -eq 0 ]; then
    echo "FAIL: xgamma -nosuchopt exit=0 (expected nonzero)"
elif echo "$out" | grep -q "unrecognized argument"; then
    echo "PASS: xgamma -nosuchopt rejected with 'unrecognized argument' (rc=$rc)"
    passed=$((passed + 1))
else
    echo "FAIL: xgamma -nosuchopt nonzero but no 'unrecognized argument' line (rc=$rc)"
fi

# --- test 5: gamma 下界校验 (xgamma.c:144-149, GAMMA_MIN 0.1f) ---
# 核心领域逻辑：-gamma 0.05 低于 GAMMA_MIN，必须被拒且发生在连 X server 之前。
echo "[test 5/$discovered] xgamma -gamma 0.05 (below GAMMA_MIN -> rejected)"
out=$("$XGAMMA_BIN" -gamma 0.05 2>&1)
rc=$?
echo "$out" | head -5
if [ $rc -eq 0 ]; then
    echo "FAIL: xgamma -gamma 0.05 exit=0 (expected nonzero, GAMMA_MIN=0.1)"
elif echo "$out" | grep -q "Gamma values must be between"; then
    if echo "$out" | grep -q "0.100" && echo "$out" | grep -q "10.000"; then
        echo "PASS: xgamma -gamma 0.05 rejected, bounds printed 0.100..10.000 (rc=$rc)"
        passed=$((passed + 1))
    else
        echo "FAIL: rejected but bounds text missing (expected 0.100 / 10.000)"
    fi
else
    echo "FAIL: xgamma -gamma 0.05 nonzero but no range-error line (rc=$rc)"
fi

# --- test 6: gamma 上界校验 (xgamma.c:144-149, GAMMA_MAX 10.0f) ---
echo "[test 6/$discovered] xgamma -gamma 99.0 (above GAMMA_MAX -> rejected)"
out=$("$XGAMMA_BIN" -gamma 99.0 2>&1)
rc=$?
echo "$out" | head -5
if [ $rc -eq 0 ]; then
    echo "FAIL: xgamma -gamma 99.0 exit=0 (expected nonzero, GAMMA_MAX=10.0)"
elif echo "$out" | grep -q "Gamma values must be between"; then
    echo "PASS: xgamma -gamma 99.0 rejected by GAMMA_MAX check (rc=$rc)"
    passed=$((passed + 1))
else
    echo "FAIL: xgamma -gamma 99.0 nonzero but no range-error line (rc=$rc)"
fi

# --- test 7: -gamma 与 -rgamma 互斥 (xgamma.c:154-155) ---
echo "[test 7/$discovered] xgamma -gamma 1.0 -rgamma 1.0 (mutual exclusion)"
out=$("$XGAMMA_BIN" -gamma 1.0 -rgamma 1.0 2>&1)
rc=$?
echo "$out" | head -5
if [ $rc -eq 0 ]; then
    echo "FAIL: combined -gamma/-rgamma exit=0 (expected nonzero)"
elif echo "$out" | grep -q "cannot set both -gamma and -rgamma"; then
    echo "PASS: -gamma with -rgamma rejected by mutual-exclusion check (rc=$rc)"
    passed=$((passed + 1))
else
    echo "FAIL: nonzero but no mutual-exclusion line (rc=$rc)"
fi

# --- test 8: -gamma 缺参数 (xgamma.c:139-140) ---
echo "[test 8/$discovered] xgamma -gamma (missing argument -> Syntax failure)"
out=$("$XGAMMA_BIN" -gamma 2>&1)
rc=$?
echo "$out" | head -5
if [ $rc -eq 0 ]; then
    echo "FAIL: xgamma -gamma (no arg) exit=0 (expected nonzero)"
elif echo "$out" | grep -q "requires an argument"; then
    echo "PASS: xgamma -gamma without value rejected (rc=$rc)"
    passed=$((passed + 1))
else
    echo "FAIL: nonzero but no 'requires an argument' line (rc=$rc)"
fi

# --- test 9: 只读查询路径 (xgamma.c:202-205 + 245-249，永不 SetGamma) ---
if [ "$X_REACHABLE" -eq 1 ]; then
    echo "[test 9/$discovered] SKIPPED: reachable X server; server-side query result"
    echo "  depends on XFree86-VidModeExtension availability (assertion would be"
    echo "  non-deterministic). Bare xgamma is read-only by source (lines 245-249),"
    echo "  so no gamma write risk exists either way."
    skipped=$((skipped + 1))
else
    echo "[test 9/$discovered] xgamma (bare, read-only query path, no X server)"
    out=$("$XGAMMA_BIN" 2>&1)
    rc=$?
    echo "$out" | head -5
    if [ $rc -eq 0 ]; then
        echo "FAIL: bare xgamma exit=0 without any X server"
    elif echo "$out" | grep -q "unable to open display"; then
        echo "PASS: bare xgamma reaches XOpenDisplay and reports upstream"
        echo "      'unable to open display' (rc=$rc); gamma never written"
        passed=$((passed + 1))
    else
        echo "FAIL: bare xgamma nonzero but no 'unable to open display' line (rc=$rc)"
    fi
fi

# 判定：failed = discovered - passed - skipped（skipped 不算通过，也不算失败）
failed=$((discovered - passed - skipped))
echo "[summary] discovered=$discovered passed=$passed skipped=$skipped failed=$failed"

if [ "$failed" -ne 0 ]; then
    echo "FAIL: $failed/$discovered checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_xgamma.sh","discovered":%d,"passedCount":%d,"skipped":%d}\n' \
        "$discovered" "$passed" "$skipped"
    exit 1
fi

echo "OK: $passed/$discovered checks passed, $skipped skipped (no X server path)"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_xgamma.sh","discovered":%d,"passedCount":%d,"skipped":%d}\n' \
    "$discovered" "$passed" "$skipped"
