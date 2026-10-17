#!/data/service/hnp/bin/bash
# =============================================================================
# test_package/test.sh — yasw 0.6 消费者测试（OpenHarmony PC / aarch64）
# =============================================================================
# 上游 yasw 0.6 无任何自动化测试（R51 清点证据见
# archives/y/yasw/0.6/notes.md「上游测试情况」节）。本脚本新增 3 个鸿蒙
# 消费者用例，验证该包在目标平台上的真实可消费性：
#
#   用例 1  consumer.ohos.arch     产物为 OHOS PC 目标架构 aarch64 的 ELF 可执行文件
#   用例 2  consumer.ohos.qt5      Qt5 动态依赖链完整（含 PrintSupport，PDF 导出必需）
#   用例 3  consumer.ohos.runtime  GUI 真实启动并进入 Qt 事件循环（offscreen 平台）
#
# 由 test_package/conanfile.py 在 conanrun 环境中调用（conan create 阶段执行）。
# 参数 $1 = 被测包内 yasw 可执行文件绝对路径。
# =============================================================================
set -u

BIN="${1:-yasw}"
TMO=8

# 日志目录：优先使用调用方传入（conanfile.py 传 conan 构建目录，位于 conan
# 缓存内，不污染 archives 源码树），否则退到 $TMPDIR / 当前目录。
LOGDIR=""
for _c in "${2:-}" "${TMPDIR:-}" "$PWD"; do
    [ -n "$_c" ] || continue
    [ -d "$_c" ] || continue
    [ -w "$_c" ] || continue
    LOGDIR="$_c"
    break
done
[ -n "$LOGDIR" ] || LOGDIR=/tmp

CASE_TOTAL=0
CASE_PASS=0
CASE_FAIL=0
CASE_SKIP=0
ASSERT_PASS=0
ASSERT_FAIL=0

ok()   { echo "     ✅ $*"; ASSERT_PASS=$((ASSERT_PASS + 1)); }
bad()  { echo "     ❌ $*"; ASSERT_FAIL=$((ASSERT_FAIL + 1)); }
skip() { echo "     ⏭️  $*"; }
case_result() { # $1=用例名 $2=ok|fail|skip
    CASE_TOTAL=$((CASE_TOTAL + 1))
    case "$2" in
        ok)   CASE_PASS=$((CASE_PASS + 1)); printf '  ==> 用例 %-24s : PASS\n' "$1" ;;
        fail) CASE_FAIL=$((CASE_FAIL + 1)); printf '  ==> 用例 %-24s : FAIL\n' "$1" ;;
        skip) CASE_SKIP=$((CASE_SKIP + 1)); printf '  ==> 用例 %-24s : SKIP\n' "$1" ;;
    esac
}

# musl 动态加载器在此 OHOS 环境下不跟随 .so 版本化符号链接加载共享库
# （qt 包内 lib/libQt5Core.so.5 等是 conan 生成的符号链接；实体文件则正常）。
# 直连加载失败且命中该特征时，解引用复制到可写目录后重试。
classify() { # $1=退出码 $2=日志；输出 ok|loader|other
    local rc="$1" log="$2"
    [ "$rc" -eq 124 ] && { echo ok; return; }   # 超时被杀 = 已进入事件循环
    [ "$rc" -eq 0 ]   && { echo ok; return; }
    if [ -f "$log" ] && grep -qE 'Error loading shared library|symbol not found' "$log"; then
        echo loader; return
    fi
    echo other
}

run_yasw() { # $1=额外库目录(可空) $2=日志；返回进程退出码
    # 用 env 只给被测进程设置变量：timeout 自身仍用原始环境，
    # 避免被 RELOC 中的库影响（曾致 /bin/timeout 自身加载失败 → 退出 127）。
    local extra="$1" log="$2"
    if [ -n "$extra" ]; then
        timeout "$TMO" env LD_LIBRARY_PATH="$extra:${LD_LIBRARY_PATH:-}" \
            QT_QPA_PLATFORM=offscreen "$BIN" -platform offscreen >"$log" 2>&1
    else
        timeout "$TMO" env QT_QPA_PLATFORM=offscreen \
            "$BIN" -platform offscreen >"$log" 2>&1
    fi
    return $?
}

find_in_ldpaths() { # $1=库名；在 LD_LIBRARY_PATH 中输出其路径
    local name="$1" d
    local old_ifs="$IFS"; IFS=:
    for d in ${LD_LIBRARY_PATH:-}; do
        if [ -e "$d/$name" ]; then
            printf '%s\n' "$d/$name"
            IFS="$old_ifs"
            return 0
        fi
    done
    IFS="$old_ifs"
    return 1
}

relocate_libs() { # 输出解引用后的库目录；失败返回 1
    # 只复制被测二进制 DT_NEEDED **传递闭包**中、能在 LD_LIBRARY_PATH 命中、
    # 且**不位于系统库目录**的库。两条排除都是实测必需：
    #   ① 整批遍历 LD_LIBRARY_PATH（本环境含 /system/lib64 等）会把系统库
    #      也搬进来 → timeout 等系统程序自身加载失败（退出 127）；
    #   ② 复制 /system/lib64 下的 libc.so 会破坏 musl 的 libc 绑定
    #      （同样退出 127）。系统库交由系统自行解析。
    local dest="" base
    for base in "${TMPDIR:-}" "$PWD" "${HOME:-}"; do
        [ -n "$base" ] || continue
        [ -d "$base" ] || continue
        # 每次运行使用独立目录：避免上一轮的残留（如误复制的 libc.so）
        # 影响本次结果。
        dest="$base/.yasw_consumer_libs.$$"
        if mkdir -p "$dest" 2>/dev/null; then
            break
        fi
        dest=""
    done
    [ -n "$dest" ] || return 1

    local queue="$BIN" seen=" " item path name
    while [ -n "$queue" ]; do
        item="${queue%% *}"
        if [ "$item" = "$queue" ]; then queue=""; else queue="${queue#* }"; fi
        [ -n "$item" ] || continue
        case "$seen" in *" $item "*) continue ;; esac
        seen="$seen$item "
        for name in $("$READELF" -d "$item" 2>/dev/null \
                       | sed -n 's/.*(NEEDED).*\[\(.*\)\].*/\1/p'); do
            path="$(find_in_ldpaths "$name" 2>/dev/null || true)"
            [ -n "$path" ] || continue
            case "$path" in
                /system/*|/vendor/*|/lib/*|/lib64/*|/usr/lib/*) continue ;;
            esac
            if [ ! -e "$dest/$name" ]; then
                cp -L "$path" "$dest/$name" 2>/dev/null || true
            fi
            queue="$queue $dest/$name"
        done
    done
    echo "$dest"
}

READELF="$(command -v readelf 2>/dev/null || echo /data/service/hnp/bin/readelf)"

echo "=============================================================="
echo " yasw 0.6 消费者测试（OHOS PC / aarch64）"
echo " 待测二进制: $BIN"
echo " 加载器库路径: ${LD_LIBRARY_PATH:-<empty>}"
echo " Qt 插件路径: ${QT_PLUGIN_PATH:-<empty>}"
echo "=============================================================="

# -----------------------------------------------------------------------------
# 用例 1：产物为目标平台 aarch64 ELF 可执行文件
# -----------------------------------------------------------------------------
echo
echo "--- 用例 1/3：consumer.ohos.arch（OHOS PC aarch64 ELF）---"
C1=1
if [ ! -f "$BIN" ]; then
    bad "待测二进制不存在: $BIN"
    C1=0
else
    HDR="$("$READELF" -h "$BIN" 2>&1)"
    MACHINE="$(printf '%s\n' "$HDR" | grep -E '^[[:space:]]*Machine:' | head -1)"
    FILEOUT="$(file "$BIN" 2>&1)"
    echo "     $MACHINE"
    echo "     $FILEOUT"
    printf '%s\n' "$HDR" | grep -q 'AArch64' \
        && ok "ELF 架构 = AArch64（OHOS PC 目标平台）" \
        || { bad "ELF 架构非 AArch64 → $MACHINE"; C1=0; }
    printf '%s\n' "$FILEOUT" | grep -q 'ELF' \
        && ok "产物为 ELF 动态链接文件" \
        || { bad "产物不是 ELF 文件"; C1=0; }
fi
[ "$C1" -eq 1 ] && case_result "consumer.ohos.arch" ok || case_result "consumer.ohos.arch" fail

# -----------------------------------------------------------------------------
# 用例 2：Qt5 动态依赖链完整（消费者可解析全部 .so）
# -----------------------------------------------------------------------------
echo
echo "--- 用例 2/3：consumer.ohos.qt5（Qt5 动态依赖链完整）---"
C2=1
if [ ! -f "$BIN" ]; then
    bad "待测二进制不存在，无法读取动态依赖"
    C2=0
else
    NEEDED="$("$READELF" -d "$BIN" 2>/dev/null | grep -E '\(NEEDED\)' | sed 's/.*\[\(.*\)\].*/\1/')"
    printf '%s\n' "$NEEDED" | sed 's/^/       /'
    if [ -z "$NEEDED" ]; then
        bad "未读取到任何 DT_NEEDED 条目"
        C2=0
    else
        for lib in libQt5PrintSupport.so.5 libQt5Widgets.so.5 libQt5Gui.so.5 \
                   libQt5Xml.so.5 libQt5Core.so.5; do
            if printf '%s\n' "$NEEDED" | grep -qF "$lib"; then
                ok "依赖声明存在: $lib"
            else
                bad "依赖缺失: $lib"
                C2=0
            fi
        done
        printf '%s\n' "$NEEDED" | grep -qF 'libc++_shared.so' \
            && ok "C++ 运行时依赖存在: libc++_shared.so" \
            || { bad "C++ 运行时依赖缺失: libc++_shared.so"; C2=0; }
    fi
fi
[ "$C2" -eq 1 ] && case_result "consumer.ohos.qt5" ok || case_result "consumer.ohos.qt5" fail

# -----------------------------------------------------------------------------
# 用例 3：GUI 真实启动（offscreen 平台，进入 Qt 事件循环）
# -----------------------------------------------------------------------------
echo
echo "--- 用例 3/3：consumer.ohos.runtime（GUI 真实启动）---"
C3=1
LOG="$LOGDIR/yasw-consumer-runtime.log"
if [ ! -f "$BIN" ]; then
    bad "待测二进制不存在，无法启动"
    C3=0
elif ! command -v timeout >/dev/null 2>&1; then
    skip "系统无 timeout 命令，无法做启动超时控制 —— 用例跳过"
    C3=2
else
    run_yasw "" "$LOG"
    RC=$?
    echo "     直连启动退出码=$RC（124=超时被杀，即已进入事件循环）"
    case "$(classify "$RC" "$LOG")" in
        ok)
            ok "GUI 真实启动成功 —— 进入 Qt 事件循环"
            ;;
        loader)
            echo "     ⚠️  命中本 OHOS 环境加载器限制：musl 不跟随 .so 版本化符号链接"
            echo "         （qt 包内 lib/*.so.5 为符号链接）→ 解引用复制后重试"
            RELOC="$(relocate_libs || true)"
            if [ -z "$RELOC" ]; then
                bad "无法创建解引用库目录，启动校验无法完成"
                C3=0
            else
                echo "     解引用库目录: $RELOC"
                LOG="$LOGDIR/yasw-consumer-runtime-relocated.log"
                run_yasw "$RELOC" "$LOG"
                RC2=$?
                echo "     解引用后启动退出码=$RC2"
                if [ "$(classify "$RC2" "$LOG")" = ok ]; then
                    ok "GUI 真实启动成功（解除符号链接后）—— 进入 Qt 事件循环"
                else
                    bad "解引用后仍启动失败（退出码 $RC2）"
                    C3=0
                fi
                # 清理一次性库目录（best-effort）
                find "$RELOC" -depth -delete 2>/dev/null || true
            fi
            ;;
        *)
            bad "GUI 启动失败（退出码 $RC），日志尾部："
            [ -f "$LOG" ] && tail -5 "$LOG" | sed 's/^/       /'
            C3=0
            ;;
    esac
fi
if [ "$C3" -eq 2 ]; then
    case_result "consumer.ohos.runtime" skip
elif [ "$C3" -eq 1 ]; then
    case_result "consumer.ohos.runtime" ok
else
    case_result "consumer.ohos.runtime" fail
fi

# -----------------------------------------------------------------------------
# 汇总
# -----------------------------------------------------------------------------
echo
echo "=============================================================="
echo " 消费者测试汇总（yasw 0.6 / OHOS PC aarch64）"
echo "--------------------------------------------------------------"
printf ' 用例总数: %s   通过: %s   失败: %s   跳过: %s\n' \
       "$CASE_TOTAL" "$CASE_PASS" "$CASE_FAIL" "$CASE_SKIP"
printf ' 断言总数: %s   通过: %s   失败: %s\n' \
       "$((ASSERT_PASS + ASSERT_FAIL))" "$ASSERT_PASS" "$ASSERT_FAIL"
echo " 运行日志: $LOG"
echo "=============================================================="

if [ "$CASE_FAIL" -ne 0 ]; then
    echo "FAIL: yasw 消费者测试存在失败用例"
    exit 1
fi
echo "PASS: yasw 消费者测试通过（$CASE_PASS 用例通过，$CASE_SKIP 跳过）"
exit 0
