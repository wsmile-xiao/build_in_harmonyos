#!/bin/sh
# bats-shim.sh — atools-apkbuild-lint OHOS 适配专用的最小 BATS 兼容驱动。
#
# 上游 atools 的测试套件是 5 个 bats 文件（tests/*.bats，共 224 个 @test 用例），
# 官方通过 `redo check -> bats --tap` 执行。OHOS 工具链没有 bats（也没有网络
# 安装渠道），因此本脚本以 bats-core 的语义子集直接驱动这些 .bats 文件：
#
#   - 预处理：把 `@test 'name' { ... }` 块逐行改写成函数定义 + 名称登记；
#     heredoc（cat <<-EOF）内容、整行注释一律原样保留，不做任何解析。
#   - 运行时内置：run / skip / $status / $output / ${lines[@]} / $BATS_TMPDIR。
#   - 每个用例在独立子 shell 中以 `set -e` 执行（与 bats 一致，断言失败即失败）。
#   - 输出 TAP 行 + 汇总标记，供 conan 配方解析生成 HMBS_UPSTREAM_TEST_RESULT。
#
# 仅实现上游套件实际用到的特性；不追求完整 bats-core 兼容。
#
# 方言约束（R2 真机修复）：OHOS 没有 GNU bash；PATH 里名为 bash 的往往是
# mksh/toybox sh 别名。真机日志显示 mksh 在 `[[ =~ ]]` 处报
# "syntax error: unexpected operator/operand '=~'"。因此本脚本只使用
# mksh/bash/ksh93 共同支持的构造：
#   - 有：数组 x=(..) / x+=(..)、${x[i]}、${#x[@]}、[[ ... ]]、local、$( )
#   - 无：=~ 正则、mapfile、<<< here-string、$'..'、for ((;;))、进程替换
# 上游用例体恰好也只用 [[ ]] 与 ${lines[N]}（已对 5 个套件逐行审计），与该
# 方言集合吻合；调用方（conanfile._resolve_shell）负责用探针确保解释器具备
# 这些能力，dash/纯 busybox ash 等无数组 shell 会被显式拒绝。

set -u

usage() {
    printf 'usage: %s [--tap] <file.bats> [file.bats ...]\n' "$0" >&2
    exit 2
}

# 常用字符变量（避免 $'\t' 等 bash/mksh 才有的 ANSI-C 引号）
SP=' '
TAB='	'
NL='
'

strip_left() {
    # $1 -> STRIP_LEFT（去掉前导空格/制表符）
    _s="$1"
    while :; do
        case "$_s" in
            "$SP"*) _s="${_s#"$SP"}" ;;
            "$TAB"*) _s="${_s#"$TAB"}" ;;
            *) break ;;
        esac
    done
    STRIP_LEFT="$_s"
}

strip_both() {
    # $1 -> STRIP_BOTH（去掉前导与尾随空格/制表符）
    strip_left "$1"
    _s="$STRIP_LEFT"
    while :; do
        case "$_s" in
            *"$SP") _s="${_s%"$SP"}" ;;
            *"$TAB") _s="${_s%"$TAB"}" ;;
            *) break ;;
        esac
    done
    STRIP_BOTH="$_s"
}

files=()
for arg in "$@"; do
    case "$arg" in
        --tap) ;;
        -h|--help) usage ;;
        -*) printf '%s: unknown option: %s\n' "$0" "$arg" >&2; exit 2 ;;
        *) files+=("$arg") ;;
    esac
done
[ "${#files[@]}" -gt 0 ] || usage

# 临时目录链：配方注入的 BATS_TMPDIR（conan build 目录下，可写）优先，
# 再退 HMBS 注入的 TMPDIR/TMP/TEMP；最后兜底为当前目录（HMBS 真机 /tmp 只读）
: "${BATS_TMPDIR:=${TMPDIR:-${TMP:-${TEMP:-.}}}}"
export BATS_TMPDIR

WORK_DIR=""
mkworkdir() {
    _d=""
    if command -v mktemp >/dev/null 2>&1; then
        _d="$(mktemp -d "$BATS_TMPDIR/bats-shim.XXXXXXXX" 2>/dev/null)" || _d=""
    fi
    if [ -z "$_d" ]; then
        # mktemp 缺失或模板不受支持时手工建目录（$$ 保证并发不冲突）
        _n=0
        while :; do
            _d="$BATS_TMPDIR/bats-shim.$$.$_n"
            mkdir "$_d" 2>/dev/null && break
            _n=$((_n + 1))
            if [ "$_n" -gt 100 ]; then
                printf 'bats-shim: cannot create work dir under %s\n' "$BATS_TMPDIR" >&2
                return 1
            fi
        done
    fi
    WORK_DIR="$_d"
}
mkworkdir || exit 2
trap 'rm -rf "$WORK_DIR"' EXIT

# 执行集排除名单：BATS_EXCLUDE 内每行一个精确用例名。被排除的用例不执行、
# 不计数（不计入 discovered/passed/failed/skipped），仅打印注释行留痕。
# 用于上游作者以无条件 skip() 禁用的用例（见 test_package/MANIFEST.yml
# upstream_test_audit），语义与 abuild 配方的 ATF_EXCLUDE_CASES 一致。
bats_exclude=()
_ex_rest="${BATS_EXCLUDE:-}"
while [ -n "$_ex_rest" ]; do
    case "$_ex_rest" in
        *"$NL"*)
            _ex="${_ex_rest%%"$NL"*}"
            _ex_rest="${_ex_rest#*"$NL"}"
            ;;
        *)
            _ex="$_ex_rest"
            _ex_rest=""
            ;;
    esac
    [ -n "$_ex" ] && bats_exclude+=("$_ex")
done

is_excluded() {
    _name="$1"
    _i=0
    while [ "$_i" -lt "${#bats_exclude[@]}" ]; do
        [ "${bats_exclude[$_i]}" = "$_name" ] && return 0
        _i=$((_i + 1))
    done
    return 1
}

# ---------------------------------------------------------------------------
# 内置命令（先于 source 定义，测试文件内的同名辅助函数可按需覆盖）
# ---------------------------------------------------------------------------

RUN_OUT_FILE="$WORK_DIR/run.out"

# bats 语义：捕获 stdout(+stderr) 到 $output，退出码到 $status，按行拆分到
# $lines[]。run 本身永远返回 0，断言交给后续语句（配合 set -e）。
# 拆行经临时文件完成（printf %s 逐字节保真，不经任何二次展开；
# heredoc/here-string 会把捕获输出再过一遍展开器并依赖 /tmp 临时文件，均不可用）。
run() {
    status=0
    output=$("$@" 2>&1) || status=$?
    lines=()
    printf '%s\n' "$output" > "$RUN_OUT_FILE"
    while IFS= read -r _l || [ -n "$_l" ]; do
        lines+=("$_l")
    done < "$RUN_OUT_FILE"
    return 0
}

# bats 语义：跳过当前用例；原因经 fd3 带出（fd3 由执行器重定向到标记文件）。
skip() {
    printf '%s\n' "${*:-skipped}" >&3
    exit 0
}

# ---------------------------------------------------------------------------
# 预处理：@test 块 -> 函数定义
# ---------------------------------------------------------------------------

# 检测一行是否是 heredoc 开始（<<[-]DELIM，DELIM 允许带引号）。
# 命中时设置 HD_DASH(0/1) 与 HD_DELIM 并返回 0；否则返回 1。
detect_heredoc_start() {
    _s="$1"
    HD_DELIM=""
    HD_DASH=0
    case "$_s" in
        *"<<"*) ;;
        *) return 1 ;;
    esac
    _r="${_s#*<<}"
    case "$_r" in
        "-"*) HD_DASH=1; _r="${_r#-}" ;;
    esac
    while :; do
        case "$_r" in
            "$SP"*) _r="${_r#"$SP"}" ;;
            "$TAB"*) _r="${_r#"$TAB"}" ;;
            *) break ;;
        esac
    done
    case "$_r" in
        \"*\")
            _d="${_r#\"}"
            _d="${_d%%\"*}"
            ;;
        \'*\')
            _d="${_r#\'}"
            _d="${_d%%\'*}"
            ;;
        [A-Za-z_]*)
            _d="${_r%%[!A-Za-z0-9_]*}"
            ;;
        *)
            return 1
            ;;
    esac
    case "$_d" in
        "") return 1 ;;
    esac
    HD_DELIM="$_d"
    return 0
}

# 逐行读取 $1，改写结果写入 $2：
#   "@test <quoted-name> {"  ->  bats_names+=(<quoted-name>)
#                                bats_test_<N>() {
#   独立的 "}"（处于某个 @test 块内）-> "}"（结束函数定义）
#   其余行原样保留。
# heredoc 跟踪：出现 "<<[-]DELIM" 后进入 heredoc，直到（对 <<- 去除行首制表符后）
# 等于 DELIM 的行为止；heredoc 内容不改写。整行注释不改写也不改变状态
# （上游有整段注释掉的 XFAIL @test，必须忽略）。
# $3 为跨文件延续的起始编号偏移；回显本文件的 @test 数量。
preprocess() {
    local src="$1" dst="$2" offset="${3:-0}"
    local in_heredoc=0 hd_dash=0 delim=
    local n=$offset inside=0
    local line trimmed s is_test rest name _s _r _d
    : > "$dst"
    while IFS= read -r line || [ -n "$line" ]; do
        if [ "$in_heredoc" -eq 1 ]; then
            if [ "$hd_dash" -eq 1 ]; then
                trimmed="$line"
                # <<- 允许前导制表符，逐个剥除
                while :; do
                    case "$trimmed" in
                        "$TAB"*) trimmed="${trimmed#"$TAB"}" ;;
                        *) break ;;
                    esac
                done
            else
                trimmed="$line"
            fi
            if [ "$trimmed" = "$delim" ]; then
                in_heredoc=0
            fi
            printf '%s\n' "$line" >> "$dst"
            continue
        fi

        strip_both "$line"

        # 整行注释：原样保留（可能是注释掉的 @test/heredoc）
        case "$STRIP_BOTH" in
            '#'*)
                printf '%s\n' "$line" >> "$dst"
                continue
                ;;
        esac

        # heredoc 开始？
        if detect_heredoc_start "$line"; then
            hd_dash=$HD_DASH
            delim=$HD_DELIM
            in_heredoc=1
            printf '%s\n' "$line" >> "$dst"
            continue
        fi

        # @test 开始？（名字连同其原始引号整体登记，供排除名单精确匹配）
        s="$STRIP_BOTH"
        is_test=0
        case "$s" in
            "@test"*)
                rest="${s#'@test'}"
                strip_left "$rest"
                rest="$STRIP_LEFT"
                case "$rest" in
                    "{"|""|*"{"*) is_test=1 ;;
                esac
                ;;
        esac
        if [ "$is_test" -eq 1 ]; then
            name="${rest%"{"}"
            strip_both "$name"
            name="$STRIP_BOTH"
            if [ -n "$name" ]; then
                n=$((n + 1))
                inside=1
                printf 'bats_names+=(%s)\n' "$name" >> "$dst"
                printf 'bats_test_%s() {\n' "$n" >> "$dst"
                continue
            fi
        fi

        # @test 块的结束 "}"？
        if [ "$inside" -eq 1 ] && [ "$s" = "}" ]; then
            inside=0
            printf '}\n' >> "$dst"
            continue
        fi

        printf '%s\n' "$line" >> "$dst"
    done < "$src"
    printf '%s\n' "$((n - offset))"
}

# ---------------------------------------------------------------------------
# 执行
# ---------------------------------------------------------------------------

bats_names=()
passed_total=0
failed_total=0
skipped_total=0
excluded_total=0

exec_test() {
    idx="$1"
    fn="bats_test_${idx}"
    name="${bats_names[idx - 1]}"
    marker="$WORK_DIR/marker.$idx"
    outfile="$WORK_DIR/out.$idx"
    : > "$marker"
    # 与 bats 一致：用例体运行在 set -e 下；不启用 -u（bats 同样不启用）
    ( set -e; set +u; "$fn" ) > "$outfile" 2>&1 3> "$marker"
    rc=$?
    if [ -s "$marker" ]; then
        skipped_total=$((skipped_total + 1))
        reason="$(head -n 1 "$marker")"
        printf 'ok %s - %s # skip %s\n' "$idx" "$name" "$reason"
    elif [ "$rc" -eq 0 ]; then
        passed_total=$((passed_total + 1))
        printf 'ok %s - %s\n' "$idx" "$name"
    else
        failed_total=$((failed_total + 1))
        printf 'not ok %s - %s\n' "$idx" "$name"
        printf '  --- output tail (exit %s) ---\n' "$rc"
        tail -n 25 "$outfile" | sed 's/^/  /'
        printf '  ---\n'
    fi
    rm -f "$marker" "$outfile"
}

printf 'TAP version 13 (bats-shim)\n'
for f in "${files[@]}"; do
    if [ ! -f "$f" ]; then
        printf 'bats-shim: no such file: %s\n' "$f" >&2
        exit 2
    fi
    printf '# --- suite: %s ---\n' "$f"
    pp="$WORK_DIR/pp.$(basename "$f").sh"
    cnt="$(preprocess "$f" "$pp" "${#bats_names[@]}")"
    start=$(( ${#bats_names[@]} + 1 ))
    p0=$passed_total; f0=$failed_total; s0=$skipped_total
    excluded_here=0
    # shellcheck disable=SC1090
    . "$pp"
    end=${#bats_names[@]}
    idx=$start
    while [ "$idx" -le "$end" ]; do
        if is_excluded "${bats_names[idx - 1]}"; then
            excluded_here=$((excluded_here + 1))
            excluded_total=$((excluded_total + 1))
            printf '# EXCLUDED (upstream skip): %s\n' "${bats_names[idx - 1]}"
        else
            exec_test "$idx"
        fi
        idx=$((idx + 1))
    done
    printf '# BATS_SUITE_JSON={"file":"%s","discovered":%d,"executed":%d,"passed":%d,"failed":%d,"skipped":%d}\n' \
        "$f" \
        $(( cnt - excluded_here )) \
        $(( (passed_total - p0) + (failed_total - f0) + (skipped_total - s0) )) \
        $(( passed_total - p0 )) \
        $(( failed_total - f0 )) \
        $(( skipped_total - s0 ))
done

discovered_total=$(( ${#bats_names[@]} - excluded_total ))
printf 'BATS_SUMMARY_JSON={"discovered":%d,"executed":%d,"passed":%d,"failed":%d,"skipped":%d}\n' \
    "$discovered_total" \
    $(( passed_total + failed_total + skipped_total )) \
    "$passed_total" "$failed_total" "$skipped_total"

if [ "$failed_total" -gt 0 ]; then
    exit 1
fi
exit 0
