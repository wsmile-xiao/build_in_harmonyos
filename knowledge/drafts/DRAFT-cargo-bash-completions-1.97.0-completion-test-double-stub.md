# DRAFT-cargo-bash-completions-1.97.0-completion-test-double-stub — shell 补全脚本包的 test_package 双桩夹具

> 草稿，等待主编审核分配正式编号。
> 首次发现：`cargo-bash-completions 1.97.0`（test_package A1–A7 构造过程）。

## 现象

补全脚本包做 test_package 时，两类失败/退化反复出现：

```console
# ① 直接 source 后查注册（CI clean 环境没有被补全的命令）
$ bash -c 'source .../completions/cargo; complete -p cargo'
bash: complete: cargo: no completion specified        # 误读为"脚本损坏"

# ② 驱动补全函数（clean 环境没装 bash-completion）
$ bash -c 'source .../completions/cargo; COMP_WORDS=(cargo ""); COMP_CWORD=1; _cargo'
bash: _get_comp_words_by_ref: command not found

# ③ 负向测试（验证守卫生效）写错位置
$ PATH="$TMPROOT/empty" bash -c 'source "$1"; declare -F _cargo' _ "$FILE"
bash: command not found                                # 连解释器都找不到
```

结果要么"测试跑不起来"，要么作者退而求其次写成 `grep -q 'complete -F'` 的字符串断言——
被 PF3 测试闸/CI L1e 判为空壳。

## 根因

现代补全脚本有两项运行期前提：

1. **存在性守卫**。上游把整段定义挂在被补全命令存在之后，例如
   `cargo.bashcomp.sh`：

   ```bash
   command -v cargo >/dev/null 2>&1 &&
   _cargo()
   {
       ...
   } &&
   complete -F _cargo cargo
   ```

   `&&` 把「函数定义」和「complete 注册」串成一条链：PATH 中没有 `cargo` 时，
   `_cargo` 不定义、补全不注册。CI clean 环境几乎不会装被补全的命令
   （cargo / docker / pip），所以这是**常态**而非异常。

2. **框架依赖**。脚本调用 bash-completion 提供的 helper：
   `_get_comp_words_by_ref`（取 cur/prev/words/cword）、`_filedir`、
   `_comp_command_offset`（≥2.12 时转发 `cargo-*` 第三方子命令）。clean 环境未必装
   bash-completion。

另外 ③ 是**夹具自身 bug**：外层 `PATH=<empty> bash -c` 会让 shell 找不到 `bash` 可执行，
失败原因与被测对象无关。

## 处置：双桩夹具

### 桩 1 — 被补全命令（满足守卫 + 喂真实数据）

补全候选往往由该命令实时产出。`cargo.bashcomp.sh` 的实现是：

```bash
__cargo_commands_cache="$(cargo --list 2>/dev/null | awk 'NR>1 {print $1}')"
```

所以桩必须复刻输出格式（首行标题被 `NR>1` 跳过）：

```bash
cat > "$STUB_DIR/cargo" <<'EOF'
#!/usr/bin/env bash
case "${1:-}" in
    --list) printf '%s\n' "Installed Commands:" "    build  x" "    check  x" "    run  x" "    test  x" ;;
    --version) echo "cargo 1.97.0 (test stub)" ;;
    *) exit 0 ;;
esac
EOF
chmod +x "$STUB_DIR/cargo"
```

### 桩 2 — bash-completion 框架函数

```bash
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
```

⚠️ 桩内**不得**声明 `local cur prev …`：补全函数自身已 `local cur prev words cword`，
桩靠 bash **动态作用域**写回调用者的局部变量；桩内再 local 会把赋值困在桩里，
COMPREPLY 恒空。

### 驱动与断言

```bash
PATH="$STUB_DIR:$PATH" bash -c '
source harness.bash
source "$1"
complete -p cargo                      # -> complete -F _cargo cargo
COMP_WORDS=(cargo ""); COMP_CWORD=1
_cargo; printf "%s " "${COMPREPLY[@]}" # -> build check run test
COMP_WORDS=(cargo build "--"); COMP_CWORD=2
_cargo; printf "%s " "${COMPREPLY[@]}" # -> --release --target --manifest-path ...
' _ "$COMPLETION_FILE"
```

### 负向断言（守卫生效）——PATH 收窄写在子 shell 内部

```bash
bash -c '
PATH="$2"                       # 空目录
source "$1" >/dev/null 2>&1
declare -F _cargo >/dev/null 2>&1 && echo DEFINED || echo NOT_DEFINED
' _ "$COMPLETION_FILE" "$EMPTY_DIR"    # 期望 NOT_DEFINED
```

`source` / `declare` / `echo` 均为 bash 内建，空 PATH 下仍可用。

## 禁止

- ❌ 只 `grep -q 'complete -F'` 不真实加载驱动 → PF3 建 PR 前拦截，CI L1e 反向验证兜底。
- ❌ 外层 `PATH=… bash -c` / `env -i bash -c` 做负向测试 → `bash: command not found` 假失败。

## 相关

- 相似但不同：`E325`（OHOS 上 bash 发现与 `$TMPDIR` 可写性）——那条解决"用哪个 shell、
  临时文件放哪"，本条解决"补全脚本怎么被真实驱动起来"。
- 规则：R34（test 必须实质依赖被测包）、PF3（测试闸）、R51（上游测试三步法）。
- 同族可复用归档：`archives/c/cargo-bash-completions/1.97.0/test_package/test_cargo_completion.sh`
  （A1–A7，7/7 通过，已在 `conan create` 内实跑）。
