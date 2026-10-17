# libamplsolver

AMPL Solver Library（ASL）：AMPL（A Mathematical Programming Language）求解器接口库，提供读取 AMPL 通用输出（`.nl`）文件和写入解（`.sol`）文件的例程，帮助自定义求解器与 AMPL 集成。纯 C 实现，无第三方依赖。

## 功能概述

- 读取 AMPL 通用输出 `.nl` 文件（fg/pfgh 等模式）
- 写入 AMPL 解 `.sol` 文件
- 提供 ASL 结构分配/释放（`ASL_alloc` / `ASL_free`）及目标/约束/梯度/Jacobian/Hessian 求值例程
- 内含自包含的 printf/浮点转换（dtoa）等运行时例程，不依赖外部库

## OHOS 适配

- 构建系统为传统 raw Makefile（`makefile.u`），上游无默认 `Makefile`/`makefile`，必须显式 `make -f makefile.u`
- `make` 需在源码目录执行（`cwd=self.source_folder`），`arith.h` 目标会在构建期编译并运行 `arithchk.c` 探针生成平台头文件（真机可运行，产物就地生成）
- 构建产物为 `amplsolver.a`（无 `lib` 前缀），打包时改名为 `libamplsolver.a`，下游可用标准 `-lamplsolver` 链接
- 编译器从 Conan conf 获取（R33），构建使用 `-fPIC` 便于链接进共享库
- 上游无自动化测试套件（makefile 无 check/test 目标、无 tests/ 目录），由 test_package 对真实 ASL API 做 6 项消费者断言验证

## 依赖关系

- 编译依赖：无
- 运行依赖：libm（`-lm`，按需）

## 参考资料

- 上游 netlib 源码：https://ampl.com/netlib/ampl/ （solvers.tgz）
- Debian 源码包：https://sources.debian.org/src/libamplsolver/
- 许可证：BSD-3-Clause
