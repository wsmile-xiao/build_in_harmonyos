# DRAFT-cgl-0.60.10.1-osi-clp-pc-alias — COIN-OR AC_COIN_CHECK_PACKAGE 探测名缺失 → 条件编译子模块与公开头双缺失，配方 generate() 生成兼容别名 .pc 恢复

## 问题现象

已发布 `cgl/0.60.10` Conan 包存在打包缺陷：`include/coin/` 仅 28 个头文件，
缺失 `CglLandP.hpp` 与 `CglLandPValidator.hpp`；`libCgl.a` 内无
CglLandP/CglLandPValidator 类符号。消费方 cbc 2.10.13 `CbcSolver.cpp:216`
无条件 `#include "CglLandP.hpp"`，编译必然失败：

```
fatal error: 'CglLandP.hpp' file not found
```

上游官方源码 `releases/0.60.10` 确实包含 `src/CglLandP/` 及
`CglLandP.hpp`/`CglLandPValidator.hpp`——上游无缺失，缺陷在打包侧。

## 根因分析

1. **探测名不匹配**：Cgl `configure.ac:73`
   `AC_COIN_CHECK_PACKAGE(OsiClp, [osi-clp], [CglLib])` 按 pkg-config 名
   `osi-clp` 探测 Clp 依赖；已发布 `clp/1.17.10` 包只导出 `clp.pc`，
   无 `osi-clp.pc` → 探测静默失败 → `COIN_HAS_OSICLP` 未定义。
2. **条件编译整段跳过**：`src/CglLandP/Makefile.am`
   `if COIN_HAS_OSICLP` 分支才编译 CglLandP 源文件，且
   `includecoin_HEADERS = CglLandP.hpp CglLandPValidator.hpp` 只在同一
   条件下安装头文件 → 子模块源 + 公开头整体被排除。
3. **无任何打包期报错**：configure/make 均成功，缺陷直到消费方
   include 该头文件才暴露（"缺头文件/缺符号"双缺失型打包缺陷）。

## 解决方案

1. **兼容别名 .pc**：`generate()` 中从 PkgConfigDeps 生成的 `clp.pc` 读取
   Version，写入 `osi-clp.pc`（`Name: OsiClp` + `Requires: clp`），使
   `AC_COIN_CHECK_PACKAGE` 探测命中、`COIN_HAS_OSICLP` 定义。
2. **显式 --with-\* 双保险**：configure 传
   `--with-osiclp-incdir='{clp}/include/coin'` 与
   `--with-osiclp-lib='libOsiClp.a libClp.a …'`。
3. **消费者闭包传递**：`package_info()` 把依赖 include 目录
   （`{coin-or}/include/coin`、`{clp}/include/coin`）加入
   `cpp_info.includedirs`（CglLandP 公开头裸名 include Osi 头），并把
   clp 包内已发布但未声明的 `libOsiClp.a` 以 `libs + libdirs` 方式传给
   CMakeDeps 消费者。
4. **测试数据自包含**：启用 OSICLP 后上游 `unitTest` 的测试段需要
   `Data/Sample/*.mps`（coin-or-tools/Data-Sample 独立数据集），配方
   conandata 声明 `test_data`（releases/1.2.13，sha256 cb4c37…）在
   build() 中自取官方数据集，`make test` 全量通过。

## 验证

- `nm libCgl.a | grep -c CglLandP` → 97（含 CglLandP/CachedData/Parameters/
  Validator 等 T/W 定义符号）
- `include/coin/CglLandP.hpp`、`include/coin/CglLandPValidator.hpp` 均已安装
- 上游 unitTest 14 段（OSICLP）全过："All tests completed successfully"
- test_package 3 用例（test_cgl / landp_ohos_test / landp_consumer）
  真实编译链接运行全 PASS（ctest 3/3）

## R02 数据路径补充（CI 实测修正）

启用 OSICLP 后上游 `make test` 需要 `Data/Sample/*.mps`；数据放置路径必须与
测试实际 cwd 对齐：conan build 布局下 COIN-OR 项目根为 `{src}/Cgl`，`make test`
从 `{src}/Cgl/test` 把 `../../Data/Sample` 解析为 `{src}/Data/Sample`。若配方用
`os.path.dirname(src)` 会高一层（`{parent}/Data/Sample`），导致数据缺失、
`Coin6001E` + `CglGomoryTest:1468` 断言失败。修正为
`os.path.join(src, "Data", "Sample")` 后 make test 14/14 通过（CI 布局复现验证）。

## 适用边界与反例

- 适用：所有使用 `AC_COIN_CHECK_PACKAGE`/pkg-config 探测的 COIN-OR 系
  autotools 库（cgl/clp/osi/coinutils/cbc 系）；一般"上游探测名 ≠ 依赖包
  导出 .pc 名"的 autotools 库。
- 反例：CMake `find_package` 系探测不受影响（按 config 名，别名机制不同）；
  探测名已存在的库不需要别名。
- 约束：不得伪造头文件/符号，必须来自官方源码真实构建；别名 .pc 只补探测
  名，不改变真实依赖闭包。

## 关系

- similar_to: E075（pkg-config 环境陷阱）、E089（autotools pkg.m4）、
  E247（pkg-config 静态链接闭包）
- caused_by: COIN-OR 上游 AC_COIN_CHECK_PACKAGE 探测设计 + 依赖包 .pc
  导出名约定
- prerequisite_of: cbc/2.10.13（CglLandP 消费者）
