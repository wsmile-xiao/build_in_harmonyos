#!/data/service/hnp/bin/bash
# test_xset.sh — xset/1.2.5 消费者冒烟测试
# 真实执行打包的 xset 二进制（R34：二进制本身即被测 API）。
#
# 六条断言全部在**无 X server** 环境下可达，每条绑定 xset.c 的一个确定出口。
# 出口可达性是本轮实测校正过的（上一版曾断言 `xset -no-such-option` 命中
# xset.c:756 的 unknown option，实为不可达，见下）：
#   xset.c:165-177  第一轮扫参：-display/-d 取值、-version 直接 exit(0)、
#                   其余任意参数只置 hasargs=True（**不报错**）
#   xset.c:178-180  无参数 → usage(NULL)
#   xset.c:182-187  XOpenDisplay(disp) 失败 → 报 unable to open display; exit(EXIT_FAILURE)
#   xset.c:189-757  第二轮逐条解释参数；**只有 XOpenDisplay 成功才会进这里**，
#                   故 xset.c:756 的 usage("unknown option %s") 在无 X 环境**不可达**
#   xset.c:1565-1649 usage()：无论有无 fmt，尾部一律 exit(EXIT_SUCCESS)
#                   ⇒ 走 usage 分支恒 rc=0（上游事实，不是本包 bug）
# 改断言请同步 test_package/conanfile.py 的 docstring 与 MANIFEST.yml。
set -u

BIN="xset"
USAGE_LINE="usage:  xset [-display host:dpy] option ..."
discovered=6
passed=0
failed=0

# 没有 timeout 就别加超时（有就用，防极端环境卡死）
if command -v timeout >/dev/null 2>&1; then
    TX="timeout 60"
else
    TX=""
fi

ok() { passed=$((passed + 1)); echo "[OK] $1"; }
nope() { failed=$((failed + 1)); echo "[FAIL] $1"; }

echo "[test] 1. $BIN -version（版本串原样，未归一化）"
VOUT=$($TX "$BIN" -version 2>&1)
VRC=$?
echo "$VOUT"
if [ "$VRC" -eq 0 ] && [ "$VOUT" = "xset 1.2.5" ]; then
    ok "rc=0 且输出 PACKAGE_STRING == 'xset 1.2.5'（xset.c:171-173，XOpenDisplay 之前）"
else
    nope "-version rc=$VRC output='$VOUT'，期望 rc=0 且输出恰为 'xset 1.2.5'"
fi

echo "[test] 2. $BIN（无选项 → usage(NULL) 分支；上游 usage() 尾部 exit(EXIT_SUCCESS)）"
UOUT=$($TX "$BIN" 2>&1)
URC=$?
echo "$UOUT" | sed -n '1,3p'
if [ "$URC" -eq 0 ] && echo "$UOUT" | grep -qF "$USAGE_LINE"; then
    ok "rc=0（xset.c:1648 的 EXIT_SUCCESS）且命中 usage 行 ⇒ 无参数走 usage 分支、未触碰 XOpenDisplay"
else
    nope "无选项 rc=$URC（期望 0，见 xset.c:1648），usage 行命中=$(echo "$UOUT" | grep -cF "$USAGE_LINE")"
fi

echo "[test] 3. usage 文本含 DPMS 小节（正向反证 libxext 依赖生效：#ifdef DPMSExtension）"
if echo "$UOUT" | grep -qF "Display Power Management Signaling (DPMS)"; then
    ok "DPMS 小节被编译进来 ⇒ SET_XEXT(xext) 探测成功、DPMSExtension 成立（xset.c:1593-1604）"
else
    nope "usage 文本缺 DPMS 小节 ⇒ libxext 未生效（DPMSExtension 未定义），依赖链断裂"
fi

echo "[test] 4. $BIN -display <不存在> q（Xlib 连接路径 + 动态装载验证）"
BAD="qzy-no-such-x-host:99"
QOUT=$($TX "$BIN" -display "$BAD" q 2>&1)
QRC=$?
echo "$QOUT"
if [ "$QRC" -ne 0 ] && echo "$QOUT" | grep -qF 'unable to open display'; then
    ok "rc=$QRC 且报 unable to open display（xset.c:182-187）：二进制可装载（libX11.so.6/libXext.so.6 的 DT_NEEDED 解析成功）且真实进入 Xlib 连接路径"
else
    nope "-display $BAD q rc=$QRC output='$QOUT'，期望非 0 退出且含 'unable to open display'"
fi

echo "[test] 5. $BIN -display / -d 缺值（第一轮扫参的错误分支，XOpenDisplay 之前 ⇒ 无 X 可达）"
MAOUT=$($TX "$BIN" -display 2>&1)
MARCS=$?
MAOUT2=$($TX "$BIN" -d 2>&1)
MARCS2=$?
echo "$MAOUT" | sed -n '1,2p'
if [ "$MARCS" -eq 0 ] && [ "$MARCS2" -eq 0 ] \
    && echo "$MAOUT" | grep -qF "missing argument to -display" \
    && echo "$MAOUT" | grep -qF "$USAGE_LINE" \
    && echo "$MAOUT2" | grep -qF "missing argument to -display" \
    && echo "$MAOUT2" | grep -qF "$USAGE_LINE"; then
    ok "-display 与 -d 两个别名都命中 xset.c:167-170 的 usage('missing argument to -display')，且带 fmt 时仍接 usage 文本、rc=0（xset.c:1569-1576 + 1648）"
else
    MISS1=$(echo "$MAOUT" | grep -cF "missing argument to -display")
    MISS2=$(echo "$MAOUT2" | grep -cF "missing argument to -display")
    nope "-display rc=$MARCS（期望 0，xset.c:1648）/ -d rc=$MARCS2；missing 消息命中数=$MISS1/$MISS2，usage 行命中数=$(echo "$MAOUT" | grep -cF "$USAGE_LINE")/$(echo "$MAOUT2" | grep -cF "$USAGE_LINE")"
fi

echo "[test] 6. usage 文本不含 font cache 小节（反向反证 --without-fontcache 真生效）"
if echo "$UOUT" | grep -qF "To control font cache"; then
    nope "usage 文本仍含 'To control font cache' ⇒ 配方的 --without-fontcache 未生效（xset.c:1605-1612 的 #ifdef FONTCACHE 未被裁），构建配置不可信"
else
    ok "FONTCACHE 段已被裁掉（xset.c:1605-1612）⇒ 配方显式 --without-fontcache 真实传达到 configure"
fi

if [ "$failed" -ne 0 ]; then
    echo "FAIL: $failed/$discovered checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_xset.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "OK: all $discovered checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_xset.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"autotools","command":"make check (n/a)","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"xset 1.2.5 上游无自动化测试：源码包无 test/、tests/ 目录；Makefile.am 仅 SUBDIRS=man 与 bin_PROGRAMS=xset，无 check/test 目标、无 TESTS 变量；configure.ac 仅 AC_CHECK_FUNCS(usleep) 与 4 处 PKG_CHECK_MODULES，无测试宏。man/Makefile.am 只做 man page 生成。"}\n'
exit 0
