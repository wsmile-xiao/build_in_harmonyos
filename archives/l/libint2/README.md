# Libint2

Libint2 是用于计算高斯函数上多体算符分子积分的 C/C++ 库（量子化学电子积分库），
由 Edward F. Valeev 开发。上游仓库：<https://github.com/evaleev/libint>。

本归档适配的是上游官方 Release 资产 `libint-2.7.2.tgz`（exported library），
即已由 libint 编译器生成全部积分 kernel 源码的发布包（`src/` 6520 个 `.cc`），
自带上游 CTest 测试，使用 CMake 构建。

## 特性

- 1 电子积分（overlap / kinetic / nuclear / multipole / sphemultipole 等）
- 2/3/4 中心电子排斥积分（ERI，最大角动量 l=6，generic code + FMA）
- C API（`libint2.h`）与 C++11 API（`libint2.hpp`，`libint2::BasisSet` / `libint2::Engine`）
- 基组数据库（`share/libint/2.7.2/basis`，81 个文件，含 STO-3G/6-31G*/cc-pVXZ 等）
- CMake package config（`libint2-config.cmake`，`Libint2::int2` / `Libint2::cxx`）

## 依赖

- **eigen/3.4.0**（必需）：C++ API（`REQUIRE_CXX_API` 默认 ON）需要 Eigen 头文件，
  作为公开依赖传递给消费者。
- Boost：可选。系统未提供时上游自动解包包内 `external/boost.tar.gz`
  （Boost.Preprocessor）并安装到 `include/libint2/boost`，因此不引入 Conan 依赖。
- GMP / MPFR：**不需要**。它们只是 libint *编译器*（生成 kernel 源码）的依赖，
  本归档使用上游预生成库 tarball，不运行代码生成器。
- Fortran 绑定默认关闭（无 Fortran 工具链）。

## 构建要点（OHOS / HarmonyOS PC）

- 默认构建**静态库** `libint2.a`（上游 `ARCHIVE_OUTPUT_NAME` 为 `int2`，非系统同名库，
  R26 口径下静态可避免 OHOS 上 RPATH / 依赖链问题）。
- 上游测试在 `build()` 中通过 `ctest --output-on-failure -R libint2/` 真实执行
  （生成 4 组测试：`eritest`、`unit`、`hf`、`hf++`）。
- `package_info()` 中定义 `DATADIR=<pkg>/share/libint/2.7.2`，使消费者可以按名加载
  基组（如 `libint2::BasisSet("sto-3g", atoms)`）。
- 上游 `CMakeLists.txt` 的 `cmake_minimum_required(VERSION 3.8)` 与 OHOS 环境
  CMake 4.1.2 兼容；CMake 会对未知 host 系统名 `HarmonyOS` 打印提示（非错误）。

## 构建规模（供超时预算参考）

- 6520 个 kernel 源文件，本机 20 核并行全量编译约 18-20 分钟；
- 本地 W3 完整 CI 模拟（强制重建 + 上游 ctest + test_package + L4/L5）实测 ≈29.5 分钟
  （1763s），在 CI 默认 3600s 预算内，未申请超时覆盖。
