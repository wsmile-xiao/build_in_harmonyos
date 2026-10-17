# DRAFT-metamath-cli-read-command-sequence：多命令模式必须显式 READ 并引用数据库路径

> 状态：draft
> 适用版本：Metamath 0.198 及同类命令驱动 CLI
> 来源：metamath 0.198 HarmonyOS AArch64 shadow CI 首次失败与修复复盘
> 更新日期：2026-09-14

## 现象

在 `test_package` 中同时传入数据库路径、证明校验命令和 `EXIT` 时，直接把裸路径作为第一个参数：

```sh
"$METAMATH_BIN" "$DATABASE" "VERIFY PROOF *" "EXIT"
```

真机运行没有读取数据库，而是把参数按 Metamath 命令解析，出现 `Expected DBG,...`、`No source file has been read in` 等提示。

改为不带引号的多命令形式：

```sh
"$METAMATH_BIN" "READ $DATABASE" "VERIFY PROOF *" "EXIT"
```

当路径包含 `/` 时，路径仍可能被命令解析器截断，出现尝试打开 `/` 的错误。最终可工作的调用方式是：

```sh
output=$("$METAMATH_BIN" "READ \"$DATABASE\"" "VERIFY PROOF *" "EXIT")
```

Metamath 0.198 的实际成功输出包含：

```text
The source has 6 statements
All proofs in the database were verified
```

## 根因

Metamath CLI 的裸路径便利行为不能假定适用于“多个命令行参数”的场景。传入多个参数后，每个参数会进入命令解析流程；数据库读取应明确写成 `READ "<path>"`，并在命令字符串内部保护包含 `/` 的路径。

此外，版本不同或构建配置不同可能改变读取摘要的文案。v0.198 不应使用旧版本的：

```text
(READ...) 6 statements have been read
```

作为稳定断言。

## 可复用方案

1. 用独立的 `minimal.mm` 离线数据库作为消费者测试输入，避免依赖网络或上游未随归档提供的测试数据。
2. 多命令调用始终使用显式 `READ`，并在命令字符串中给数据库路径加双引号。
3. 断言稳定的版本号、语句数量摘要和证明验证成功文本；不要断言历史版本的完整欢迎语或读取格式化细节。
4. 在 Windows 主机交叉编译时只做 ELF、包内容和命令行参数检查；把实际 CLI 运行放到 OHOS shadow CI 或真机。

推荐的 `test_package/test_metamath.sh` 核心逻辑：

```sh
output=$("$METAMATH_BIN" "READ \"$DATABASE\"" "VERIFY PROOF *" "EXIT")

printf '%s\n' "$output" | grep -F "Metamath - Version 0.198" >/dev/null
printf '%s\n' "$output" | grep -F "The source has 6 statements" >/dev/null
printf '%s\n' "$output" | grep -F "All proofs in the database were verified" >/dev/null
```

## 验证证据

- 包：`metamath/0.198`
- 设备：HarmonyOS AArch64，`10.62.178.77:2222`
- shadow CI：L0、L1、L2、L4、L5 全部通过
- `test_package`：`PASS: metamath version, source parsing, and proof verification`
- 修复前的失败与修复后的成功均在本轮真机日志中复现，说明该规则不是只针对主机环境的推断。

## 禁止做法

- 不要在多命令调用中把裸数据库路径当作隐式 `READ`。
- 不要拼接未引用的绝对路径到 `READ` 命令中。
- 不要把旧版本读取摘要硬编码为 v0.198 的唯一成功条件。
- 不要因为 Windows 无法运行 AArch64 OHOS ELF 就删除运行时测试；应使用 `can_run()` 跳过主机执行并补 shadow CI 证据。

## 关联知识

- `DRAFT-pico-sdk-cli-commands-json-r38`：CLI 工具的软件级 `commands.json` 门禁。
- `DRAFT-ZLIB-SHADOW-CI-HNP-TOOL-PATH`：shadow runner 的工具 PATH 处理。
