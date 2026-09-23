# superopt 2.5 适配笔记

## 编译环境
- 构建系统: custom（无构建系统族：单 superopt.c + 手写 Makefile，无 configure）
- 编译日期: 2026-09-15
- 编译器: clang 15（profile conf tools.build:compiler_executables）
- 状态: built（conan-verify G0-G4 通过，G2 一次通过）
- worktree: ~/qzy/GLM-33-superopt-2.5 分支 feat/superopt-2.5（基于 upstream/main fb121b78c2）
- 任务号: 13489（依赖活动 activity_id=6）

## 编译步骤
1. 上游 Makefile 硬编码 `CC = gcc`（环境覆盖无效），且 `make superopt` 等规则逐机型加 `-D` 宏。
   适配为配方内直接编译：`clang -O2 -D<MACRO> -o dist/superopt-<machine> superopt.c`，
   机型/宏对照上游 Makefile 全量 14 个变体（SPARC/POWER/POWERPC/M88000/AM29K/MC68000/
   MC68020/I386/I960/I960B/PYR/ALPHA/SH/HPPA），无 patches。
2. 已知平台事实（本机实测）：/tmp 只读（E002），编译输出走包内 dist/。

## 测试账本（四维）
| 维度 | 数值 | 来源 |
|---|---|---|
| 上游静态用例 N_static | 0 | 全树无 TESTS/check 目标/测试脚本（Makefile 仅 build 目标，configure 不存在） |
| 实际执行 | 0 | 上游无测试套件，如实申报 |
| 通过 | - | - |
| 新增消费者测试 | 1 程序 / 3 断言，通过 | test_package/test_superopt.sh：运行安装的 superopt-sparc 二进制，断言真实合成运行（`-flts0 -as` 输出结果序列，README 示例用例）、空参数退出码、未知选项退出码 |

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 直接编译报 `You have to choose target CPU type` | superopt.c 需要 -D 目标 CPU 宏，裸编译不可行 | 逐机型 -D 宏循环编译，全量 14 变体交付 |
| 2 | Makefile `CC = gcc` 硬编码 | 上游 Makefile 覆盖环境变量 | 配方内直接调用 conf 提供的 clang（R33），不走上游 Makefile |

## 路径 A/B 判断
**不走路径 B，按纯路径 A 交付。** 单文件工具、逐机型 -D 编译属常规无构建系统族适配
（检查清单 makefile/无构建系统条目已覆盖），无跨仓库复用的新知识增量。

## 已知限制
- 14 个机型变体均按上游语义全量交付；工具为纯计算搜索器，不依赖目标机硬件。
---

**编译结束**: 2026-09-15 06:22
**最终状态**: built
