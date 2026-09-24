# libsepol 3.11 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure/cmake）
- 编译日期: 2026-09-21
- 编译器: clang 15（OHOS aarch64，Conan profile ci/conan/profiles/ohos-aarch64）
- 状态: built

## 编译步骤
- `make -C libsepol -j1 CC=<conan注入clang> CFLAGS='-O2 -fPIC -D_GNU_SOURCE -I. -I../include' DISABLE_SHARED=y all`（R33：编译器从 Conan conf 取，不裸用 shell 变量）
- 打包：libsepol/include 头树 + **libsepol/cil/include/cil/*.h → include/sepol/cil/**（对齐上游 `make install` 的 CIL 头安装布局）+ libsepol.a + libsepol.pc

## 为什么要做 3.11（下游驱动）
- secilc 3.11 的 secilcheck 链接需要 3.11 新增符号 `sepol_kernel_policydb_decls_to_cil`、`cil_check_neverallows_against_pdb`，libsepol/3.10 制品中不存在（nm 实测）
- 升级后静态库继续合并全部 CIL 符号（`nm libsepol.a | grep ' T cil_'` ≈585 个）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 3.10 制品不带 sepol/cil/cil.h，下游 secilc include 失败 | 3.10 配方 package() 只装 libsepol/include，未装 cil 头 | 本版 package() 按上游安装布局补装 cil/include/cil/*.h → include/sepol/cil/ |

## 依赖版本
- 无编译依赖

## 测试账本（§10.1 五维口径）
- N_static = 28（上游 `libsepol/tests/` 的 **CUnit 套件**：7 suite / 28 注册用例；由 `tests/Makefile:70` 的 `test:` 目标驱动，链接 `-lcunit` 且调用同源码树 `checkpolicy`、m4 预处理 `.conf`）
- N_executed = 28（**已在 build() 真实执行**：`Run Summary: suites 7 / tests 28 / Ran 28 / Passed 28 / Failed 0`，asserts 854589 全通过；MLS 变体 24/24。接入三件：`test_requires(cunit/2.1.3)` + 先建 `checkpolicy`（传 `LIBSEPOLA`）+ `test:` 目标须用 `LDFLAGS` 注入 `-L`）
- N_consumer = 1（test_package/test_sepol：handle 生命周期 / boolean record / context record 往返断言 + 编译期包含 sepol/cil/cil.h）

## 路径 B 判断
- 本任务为既有 3.10 配方的版本升级 + 下游驱动的 CIL 头补装，属"普通配方升级"，无跨仓库复用的新知识增量（CIL 头布局属上游 install 事实），判纯 A，不走 B。

## 验证结果
- conan-verify：见 reports/conan-verify-report.md（G0-G4）

---
**编译结束**: 2026-09-21
**最终状态**: built
