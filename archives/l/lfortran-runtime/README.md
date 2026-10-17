# lfortran-runtime

> LFortran（LLVM 系现代 Fortran 编译器）的 **C 运行时库** `liblfortran_runtime` 的 OpenHarmony/HarmonyOS PC 适配包。

## 是什么

LFortran 在把 Fortran 源码编译为可执行程序/库时，生成的代码会调用一组约定命名的
运行时函数（`_lfortran_*` / `_lcompilers_*`，如 `_lfortran_dsin`、`_lfortran_sum`、
`_lfortran_random`、`_lfortran_enable_fpe_traps`）。这些函数由 LFortran 随编译器发布的
**C 运行时库** `liblfortran_runtime` 提供，源码位于上游 `src/libasr/runtime/lfortran_intrinsics.c`。
本包把该运行时库单独交付给 HarmonyOS PC（aarch64）平台。

## 功能概述

- Fortran 数值 intrinsic（三角/双曲/指数/对数/复数/位运算等）的 C 实现
- 字符串与字符数组操作（拼接/切片/查找/大小写/trim）
- 格式化 I/O（`_lfortran_printf` / `_lcompilers_snprintf`、WRITE/READ 序列化）
- 类型杂项：kind 查询、复数运算、随机数、命令行参数、文件单元管理
- 运行时诊断：stacktrace / RTTI（可选特性，默认关闭）、FPE trap 设置

## OHOS 适配要点

1. **只交付 C 运行时库**：运行时库为纯 C 单文件，可独立编译，无需 LLVM/MLIR 全量工程；
   上游 Fortran 侧运行时模块（`src/runtime/*.f90`）需 LFortran 编译器自举，不在本包范围。
2. **musl 缺失 glibc 扩展**：`liblfortran_runtime` 的 `_lfortran_enable_fpe_traps()` 调用
   `feenableexcept`（GNU/glibc 扩展）。OHOS 用 musl，不提供该符号 → 补丁以 ARMv8-A **FPCR**
   trap 位直写替代（`__GLIBC__` 之外分支），消除未定义符号。若不打补丁，静态链接受损、
   动态库运行期符号解析失败。
3. **产物命名/布局与上游一致**：`liblfortran_runtime.so`（SOVERSION 0）/ `liblfortran_runtime_static.a`，
   头文件 `include/lfortran/impure/lfortran_intrinsics.h`。

## 依赖关系

- 编译依赖：无第三方依赖；OHOS SDK clang + llvm-ar（配方从 Conan 配置取编译器路径）
- 运行依赖：libc / libm

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 0.61.0 | built | 首个适配版本（HarmonyOS PC aarch64） |

## 参考资料

- 上游官网：https://lfortran.org
- 上游仓库：https://github.com/lfortran/lfortran
- 运行时源码：`src/libasr/runtime/lfortran_intrinsics.c`
