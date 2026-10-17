#!/usr/bin/env bash
# test_cargo_completion.sh — cargo-bash-completions 1.97.0 消费者视角功能测试
#
# 关于 `set`（code-style §6/§7 要求 set -euo pipefail，此处按下述理由局部取舍）：
#   - `set -u` 已启用；
#   - **不启用 `-e`**：本脚本是断言集合，A1–A7 中多条断言的被测命令**预期可能失败**
#     （如 A3 的 bash -n、A4 在空 PATH 下 source），需要继续执行完所有断言并汇总
#     fails 计数，最后用退出码统一反映结果；`-e` 会在第一条失败处直接中断，
#     丢失后续断言信息；
#   - **不启用 `-o pipefail`**：A6/A7/A8 的候选判定用 `printf | grep`，grep 无匹配返回 1
#     属正常分支（由 if 接管）。单独的 pipefail 不会中断脚本，但会让管道退出码由中间命令
#     决定；本脚本的判定语义就是「最后一个 grep 的结果」，保持默认更贴合意图，
#     也避免日后有人加上 `-e` 时这些正常分支被误判为失败。
#
# 用法: bash test_cargo_completion.sh <安装后的补全脚本绝对路径>
#
# 断言（A1–A8）全部真实加载并驱动被测脚本，不做字符串 print 空壳测试（R34）：
#   A1 产物存在且非空
#   A2 体积合理（上游 11443 字节；阈值 8192 防止截断/空文件入包）
#   A3 bash -n 语法检查
#   A4 负向：PATH 中没有 cargo 时上游守卫生效 → 不定义 _cargo、不注册补全
#   A5 有 cargo 时 source 后 `complete -p cargo` 输出 `-F _cargo`
#   A6 `cargo <TAB>` 经 `cargo --list` 真实产出子命令候选（build/check/run/test）
#   A7 `cargo build --<TAB>` 产出子命令选项候选（--release/--target/--manifest-path）
#   A8 版本实证：`cargo build -<TAB>` 候选含 1.97 新增的 `-m` 短选项
#      （cargo 1.96 的脚本为 opt_mani='--manifest-path'，无 -m；该断言确保交付的
#       确实是 1.97 对应的 tag 0.98.0 脚本，而非上一周期的 0.97.0）
#
# bash-completion 框架函数（_get_comp_words_by_ref/_filedir/_comp_command_offset）用轻量
# 桩提供，cargo 用固定输出的桩提供——保证 CI clean 环境（无 bash-completion、无 Rust
# 工具链）下结果可复现。
set -u

COMPLETION_FILE="${1:?usage: bash test_cargo_completion.sh <completion-file>}"
fails=0

TMPROOT="${TMPDIR:-/tmp}/cargo-bashcomp-test-$$"
mkdir -p "$TMPROOT/empty" "$TMPROOT/bin"
trap 'rm -rf "$TMPROOT"' EXIT

# ── 测试夹具 1：bash-completion 框架桩 ────────────────────────────────
# _cargo() 内已 `local cur prev words cword`；桩内不得再 local，依 bash 动态作用域写回。
HARNESS="$TMPROOT/harness.bash"
cat > "$HARNESS" <<'HARNESS_EOF'
_get_comp_words_by_ref() {
    local arg
    for arg in "$@"; do
        case "$arg" in
            cur)   cur="${COMP_WORDS[COMP_CWORD]}" ;;
            prev)  prev="${COMP_WORDS[COMP_CWORD-1]:-}" ;;
            words) words=("${COMP_WORDS[@]}") ;;
            cword) cword="$COMP_CWORD" ;;
        esac
    done
}
_filedir() { :; }
_comp_command_offset() { :; }
HARNESS_EOF

# ── 测试夹具 2：cargo 桩（被测脚本顶部 `command -v cargo` 守卫 + `cargo --list` 取子命令）
cat > "$TMPROOT/bin/cargo" <<'SHIM_EOF'
#!/usr/bin/env bash
case "${1:-}" in
    --list)
        cat <<'LIST'
Installed Commands:
    build                Compile the current package
    check                Analyze the current package and report errors
    run                  Run a binary or example of the local package
    test                 Run the tests
LIST
        ;;
    --version) echo "cargo 1.97.0 (test stub)" ;;
    *) exit 0 ;;
esac
SHIM_EOF
chmod +x "$TMPROOT/bin/cargo"

# ── A1 产物存在且非空 ────────────────────────────────────────────────
if [ -s "$COMPLETION_FILE" ]; then
    echo "PASS: A1 completion file exists and is non-empty ($COMPLETION_FILE)"
else
    echo "FAIL: A1 completion file missing or empty: $COMPLETION_FILE"
    fails=$((fails + 1))
fi

# ── A2 体积合理 ──────────────────────────────────────────────────────
size=$(wc -c < "$COMPLETION_FILE" 2>/dev/null || echo 0)
if [ "$size" -ge 8192 ]; then
    echo "PASS: A2 size sane ($size bytes >= 8192)"
else
    echo "FAIL: A2 unexpected size ($size bytes < 8192)"
    fails=$((fails + 1))
fi

# ── A3 语法检查 ──────────────────────────────────────────────────────
if bash -n "$COMPLETION_FILE" 2>"$TMPROOT/a3.err"; then
    echo "PASS: A3 bash -n syntax check"
else
    echo "FAIL: A3 bash -n reported syntax errors:"
    sed 's/^/      /' "$TMPROOT/a3.err"
    fails=$((fails + 1))
fi

# ── A4 负向：无 cargo 时守卫生效 ─────────────────────────────────────
# 注意：PATH 必须在子 shell 内部收窄（在外部清空会导致连 bash 本身都找不到）；
# source/declare/echo 均为 bash 内建，空 PATH 下仍可用。
guard=$(bash -c '
PATH="$2"
source "$1" >/dev/null 2>&1
if declare -F _cargo >/dev/null 2>&1; then echo DEFINED; else echo NOT_DEFINED; fi
' _ "$COMPLETION_FILE" "$TMPROOT/empty" 2>&1)
if [ "$guard" = "NOT_DEFINED" ]; then
    echo "PASS: A4 'command -v cargo' guard suppresses registration when cargo is absent"
else
    echo "FAIL: A4 expected NOT_DEFINED without cargo in PATH, got: $guard"
    fails=$((fails + 1))
fi

# ── A5 complete 注册 ─────────────────────────────────────────────────
reg=$(PATH="$TMPROOT/bin:$PATH" bash -c '
source "$1"
source "$2"
complete -p cargo
' _ "$HARNESS" "$COMPLETION_FILE" 2>&1)
if printf '%s' "$reg" | grep -q -- "-F _cargo"; then
    echo "PASS: A5 completion registered: $reg"
else
    echo "FAIL: A5 'complete -p cargo' did not report -F _cargo, got: $reg"
    fails=$((fails + 1))
fi

# ── A6 子命令候选（驱动 _cargo，经 cargo --list + awk 链路） ─────────
subs=$(PATH="$TMPROOT/bin:$PATH" bash -c '
source "$1"
source "$2"
COMP_WORDS=(cargo ""); COMP_CWORD=1
_cargo
printf "%s " "${COMPREPLY[@]}"
' _ "$HARNESS" "$COMPLETION_FILE" 2>&1)
if printf '%s' "$subs" | grep -qw build \
   && printf '%s' "$subs" | grep -qw check \
   && printf '%s' "$subs" | grep -qw run \
   && printf '%s' "$subs" | grep -qw test; then
    echo "PASS: A6 _cargo() produced sub-command candidates: $subs"
else
    echo "FAIL: A6 sub-command candidates missing build/check/run/test, got: $subs"
    fails=$((fails + 1))
fi

# ── A7 子命令选项候选（cargo build --<TAB>） ─────────────────────────
opts=$(PATH="$TMPROOT/bin:$PATH" bash -c '
source "$1"
source "$2"
COMP_WORDS=(cargo build "--"); COMP_CWORD=2
_cargo
printf "%s " "${COMPREPLY[@]}"
' _ "$HARNESS" "$COMPLETION_FILE" 2>&1)
if printf '%s' "$opts" | grep -qw -- --release \
   && printf '%s' "$opts" | grep -qw -- --target \
   && printf '%s' "$opts" | grep -qw -- --manifest-path; then
    echo "PASS: A7 'cargo build --' produced option candidates (--release/--target/--manifest-path)"
else
    echo "FAIL: A7 option candidates incomplete, got: $opts"
    fails=$((fails + 1))
fi

# ── A8 版本实证：1.97 新增的 -m 短选项（cargo build -<TAB>） ─────────
short=$(PATH="$TMPROOT/bin:$PATH" bash -c '
source "$1"
source "$2"
COMP_WORDS=(cargo build "-"); COMP_CWORD=2
_cargo
printf "%s " "${COMPREPLY[@]}"
' _ "$HARNESS" "$COMPLETION_FILE" 2>&1)
if printf '%s' "$short" | grep -qw -- -m; then
    echo "PASS: A8 '-m' short option present (cargo 1.97 feature; proves tag 0.98.0 script)"
else
    echo "FAIL: A8 '-m' (1.97 新增) 未出现在候选中 —— 交付脚本可能来自错误的上游 tag"
    echo "      got: $short"
    fails=$((fails + 1))
fi

echo "test_cargo_completion.sh: $([ "$fails" -eq 0 ] && echo 'ALL PASSED (8/8)' || echo "$fails FAILED")"
[ "$fails" -eq 0 ]
