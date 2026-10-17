#!/data/service/hnp/bin/bash
# test.sh — openvi 7.9.33 功能性测试（ex 批处理模式，7 项断言式检查）
# 用法: bash test.sh <openvi-package-folder> <writable-workdir>
#
# 为什么用 ex 批处理：ex 模式不初始化屏幕（不碰 tty），可直接在 CI worker
# 上无头实跑；同时真正走过 openvi 的核心路径——行编辑缓冲、BSD regex 兼容层
# （%s 替换）、BSD db 快照、文件读写。注意 ex 模式**仍需要 terminfo 数据库**：
# openvi 的入口是 cl/cl_main.c 的 main()，它在 editor() 前无条件
# term_init()→setupterm()（失败即 "No terminal database found"）；
# 调用方须设 TERM + TERMINFO（由 test_package/conanfile.py 注入，指向
# Conan ncurses/6.6 的 share/terminfo）。
#
# 调用 bin/ex 而非 `bin/vi -e -s`：上游按 argv[0] 选 getopt 串，vi 模式的
# optstr 不含 -s（"c:C:eFlRrSt:w:"），只有 ex 模式串含 s
# （"c:C:FlRrSst:vw:"）。调用方须以 TMPDIR=<workdir> 运行（HMFS /tmp 只读）。
set -u

PKG="$1"
WORK="$2"
VI="$PKG/bin/vi"
EX="$PKG/bin/ex"
XI="$PKG/bin/xinstall"

fail=0
ok()  { echo "ok - $1"; }
bad() { echo "FAIL - $1"; fail=1; }

rm -rf "$WORK/t" && mkdir -p "$WORK/t" && cd "$WORK/t"

# 1) ex 别名生效（argv[0] 决定模式：bin/ex 直接进 ex 模式，无需 -e）
if printf 'q!\n' | "$EX" -s >/dev/null 2>&1; then
    ok "bin/ex 别名按 argv[0] 进入 ex 模式"
else
    bad "bin/ex 别名未能进入 ex 模式"
fi

# 2) 新建文件：a / . / wq 往返（文件读写路径）
printf 'a\nOPENVI_HARMONY_OK\n.\nwq\n' | "$EX" -s created.txt >/dev/null 2>&1
if grep -qx 'OPENVI_HARMONY_OK' created.txt 2>/dev/null; then
    ok "ex 批处理新建文件并写入"
else
    bad "ex 批处理新建文件写入失败"
fi

# 3) 正则替换（BSD regex 兼容层）
printf 'alpha\nbeta\ngamma\n' > sub.txt
printf '%%s/alpha/ALPHA/\nwq\n' | "$EX" -s sub.txt >/dev/null 2>&1
if [ "$(sed -n 1p sub.txt)" = "ALPHA" ] && [ "$(sed -n 2p sub.txt)" = "beta" ]; then
    ok "ex %%s 正则替换正确（BSD regex 兼容层）"
else
    bad "ex %%s 正则替换结果不符"
fi

# 4) 范围删除（行编辑核心）
printf '1,2d\nwq\n' | "$EX" -s sub.txt >/dev/null 2>&1
if [ "$(wc -l < sub.txt | tr -d ' ')" = "1" ] && [ "$(sed -n 1p sub.txt)" = "gamma" ]; then
    ok "ex 1,2d 范围删除并保留剩余行"
else
    bad "ex 范围删除结果不符"
fi

# 5) 追加时不破坏既有内容
printf '$a\nDELTA_TAIL\n.\nwq\n' | "$EX" -s sub.txt >/dev/null 2>&1
if [ "$(sed -n 1p sub.txt)" = "gamma" ] && [ "$(sed -n 2p sub.txt)" = "DELTA_TAIL" ]; then
    ok "ex \$a 追加行且既有内容不变"
else
    bad "ex 追加行结果不符"
fi

# 6) -R 只读模式拒绝写回（vi 模式串与 ex 模式串都含 R）
cp sub.txt ro.txt
printf 'a\nMUTATION\n.\nwq\n' | "$EX" -s -R ro.txt >/dev/null 2>&1 || true
if cmp -s sub.txt ro.txt; then
    ok "ex -R 只读模式拒绝写回（文件未被修改）"
else
    bad "ex -R 只读模式仍写回了文件"
fi

# 7) 捆绑的 xinstall 按 -m 解析权限（BSD setmode/parsemode 兼容层）
printf 'xinstall-payload\n' > xi.src
"$XI" -m 0640 xi.src xi.dst >/dev/null 2>&1
mode="$(ls -l xi.dst 2>/dev/null | cut -c1-10)"
if [ "$mode" = "-rw-r-----" ] && cmp -s xi.src xi.dst; then
    ok "xinstall -m 0640 复制且权限位正确（BSD setmode 兼容层）"
else
    bad "xinstall -m 权限/内容不符（得到 '$mode'）"
fi

# 8) bin/vi 副本可用（vi 模式串：-e 进入 ex 模式）
printf 'q!\n' | "$VI" -e >/dev/null 2>&1
if [ $? -eq 0 ]; then
    ok "bin/vi 副本可运行（vi 模式 -e 进入 ex）"
else
    bad "bin/vi 副本运行失败"
fi

if [ "$fail" -ne 0 ]; then
    echo "openvi test_package: FAILED"
    exit 1
fi
echo "openvi test_package: all 8 checks passed"
