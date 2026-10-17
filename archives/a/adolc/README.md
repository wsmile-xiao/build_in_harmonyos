# ADOL-C (adolc)

ADOL-C（Automatic Differentiation by OverLoading in C++）是 C/C++ 程序的自动微分（Automatic Differentiation, AD）开源库，属于 COIN-OR 项目。

## 功能概述

- 通过 C++ 运算符重载实现前向/反向模式的自动微分
- 计算任意阶导数向量/矩阵（稠密与稀疏格式）
- 提供 Taylor 系数向量及其 Jacobian 的 ODE 求解器专用例程
- 提供与 C、C++、Fortran 等语言的链接接口
- 支持求解显式或隐式函数的高阶导数张量

## OHOS 适配

- 基于 autotools 构建系统，适配 HarmonyOS aarch64 平台
- config.guess/config.sub 补 HarmonyOS 三元组识别（aarch64-unknown-linux-ohos，E205/E072）
- configure 临时目录 umask 077→022（E129，HMDFS 权限）
- 链接 libclang_rt.builtins.a 使 libadolc.so 自包含 quad-float 符号（taylor.o 用 long double，E098 模式）
- 可选依赖（ColPack/Boost/OpenMP）在 ohpcd 未发布，保持禁用（`--enable-sparse=no --without-boost`）
- 上游 `make check`（run_tests）验证通过：powexam / speelpenning 测试 passed

## 依赖关系

- 编译依赖：clang/clang++（aarch64-unknown-linux-ohos）、autotools
- 运行依赖：libclang_rt.builtins（静态内链，运行时自包含）
- 可选依赖（默认禁用）：ColPack、Boost、OpenMP

## 参考资料

- 官网/源码：https://github.com/coin-or/ADOL-C
- COIN-OR 项目主页：https://www.coin-or.org
