#!/bin/sh
# tlog CLI 功能验证（消费者侧，真实执行三个命令行工具；7 条断言）
#
# 用法: sh test_cli.sh <工作目录> <被测包 package_folder>
# 退出码: 0 = 全部通过；非 0 = 有失败
#
# ── 为什么按上游「构建树布局」摆文件，而不是直接跑 <pkg>/bin/tlog-rec ──
# tlog 按「二进制自身的真实路径」定位配置（lib/tlog/misc.c:44
# tlog_build_or_inst_path）：若二进制所在目录名是 libtool 的 .libs，则用相对
# 路径 <exe_dir>/../<name>.default.conf；否则用编译期绝对路径（本配方 prefix
# 为 conan 默认 `/`，即 /share/tlog/… 与 /etc/tlog/…，包内并不存在于该位置）。
# 且**默认配置与本地配置缺一不可**，否则 CLI 直接以 rc=1 退出，报
# "Failed loading default configuration"（rec_conf.c:187-205）或
# "Failed finding system configuration"（rec_conf.c:207-211）。
# 于是把包内 bin/ 与两组配置按上游构建树布局摆进工作目录，走「构建树」分支，
# 让默认配置真实加载 —— 这是上游自己的运行时规则，不是测试专属后门。
#
# 刻意只用 `set -u` 而不加 `-e`：断言由 check() 逐条计数（passed/failed），
# `-e` 会在 expect 失配的第一条就中止，拿不到完整的通过/失败统计；退出码由
# 末尾的 `[ "$failed" -eq 0 ]` 兜底，等价于安全模式下的"任一失败即非 0"。
set -u

work=$1
pkg=$2

if [ ! -d "$pkg/bin" ]; then
    echo "FAIL 被测包内没有 bin/：$pkg"
    exit 1
fi

mkdir -p "$work/.libs" || exit 1
for exe in tlog-rec tlog-play tlog-rec-session; do
    cp "$pkg/bin/$exe" "$work/.libs/" || { echo "FAIL 缺少 $pkg/bin/$exe"; exit 1; }
done
cp "$pkg"/share/tlog/*.default.conf "$work/" \
    || { echo "FAIL 缺少 $pkg/share/tlog/*.default.conf"; exit 1; }
cp "$pkg"/etc/tlog/*.conf "$work/" \
    || { echo "FAIL 缺少 $pkg/etc/tlog/*.conf"; exit 1; }

cd "$work/.libs" || exit 1

passed=0
failed=0

check() {
    name=$1
    want=$2
    shift 2
    out=$("$@" 2>&1)
    rc=$?
    if [ "$rc" -ne 0 ]; then
        echo "FAIL [$name] rc=$rc"
        printf '%s\n' "$out" | head -5 | sed 's/^/       /'
        failed=$((failed + 1))
        return
    fi
    case "$out" in
        *"$want"*)
            passed=$((passed + 1))
            echo "ok   [$name]"
            ;;
        *)
            echo "FAIL [$name] 输出中不含 \"$want\""
            printf '%s\n' "$out" | head -5 | sed 's/^/       /'
            failed=$((failed + 1))
            ;;
    esac
}

check "tlog-rec --version"        "tlog 14"           ./tlog-rec --version
check "tlog-play --version"       "tlog 14"           ./tlog-play --version
check "tlog-rec-session --version" "tlog 14"          ./tlog-rec-session --version
check "tlog-rec --help"           "Usage: tlog-rec"   ./tlog-rec --help
check "tlog-play --help"          "Usage: tlog-play"  ./tlog-play --help
check "tlog-rec --configuration"  '"latency"'         ./tlog-rec --configuration
check "tlog-play --configuration" '"reader"'          ./tlog-play --configuration

echo "tlog CLI: $passed passed, $failed failed"
[ "$failed" -eq 0 ] || exit 1
exit 0
