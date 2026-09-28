#!/data/service/hnp/bin/bash
# test_package/test.sh — vcdimager 2.0.1 消费者测试（装好的 CLI 逐个真跑）
#
# 为什么用 shell 而不是 conan-init 留下的空壳 test.c：vcdimager 的
# package_type = "application"，交付物是 7 个命令行程序（configure 后
# `frontends/cli/Makefile.am:18 bin_PROGRAMS = vcdimager cdxa2mpeg vcd-info`、
# `frontends/xml/Makefile.am:19 bin_PROGRAMS = vcdxbuild vcdxgen vcdxrip vcdxminfo`），
# 一个只 print 的 test.c 证明不了任何东西（PF3/R34）；那份空壳 test.c 与
# CMakeLists.txt 已从本 test_package 删除，这里不再与之并存。
#
# 覆盖面：
#  A. 每个安装出来的二进制在 conanrun PATH 上真能执行（-V/--version，退出码 0），
#     且 -V 自述的版本串就是本次归档的版本 2.0.1；
#  B. 消费者侧数据面：vcdxgen 由 mpeg 轨道生成 videocd.xml，再让 vcdxbuild 把这份
#     XML 读回来（断言它推进到 mpeg 扫描阶段的诊断）。vcdxbuild 读 XML 走的就是
#     frontends/xml/vcd_xml_common.c 里补丁 0001 改过的那条 libxml2 调用面 —— 若该
#     调用式退化，这一步会以 SIGSEGV 收场而不是给出 mpeg 诊断，故同时是崩溃哨兵；
#  C. 负控制：非法选项 / 无 CD-ROM 设备时必须**非零**退出并给出错误，
#     防止"任何调用都返回 0"的假绿。
#
# 更正记录（2026-09-26 主理-64）：本节原先把 B 写成"vcd_version_string() 在运行时向
# libcdio/libvcdinfo 取版本并打印"，并据此加了 grep "libcdio" 的断言 —— **该声明不成立**：
# 实拍 vcdimager -V / vcd-info -V 只有 GNU 标准横幅（程序名/作者/版权），且全树 grep
# 无任何 libcdio 版本打印（横幅实现见 lib/vcd.c:2426 起的 vcd_version_string()）。
# 两条错规格断言已换成上面 B 的真实数据面断言。
#
# 上游 make check 的 8 项测试在 build() 里真跑（含 check_vcd11/check_vcd20/check_svcd1/
# check_nrg 这四个会真调 vcdimager/vcdxbuild/vcdxrip 并比对 .right 基准的 shell 驱动），
# 判决读数见 conanfile.py 的 HMBS_UPSTREAM_TEST_RESULT。
set -u

# OHOS: /system/bin/sh (mksh) 不能执行 ELF，本脚本必须跑在 bash 下。
# 原先这里只是给 $BASH 赋值并"回退到 CONFIG_SHELL/sh"，而全脚本再没引用过 $BASH
# ⇒ 回退路径命中时等于用 sh 跑 bash 脚本，属声明了却不生效的死代码（09-26 审查 P3）。
# 改成真正生效的收口：非 bash 起起来就立刻用确认存在的 bash 包装重新 exec；
# 包装也不在则明确报错退出 1，绝不静默降级成一次假绿。
if [ -z "${BASH_VERSION:-}" ]; then
    if [ -x /data/service/hnp/bin/bash ]; then
        exec /data/service/hnp/bin/bash "$0" "$@"
    fi
    echo "FATAL: 本测试需要 bash，但 /data/service/hnp/bin/bash 不存在" >&2
    exit 1
fi

# HMDFS: /tmp 是只读 erofs，且脚本子进程在新建目录里写文件会被拦。
# 夹具目录取环境里的临时目录（TMPDIR/TMP/TEMP 逐级回退，都没有才用 $HOME/tmp），
# 并以 $$ 结尾保证每一轮唯一：框架 L1e 会把包产物 mv 走、对同一个 test_package 起
# 第二次 conan test（破坏性负例），两轮共用一枚固定目录会互相覆写。
# 不用 mktemp -d —— HMDFS 上 mktemp 出来的目录是 drwx--S---，连 owner 都写不进去。
# 也不退回 "." —— 那会把夹具相对写进 test_package 目录，正是第二轮覆写的形态。
_TMPBASE="${TMPDIR:-${TMP:-${TEMP:-$HOME/tmp}}}"
WORK="${_TMPBASE}/vcdimager-test-package.$$"
if ! mkdir -p "$WORK" 2>/dev/null; then
    WORK="${HOME}/tmp/vcdimager-test-package.$$"   # 兜底：换一根可写根，仍是 $$ 唯一路径
    mkdir -p "$WORK" 2>/dev/null || { echo "FATAL: no writable work dir $WORK" >&2; exit 1; }
fi

TOTAL=0
FAILED=0

run() {
    # run <label> <expect: ok|fail> <cmd...>
    label="$1"; shift
    expect="$1"; shift
    TOTAL=$((TOTAL + 1))
    out="$("$@" 2>&1)"
    rc=$?
    echo "----- [$TOTAL] $label  (cmd: $*, rc=$rc)"
    echo "$out" | head -20
    if [ "$expect" = "ok" ] && [ "$rc" -ne 0 ]; then
        echo "❌ $label: 期望退出 0，实得 $rc"; FAILED=$((FAILED + 1)); return
    fi
    if [ "$expect" = "fail" ] && [ "$rc" -eq 0 ]; then
        echo "❌ $label: 期望非零退出，实得 0（无条件 return 0 的假绿）"
        FAILED=$((FAILED + 1)); return
    fi
}

grep_check() {
    # grep_check <label> <pattern>  —— 对上一次 run 的输出做内容断言
    label="$1"; pat="$2"
    TOTAL=$((TOTAL + 1))
    if printf '%s\n' "$out" | grep -qi -- "$pat"; then
        echo "----- [$TOTAL] $label: 命中 /$pat/"
    else
        echo "❌ $label: 输出里没有 /$pat/"
        FAILED=$((FAILED + 1))
    fi
}

echo "== vcdimager 2.0.1 消费者测试（真跑安装后的 CLI）=="

run "vcdimager -V 可执行"        ok   vcdimager -V
grep_check "vcdimager 版本自述 2.0.1" "2\.0\.1"
# [3][4][5] 数据面：用 vcdxgen 由 mpeg 轨道生成 videocd.xml，再让 vcdxbuild 读回来。
# vcdxbuild 读回这一步同时是补丁 0001 的**消费者侧崩溃哨兵**：如果 libxml2 2.15 的
# enc-handler 调用式回退成 4 参 legacy 型（第 6/7 轮实拍），这里会以 SIGSEGV(139) 结束，
# 而拿不到下面这条 mpeg 扫描诊断 —— 即"XML 解析已经跑通"的证据。
printf "not-an-mpeg-stream" > "$WORK/dummy.mpg"
run "vcdxgen 由 mpeg 轨道生成 XML 描述"        ok   vcdxgen -o "$WORK/gen.xml" "$WORK/dummy.mpg"
grep_check "vcdxgen 自报生成成功"              "created successfully"
run "生成的 XML 文件里确有 videocd 根节点"      ok   grep -q "<videocd" "$WORK/gen.xml"

# [6] vcdxbuild 解析该 XML：必须推进到 mpeg 扫描阶段并以诊断退出（非零但不是信号死亡）。
run "vcdxbuild 读回生成的 XML（libxml2 解析面）" fail vcdxbuild "$WORK/gen.xml"
grep_check "vcdxbuild 已推进到 mpeg 扫描（未段错误）" "mpeg scan"

run "vcd-info -V 可执行"         ok   vcd-info -V
grep_check "vcd-info 版本自述 2.0.1" "2\.0\.1"

run "vcdxbuild -V 可执行"        ok   vcdxbuild -V
run "vcdxgen -V 可执行"          ok   vcdxgen -V
run "vcdxminfo -V 可执行"        ok   vcdxminfo -V
run "vcdxrip -V 可执行"          ok   vcdxrip -V
grep_check "vcdxrip 版本自述 2.0.1" "2\.0\.1"

# cdxa2mpeg 没有 -V（上游只在 vcd-info / xml 前端里放了版本选项），
# 用它的 usage 输出证明二进制可执行、且参数校验真的在跑。
run "cdxa2mpeg 无参给出 usage 并非零退出" fail cdxa2mpeg

# 负控制：非法选项必须被拒
run "vcdimager 非法选项被拒"      fail vcdimager --no-such-option-zzz
# 负控制：xml 前端同样要拒绝未知选项，而不是吞掉后 return 0
run "vcdxbuild 非法选项被拒"      fail vcdxbuild --no-such-option-zzz

echo "== 消费者测试汇总：$TOTAL 项断言，失败 $FAILED 项 =="
if [ "$FAILED" -ne 0 ]; then
    exit 1
fi
echo "vcdimager 2.0.1 test_package: ALL PASSED"
exit 0
