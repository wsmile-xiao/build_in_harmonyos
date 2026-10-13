# DRAFT-rset-3.3-toybox-awk-script-args

## 问题

rset 的 renv.awk 使用 `#!/usr/bin/awk -f` shebang。OHOS 系统 awk 是 toybox 0.8.12
实现，**违反 POSIX**：把"第一个操作数之后"的以 `-` 开头的参数继续当 awk 自身选项
解析，而不是传给 awk 脚本。rset 核心路径（input.c:496）调用 `renv - -q`，toybox awk
直接报错：

```
$ renv - -q
awk: Unknown option 'q' (see "awk --help")
```

后果：rset 的 quiet 模式（仅 stderr 报错、不回显变量）完全不可用，上游
test_renv.rb 的 "Print only environment errors" 用例失败。这不是脚本内容问题——
同样的 awk 程序体在 gawk 下一切正常。

## 根因

- toybox awk 的参数解析不符合 POSIX awk 语义（`awk -f prog.awk -- -q` 中 `--`
  之后的 `-q` 应作为脚本参数 ARGV[1]，toybox 仍当作自身选项）。
- `env -S` 在 OHOS 上不可用，shebang 无法加复杂参数。
- 属平台解释器能力差异，非上游 bug。

## 修复（sh+awk 单文件 polyglot，通过 /dev/fd/3 喂程序）

把 renv.awk 改成 shebang `#!/bin/sh` 的 shell 脚本，用 heredoc 携带 awk 程序体：

```sh
#!/bin/sh
exec awk -f /dev/fd/3 -- "$@" 3<<'RSET_AWK_PROGRAM'
<原 awk 程序体逐字保留>
RSET_AWK_PROGRAM
```

要点：
1. `--` 终止选项解析后，`-q` 等脚本参数原样进入 ARGV（toybox/gawk 双双验证通过）。
2. **单文件性质保留**：rset 会把 renv 复制到远端 staging 目录执行，拆成两个文件
   会破坏 `rset` 的远端分发模型；heredoc polyglot 仍是单文件。
3. heredoc 定界符用带引号形式（`<<'EOF'`），禁止 shell 对程序体做 `$$` 等展开
   （renv 程序体本身会输出 `\$` 转义）。
4. GNU/Linux（gawk/mawk）行为不变——同一文件跨平台可用。

## 验证

- rset 3.3 上游 test_renv.rb：补丁前 6/7（-q 用例失败），补丁后 **7/7**。
- conan test_package 冒烟：`renv -` 过滤引用、`renv - -q` 静默 stdout 且 stderr
  保留 `renv: unknown pattern` 错误，全部通过。
- 同一文件在 gawk 环境（本机 /usr/bin/gawk）行为不变。

## 适用范围

任何 `#!/usr/bin/awk -f` 且需要向脚本传 `-` 开头参数（`-q`、`-v` 之外的脚本级
flag）的 awk 工具。核心模式：**shebang 改 /bin/sh + `exec awk -f /dev/fd/3 -- "$@" 3<<'EOF'`**。
注意：依赖 /dev/fd（Linux 均有）；若目标平台无 /dev/fd 需退化为 mktemp 中转。
