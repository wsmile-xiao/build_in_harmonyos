# PaPILO - Parallel Presolve for Integer and Linear Optimization

> C++ header-only library providing parallel presolve routines for MIP and LP problems

## 简介

PaPILO (Parallel Presolve for Integer and Linear Optimization) 是一个基于 C++14 的软件包，提供并行预求解功能，用于混合整数线性规划（MIP）和线性规划（LP）问题。它使用模板实现，允许切换到更高精度或使用 boost multiprecision 包的理性算术。

PaPILO 是 SCIP Optimization Suite 的一部分，可以作为 header-only 库使用，也提供可执行文件。可执行文件可以基于文件预求解和后求解 MILP 实例。此外，PaPILO 可以链接到 SCIP、SoPlex、Gurobi、Glop 和 HiGHS 等求解器，并作为前端使用。

## OHOS 适配要点

1. **系统识别问题**：CMake 无法识别 HarmonyOS 系统，会警告 "System is unknown to cmake"，但不影响编译。
2. **TBB 依赖**：Intel TBB 默认未安装。可使用 `-DTBB=off` 禁用（性能会下降），或安装 TBB（推荐）。
3. **GMP 依赖**：需要手动指定 GMP 安装路径，使用 `-DGMP_DIR=/path/to/gmp`。
4. **测试构建**：单元测试链接失败（libc++ 符号缺失），建议禁用测试 `-DBUILD_TESTING=off`。
5. **Boost 依赖**：如果缺少 Boost iostreams/serialization/program_options，可执行文件不会构建（仅构建库）。

## 排除与替代

由于缺少 Boost iostreams/serialization/program_options，可执行文件（papilo-bin）未构建。PaPILO 只能作为库使用。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| Boost | >= 1.65 | 必须，header-only 库 |
| GMP | >= 6.0 | 可选，高精度算术 |
| TBB | >= 2020 | 可选，并行加速（强烈推荐）|

## 功能验证

由于可执行文件未构建，验证通过编译测试程序：

```cpp
#include <papilo/core/Problem.hpp>
#include <papilo/core/Presolve.hpp>

int main() {
    papilo::Problem<double> problem;
    return 0;
}
```

编译命令：
```bash
clang++ -std=c++14 -I/path/to/papilo/include test.cpp -o test
```

## 参考

- [官方文档](https://scipopt.org/)
- [源码仓库](https://github.com/scipopt/papilo)
- [SCIP Optimization Suite](https://scipopt.org/)