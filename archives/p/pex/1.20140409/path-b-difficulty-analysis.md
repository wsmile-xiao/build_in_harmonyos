# pex 1.20140409 路径 B 申请材料汇总

## 申请范围

本文件只服务于 `pex/1.20140409` 的知识库扩展申请，配套草稿位于：

- `knowledge/drafts/DRAFT-pex-1.20140409-ohos-shell-entrypoint.kv` +
  `knowledge/drafts/DRAFT-pex-1.20140409-ohos-shell-entrypoint.md`
- `knowledge/drafts/DRAFT-pex-1.20140409-tap-evidence-boundary.kv` +
  `knowledge/drafts/DRAFT-pex-1.20140409-tap-evidence-boundary.md`
- `knowledge/drafts/DRAFT-pex-1.20140409-permission-semantics.kv` +
  `knowledge/drafts/DRAFT-pex-1.20140409-permission-semantics.md`
- `knowledge/drafts/DRAFT-pex-1.20140409-consumer-package-contract.kv` +
  `knowledge/drafts/DRAFT-pex-1.20140409-consumer-package-contract.md`

这些文件是路径 B 候选材料，不是已经通过审核的正式知识条目。

## 可审查的实际贡献

### 1. 纯 shell application 的双入口适配

`pex` 没有编译产物，适配难点集中在目标解释器路径和运行时命令边界。
配方在 OHOS build 阶段通过 `/system/bin/sh` 启动官方 TAP 测试，在
package 阶段修正安装副本的 shebang，并用 15 项消费测试验证安装后 CLI。

### 2. 上游测试统计的真实口径

上游不存在 C/C++ unit test 或单独 integration suite，官方测试是
`t/*.t` 的 17 个 shell TAP 文件、98 个计划断言。因此模板里的
“单元测试 0、集成测试 0”只是分类不适用，不能写成上游测试总数为 0。

OHOS shadow CI 中 `audit.t` 因缺少 Perl YAML skipped，16 个文件和 88 个
断言实际运行；当前分支 #43900 中 87 个断言通过，1 个权限前提断言按
OHOS 的实际模式位结果条件 skipped。test_package 的 15 项消费断言单独
统计并已在 #43900 通过。

### 3. 真实平台边界与最小修复

`t/pg_config.t` 的第 7 项验证不可读 `postmaster.opts` 应使 `-d` 失败；
该项在 OHOS CI 因权限语义差异失败。配方现仅在 OHOS 的源码构建副本中
增加文件模式位检查：模式位确实移除时仍要求 `pex` 返回失败；如果
`chmod a-r` 在目标文件系统上没有改变读位，则只对这一条断言输出带原因的
TAP skip。Linux 不改变，仓库内上游 `t/*.t` 文件不修改，也没有用
`|| true` 或改写期望值制造假通过。当前分支已由 #43900 确认完整构建链
和 test_package 通过；上游统计仍保留 17 个计划文件、98 个计划断言，
其中 10 个 audit.t 断言因缺 Perl YAML、1 个权限前提断言因 OHOS chmod
语义而条件跳过。

## 与普通基础适配的边界

### 4. 安装后消费者契约的独立证据

`test_package/test_pex.sh` 不是把上游 TAP 重复执行，而是从 Conan
安装结果验证消费者真正拿到的契约：4 项安装文件、可执行位、OHOS
shebang、`--help`、XDG 路径、本地 Git 仓库 `init/search/cat`，以及
非法命令的退出码和诊断，共 15 项断言。`test_package/MANIFEST.yml`
现在同时声明上游 17 文件/98 断言和这 15 项消费者证据；#43900 已报告
消费者测试通过。这个分层能直接复核“上游测试分类为 0”与“安装后包是否
可用”是两个不同问题。

以上材料均绑定到 `pex` 的上游文件、Conan 阶段、OHOS 测试命令、安装
后消费者契约和 CI 结果，不把通用“换编译器”或“缺少依赖”单独包装成
创新。最终是否符合 B 类难度及是否计分，以仓库维护者和评审结论为准。
