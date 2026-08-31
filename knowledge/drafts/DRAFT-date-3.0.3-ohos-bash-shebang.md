# DRAFT-date-3.0.3-ohos-bash-shebang — 上游测试辅助脚本硬编码 `#!/bin/bash` 导致 CTest BAD_COMMAND

> 正式编号未分配；合并/提升时由知识库维护流程分配下一个可用 E###。
> 来源：date 3.0.3 HarmonyOS PC 适配（R01 bootstrap 首错 + R02 路径 B 知识草稿）。

## 错误特征

上游测试基础设施把解释器绝对路径 `/bin/bash` 硬编码进 shell 辅助脚本的 shebang。在 OHOS 上运行 CTest 时，整组 compile-fail 测试显示：

```text
77/108 Test  #77: date_test_fail_year_month_day_m_year_month_day_test .....***Not Run   0.00 sec
     77 - date_test_fail_year_month_day_m_year_month_day_test (BAD_COMMAND)
Errors while running CTest
```

CTest 无法 exec wrapper（shebang 指向不存在的 `/bin/bash`），表现为 `BAD_COMMAND` + `Not Run`，而不是直观的 `bad interpreter` 日志行。

## 触发条件

- 上游测试入口通过 CTest / wrapper 脚本执行测试（如 date 的 `test_fail.sh`、`compile_fail.sh`）。
- 该脚本 shebang 硬编码 `/bin/bash`（或 `/bin/sh`）。
- 目标 OHOS 环境没有 `/bin/bash`，bash 实际位于 `/data/service/hnp/bin/bash`（PATH 可解析）。

## 根因分析

OHOS（HarmonyOS PC）没有传统 `/bin` 目录：`ls /bin/bash` → `No such file or directory`，bash 由 `/data/service/hnp/bin/bash` 提供。内核执行脚本时按 shebang 查找 `/bin/bash` 失败，`execve` 返回 ENOENT，CTest 将其归类为 `BAD_COMMAND`。这与 configure/install 脚本缺 bash 的 `bad interpreter` 现象学略有不同——故障点在 **CTest 对 wrapper 的 exec**，且不产生可 grep 的错误正文。

本机实测：`/usr/bin/env` 存在（toybox 提供），因此改为 `#!/usr/bin/env bash` 后解释器可经 PATH 解析到 `/data/service/hnp/bin/bash`。

## 推荐方案

最小补丁只改两个测试辅助脚本的 shebang（不改编译产物、不改测试语义）：

```diff
--- a/compile_fail.sh
-#!/bin/bash
+#!/usr/bin/env bash
@@
-	echo -ne "#!/bin/bash\nexit 1;" > ${TEST_BIN_NAME}
+	echo -ne "#!/usr/bin/env bash\nexit 1;" > ${TEST_BIN_NAME}
@@
-	echo -ne "#!/bin/bash\nexit 0;" > ${TEST_BIN_NAME}
+	echo -ne "#!/usr/bin/env bash\nexit 0;" > ${TEST_BIN_NAME}
--- a/test_fail.sh
-#!/bin/bash
+#!/usr/bin/env bash
```

要点：`compile_fail.sh` 不仅自身 shebang 要改，它**生成**的 stub 脚本的内嵌 shebang 也要同步改；`test_fail.sh` 是 CTest 直接 exec 的 wrapper，同样必须改。只改其一（如仅 compile_fail.sh，3.0.4 参考补丁的教训）无法通过全部测试。

## 验证口径

- `conan create` 二轮 `testit`：`100% tests passed, 0 tests failed out of 108`（108/108，37 个 BAD_COMMAND 清零）。
- `test_package` 消费测试：`date checks passed: 220`（220 项消费者断言，含 date-tz 链接符号 `set_install()`）。
- `patch -p1` 应用 exit 0，`grep -n "env bash"` 命中 3 处（compile_fail.sh:1/10/12 + test_fail.sh:1）。

## 适用边界

- **适用**：上游测试/构建辅助脚本依赖 bash，目标环境可通过 PATH 找到 bash（`/usr/bin/env` 存在）时，改 shebang 为 `#!/usr/bin/env bash`。
- **不适用**：bash 语法本身与目标环境不兼容；目标环境完全没有 bash；或脚本实际由 sh/perl/python 等其他解释器执行而仅 shebang 写错（此时应改写为对应解释器的可移植 shebang）。
- **禁止**：把 `/data/service/hnp/bin/bash` 本机路径写成通用结论；应始终以 PATH 解析 + `/usr/bin/env` 存在性检测为准。

## 与既有知识的关系（查重结论）

| 条目 | 覆盖内容 | 与本品差异 |
|------|---------|-----------|
| E165 | configure 阶段 `#!/bin/bash` 缺失根因（bash 位于 `/data/service/hnp/bin/bash`）、shebang-fix | 场景是 configure 配置脚本；不覆盖 CTest 测试辅助脚本 BAD_COMMAND 现象学，也无 env-bash 修复实证 |
| E037 | `/usr/bin/env` 缺失与 shebang 可移植性双向修复 | 其"鸿蒙无 `/usr/bin/env`"断言与本机实测不符（本机 `/usr/bin/env -> toybox` 存在），需以实测为准；未覆盖 CTest 场景 |
| E201 | test_run.sh 需 `/bin/bash`，方案为绕过 wrapper 手动跑测试 | 采用"绕开"而非修复，测试自动化无法保留；本品给出保住完整 testit 的路径 |
| E049/E143 | 生成脚本硬编码解释器路径、python shebang | 构建产物侧；本品为测试 wrapper 侧，且配 `compile_fail.sh` 生成 stub 的特殊性 |

结论：既有条目未完整覆盖"C AMake/CTest 测试辅助脚本硬编码 `#!/bin/bash` → BAD_COMMAND → env-bash shebang 修复保住 108/108 完整自动化测试"这一模式，且 E037 的平台断言需实测纠正，故新增本同 stem 草稿对（.kv + .md），不覆盖任何既有条目。

## 本轮只读边界

本草稿仅写入 `knowledge/drafts/DRAFT-date-3.0.3-ohos-bash-shebang.md` 与 `.kv`（同 stem 配对）；未写入 `knowledge/doc/`、`knowledge/graph/`、`index.tsv` 或任何正式条目。远端动作（commit/push/PR/Issue/远端 CI）本轮未授权，未执行。