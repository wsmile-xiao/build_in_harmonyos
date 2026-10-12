#!/bin/sh
# test_package/test.sh — zram-generator 消费者冒烟测试（OHOS 独立 CLI 形态）
# Runs in conanrun env (PATH includes installed bin/)
# Counts each real case and emits the HMBS_TEST_PACKAGE_RESULT marker.
#
# OHOS 适配点（本 run patch/配置引入的平台差异的针对性断言）：
#   case2 断言 --help 内嵌编译期文本 "Uses /usr/lib/systemd/systemd-makefs"——
#   该文本来自 src/setup.rs env!("SYSTEMD_UTIL_DIR")，值由上游 Makefile
#   `export SYSTEMD_UTIL_DIR` 从 make 命令行变量覆盖传入（本 run 零补丁构建
#   路径的实际生效证明）。
#   case3 以 ZRAM_GENERATOR_ROOT 指向临时根走生成器模式（OHOS 无 systemd，
#   独立 CLI 交付形态；rust-ini/liboverdrop/fasteval 配置路径真机执行）。
#   case4 断言设备无内核 zram（/sys/class/zram-control 不存在）时
#   --setup-device 干净报错（exit 1，anyhow 上下文，无 panic）——OHOS 缺
#   内核特性的行为边界记录。
set -u

PASS=0
FAIL=0
BIN=zram-generator

# 可写工作目录（OHOS /tmp 只读：HMBS_TMPDIR/TMPDIR 优先，兜底 $HOME/tmp）
WORK_BASE="${HMBS_TMPDIR:-${TMPDIR:-${TMP:-${TEMP:-$HOME/tmp}}}}"
WORK="$WORK_BASE/zram-smoke"
rm -rf "$WORK"
mkdir -p "$WORK" || { echo "[fail] cannot create work dir $WORK"; exit 1; }

# ── case 1: --version ──
echo "[test] zram-generator --version"
VERSION_OUT=$("$BIN" --version 2>&1)
if printf '%s' "$VERSION_OUT" | grep -q "zram-generator 1.2.1"; then
    PASS=$((PASS + 1))
    echo "[ok] --version prints 'zram-generator 1.2.1'"
else
    FAIL=$((FAIL + 1))
    echo "[fail] --version output unexpected: $VERSION_OUT"
fi

# ── case 2: --help（clap 用法 + 编译期 SYSTEMD_UTIL_DIR 内联文本）──
echo "[test] zram-generator --help"
HELP_OUT=$("$BIN" --help 2>&1)
if printf '%s' "$HELP_OUT" | grep -q -- "--setup-device" \
   && printf '%s' "$HELP_OUT" | grep -q "Uses /usr/lib/systemd/systemd-makefs"; then
    PASS=$((PASS + 1))
    echo "[ok] --help shows usage and compile-time SYSTEMD_UTIL_DIR inline text"
else
    FAIL=$((FAIL + 1))
    echo "[fail] --help output unexpected: $HELP_OUT"
fi

# ── case 3: 生成器模式（OHOS 独立 CLI 交付形态；无需 systemd/内核 zram）──
echo "[test] generator mode writes dev-zram0.swap from a fake root"
ROOT="$WORK/root"
mkdir -p "$ROOT/etc/systemd" "$ROOT/proc" "$ROOT/run/units"
printf '[zram0]\n' > "$ROOT/etc/systemd/zram-generator.conf"
printf 'MemTotal:         801322 kB\nMemFree:          611992 kB\nMemAvailable:     139764 kB\n' > "$ROOT/proc/meminfo"
GEN_OUT=$(ZRAM_GENERATOR_ROOT="$ROOT" "$BIN" "$ROOT/run/units" 2>&1)
GEN_RC=$?
if [ "$GEN_RC" -eq 0 ] && [ -f "$ROOT/run/units/dev-zram0.swap" ] \
   && grep -q "What=/dev/zram0" "$ROOT/run/units/dev-zram0.swap"; then
    PASS=$((PASS + 1))
    echo "[ok] generator mode produced dev-zram0.swap (What=/dev/zram0)"
else
    FAIL=$((FAIL + 1))
    echo "[fail] generator mode rc=$GEN_RC output: $GEN_OUT"
    ls -la "$ROOT/run/units" 2>/dev/null
fi

# ── case 4: 无内核 zram 时 --setup-device 干净报错（平台行为边界）──
echo "[test] --setup-device on a kernel without zram fails cleanly"
SETUP_OUT=$(ZRAM_GENERATOR_ROOT="$ROOT" "$BIN" --setup-device zram0 2>&1)
SETUP_RC=$?
if [ "$SETUP_RC" -ne 0 ] \
   && ! printf '%s' "$SETUP_OUT" | grep -q "panicked"; then
    PASS=$((PASS + 1))
    echo "[ok] --setup-device exits $SETUP_RC with a clean error (no panic): $(printf '%s' "$SETUP_OUT" | head -1)"
else
    FAIL=$((FAIL + 1))
    echo "[fail] --setup-device rc=$SETUP_RC output: $SETUP_OUT"
fi

echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$([ "$FAIL" -eq 0 ] && echo true || echo false),\"command\":\"/bin/sh test.sh\",\"discovered\":4,\"passedCount\":$PASS}"

if [ "$FAIL" -ne 0 ]; then
    echo "[fail] $FAIL case(s) failed, $PASS passed"
    exit 1
fi
echo "[ok] all $PASS test_package cases passed"
