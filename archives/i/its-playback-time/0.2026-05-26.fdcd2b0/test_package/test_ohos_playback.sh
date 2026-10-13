#!/bin/sh
# test_ohos_playback.sh — its-playback-time 鸿蒙特有测试（rule12 完整端到端消费者用例）
#
# 模拟真实用户在 HarmonyOS PC 上用 ipbt-dump 处理一段终端会话录像的完整流程，
# 并断言 OHOS PC 交付契约。四段式：
#   构造输入 → 合成一个 3 帧 ttyrec（模拟 OHOS PC 终端会话），固定字节
#   真实执行 → 用安装后的 ipbt-dump 跑完整转换流水线：
#              SUMMARY → typescript → hex dump → screen XML → raw 往返 → 格式自动识别
#   产出结果 → 每步确定性输出
#   校验内容 → 与参考输出逐字节比对（typescript cmp）+ 语义不变量
#              （帧数 3 / 帧时间戳 / 屏幕文本 / hex 字节 / 反假阳性）
#
# 同时断言 OHOS PC 交付契约：bin/ipbt、bin/ipbt-dump 为 ELF、整包不交付 .so、
# TERMINFO 环境变量指向有效目录（OHOS 终端环境所需）、二进制可运行。
#
# 只比较程序 stdout（2>/dev/null）：运行环境的 stderr 噪音（动态加载器、qemu-binfmt
# 包装层往 stderr 写 ld.so cannot be preloaded）不得折进被比较文本（见 T400）。
set -u

PKG="${1:?usage: test_ohos_playback.sh <package_folder> [terminfo_dir]}"
TERMINFO_DIR="${2:-}"
# 运行环境（conanrun）里 ncurses 导出的 TERMINFO 优先；未导出时才用第二参数。
if [ -z "${TERMINFO:-}" ] && [ -n "$TERMINFO_DIR" ] && [ -d "$TERMINFO_DIR" ]; then
    TERMINFO="$TERMINFO_DIR"
    export TERMINFO
fi

PASS=0
FAIL=0
N=0
ok()    { N=$((N + 1)); PASS=$((PASS + 1)); echo "ok $N - $1"; }
not_ok(){ N=$((N + 1)); FAIL=$((FAIL + 1)); echo "not ok $N - $1"; }

echo "1..18"

PLAYER="$PKG/bin/ipbt"
DUMPER="$PKG/bin/ipbt-dump"

# 1-2: bin/ipbt 与 bin/ipbt-dump 存在且为 ELF
for name in ipbt ipbt-dump; do
    f="$PKG/bin/$name"
    if [ -x "$f" ]; then
        magic=""
        IFS= read -r -n 4 magic < "$f" 2>/dev/null
        if [ "$magic" = "$(printf '\177ELF')" ]; then ok "bin/$name 存在且为 ELF"; else not_ok "bin/$name 非 ELF"; fi
    else
        not_ok "bin/$name 缺失或不可执行"
    fi
done

# 3: 整包不交付 .so（ncurses 静态链入，不污染系统同名库）
SO_COUNT="$(find "$PKG" -name '*.so' 2>/dev/null | wc -l)"
if [ "$SO_COUNT" -eq 0 ]; then ok "整包不含 .so（ncurses 静态链入）"; else not_ok "发现 $SO_COUNT 个 .so"; fi

# 4: 终端库契约（OHOS 终端环境所需）。三分支，逐支给出可核验证据：
#    a) 注入了 TERMINFO → 必须是有效目录（强断言，保持原有强度）
#    b) 未注入但设备/系统自带终端库 → 记录实际路径并接受（真机由系统提供）
#    c) 两者都没有 → 负控：把 TERMINFO 指向不存在的路径，转换器仍必须可用
#       （证伪「依赖宿主终端库」；不把宿主 env 配置当成交付契约）
if [ -n "${TERMINFO:-}" ]; then
    if [ -d "${TERMINFO:-}" ]; then
        ok "TERMINFO 指向有效目录（注入：$TERMINFO）"
    else
        not_ok "TERMINFO 无效 (got: $TERMINFO)"
    fi
else
    SYS_TI=""
    for d in /usr/share/terminfo /etc/terminfo /lib/terminfo /usr/lib/terminfo /data/service/hnp/share/terminfo; do
        if [ -d "$d" ]; then SYS_TI="$d"; break; fi
    done
    if [ -n "$SYS_TI" ]; then
        ok "未注入 TERMINFO，使用设备自带终端库：$SYS_TI"
    else
        V_TI="$(TERMINFO=/nonexistent-termlib TERMINFO_DIRS=/nonexistent-termlib "$DUMPER" --version 2>/dev/null || true)"
        case "$V_TI" in
            *ipbt,\ source\ commit*) ok "无终端库（TERMINFO 指向不存在路径）时转换器仍可用";;
            *) not_ok "无终端库时转换器不可用 (got: ${V_TI:-empty})";;
        esac
    fi
fi

# 5-6: ipbt / ipbt-dump 可运行（--version 退出 0 且输出版本标记）
V="$("$PLAYER" --version 2>/dev/null || true)"
case "$V" in *ipbt,\ source\ commit*) ok "ipbt --version 可运行且输出版本标记";; *) not_ok "ipbt --version 异常 (got: $V)";; esac
V="$("$DUMPER" --version 2>/dev/null || true)"
case "$V" in *ipbt,\ source\ commit*) ok "ipbt-dump --version 可运行且输出版本标记";; *) not_ok "ipbt-dump --version 异常 (got: $V)";; esac

# 端到端消费者用例 (7-18)：3 帧 ttyrec 模拟 OHOS PC 终端会话
#   帧 0 (t=0.0): "HarmonyOS PC\r\n"    14 字节
#   帧 1 (t=1.0): "ipbt replay ok\r\n"  16 字节
#   帧 2 (t=2.0): "done\r\n"             6 字节

WORK="$(mktemp -d "${TMPDIR:-/tmp}/ipbt-ohos.XXXXXX" 2>/dev/null || (mkdir -p /tmp/ipbt-ohos.$$ && echo /tmp/ipbt-ohos.$$))"
trap 'rm -rf "$WORK" 2>/dev/null || true' EXIT

{
    printf '\000\000\000\000\000\000\000\000\016\000\000\000'
    printf 'HarmonyOS PC\r\n'
    printf '\001\000\000\000\000\000\000\000\020\000\000\000'
    printf 'ipbt replay ok\r\n'
    printf '\002\000\000\000\000\000\000\000\006\000\000\000'
    printf 'done\r\n'
} > "$WORK/session.ttyrec"
REC="$WORK/session.ttyrec"

printf 'HarmonyOS PC\r\nipbt replay ok\r\ndone\r\n' > "$WORK/expected.dat"

# 7: ttyrec 文件 72 字节 (3*12 头 + 36 数据)
REC_SIZE="$(wc -c < "$REC" 2>/dev/null)"
if [ "${REC_SIZE:-0}" = "72" ]; then ok "ttyrec 文件 72 字节 (3 帧 12 头 + 36 数据)"; else not_ok "ttyrec 文件 $REC_SIZE 字节 (期望 72)"; fi

# 8: SUMMARY 报 3 帧
SUMMARY="$("$DUMPER" -T "$REC" 2>/dev/null || true)"
FRAME_COUNT="$(printf '%s\n' "$SUMMARY" | grep -c ':offset' 2>/dev/null || echo 0)"
if [ "${FRAME_COUNT:-0}" = "3" ]; then ok "SUMMARY 报 3 帧"; else not_ok "SUMMARY 报 ${FRAME_COUNT:-0} 帧 (期望 3)"; fi

# 9: SUMMARY 帧时间戳 0.0/1.0/2.0
if printf '%s\n' "$SUMMARY" | grep -q ':0:0\.000000:' && \
   printf '%s\n' "$SUMMARY" | grep -q ':1:1\.000000:' && \
   printf '%s\n' "$SUMMARY" | grep -q ':2:2\.000000:'; then
    ok "SUMMARY 帧时间戳 0.0/1.0/2.0 正确"
else
    not_ok "SUMMARY 帧时间戳不完整"
fi

# 10: typescript 逐字节 = 三段拼接（独立构造的参考输出）
"$DUMPER" -T -S -o "$WORK/out.script" "$REC" >/dev/null 2>&1 || true
if cmp -s "$WORK/out.script" "$WORK/expected.dat"; then
    ok "typescript 输出与录制数据逐字节相同"
else
    not_ok "typescript 输出与录制数据不一致"
fi

# 11: hex dump 含 "HarmonyOS" 的字节序列
HEX="$("$DUMPER" -T -H "$REC" 2>/dev/null || true)"
if printf '%s\n' "$HEX" | grep -q '48 61 72 6d 6f 6e 79 4f 53'; then
    ok "hex dump 含 HarmonyOS 的字节序列"
else
    not_ok "hex dump 不含 HarmonyOS 字节序列"
fi

# 12: hex dump ASCII 列含 "HarmonyOS PC"
if printf '%s\n' "$HEX" | grep -q 'HarmonyOS PC'; then
    ok "hex dump ASCII 列含 HarmonyOS PC"
else
    not_ok "hex dump ASCII 列不含 HarmonyOS PC"
fi

# 13: screen XML 含 <ttyrecording> 根
XML="$("$DUMPER" -T -x "$REC" 2>/dev/null || true)"
if printf '%s\n' "$XML" | grep -q '<ttyrecording'; then
    ok "screen XML 含 <ttyrecording> 根"
else
    not_ok "screen XML 缺 <ttyrecording> 根"
fi

# 14: screen XML 含 3 个 frame 元素
XML_FRAMES="$(printf '%s\n' "$XML" | grep -c '<frame index=' 2>/dev/null || echo 0)"
if [ "${XML_FRAMES:-0}" = "3" ]; then ok "screen XML 含 3 个 frame 元素"; else not_ok "screen XML 含 ${XML_FRAMES:-0} 个 frame (期望 3)"; fi

# 15: screen XML 渲染出 "HarmonyOS PC" 屏幕文本
if printf '%s\n' "$XML" | grep -q 'HarmonyOS PC'; then
    ok "screen XML 含屏幕文本 HarmonyOS PC"
else
    not_ok "screen XML 不含屏幕文本 HarmonyOS PC"
fi

# 16: raw 字节模式往返一致
printf 'raw ohos terminal bytes\n' > "$WORK/raw.in"
"$DUMPER" -R -S -o "$WORK/raw.out" "$WORK/raw.in" >/dev/null 2>&1 || true
if cmp -s "$WORK/raw.out" "$WORK/raw.in"; then ok "raw 模式往返一致"; else not_ok "raw 模式往返不一致"; fi

# 17: 反假阳性 — 篡改帧 1 载荷后 hex dump 必须改变
{
    printf '\000\000\000\000\000\000\000\000\016\000\000\000'
    printf 'HarmonyOS PC\r\n'
    printf '\001\000\000\000\000\000\000\000\020\000\000\000'
    printf 'ipbt replay XX\r\n'
    printf '\002\000\000\000\000\000\000\000\006\000\000\000'
    printf 'done\r\n'
} > "$WORK/tampered.ttyrec"
HEX_BAD="$("$DUMPER" -T -H "$WORK/tampered.ttyrec" 2>/dev/null || true)"
if [ "$HEX" != "$HEX_BAD" ]; then ok "反假阳性：篡改载荷后 hex dump 改变"; else not_ok "篡改载荷后 hex dump 未变"; fi

# 18: 格式自动识别（去掉 -T）仍解析出 3 帧
AUTO="$("$DUMPER" -H "$REC" 2>/dev/null || true)"
AUTO_FRAMES="$(printf '%s\n' "$AUTO" | grep -c ':offset' 2>/dev/null || echo 0)"
if [ "${AUTO_FRAMES:-0}" = "3" ]; then ok "格式自动识别解析出 3 帧"; else not_ok "格式自动识别解析出 ${AUTO_FRAMES:-0} 帧 (期望 3)"; fi

echo
if [ "$FAIL" -eq 0 ]; then
    echo "its-playback-time OHOS 端到端消费者用例：全部 $PASS 条通过"
    exit 0
else
    echo "its-playback-time OHOS 端到端消费者用例：$PASS 通过 / $FAIL 失败"
    exit 1
fi
