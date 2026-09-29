#!/bin/bash
# 消费者测试 — jailkit 2.23
# 用法: test_jailkit.sh <包根目录（含 bin/ sbin/ etc/ share/）>
# 6 项断言，全部离线，真实执行被适配产物（R34）。
# chroot 类功能需要 root，非交互面用 CLI 自检 + 安装库 API 验证。
set -u
PKG="$1"
BIN="$PKG/bin"
SBIN="$PKG/sbin"
TMP="$(mktemp -d)" || exit 1
trap 'rm -rf "$TMP"' EXIT
PASS=0
FAIL=0

ok() { PASS=$((PASS+1)); echo "ok $PASS - $1"; }
bad() { FAIL=$((FAIL+1)); echo "FAIL - $1"; }

# 1. jk_uchroot -h：上游特权语义（jk_uchroot.c:144 #ifndef DEVELOPMENT
#    下 geteuid()!=0 → exit(11)，错误走 syslog 不进 stdout，且先于
#    参数解析）→ 非 root 恒 rc=11 零输出；root 才走解析：-h → 版本
#    +用法退出 1。非 root 分支 rc=11 + 零输出本身即上游语义断言。
"$BIN/jk_uchroot" -h >"$TMP/u.txt" 2>&1
RC=$?
if [ "$(id -u)" = "0" ]; then
  if [ $RC -eq 1 ] && grep -q "jailkit 2.23" "$TMP/u.txt" \
     && grep -q "Usage:" "$TMP/u.txt"; then
    ok "jk_uchroot -h（root：版本+用法）"
  else
    bad "jk_uchroot -h: rc=$RC"
  fi
else
  if [ $RC -eq 11 ] && [ ! -s "$TMP/u.txt" ]; then
    ok "jk_uchroot -h（非 root：特权门 exit(11)，输出仅走 syslog）"
  else
    bad "jk_uchroot -h 非 root 语义: rc=$RC, out=$(head -2 "$TMP/u.txt")"
  fi
fi

# 2. jk_uchroot 缺参数：euid 门先于参数解析（"No jail path specified"
#    在 jk_uchroot.c:235）→ 非 root 恒 rc=11 零输出；root 才到缺参
#    ERROR 分支
"$BIN/jk_uchroot" >"$TMP/u2.txt" 2>&1
RC=$?
if [ "$(id -u)" = "0" ]; then
  if [ $RC -ne 0 ] && grep -q "No jail path specified" "$TMP/u2.txt"; then
    ok "jk_uchroot 缺参报错（root）"
  else
    bad "jk_uchroot 缺参: rc=$RC"
  fi
else
  if [ $RC -eq 11 ] && [ ! -s "$TMP/u2.txt" ]; then
    ok "jk_uchroot 缺参（非 root：特权门 exit(11) 先于解析）"
  else
    bad "jk_uchroot 缺参非 root 语义: rc=$RC, out=$(head -2 "$TMP/u2.txt")"
  fi
fi

# 3. jk_chrootlaunch -h：用法，退出码 1
"$SBIN/jk_chrootlaunch" -h >"$TMP/c.txt" 2>&1
RC=$?
if [ $RC -eq 1 ] && grep -q "Usage:" "$TMP/c.txt"; then
  ok "jk_chrootlaunch -h"
else
  bad "jk_chrootlaunch -h: rc=$RC"
fi

# 4. jk_init -h（Python 脚本链：shebang→jk_lib import→参数处理）：
#    非 root 时上游先退出 5（Abort），root 时打印用法退出 0
"$SBIN/jk_init" -h >"$TMP/i.txt" 2>&1
RC=$?
if { [ $RC -eq 5 ] && grep -q "root privileges" "$TMP/i.txt"; } \
   || { [ $RC -eq 0 ] && grep -q "Usage\|usage" "$TMP/i.txt"; }; then
  ok "jk_init -h（Python 脚本链可执行）"
else
  bad "jk_init -h: rc=$RC, out=$(head -2 "$TMP/i.txt")"
fi

# 5. 安装库 jk_lib.py 真实 API：路径工具纯函数（fix_double_slashes /
#    split_path/join_path roundtrip）+ 从包内 share/jailkit 导入
PY="${PYTHON:-/data/service/hnp/bin/python3}"
command -v "$PY" >/dev/null 2>&1 || PY=python3
"$PY" - "$PKG/share/jailkit" <<'EOF' >"$TMP/api.txt" 2>&1
import sys
sys.path.insert(0, sys.argv[1])
import jk_lib
assert jk_lib.fix_double_slashes('//a//b///c') == '/a/b/c'
assert jk_lib.split_path('/usr/bin/ls') == ['usr', 'bin', 'ls']
assert jk_lib.join_path(['usr', 'bin', 'ls']) == '/usr/bin/ls'
assert jk_lib.join_path(jk_lib.split_path('//x//y')) == '/x/y'
print('jk_lib API OK')
EOF
RC=$?
if [ $RC -eq 0 ] && grep -q "jk_lib API OK" "$TMP/api.txt"; then
  ok "jk_lib 纯函数 API"
else
  bad "jk_lib API: rc=$RC, out=$(cat "$TMP/api.txt")"
fi

# 6. 包内容完整性：ini 配置 + 全部 C 二进制 + Python 运维脚本落位
MISS=""
for f in etc/jailkit/jk_init.ini etc/jailkit/jk_lsh.ini \
         bin/jk_uchroot sbin/jk_socketd sbin/jk_chrootsh \
         sbin/jk_chrootlaunch sbin/jk_lsh sbin/jk_init sbin/jk_cp \
         sbin/jk_check sbin/jk_jailuser sbin/jk_list sbin/jk_update \
         share/jailkit/jk_lib.py; do
  [ -e "$PKG/$f" ] || MISS="$MISS $f"
done
if [ -z "$MISS" ] && grep -q "^\[netbasics\]" "$PKG/etc/jailkit/jk_init.ini"; then
  ok "包内容完整（ini/二进制/Python 脚本）"
else
  bad "缺产物:$MISS"
fi

echo "----------------------------------------"
echo "总结: 通过 $PASS / $((PASS+FAIL)), 失败 $FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
