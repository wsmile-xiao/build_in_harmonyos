# posh

**posh — Policy-compliant Ordinary SHell**（pdksh 剥离版 POSIX shell，Debian 维护）

posh 是 Public Domain ksh（pdksh）的衍生 shell，剥去了非 POSIX 扩展（历史、别名、数组、协进程、here-strings、ulimit 等），目标是**严格 POSIX 合规**——适合作为测试脚本可移植性的参照 shell。Debian 仓库维护，单一可执行文件 `posh`，零外部依赖。

## 用法

```bash
# 交互使用
posh

# 执行命令串
posh -c 'echo $((3*7+1))'

# 执行脚本
posh script.sh

# 查询版本（注意：posh 无 -version 选项，版本经 $POSH_VERSION 变量查询；
# 0.14.6 发布时上游忘 bump acinclude.m4，故报告 0.14.5，与上游一致）
posh -c 'echo $POSH_VERSION'
```

## 已知限制（OHOS）

- `/tmp` 只读（E002）：heredoc 临时文件路径由 `TMPDIR` 决定，使用 heredoc 的脚本需设置 `TMPDIR` 指向可写目录
- `umask` 内建报错消息为 musl getopt 格式（`unrecognized option: r`，glibc 为 `invalid option -- 'r'`），仅消息格式差异
- `getopts` 在解析错误（`?`）后不重置 `OPTARG`（上游实现与 mksh/pdksh 语义的分歧，非平台问题）
