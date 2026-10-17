#!/bin/sh
# ttygif 1.5.0 —— 鸿蒙消费者功能测试（test_package/test.sh）
# 用法: test.sh <ttygif_bindir> <imagemagick_bindir> <ttyrec-fixture>
#
# 上游 1.5.0 不带任何自动化测试（清点见 MANIFEST.yml 与
# reports/upstream-test-scan.txt），所以下面每一条都是本包新增、
# 真执行打包二进制的断言。判决只看 ASSERT 行与最后的 VERDICT 行。
#
# 账本口径：DISCOVERED 只在「发起一条断言」时自加一次，判决一律由
# ok()/bad()/skip() 产出，故恒有 DISCOVERED = PASS + FAIL + SKIP；
# 末尾的自检行会把这条不变式实测出来，不成立即判 FAIL（不许静默）。
#
# 平台纪律：
#   * 鸿蒙 /tmp 只读，且 toybox sh 的 $(…) 命令替换要往 /tmp 落临时件
#     ⇒ 本脚本**零命令替换、零反引号**；计数一律「重定向到文件 + read」。
#   * 系统里没有 /bin/bash ⇒ shebang 用 /bin/sh。
#   * 不用 LINES/COLUMNS 作变量名（ash 托管这两个名字）。
#   * 框架 L1e 会对同一个 test_package 起第二次 conan test（负向用例）⇒
#     所有产物写进按进程号分址的 $W，正负两轮不共用，也不往 cwd 相对写。
set -u

BINDIR="${1:-}"
IMBIN="${2:-}"
REC="${3:-}"

if [ -z "$BINDIR" ] || [ ! -d "$BINDIR" ]; then
    echo "test.sh: ttygif bindir 未解析（收到 '$BINDIR'）"
    exit 1
fi
TTYGIF="$BINDIR/ttygif"
if [ ! -f "$TTYGIF" ]; then
    echo "test.sh: $TTYGIF 不存在 —— 配方没交付 CLI（L1e 破坏性验证期望在此失败）"
    exit 1
fi

BASE="${TMPDIR:-$PWD}"
W="$BASE/ttygif-cases.$$"
mkdir -p "$W" || exit 1
export TMPDIR="$W"
export TMP="$W"
export TEMP="$W"
export TEMPDIR="$W"

if [ -n "$IMBIN" ] && [ -d "$IMBIN" ]; then
    CONV="$IMBIN/convert"
    IDENT="$IMBIN/identify"
else
    CONV=""
    IDENT=""
fi

if [ -z "$REC" ] || [ ! -f "$REC" ]; then
    REC="$W/no-fixture.tty"
    : > "$REC"
fi

PASS=0
FAIL=0
SKIP=0
DISCOVERED=0
RC=0
N=0

ok()   { PASS=$((PASS+1)); echo "ok:   $1 $2"; }
bad()  { FAIL=$((FAIL+1)); echo "FAIL: $1 $2 -- $3"; }
skip() { SKIP=$((SKIP+1)); echo "SKIP: $1 $2 -- $3"; }
# gate_skip <id> <名称> <依据原文> —— 一条**被实测依据降级**的断言，
# 计入 DISCOVERED 与 SKIP 两维（skip() 本身不自加，防漏计）。
gate_skip() {
    DISCOVERED=$((DISCOVERED+1))
    skip "$1" "$2" "$3"
}
# rd <文件> —— 把该文件的**行数**读进全局 N（零命令替换）
rd() {
    wc -l < "$1" > "$W/lc" 2>/dev/null
    N=0
    read N < "$W/lc" 2>/dev/null
    return 0
}
# rf <文件> —— 把该文件里**写着的数字**读进全局 N（配合 wc -c 之类的计数）
rf() {
    N=0
    read N < "$1" 2>/dev/null
    return 0
}
# show <标签> <文件> —— 打印某个证据件的行数与原文（依据入日志）
show() {
    rd "$2"
    printf '    %s: %s 行\n' "$1" "$N"
    sed -n '1,12p' "$2" 2>/dev/null | sed 's/^/      | /'
}

# want <id> <名称> <模式> <文件>
want() {
    DISCOVERED=$((DISCOVERED+1))
    if [ ! -f "$4" ]; then bad "$1" "$2" "无输出文件"; return; fi
    if grep -q -e "$3" "$4"; then ok "$1" "$2"; else bad "$1" "$2" "缺模式 $3"; fi
}
# wantf <id> <名称> <固定串> <文件> —— grep -F，用于含点号的路径字面量
wantf() {
    DISCOVERED=$((DISCOVERED+1))
    if [ ! -f "$4" ]; then bad "$1" "$2" "无输出文件"; return; fi
    if grep -q -F -e "$3" "$4"; then ok "$1" "$2"; else bad "$1" "$2" "缺固定串 $3"; fi
}
# wantnot <id> <名称> <模式> <文件>
wantnot() {
    DISCOVERED=$((DISCOVERED+1))
    if [ ! -f "$4" ]; then bad "$1" "$2" "无输出文件"; return; fi
    if grep -q -e "$3" "$4"; then bad "$1" "$2" "不该出现 $3"; else ok "$1" "$2"; fi
}
# rceq <id> <名称> <期望rc> <实际rc>
rceq() {
    DISCOVERED=$((DISCOVERED+1))
    if [ "$3" = "$4" ]; then ok "$1" "$2 (rc=$4)"; else bad "$1" "$2" "rc=$4 应为 $3"; fi
}
# count_is <id> <名称> <模式> <文件> <期望次数>
# 口径：**按出现次数**计（grep -o 每次命中一行），不是按行数 —— 同一串参数
# 往往挤在一行里，按行计恒为 1（本函数此前的缺陷即 C15 假失败根因）。
count_is() {
    DISCOVERED=$((DISCOVERED+1))
    grep -o -e "$3" "$4" > "$W/cnt" 2>/dev/null
    rd "$W/cnt"
    if [ "$N" = "$5" ]; then ok "$1" "$2 (计数 $N)"; else bad "$1" "$2" "计数 $N 应为 $5"; fi
}
# bytes_is <id> <名称> <文件> <期望字节数> —— 与上面的签名注释一致用 $3/$4
# （此前函数体按 $2/$3 取参，把名称当文件名去 wc -c，期望值错位到路径）
bytes_is() {
    DISCOVERED=$((DISCOVERED+1))
    if [ ! -f "$3" ]; then bad "$1" "$2" "文件不存在: $3"; return; fi
    wc -c < "$3" > "$W/sz" 2>/dev/null
    rf "$W/sz"
    if [ "$N" = "$4" ]; then ok "$1" "$2 (大小 $N)"; else bad "$1" "$2" "大小 $N 应为 $4"; fi
}

echo "=== ttygif 1.5.0 消费者测试 ==="
echo "bindir=$BINDIR"
ls -la "$BINDIR"
echo "scratch=$W"
echo "imagemagick bindir=${IMBIN:-<未解析>}"
printf 'fixture=%s DISPLAY=[%s] WINDOWID=[%s]\n' "$REC" "${DISPLAY-}" "${WINDOWID-}"

# ─── A 组：CLI 参数语义与错误路径 ───────────────────────────────────────
echo "--- A: CLI 语义与错误路径 ---"

# argc<2 → usage() → exit(EXIT_FAILURE)
"$TTYGIF" > "$W/a1.out" 2>"$W/a1.err" </dev/null
RC=$?
rceq A01 "无参数退出 1" 1 "$RC"
want A02 "无参数打印 usage" "Usage: ttygif" "$W/a1.out"

"$TTYGIF" -h > "$W/a3.out" 2>&1 </dev/null
RC=$?
rceq A03 "-h 退出 0" 0 "$RC"
want A04 "-h 打印 usage" "Usage: ttygif" "$W/a3.out"
want A05 "usage 自述版本开关" "--version" "$W/a3.out"

"$TTYGIF" --help > "$W/a6.out" 2>&1 </dev/null
RC=$?
rceq A06 "--help 退出 0" 0 "$RC"

"$TTYGIF" --version > "$W/a7.out" 2>&1 </dev/null
RC=$?
rceq A07 "--version 退出 0" 0 "$RC"
want A08 "--version 报 1.5.0（补丁 0002 与 tag 对齐）" "^1\.5\.0$" "$W/a7.out"
wantnot A09 "--version 不再报上游遗留的 1.4.0" "1\.4\.0" "$W/a7.out"

# 补丁 0001 把 CLI 早退提到了所有显示相关初始化之前 ⇒ 无头环境也取到版本
sh -c 'unset TMPDIR; unset WINDOWID; exec "$1" "$2"' sh "$TTYGIF" --version \
    > "$W/a10.out" 2>&1 </dev/null
RC=$?
rceq A10 "无 TMPDIR/无 WINDOWID 时 --version 仍退出 0" 0 "$RC"
want A11 "且输出仍是版本号" "^1\.5\.0$" "$W/a10.out"

# 真跑（非 debug）时缺 WINDOWID 必须在读录像之前 fatal
sh -c 'unset WINDOWID; exec "$1" "$2"' sh "$TTYGIF" "$REC" > "$W/a12.out" 2>&1 </dev/null
RC=$?
rceq A12 "缺 WINDOWID 的真回放退出 1" 1 "$RC"
want A13 "报错文案点名 WINDOWID" "WINDOWID environment variable was empty" "$W/a12.out"

# efopen() 走 strerror 分支
WINDOWID=1 "$TTYGIF" "$W/definitely-absent.tty" > "$W/a14.out" 2>&1 </dev/null
RC=$?
rceq A14 "输入文件不存在退出 1" 1 "$RC"
want A15 "efopen 如实报 ENOENT" "No such file" "$W/a14.out"

# ─── B 组：帧暂存目录与 TMPDIR（补丁 0001 的功能面） ────────────────────
echo "--- B: 暂存目录与 TMPDIR ---"

# 同一条命令，差别只在 TMPDIR ⇒ 直接证明补丁确实接管了暂存根目录
sh -c 'unset TMPDIR; unset TMP; unset TEMP; WINDOWID=4242 TTYGIF_DEBUG=1 exec "$1" "$2"' \
    sh "$TTYGIF" "$REC" > "$W/b1.out" 2>&1 </dev/null
RC=$?
printf 'B01 无 TMPDIR 的读数 rc=%s: ' "$RC"
cat "$W/b1.out"
if [ "$RC" = 0 ]; then
    # /tmp 若可写，回落分支就是上游原语义；仍要能跑出抓帧命令
    want B01 "无 TMPDIR 时回落 /tmp 且真跑出抓帧命令" "DEBUG: xwd " "$W/b1.out"
else
    want B02 "无 TMPDIR 时回落 /tmp 并如实失败（本平台 /tmp 只读）" \
        "Failed to create tmp" "$W/b1.out"
fi

WINDOWID=4242 TTYGIF_DEBUG=1 "$TTYGIF" "$REC" > "$W/c.out" 2>&1 </dev/null
RC=$?
rceq B03 "设了 TMPDIR 后 4 帧录像回放退出 0" 0 "$RC"
# 直接拿本脚本自己导出的 TMPDIR（$W）当固定串去比对：ttygif 的 mkdtemp
# 模板是 "$TMPDIR/ttygif.XXXXXX" ⇒ 日志里必须出现 "$W/ttygif." 这个前缀。
# （此前用正则 ttygif-cases[0-9]*/ttygif\. —— 漏了目录名里的字面点号，
#   实际目录是 ttygif-cases.<pid>，[0-9]* 前面少了 `\.` ⇒ 恒不命中。）
wantf B04 "暂存目录确实落在导出的 TMPDIR 下" "$W/ttygif." "$W/c.out"
wantnot B05 "不再出现硬编码的 /tmp 路径" "/tmp/ttygif\." "$W/c.out"
bytes_is B06 "ttyrec 语料 4 帧 × (12 字节头 + 4 字节负载) = 64" "$REC" 64

# ─── C 组：ttyrec 解析 → 逐帧抓帧命令 → GIF 合成命令 ────────────────────
echo "--- C: 帧回放与命令编排 ---"

grep -e "DEBUG: xwd " "$W/c.out" > "$W/xwd" 2>/dev/null
count_is C01 "每帧一条 xwd 抓帧命令（4 帧）" "DEBUG: xwd " "$W/c.out" 4
want C02 "xwd 命令模板与上游一致" "xwd -id 4242 -out " "$W/xwd"
want C03 "Linux 分支抓 .xwd" "\.xwd" "$W/xwd"
want C04 "帧 0 路径" "/0\.xwd" "$W/xwd"
want C05 "帧 1 路径" "/1\.xwd" "$W/xwd"
want C06 "帧 2 路径" "/2\.xwd" "$W/xwd"
want C07 "帧 3 路径" "/3\.xwd" "$W/xwd"
want C08 "GIF 合成命令无限循环" "convert -loop 0" "$W/c.out"
want C09 "GIF 合成命令做图层优化" "-layers Optimize" "$W/c.out"
want C10 "输出名是 tty.gif" "tty\.gif" "$W/c.out"

# 语料时间戳 100.000 / 100.500 / 101.200 / 103.000
# ⇒ 帧间隔 500 / 700 / 1800 ms；ttygif 把毫秒 ×0.1 转成 ImageMagick 的
#   1/100 秒单位 ⇒ 期望 -delay 50.0 / 70.0 / 180.0，末帧再补 100.0。
want C11 "500 ms 间隔换算 -delay 50" "-delay 50\.000000" "$W/c.out"
want C12 "700 ms 间隔换算 -delay 70" "-delay 70\.000000" "$W/c.out"
want C13 "1800 ms 间隔换算 -delay 180" "-delay 180\.000000" "$W/c.out"
want C14 "末帧按 last_frame_delay(1000ms) 补 -delay 100" "-delay 100\.000000" "$W/c.out"
count_is C15 "整条命令恰有 4 个 -delay（3 间隔 + 末帧）" "-delay" "$W/c.out" 4
want C16 "回放结束打印创建提示" "Creating Animated GIF" "$W/c.out"
want C17 "打印的 GIF 命令以 2>&1 收尾（上游形态）" "2>&1" "$W/c.out"

# -s 只缩放帧间隔，不缩放末帧停留时间（argc>=3 才进解析分支）
WINDOWID=4242 TTYGIF_DEBUG=1 "$TTYGIF" "$REC" -s 2.0 > "$W/s2.out" 2>&1 </dev/null
RC=$?
rceq C18 "-s 2.0 回放退出 0" 0 "$RC"
want C19 "-s 2.0 把 500ms 变 250ms" "-delay 25\.000000" "$W/s2.out"
want C20 "-s 2.0 把 1800ms 变 900ms" "-delay 90\.000000" "$W/s2.out"
wantnot C21 "-s 2.0 后不再有未缩放的 -delay 50" "-delay 50\.000000" "$W/s2.out"

# ─── D 组：消费者运行环境 + 打包 ImageMagick 的真实能力面 ───────────────
echo "--- D: 消费者运行环境与图像链能力 ---"

# 故意不用绝对路径：这里验的就是 conanrun 的 PATH 组装
command -v ttygif > "$W/d1" 2>/dev/null
want D01 "ttygif 经 conanrun PATH 可达" "ttygif" "$W/d1"
"$TTYGIF" --version > "$W/d2.out" 2>&1 </dev/null
RC=$?
rceq D02 "打包二进制真加载执行（非 126/127）" 0 "$RC"

if [ -z "$CONV" ] || [ ! -x "$CONV" ] || [ -z "$IDENT" ] || [ ! -x "$IDENT" ]; then
    printf 'D 组依据: 解析到的 imagemagick bindir=%s convert=%s identify=%s\n' \
        "${IMBIN:-<空>}" "${CONV:-<空>}" "${IDENT:-<空>}"
    echo "  convert/identify 的 command -v 读数:"
    command -v convert > "$W/d3" 2>/dev/null
    cat "$W/d3"
    gate_skip D03 "convert 可达性" \
        "imagemagick 的 bin 目录未解析出来（见上一行读数），无法起能力探针"
    gate_skip D04 "identify -list format 能力探针" "无 identify"
    gate_skip D05 "格式表含 GIF 编码行" "无 identify"
    gate_skip D06 "XWD 帧写入/解码（ttygif 真实抓帧格式）" "无 convert"
    gate_skip D07 "ttygif 的编排参数在打包 IM 上真跑通" "无 convert"
    gate_skip D08 "合成产物的 GIF 魔数" "无 convert"
    gate_skip D09 "identify 读出 4 帧" "无 identify"
else
    # convert 是否真的经 conanrun 的 PATH 可达（一手读数，直接进日志）
    command -v convert > "$W/d3" 2>/dev/null
    RC=$?
    printf 'D03 探针: command -v convert rc=%s 读数=' "$RC"
    cat "$W/d3"
    want D03 "convert 经 conanrun PATH 可达（requires run=True 生效）" \
        "convert" "$W/d3"

    # ★ 一手依据：直接问打包的 ImageMagick 自己支持哪些格式，
    #   再据此决定 XWD 那条链是断言还是降级 —— 不猜、不无条件 skip。
    "$IDENT" -list format > "$W/fmt" 2>"$W/fmt.err"
    RC=$?
    rceq D04 "能力探针 identify -list format 退出 0" 0 "$RC"
    printf '    格式表原文行数='
    wc -l < "$W/fmt"
    show "identify 的 stderr（delegates/colors 告警原文）" "$W/fmt.err"
    grep -i -e "xwd" "$W/fmt" > "$W/fmt_xwd" 2>/dev/null
    grep -e "^ *PNG" "$W/fmt" > "$W/fmt_png" 2>/dev/null
    grep -i -e "png" "$W/fmt" > "$W/fmt_png_any" 2>/dev/null
    rd "$W/fmt_xwd"; N_XWD="$N"
    rd "$W/fmt_png"; N_PNG="$N"
    rd "$W/fmt_png_any"; N_PNG_ANY="$N"
    printf '    探针读数: XWD 行=%s 裸 PNG 行=%s（含 APNG 等 png 字样行=%s）\n' \
        "$N_XWD" "$N_PNG" "$N_PNG_ANY"
    show "XWD 命中原文" "$W/fmt_xwd"
    show "裸 PNG 命中原文" "$W/fmt_png"
    show "含 png 字样的全部行" "$W/fmt_png_any"
    want D05 "格式表列有 GIF 编码行（排除整个 ImageMagick 不可用的误判）" \
        "^ *GIF" "$W/fmt"

    # ── XWD 那条链：ttygif 真实落地的是 .xwd 帧，先量写入再量解码 ──
    mkdir -p "$W/frames"
    WRKC=0
    for spec in "0:red" "1:green" "2:blue" "3:gray"; do
        IDX="${spec%%:*}"
        COL="${spec##*:}"
        "$CONV" -size 64x48 "xc:$COL" "$W/frames/$IDX.xwd" > "$W/wframe.log" 2>&1
        if [ $? -ne 0 ]; then
            if [ "$WRKC" = 0 ]; then
                printf '    帧写入失败读数（首帧 %s.xwd，四帧同型，聚合 rc 记 1）:\n' "$IDX"
                sed -n '1,6p' "$W/wframe.log" | sed 's/^/      | /'
            fi
            WRKC=1
        fi
    done
    "$CONV" "$W/frames/0.xwd" "$W/decprobe.gif" > "$W/dec.log" 2>&1
    DECRK=$?
    printf '    .xwd 解码实测 rc=%s 读数:\n' "$DECRK"
    sed -n '1,6p' "$W/dec.log" | sed 's/^/      | /'

    if [ "$N_XWD" = "0" ]; then
        # 依据：格式表内 XWD 行命中 0（上面 show 已打原文），且写入/解码两侧
        # 都实测报错 ⇒ 这条链在**已发布的依赖**上不可用，不是本包缺陷。
        gate_skip D06 "XWD 帧写入与解码（ttygif 的真实抓帧格式）" \
            "identify -list format 全表内 XWD 行命中 ${N_XWD}（原文见上一节 show 块）；convert 写 .xwd 的聚合 rc=${WRKC}；把 .xwd 喂回 convert 的解码 rc=${DECRK}，报错原文见本段行首带 | 的读数。⇒ 已发布的 imagemagick/7.1.2.29 不带 XWD coder，属依赖能力缺口，按红线不在本 PR 里改别的包，也不把 FAIL 抹成无条件 PASS"
    else
        rceq D06 "XWD 帧写入 rc=0" 0 "$WRKC"
    fi

    # ── 编排链：ttygif 发射的那串参数原样跑一遍 ──
    # 输入帧换成 .gif（XWD 不可用，依据见 D06），其余参数与 ttygif 逐字相同：
    # -loop 0 / -delay 50.000000 / -delay 70.000000 / -delay 180.000000 /
    # -delay 100.000000 / -layers Optimize / 输出 tty.gif
    mkdir -p "$W/gframes"
    for spec in "0:red" "1:green" "2:blue" "3:gray"; do
        IDX="${spec%%:*}"
        COL="${spec##*:}"
        "$CONV" -size 64x48 "xc:$COL" "$W/gframes/$IDX.gif" > "$W/mkg.log" 2>&1
    done
    "$CONV" -loop 0 \
        -delay 50.000000 "$W/gframes/0.gif" \
        -delay 70.000000 "$W/gframes/1.gif" \
        -delay 180.000000 "$W/gframes/2.gif" \
        -delay 100.000000 "$W/gframes/3.gif" \
        -layers Optimize "$W/tty.gif" > "$W/d7.out" 2>&1
    RC=$?
    if [ "$RC" != 0 ]; then
        echo "    合成失败读数:"
        sed -n '1,10p' "$W/d7.out" | sed 's/^/      | /'
    fi
    rceq D07 "ttygif 的编排参数（-loop 0/-delay×4/-layers Optimize）在打包 ImageMagick 上真跑通" 0 "$RC"
    DISCOVERED=$((DISCOVERED+1))
    if [ -s "$W/tty.gif" ]; then
        head -c 4 "$W/tty.gif" > "$W/magic"
        if grep -q -e "GIF8" "$W/magic"; then
            ok D08 "GIF 产物存在且魔数正确（字节数见下一行）"
            printf '    tty.gif 字节数='
            wc -c < "$W/tty.gif"
        else
            bad D08 "产物没有 GIF 魔数" "见 $W/d7.out"
        fi
    else
        bad D08 "没有产出 GIF 文件" "见 $W/d7.out"
    fi
    "$IDENT" "$W/tty.gif" > "$W/d9.out" 2>&1
    count_is D09 "identify 对产物报出 4 帧" "tty\.gif\[" "$W/d9.out" 4
fi

# ─── E 组：抓屏面 —— 如实登记未执行，不用桩冒充通过 ────────────────────
echo "--- E: X11 抓屏面（本设备无 X server，登记为未执行项） ---"
WINDOWID=4242 "$TTYGIF" "$REC" > "$W/e1.out" 2>&1 </dev/null
RC=$?
printf 'E01 真机非 debug 全链路 rc=%s，输出：\n' "$RC"
cat "$W/e1.out"
command -v xwd > "$W/e2.out" 2>&1
printf 'E02 直连 xwd 的 command -v 读数：'
cat "$W/e2.out"
grep -e "xwd -id" "$W/c.out" > "$W/e3.out" 2>/dev/null
printf 'E03 ttygif 发射的抓帧命令（来自 DEBUG 读数）：\n'
sed -n '1,2p' "$W/e3.out" | sed 's/^/  | /'
gate_skip E01 "端到端 xwd 抓屏 ⇒ tty.gif" \
    "需要活的 X display 与真实窗口 id：DISPLAY 实测为空（见开头读数），且 xwd 不在制品仓（本任务 conan search xwd -r=ohpcd → Recipe 'xwd' not found；archives/x/xwd/1.0.9 只有 manifest/notes/patches，无 conanfile.py）。按 R36/PF4 不在本 PR 里补依赖，故整条抓屏链如实登记为未执行，不伪造 GIF 断言。"

echo "--- 上游测试框架清点 ---"
echo "HMBS_UPSTREAM_TEST_RESULT={\"status\":\"no_tests\",\"framework\":\"none\",\"command\":\"audit: no upstream test framework\",\"reason\":\"ttygif 1.5.0 ships no test suite (13 files, no tests/ directory, no make check target, no assert framework). The framework extractor was not used because it hardcodes the read-only /tmp; the inventory came from a manual equivalent scan (fresh tarball + sha256 alignment, full listing, six grep markers, find t/tests/test/spec, make -np target dump) kept at reports/upstream-test-scan.txt.\",\"discovered\":0,\"executed\":0,\"passed\":0,\"failed\":0,\"skipped\":0}"

# ─── 账本不变式自检（DISCOVERED = PASS + FAIL + SKIP） ──────────────────
TOTAL=$((PASS + FAIL + SKIP))
echo "=== 汇总 discovered=$DISCOVERED pass=$PASS fail=$FAIL skip=$SKIP 合计=$TOTAL ==="
if [ "$DISCOVERED" != "$TOTAL" ]; then
    echo "FAIL: LEDGER 账本不变式被破坏（discovered=$DISCOVERED != pass+fail+skip=$TOTAL）"
    echo "VERDICT: FAIL"
    exit 1
fi
if [ "$FAIL" -eq 0 ]; then
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"/bin/sh test.sh\",\"discovered\":$DISCOVERED,\"passedCount\":$PASS,\"skipped\":$SKIP}"
    echo "VERDICT: PASS"
    exit 0
fi
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"/bin/sh test.sh\",\"discovered\":$DISCOVERED,\"passedCount\":$PASS,\"skipped\":$SKIP}"
echo "VERDICT: FAIL"
exit 1
