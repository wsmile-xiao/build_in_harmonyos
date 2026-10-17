#!/usr/bin/env bash
# test_package/test_ohos.sh — libsvg-cairo 0.1.6 鸿蒙(OHOS PC aarch64)特有测试
#
# 严格区分三类对象（rule12：验证的是最终 Conan 包产物，而非源码或构建目录）：
#
#   [P] libsvg-cairo.a — 最终 Conan 包产物（conan cache package_folder）。
#       静态归档本身没有 SONAME / PT_INTERP / .code_signature 段，这些 ELF
#       动态元数据只存在于链接后的动态对象上。对 [P] 只做归档级直接验证：
#       ar archive 魔数、非空、成员可提取/遍历、每个成员均为 ELF64
#       little-endian AArch64 REL（可重定位目标文件）。
#   [S] libsvg-cairo-ohos.so.0 — 测试派生的共享库（消费者打包场景模拟）。
#       DT_SONAME、导出符号、NEEDED 等 .so 级断言只施加于 [S]。
#   [E] ohos_svg_check — 消费者可执行文件（OHOS 运行时产物）。
#       PT_INTERP（/lib/ld-musl-aarch64.so.1）、.code_signature 段、
#       NEEDED/RUNPATH 洁净性等只施加于 [E]；真实 SVG 解析 + 渲染由 [E] 完成。
#
# 分层断言清单：
#   A. 定位最终 Conan 包目录（package_folder，经 env 显式传入）
#   B. [P] 归档直接验证：ar magic / 非空 / 成员提取 / 成员 ELF64-LE-AArch64-REL
#   C. [S] 派生共享库链接（--whole-archive）+ ELF64/AArch64/SONAME/导出符号/NEEDED
#   D. [E] 消费者可执行文件链接 + ELF64/AArch64/INTERP/.code_signature/NEEDED
#   E. [E] 在 OHOS PC 上运行真实 SVG 解析 + 渲染流程（ohos_svg_check）
#
# --whole-archive 的边界：仅用于确认包内归档成员确实进入派生产物
# （防止零导出空壳 .so），且要求归档对象满足 PIC（本包 fPIC=True）。
# 非 PIC 静态库不能强行用本方式生成共享库，应改为构建直接引用公开 API
# 的可执行消费者（本脚本的 [E] 链路即该回退形态的保留）。
#
# 任一检查失败 → 非零退出（set -e + 显式断言），无 skip、无静默通过。
set -eu
set -o pipefail

# ── 环境定位 ─────────────────────────────────────────────
# conan test 由 conanfile.py 以 self.run(..., env="conanrun") 调起本脚本，
# 包目录通过 env 显式传入（VirtualRunEnv 不导出 CONAN_LIB_DIRS_*）：
#   OHOS_PKG_LIBDIR = 被测包产物 lib/ 目录（最终包，非构建目录）
#   OHOS_PKG_INCDIR = 被测包 include/ 目录
#   OHOS_DEP_LIBS   = 全部宿主依赖包 lib/ 目录（冒号分隔）
#   OHOS_DEP_INCS   = 全部宿主依赖包 include/ 目录（冒号分隔）
#   OHOS_CC         = 交叉 clang 绝对路径（conanfile.py 取自当前 profile
#                     的 tools.build:compiler_executables["c"]；缺失即 fail，
#                     不做任何硬编码安装位置回退）
#   OHOS_AR         = clang -print-prog-name=llvm-ar 查得的绝对路径（可为空，
#                     空则回退 AR 环境变量 → PATH 中 llvm-ar/ar）
#   OHOS_READELF    = conanfile.py 侧查得的 readelf 绝对路径（可为空，空则
#                     回退 PATH 查找 → clang 同目录推导）
#   OHOS_TOOL_LD_LIBRARY_PATH = 宿主工具链自身运行所需的 LD_LIBRARY_PATH
#       （E429 恢复目录 + conanbuild LD_LIBRARY_PATH，已剔除目标依赖目录）。
#       conanrun 的 LD_LIBRARY_PATH 前置了目标依赖包 lib/ 目录，若宿主
#       clang/lld 继承它，lld 会加载目标包的 libxml2.so.16 并因符号重定位
#       失败而崩（CI #42924）。因此环境按用途分裂：
#         - 宿主工具（clang/lld/llvm-ar/readelf）→ env LD_LIBRARY_PATH=
#           "$OHOS_TOOL_LD_LIBRARY_PATH"，仅工具链自身运行库；
#         - 目标依赖解析 → -L / 绝对库路径 / OHOS_DEP_LIBS，不进入
#           宿主工具的加载路径；
#         - LD_LIBRARY_PATH=目标依赖目录 仅在真正运行目标消费者 [E] 时
#           临时设置（见 E 段）。
PKG_LIBDIR="${OHOS_PKG_LIBDIR:-}"
PKG_INCDIR="${OHOS_PKG_INCDIR:-}"
DEP_LIBS="${OHOS_DEP_LIBS:-}"
DEP_INCS="${OHOS_DEP_INCS:-}"
# 未显式传入时归一化为空串（run_tool 直接引用该变量，set -u 下不得为 unset）
OHOS_TOOL_LD_LIBRARY_PATH="${OHOS_TOOL_LD_LIBRARY_PATH:-}"
[ -n "$PKG_LIBDIR" ] || { echo "[test_ohos] FAIL: OHOS_PKG_LIBDIR not set"; exit 1; }
[ -n "$PKG_INCDIR" ] || { echo "[test_ohos] FAIL: OHOS_PKG_INCDIR not set"; exit 1; }
[ -n "$DEP_LIBS" ] || { echo "[test_ohos] FAIL: OHOS_DEP_LIBS not set"; exit 1; }
[ -n "$DEP_INCS" ] || { echo "[test_ohos] FAIL: OHOS_DEP_INCS not set"; exit 1; }

# [P] 最终 Conan 包产物（静态归档）
SVGC_A="$PKG_LIBDIR/libsvg-cairo.a"
[ -f "$SVGC_A" ] || { echo "[test_ohos] FAIL: package artifact libsvg-cairo.a not found at $SVGC_A"; exit 1; }
echo "[test_ohos] package artifact [P]: $SVGC_A ($(du -h "$SVGC_A" | cut -f1))"

fail()
{
    echo "[test_ohos] FAIL: $1"
    exit 1
}

# ── 工具链 ───────────────────────────────────────────────
# CC 只认 OHOS_CC（conanfile.py 从当前 profile 的
# tools.build:compiler_executables 推导）。不回退 PATH、不硬编码安装位置：
# 一个错误选中的 clang 会产出错误架构/错误 sysroot 的产物，比直接失败更糟。
CC_BIN="${OHOS_CC:-}"
if [ -z "$CC_BIN" ] || [ ! -x "$CC_BIN" ]; then
    echo "[test_ohos] FAIL: OHOS_CC not set or not executable: '${CC_BIN:-<empty>}'"
    echo "[test_ohos]        conanfile.py 应从当前 profile 的 tools.build:compiler_executables 传入交叉 clang"
    exit 1
fi

# readelf：优先 conanfile.py 查得的 OHOS_READELF（可为空）；否则 PATH 查找
# （PATH 本就来自 profile buildenv，不硬编码任何位置）；最后从 clang 所在
# 目录推导同级 readelf/llvm-readelf（工具链目录内的工具与编译器同源）。
READELF_BIN=""
for cand in "${OHOS_READELF:-}" "$(command -v readelf || true)" "$(command -v llvm-readelf || true)" \
            "$(dirname "$CC_BIN")/readelf" "$(dirname "$CC_BIN")/llvm-readelf"; do
    [ -n "$cand" ] || continue
    if [ -x "$cand" ]; then
        READELF_BIN="$cand"
        break
    fi
done
[ -n "$READELF_BIN" ] && [ -x "$READELF_BIN" ] || { echo "[test_ohos] FAIL: no usable readelf (OHOS_READELF unset, not on PATH, not beside clang at $(dirname "$CC_BIN"))"; exit 1; }

# ar（binutils 或 llvm-ar 均可）：用于静态归档直接验证。
# 解析顺序（编译器指名的工具优先，PATH 回退在后）：
#   1. OHOS_AR — conanfile.py 用 clang -print-prog-name=llvm-ar 查得的、
#      与 OHOS 交叉编译器配套的 llvm-ar 绝对路径
#   2. AR — 环境注入的 ar/llvm-ar（可能是命令名，也可能是路径）
#   3. PATH 中的 llvm-ar
#   4. PATH 中的 ar
# 注意：命令名（非绝对路径）必须先经 command -v 解析为可执行路径，
# 不能直接对相对命令名做 -x 文件判断（CI 中 AR=llvm-ar 即相对名）。
# 编译器指名的工具不可用时，继续向后回退；最终仍无可用工具则 fail。
AR_BIN=""
for cand in "${OHOS_AR:-}" "${AR:-}" "$(command -v llvm-ar || true)" "$(command -v ar || true)"; do
    [ -n "$cand" ] || continue
    case "$cand" in
        /*) resolved="$cand" ;;
        *)  resolved="$(command -v "$cand" 2>/dev/null || true)" ;;
    esac
    if [ -n "$resolved" ] && [ -x "$resolved" ]; then
        AR_BIN="$resolved"
        break
    fi
done
[ -n "$AR_BIN" ] && [ -x "$AR_BIN" ] || { echo "[test_ohos] FAIL: no usable ar (binutils or llvm-ar)"; exit 1; }
echo "[test_ohos] CC=$CC_BIN READELF=$READELF_BIN AR=$AR_BIN"

# 宿主工具运行环境分裂（CI #42924）：clang/lld/llvm-ar/readelf 是宿主
# 二进制，其自身的共享库解析必须走 OHOS_TOOL_LD_LIBRARY_PATH（仅含
# 工具链运行库目录），绝不能继承 conanrun 的 LD_LIBRARY_PATH（其中
# 前置了目标依赖目录，lld 会因此加载目标包 libxml2.so.16 而崩）。
# 下面所有宿主工具调用统一经 run_tool 包装。
run_tool()
{
    env LD_LIBRARY_PATH="$OHOS_TOOL_LD_LIBRARY_PATH" "$@"
}

# ── 工作目录（脚本自身所在处，conan test 会把 test_package/ 作为 source_folder）──
WORK="$(cd "$(dirname "$0")" && pwd)"
OUT="$WORK/ohos_check_out"
rm -rf "$OUT"; mkdir -p "$OUT"

# ── B. [P] 静态归档直接验证 ──────────────────────────────
# 对包产物本身的检查：ar archive 魔数、非空、成员提取遍历、
# 成员为 ELF64 little-endian AArch64 REL 可重定位目标文件。
# 静态归档没有 SONAME/INTERP/.code_signature —— 那些断言见 [S]/[E]。
echo "[test_ohos] verifying package static archive [P] directly..."

# B1. ar archive 魔数（!<arch>\n）
magic="$(head -c 8 "$SVGC_A")"
[ "$magic" = "!<arch>" ] || fail "package artifact is not an ar archive (magic: '$magic')"

# B2. 归档非空（成员列表至少 1 个目标文件）
members="$(run_tool "$AR_BIN" t "$SVGC_A")"
n_members="$(echo "$members" | grep -c . || true)"
[ "$n_members" -ge 1 ] || fail "package archive has no members"
echo "[test_ohos] [P] ar archive OK: $n_members member(s)"

# B3. 提取每个成员并验证 ELF 头
MEM_DIR="$OUT/archive_members"
mkdir -p "$MEM_DIR"
echo "$members" | while IFS= read -r m; do
    [ -n "$m" ] || continue
    run_tool "$AR_BIN" p "$SVGC_A" "$m" > "$MEM_DIR/$m" 2>/dev/null || { echo "[test_ohos] FAIL: cannot extract member $m"; exit 1; }
    mh="$(run_tool "$READELF_BIN" -h "$MEM_DIR/$m")"
    echo "$mh" | grep -q "Class:.*ELF64" || { echo "[test_ohos] FAIL: member $m not ELF64"; exit 1; }
    echo "$mh" | grep -q "Data:.*little endian" || { echo "[test_ohos] FAIL: member $m not little-endian"; exit 1; }
    echo "$mh" | grep -q "Type:.*REL" || { echo "[test_ohos] FAIL: member $m not a relocatable object"; exit 1; }
    echo "$mh" | grep -q "Machine:.*AArch64" || { echo "[test_ohos] FAIL: member $m not AArch64"; exit 1; }
    echo "[test_ohos] [P] member $m: ELF64 LE REL AArch64 OK"
done
# 子 shell while 中的 exit 1 会作为管道退出码传出（pipefail 已设置）
[ -d "$MEM_DIR" ] || fail "member extraction dir missing"

# ── 依赖库目录（用于链接共享库时的 -L 搜索路径）────────────
# OHOS_DEP_LIBS 给出全部依赖包 lib 目录（冒号分隔）
LIB_SEARCH_FLAGS=""
IFS=':' read -r -a libdirs <<< "$DEP_LIBS"
for d in "${libdirs[@]}"; do
    [ -n "$d" ] && LIB_SEARCH_FLAGS="$LIB_SEARCH_FLAGS -L$d"
done
[ -n "$LIB_SEARCH_FLAGS" ] || { echo "[test_ohos] FAIL: no dependency lib dirs — cannot resolve deps"; exit 1; }

# 依赖共享库运行时路径（OHOS PC 上依赖 so 的实际位置）
RUN_LD_PATHS=""
for d in "${libdirs[@]}"; do
    [ -n "$d" ] && RUN_LD_PATHS="$RUN_LD_PATHS:$d"
done

# ── C. [S] 从包产物链接派生共享库 ────────────────────────
# 场景：消费者把 libsvg-cairo.a（静态库包）打进自己的 .so。
# --whole-archive 仅用于确认归档成员确实进入派生产物（防零导出空壳），
# 前提是归档对象满足 PIC（本包 fPIC=True）；非 PIC 静态库应改走
# 可执行消费者路径（见 [E]），不得强行生成共享库。
# 传递依赖（libsvg.a、libjpeg.a 等）由 conanrun 环境给出，缓存中均为静态库
# 时直接并入；全部 svg_cairo_* 符号必须来自包内 libsvg-cairo.a。
SO="$OUT/libsvg-cairo-ohos.so.0"
SONAME="libsvg-cairo-ohos.so.0"

# 链接失败三分类诊断（CI #42924 的教训：lld 崩溃曾被误报为归档非 PIC，
# 所以三类必须互斥判定，先看宿主加载器错误，再看 lld 自身的诊断）：
#   (a) 链接器无法启动 —— musl 加载器报 "Error loading shared library" /
#       "Error relocating"，发生在任何链接活动之前，lld 诊断一条都没有；
#   (b) 目标库非 PIC —— lld 报 "relocation R_* ... cannot be used ...
#       recompile with -fPIC"；
#   (c) 符号未解析 —— lld 报 "undefined symbol: ..."。
# 先把完整工具输出落盘再分类，保证真实错误始终可见。
LINK_LOG="$OUT/link_shared.log"
echo "[test_ohos] linking derived shared lib [S] from package artifact..."
DEP_STATICS=""
for d in "${libdirs[@]}"; do
    for a in "$d"/libsvg.a "$d"/libjpeg.a; do
        [ -f "$a" ] && DEP_STATICS="$DEP_STATICS $a"
    done
done
# 去重
DEP_STATICS="$(echo $DEP_STATICS | tr ' ' '\n' | sort -u | tr '\n' ' ')"
echo "[test_ohos] bundled static deps: ${DEP_STATICS:-<none>}"

link_rc=0
run_tool "$CC_BIN" -shared -Wl,-soname,"$SONAME" -o "$SO" \
    -Wl,--whole-archive "$SVGC_A" -Wl,--no-whole-archive \
    $DEP_STATICS $LIB_SEARCH_FLAGS \
    -lcairo -lxml2 -lpng16 -lfreetype -lfontconfig -lpixman-1 -lz -lpthread -lm -ldl \
    >"$LINK_LOG" 2>&1 || link_rc=$?

if [ "$link_rc" -ne 0 ]; then
    # 失败也把真实工具输出原样吐给 CI 日志（cat 不受 set -e 影响）。
    # 分类只基于 lld/加载器自己的签名，互相排斥，谁先命中报谁：
    # 加载器签名（a）要求 lld 一条诊断都没有；lld 诊断（b/c）再按
    # relocation/undefined 区分。都 miss 就不猜，原文兜底。
    cat "$LINK_LOG"

    # 各类签名的原始 grep（分类与提取共用，保证互斥且不重复匹配）。
    # 加载器签名（a）单独判；lld 自身诊断（b/c）在判之前先剔除加载器行
    # —— glibc 加载器也会写 "symbol lookup error: undefined symbol: ..."，
    # 那是宿主加载失败，不是 lld 的链接诊断，绝不能归进 (c)（CI #42924
    # 的教训：加载器层面的错误曾被误报成目标代码 non-PIC）。
    loader_line_re="Error loading shared library|Error relocating|symbol lookup error"
    # (a) 的判定签名 = musl 两种措辞 + glibc 的加载期符号查找失败
    # （"symbol lookup error" 只在加载器层面出现，lld 不会这样写）
    loader_sig="$(grep -E "$loader_line_re" "$LINK_LOG" || true)"
    pic_sig="$(grep -E "relocation R_[A-Za-z0-9_]+ (against symbol|in module)|can ?not be used when making a shared object|recompile with -fPIC" "$LINK_LOG" | grep -vE "$loader_line_re" || true)"
    undef_sig="$(grep -E "undefined symbol:|undefined reference to" "$LINK_LOG" | grep -vE "$loader_line_re" || true)"

    # (a) [host-tool-env] 链接器无法启动：musl/glibc 加载器在 lld 任何
    #     链接活动之前就报错（rc=127/126，或 "Error loading shared
    #     library" / "Error relocating"）。若 lld 已给出自身诊断
    #     （relocation/undefined），说明链接器本体起来了，不属此类。
    if { [ -n "$loader_sig" ] || [ "$link_rc" -eq 127 ] || [ "$link_rc" -eq 126 ]; } \
       && [ -z "$pic_sig" ] && [ -z "$undef_sig" ]; then
        echo "[test_ohos] FAIL [host-tool-env]: linker/loader could not start — host tool dynamic-library environment is polluted or incomplete (exit $link_rc)"
        if [ -n "$loader_sig" ]; then
            echo "[test_ohos]        loader errors:"
            echo "$loader_sig" | sed "s/^/[test_ohos]          /"
        else
            echo "[test_ohos]        no loader error captured — exit $link_rc is a command-not-found / not-executable signature"
        fi
        echo "[test_ohos]        ---- LD_LIBRARY_PATH diff (host tool env vs inherited conanrun env) ----"
        echo "[test_ohos]        [tool] LD_LIBRARY_PATH applied to host tools (OHOS_TOOL_LD_LIBRARY_PATH): ${OHOS_TOOL_LD_LIBRARY_PATH:-<empty>}"
        echo "[test_ohos]        [run ] LD_LIBRARY_PATH this script inherited (conanrun, TARGET deps first): ${LD_LIBRARY_PATH:-<empty>}"
        echo "[test_ohos]        target dependency dirs that must NEVER be in the host tool path (OHOS_DEP_LIBS): $DEP_LIBS"
        # 逐条点名 conanrun 环境里有、而工具环境里没有的目录（即被剔除/
        # 泄漏的差异），让“污染”落到具体目录上
        IFS=':' read -r -a _tool_dirs <<< "${OHOS_TOOL_LD_LIBRARY_PATH:-}"
        IFS=':' read -r -a _run_dirs <<< "${LD_LIBRARY_PATH:-}"
        _diff_shown=0
        for d in "${_run_dirs[@]}"; do
            [ -n "$d" ] || continue
            _in_tool=0
            for t in "${_tool_dirs[@]}"; do
                [ "$t" = "$d" ] && { _in_tool=1; break; }
            done
            if [ "$_in_tool" -eq 0 ]; then
                [ "$_diff_shown" -eq 0 ] && echo "[test_ohos]        dirs present in conanrun env but NOT in the host tool env:"
                echo "[test_ohos]          $d"
                _diff_shown=1
            fi
        done
        echo "[test_ohos]        宿主工具（clang/lld/llvm-ar/readelf）的运行库环境必须来自 profile [buildenv] / conanbuild"
        echo "[test_ohos]        （经 OHOS_TOOL_LD_LIBRARY_PATH 注入），绝不能继承 conanrun 前置的目标依赖 lib/ 目录"
        echo "[test_ohos]        （CI #42924：宿主 lld 解析到目标侧 libxml2.so.16，17 行 xml* symbol not found，启动即崩，曾被误报为 non-PIC）"
        exit 1
    fi

    # (b) [non-PIC] 目标库非 PIC：lld 自身的 relocation 诊断。
    if [ -n "$pic_sig" ]; then
        echo "[test_ohos] FAIL [non-PIC]: package archive contains non-PIC members — lld relocation rejected while making a shared object (recompile with -fPIC)"
        echo "[test_ohos]        relocation errors:"
        echo "$pic_sig" | sed "s/^/[test_ohos]          /"
        # 涉事成员：lld 的 file:line 定位里形如 .../libX.a(member.o)；
        # 提取不到（如某些 lld 版本只在 file 一栏给 .o）就说明并列出
        # 裸 .o 名，仍取不到则不硬造。
        pic_members="$(grep -E -A 4 "relocation R_[A-Za-z0-9_]+ |can ?not be used when making a shared object|recompile with -fPIC" "$LINK_LOG" | grep -oE "[^[:space:]]+\.a\([^()]*\)" | sort -u || true)"
        if [ -n "$pic_members" ]; then
            echo "[test_ohos]        offending archive members:"
            echo "$pic_members" | sed "s/^/[test_ohos]          /"
        else
            pic_objs="$(grep -E -A 4 "relocation R_[A-Za-z0-9_]+ " "$LINK_LOG" | grep -oE "[^[:space:]()/]+\.o" | sort -u | head -20 || true)"
            if [ -n "$pic_objs" ]; then
                echo "[test_ohos]        offending object files (member names not in an archive reference):"
                echo "$pic_objs" | sed "s/^/[test_ohos]          /"
            else
                echo "[test_ohos]        (could not extract member names from the linker output; see relocation errors above)"
            fi
        fi
        exit 1
    fi

    # (c) [undefined-symbols] 符号未解析：lld 末尾的 undefined symbol
    #     清单，封顶前 20 个（去重后）。注意这是 lld 自身诊断，说明
    #     链接器起来了、加载器没坑，与 (a) 互斥。
    if [ -n "$undef_sig" ]; then
        echo "[test_ohos] FAIL [undefined-symbols]: linker started but symbols stayed unresolved (exit $link_rc; see linker output above)"
        # lld: "undefined symbol: xmlFree"；GNU ld: "undefined reference to `xmlFree'"
        # （加载器行已在 undef_sig 判定时剔除，这里从原文提取后同样过滤）
        {
            grep -E "undefined symbol:|undefined reference to" "$LINK_LOG" | grep -vE "$loader_line_re" \
                | grep -oE "undefined symbol: [^[:space:]]+" | sed "s/^undefined symbol: //" || true
            grep -E "undefined symbol:|undefined reference to" "$LINK_LOG" | grep -vE "$loader_line_re" \
                | grep -oE "undefined reference to \`[^[:space:]]+'" | sed "s/^undefined reference to \`//;s/'\$//" || true
        } | sort -u | head -20 | sed "s/^/[test_ohos]        undefined: /"
        exit 1
    fi

    # 加载器/链接器签名都没匹配上：不猜原因，原文已 cat，指回即可。
    fail "cannot link derived shared lib from package archive (exit $link_rc; no loader/non-PIC/undefined-symbol signature matched — see raw tool output above)"
fi
[ -f "$SO" ] || fail "derived shared lib not produced"
ln -sf "$(basename "$SO")" "$OUT/libsvg-cairo-ohos.so"

# ── C. [S] 派生共享库 ELF 断言 ──────────────────────────
hdr="$(run_tool "$READELF_BIN" -h "$SO")"
echo "$hdr" | grep -q "Class:.*ELF64" || fail "derived shared lib not ELF64"
echo "$hdr" | grep -q "Machine:.*AArch64" || fail "derived shared lib not AArch64"
echo "[test_ohos] ELF64/AArch64 OK (shared lib [S])"

# SONAME 与实际文件一致（DT_SONAME 只属于派生共享库，不属于静态包）
dyn="$(run_tool "$READELF_BIN" -d "$SO")"
echo "$dyn" | grep -q "(SONAME).*libsvg-cairo-ohos\.so\.0" || fail "derived shared lib SONAME mismatch/missing"
echo "[test_ohos] SONAME OK: $SONAME"

# svg_cairo 符号确实来自包内静态库（--whole-archive 防空壳的目的所在：
# 确认归档成员确实进入派生产物，而非零导出空壳）
NDYN="$(run_tool "$READELF_BIN" --dyn-syms "$SO" | grep -c svg_cairo || true)"
[ "$NDYN" -ge 5 ] || fail "derived shared lib exports <5 svg_cairo symbols ($NDYN) — package artifact not really linked in"
echo "[test_ohos] svg_cairo symbols exported: $NDYN"

# NEEDED 不得包含宿主机路径
while IFS= read -r line; do
    lib="$(echo "$line" | sed 's/.*\[\(.*\)\]/\1/')"
    case "$lib" in
        /storage/*|/home/*|/tmp/*|/root/*|/Users/*|/mnt/*)
            fail "derived shared lib NEEDED contains host path: $lib" ;;
    esac
done < <(echo "$dyn" | grep "(NEEDED)" || true)
echo "[test_ohos] NEEDED host-path scan OK (shared lib [S])"

# ── D. 链接消费者可执行文件（OHOS 运行时消费者产物）──────
BIN="$OUT/ohos_svg_check"
INC_FLAGS="-I$PKG_INCDIR"
# svg-cairo.h includes svg.h / cairo.h：依赖包 include 目录（冒号分隔）。
# cairo 头文件在 include/cairo/ 子目录（cairo.h 用 <cairo.h> 引用时需
# 额外加 include/cairo 本身）。
IFS=':' read -r -a incdirs <<< "$DEP_INCS"
for d in "${incdirs[@]}"; do
    case "$d" in
        "$PKG_INCDIR") ;;
        *) [ -n "$d" ] && INC_FLAGS="$INC_FLAGS -I$d"
           [ -d "$d/cairo" ] && INC_FLAGS="$INC_FLAGS -I$d/cairo" ;;
    esac
done

# 不用 -Wl,-rpath：DT_RUNPATH 会嵌入本机 OUT 目录（/storage/... 宿主路径），
# 运行期改用 LD_LIBRARY_PATH 定位派生库（见 [E]）。
# 目标依赖经 -L/$LIB_SEARCH_FLAGS（来自 OHOS_DEP_LIBS）解析，不进入
# 宿主工具的 LD_LIBRARY_PATH（环境分裂，见 run_tool）。
run_tool "$CC_BIN" $INC_FLAGS -I"$WORK" \
    "$WORK/ohos_svg_check.c" -o "$BIN" \
    -L"$OUT" -lsvg-cairo-ohos \
    $LIB_SEARCH_FLAGS -lcairo \
    || fail "cannot link consumer executable (see tool/linker errors above)"
[ -x "$BIN" ] || fail "consumer binary not produced"

# ── D. [E] 消费者可执行文件 ELF 断言 ────────────────────
hdr2="$(run_tool "$READELF_BIN" -h "$BIN")"
echo "$hdr2" | grep -q "Class:.*ELF64" || fail "consumer binary not ELF64"
echo "$hdr2" | grep -q "Machine:.*AArch64" || fail "consumer binary not AArch64"

# PT_INTERP 只属于消费者可执行文件（静态归档没有 INTERP）
interp="$(run_tool "$READELF_BIN" -l "$BIN" | grep "Requesting program interpreter" || true)"
echo "$interp" | grep -q "/lib/ld-musl-aarch64\.so\.1" || fail "consumer binary INTERP is not OHOS musl loader: $interp"
echo "[test_ohos] INTERP OK: $(echo "$interp" | sed 's/^.*interpreter: //;s/^ *//')"

# .code_signature 段：OHOS lld 对消费者链接生成的动态对象（.so/可执行文件）
# 注入的签名段。实测 readelf -SW 段名为 .codesign（即 code signature 段，
# 编号 .code_signature 在工具输出中显示为 .codesign）。
# 该断言只适用于消费者链接产物，静态归档本身没有此段。
# 注意 grep 必须用 -E：OHOS 的 grep 是 toybox，BRE 不支持 \| 交替
# （"A\|B" 恒失配，得到假失败）。
run_tool "$READELF_BIN" -SW "$BIN" | grep -qE "\.code_signature|\.codesign" || fail "consumer binary has no .code_signature/.codesign section"
echo "[test_ohos] .code_signature OK (consumer binary [E])"

dyn2="$(run_tool "$READELF_BIN" -d "$BIN")"
echo "$dyn2" | grep -q "(NEEDED).*libsvg-cairo-ohos\.so\.0" || fail "consumer binary does not depend on libsvg-cairo-ohos.so.0"
while IFS= read -r line; do
    lib="$(echo "$line" | sed 's/.*\[\(.*\)\]/\1/')"
    case "$lib" in
        /storage/*|/home/*|/tmp/*|/root/*|/Users/*|/mnt/*)
            fail "consumer binary NEEDED contains host path: $lib" ;;
    esac
done < <(echo "$dyn2" | grep "(NEEDED)" || true)
echo "[test_ohos] NEEDED host-path scan OK (consumer binary [E])"

# RPATH/RUNPATH 不得指向宿主机路径（未注入 rpath 时应无该条目）
rpaths="$(echo "$dyn2" | grep -E '\((RPATH|RUNPATH)\)' || true)"
if [ -n "$rpaths" ]; then
    case "$rpaths" in
        *"/storage/"*|*"/home/"*|*"/Users/"*|*"/tmp/"*)
            fail "consumer binary RUNPATH contains host path: $rpaths" ;;
    esac
fi

# ── E. [E] OHOS PC 上运行真实 SVG 解析 + 渲染 ────────────
# 只有此刻才设置目标运行时 LD_LIBRARY_PATH：链接出的 .so + 依赖 so 目录
# （OHOS_DEP_LIBS）。目标依赖目录只进入目标进程的加载路径，不回灌给
# 宿主工具（见 run_tool 的环境分裂，CI #42924）。
echo "[test_ohos] running real SVG parse + render on OHOS PC..."
rc=0
LD_LIBRARY_PATH="$OUT${RUN_LD_PATHS:+$RUN_LD_PATHS}" "$BIN" || rc=$?
[ "$rc" -eq 0 ] || fail "ohos_svg_check exited $rc"

echo "[test_ohos] ALL OHOS-SPECIFIC CHECKS PASSED"
exit 0
