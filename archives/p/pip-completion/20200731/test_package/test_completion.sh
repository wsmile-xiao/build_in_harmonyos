#!/usr/bin/env bash
# test_package/test_completion.sh — pip-completion 20200731 消费者视角冒烟测试
#
# 用法: bash test_completion.sh <path-to-installed-pip-completion-script>
#
# 断言（与 test_package/MANIFEST.yml 的 assertion_count 对应）：
#   A1 安装产物存在        A2 大小合理(>=100B)     A3 bash -n 语法校验
#   A4 source 后 complete -p pip 注册正确（Homebrew test do 等价断言）
#   A5 pip2/pip3 亦注册    A6 _pip() 真实产出补全候选（pip 桩驱动，CI 无需真 pip）
#   A7 POSIX sh 下不可加载（证明 bash 为强制运行期依赖）
# 不用 `set -e`：本脚本要统计全部断言而不是首错即停，失败通过 $fails 计数
# 传导退出码（见末尾）；`set -u` 保留以捕获未定义变量。
set -u

COMPLETION_FILE="${1:-}"
if [ -z "$COMPLETION_FILE" ]; then
    echo "Usage: $0 <completion_file>" >&2
    exit 1
fi

fails=0
# OHOS 上 /tmp 只读（E002），日志落在当前可写目录
CHECK_LOG=".ohc-check-out.$$"
check() { # <名称> <命令...>
    local name="$1"; shift
    if "$@" >"$CHECK_LOG" 2>&1; then
        echo "PASS: $name"
    else
        local rc=$?
        echo "FAIL: $name (rc=$rc)"
        sed 's/^/      /' "$CHECK_LOG"
        fails=$((fails + 1))
    fi
    rm -f "$CHECK_LOG"
}

# --- A1 存在性
check "A1 installed completion file exists" test -f "$COMPLETION_FILE"

# --- A2 非空且大小合理
size=$(wc -c < "$COMPLETION_FILE" 2>/dev/null || echo 0)
check "A2 completion script size sane (${size} bytes)" test "$size" -ge 100

# --- A3 语法校验（等价 Homebrew 之外的静态检查，先例 docker-completion 同款）
check "A3 bash -n syntax check" bash -n "$COMPLETION_FILE"

# --- A4/A5 注册断言（Homebrew Formula test do: assert_match "-F _pip"）
out=$(bash -c "source '$COMPLETION_FILE' && complete -p pip" 2>&1)
check "A4 complete -p pip == 'complete -o default -F _pip pip'" \
    test "$out" = "complete -o default -F _pip pip"
n=$(bash -c "source '$COMPLETION_FILE' && complete -p pip2 && complete -p pip3" 2>/dev/null | grep -c -- '-F _pip')
check "A5 pip2/pip3 registered (got $n of 2)" test "$n" -eq 2

# --- A6 功能断言：用 pip 桩驱动被测的 _pip() 解析逻辑（awk + grep + tr）
SHIM_DIR="$PWD/.pip-completion-shim"
mkdir -p "$SHIM_DIR"
cat > "$SHIM_DIR/pip" <<'SHIM'
#!/usr/bin/env bash
cat <<'HELP'
Usage: pip <command> [options]

Options: ...

Commands:
  install
  download
  uninstall
  freeze
  list

General Options:
  -h, --help
HELP
SHIM
chmod +x "$SHIM_DIR/pip"
cands=$(PATH="$SHIM_DIR:$PATH" bash -c '
source "$1"
COMP_WORDS=(pip ""); COMP_CWORD=1
command -v pip >/dev/null || exit 3
_pip
printf "%s\n" "${COMPREPLY[@]}" | tr "\n" " "
' _ "$COMPLETION_FILE" 2>&1)
if printf '%s' "$cands" | grep -qw install \
   && printf '%s' "$cands" | grep -qw download \
   && printf '%s' "$cands" | grep -qw uninstall; then
    echo "PASS: A6 _pip() generated sub-command candidates via awk+grep+tr"
    echo "      candidates: $cands"
else
    echo "FAIL: A6 _pip() candidates missing install/download/uninstall"
    echo "      got: $cands"
    fails=$((fails + 1))
fi
rm -rf "$SHIM_DIR"

# --- A7 反例：POSIX sh 无法加载（complete 为 bash 内建）
# 注意：部分 runner 的 /bin/sh 本身就是 bash（POSIX 模式下仍有 complete/[[）
# ——此时负向加载测试会假失败拖红 CI。先探测 sh 实现，非 bash 才做动态负断言，
# 否则降级为「脚本依赖 bash 专有语法」的静态断言（同样成立、可复现）。
if [ "$(basename "$(readlink -f "$(command -v sh)")")" = "bash" ]; then
    if grep -q '\[\[' "$COMPLETION_FILE" && grep -q '^complete ' "$COMPLETION_FILE"; then
        echo "PASS: A7 bash-only syntax ([[ ]] + complete) present (host /bin/sh is bash, dynamic negative check skipped)"
    else
        echo "FAIL: A7 no bash-only construct found, negative test would be meaningless"
        fails=$((fails + 1))
    fi
elif sh -c "source '$COMPLETION_FILE'" >/dev/null 2>&1; then
    echo "FAIL: A7 POSIX sh unexpectedly loaded the completion (bash-only builtins?)"
    fails=$((fails + 1))
else
    echo "PASS: A7 POSIX sh cannot load it (bash is a mandatory runtime dependency)"
fi

echo "test_completion.sh: $([ "$fails" -eq 0 ] && echo 'ALL PASSED' || echo "$fails FAILED")"
[ "$fails" -eq 0 ]
