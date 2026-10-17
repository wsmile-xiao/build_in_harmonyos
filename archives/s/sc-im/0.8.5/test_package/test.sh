#!/data/service/hnp/bin/bash
# test_package/test.sh — sc-im 0.8.5 消费者测试（7 项断言）
#
# 用法: test.sh <package_folder> <writable_workdir>
#   1/2/3 上游功能 + 依赖接通：--version（补丁 0001 后无控制终端必须 rc=0）
#   4     鸿蒙特有①：xlsx 族（xlsxio/libxlsxwriter）不在制品仓 → 编译开关必须缺席
#   5     鸿蒙特有②：无控制终端的纯管道形态（CI/worker 真实形态）输出契约必须干净
#   6     消费者视角安装树完整性（上游 install 目标交付面）
#   7     鸿蒙特有③：scopen shebang 回归（设备 /usr/bin/env 为 toybox，无 -S）
set -u

PKG="$1"
WORK="$2"
SCIM="$PKG/bin/sc-im"
SCOPEN="$PKG/bin/scopen"
FAIL=0
RUN=0

ok()   { RUN=$((RUN + 1)); echo "ok - $1"; }
bad()  { RUN=$((RUN + 1)); FAIL=1; echo "FAIL - $1"; }

mkdir -p "$WORK" "$WORK/home"
[ -x "$SCIM" ] || { echo "FAIL - $SCIM 不可执行"; exit 1; }

# ── 1) --version 版本锚点 + 无控制终端退出码（上游功能） ──
"$SCIM" --version > "$WORK/version.out" 2>&1
rc=$?
if [ "$rc" -eq 0 ] && grep -q "sc-im - version 0.8.5" "$WORK/version.out"; then
    ok "--version rc=0 且输出 sc-im - version 0.8.5（headless 退出码契约）"
else
    bad "--version rc=$rc / 输出见 $WORK/version.out"
fi

# ── 2) 宽字符 ncurses 依赖接通（-DNCURSES 编译开关自证） ──
if grep -q -- "-DNCURSES" "$WORK/version.out"; then
    ok "--version 自报 -DNCURSES（ncursesw 宽字符依赖接通）"
else
    bad "--version 缺少 -DNCURSES（ncursesw 探测失败）"
fi

# ── 3) libxls 依赖接通（-DXLS 编译开关自证） ──
if grep -q -- "-DXLS" "$WORK/version.out"; then
    ok "--version 自报 -DXLS（libxls 依赖接通，xls 导入可用）"
else
    bad "--version 缺少 -DXLS（libxls 探测失败）"
fi

# ── 4) 鸿蒙特有①：xlsx/ods 编译开关必须缺席 ──
# 制品仓 ohpcd 无 xlsxio / libxlsxwriter（conan list 实测 0 条），配方未声明对应
# requires 且 PKG_CONFIG_LIBDIR 钉死在生成目录 ⇒ src/Makefile 三条 --exists 条件
# 全走 else。断言 -DXLSX / -DODS / -DXLSX_EXPORT 三者都不出现。
if grep -qE -- "-DXLSX|-DODS|-DXLSX_EXPORT" "$WORK/version.out"; then
    bad "出现 xlsx/ods 编译开关（应为缺省禁用）：$(grep -E -- '-DXLSX|-DODS|-DXLSX_EXPORT' "$WORK/version.out" | tr '\n' ' ')"
else
    ok "鸿蒙特有①: -DXLSX/-DODS/-DXLSX_EXPORT 均缺席（xlsx 族不在档 → 缺省禁用回归锚点）"
fi

# ── 5) 鸿蒙特有②：无控制终端纯管道计算，输出契约干净 ──
# sc-im 上游 read_stdin() 假定总有控制终端（补丁 0001 前此处 rc=255 且 stderr
# 多一行 "Bad file descriptor"，上游测试的精确比对必然失配）。
# 夹具为上游 tests/test1.sc 的副本：C2 = Sheet2!A0 + A0 = 56 + (B0+2) = 81。
cp "$(dirname "$0")/test.sc" "$WORK/fixture.sc" || { echo "FAIL - 夹具 test.sc 不可读"; exit 1; }
out=$(HOME="$WORK/home" sh -c "echo GETNUM C2 | \"$SCIM\" \"$WORK/fixture.sc\" --nocurses --nodebug --quit_afterload" 2>&1)
rc=$?
if [ "$rc" -eq 0 ] && [ "$out" = "81" ]; then
    ok "鸿蒙特有②: 无 TTY 纯管道 GETNUM C2 == 81 且 rc=0（输出无杂散行）"
else
    bad "管道计算 rc=$rc out=[$out]"
fi

# ── 6) 安装树完整性（上游 install 目标交付面） ──
missing=""
for f in bin/sc-im bin/scopen share/sc-im/sc-im_help share/sc-im/plot_bar \
         share/man/man1/sc-im.1 licenses/LICENSE; do
    [ -s "$PKG/$f" ] || missing="$missing $f"
done
themes_n=$(ls "$PKG"/share/themes/*.sc 2>/dev/null | wc -l)
if [ -z "$missing" ] && [ "$themes_n" -ge 1 ]; then
    ok "安装树完整：bin×2 + sc-im_help + plot_* + man1 + licenses + themes×${themes_n}"
else
    bad "安装树缺失:$missing themes=$themes_n"
fi

# ── 7) 鸿蒙特有③：scopen shebang 回归（补丁 0002） ──
HOME="$WORK/home" "$SCOPEN" --version > "$WORK/scopen.out" 2>&1
rc=$?
if [ "$rc" -eq 0 ]; then
    ok "鸿蒙特有③: scopen 可执行且 rc=0（env -S shebang 在 toybox env 下不可用的回归）"
else
    bad "scopen rc=$rc（shebang/env -S 回归）"
fi

echo "assertions_run=$RUN"
if [ "$FAIL" -ne 0 ]; then
    # 失败时把工作目录现场打进日志（随后目录仍会被清理，避免污染 worktree）
    echo "---- 失败现场（$WORK） ----"
    for f in "$WORK"/*.out "$WORK"/*.err; do
        [ -f "$f" ] || continue
        echo "== $f"; cat "$f"
    done
fi
# 工作目录只在 conan test 的构建目录内存在；成功与否都清掉，避免把未跟踪的
# 中间产物留在 worktree（test_package 的生成 env 文件已被 .gitignore 覆盖）。
rm -rf "$WORK"
if [ "$FAIL" -ne 0 ]; then
    exit 1
fi
exit 0
