# spooles 2.2 适配笔记

## 编译环境

- 构建系统: 纯 Makefile（无 configure，递归子 make）
- 适配日期: 2026-09-23
- 编译器: clang 15（真机 `/data/service/hnp/bin/clang`，经 Conan conf 注入）
- 状态: built（待 HMBS 真机 rule4 门禁通过后由后端提交）

## 上游信息

- 上游仓库/主页: https://www.netlib.org/linalg/spooles/spooles.2.2.html
- 源码包: https://www.netlib.org/linalg/spooles/spooles.2.2.tgz
- sha256: `a84559a0e987a1e423055ef4fdf3035d55b65bbe4bf915efaa1a35bef7f8c5dd`
  （与 FreeBSD ports、Spack、Homebrew 三方记录一致）
- 许可: 公共领域（netlib 原文 "entirely within the public domain"），
  配方 `license = "LicenseRef-SPOOLES-Public-Domain"`
- 依赖: 无（纯 C，无第三方依赖；W0 无需检查制品仓）

## 源码结构审计（R51 第一步：清点）

- 归档共 1871 个成员，无顶层目录：`Make.inc` 与顶层 `makefile` 直接位于源码根。
  因此 `source()` 使用 `strip_root=False`（`True` 会因缺少单一根目录而失败）。
- 45+ 功能模块（A2/BKL/Chv/DV/ETree/FrontMtx/InpMtx/LinSol/Tree/…），
  每模块 `src/makefile`（单模块库）+ `src/makeGlobalLib`（向根 `spooles.a` 追加）。
- 顶层 `makefile` 目标仅四类：`drivers`（各模块演示驱动）、`lib`（不含
  MPI/MT）、`global`（`make -f makeGlobalLib` 全量归档，MPI/MT 注释在外）、
  `clean`。**无 `check`/`test`/`tests` 目标**（配方 `_assert_no_upstream_test_target`
  做机器复核）。
- `drivers/` 下的 `test*.c`（如 `InpMtx/drivers/testIO.c`）全部经 argv 读取外部
  `*.inpmtxf/*.inpmtxb` 矩阵文件，无自包含断言、无聚合入口、无期望输出比对：
  属于示例程序，不是测试套件。结论见 `test_package/MANIFEST.yml` 的
  `upstream_test_audit`，按 `no_tests` 申报（`upstream_test_total: 0`）。

## 构建方案（路径 A：基础适配）

1. `Make.inc` 改写（配方 `_patch_make_inc`，R33：取值全部来自
   `tools.build:compiler_executables` conf）：
   `CC=<conf c>`、`CFLAGS=-O2 -fPIC`、`AR=<conf ar>`、`RANLIB=<conf ranlib>`。
   上游默认 `CC=/usr/lang-4.0/bin/cc`、`RANLIB=echo` 在 OHOS 上不可用；
   `-fPIC` 保证静态归档可被共享消费方链接。
2. `Tree/src/makeGlobalLib` 的 `drawTree.c` → `draw.c`
  （配方 `_fix_tree_make_global_lib`，改前校验引用存在且 `draw.c` 存在；
   与 Spack/Homebrew/FreeBSD 三方修复同因）。
3. `make -f makefile global -j1`（R9：递归子 make 串行，禁用并行），
   产物根目录 `spooles.a`。
4. MT（多线程）与 MPI 子目录保持上游默认（在 `global` 中注释在外）不启用：
   MT 需要 `-DUSE_MT` 消费约定，MPI 需要外部 MPI 工具链，均超出基础适配范围。

## 产物布局

- `lib/libspooles.a`（由 `spooles.a` 改名，`-lspooles` 可链接）
- `include/` 下保留源码树头文件相对布局（如 `FrontMtx/FrontMtx.h`、
  `IV/IV.h`），消费方单 `-I<package>/include` 即可同时满足入口 include
  与模块间 `../Xxx.h` 相对引用。
- `package_info()`: `libs=["spooles"]`，`system_libs=["m", "pthread"]`
  （`Make.inc` 的 `THREAD_LIBS=-lpthread` 同源；R32 用 `in ("Linux", "OHOS")`），
  另声明 `cmake_file_name`/`cmake_target_name=spooles::spooles`/`pkg_config_name`。

## test_package 设计（R34 + rule12 完整消费者用例）

- `test_spooles.c` 直调三模块真实 API，全内存、确定性、无需输入文件：
  IV（`IV_new/IV_init/IV_size/IV_entry/IV_free`，4 断言）、
  DV（`DV_new/DV_init/DV_size/DV_entry/DV_free`，3 断言）、
  InpMtx（`InpMtx_new/InpMtx_init/InpMtx_inputRealEntry/InpMtx_free`，
  对 `[[4,1],[1,3]]` 校验 `nent/coordType/inputMode`，3 断言）。
- 端到端完整消费者用例（`test_e2e_spmv_persist`，5 断言，rule12）：
  同 2x2 矩阵组装→真实计算内核 `InpMtx_nonsym_gmvm` 做 `y=A*x`
 （x=[1,2] 期望 y=[6,7]，源码 `InpMtx/src/gmvm.c` 核实直接支持
  BY_ROWS 裸三元组，无需预排序）→`InpMtx_writeToFormattedFile` 落盘→
  新对象 `InpMtx_readFromFormattedFile` 重载（校验 `nent==4`）→重载对象
  复算结果一致。组装/计算/落盘/重载/复算全流程，非纯断言。
- 共 15 处 `CHECK`，程序末尾自校验总数（变动即非零退出），
  `test()` 的 `HMBS_TEST_PACKAGE_RESULT{discovered:15,passedCount:15}` 以
  退出码 0 为通过证据（OHOS 上经 `CONFIG_SHELL` bash 包裹执行 ELF）。
- 上游标记：`HMBS_UPSTREAM_TEST_RESULT{status:no_tests,discovered:0,...}`
  由 `build()` 在完成机器复核后输出。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 归档无顶层目录 | 1999 年 netlib 打包风格 | `get(..., strip_root=False)` |
| 2 | `Tree/src` 构建失败：找不到 drawTree.c | 上游 `makeGlobalLib` 过时引用 | 改写为 `draw.c`（三方同修） |
| 3 | 默认编译器/ranlib 在 OHOS 不可用 | `Make.inc` 写死历史路径 | 从 Conan conf 注入 CC/AR/RANLIB |
| 4 | 上游无测试套件 | 只有需外部输入的 drivers | `no_tests` 如实申报 + 自建 10 断言检查 + 1 个端到端 SpMV/落盘重载消费者用例（5 断言，共 15） |

## 验证结果

- 本轮为配方准备轮（Windows 本机，无 conan/OHOS 工具链，不在本机运行 conan）；
  真机预检（conan create 全量：`make global` + 上游复核 + test_package 15 断言）
  由 HMBS 后台执行，evidence 轮回填 PR 正文通过率。

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libspooles.a | SPOOLES 核心静态库（串行全模块归档） |
| include/** | 全模块头文件（源码树相对布局） |

## 注意事项

1. 消费示例：`cc prog.c -I<spooles>/include <spooles>/lib/libspooles.a -lm -lpthread`
   或 CMake `find_package(spooles)` + `target_link_libraries(t spooles::spooles)`。
2. 头文件入口为扁平包装头形式（如 `#include "InpMtx.h"`，顶层带 `#ifndef` 守卫），
   常量在 `SPOOLES.h`。不要直接含 `InpMtx/InpMtx.h` 等子路径头（无守卫，会重定义）。
3. 需要 MT 符号（`-DUSE_MT` + CalculiX/preCICE 适配）或共享库的场景超出本版本范围，
   后续版本可再议。
4. 消费方必须用扁平包装头（`#include "IV.h"` / `#include "InpMtx.h"` 等，
   顶层带 `#ifndef` 守卫）；不要直接含子路径 `IV/IV.h`（无守卫），否则与
   `SPOOLES.h` 传递包含的同一定义重复（2026-09-23 真机 test_package 教训）。
