# acr 2.2.6 路径 B 候选说明

## 申请范围

- 任务：`acr/2.2.6`
- 智能平台任务分支：`feat/acr-2.2.6`
- 上游标签：`2.2.6`
- 上游源码 SHA-256：`18c8e66c297bb8216a6de54945701e6813f404e162887456f495a01bc1b427b3`
- 申请类型：路径 B（上游测试修复及 HarmonyOS PC 环境适配，最终以官方审核为准）

## 上游测试清单与原始结果

上游标签内共有 30 个活动测试项：

| 测试入口 | 计数依据 | 原始结果 |
|---|---:|---:|
| `tests/test.sh` | `examples/*.acr` 共 18 个文件 | 18/18 |
| `tests/test-triplet.sh` | 12 行未注释的 `test <tuple> <os> <cpu>` | 11/12 |
| 合计 | 18 + 12 | 29/30 |

`#test openbsd-unknown-i386 openbsd i386` 是注释，不计入测试数。原始失败为：

```text
m68k-coff
  OS FAIL   - coff vs linux
```

上游脚本即使输出 `FAIL` 仍返回 0，因此验证不能只检查退出码。

## 根因

`m68k-coff` 是两个字段的目标元组。ACR 的 `split_host` 正确解析为 CPU
`m68k`、OS `coff`，但测试把预期 OS 写成了运行测试的主机 OS `$UNAME`
（Linux 上为 `linux`）。系统 GNU `config.sub m68k-coff` 的规范化输出是
`m68k-unknown-coff`，与 ACR 的解析一致，说明错误在测试期望而不是实现。

## 最小测试修复

`0001-fix-m68k-coff-test-expectation.patch` 只修改一个期望值：

```diff
-test m68k-coff $UNAME m68k
+test m68k-coff coff m68k
```

该修复没有删除、跳过或放宽测试；CPU 断言仍为 `m68k`，OS 断言改为目标
元组和 GNU `config.sub` 都认可的 `coff`。配方额外要求 triplet 输出中不能
出现 `FAIL`，防止上游脚本的零退出码造成假通过。

## HarmonyOS PC 环境处理

PC 模拟器基础镜像没有 `getopt`、`awk`、`expr`、`tr`。本适配仅处理 ACR
核心流程中无条件执行的路径：

1. 有 `getopt` 时保持上游参数规范化；没有时使用上游已有参数循环。
2. 缺失的语义版本段以 `0` 补齐，并用 POSIX `cut` 取段。
3. 仅在 `awk` 存在时探测 mawk；无条件分词的行后缀操作改用 `sed`。
4. 生成的 `split_host` 使用 shell `case` 与 `cut`，`guess_os` 使用 `sed y`。

需要编译器、语言解释器或其他外部程序的可选 ACR 指令仍按上游逻辑检查
真实工具，不伪装为可用。

## 前后对照

| 阶段 | triplet | examples | 合计 | 隐藏错误检查 |
|---|---:|---:|---:|---|
| 未修改上游 | 11/12 | 18/18 | 29/30 | 检出 1 个 `FAIL` |
| 应用补丁后 | 12/12 | 18/18 | 30/30 | 无 `FAIL`，无算术告警 |
| PC 模拟器消费者测试 | - | 3 个场景 | 7/7 断言 | 无命令缺失或算术错误日志 |

Linux Release 和 Debug 均由 Conan 构建过程执行完整 30 项上游测试；OHOS
armv8 配方创建通过，PC 模拟器完成版本、生成/执行 configure、缺失输入故障
注入。详细结果见 `test-report.md` 和 `conan-verify-report.md`。

## 可复现命令

```text
conan create . --user=ohpcd --channel=stable --build=missing -s build_type=Release
conan create . --user=ohpcd --channel=stable --build=missing -s build_type=Debug
conan create . --user=ohpcd --channel=stable --build=missing -pr:h=new4-ohos-aarch64-windows -pr:b=default
/system/bin/sh test_emulator.sh /data/local/tmp/acr-2.2.6-package
```
