# DRAFT-perl-regexp-common-2017060201-shadow-exitcode-pipe-distortion

## 使用说明

通过 ssh / 后台 job 采集真机 shadow CI 结果时，若把 runner 命令**接进管道**
（`sh run-conan-heavy.sh 2>&1 | tail -60; echo EXIT=$?`），`$?` 拿到的是**管道最后
一个命令（tail/ssh 客户端）的退出码**，不是 runner 的退出码。本文给出通用的
退出码采集规范，适用于所有 shadow CI 结果读取、CI 包装脚本和远端命令封装。

## 适用范围

- 场景：ssh 远端执行 runner 并回传退出码；PowerShell/bash 后台 job 包装；
  任何 `cmd | filter` 后判断成败的脚本
- 不适用：单命令直接执行（无管道）的退出码采集

## 输入 / 输出定义

- 输入（症状）：设备端 `logs/exit-code.txt` 明明是 1，本机包装脚本却打出
  `RUNNER_EXIT=0`（本轮实例：`echo RUNNER_EXIT=$?` 中 `$?` 是 `tail` 的退出码）
- 输入（代码特征）：`ssh ... "runner ...; echo EXIT=$?"` 与
  `ssh ... "runner | tail"` 两种写法混用；或本机再套一层管道
- 输出（规范）：退出码必须在**与 runner 同一个 shell、且无中间管道**的上下文中
  采集；输出过滤与退出码采集分离

## 示例

错误（退出码被 tail 篡改，本轮 r2 实际 exit 1 却读到 0）：

```sh
ssh host "sh run-conan-heavy.sh 2>&1 | tail -60; echo RUNNER_EXIT=\$?"
```

正确写法一（重定向到文件，退出码直接来自 runner）：

```sh
ssh host "sh run-conan-heavy.sh > /dev/null 2>&1; echo EXIT=\$?"
# 结果从 logs/exit-code.txt / logs/stdout.log 读取，与退出码分离
```

正确写法二（bash 管道但取首个命令退出码）：

```bash
set -o pipefail        # bash/zsh
sh run-conan-heavy.sh 2>&1 | tail -60
echo "EXIT=${PIPESTATUS[0]}"
```

审查清单：grep 包装脚本中所有 `echo .*EXIT=` / `exit \$?`，确认与被测命令之间
无管道（或有 pipefail/PIPESTATUS 保护）。

## 本轮证据

perl-regexp-common r2 真机：`logs/exit-code.txt=1` 而后台 job 输出
`RUNNER_EXIT=0`，导致误判成功；改用"重定向 + 独立读 exit-code.txt"后 r3 判定正确。
