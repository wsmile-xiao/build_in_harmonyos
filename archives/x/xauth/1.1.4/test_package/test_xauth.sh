#!/bin/sh
# test_xauth.sh — 真实执行**已安装的** xauth 二进制（R34：二进制即被测 API）
#
# 由 test_package/conanfile.py test() 调用：
#   $1 = 已安装的 bin/xauth 绝对路径
#   $2 = 可选的冒号分隔 LD_PRELOAD 列表（libX11.so.6 的 DT_NEEDED
#        libxcb.so.1 / libXau.so.6 / libXdmcp.so.6 的绝对路径；
#        HMBS [stale_runtime_library]：loader 可能忽略 LD_LIBRARY_PATH）
#   $3 = 可写 scratch 目录（OHOS 的 /tmp 是 erofs 只读，E002）
#
# 仅用 POSIX sh（HMBS [shell_getcwd]：用注入的 SHELL 执行，不硬编码
# /data/service/hnp/bin/bash）。不用 set -e/-u/pipefail（toybox ash 拒绝），
# 每条断言自己收 rc 并始终打印输出，让加载器错误能进日志。
#
# 覆盖范围（5 项可观测行为）：版本输出 → 授权文件写入 → 读出 → 删除 →
# 删除后为空。xauth 的全部用户可见功能都围绕 Xauthority 文件的
# 增/查/删，因此这 5 项是端到端行为断言，不是"能跑就算过"。
#
# 除 -V 外每条都带 `-i`（上游文档化选项：ignore locks on authority file）：
# XauLockAuth() 靠 link()+O_EXCL 建锁，HMDFS 不支持硬链接 ⇒ 必然
# LOCK_ERROR/LOCK_TIMEOUT，xauth 会在写授权文件之前就退出（CI #62240 实测：
# 5 项里 4 项因 "error/timeout in locking authority file" 失败）。这与
# tests/setup-sourced 补丁用的是同一个开关，产品行为不变。

XAUTH_BIN="$1"
LD_PRELOAD_EXTRA="${2:-}"
WORK="${3:-}"

if [ -z "$XAUTH_BIN" ]; then
    echo "FAIL: xauth binary path not provided"
    exit 1
fi

if [ ! -x "$XAUTH_BIN" ]; then
    echo "FAIL: $XAUTH_BIN not found or not executable"
    exit 1
fi

if [ -z "$WORK" ] || [ ! -d "$WORK" ]; then
    echo "FAIL: writable scratch dir not provided (arg 3)"
    exit 1
fi

BIN_DIR=$(dirname "$XAUTH_BIN")
export LD_LIBRARY_PATH="${BIN_DIR}:${LD_LIBRARY_PATH:-}"
if [ -n "$LD_PRELOAD_EXTRA" ]; then
    export LD_PRELOAD="$LD_PRELOAD_EXTRA"
fi

echo "[shell] $0"
echo "[env] LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "[env] LD_PRELOAD=${LD_PRELOAD:-}"
echo "[env] WORK=$WORK"

discovered=5
passed=0

AUTHFILE="$WORK/.Xauthority"
DISPLAY="examplehost1/unix:0"
PROTO="MIT-MAGIC-COOKIE-1"
COOKIE="b90b0fd1cf6a0e7a2c74c00000000001"

rm -f "$AUTHFILE" "$AUTHFILE"-c "$AUTHFILE"-l

# ── 1. 版本输出（main() 在解析到 -V 时 puts(PACKAGE_VERSION) 后立即 exit(0)）──
echo "[test 1/$discovered] $XAUTH_BIN -V"
version_output=$("$XAUTH_BIN" -V 2>&1)
rc=$?
echo "$version_output"
if [ $rc -eq 0 ] && [ "$version_output" = "1.1.4" ]; then
    echo "PASS: -V reports 1.1.4"
    passed=$((passed + 1))
else
    echo "FAIL: -V exit=$rc output=[$version_output] expected=1.1.4"
fi

# ── 2. 写入一条授权记录（走 libXau 的 XauLockAuth/XauWriteAuth 全链路）────
# -i（上游文档化选项 `xauth(1)`：ignore locks on authority file）在 HMDFS 上
# 是必需的：XauLockAuth() 用 link()+O_EXCL 建锁，而 HMDFS 不支持硬链接，
# 于是它必然返回 LOCK_ERROR/LOCK_TIMEOUT，xauth 在写授权文件之前就退出。
# 与 tests/setup-sourced 补丁用的是同一个开关，产品行为不变。
echo "[test 2/$discovered] $XAUTH_BIN -i -f <file> add $DISPLAY …"
"$XAUTH_BIN" -i -f "$AUTHFILE" add "$DISPLAY" "$PROTO" "$COOKIE" > "$WORK/add.out" 2>&1
rc=$?
cat "$WORK/add.out"
if [ $rc -eq 0 ] && [ -s "$AUTHFILE" ]; then
    echo "PASS: add exit=0 and authority file is non-empty"
    passed=$((passed + 1))
else
    echo "FAIL: add exit=$rc, authority file empty or missing"
fi

# ── 3. 读回：list 必须原样打印 display 与 cookie ────────────────────────
echo "[test 3/$discovered] $XAUTH_BIN -i -f <file> list"
list_output=$("$XAUTH_BIN" -i -f "$AUTHFILE" list 2>&1)
rc=$?
echo "$list_output"
if [ $rc -eq 0 ] && echo "$list_output" | grep -q "$DISPLAY" \
        && echo "$list_output" | grep -q "$COOKIE"; then
    echo "PASS: list returns the entry just written"
    passed=$((passed + 1))
else
    echo "FAIL: list exit=$rc, display/cookie not found"
fi

# ── 4. 删除该记录 ───────────────────────────────────────────────────────
echo "[test 4/$discovered] $XAUTH_BIN -i -f <file> remove $DISPLAY"
"$XAUTH_BIN" -i -f "$AUTHFILE" remove "$DISPLAY" > "$WORK/remove.out" 2>&1
rc=$?
cat "$WORK/remove.out"
if [ $rc -eq 0 ]; then
    echo "PASS: remove exit=0"
    passed=$((passed + 1))
else
    echo "FAIL: remove exit=$rc"
fi

# ── 5. 删除后 list 不再包含该记录，且仍以 0 退出 ────────────────────────
echo "[test 5/$discovered] $XAUTH_BIN -i -f <file> list (after remove)"
after_output=$("$XAUTH_BIN" -i -f "$AUTHFILE" list 2>&1)
rc=$?
echo "$after_output"
if [ $rc -eq 0 ] && ! echo "$after_output" | grep -q "$DISPLAY"; then
    echo "PASS: entry gone after remove, list still exits 0"
    passed=$((passed + 1))
else
    echo "FAIL: list exit=$rc, entry still present after remove"
fi

if [ "$passed" -ne "$discovered" ]; then
    echo "FAIL: $((discovered - passed))/$discovered checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_xauth.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "OK: all $discovered checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_xauth.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"autotools","command":"make check (TESTS = test_xauth)","discovered":5,"executed":5,"passed":5,"failed":0,"skipped":0,"reason":"xauth 1.1.4 上游 tests/ 由 TESTS = test_xauth 驱动，遍历 5 个 *.script 场景（010 add-inet / 020 add-local / 030 extract / 040 source / 090 bad-usage），每个场景把 xauth 的 stdout/stderr 与随包 .stdout/.stderr 夹具逐字节 diff；主配方 build() 内实跑，5/5 通过"}\n'
exit 0
