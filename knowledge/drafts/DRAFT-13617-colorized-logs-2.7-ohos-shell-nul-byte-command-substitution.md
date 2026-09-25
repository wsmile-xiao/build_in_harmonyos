# DRAFT-13617 — OHOS shell 命令替换丢弃 NUL 字节（二进制流测试数据必须走临时文件）

> 状态：草稿（来自 colorized-logs 2.7 适配，task_id=colorized-logs-2.7-r01-pc2-8-20260921T161028Z）

## 问题

OHOS 上的 shell（mksh）与 bash 在执行 `$(...)` 命令替换时会把输出字节流中的 **NUL 字节（\x00）静默丢弃**——NUL 无法存在于结果字符串中。任何把二进制测试数据（ttyrec 帧头、termios 序列、转义载荷）经命令替换回传的测试/消费者脚本都会得到静默损坏的数据。

实测：`printf 'aaaa10\a\0\t\0\0\0hello tty\n' | ttyrec2ansi` 直管输出 `hello tty`（正确）；但经 `out=$(... | ttyrec2ansi)` 捕获后输出变为 `hello tt`（尾字节丢失），stderr 出现 `File was truncated`。

## 根因

- ttyrec 帧头 12 字节含 `\x00`（sec/usec/len 小端字段），命令替换剥离 NUL 后 len 字段被破坏，重放器读到错误的 payload 长度。
- 上游 testsuite（Perl）本身就用**临时文件**传输二进制数据（`stdin.$id`/`stdout.$id` + `cmp`），从不经过命令替换。
- 另外 `pipetty sh -c '...'` 在 OHOS mksh 下返回非零且无输出；上游调用形式 `pipetty </dev/null sh <script文件>` 正常。

## 方案

1. 二进制测试数据一律走临时文件：`printf ... > in; tool < in > out; cmp/cat 比较`。
2. pty 类工具用脚本文件形式调用（`pipetty </dev/null sh script.sh`）。
3. ttyrec 测试数据帧长与 len 字段精确匹配（9 字节 payload 用 `\t\0\0\0` = 9 LE）。

## 验证

- 上游 ctest 5/5 通过（ansi2txt/ansi2html/pipetty/pipetty:sigobit/ttyrec2ansi）
- test_package 消费者验证全通过（ansi2txt/ansi2html/ttyrec2ansi/pipetty/lesstty）
- test_ohos 鸿蒙专项 T1-T5 全通过（aarch64 ELF / 无宿主路径 / ANSI 解码往返 / ttyrec 重放 / pipetty pty）
- conan-verify G2 conan create（ohos-aarch64）通过

## 适用边界

- 适用于 OHOS（mksh/bash）及一切按 POSIX 字符串模型处理命令替换输出的受限环境。
- 仅影响含 NUL 的二进制流；纯文本输出不受影响。
- 上游本身用临时文件+cmp 的测试（testsuite 类）天然免疫，无需改动。

## 查重差异

- E275（OHOS shell grep -v + set -e）是 grep 空结果退出码问题，非字节丢失。
- E363（legacy Bash harness 假绿）是 /tmp 只读 + shebang + xargs -I 的 false-green 问题，非 NUL 字节。
- DRAFT-13491（toybox file --mime 空输出）是命令替换返回**空字符串**的语义差异，与本条 NUL 字节截断属不同字节级现象。
- 本条目聚焦"二进制字节完整性"传输层面，独立于上述退出码/假绿/空输出条目。
